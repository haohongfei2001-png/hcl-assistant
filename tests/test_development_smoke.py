import unittest
from scripts.smoke_development_chat import verify_single_hosted_attempt, GRANT

class HostedGrantTests(unittest.TestCase):
    def setUp(self):self.env={'HCLA_APPROVED_GRANT':GRANT,'GITHUB_REPOSITORY':'haohongfei2001-png/hcl-assistant','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123'}
    def get(self,path):return {'workflow_id':456,'run_number':1,'event':'workflow_dispatch','head_branch':'main'} if path=='/actions/runs/123' else {'workflow_runs':[{'id':123}],'total_count':1}
    def test_first_manual_main_only(self):verify_single_hosted_attempt(self.env,self.get)
    def test_any_previous_attempt_refuses_even_failure_or_cancellation(self):
        def previous(path):return self.get(path) if path=='/actions/runs/123' else {'workflow_runs':[{'id':123},{'id':122,'conclusion':'cancelled'}],'total_count':2}
        with self.assertRaisesRegex(ValueError,'grant_already_attempted'):verify_single_hosted_attempt(self.env,previous)
    def test_rerun_fork_branch_and_unapproved_grant_refused(self):
        for key,value in [('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/feature'),('GITHUB_REPOSITORY','other/repo'),('HCLA_APPROVED_GRANT','research-experiment')]:
            with self.subTest(key=key),self.assertRaises(ValueError):verify_single_hosted_attempt({**self.env,key:value},self.get)
    def test_missing_current_or_deleted_history_never_reopens_grant(self):
        for listing in [{'workflow_runs':[],'total_count':0},{'workflow_runs':[{'id':122}],'total_count':1}]:
            with self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,lambda path:self.get(path) if path=='/actions/runs/123' else listing)
        with self.assertRaisesRegex(ValueError,'run_number'):verify_single_hosted_attempt(self.env,lambda path:{**self.get(path),'run_number':2} if path=='/actions/runs/123' else self.get(path))
    def test_api_failure_cannot_spend(self):
        def fail(path):raise OSError('offline')
        with self.assertRaises(OSError):verify_single_hosted_attempt(self.env,fail)

class ContinuationGuardTests(unittest.TestCase):
    def setUp(self):
        import json
        from scripts.smoke_development_chat import CHECKPOINT, OWNER_ID, COMMAND_TITLE, PRIOR_RUN
        self.prior=PRIOR_RUN;self.sha='c'*40;self.owner=OWNER_ID
        self.frozen=json.loads(CHECKPOINT.read_text())
        self.env={'HCLA_APPROVED_GRANT':GRANT,'HCLA_SMOKE_PROFILE':'continuation','GITHUB_REPOSITORY':'haohongfei2001-png/hcl-assistant','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_NUMBER':'2','GITHUB_RUN_ID':'124','GITHUB_SHA':self.sha}
        self.run={'workflow_id':456,'run_number':2,'head_branch':'main','head_sha':self.sha,'actor':{'id':self.owner},'event':'issues'}
        self.previous={'workflow_id':456,'run_number':1,'run_attempt':1,'head_sha':self.frozen['source_commit']}
        self.listing={'workflow_runs':[{'id':self.prior},{'id':124}],'total_count':2}
        self.event={'action':'opened','sender':{'id':self.owner},'issue':{'title':COMMAND_TITLE,'user':{'id':self.owner},'body':f'/hcla-continue-initial-smoke\nprior_run={self.prior}\nmain_sha={self.sha}\ngrant={GRANT}'}}
    def get(self,path):
        if path=='/actions/runs/124':return self.run
        if path=='/actions/runs/'+str(self.prior):return self.previous
        return self.listing
    def test_exact_owner_command_and_existing_prior_only(self):verify_single_hosted_attempt(self.env,self.get,self.event)
    def test_button_and_command_share_the_same_one_remaining_slot(self):
        self.run['event']='workflow_dispatch';verify_single_hosted_attempt(self.env,self.get)
        self.listing={'workflow_runs':[{'id':self.prior},{'id':124},{'id':125}],'total_count':3}
        with self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,self.get)
    def test_replayed_run_attempt_and_run_number_refused(self):
        for change in [{'GITHUB_RUN_ATTEMPT':'2'},{'GITHUB_RUN_NUMBER':'3'}]:
            with self.assertRaises(ValueError):verify_single_hosted_attempt({**self.env,**change},self.get,self.event)
    def test_nonowner_changed_sha_title_body_and_pr_refused(self):
        import copy
        variants=[]
        for field,value in [('title','ordinary issue'),('body',self.event['issue']['body']+'\nextra'),('user',{'id':999}),('pull_request',{})]:
            event=copy.deepcopy(self.event);event['issue'][field]=value if field!='pull_request' else {'url':'not-an-issue'};variants.append(event)
        event=copy.deepcopy(self.event);event['sender']['id']=999;variants.append(event)
        for event in variants:
            with self.subTest(event=event),self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,self.get,event)
        with self.assertRaises(ValueError):verify_single_hosted_attempt({**self.env,'GITHUB_SHA':'d'*40},self.get,self.event)
    def test_prior_identity_or_missing_history_refused(self):
        self.previous['head_sha']='d'*40
        with self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,self.get,self.event)
        self.previous['head_sha']=self.frozen['source_commit'];self.listing={'workflow_runs':[{'id':124}],'total_count':1}
        with self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,self.get,self.event)

