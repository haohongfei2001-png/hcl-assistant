"""Original synthetic full Controller smoke; prints receipts without research data."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.runtime_bridge.bridge import RuntimeBridge
from packages.controller.interaction import Controller
from packages.store.ledger import Ledger


def smoke(directory):
    bridge=RuntimeBridge(directory);ready=bridge.handshake()
    if ready['handshake_status']!='READY':raise ValueError(ready['handshake_status'])
    tenant='synthetic-demo-a';store=Ledger();conversation=store.conversation(tenant,memory='TEMPORARY')['id'];controller=Controller(store,development_bridge=bridge)
    rows=[]
    try:
        for text,query,capability,expected in [
            ('Original synthetic workshop scheduling task.','2+2','belief_interpretation','NO_TREATMENT'),
            ('Ada said, "I believe that the workshop starts Friday."','What does Ada believe?','belief_interpretation','EXECUTED'),
            ('原创中文：我不知道合成同事的想法。','对方在想什么？','belief_interpretation','NO_TREATMENT'),
            ('The synthetic workshop begins tomorrow.','What is the plan?','goal_plan','UNSUPPORTED')]:
            run=controller.handle_interaction(tenant,{'scope':{'conversation_id':conversation},'event':{'text':text},
                'expected_state_version':store.version(tenant),'idempotency_key':str(store.version(tenant)),
                'development_execution':{'schema_version':'1.0','capability_id':capability,'query':query,'input_class':'SYNTHETIC_NON_CONFIRMATION',
                    'fixture_family':'original_workshop_smoke_20261001','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}})
            if run['run_receipt']['actual_treatment']!=expected:raise ValueError('Unexpected smoke treatment: '+str(run['errors']))
            rows.append({'run_id':run['run_id'],'route':run['route'],'source_sha256':run['input_source_ref']['sha256'],
                         'receipt':run['run_receipt'],'operations':run['operation_receipts']})
        return {'pin':ready['runtime_identity'],'interface_identity':ready['interface_version'],'smoke':'PASS',
                'fixture_lineage':'ORIGINAL_SYNTHETIC_WORKSHOP_20261001','production_enabled':False,'efficacy':'NOT_TESTED','runs':rows}
    finally:store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('artifact_directory');args=parser.parse_args()
    print(json.dumps(smoke(args.artifact_directory),ensure_ascii=False,indent=2))
