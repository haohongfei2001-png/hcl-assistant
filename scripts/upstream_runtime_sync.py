"""Validate an exact upstream candidate in a disposable PRODUCT copy.

The stable checkout is never changed. Only main's SHA metadata and the existing
three exact-SHA runtime files are read. No token or research tree is required.
"""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.runtime_bridge.contract import PATHS, REPOSITORY, fingerprint
from scripts.check_planning import product_files

LOCK = 'contracts/runtime-bridge.lock.json'
CHECKS = ('manifest', 'acquisition', 'handshake', 'smoke', 'planning', 'repository',
          'python', 'npm_install', 'build', 'browser_install', 'browser')


def exact_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('Exact upstream SHA required')
    return value


def public_get(relative):
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + '/' + relative,
                                    headers={'User-Agent': 'hcl-assistant-upstream-sync', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def allowed_blobs(tree_sha, get):
    """Prove ordinary file modes BEFORE Contents API can dereference a symlink.

    Read only ancestor directory metadata (root -> hcl -> cognition), never a
    recursive tree, another subtree or a non-allowlisted blob.
    """
    for directory in ('hcl', 'cognition', None):
        tree = get('git/trees/' + tree_sha)
        if tree.get('sha') != tree_sha or tree.get('truncated'):
            raise ValueError('Incomplete/mismatched ancestor tree provenance')
        if directory is None:
            blobs = {}
            for path in PATHS:
                found = [r for r in tree['tree'] if r['path'] == Path(path).name]
                if len(found) != 1 or found[0]['type'] != 'blob' or found[0]['mode'] not in ('100644', '100755'):
                    raise ValueError('Missing/non-regular allowlisted runtime file: ' + path)
                blobs[path] = exact_sha(found[0]['sha'])
            return blobs
        found = [r for r in tree['tree'] if r['path'] == directory]
        if len(found) != 1 or found[0]['type'] != 'tree' or found[0]['mode'] != '040000':
            raise ValueError('Non-directory allowlisted ancestor: ' + directory)
        tree_sha = exact_sha(found[0]['sha'])


def build_candidate(stable, sha, get=public_get):
    exact_sha(sha)
    if stable['source_repository'] != REPOSITORY or stable['allowed_runtime_paths'] != list(PATHS):
        raise ValueError('Unexpected stable repository/allowlist')
    commit = get('git/commits/' + sha)
    if commit['sha'] != sha:
        raise ValueError('Upstream commit identity mismatch')
    candidate = copy.deepcopy(stable)
    candidate['source_commit_sha'] = sha
    candidate['source_tree_sha'] = exact_sha(commit['tree']['sha'])
    major, minor = stable['bridge_version'].split('.')
    candidate['bridge_version'] = f'{int(major)}.{int(minor) + 1}'
    expected_blobs = allowed_blobs(candidate['source_tree_sha'], get)
    files = {}
    for path in PATHS:
        row = get('contents/' + path + '?ref=' + sha)
        if row.get('type') != 'file' or row.get('path') != path or row.get('encoding') != 'base64':
            raise ValueError('Missing/invalid allowlisted file: ' + path)
        data = base64.b64decode(''.join(row['content'].split()), validate=True)
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != row.get('sha') or blob != expected_blobs[path]:
            raise ValueError('Git blob provenance mismatch: ' + path)
        files[path] = {'git_blob_sha': blob, 'sha256': hashlib.sha256(data).hexdigest()}
    candidate['files'] = files
    candidate['artifact_digest'] = fingerprint(files)
    # Interface, capability identities, limits and activation policy never expand.
    return candidate


def snapshot(root, replacement=None):
    rows = {}
    for path in product_files(root):
        relative = path.relative_to(root).as_posix()
        data = replacement if relative == LOCK and replacement is not None else path.read_bytes()
        rows[relative] = hashlib.sha256(data).hexdigest()
    return fingerprint(rows)


def product_identity(root):
    """Only a clean exact product commit can be used as a publication base."""
    try:
        sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                      stderr=subprocess.DEVNULL, text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'],
                                        stderr=subprocess.DEVNULL, text=True)
        return exact_sha(sha) if not dirty else None
    except (subprocess.SubprocessError, ValueError):
        return None


