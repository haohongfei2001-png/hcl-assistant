"""Explicit synthetic development branch of the existing Interaction Controller.

Transient preparation only. No product context record is derived from HCL output.
"""
import copy
import json
import threading
import time
from packages.store.ledger import Fault, canonical, digest, now, uid
from packages.runtime_bridge.contract import CAPABILITIES, fingerprint
from packages.runtime_bridge.serialization import validate_request, provenance

SPEC_FIELDS={'schema_version','capability_id','query','input_class','fixture_family','purpose','timeout_ms'}


def validate(controller, tenant, request, conversation):
    spec=request.get('development_execution')
    if spec is None:return None
    if controller.development_bridge is None: raise Fault(403,'Experimental development bridge is not configured')
    if not controller.store.volatile or tenant not in {'synthetic-demo-a','synthetic-demo-b'} or conversation['memory']!='TEMPORARY' or conversation.get('topic_id') is not None:
        raise Fault(403,'Development runtime requires an isolated temporary synthetic conversation')
    if not isinstance(spec,dict) or set(spec)!=SPEC_FIELDS: raise Fault(400,'Unknown development input field')
    event=request.get('event',{})
    if event.get('type','message') not in {'message','upload'} or event.get('records') or event.get('revisions') or event.get('simulation') or request.get('source_refs'):
        raise Fault(403,'Experimental preparation accepts original sources only, without memory commands or simulation')
    candidate={**spec,'request_id':'validation','sources':[{'source_id':'validation','version':1,'sha256':digest(event.get('text','')),'text':event.get('text','')}]}
    try: validate_request(candidate)
    except (ValueError,TypeError,UnicodeError) as error: raise Fault(400,str(error)) from None
    result=controller.development_bridge.handshake()
    if result['handshake_status']!='READY':raise Fault(409,'Runtime handshake refused: '+result['handshake_status'])
    return {**copy.deepcopy(spec),'handshake':result}


def operation(run):
    capability=run['development_request']['capability_id']
    return {'operation_id':uid(),'capability_id':capability,'input_versions':[run['input_source_ref']],
            'read_dependencies':[run['input_source_ref']],'output_ids':[],'status':'PENDING',
            'cache_status':'NOT_REUSED','model_calls':0,'usage_refs':[],'selected':capability in CAPABILITIES,
            'executed':False,'result_produced':False,'used_in_answer':False,'cache_reused':False,'actual_treatment':False}


def initialize(controller,run,spec,source):
    ready=spec.pop('handshake')
    run['selected_context'].update(record_ids=[],records=[],source_versions=[run['input_source_ref']],coverage='PARTIAL',extraction_scope='EXPERIMENTAL_INPUT_ONLY',content_digest=digest(source['text']))
    request={**spec,'request_id':run['run_id'],'sources':[{'source_id':source['id'],'version':source['version'],'sha256':source['sha256'],'text':source['text']}]}
    direct=controller.direct(request['query'])
    run.update(development_request=request,development_handshake=ready,runtime_outputs=[],unresolved_updates=[],
               selected_capability_ids=[] if direct or request['capability_id'] not in CAPABILITIES else [request['capability_id']],
               route='DIRECT' if direct else ('SELECTED_COGNITION' if request['capability_id'] in CAPABILITIES else 'CLARIFY'))
    identity=provenance(controller.development_bridge.config,ready['capability_manifest_digest'])
    run['run_receipt'].update(mode='REAL',development_only=True,production_enabled=False,evidence_class='DEVELOPMENT_INTEGRATION_ONLY',
        bridge_provenance=identity,capability_snapshot=ready['discovered_capabilities'],runtime_hash=identity['artifact_digest'],
        config_hash=identity['config_hash'],route=run['route'],capabilities=run['selected_capability_ids'],actual_treatment='PENDING',
        usage={'provider_calls':0,'adapter_invocations':0,'input_tokens':None,'output_tokens':None,'reasoning_tokens':None,
               'cost':{'amount':0,'currency':'USD','source':'PROVIDER_FREE_RUNTIME_PREPARATION'},'latency_ms':None})
    run['operation_receipts']=[] if direct else [operation(run)]
    run['run_receipt']['operations']=copy.deepcopy(run['operation_receipts'])


