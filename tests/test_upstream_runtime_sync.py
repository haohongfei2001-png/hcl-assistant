"""Synthetic sync orchestration/provenance regressions; no research evaluation."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from packages.runtime_bridge import contract
from scripts.upstream_runtime_sync import CHECKS, LOCK, build_candidate, command_runner, snapshot, sync, validate_handshake
from scripts.publish_runtime_sync import MARKER, publish, validate_evidence

ROOT = Path(__file__).resolve().parents[1]
SHA = '1' * 40
BASE = '2' * 40


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'product'; self.root.mkdir()
        for path in ('contracts/runtime-bridge.lock.json', 'contracts/capabilities.json'):
            dest = self.root / path; dest.parent.mkdir(exist_ok=True); dest.write_bytes((ROOT / path).read_bytes())
        self.output = Path(self.temp.name) / 'receipts'
        self.stable = json.loads((self.root / LOCK).read_text())
        self.original = (self.root / LOCK).read_bytes()
        self.calls = []; self.stages = []; self.fail_stage = None; self.drift = None
        self.identity = patch('scripts.upstream_runtime_sync.product_identity', return_value=BASE); self.identity.start(); self.addCleanup(self.identity.stop)
        self.publisher_identity = patch('scripts.publish_runtime_sync.product_identity', return_value=BASE); self.publisher_identity.start(); self.addCleanup(self.publisher_identity.stop)
        self.patch_env = patch.dict(os.environ, {'PRODUCT_SHA': BASE}); self.patch_env.start(); self.addCleanup(self.patch_env.stop)

    def get(self, endpoint):
        self.calls.append(endpoint)
        if endpoint == 'commits/main': return {'sha': SHA}
        if endpoint == 'git/commits/' + SHA: return {'sha': SHA, 'tree': {'sha': '3' * 40}}
        if endpoint == 'git/trees/' + '3' * 40:
            return {'sha': '3' * 40, 'tree': [{'path': 'hcl', 'type': 'tree', 'mode': '040000', 'sha': '4' * 40}]}
        if endpoint == 'git/trees/' + '4' * 40:
            return {'sha': '4' * 40, 'tree': [{'path': 'cognition', 'type': 'tree', 'mode': '040000', 'sha': '5' * 40}]}
        if endpoint == 'git/trees/' + '5' * 40:
            rows = []
            for name in contract.PATHS:
                data = ('# original synthetic module ' + name).encode()
                blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                rows.append({'path': Path(name).name, 'type': 'blob', 'mode': '100644', 'sha': blob})
            return {'sha': '5' * 40, 'tree': rows}
        allowed = {'contents/' + p + '?ref=' + SHA: p for p in contract.PATHS}
        self.assertIn(endpoint, allowed)
        name = allowed[endpoint]; data = ('# original synthetic module ' + name).encode()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        return {'type': 'file', 'path': name, 'encoding': 'base64', 'sha': blob,
                'content': base64.b64encode(data).decode()}

    def runner(self, command, work, env, log):
        stage = log.stem; self.stages.append(stage)
        self.assertNotEqual(work, self.root)
        if stage == self.fail_stage: raise subprocess.CalledProcessError(1, command)
        config = json.loads((work / LOCK).read_text())
        with patch.object(contract, 'ROOT', work), patch.object(contract, 'LOCK', work / LOCK):
            discovery = contract.manifest(config)
        if stage == 'manifest': log.write_text(json.dumps(discovery))
        elif stage == 'handshake':
            ready = {k: config[k] for k in ('source_commit_sha', 'bridge_version', 'artifact_digest', 'interface_version', 'interface_digest', 'capability_manifest_digest')}
            ready.update(handshake_status='READY', production_enabled=False,
                         runtime_identity={'source_repository': contract.REPOSITORY}, discovered_capabilities=discovery['capabilities'])
            if self.drift == 'interface': ready['interface_version'] = 'incompatible-v2'
            if self.drift == 'manifest': ready['discovered_capabilities'].append(copy.deepcopy(discovery['capabilities'][0]))
            if self.drift == 'production': ready['discovered_capabilities'][0]['product_activation_policy']['production_enabled'] = True
            log.write_text(json.dumps(ready))
        elif stage == 'smoke':
            log.write_text(json.dumps({'smoke': 'PASS', 'pin': {'source_commit_sha': SHA}, 'production_enabled': False,
                                      'runs': [{'receipt': {'usage': {'provider_calls': 0}}}]}))
        else: log.write_text('Synthetic orchestration fixture PASS\n')

    def run_sync(self): return sync(self.root, self.output, self.get, self.runner)

    def test_upstream_unchanged_only_reads_main_identity(self):
        report = sync(self.root, self.output, lambda endpoint: {'sha': self.stable['source_commit_sha']}, self.runner)
        self.assertEqual(report['status'], 'UP_TO_DATE'); self.assertEqual(self.stages, [])
        self.assertIsNone(report['candidate_sha']); self.assertFalse((self.output / 'candidate.lock.json').exists())
        self.assertEqual((self.root / LOCK).read_bytes(), self.original)

    def test_compatible_new_sha_promotable_only_after_every_check(self):
        report = self.run_sync()
        self.assertEqual(report['status'], 'VERIFIED_CANDIDATE')
        self.assertEqual(self.stages, list(CHECKS)); self.assertEqual(len(self.calls), 8)
        self.assertEqual(report['stable_verified_sha'], self.stable['source_commit_sha'])
        self.assertEqual((self.root / LOCK).read_bytes(), self.original)
        candidate = json.loads((self.output / 'candidate.lock.json').read_text())
        self.assertEqual(candidate['source_commit_sha'], SHA)
        self.assertNotEqual(candidate['capability_manifest_digest'], self.stable['capability_manifest_digest'])
        self.assertEqual(candidate['interface'], self.stable['interface'])
        self.assertEqual(candidate['execution_policy'], self.stable['execution_policy'])
        validate_evidence(self.root, self.output)

    def test_interface_manifest_and_activation_drift_refuse_candidate(self):
        for drift in ('interface', 'manifest', 'production'):
            with self.subTest(drift=drift):
                self.drift = drift; report = self.run_sync()
                self.assertEqual(report['failed_stage'], 'handshake'); self.assertEqual(report['status'], 'FAILED')
                self.assertFalse((self.output / 'candidate.lock.json').exists())
                self.assertEqual((self.root / LOCK).read_bytes(), self.original)

    def test_each_failed_check_preserves_stable_and_removes_stale_success(self):
        self.assertEqual(self.run_sync()['status'], 'VERIFIED_CANDIDATE')
        for failed in CHECKS:
            with self.subTest(failed=failed):
                self.stages = []; self.fail_stage = failed; report = self.run_sync()
                self.assertEqual(report['status'], 'FAILED'); self.assertEqual(report['failed_stage'], failed)
                self.assertEqual(self.stages[-1], failed)
                self.assertFalse((self.output / 'candidate.lock.json').exists())
                self.assertEqual((self.root / LOCK).read_bytes(), self.original)
                with self.assertRaises(ValueError): validate_evidence(self.root, self.output)

    def test_missing_file_wrong_repository_commit_or_blob_fails_before_execution(self):
        for drift in ('missing', 'blob', 'commit'):
            def get(endpoint):
                row = self.get(endpoint)
                if endpoint.startswith('contents/'):
                    if drift == 'missing': row['type'] = 'dir'
                    if drift == 'blob': row['sha'] = '0' * 40
                if endpoint.startswith('git/commits/') and drift == 'commit': row['sha'] = '0' * 40
                return row
            with self.subTest(drift=drift):
                self.stages = []; report = sync(self.root, self.output, get, self.runner)
                self.assertEqual(report['status'], 'FAILED'); self.assertEqual(self.stages, [])
                self.assertEqual((self.root / LOCK).read_bytes(), self.original)
        wrong = copy.deepcopy(self.stable); wrong['source_repository'] = 'other/runtime'
        with self.assertRaises(ValueError): build_candidate(wrong, SHA, self.get)
        with self.assertRaises(ValueError): build_candidate(self.stable, 'main', self.get)

    def test_symlink_submodule_or_missing_tree_file_never_reads_contents(self):
        for mode in ('120000', '160000', 'MISSING', 'ANCESTOR', 'TREE_DIGEST'):
            self.calls = []; self.stages = []
            def get(endpoint):
                row = self.get(endpoint)
                if endpoint == 'git/trees/' + '5' * 40:
                    if mode == 'MISSING': row['tree'].pop()
                    elif mode == 'TREE_DIGEST': row['sha'] = '0' * 40
                    elif mode != 'ANCESTOR': row['tree'][0]['mode'] = mode
                if mode == 'ANCESTOR' and endpoint == 'git/trees/' + '3' * 40:
                    row['tree'][0].update(mode='120000', type='blob')
                return row
            with self.subTest(mode=mode):
                report = sync(self.root, self.output, get, self.runner)
                self.assertEqual(report['status'], 'FAILED')
                self.assertFalse(any(p.startswith('contents/') for p in self.calls))
                self.assertEqual(self.stages, [])
                self.assertEqual((self.root / LOCK).read_bytes(), self.original)

    def test_verified_candidate_digest_or_blob_tampering_cannot_publish(self):
        self.run_sync()
        p = self.output / 'candidate.lock.json'; original = p.read_bytes()
        for field in ('sha256', 'git_blob_sha'):
            data = json.loads(original); data['files'][contract.PATHS[0]][field] = '0' * 40
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError): validate_evidence(self.root, self.output)
        p.write_bytes(original)
        (self.root / 'new-product-file.md').write_text('concurrent product change')
        with self.assertRaises(ValueError): validate_evidence(self.root, self.output)

    def test_incomplete_success_receipt_cannot_promote(self):
        self.run_sync(); path = self.output / 'receipt.json'; report = json.loads(path.read_text())
        del report['checks']['python']; path.write_text(json.dumps(report))
        with self.assertRaises(ValueError): validate_evidence(self.root, self.output)

    def test_publisher_lock_only_exact_base_no_force_and_safe_automerge(self):
        self.run_sync(); calls = []; enabled = []
        def api(method, endpoint, data=None):
            calls.append((method, endpoint, data))
            if endpoint == 'git/ref/heads/main': return {'object': {'sha': BASE}}
            if endpoint.startswith('pulls?'): return []
            if endpoint == 'git/commits/' + BASE: return {'tree': {'sha': '4' * 40}}
            if endpoint == 'git/blobs': return {'sha': '5' * 40}
            if endpoint == 'git/trees':
                self.assertEqual([x['path'] for x in data['tree']], [LOCK]); return {'sha': '6' * 40}
            if endpoint.startswith('git/ref/heads/product/'): return None
            if endpoint == 'git/commits':
                self.assertEqual(data['parents'], [BASE]); return {'sha': '7' * 40}
            if endpoint == 'pulls':
                self.assertIn(MARKER, data['body']); self.assertIn('Provider calls/spend: **0 / 0**', data['body'])
                return {'number': 9, 'node_id': 'PR9', 'html_url': 'https://example.test/pr/9'}
            if endpoint == '': return {'allow_auto_merge': True, 'allow_squash_merge': True}
            if endpoint == 'branches/main/protection': return {'required_status_checks': {'strict': True, 'contexts': ['planning']}}
            return None
        result = publish(self.root, self.output, api, enabled.append)
        self.assertEqual(result['status'], 'PR_READY'); self.assertEqual(enabled, ['PR9'])
        self.assertEqual((self.root / LOCK).read_bytes(), self.original)
        self.assertFalse(any(method == 'PATCH' and endpoint.startswith('git/') for method, endpoint, data in calls))
        self.assertTrue(any(endpoint.endswith('/dispatches') for method, endpoint, data in calls))
        self.assertEqual(result['stable_verified_sha'], self.stable['source_commit_sha'])

    def test_wrong_product_commit_cannot_test_or_publish(self):
        with patch('scripts.upstream_runtime_sync.product_identity', return_value=None):
            report = self.run_sync()
        self.assertEqual(report['status'], 'FAILED'); self.assertEqual(self.calls, [])
        self.run_sync()
        with patch('scripts.publish_runtime_sync.product_identity', return_value='0' * 40):
            with self.assertRaises(ValueError): validate_evidence(self.root, self.output)

    def test_existing_exact_branch_updates_pr_but_never_replaces_foreign_tree(self):
        self.run_sync(); calls = []; branch = 'product/runtime-sync-' + SHA[:12] + '-' + BASE[:12]
        def api(method, endpoint, data=None):
            calls.append((method, endpoint))
            if endpoint == 'git/ref/heads/main': return {'object': {'sha': BASE}}
            if endpoint.startswith('pulls?'): return [{'number': 9, 'head': {'ref': branch}, 'body': MARKER}]
            if endpoint == 'git/commits/' + BASE: return {'tree': {'sha': '4' * 40}}
            if endpoint == 'git/blobs': return {'sha': '5' * 40}
            if endpoint == 'git/trees': return {'sha': '6' * 40}
            if endpoint.startswith('git/ref/heads/product/'): return {'object': {'sha': '7' * 40}}
            if endpoint == 'git/commits/' + '7' * 40: return {'tree': {'sha': '6' * 40}, 'parents': [{'sha': BASE}]}
            if endpoint == 'pulls/9': return {'number': 9, 'node_id': 'PR9', 'html_url': 'https://example.test/pr/9'}
            if endpoint == '': return {'allow_auto_merge': False, 'allow_squash_merge': True}
            return None
        result = publish(self.root, self.output, api, lambda _: self.fail('Unsafe auto-merge'))
        self.assertEqual(result['status'], 'PR_READY')
        self.assertIn(('PATCH', 'pulls/9'), calls); self.assertNotIn(('POST', 'git/commits'), calls)
        def foreign(method, endpoint, data=None):
            if endpoint == 'git/commits/' + '7' * 40: return {'tree': {'sha': '8' * 40}, 'parents': [{'sha': BASE}]}
            return api(method, endpoint, data)
        self.assertEqual(publish(self.root, self.output, foreign)['status'], 'DEFERRED_BRANCH_OWNERSHIP')

    def test_unprotected_or_non_strict_settings_never_auto_merge(self):
        # Reuse the successful publisher fixture with a settings override.
        # Publication still dispatches exact-head CI and leaves the PR for review.
        self.run_sync()
        def api(method, endpoint, data=None):
            if endpoint == 'git/ref/heads/main': return {'object': {'sha': BASE}}
            if endpoint.startswith('pulls?'): return []
            if endpoint.startswith('git/ref/heads/product/'): return None
            if endpoint == 'git/commits/' + BASE: return {'tree': {'sha': '4' * 40}}
            if endpoint in ('git/blobs', 'git/trees', 'git/commits'): return {'sha': '5' * 40}
            if endpoint == 'pulls': return {'number': 9, 'node_id': 'PR9', 'html_url': 'https://example.test/pr/9'}
            if endpoint == '': return {'allow_auto_merge': True, 'allow_squash_merge': True}
            if endpoint == 'branches/main/protection': return self.protection
            return None
        for protection in (None, {}, {'required_status_checks': {'strict': False, 'contexts': ['planning']}},
                           {'required_status_checks': {'strict': True, 'contexts': ['other']}}):
            self.protection = protection
            result = publish(self.root, self.output, api, lambda _: self.fail('Unsafe auto-merge'))
            self.assertEqual(result['status'], 'PR_READY')
            self.assertEqual(result['auto_merge'], 'NOT_ENABLED_SETTINGS_OR_PROTECTION')

    def test_concurrent_main_or_writer_does_not_publish(self):
        self.run_sync()
        calls = []
        def moved(method, endpoint, data=None):
            calls.append(method); return {'object': {'sha': '9' * 40}}
        self.assertEqual(publish(self.root, self.output, moved)['status'], 'DEFERRED_MAIN_CHANGED')
        self.assertEqual(calls, ['GET'])
        def writer(method, endpoint, data=None):
            self.assertEqual(method, 'GET')
            if endpoint == 'git/ref/heads/main': return {'object': {'sha': BASE}}
            return [{'head': {'ref': 'product/human-work'}, 'body': 'Human writer claim'}]
        self.assertEqual(publish(self.root, self.output, writer)['status'], 'DEFERRED_ACTIVE_PRODUCT_WRITER')

    def test_normal_bridge_never_accepts_candidate_as_floating_or_stable_pin(self):
        self.run_sync(); candidate = json.loads((self.output / 'candidate.lock.json').read_text())
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_VERSION'): contract.validate_config(candidate)
        self.assertEqual(contract.load_config()['source_commit_sha'], self.stable['source_commit_sha'])

    def test_real_command_runner_scrubs_tokens_and_bounds_timeout_errors(self):
        env = {**os.environ, 'GH_TOKEN': 'synthetic-token', 'PRODUCT_READ_TOKEN': 'synthetic-read',
               'NODE_OPTIONS': 'synthetic-options', 'HCL_DEVELOPMENT_ARTIFACT': str(self.root / 'runtime')}
        log = Path(self.temp.name) / 'command.log'
        command_runner([sys.executable, '-c', 'import os,json; print(json.dumps(dict(os.environ)))'], self.root, env, log)
        child = json.loads(log.read_text())
        for key in ('GH_TOKEN', 'PRODUCT_READ_TOKEN', 'NODE_OPTIONS'):
            self.assertNotIn(key, child)
        with self.assertRaises(subprocess.TimeoutExpired):
            command_runner([sys.executable, '-c', 'import time; time.sleep(10)'], self.root, env, log, timeout=0.05)
        with self.assertRaises(subprocess.CalledProcessError):
            command_runner([sys.executable, '-c', 'raise SystemExit(4)'], self.root, env, log)

    def test_workflow_hourly_manual_separate_write_token_and_exact_ci(self):
        workflow = (ROOT / '.github/workflows/upstream-runtime-sync.yml').read_text()
        self.assertIn("cron: '17 * * * *'", workflow); self.assertIn('workflow_dispatch:', workflow)
        candidate, publisher = workflow.split('  publish:\n')
        self.assertNotIn('GH_TOKEN', candidate); self.assertNotIn('contents: write', candidate)
        self.assertIn('VERIFIED_CANDIDATE', publisher); self.assertIn('persist-credentials: false', workflow)
        self.assertNotIn('pull_request_target', workflow); self.assertNotIn('secrets.', workflow)
        self.assertIn('workflow_dispatch:', (ROOT / '.github/workflows/hcl-assistant-planning.yml').read_text())
