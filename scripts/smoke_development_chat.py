"""Manual one-grant original-synthetic product smoke. Never called by default CI."""
import hashlib
import io
import json
import re
import zipfile
from decimal import Decimal
from urllib.parse import urlsplit
from urllib.error import HTTPError
import os
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apps.api.development_server import application
from packages.store.ledger import Fault

GRANT='hcla-20261001-six-requests-usd10'
PRIOR_RUN=36797830169
OWNER_ID=326690450
COMMAND_TITLE='HCLA approved smoke continuation 36797830169'
CHECKPOINT=Path(__file__).resolve().parents[1]/'docs/DEVELOPMENT_CHAT_LIVE_CHECKPOINT.json'

def verify_single_hosted_attempt(env, get_json, event=None):
    if env.get('HCLA_APPROVED_GRANT')!=GRANT:raise ValueError('explicit_product_grant_required')
    if env.get('GITHUB_REPOSITORY')!='haohongfei2001-png/hcl-assistant' or env.get('GITHUB_REF')!='refs/heads/main':raise ValueError('reviewed_product_main_required')
    if env.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('paid_workflow_reruns_refused')
    continuation=env.get('HCLA_SMOKE_PROFILE')=='continuation'
    run_id=env.get('GITHUB_RUN_ID');run=get_json('/actions/runs/'+str(run_id));number=2 if continuation else 1
    if run.get('run_number')!=number or env.get('GITHUB_RUN_NUMBER',str(number))!=str(number):raise ValueError('initial_grant_run_number_required')
    runs=get_json('/actions/workflows/'+str(run['workflow_id'])+'/runs?per_page=100')
    expected={run_id,str(PRIOR_RUN)} if continuation else {run_id}
    if {str(item['id']) for item in runs.get('workflow_runs',[])}!=expected or len(runs.get('workflow_runs',[]))!=number or runs.get('total_count')!=number:raise ValueError('grant_already_attempted_new_approval_required')
    if run.get('head_branch')!='main':raise ValueError('manual_main_dispatch_required')
    if continuation:
        if run.get('actor',{}).get('id')!=OWNER_ID:raise ValueError('owner_control_required')
        prior=get_json('/actions/runs/'+str(PRIOR_RUN))
        if prior.get('run_number')!=1 or prior.get('run_attempt')!=1 or prior.get('workflow_id')!=run['workflow_id'] or prior.get('head_sha')!=json.loads(CHECKPOINT.read_text())['source_commit']:raise ValueError('prior_run_identity_required')
    if run.get('event')=='issues' and continuation:
        event=event or {};issue=event.get('issue',{})
        expected_body='/hcla-continue-initial-smoke\nprior_run='+str(PRIOR_RUN)+'\nmain_sha='+env.get('GITHUB_SHA','')+'\ngrant='+GRANT
        if event.get('action')!='opened' or issue.get('user',{}).get('id')!=OWNER_ID or event.get('sender',{}).get('id')!=OWNER_ID or issue.get('title')!=COMMAND_TITLE or issue.get('body')!=expected_body or issue.get('pull_request') or not re.fullmatch('[0-9a-f]{40}',env.get('GITHUB_SHA','')) or run.get('head_sha')!=env.get('GITHUB_SHA'):raise ValueError('exact_owner_command_required')
    elif run.get('event')!='workflow_dispatch':raise ValueError('manual_main_dispatch_required')


