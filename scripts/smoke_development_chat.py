"""Manual one-grant original-synthetic product smoke. Never called by default CI."""
import json
import os
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apps.api.development_server import application
from packages.store.ledger import Fault

GRANT='hcla-20261001-six-requests-usd10'

def verify_single_hosted_attempt(env, get_json):
    if env.get('HCLA_APPROVED_GRANT')!=GRANT:raise ValueError('explicit_product_grant_required')
    if env.get('GITHUB_REPOSITORY')!='haohongfei2001-png/hcl-assistant' or env.get('GITHUB_REF')!='refs/heads/main':raise ValueError('reviewed_product_main_required')
    if env.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('paid_workflow_reruns_refused')
    run_id=env.get('GITHUB_RUN_ID');run=get_json('/actions/runs/'+str(run_id))
    if run.get('run_number')!=1 or env.get('GITHUB_RUN_NUMBER','1')!='1':raise ValueError('initial_grant_run_number_required')
    runs=get_json('/actions/workflows/'+str(run['workflow_id'])+'/runs?per_page=100')
    if len(runs.get('workflow_runs',[]))!=1 or str(runs['workflow_runs'][0]['id'])!=run_id or runs.get('total_count')!=1:raise ValueError('grant_already_attempted_new_approval_required')
    if run.get('event')!='workflow_dispatch' or run.get('head_branch')!='main':raise ValueError('manual_main_dispatch_required')


def smoke(app):
    service=app.live_chat_service
    if service is None:raise ValueError('server_configuration_required')
    if service.config.max_requests!=6 or service.config.max_cost_usd>10 or service.config.max_output_tokens>2048:raise ValueError('approved_smoke_caps_exceeded')
    if app.development_bridge is None or app.development_bridge.handshake()['handshake_status']!='READY':raise ValueError('reviewed_bridge_required')
    tenant='synthetic-demo-a';c=app.stores.conversation(tenant,memory='TEMPORARY')['id'];store=app.stores.for_conversation(tenant,c);ctrl=app.controller(store);receipts=[]
    def say(text,live=True,**extra):
        event={'text':text};event.update(extra.pop('event',{}))
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':c},'expected_state_version':store.version(tenant),'idempotency_key':'original-smoke-'+str(store.version(tenant)),'development_chat':live,'synthetic_input_confirmed':True,'event':event,**extra})
        if live:
            receipts.append({'run_id':run['run_id'],'answer':run.get('answer'),'receipt':run['run_receipt'],'source_binding_count':len((run.get('answer') or {}).get('citation_refs',[]))})
            if run['run_receipt']['outcome']!='COMPLETED' or not run.get('answer'):raise ValueError('live_smoke_not_completed_no_retry')
        return run
    try:
        first=say('这是原创虚构场景：纸灯工作坊的主色是蓝色。请用一句自然中文确认。')
        follow=say('在这个虚构场景中，刚才设定的主色是什么？')
        if first['run_receipt']['actual_treatment']!='NO_TREATMENT' or '蓝' not in follow['answer']['text']:raise ValueError('ordinary_followup_acceptance_unverified')
        record=say('报告[原创角色]：纸灯工作坊周四开放',False)
        target=next(r['record_id'] for r in record['selected_context']['records'] if r['content']=='纸灯工作坊周四开放')
        changed=say('明确更正',False,event={'type':'revision','revisions':[{'action':'CORRECT','target_ids':[target],'new_record':{'kind':'USER_REPORTED_EVENT','content':'纸灯工作坊周五开放'}}]})
        corrected=say('根据当前有效记录，虚构工作坊哪天开放？请区分已更正的旧说法。')
        if '周五' not in corrected['answer']['text']:raise ValueError('correction_acceptance_unverified')
        successor=next(r['record_id'] for r in changed['selected_context']['records'] if r['content']=='纸灯工作坊周五开放')
        say('停止使用安排',False,event={'type':'revision','revisions':[{'action':'STOP_USING','target_ids':[successor]}]})
        withdrawn=say('现在是否还有可用的开放日期记录？没有则说明未知。')
        if any(r['content']=='纸灯工作坊周五开放' for r in withdrawn['selected_context']['records']):raise ValueError('withdrawal_context_failed')
        # A fresh isolated original input goes through the unchanged pinned Bridge.
        c=app.stores.conversation(tenant,memory='TEMPORARY')['id']
        treated=say('Ada said, "I believe that the workshop starts Friday."',development_execution={'schema_version':'1.0','capability_id':'belief_interpretation','query':'What does Ada explicitly believe? Cite the supplied HCL output marker when using it.','input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000})
        if treated['run_receipt']['actual_treatment']!='EXECUTED' or not any(o['used_in_answer'] for o in treated['operation_receipts']):raise ValueError('hcl_used_acceptance_unverified')
        return {'status':'VERIFIED_DEVELOPMENT_CHAIN_ONLY','live_calls':len(receipts),'runs':receipts,'budget':service.budget.snapshot(),'public_https_url_verified':False,'efficacy':'NOT_TESTED'}
    except Exception:
        return {'status':'INCOMPLETE_NO_AUTOMATIC_RETRY','live_calls':len(receipts),'runs':receipts,'budget':service.budget.snapshot(),'public_https_url_verified':False,'efficacy':'NOT_TESTED'}


def main():
    root='https://api.github.com/repos/haohongfei2001-png/hcl-assistant'
    def get_json(path):
        request=urllib.request.Request(root+path,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
    executing=False
    try:
        verify_single_hosted_attempt(os.environ,get_json)
        app=application(':memory:','.local/hosted-smoke-budget.sqlite',os.environ.get('HCL_DEVELOPMENT_ARTIFACT'))
        executing=True
        result=smoke(app)
    except Exception:
        result={'status':'EXECUTION_UNKNOWN_NO_RETRY' if executing else 'PREFLIGHT_REFUSED_NO_RETRY','live_calls':None if executing else 0,'public_https_url_verified':False}
    Path('.local').mkdir(exist_ok=True);Path('.local/development-chat-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'runs'}},ensure_ascii=False))
    return 0 if result['status']=='VERIFIED_DEVELOPMENT_CHAIN_ONLY' else 1

if __name__=='__main__':raise SystemExit(main())