def finish(controller,tenant,run_id):
    store=controller.store
    with store.transaction():
        run=store.get(tenant,'run',run_id)
        if not run['pending'] or run.get('executing'):return
        run['executing']=True
        cancel=threading.Event();controller.development_cancellations[run_id]=cancel
        for op in run['operation_receipts']:op.update(status='RUNNING',executed=None)
        run['run_receipt']['operations']=copy.deepcopy(run['operation_receipts']);store.put(tenant,'run',run)
    started=time.monotonic();called=False
    try:
        if controller.development_bridge is None or fingerprint(controller.development_bridge.config)!=run['run_receipt']['config_hash']:
            raise Fault(409,'PIN_CHANGED_REPIN_REQUIRED')
        store.source(tenant,run['input_source_ref'],run['conversation_id'],run['topic_id'])
        response=None
        if run['route']!='DIRECT':
            called=True;response=controller.development_bridge.execute(run['development_request'],cancel)
        with store.transaction():
            current=store.get(tenant,'run',run_id)
            if not current['pending']:return
            if current.get('redacted') or store.version(tenant)!=run['state_version_after'] or store.account(tenant)['policy']!=run['selected_context']['policy_revision']:
                current.update(pending=False,errors=['STALE_OUTPUT_WITHHELD'],answer=None)
                current['run_receipt'].update(outcome='PARTIAL',errors=current['errors'],actual_treatment='NO_TREATMENT' if response is None else response['status'],finished_at=now())
                for op in current['operation_receipts']:
                    op.update(status=response['status'],executed=response['executed'],result_produced=response['result_produced'],used_in_answer=False,
                              publication_status='WITHHELD_STALE',provenance=response['provenance'],native_receipt_digest=response['native_receipt_digest'])
                current['run_receipt']['operations']=copy.deepcopy(current['operation_receipts'])
                controller.emit(current,'run.failed',{'reason':'State or policy changed'});store.put(tenant,'run',current);return
            status='NO_TREATMENT' if response is None else response['status']
            outputs=[] if response is None else response['outputs'];current['runtime_outputs']=outputs
            diagnostics=[] if response is None else response['diagnostics']
            current['development_result']=response
            for op in current['operation_receipts']:
                op.update(status=status,selected=response['selected'],executed=response['executed'],result_produced=response['result_produced'],
                          output_ids=[o['output_id'] for o in outputs],actual_treatment=status=='EXECUTED',
                          provenance=response['provenance'],native_receipt_digest=response['native_receipt_digest'],diagnostics=diagnostics)
            receipt=current['run_receipt'];receipt.update(actual_treatment=status,finished_at=now())
            receipt['usage']['latency_ms']=round((time.monotonic()-started)*1000)
            terminal={'FAILED':'FAILED','UNRESOLVED':'UNRESOLVED','CANCELLED':'CANCELLED'}
            current['pending']=False
            if status in terminal:
                current['errors']=[d['reason'] for d in diagnostics];receipt.update(outcome='UNKNOWN' if status=='UNRESOLVED' and response['executed'] is None else terminal[status],errors=current['errors'])
                receipt['operations']=copy.deepcopy(current['operation_receipts'])
                controller.emit(current,'run.cancelled' if status=='CANCELLED' else 'run.failed',{'reason':status})
                store.put(tenant,'run',current);return
            if response is None:answer='2 + 2 = 4。'
            elif outputs:
                answer='开发运行时识别到来源中的显式表达：'+ '；'.join(o['quote'] for o in outputs[:4])+'。这些表达不确立私人状态或世界事实。'
            else:answer='开发运行时未对原始输入产生专门处理（'+status+'）。未改写输入；未声称理解或生成认知结论。'
            used_outputs=outputs[:4];used_ids=[o['output_id'] for o in used_outputs]
            for op in current['operation_receipts']:op['used_in_answer']=bool(used_outputs)
            if response is not None: current['development_result']['used_in_answer']=bool(used_outputs)
            claims=[{'operation_output_id':o['output_id'],'source_refs':[{**current['input_source_ref'],'span':o['span']}],
                     'text':o['quote'],'epistemic_status':o['epistemic_status']} for o in used_outputs]
            prep={'snapshot_id':run['snapshot_id'],'valid_context_refs':[], 'operation_output_refs':used_ids,'claim_bindings':claims,
                  'material_uncertainties':['Development syntax only; private state and world truth not established.'],
                  'alternatives':[],'assumptions':[],'coverage':'PARTIAL','input_coverage':'EXPERIMENTAL_BOUNDED_SYNTAX','main_judgment':answer,
                  'forbidden_promotions':['expression_to_private_truth','experimental_to_production','execution_to_efficacy'],
                  'response_intent':'development_report','length_style_policy':'concise','resource_remaining':{'provider_calls':0}}
            current['answer_preparation']=prep;answer_id=uid()
            current['answer']={'answer_id':answer_id,'run_id':run_id,'snapshot_id':run['snapshot_id'],'text':answer,
                'claim_bindings':claims,'citation_refs':[current['input_source_ref']],'material_uncertainties':prep['material_uncertainties'],
                'coverage':prep['coverage'],'published_at':now(),'status':'PUBLISHED','mode':'REAL','development_only':True}
            current['answer_identity']={k:current['answer'][k] for k in ('answer_id','run_id','snapshot_id')}
            current['explain_projection']={**current['answer_identity'],'judgment_basis':claims,'source_links':[current['input_source_ref']],
                                           'redactions':[],'recorded_at':now()}
            current['unresolved_updates']=[] if status=='EXECUTED' or response is None else [{'event_id':run['input_event_id'],'reason':status}]
            receipt.update(outcome='COMPLETED' if status=='EXECUTED' or response is None else 'UNRESOLVED',operations=copy.deepcopy(current['operation_receipts']))
            for op in current['operation_receipts']:controller.emit(current,'operation.completed',op)
            controller.emit(current,'answer.delta',{'text':answer});controller.emit(current,'answer.completed',current['answer']);store.put(tenant,'run',current)
    except Exception as error:
        reason='PIN_CHANGED_REPIN_REQUIRED' if str(error)=='PIN_CHANGED_REPIN_REQUIRED' else 'DEVELOPMENT_EXECUTION_FAILED'
        with store.transaction():
            current=store.get(tenant,'run',run_id)
            if current['pending']:
                current.update(pending=False,errors=[reason],answer=None)
                current['run_receipt'].update(outcome='FAILED',actual_treatment='FAILED',errors=current['errors'],finished_at=now())
                for op in current['operation_receipts']:op.update(status='FAILED',executed=None if called else False)
                current['run_receipt']['operations']=copy.deepcopy(current['operation_receipts'])
                controller.emit(current,'run.failed',{'reason':reason});store.put(tenant,'run',current)
    finally:
        with store.lock:controller.development_cancellations.pop(run_id,None)


def reset_retry(controller,retry):
    retry.pop('development_result',None);retry['runtime_outputs']=[]
    retry['development_request']['request_id']=retry['run_id']
    retry['operation_receipts']=[] if retry['route']=='DIRECT' else [operation(retry)]
    retry['run_receipt'].update(actual_treatment='PENDING',operations=copy.deepcopy(retry['operation_receipts']))
    retry['run_receipt']['usage']['latency_ms']=None