def verify_checkpoint(raw):
    frozen=json.loads(CHECKPOINT.read_text())
    if (frozen['prior_calls']!=3 or frozen['remaining_calls']!=3 or frozen['grant_total_calls']!=6 or Decimal(frozen['prior_reserved_usd'])+Decimal(frozen['remaining_reserved_allowance_usd'])!=Decimal('10')):raise ValueError('frozen_grant_accounting_mismatch')
    if hashlib.sha256(raw).hexdigest()!=frozen['artifact_sha256']:raise ValueError('prior_artifact_digest_mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.namelist()!=['development-chat-receipt.json'] or archive.getinfo(archive.namelist()[0]).file_size>65536:raise ValueError('bounded_receipt_required')
        prior=json.loads(archive.read(archive.namelist()[0]))
    if prior.get('live_calls')!=3 or len(prior.get('runs',[]))!=3 or prior['budget']['request_count']!=3 or prior['budget']['reserved_cost_usd']!=frozen['prior_reserved_usd'] or prior['budget']['max_requests']!=6 or prior['budget']['max_cost_usd']!='10':raise ValueError('prior_accounting_mismatch')
    for attempt in prior['runs']:
        receipt=attempt['receipt']
        if receipt['usage']['provider_calls']!=1 or receipt['provider']['send_state']!='sent' or receipt['provider']['actual_model']!='deepseek-v4-pro':raise ValueError('prior_attempt_unresolved')
    if [r['run_id'] for r in prior['runs']]!=[r['run_id'] for r in frozen['prior_outcomes']]:raise ValueError('prior_attempt_identity_mismatch')
    return frozen


def download_checkpoint(root, token, get_json):
    frozen=json.loads(CHECKPOINT.read_text());identity=frozen['artifact_id']
    meta=get_json('/actions/artifacts/'+str(identity))
    if meta.get('expired') or meta.get('workflow_run',{}).get('id')!=PRIOR_RUN or meta['workflow_run'].get('head_sha')!=frozen['source_commit']:raise ValueError('prior_artifact_identity_required')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    request=urllib.request.Request(root+'/actions/artifacts/'+str(identity)+'/zip',headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=20) as response:raw=response.read(1048577)
    except HTTPError as error:
        if error.code not in (301,302,303,307,308):raise
        target=error.headers.get('Location','');parsed=urlsplit(target)
        if parsed.scheme!='https' or parsed.username or parsed.password or not parsed.hostname or not parsed.hostname.endswith(('.blob.core.windows.net','.githubusercontent.com','.s3.amazonaws.com')):raise ValueError('unexpected_artifact_destination')
        # Never forward the GitHub bearer credential to the signed blob destination.
        with urllib.request.urlopen(urllib.request.Request(target),timeout=20) as response:raw=response.read(1048577)
    if len(raw)>1048576:raise ValueError('artifact_size_limit')
    return verify_checkpoint(raw)


def smoke(app, checkpoint=None):
    service=app.live_chat_service
    if service is None:raise ValueError('server_configuration_required')
    if service.config.model!='deepseek-v4-pro':raise ValueError('approved_same_hcl_model_required')
    count=3 if checkpoint else 6;cap=Decimal('5.8233088') if checkpoint else Decimal('10');output_cap=8192 if checkpoint else 2048
    if service.config.max_requests!=count or service.config.max_cost_usd>cap or service.config.max_output_tokens>output_cap:raise ValueError('approved_smoke_caps_exceeded')
    if app.development_bridge is None or app.development_bridge.handshake()['handshake_status']!='READY':raise ValueError('reviewed_bridge_required')
    tenant='synthetic-demo-a';c=app.stores.conversation(tenant,memory='TEMPORARY')['id'];store=app.stores.for_conversation(tenant,c);ctrl=app.controller(store);receipts=[];failures=[]
    def check(condition,reason):
        if condition:return
        if checkpoint:failures.append(reason)
        else:raise ValueError(reason)
    def report(status):
        budget=service.budget.snapshot();calls=[r['receipt']['usage']['provider_calls'] for r in receipts]
        live_calls=sum(calls) if budget['request_count']<=len(receipts) and all(isinstance(c,int) for c in calls) else None
        prior_calls=checkpoint['prior_calls'] if checkpoint else 0
        prior_reserved=Decimal(checkpoint['prior_reserved_usd']) if checkpoint else Decimal(0)
        return {'status':status,'live_calls':live_calls,'attempts_recorded':len(receipts),'prior_calls':prior_calls,'aggregate_calls':prior_calls+live_calls if live_calls is not None else None,'aggregate_reserved_usd':str(prior_reserved+Decimal(budget['reserved_cost_usd'])),'runs':receipts,'budget':budget,'failures':failures,'prior_run_id':PRIOR_RUN if checkpoint else None,'public_https_url_verified':False,'efficacy':'NOT_TESTED'}
    def say(text,live=True,**extra):
        event={'text':text};event.update(extra.pop('event',{}))
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':c},'expected_state_version':store.version(tenant),'idempotency_key':'original-smoke-'+str(store.version(tenant)),'development_chat':live,'synthetic_input_confirmed':True,'event':event,**extra})
        if live:
            receipts.append({'run_id':run['run_id'],'answer':run.get('answer'),'receipt':run['run_receipt'],'source_binding_count':len((run.get('answer') or {}).get('citation_refs',[]))})
            check(run['run_receipt']['outcome']=='COMPLETED' and bool(run.get('answer')),'live_smoke_not_completed_no_retry')
        return run
    try:
        if not checkpoint:
            first=say('这是原创虚构场景：纸灯工作坊的主色是蓝色。请用一句自然中文确认。')
            follow=say('在这个虚构场景中，刚才设定的主色是什么？')
            if first['run_receipt']['actual_treatment']!='NO_TREATMENT' or '蓝' not in follow['answer']['text']:raise ValueError('ordinary_followup_acceptance_unverified')
        record=say('报告[原创角色]：纸灯工作坊周四开放',False)
        target=next(r['record_id'] for r in record['selected_context']['records'] if r['content']=='纸灯工作坊周四开放')
        changed=say('明确更正',False,event={'type':'revision','revisions':[{'action':'CORRECT','target_ids':[target],'new_record':{'kind':'USER_REPORTED_EVENT','content':'纸灯工作坊周五开放'}}]})
        corrected=say('根据当前有效记录，虚构工作坊哪天开放？请区分已更正的旧说法。')
        check('周五' in (corrected.get('answer') or {}).get('text',''),'correction_acceptance_unverified')
        successor=next(r['record_id'] for r in changed['selected_context']['records'] if r['content']=='纸灯工作坊周五开放')
        say('停止使用安排',False,event={'type':'revision','revisions':[{'action':'STOP_USING','target_ids':[successor]}]})
        withdrawn=say('现在是否还有可用的开放日期记录？没有则说明未知。')
        check(not any(r['content']=='纸灯工作坊周五开放' for r in withdrawn['selected_context']['records']),'withdrawal_context_failed')
        # A fresh isolated original input goes through the unchanged pinned Bridge.
        c=app.stores.conversation(tenant,memory='TEMPORARY')['id']
        treated=say('Ada said, "I believe that the workshop starts Friday."',development_execution={'schema_version':'1.0','capability_id':'belief_interpretation','query':'What does Ada explicitly believe? Cite the supplied HCL output marker when using it.','input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000})
        check(treated['run_receipt']['actual_treatment']=='EXECUTED' and any(o['used_in_answer'] for o in treated['operation_receipts']),'hcl_used_acceptance_unverified')
        return report('INCOMPLETE_NO_AUTOMATIC_RETRY' if failures else 'VERIFIED_DEVELOPMENT_CHAIN_ONLY')
    except Exception:
        return report('INCOMPLETE_NO_AUTOMATIC_RETRY')


def main():
    root='https://api.github.com/repos/haohongfei2001-png/hcl-assistant'
    def get_json(path):
        request=urllib.request.Request(root+path,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'})
        with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
    executing=False
    try:
        event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text()) if os.environ.get('GITHUB_EVENT_PATH') else None
        verify_single_hosted_attempt(os.environ,get_json,event)
        checkpoint=download_checkpoint(root,os.environ['GITHUB_TOKEN'],get_json) if os.environ.get('HCLA_SMOKE_PROFILE')=='continuation' else None
        app=application(':memory:','.local/hosted-smoke-budget.sqlite',os.environ.get('HCL_DEVELOPMENT_ARTIFACT'))
        executing=True
        result=smoke(app,checkpoint)
    except Exception:
        result={'status':'EXECUTION_UNKNOWN_NO_RETRY' if executing else 'PREFLIGHT_REFUSED_NO_RETRY','live_calls':None if executing else 0,'public_https_url_verified':False}
    Path('.local').mkdir(exist_ok=True);Path('.local/development-chat-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'runs'}},ensure_ascii=False))
    return 0 if result['status']=='VERIFIED_DEVELOPMENT_CHAIN_ONLY' else 1

if __name__=='__main__':raise SystemExit(main())