class FrozenCheckpointTests(unittest.TestCase):
    def make(self,changes=None):
        import io,json,zipfile,hashlib
        prior={'live_calls':3,'budget':{'request_count':3,'reserved_cost_usd':'4.1766912','max_requests':6,'max_cost_usd':'10'},'runs':[{'run_id':'r'+str(i),'receipt':{'usage':{'provider_calls':1},'provider':{'send_state':'sent','actual_model':'deepseek-v4-pro'}}} for i in range(3)]}
        if changes:changes(prior)
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:z.writestr('development-chat-receipt.json',json.dumps(prior))
        raw=output.getvalue();frozen={'prior_calls':3,'remaining_calls':3,'grant_total_calls':6,'remaining_reserved_allowance_usd':'5.8233088','artifact_sha256':hashlib.sha256(raw).hexdigest(),'prior_reserved_usd':'4.1766912','prior_outcomes':[{'run_id':'r'+str(i)} for i in range(3)]}
        return raw,frozen
    def verify(self,raw,frozen):
        import tempfile,json
        from pathlib import Path
        from unittest.mock import patch
        from scripts.smoke_development_chat import verify_checkpoint
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'checkpoint.json';p.write_text(json.dumps(frozen))
            with patch('scripts.smoke_development_chat.CHECKPOINT',p):return verify_checkpoint(raw)
    def test_exact_three_consumed_attempts_and_reservation_retained(self):
        raw,frozen=self.make();self.assertEqual(self.verify(raw,frozen)['prior_reserved_usd'],'4.1766912')
    def test_tampering_and_unknown_prior_attempt_refuse(self):
        raw,frozen=self.make()
        with self.assertRaises(ValueError):self.verify(raw+b'changed',frozen)
        for mutate in [lambda j:j.update(live_calls=2),lambda j:j['budget'].update(request_count=2),lambda j:j['runs'][0]['receipt']['provider'].update(send_state='unknown'),lambda j:j['runs'][0]['receipt']['provider'].update(actual_model='another-model')]:
            raw,frozen=self.make(mutate)
            with self.assertRaises(ValueError):self.verify(raw,frozen)