def command_runner(command, cwd, env, log, timeout=300):
    # Write-token environments never propagate into candidate code or npm.
    safe = {k: env[k] for k in ('PATH', 'HOME', 'TMPDIR', 'PLAYWRIGHT_BROWSERS_PATH') if k in env}
    safe.update(PYTHONDONTWRITEBYTECODE='1', HCL_DEVELOPMENT_ARTIFACT=env['HCL_DEVELOPMENT_ARTIFACT'], CI='true',
                npm_config_cache=str(Path(env['HCL_DEVELOPMENT_ARTIFACT']).parent / 'npm-cache'))
    with log.open('w') as stream:
        process = subprocess.Popen(command, cwd=cwd, env=safe, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
            if code:
                raise subprocess.CalledProcessError(code, command)
        finally:
            # npm/Playwright descendants must not keep servers/ports alive after
            # a failed/timed-out stage, or after a successful command exits.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()



def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def validate_handshake(ready, candidate):
    if ready.get('handshake_status') != 'READY':
        raise ValueError('Candidate handshake refused: ' + str(ready.get('handshake_status')))
    for field in ('source_commit_sha', 'bridge_version', 'artifact_digest', 'interface_version',
                  'interface_digest', 'capability_manifest_digest'):
        if ready.get(field) != candidate[field]:
            raise ValueError('Handshake provenance mismatch: ' + field)
    if ready.get('production_enabled') is not False or ready['runtime_identity']['source_repository'] != REPOSITORY:
        raise ValueError('Candidate activation/repository mismatch')
    rows = ready['discovered_capabilities']
    experimental = []
    for row in rows:
        policy = row['product_activation_policy']
        if policy['production_enabled'] is not False or row['i06_disposition'] != 'PENDING_I06':
            raise ValueError('Capability activation/disposition change')
        if policy['mode'] == 'EXPERIMENTAL':
            experimental.append(row['capability_id'])
    if sorted(experimental) != sorted(candidate['interface']['capabilities']):
        raise ValueError('Capability manifest change requires explicit adapter review')
    if fingerprint({'schema_version': '1.0', 'capabilities': rows}) != candidate['capability_manifest_digest']:
        raise ValueError('Capability manifest digest mismatch')
    return experimental


def sync(root, output, get=public_get, runner=command_runner):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Receipts must be outside the stable product checkout')
    output.mkdir(parents=True, exist_ok=True)
    # A previous successful output must never survive a failed rerun.
    (output / 'candidate.lock.json').unlink(missing_ok=True)
    stable_bytes = (root / LOCK).read_bytes()
    stable = json.loads(stable_bytes)
    report = {'schema_version': '1.0', 'status': 'FAILED', 'stable_verified_sha': stable['source_commit_sha'],
              'upstream_main_sha': None, 'candidate_sha': None, 'checks': {},
              'product_sha': product_identity(root), 'product_source_digest': snapshot(root),
              'provider_calls': 0, 'provider_spend': 0, 'production_enabled': False, 'efficacy': 'NOT_TESTED'}
    stage = 'upstream_identity'
    try:
        if os.environ.get('PRODUCT_SHA') and report['product_sha'] != os.environ['PRODUCT_SHA']:
            raise ValueError('Product checkout is dirty or differs from the exact validation SHA')
        sha = exact_sha(get('commits/main')['sha'])
        report['upstream_main_sha'] = sha
        if sha == stable['source_commit_sha']:
            report['status'] = 'UP_TO_DATE'
            return report
        report['candidate_sha'] = sha
        stage = 'candidate_provenance'
        candidate = build_candidate(stable, sha, get)
        with tempfile.TemporaryDirectory(prefix='hcla-candidate-') as temporary:
            work = Path(temporary) / 'product'; work.mkdir()
            artifact = Path(temporary) / 'runtime'
            for path in product_files(root):
                target = work / path.relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            write_json(work / LOCK, candidate)
            (work / '.tmp').mkdir()
            env = {**os.environ, 'HCL_DEVELOPMENT_ARTIFACT': str(artifact)}
            commands = {
                'manifest': [sys.executable, '-c', 'import json; from packages.runtime_bridge.contract import load_config,manifest; print(json.dumps(manifest(load_config())))'],
                'acquisition': [sys.executable, 'scripts/fetch_development_runtime.py', str(artifact)],
                'handshake': [sys.executable, '-c', 'import json,os; from packages.runtime_bridge.bridge import RuntimeBridge; print(json.dumps(RuntimeBridge(os.environ["HCL_DEVELOPMENT_ARTIFACT"]).handshake()))'],
                'smoke': [sys.executable, 'scripts/smoke_development_bridge.py', str(artifact)],
                'planning': [sys.executable, 'scripts/check_planning.py'],
                'repository': [sys.executable, 'scripts/check_repository.py'],
                'python': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                'npm_install': ['npm', 'ci', '--ignore-scripts'],
                'build': ['npm', 'run', 'build'],
                'browser_install': ['npx', '--no-install', 'playwright', 'install', '--with-deps', 'chromium', '--only-shell'],
                'browser': ['npm', 'run', 'test:browser'],
            }
            for stage in CHECKS:
                log = output / (stage + '.log')
                runner(commands[stage], work, env, log)
                if stage == 'manifest':
                    discovery = json.loads(log.read_text())
                    candidate['capability_manifest_digest'] = fingerprint(discovery)
                    write_json(work / LOCK, candidate)
                if stage == 'handshake':
                    ready = json.loads(log.read_text())
                    report['experimental_capabilities'] = validate_handshake(ready, candidate)
                    report['interface_identity'] = ready['interface_version']
                    report['capability_manifest_digest'] = ready['capability_manifest_digest']
                if stage == 'smoke':
                    smoke = json.loads(log.read_text())
                    if smoke['smoke'] != 'PASS' or smoke['pin']['source_commit_sha'] != sha or smoke['production_enabled'] is not False:
                        raise ValueError('Runtime smoke mismatch')
                    if any(row['receipt']['usage']['provider_calls'] != 0 for row in smoke['runs']):
                        raise ValueError('Provider budget violated')
                report['checks'][stage] = 'PASS'
            report['candidate_product_digest'] = snapshot(work)
            write_json(output / 'candidate.lock.json', candidate)
            report['candidate_lock_digest'] = hashlib.sha256((output / 'candidate.lock.json').read_bytes()).hexdigest()
            report['status'] = 'VERIFIED_CANDIDATE'
    except Exception as error:
        report['failed_stage'] = stage
        report['checks'][stage] = 'FAIL'
        report['error'] = type(error).__name__ + ': ' + str(error)[:500]
    finally:
        if (root / LOCK).read_bytes() != stable_bytes or snapshot(root) != report['product_source_digest']:
            report['status'] = 'FAILED'; report['error'] = 'Stable product checkout changed during validation'
            (output / 'candidate.lock.json').unlink(missing_ok=True)
        if report['status'] != 'VERIFIED_CANDIDATE':
            (output / 'candidate.lock.json').unlink(missing_ok=True)
        write_json(output / 'receipt.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output'); args = parser.parse_args()
    result = sync(Path(__file__).resolve().parents[1], args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result['status'] == 'FAILED' else 0)
