"""Compatibility and provenance, never semantic efficacy."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from packages.runtime_bridge.contract import load_config, validate_config, manifest, handshake, fingerprint
from packages.runtime_bridge.bridge import RuntimeBridge


class HandshakeTests(unittest.TestCase):
    def setUp(self): self.config = load_config()

    def test_exact_repository_sha_paths_and_explicit_repin(self):
        for field, value in [('source_repository','other/runtime'), ('source_commit_sha','main'), ('source_commit_sha','v1'),
                             ('source_commit_sha','f'*40), ('bridge_version','2.0'),
                             ('allowed_runtime_paths',['eval/item.py']), ('allowed_runtime_paths',['data/input.py']),
                             ('allowed_runtime_paths',['../hcl/cognition/core.py'])]:
            changed = copy.deepcopy(self.config); changed[field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): validate_config(changed)

    def test_interface_digest_and_manifest_policy_fail_closed(self):
        for change, expected in [({'artifact_digest':'sha256:bad'},'DIGEST_MISMATCH'),
                                 ({'interface_version':'wrong'},'INTERFACE_MISMATCH'),
                                 ({'interface_digest':'sha256:bad'},'INTERFACE_MISMATCH'),
                                 ({'execution_policy':{'production_enabled':True}},'CAPABILITY_MANIFEST_INVALID'),
                                 ({'input_policy':'FORMAL_EVAL_TUNING'},'CAPABILITY_MANIFEST_INVALID')]:
            result = handshake('/missing/artifact', {**self.config, **change})
            self.assertEqual(result['handshake_status'],expected)
            self.assertEqual(result['discovered_capabilities'],[])
        changed=copy.deepcopy(self.config);changed['interface']['capabilities'].append('unknown_capability')
        changed['interface_digest']=fingerprint(changed['interface'])
        self.assertEqual(handshake('/missing',changed)['handshake_status'],'INTERFACE_MISMATCH')

    def test_discovery_does_not_infer_retention_language_or_production(self):
        rows = manifest(self.config)['capabilities']
        self.assertEqual(len(rows),10)
        for row in rows:
            self.assertEqual(row['i06_disposition'],'PENDING_I06')
            self.assertFalse(row['product_activation_policy']['production_enabled'])
            self.assertEqual(row['language'],[])
            if row['capability_id'] in {'belief_interpretation','information_access'}:
                self.assertEqual(row['product_activation_policy']['mode'],'EXPERIMENTAL')
                self.assertEqual(row['runtime_implementation']['source_commit_sha'],self.config['source_commit_sha'])
            else: self.assertIsNone(row['runtime_implementation'])

    def test_discovery_snapshot_drift_cannot_infer_retention(self):
        rows=manifest(self.config)
        rows['capabilities'][1]['i06_disposition']='RETAIN'
        with patch('packages.runtime_bridge.contract.manifest',return_value=rows):
            result=handshake(os.environ['HCL_DEVELOPMENT_ARTIFACT'])
        self.assertEqual(result['handshake_status'],'CAPABILITY_MANIFEST_INVALID')
        self.assertEqual(result['discovered_capabilities'],[])

    def test_wrong_process_identity_and_interface_have_explicit_refusal(self):
        bridge=RuntimeBridge(os.environ['HCL_DEVELOPMENT_ARTIFACT']);ready=bridge.handshake()
        for field,value,status in [('source_commit_sha','f'*40,'UNSUPPORTED_VERSION'),('artifact_digest','wrong','DIGEST_MISMATCH'),
                                  ('interface_version','wrong','INTERFACE_MISMATCH'),('discovered_capabilities',[],'CAPABILITY_MANIFEST_INVALID')]:
            actual={**ready,field:value}
            with patch.object(bridge,'_exchange',return_value=actual):result=bridge.handshake()
            self.assertEqual(result['handshake_status'],status);self.assertEqual(result['discovered_capabilities'],[])

    def test_missing_runtime_is_failed_without_mock_fallback(self):
        result=RuntimeBridge('/does/not/exist').handshake()
        self.assertEqual(result['handshake_status'],'FAILED')
        self.assertFalse(result['discovered_capabilities'])

    def test_corrupt_and_symlink_material_refused_without_tree_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'hcl/cognition';path.mkdir(parents=True)
            (path/'core.py').write_text('altered')
            self.assertEqual(handshake(temp)['handshake_status'],'DIGEST_MISMATCH')
            (path/'core.py').unlink();(path/'core.py').symlink_to('/missing')
            self.assertEqual(handshake(temp)['handshake_status'],'DIGEST_MISMATCH')


class PinnedHandshakeSmoke(unittest.TestCase):
    def test_actual_pinned_runtime_process_handshake(self):
        directory=os.environ.get('HCL_DEVELOPMENT_ARTIFACT')
        self.assertTrue(directory,'Acquire the allowlisted runtime and set HCL_DEVELOPMENT_ARTIFACT; this mandatory smoke never skips.')
        bridge=RuntimeBridge(directory); result=bridge.handshake()
        self.assertEqual(result['handshake_status'],'READY',result)
        self.assertEqual(result['source_commit_sha'],load_config()['source_commit_sha'])
        self.assertEqual(result['interface_version'],'hcl-epistemic-callables-v1')
        # Immutable JSON round trip is suitable for historical receipt binding.
        stored=json.loads(json.dumps(result)); second=bridge.handshake()
        self.assertEqual(stored,second)
        self.assertEqual(stored['capability_manifest_digest'],fingerprint({'schema_version':'1.0','capabilities':stored['discovered_capabilities']}))