class ContinuationFlowTests(unittest.TestCase):
    @unittest.skipUnless(__import__('os').environ.get('HCL_DEVELOPMENT_ARTIFACT'),'fixed runtime required')
    def test_three_distinct_remaining_cases_with_real_bridge_and_fake_provider(self):
        import os,json,tempfile
        from pathlib import Path
        from apps.api.server import Application
        from packages.adapter.development_budget import DevelopmentConfig,DevelopmentBudget
        from packages.adapter.deepseek import DeepSeekResult
        from packages.controller.live_chat import LiveChat
        from scripts.smoke_development_chat import smoke,CHECKPOINT
        class Fake:
            model='deepseek-v4-pro'
            calls=0
            def generate(self,messages,*,max_tokens,cancel_event,on_delta):
                self.calls+=1
                context=json.loads(messages[0]['content'].split('Current valid context:\n')[1])
                if any(c['marker']=='HCL1' for c in context):text='Ada 表达了工作坊周五开始的信念。[HCL1]'
                elif any(c['content']=='纸灯工作坊周五开放' for c in context):text='当前是周五。'
                else:text='没有可用的开放日期记录。'
                on_delta(text)
                return DeepSeekResult('SUCCEEDED',text,self.model,actual_model=self.model,send_state='sent',usage={'prompt_tokens':100,'completion_tokens':20},transport_stopped=True)
        env={'HCLA_DEEPSEEK_API_KEY':'fake.offline.only','HCLA_DEEPSEEK_BASE_URL':'https://api.deepseek.com','HCLA_DEEPSEEK_MODEL':'deepseek-v4-pro','HCLA_DEV_ACCESS_TOKEN':'fake.offline.access.password.only','HCLA_DEV_MAX_REQUESTS':'3','HCLA_DEV_MAX_COST_USD':'5.8233088','HCLA_DEV_MAX_OUTPUT_TOKENS':'8192','HCLA_DEV_BUDGET_ID':'offline-continuation-fixture','HCLA_DEV_INPUT_USD_PER_MILLION':'1.32','HCLA_DEV_OUTPUT_USD_PER_MILLION':'3.96'}
        with tempfile.TemporaryDirectory() as d:
            config=DevelopmentConfig.from_env(env);budget=DevelopmentBudget(str(Path(d)/'budget.sqlite'),config);adapter=Fake()
            app=Application(':memory:',os.environ['HCL_DEVELOPMENT_ARTIFACT'],LiveChat(config,budget,adapter))
            result=smoke(app,json.loads(CHECKPOINT.read_text()))
            self.assertEqual(result['status'],'VERIFIED_DEVELOPMENT_CHAIN_ONLY',result)
            self.assertEqual(adapter.calls,3);self.assertEqual(result['aggregate_calls'],6)
            self.assertLess(__import__('decimal').Decimal(result['aggregate_reserved_usd']),10)
            self.assertEqual(result['runs'][-1]['receipt']['actual_treatment'],'EXECUTED')
            app.close();budget.close()

    @unittest.skipUnless(__import__('os').environ.get('HCL_DEVELOPMENT_ARTIFACT'),'fixed runtime required')
    def test_interrupted_after_dispatch_never_reports_zero_calls(self):
        import os,json,tempfile
        from pathlib import Path
        from apps.api.server import Application
        from packages.adapter.development_budget import DevelopmentConfig,DevelopmentBudget
        from packages.controller.live_chat import LiveChat
        from tests.test_development_budget import fake_env
        from tests.test_live_chat_controller import Adapter
        from scripts.smoke_development_chat import smoke,CHECKPOINT
        with tempfile.TemporaryDirectory() as d:
            config=DevelopmentConfig.from_env(fake_env(HCLA_DEEPSEEK_MODEL='deepseek-v4-pro',HCLA_DEV_MAX_REQUESTS='3',HCLA_DEV_MAX_COST_USD='5.8233088',HCLA_DEV_MAX_OUTPUT_TOKENS='8192',HCLA_DEV_INPUT_USD_PER_MILLION='1.32',HCLA_DEV_OUTPUT_USD_PER_MILLION='3.96'))
            budget=DevelopmentBudget(str(Path(d)/'budget.sqlite'),config);adapter=Adapter();adapter.model='deepseek-v4-pro'
            app=Application(':memory:',os.environ['HCL_DEVELOPMENT_ARTIFACT'],LiveChat(config,budget,adapter))
            ctrl=app.controller(app.stores.temporary);original=ctrl.handle_interaction
            def interrupted(tenant,request,**kwargs):
                result=original(tenant,request,**kwargs)
                if request.get('development_chat'):raise RuntimeError('simulated lost controller return after dispatch')
                return result
            ctrl.handle_interaction=interrupted
            result=smoke(app,json.loads(CHECKPOINT.read_text()))
            self.assertEqual(result['budget']['request_count'],1);self.assertEqual(result['attempts_recorded'],0)
            self.assertIsNone(result['live_calls']);self.assertIsNone(result['aggregate_calls'])
            app.close();budget.close()

class ArtifactRedirectTests(unittest.TestCase):
    def test_signed_blob_request_never_receives_github_bearer(self):
        import io,json
        from unittest.mock import patch
        from urllib.error import HTTPError
        from email.message import Message
        from scripts.smoke_development_chat import download_checkpoint,CHECKPOINT,PRIOR_RUN
        frozen=json.loads(CHECKPOINT.read_text());headers=Message();headers['Location']='https://original-artifact.blob.core.windows.net/fixture'
        class Opener:
            def open(self,request,timeout):
                assert request.get_header('Authorization')=='Bearer original-offline-token'
                raise HTTPError(request.full_url,302,'redirect',headers,None)
        def blob(request,timeout):
            self.assertIsNone(request.get_header('Authorization'));return io.BytesIO(b'original-offline-zip')
        meta={'expired':False,'workflow_run':{'id':PRIOR_RUN,'head_sha':frozen['source_commit']}}
        with patch('urllib.request.build_opener',return_value=Opener()),patch('urllib.request.urlopen',side_effect=blob),patch('scripts.smoke_development_chat.verify_checkpoint',return_value=frozen) as verify:
            result=download_checkpoint('https://api.github.com/repos/haohongfei2001-png/hcl-assistant','original-offline-token',lambda _:meta)
            self.assertEqual(result,frozen);verify.assert_called_once_with(b'original-offline-zip')
