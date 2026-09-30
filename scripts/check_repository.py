"""Offline repository-boundary and public-content checks, not runtime implementation.

Origin hashes prove migration preservation without fetching research assets.
Pattern checks are bounded, not a universal proof that no secret exists.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from check_planning import PlanningError, product_files, require, safe_path, validate_plan

CANONICAL = 'haohongfei2001-png/hcl-assistant'
FORBIDDEN_PARTS = {'hcl', 'eval', 'evaluation', 'confirmation', 'confirmation_gold',
                   'longmemeval', 'credentials', 'secrets', 'private_data', 'data', 'datasets'}
FORBIDDEN_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.sqlite3', '.db', '.zip',
                      '.csv', '.jsonl', '.parquet', '.pdf', '.docx'}
TOKEN_PATTERNS = (
    re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    re.compile(r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})\b'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    re.compile(r'''(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["'][A-Za-z0-9_+/=-]{20,}["']'''),
)


def git_hash(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def inspect_file(relative: str, data: bytes) -> None:
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'unsafe product path')
    parts = {p.casefold() for p in path.parts}
    require(not parts & FORBIDDEN_PARTS, 'forbidden data/research path: ' + relative)
    require(not any('longmemeval' in p or p.startswith('confirmation_') for p in parts),
            'forbidden data path: ' + relative)
    require(path.suffix.casefold() not in FORBIDDEN_SUFFIXES, 'non-planning payload: ' + relative)
    require(not path.name.startswith('.env') or path.name == '.env.example', 'environment file forbidden')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise PlanningError('binary payload forbidden: ' + relative) from exc
    require('\0' not in text, 'binary payload forbidden: ' + relative)
    for pattern in TOKEN_PATTERNS:
        require(pattern.search(text) is None, 'possible credential in: ' + relative)
    if path.suffix == '.py':
        tree = ast.parse(text)
        for node in ast.walk(tree):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else (
                [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            require(not any(m.split('.')[0] in {'hcl', 'eval'} for m in modules),
                    'research runtime import forbidden: ' + relative)


def original_document(relative: str, text: str) -> str:
    """Undo only the two declared metadata edits, never rewrite product semantics."""
    if relative == 'HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md':
        edits = (
            ('版本：Canonical 1.0 / 2026-09-30（物理迁移，产品定义与L0–L2不变）。唯一产品事实源：`haohongfei2001-png/hcl-assistant/main`。',
             '版本：Canonical 1.0 / 2026-09-30。'),
            ('L0 planning/setup已完成；物理迁移执行者在新仓库exact-main核验后停止，不开始L1。',
             '合并通过的 L0 planning/setup 后，本轮执行者停止。'),
        )
    elif relative == 'docs/L0_L2_WORK_PACKAGES.md':
        edits = (('停止于I06/真实接入gate；物理分仓已完成。', '停止于I06/分仓/真实接入gate。'),)
    else:
        return text
    for new, old in edits:
        require(text.count(new) == 1, 'declared metadata edit mismatch: ' + relative)
        text = text.replace(new, old, 1)
    return text


def check_repository(root: Path) -> dict:
    root = root.resolve()
    plan = json.loads(safe_path(root, 'control/plan.json').read_text())
    validate_plan(plan)
    require(os.environ.get('PRODUCT_REPOSITORY', CANONICAL) == CANONICAL, 'wrong execution repository')
    files = product_files(root)
    for path in files:
        inspect_file(path.relative_to(root).as_posix(), path.read_bytes())
    require(not (root / 'products').exists(), 'legacy nested product root forbidden')
    workflow = (root / '.github/workflows/hcl-assistant-planning.yml').read_text()
    require('products/hcl-assistant/' not in workflow and "('products', 'hcl-assistant')" not in workflow,
            'legacy workflow prefix')
    require('pull_request_target' not in workflow and 'secrets.' not in workflow, 'unsafe workflow context')
    require('contents: read' in workflow and 'contents: write' not in workflow, 'planning CI must be read-only')
    require(CANONICAL in workflow and 'human-cognition-layer' not in workflow, 'CI must only read product repository')
    for name in ('README.md', 'STATUS.md', 'DEVELOPMENT_PLAN.md', 'AGENTS.md', 'apps/README.md'):
        text = (root / name).read_text()
        require('NOT_CREATED' not in text and '分仓未完成' not in text and '仓库尚未创建' not in text,
                'obsolete split blocker: ' + name)
    status = (root / 'STATUS.md').read_text()
    require('physical split = COMPLETE' in status and 'repository isolation = COMPLETE at repository boundary' in status,
            'status boundary mismatch')
    ledger = json.loads((root / 'control/repository-migration.json').read_text())
    require(ledger['source_commit'] == '2e54a12cad4441f4a363f852b1c2864b9254c243', 'source pin changed')
    require(ledger['source_tree'] == 'c9e43ef2071100c5a51ecc56001bd7f74830fd12', 'source tree changed')
    require(ledger['destination_repository'] == CANONICAL and ledger['destination_root'] == '.', 'wrong migration destination')
    require(ledger['source_prefix'] == 'products/hcl-assistant/', 'source provenance mismatch')
    rows = ledger['files']
    require(len(rows) == 22, 'incomplete migration inventory')
    require(ledger['research_history_copied'] is False and ledger['research_data_copied'] is False
            and ledger['l1_implementation_started'] is False, 'migration scope exceeded')
    allowed = set(rows) | set(ledger['new_migration_files'])
    if plan['phase'] == 'L0_COMPLETE':
        require({p.relative_to(root).as_posix() for p in files} == allowed,
                'L0 tree differs from complete migration allowlist')
    checked_originals = []
    for relative, row in rows.items():
        path = safe_path(root, relative)
        require(path.is_file(), 'missing migrated file: ' + relative)
        require(re.fullmatch('[0-9a-f]{40}', row['source_blob_sha']) is not None, 'invalid origin hash')
        data = path.read_bytes()
        if plan['phase'] != 'L0_COMPLETE':
            continue  # Historical provenance must not freeze legitimate L1-L5 changes.
        kind = row['adjustment']
        if kind == 'BYTE_IDENTICAL':
            require(git_hash(data) == row['source_blob_sha'], 'original file changed: ' + relative)
            checked_originals.append(relative)
        elif kind == 'TERMINAL_NEWLINE_ONLY':
            require(row['source_blob_sha'] in {git_hash(data), git_hash(data.rstrip(b'\n') + b'\n')},
                    'contract changed beyond terminal newline: ' + relative)
            checked_originals.append(relative)
        elif kind in {'MIGRATION_HEADER_AND_STOP_ONLY', 'SATISFIED_SPLIT_GATE_ONLY'}:
            restored = original_document(relative, data.decode()).encode()
            require(row['source_blob_sha'] in {git_hash(restored), git_hash(restored.rstrip(b'\n') + b'\n')},
                    'product plan changed beyond relocation: ' + relative)
            checked_originals.append(relative)
        else:
            require(kind in {'ROOT_BOUNDARY', 'REPOSITORY_ROOT_CI'}, 'unknown migration adjustment')
    return {'check': 'REPOSITORY_BOUNDARY_AND_MIGRATION', 'repository': CANONICAL,
            'physical_split': 'COMPLETE', 'imported_origin_files': len(rows),
            'scanned_text_files': len(files), 'preserved_source_hashes': checked_originals,
            'provider_calls': 0, 'credential_scan': 'NO_MATCH_IN_SCANNED_FILES',
            'scan_limit': 'bounded path/import/credential checks; not universal secret detection or production privacy certification'}


if __name__ == '__main__':
    import sys
    try:
        print(json.dumps(check_repository(Path(__file__).resolve().parents[1]), indent=2))
    except (PlanningError, ValueError, KeyError, TypeError, OSError) as exc:
        print('REPOSITORY CHECK FAILED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
