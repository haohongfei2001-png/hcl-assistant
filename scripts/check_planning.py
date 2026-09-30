"""Provider-free L0 control-plane checks; never import or inspect research assets.

This validates planning structure and declared boundaries, not cognition efficacy.
Run from the independent product repository root. No network calls are made.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class PlanningError(ValueError):
    """An adopted planning invariant or reference is invalid."""


REQUIRED_DOCS = (
    'README.md', 'STATUS.md', 'DEVELOPMENT_PLAN.md', 'AGENTS.md',
    'HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md',
    'contracts/PRODUCT_CONTRACTS_V1.md', 'contracts/catalog.json',
    'contracts/capabilities.json', 'contracts/capability-manifest.schema.json',
    'control/plan.json', 'docs/L0_L2_WORK_PACKAGES.md',
    'docs/ACCEPTANCE_MATRIX.md', 'docs/UX_SPEC.md',
    'docs/DOCUMENT_AUTHORITY.md', 'docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md', 'docs/VISUAL_SYSTEM.md',
    'docs/BOUNDARY_AND_ISOLATION.md', 'docs/RESEARCH_BASELINE.md',
    'control/repository-migration.json', 'docs/REPOSITORY_MIGRATION.md',
    'scripts/check_repository.py', 'tests/test_repository_split.py',
    '.github/workflows/hcl-assistant-planning.yml',
)
CONTRACT_IDS = {'interaction_controller', 'context', 'revision',
                'answer_synthesis', 'explain_projection', 'capability_manifest',
                'run_receipt', 'runtime_bridge'}
CONTEXT_KINDS = {'USER_REPORTED_EVENT', 'USER_GUESS', 'CHARACTER_SELF_REPORT',
                 'THIRD_PARTY_REPORT', 'SYSTEM_INTERPRETATION', 'HYPOTHETICAL',
                 'CONDITIONAL_RULE', 'CORRECTION', 'RETRACTION'}
REVISION_ACTIONS = {'ADD', 'CORRECT', 'RETRACT', 'SUPERSEDE',
                    'HYPOTHETICAL_BRANCH', 'STOP_USING', 'DELETE'}
PERMISSIONS = {'ACCOUNT_DATA_ACCESS', 'PERSON_PERSPECTIVE_ACCESS',
               'PERSISTENCE_REUSE_PERMISSION'}
IGNORED_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', 'dist', 'pages-dist', 'coverage', 'test-results', 'playwright-report', '.tmp', '.local'}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanningError(message)


def safe_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), 'nonempty relative path required')
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'outside product path')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'symlinks are not allowed in product export')
    require(current.resolve().is_relative_to(root.resolve()), 'outside product root')
    return current


def load_json(root: Path, relative: str) -> Any:
    return json.loads(safe_path(root, relative).read_text(encoding='utf-8'))


def validate_plan(plan: dict[str, Any]) -> None:
    require(plan.get('schema_version') == '1.0', 'plan version')
    require(plan.get('research_sequence') == ['I02', 'I03', 'I04', 'I05', 'I06'], 'research sequence changed')
    inv = plan.get('invariants', {})
    for key in ('assistant_first', 'controller_required_for_production_answer'):
        require(inv.get(key) is True, f'required invariant: {key}')
    for key in ('frontend_hcl_toggle', 'production_base_bypass',
                'lab_compare_enabled_in_l2', 'hidden_chain_of_thought_storage',
                'historical_model_output_is_independent_evidence',
                'mock_may_be_relabelled_real', 'confirmation_material_allowed'):
        require(inv.get(key) is False, f'forbidden invariant: {key}')
    require(type(inv.get('max_provider_calls_l0_l2')) is int and inv['max_provider_calls_l0_l2'] == 0,
            'L0-L2 provider calls must be zero')
    for key in ('l2_5_production_activation_allowed', 'l2_5_confirmation_material_allowed',
                'l2_5_real_private_data_allowed', 'l2_5_case_specific_eval_tuning_allowed',
                'l2_5_efficacy_claims_allowed'):
        require(inv.get(key) is False, f'L2.5 forbidden invariant: {key}')
    require(inv.get('l2_5_provider_backed_execution_requires_explicit_authorization') is True,
            'L2.5 provider-backed execution must require separate authorization')
    boundary = plan.get('boundary', {})
    require(boundary.get('research_import_allowed') is False, 'research import forbidden')
    if boundary.get('physical_repository_split') is not True:
        require(boundary.get('real_data_allowed') is False and boundary.get('public_deployment_allowed') is False,
                'unsplit boundary cannot allow real data or public deployment')
    require(boundary.get('hosting_repository') == 'haohongfei2001-png/hcl-assistant', 'wrong canonical product repository')
    require(boundary.get('path') == '.', 'product must use repository root')
    require(boundary.get('physical_repository_split') is True, 'physical split must remain complete')
    require(boundary.get('mode') == 'INDEPENDENT_PRODUCT_REPOSITORY', 'wrong repository mode')
    require(boundary.get('repository_isolation') == 'COMPLETE_AT_REPOSITORY_BOUNDARY', 'repository isolation status')
    require(boundary.get('canonical_product_source') == 'haohongfei2001-png/hcl-assistant/main', 'stale or dual canonical source')
    require(boundary.get('development_runtime_bridge_allowed') is True, 'L2.5 bridge authorization missing')
    require(boundary.get('development_runtime_source_repository') == 'haohongfei2001-png/human-cognition-layer',
            'wrong development runtime source')
    require(boundary.get('development_runtime_pin_policy') == 'EXACT_COMMIT_SHA_AND_INTERFACE_DIGEST',
            'floating runtime pin forbidden')
    require(boundary.get('development_runtime_input_policy') == 'SYNTHETIC_NON_CONFIRMATION_ONLY',
            'L2.5 input policy must remain synthetic/non-confirmation')
    if plan.get('phase', '').startswith(('L0', 'L1', 'L2')):
        require(boundary.get('real_data_allowed') is False and boundary.get('public_deployment_allowed') is False,
                'migration does not authorize real data or deployment')
    packages = plan.get('packages', [])
    require(len(packages) == 11, 'eleven coherent L0-L2.5 packages required')
    seen: set[str] = set()
    for row in packages:
        key = row.get('id')
        require(isinstance(key, str) and key not in seen, 'duplicate or invalid package id')
        require(re.fullmatch(r'L(?:0|1|2|2\.5)-\d{2}', key) is not None, 'invalid package id')
        require(row.get('stage') == key.rsplit('-', 1)[0], 'package stage mismatch')
        require(set(row.get('depends_on', [])) <= seen, 'unknown or forward/cyclic dependency')
        require(bool(row.get('delta')), 'product delta required')
        seen.add(key)
    expected_ids=['L0-01','L1-01','L1-02','L1-03','L1-04','L2-01','L2-02','L2-03','L2-04','L2.5-01','L2.5-02']
    require([r['id'] for r in packages]==expected_ids, 'canonical package boundaries changed')
    for index,row in enumerate(packages):
        require(row['depends_on']==([] if index==0 else [expected_ids[index-1]]), 'canonical dependencies changed')
        require(row['state'] in {'COMPLETE','NEXT_READY','WAITING_DEPENDENCY'}, 'unknown package state')
        if row['state']=='COMPLETE':
            require(all(d['state']=='COMPLETE' for d in packages[:index]), 'completed package has unsatisfied dependencies')
    next_id = plan.get('next_package_id')
    pending=[r for r in packages if r['state']!='COMPLETE']
    if pending:
        require(next_id in seen, 'unknown next package')
        require(plan.get('next_ready', '').startswith(next_id + '_'), 'NEXT_READY id mismatch')
        require(pending[0]['id']==next_id and pending[0]['state']=='NEXT_READY', 'unique dependency-safe NEXT_READY required')
        require(all(r['state']=='WAITING_DEPENDENCY' for r in pending[1:]), 'multiple ready packages')
    else:
        require(next_id is None and plan.get('next_ready')=='STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED' and plan.get('phase')=='L2_5_COMPLETE', 'completed L2.5 must stop at production activation gate')
    require(plan.get('adoption_gate') == 'MERGED_MAIN_AND_EXACT_SHA_PLANNING_PASS', 'adoption gate required')
    require('PHYSICAL_PRODUCT_REPOSITORY_SPLIT' in plan.get('satisfied_gates', []), 'split completion missing')
    require('PHYSICAL_PRODUCT_REPOSITORY_SPLIT' not in plan.get('l3_gates', []), 'obsolete outstanding split blocker')
    require('I06_DISPOSITION' in plan.get('l3_gates', []), 'I06 gate missing')
    require(plan.get('next_package_id') == 'L2.5-01' or plan.get('phase') in {'L2_5_IMPLEMENTING','L2_5_COMPLETE'},
            'post-L2 plan must enter L2.5 before L3')
    validate_current_queue(plan)


CURRENT_PACKAGES = (
    ('P0-01', 'P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR', list(range(1, 8))),
    ('P1-01', 'P1-01_ASSISTANT_FIRST_SHARED_SHELL', list(range(8, 13))),
    ('P1-02', 'P1-02_REVISION_EVIDENCE_MEMORY_LOOP', list(range(13, 17))),
    ('P1-03', 'P1-03_INTEGRATED_SYNTHETIC_ACCEPTANCE', list(range(17, 21))),
)
L3_STOP = 'STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED'


def validate_current_queue(plan: dict[str, Any]) -> dict[str, Any]:
    """The only scheduling projection; legacy validation remains independent."""
    authority = plan.get('field_authority', {})
    require(authority.get('current_product_queue') == 'product_development', 'current queue authority')
    require(authority.get('legacy_next_ready_is_global_product_queue') is False, 'legacy queue cannot schedule products')
    require(authority.get('automation_support') == 'CURRENT_PRODUCT_QUEUE_AND_LEGACY_SAFETY_CHECKED', 'current queue consumer migration required')
    require(authority.get('queue_consumer_migration_required_before_new_automated_scheduling') is False, 'unmigrated queue consumer')
    q = plan.get('product_development', {})
    require(q.get('schema_version') == '1.0' and q.get('authority') == 'SOLE_CURRENT_PRODUCT_DEVELOPMENT_QUEUE', 'current queue version/authority')
    require(q.get('canonical_document') == 'DEVELOPMENT_PLAN.md' and q.get('product_plan_version') == '1.2/A2-Product', 'current queue canonical plan')
    require(q.get('automatic_queue_consumers') == 'CURRENT_PRODUCT_QUEUE_VALIDATED', 'current consumer contract')
    require(q.get('execution_scope') == 'SYNTHETIC_PROVIDER_FREE_PRODUCT_REFINEMENT_ONLY', 'refinement execution boundary')
    require(type(q.get('max_provider_calls')) is int and q['max_provider_calls'] == 0, 'refinement provider budget must be zero')
    for key in ('real_private_data_allowed', 'production_activation_allowed', 'judge_implementation_authorized', 'agent_execution_authorized'):
        require(q.get(key) is False, f'forbidden refinement authority: {key}')
    require(q.get('judge_status') == 'LONG_TERM_GOAL_ONLY_NOT_IMPLEMENTED_NOT_VALIDATED_NOT_PRODUCTION_ENABLED', 'Judge is not implemented')
    require(q.get('after_all_complete_if_l3_gates_unmet') == L3_STOP, 'refinement completion cannot open L3')
    require(set(plan.get('l3_gates', [])) == {'I06_DISPOSITION', 'PINNED_PERMITTED_RUNTIME_ARTIFACT', 'PRODUCT_ADAPTER_SCOPE_VALIDATION', 'EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION'}, 'all four L3 gates required')
    rows = q.get('packages', [])
    require([r.get('id') for r in rows] == [r[0] for r in CURRENT_PACKAGES], 'canonical refinement package boundaries')
    pending = []
    for index, (row, expected) in enumerate(zip(rows, CURRENT_PACKAGES)):
        require(row.get('task') == expected[1], 'refinement task identity')
        require(row.get('depends_on') == ([] if index == 0 else [CURRENT_PACKAGES[index - 1][0]]), 'unknown/changed refinement dependency')
        require(row.get('acceptance') == [f'R{i:02d}' for i in expected[2]], 'refinement acceptance obligations changed')
        require(row.get('state') in {'COMPLETE', 'NEXT_READY', 'WAITING_DEPENDENCY'}, 'unknown refinement state')
        require(bool(row.get('delta')), 'refinement delta required')
        if row['state'] == 'COMPLETE':
            require(not pending, 'completed refinement has unsatisfied dependency')
            require(row.get('evidence') not in (None, '', 'NOT_IMPLEMENTED'), 'completion evidence required')
        else:
            pending.append(row)
    if pending:
        require(pending[0]['state'] == 'NEXT_READY' and all(r['state'] == 'WAITING_DEPENDENCY' for r in pending[1:]), 'unique dependency-safe current NEXT_READY required')
        require(q.get('next_package_id') == pending[0]['id'] and q.get('next_ready') == pending[0]['task'], 'current NEXT_READY mismatch')
        require(q.get('phase') in {'ASSISTANT_FIRST_REFINEMENT_READY', 'ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING'}, 'current phase mismatch')
    else:
        require(q.get('next_package_id') is None and q.get('next_ready') == L3_STOP and q.get('phase') == 'ASSISTANT_FIRST_REFINEMENT_COMPLETE', 'completed refinement must stop at L3 gate')
    return q


def queue_summary(q):
    current = next((r for r in q['packages'] if r['id'] == q['next_package_id']), None)
    detail = (current['delta'] + '。验收：' + '、'.join(current['acceptance'])) if current else '四包已完成；L3四门槛未满足，停止交接，不启动provider、Judge或Act。'
    return ('<!-- CURRENT_PRODUCT_QUEUE_START -->\n'
            '**NEXT_READY: ' + q['next_ready'] + '**\n\n'
            '当前产品阶段：' + q['phase'] + '。唯一当前任务：' + (q['next_package_id'] or '无，等待L3门槛') + '。\n\n'
            + detail + '\n\n'
            '任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。\n'
            '<!-- CURRENT_PRODUCT_QUEUE_END -->')



def validate_queue_mirrors(root: Path, q: dict[str, Any]) -> None:
    for name in ('STATUS.md', 'DEVELOPMENT_PLAN.md', 'AGENTS.md', 'README.md'):
        text = safe_path(root, name).read_text(encoding='utf-8')
        summaries = re.findall(r'<!-- CURRENT_PRODUCT_QUEUE_START -->.*?<!-- CURRENT_PRODUCT_QUEUE_END -->', text, flags=re.S)
        require(summaries == [queue_summary(q)], f'{name} current queue summary mismatch')
        markers = re.findall(r'\*\*NEXT_READY: ([A-Z0-9_.-]+)\*\*', text)
        require(markers == [q['next_ready']], f'{name} current NEXT_READY mirror mismatch')
    text = safe_path(root, 'DEVELOPMENT_PLAN.md').read_text(encoding='utf-8')
    for row in q['packages']:
        lines = [line for line in text.splitlines() if line.startswith('| ' + row['id'] + ' |')]
        require(len(lines) == 1 and lines[0].endswith('| ' + row['state'] + ' |'), 'development state mirror mismatch: ' + row['id'])


def validate_catalog(catalog: dict[str, Any]) -> None:
    rows = catalog.get('contracts', [])
    require(len(rows) == len(CONTRACT_IDS) and {r.get('id') for r in rows} == CONTRACT_IDS,
            'missing or duplicate stable contract')
    for row in rows:
        require(row.get('version') == '1.0', 'contract version mismatch')
        require(bool(row.get('required') or row.get('required_input')), 'empty contract fields')
    enums = catalog.get('enums', {})
    require(set(enums.get('context_kinds', [])) == CONTEXT_KINDS, 'context distinctions missing')
    require(set(enums.get('revision_actions', [])) == REVISION_ACTIONS, 'revision distinctions missing')
    require(set(catalog.get('permission_dimensions', [])) == PERMISSIONS, 'three separate permissions required')
    require(catalog.get('research_package_ids_are_product_keys') is False, 'package-based UI keys forbidden')
    require(catalog.get('explain_new_model_calls_default') == 0, 'Explain must not manufacture reasons')
    require(catalog.get('uncalibrated_probability_claims_allowed') is False, 'uncalibrated probabilities forbidden')
    require(catalog.get('semantics_verified_by_schema') is False, 'schema is not semantic proof')
    bridge = next(r for r in rows if r['id'] == 'runtime_bridge')
    require({'source_repository','source_commit_sha','artifact_digest','interface_version','implementation_id'} <= set(bridge['required']),
            'runtime bridge pin contract incomplete')
    require(catalog.get('experimental_activation_is_production') is False, 'experimental activation cannot be production')
    require(catalog.get('experimental_runtime_efficacy_claim_allowed') is False, 'experimental runtime cannot claim efficacy')
    controller = next(r for r in rows if r['id'] == 'interaction_controller')
    require({'event', 'scope', 'expected_state_version', 'allowed_memory_scope', 'source_refs',
             'model_resource_policy', 'idempotency_key'} <= set(controller['required_input']),
            'controller input incomplete')
    require({'accepted_change_ids', 'invalidated_state_ids', 'selected_context', 'route',
             'explain_projection', 'run_receipt', 'unresolved_updates'} <= set(controller['required_output']),
            'controller output incomplete')


def validate_capabilities(manifest: dict[str, Any], schema: dict[str, Any], catalog: dict[str, Any]) -> None:
    # A targeted dependency-free contract checker; the JSON Schema is published
    # separately for interoperable validation. This is not a generic schema engine.
    require(manifest.get('schema_version') == '1.0', 'manifest version')
    require(schema.get('$schema') == 'https://json-schema.org/draft/2020-12/schema', 'schema dialect')
    definition = schema.get('$defs', {}).get('capability', {})
    required = set(definition.get('required', []))
    expected = next(r['required'] for r in catalog['contracts'] if r['id'] == 'capability_manifest')
    require(set(expected) <= required, 'manifest schema omits required fields')
    dispositions = set(catalog['enums']['dispositions'])
    seen: set[str] = set()
    rows = manifest.get('capabilities', [])
    require(isinstance(rows, list) and bool(rows), 'capability candidates required')
    for row in rows:
        require(required <= set(row), 'missing capability field')
        key = row['capability_id']
        require(isinstance(key, str) and re.fullmatch(r'[a-z][a-z0-9_]+', key) is not None,
                'stable product capability id required')
        require(key not in seen, 'duplicate capability id')
        seen.add(key)
        require(row['contract_version'] == '1.0', 'capability version')
        for field in ('supported_input', 'language', 'planned_languages', 'output_objects', 'limitations'):
            values = row[field]
            require(isinstance(values, list) and all(isinstance(x, str) and x for x in values),
                    f'invalid capability {field}')
            require(len(values) == len(set(values)), f'duplicate {field}')
        require(bool(row['limitations']), 'limitations required')
        require(row['i06_disposition'] in dispositions, 'unknown disposition')
        policy = row['product_activation_policy']
        require(type(policy.get('production_enabled')) is bool, 'boolean production policy required')
        require(policy.get('mode') in {'MOCK_ONLY', 'DISABLED', 'EXPERIMENTAL', 'SCOPE_DEFAULT'}, 'activation mode')
        if row['i06_disposition'] == 'PENDING_I06':
            require(policy['production_enabled'] is False
                    and policy['mode'] in {'MOCK_ONLY', 'DISABLED', 'EXPERIMENTAL'},
                    'pending I06 cannot be production active')
            if policy['mode'] == 'EXPERIMENTAL':
                runtime = row['runtime_implementation']
                require(isinstance(runtime, dict), 'experimental capability requires pinned runtime')
                require(runtime.get('source_repository') == 'haohongfei2001-png/human-cognition-layer',
                        'experimental runtime repository must be HCL research repository')
                require(re.fullmatch(r'[0-9a-f]{40}', runtime.get('source_commit_sha', '')) is not None,
                        'experimental runtime requires exact commit SHA')
                require(all(isinstance(runtime.get(k), str) and runtime.get(k)
                            for k in ('artifact_digest','interface_version','implementation_id')),
                        'experimental runtime identity incomplete')
            else:
                require(row['runtime_implementation'] is None, 'non-experimental pending capability cannot bind runtime')
        if row['i06_disposition'] == 'DISABLE':
            require(policy['mode'] == 'DISABLED' and not policy['production_enabled'], 'disabled capability is active')
        if policy['production_enabled']:
            require(isinstance(row['runtime_implementation'], dict) and bool(row['language'])
                    and policy['mode'] == 'SCOPE_DEFAULT', 'production implementation/language gate missing')
        if row['evidence_status'] == 'DESIGN_ONLY':
            require(not policy['production_enabled'] and row['runtime_implementation'] is None
                    and row['language'] == [], 'design-only cannot claim live coverage')


def product_files(root: Path) -> list[Path]:
    import os
    found = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            child = Path(directory) / name
            require(not child.is_symlink(), 'symlink directory forbidden')
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in files:
            path = Path(directory) / name
            require(not path.is_symlink(), 'symlink file forbidden')
            if path.suffix == '.pyc':
                continue
            found.append(path)
    return sorted(found)


def validate_tree(root: Path) -> dict[str, Any]:
    root = root.resolve()
    for relative in REQUIRED_DOCS:
        require(safe_path(root, relative).is_file(), f'missing product file: {relative}')
    files = product_files(root)
    plan = load_json(root, 'control/plan.json')
    catalog = load_json(root, 'contracts/catalog.json')
    validate_plan(plan)
    validate_catalog(catalog)
    validate_capabilities(load_json(root, 'contracts/capabilities.json'),
                          load_json(root, 'contracts/capability-manifest.schema.json'), catalog)
    validate_queue_mirrors(root, plan['product_development'])
    package_text = safe_path(root, 'docs/L0_L2_WORK_PACKAGES.md').read_text(encoding='utf-8')
    for row in plan['packages']:
        require(f"## {row['id']} " in package_text, f"missing package detail: {row['id']}")
    fingerprints = {}
    for path in files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        fingerprints[relative] = hashlib.sha256(data).hexdigest()
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                if link.startswith(('https://', 'http://', '#', 'mailto:')):
                    continue
                target = link.split('#')[0]
                if not target:
                    continue
                combined = (path.parent / target).resolve()
                require(combined.is_relative_to(root), f'out-of-bound local doc link: {relative}')
                require(combined.exists(), f'broken doc link: {relative}: {target}')
    digest = hashlib.sha256(json.dumps(fingerprints, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'check': 'PRODUCT_CONTROL_CONTRACTS_ONLY', 'package_count': len(plan['packages']),
            'capability_candidates': len(load_json(root, 'contracts/capabilities.json')['capabilities']),
            'next_ready': plan['product_development']['next_ready'],
            'current_package_count': len(plan['product_development']['packages']),
            'queue_authority': 'product_development', 'legacy_stage_next_ready': plan['next_ready'],
            'product_content_sha256': digest,
            'file_count': len(files), 'provider_calls': 0, 'efficacy': 'NOT_TESTED'}


if __name__ == '__main__':
    import sys
    try:
        print(json.dumps(validate_tree(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
    except (PlanningError, ValueError, KeyError, TypeError, OSError) as exc:
        print(f'PLANNING CHECK FAILED: {exc}', file=sys.stderr)
        raise SystemExit(1)
