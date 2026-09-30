"""Advance the sole current queue; never rewrite the canonical product documents.

This records a reviewed package checkpoint, not a CI/adoption assertion. The PR
and final main still require exact-SHA CI. Legacy stage fields remain immutable.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_planning import L3_STOP, PlanningError, require, validate_plan, validate_queue_mirrors

ROOT = Path(__file__).resolve().parents[1]


def queue_summary(q):
    current = next((r for r in q['packages'] if r['id'] == q['next_package_id']), None)
    detail = (current['delta'] + '。验收：' + '、'.join(current['acceptance'])) if current else '四包已完成；L3四门槛未满足，停止交接，不启动provider、Judge或Act。'
    return ('<!-- CURRENT_PRODUCT_QUEUE_START -->\n'
            '**NEXT_READY: ' + q['next_ready'] + '**\n\n'
            '当前产品阶段：' + q['phase'] + '。唯一当前任务：' + (q['next_package_id'] or '无，等待L3门槛') + '。\n\n'
            + detail + '\n\n'
            '任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。\n'
            '<!-- CURRENT_PRODUCT_QUEUE_END -->')


def refresh_queue_summary(text, q):
    result, count = re.subn(r'<!-- CURRENT_PRODUCT_QUEUE_START -->.*?<!-- CURRENT_PRODUCT_QUEUE_END -->',
                            lambda _: queue_summary(q), text, flags=re.S)
    require(count == 1, 'unique generated current-queue summary required')
    return result


def advance(package: str, evidence: str, root: Path = ROOT) -> None:
    path = root / 'control/plan.json'
    plan = json.loads(path.read_text())
    validate_plan(plan)
    q = plan['product_development']
    validate_queue_mirrors(root, q)
    require(package == q['next_package_id'], 'only the current product package can advance')
    require(bool(evidence.strip()) and evidence not in {'NOT_IMPLEMENTED', 'NOT_TESTED'}, 'actual evidence reference required')
    rows = q['packages']
    current = next(r for r in rows if r['id'] == package)
    old_next = q['next_ready']
    current.update(state='COMPLETE', evidence=evidence)
    index = rows.index(current)
    if index + 1 < len(rows):
        following = rows[index + 1]
        following['state'] = 'NEXT_READY'
        q.update(next_package_id=following['id'], next_ready=following['task'], phase='ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING')
    else:
        q.update(next_package_id=None, next_ready=L3_STOP, phase='ASSISTANT_FIRST_REFINEMENT_COMPLETE')
    validate_plan(plan)
    # Prepare all replacements before writing. Preserve history, authority and gates.
    documents = {}
    for name in ('STATUS.md', 'DEVELOPMENT_PLAN.md', 'AGENTS.md', 'README.md'):
        text = (root / name).read_text()
        text = refresh_queue_summary(text, q)
        if name == 'DEVELOPMENT_PLAN.md':
            for row in rows:
                pattern = r'(?m)^(\| ' + re.escape(row['id']) + r' \|.*\| )[^|]+( \|)$'
                text, count = re.subn(pattern, lambda m: m[1] + row['state'] + m[2], text)
                require(count == 1, 'missing unique package mirror')
        documents[name] = text
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    for name, text in documents.items():
        (root / name).write_text(text)
    validate_queue_mirrors(root, q)


if __name__ == '__main__':
    try:
        advance(*sys.argv[1:])
    except (PlanningError, TypeError, OSError) as exc:
        raise SystemExit(str(exc))
