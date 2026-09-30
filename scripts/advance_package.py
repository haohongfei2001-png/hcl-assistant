"""Advance only the current dependency-safe package after its checks pass."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['CANONICAL_SETUP','EVENT_SOURCE_STATE_LEDGER','REVISION_HISTORICAL_DEPENDENCIES','PRIVACY_EXPIRY_RETRIEVAL','CONTROLLER_RUN_LIFECYCLE','DESKTOP_CHAT_FILE_FLOW','SYNTHETIC_COGNITION_SYNTHESIS','EXPLAIN_MEMORY_CONTROLS','LAB_INTEGRATED_HANDOFF']


def advance(package, evidence):
    path=ROOT/'control/plan.json'; plan=json.loads(path.read_text()); rows=plan['packages']
    current=next(r for r in rows if r['id']==package)
    assert plan['next_package_id']==package and current['state']=='NEXT_READY'
    assert all(next(r for r in rows if r['id']==d)['state']=='COMPLETE' for d in current['depends_on'])
    current.update(state='COMPLETE', evidence=evidence)
    index=rows.index(current)
    if index+1<len(rows):
        following=rows[index+1]; following['state']='NEXT_READY'
        plan['next_package_id']=following['id']; plan['next_ready']=following['id']+'_'+NAMES[index+1]
        plan['phase']=following['stage']+'_IMPLEMENTING'
    else:
        plan['next_package_id']=None; plan['next_ready']='STOP_WITH_HANDOFF_L3_GATED'; plan['phase']='L2_COMPLETE'
    plan['evidence']['product_implementation']=evidence
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    table='\n'.join('| '+r['id']+' | '+r['delta']+' | '+', '.join(r['depends_on'])+' | '+r['state']+' |' for r in rows)
    (ROOT/'DEVELOPMENT_PLAN.md').write_text('# HCL Assistant Live Development Plan\n\nCanonical: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [packages](docs/L0_L2_WORK_PACKAGES.md), [contracts](contracts/PRODUCT_CONTRACTS_V1.md).\n\n**NEXT_READY: '+plan['next_ready']+'**\n\n| ID | Delta | Dependencies | State |\n|---|---|---|---|\n'+table+'\n\nSole writer: `product/l1-01`, sequential L1/L2 checkpoints in one coherent PR. Latest package evidence: '+evidence+'. Actual SHA validation is recorded by CI, not fabricated in live state.\n\nL3 remains gated: I06 disposition, pinned permitted runtime artifact/interface, product adapter scope validation, explicit execution and data authorization. Do not enter L3.\n')
    (ROOT/'STATUS.md').write_text('# HCL Assistant Product Status\n\n**'+plan['phase']+' / '+evidence+'**\n\n**NEXT_READY: '+plan['next_ready']+'**\n\n- physical split = COMPLETE\n- repository isolation = COMPLETE at repository boundary\n- Canonical source: `haohongfei2001-png/hcl-assistant/main`. Branch checkpoints are review evidence; adoption requires exact-head CI, merge and exact-main verification.\n- Synthetic/mock only; provider calls/spend 0/0. Real runtime NOT_INTEGRATED; efficacy and real language generalization NOT_TESTED.\n- Dedicated sole writer: `product/l1-01`. See [execution](docs/EXECUTION.md), [queue](DEVELOPMENT_PLAN.md), [acceptance](docs/ACCEPTANCE_MATRIX.md).\n\nL3 gates remain unsatisfied: I06 disposition, pinned permitted artifact/interface, product adapter scope validation, explicit execution and data authorization. Physical separation is completed; no research imports or real/private data are authorized.\n')


if __name__=='__main__':
    advance(*sys.argv[1:])
