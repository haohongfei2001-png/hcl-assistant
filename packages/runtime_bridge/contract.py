"""Product-owned thin interface; native HCL modules remain external and immutable."""
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / 'contracts/runtime-bridge.lock.json'
REPOSITORY = 'haohongfei2001-png/human-cognition-layer'
PATHS = ('hcl/cognition/core.py', 'hcl/cognition/semantic.py', 'hcl/cognition/epistemic.py')
CAPABILITIES = ('belief_interpretation', 'information_access')


def fingerprint(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def load_config():
    return json.loads(LOCK.read_text())


def validate_config(config):
    pinned = load_config()
    if config.get('source_repository') != REPOSITORY or not re.fullmatch('[0-9a-f]{40}', config.get('source_commit_sha', '')):
        raise ValueError('UNSUPPORTED_VERSION')
    # A different exact SHA requires an explicit new reviewed lock/version.
    if config.get('source_commit_sha') != pinned['source_commit_sha'] or config.get('bridge_version') != pinned['bridge_version']:
        raise ValueError('UNSUPPORTED_VERSION')
    if config.get('allowed_runtime_paths') != list(PATHS) or set(config.get('files', {})) != set(PATHS):
        raise ValueError('DIGEST_MISMATCH')
    if config.get('artifact_digest') != fingerprint(config['files']) or config['files'] != pinned['files']:
        raise ValueError('DIGEST_MISMATCH')
    if (config.get('interface') != pinned['interface'] or config.get('interface_digest') != fingerprint(config['interface'])
            or config.get('interface_version') != pinned['interface_version']):
        raise ValueError('INTERFACE_MISMATCH')
    if (config.get('execution_policy') != pinned['execution_policy'] or config.get('input_policy') != pinned['input_policy']
            or config.get('receipt_version') != '1.0' or config.get('implementation_id') != pinned['implementation_id']
            or config.get('timeout_policy') != pinned['timeout_policy']):
        raise ValueError('CAPABILITY_MANIFEST_INVALID')
    if config.get('capability_manifest_digest')!=pinned.get('capability_manifest_digest'):raise ValueError('CAPABILITY_MANIFEST_INVALID')
    if set(config) != set(pinned) or config.get('source_tree_sha') != pinned['source_tree_sha']:
        raise ValueError('UNSUPPORTED_VERSION')


def verify_artifact(directory, config):
    validate_config(config)
    directory = Path(directory)
    if directory.is_symlink() or (directory / "identity.json").is_symlink(): raise ValueError("DIGEST_MISMATCH")
    # Only exact allowlisted filenames are opened; never traverse a research tree.
    for name, expected in config['files'].items():
        path = directory
        for part in Path(name).parts:
            path = path / part
            if path.is_symlink(): raise ValueError('DIGEST_MISMATCH')
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if hashlib.sha256(data).hexdigest() != expected['sha256'] or blob != expected['git_blob_sha']:
            raise ValueError('DIGEST_MISMATCH')
    identity = json.loads((directory / 'identity.json').read_text())
    if identity != {k: config[k] for k in ('source_repository', 'source_commit_sha', 'artifact_digest')}:
        raise ValueError('UNSUPPORTED_VERSION')


def manifest(config):
    validate_config(config)
    candidates = json.loads((ROOT / 'contracts/capabilities.json').read_text())
    rows = []
    for original in candidates['capabilities']:
        row = copy.deepcopy(original)
        if row['capability_id'] in CAPABILITIES:
            row.update(supported_input=['Unmodified source text with explicitly named English speech and modal expressions; ordinary question'],
                       language=[], evidence_status='DEVELOPMENT_INTEGRATION_ONLY',
                       runtime_implementation={k: config[k] for k in ('source_repository', 'source_commit_sha', 'artifact_digest', 'interface_version', 'implementation_id')},
                       product_activation_policy={'mode': 'EXPERIMENTAL', 'production_enabled': False})
            row['output_objects']=['PublicExpression']
            row['limitations'] += ['Bounded literal syntax only; no language generalization or private-state truth.',
                                   'Provider-free preparation only; no generated answer or production retention inference.',
                                   'Projection is a checked public expression, not a production belief/access record or general question answering.']
        rows.append(row)
    return {'schema_version': '1.0', 'capabilities': rows}


def handshake(directory, config=None):
    config = load_config() if config is None else copy.deepcopy(config)
    result = {k: config.get(k) for k in ('bridge_version', 'source_commit_sha', 'artifact_digest', 'interface_version', 'receipt_version')}
    result.update(runtime_identity={**{k: config.get(k) for k in ('source_repository', 'source_commit_sha', 'implementation_id')},
                                    'runtime_version':'git:'+str(config.get('source_commit_sha')),'native_runtime_version':None},
                  serialization_version='1.0', limits=config.get('timeout_policy'), errors=[],
                  capability_manifest_digest=None, discovered_capabilities=[], handshake_status='FAILED')
    try:
        verify_artifact(directory, config)
        discovered = manifest(config)
        if fingerprint(discovered)!=config.get('capability_manifest_digest'):raise ValueError('CAPABILITY_MANIFEST_INVALID')
        result.update(handshake_status='READY', capability_manifest_digest=fingerprint(discovered),
                      discovered_capabilities=discovered['capabilities'], interface_digest=config['interface_digest'],
                      production_enabled=False, evidence_class='DEVELOPMENT_INTEGRATION_ONLY')
    except (ValueError, OSError, KeyError, TypeError) as error:
        reason = str(error)
        result['handshake_status'] = reason if reason in {'UNSUPPORTED_VERSION', 'DIGEST_MISMATCH', 'INTERFACE_MISMATCH', 'CAPABILITY_MANIFEST_INVALID'} else 'FAILED'
        result['errors'] = [result['handshake_status']]
    return result
