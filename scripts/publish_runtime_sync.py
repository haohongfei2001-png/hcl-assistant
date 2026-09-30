"""Publish validated lock-only product PRs; never merge or change protection.

Run only in the workflow's separate trusted publisher job. The repository-scoped
GITHUB_TOKEN is used for product writes; upstream acquisition is unauthenticated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.upstream_runtime_sync import CHECKS, LOCK, exact_sha, fingerprint, product_identity, snapshot

PRODUCT = 'haohongfei2001-png/hcl-assistant'
MARKER = '<!-- hcla-verified-runtime-sync-v1 -->'


def github(method, endpoint, data=None):
    request = urllib.request.Request('https://api.github.com/repos/' + PRODUCT + '/' + endpoint,
        method=method, data=None if data is None else json.dumps(data).encode(), headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/json', 'User-Agent': 'hcla-runtime-sync-publisher'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response) if response.status != 204 else None
    except urllib.error.HTTPError as error:
        if error.code == 404 and method == 'GET': return None
        raise


def validate_evidence(root, output):
    report = json.loads((output / 'receipt.json').read_text())
    if report['status'] != 'VERIFIED_CANDIDATE' or report['checks'] != {k: 'PASS' for k in CHECKS}:
        raise ValueError('Full candidate validation is required before publication')
    exact_sha(report['product_sha']); exact_sha(report['candidate_sha'])
    if product_identity(root) != report['product_sha']:
        raise ValueError('Publication requires the clean exact tested product commit')
    stable = json.loads((root / LOCK).read_text())
    data = (output / 'candidate.lock.json').read_bytes(); candidate = json.loads(data)
    if report['stable_verified_sha'] != stable['source_commit_sha'] or report['candidate_sha'] == report['stable_verified_sha']:
        raise ValueError('Stable/candidate identity mismatch')
    if snapshot(root) != report['product_source_digest'] or snapshot(root, data) != report['candidate_product_digest']:
        raise ValueError('Product source changed since candidate validation')
    if hashlib.sha256(data).hexdigest() != report['candidate_lock_digest']:
        raise ValueError('Candidate lock digest changed')
    if candidate['source_commit_sha'] != report['candidate_sha'] or candidate['source_commit_sha'] != report['upstream_main_sha']:
        raise ValueError('Candidate SHA changed')
    mutable = {'source_commit_sha', 'source_tree_sha', 'bridge_version', 'files', 'artifact_digest', 'capability_manifest_digest'}
    if set(candidate) != set(stable) or any(candidate[k] != stable[k] for k in stable if k not in mutable):
        raise ValueError('Interface/allowlist/policy changes require separate review')
    if candidate['artifact_digest'] != fingerprint(candidate['files']) or set(candidate['files']) != set(stable['files']):
        raise ValueError('Artifact provenance mismatch')
    if (report['provider_calls'], report['provider_spend'], report['production_enabled'], report['efficacy']) != (0, 0, False, 'NOT_TESTED'):
        raise ValueError('Experimental boundary violation')
    return report, data


def pr_body(report):
    return MARKER + '\n\n' + f'''Repin the development-only runtime after full candidate compatibility validation.

- Previous stable SHA: `{report['stable_verified_sha']}`
- Candidate SHA: `{report['candidate_sha']}`
- Product validation base: `{report['product_sha']}`
- Interface: `{report['interface_identity']}`
- Experimental capabilities: {', '.join(report['experimental_capabilities'])}
- Capability manifest digest: `{report['capability_manifest_digest']}`
- Provider calls/spend: **0 / 0**

All required checks passed: {', '.join(CHECKS)}. Acquisition verified the exact repository/commit/tree and three allowlisted Git blobs/SHA256 digests. Original synthetic real-runtime smoke includes EXECUTED, NO_TREATMENT and UNSUPPORTED. Full Python regressions, TypeScript/Vite build and headless browser journeys passed. Logs and receipts: {os.environ.get('SYNC_RUN_URL', 'workflow artifact')}.

The upstream branch is metadata only. This candidate is not the normal execution pin until the PR is merged and exact-main CI passes. No efficacy claim, production activation, confirmation/private/evaluation data or provider authorization. The L3/I06 gates remain unchanged. Missing protection/auto-merge permission leaves this PR for review; protections are never changed.
'''


def publish(root, output, api=github, enable_auto=None):
    report, data = validate_evidence(root, output)
    base = report['product_sha']
    main = api('GET', 'git/ref/heads/main')
    if main['object']['sha'] != base:
        return {'status': 'DEFERRED_MAIN_CHANGED', 'stable_verified_sha': report['stable_verified_sha']}
    # One workflow writer, deterministic immutable branch per product base/candidate.
    branch = 'product/runtime-sync-' + report['candidate_sha'][:12] + '-' + base[:12]
    pulls = api('GET', 'pulls?state=open&base=main&per_page=100')
    if len(pulls) >= 100 or any(p['head']['ref'] != branch and MARKER not in (p.get('body') or '') for p in pulls):
        return {'status': 'DEFERRED_ACTIVE_PRODUCT_WRITER'}
    commit = api('GET', 'git/commits/' + base)
    blob = api('POST', 'git/blobs', {'content': data.decode(), 'encoding': 'utf-8'})
    tree = api('POST', 'git/trees', {'base_tree': commit['tree']['sha'],
        'tree': [{'path': LOCK, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
    existing = api('GET', 'git/ref/heads/' + branch)
    if existing:
        head = existing['object']['sha']
        previous = api('GET', 'git/commits/' + head)
        if previous['tree']['sha'] != tree['sha'] or [p['sha'] for p in previous['parents']] != [base]:
            return {'status': 'DEFERRED_BRANCH_OWNERSHIP'}
    else:
        new = api('POST', 'git/commits', {'message': 'Repin experimental runtime to ' + report['candidate_sha'],
              'tree': tree['sha'], 'parents': [base]})
        head = new['sha']
        # Never force-update or reset a concurrent branch.
        api('POST', 'git/refs', {'ref': 'refs/heads/' + branch, 'sha': head})
    if api('GET', 'git/ref/heads/main')['object']['sha'] != base:
        return {'status': 'DEFERRED_MAIN_CHANGED'}
    matching = [p for p in pulls if p['head']['ref'] == branch]
    body = pr_body(report)
    if matching:
        pr = api('PATCH', 'pulls/' + str(matching[0]['number']), {'body': body})
    else:
        pr = api('POST', 'pulls', {'title': 'Repin experimental HCL runtime to ' + report['candidate_sha'][:12],
                                  'head': branch, 'base': 'main', 'body': body})
    # Built-in-token PR events may require approval. Dispatch read-only exact-head
    # CI explicitly, without a cross-repository PAT or bypassing required checks.
    api('POST', 'actions/workflows/hcl-assistant-planning.yml/dispatches', {'ref': branch})
    result = {'status': 'PR_READY', 'url': pr['html_url'], 'head_sha': head, 'branch': branch,
              'stable_verified_sha': report['stable_verified_sha'], 'candidate_sha': report['candidate_sha'],
              'auto_merge': 'NOT_ENABLED_SETTINGS_OR_PROTECTION'}
    settings = api('GET', '')
    protection = api('GET', 'branches/main/protection')
    checks = (protection or {}).get('required_status_checks') or {}
    contexts = set(checks.get('contexts', [])) | {c['context'] for c in checks.get('checks', [])}
    if settings.get('allow_auto_merge') and settings.get('allow_squash_merge') and checks.get('strict') and 'planning' in contexts:
        try:
            if enable_auto is None:
                def enable_auto(node):
                    subprocess.run(['gh', 'api', 'graphql', '-f',
                        'query=mutation($id:ID!){enablePullRequestAutoMerge(input:{pullRequestId:$id,mergeMethod:SQUASH}){pullRequest{id}}}',
                        '-f', 'id=' + node], check=True, timeout=30, stdout=subprocess.DEVNULL)
            enable_auto(pr['node_id'])
            result['auto_merge'] = 'ENABLED_REQUIRED_CI_AND_STRICT_BASE'
        except (subprocess.SubprocessError, OSError):
            result['auto_merge'] = 'UNAVAILABLE_REVIEW_REQUIRED'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('output'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]; output = Path(args.output)
    result = publish(root, output)
    (output / 'publication.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
