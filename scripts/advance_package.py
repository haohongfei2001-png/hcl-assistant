"""Advance only the current dependency-safe package after its checks pass."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['CANONICAL_SETUP','EVENT_SOURCE_STATE_LEDGER','REVISION_HISTORICAL_DEPENDENCIES','PRIVACY_EXPIRY_RETRIEVAL','CONTROLLER_RUN_LIFECYCLE','DESKTOP_CHAT_FILE_FLOW','SYNTHETIC_COGNITION_SYNTHESIS','EXPLAIN_MEMORY_CONTROLS','LAB_INTEGRATED_HANDOFF','PINNED_RUNTIME_BRIDGE_CONTRACT_AND_HANDSHAKE','EXPERIMENTAL_MECHANISM_SYNTHETIC_E2E']


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
        plan['phase']=following['stage'].replace('.','_')+'_IMPLEMENTING'
    else:
        plan['next_package_id']=None; plan['next_ready']='STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED'; plan['phase']='L2_5_COMPLETE'
    plan['evidence']['product_implementation']=evidence
    if package.startswith('L2.5'):
        plan['evidence']['experimental_runtime_bridge']=evidence
        plan['evidence']['experimental_runtime_results']='NOT_EFFICACY_EVIDENCE'
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    table='\n'.join('| '+r['id']+' | '+r['delta']+' | '+', '.join(r['depends_on'])+' | '+r['state']+' |' for r in rows)
    (ROOT/'DEVELOPMENT_PLAN.md').write_text('# HCL Assistant Live Development Plan\n\nCanonical: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [packages](docs/L0_L2_WORK_PACKAGES.md), [contracts](contracts/PRODUCT_CONTRACTS_V1.md).\n\n**NEXT_READY: '+plan['next_ready']+'**\n\n| ID | Delta | Dependencies | State |\n|---|---|---|---|\n'+table+'\n\nSole writer follows the unique NEXT_READY package. Latest package evidence: '+evidence+'. Actual SHA validation is recorded by CI, not fabricated in live state.\n\nL2.5 is development-only. After it completes, L3 remains I06-gated Production Capability Activation and reuses the bridge transport.\n')
    (ROOT/'STATUS.md').write_text('# HCL Assistant Product Status\n\n**'+plan['phase']+' / '+evidence+'**\n\n**NEXT_READY: '+plan['next_ready']+'**\n\n- physical split = COMPLETE\n- repository isolation = COMPLETE at repository boundary\n- Canonical source: `haohongfei2001-png/hcl-assistant/main`. Branch checkpoints are review evidence; adoption requires exact-head CI, merge and exact-main verification.\n- L0-L2 mock product is complete. L2.5 may use only pinned development runtime on synthetic/non-confirmation inputs; production activation and efficacy remain NOT_TESTED.\n- Dedicated sole writer follows the unique NEXT_READY. See [execution](docs/EXECUTION.md), [queue](DEVELOPMENT_PLAN.md), [acceptance](docs/ACCEPTANCE_MATRIX.md).\n\nL2.5 bridge execution is development-only and not efficacy evidence. L3 gates remain I06 disposition, production-permitted artifact/interface, adapter scope validation and explicit execution/data authorization.\n')


if __name__=='__main__':
    advance(*sys.argv[1:])
