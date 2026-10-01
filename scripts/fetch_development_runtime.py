"""Acquire only the reviewed three-file runtime slice at the locked exact SHA.

Only an optional short-lived CI GitHub read token is used for these public paths.
No provider configuration is read. No tree
listing, archives, clone, tags, branches, evaluation or data endpoints.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.runtime_bridge.contract import load_config, validate_config, verify_artifact


def acquire(destination, get=None, github_read_token=None):
    config = load_config(); validate_config(config)
    prefix = 'https://api.github.com/repos/' + config['source_repository'] + '/'
    if get is None:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl): return None
        opener=urllib.request.build_opener(NoRedirect)
        def get(relative):
            headers={'User-Agent':'hcl-assistant-development-bridge','Accept':'application/vnd.github+json'}
            if github_read_token: headers['Authorization']='Bearer '+github_read_token
            request=urllib.request.Request(prefix+relative,headers=headers)
            with opener.open(request,timeout=20) as response: return json.load(response)
    commit = get('git/commits/' + config['source_commit_sha'])
    if commit['sha'] != config['source_commit_sha'] or commit['tree']['sha'] != config['source_tree_sha']:
        raise ValueError('UNSUPPORTED_VERSION')
    destination = Path(destination)
    if destination.is_symlink() or (destination / 'identity.json').is_symlink(): raise ValueError('Symlink artifact directory refused')
    for name in config['allowed_runtime_paths']:
        row = get('contents/' + name + '?ref=' + config['source_commit_sha'])
        if row.get('type') != 'file' or row.get('path') != name or row.get('encoding') != 'base64' or row.get('sha') != config['files'][name]['git_blob_sha']:
            raise ValueError('DIGEST_MISMATCH')
        data = base64.b64decode(row['content'], validate=False)
        import hashlib
        if hashlib.sha256(data).hexdigest() != config['files'][name]['sha256']: raise ValueError('DIGEST_MISMATCH')
        path = destination
        for part in Path(name).parts:
            path = path / part
            if path.is_symlink(): raise ValueError('Symlink artifact path refused')
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    (destination / 'identity.json').write_text(json.dumps({k: config[k] for k in ('source_repository', 'source_commit_sha', 'artifact_digest')}))
    verify_artifact(destination, config)
    return {'source_repository': config['source_repository'], 'source_commit_sha': config['source_commit_sha'], 'artifact_digest': config['artifact_digest'], 'runtime_blobs_read': 3, 'provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('destination'); args = parser.parse_args()
    print(json.dumps(acquire(args.destination,github_read_token=os.environ.get('HCLA_RUNTIME_READ_TOKEN')), indent=2))
