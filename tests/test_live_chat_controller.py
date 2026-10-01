"""D1 vertical-slice contract using fake transport only; never live provider calls."""
import copy
import json
import os
import threading
import unittest
from types import SimpleNamespace
from packages.adapter.deepseek import DeepSeekResult
from packages.controller.interaction import Controller
from packages.controller.live_chat import LiveChat
from packages.explain.projection import project
from packages.store.ledger import Ledger, Fault
from packages.runtime_bridge.bridge import RuntimeBridge

class Budget:
    def __init__(self):self.calls=[];self.finished=[]
    def reserve(self,*args):self.calls.append(args);return SimpleNamespace(granted=True)
    def finish(self,*args,**kwargs):self.finished.append((args,kwargs))

class Adapter:
    model='explicit-test-model'
    def __init__(self):self.messages=[];self.outcome='SUCCEEDED';self.answer='这是自然中文测试回答。';self.hook=None
    def generate(self,messages,*,max_tokens,cancel_event,on_delta):
        self.messages.append(copy.deepcopy(messages))
        if self.hook:self.hook()
        on_delta(self.answer)
        return DeepSeekResult(self.outcome,self.answer,self.model,actual_model=self.model,send_state='sent',usage={'prompt_tokens':30,'completion_tokens':12},finish_reason='stop')

class LiveChatTests(unittest.TestCase):
    def setUp(self):
        self.store=Ledger();self.tenant='synthetic-demo-a';self.c=self.store.conversation(self.tenant,memory='TEMPORARY')['id'];self.adapter=Adapter();self.budget=Budget()
        self.service=LiveChat(SimpleNamespace(max_output_tokens=512),self.budget,self.adapter)
        self.ctrl=Controller(self.store,live_chat_service=self.service)
    def tearDown(self):self.store.close()
    def say(self,text,live=True,defer=False,**event):
        return self.ctrl.handle_interaction(self.tenant,{'scope':{'conversation_id':self.c},'expected_state_version':self.store.version(self.tenant),'idempotency_key':str(self.store.version(self.tenant)),'development_chat':live,'synthetic_input_confirmed':True,'event':{'text':text,**event}},defer=defer)
    def test_ordinary_chinese_controller_answer_receipt_and_explain(self):
        run=self.say('请帮我构思一个虚构纸灯活动')
        self.assertEqual(run['answer']['text'],self.adapter.answer);self.assertEqual(run['run_receipt']['actual_treatment'],'NO_TREATMENT')
        self.assertEqual(run['run_receipt']['provider']['actual_model'],self.adapter.model)
        self.assertIsNone(run['run_receipt']['usage']['cost']['amount']);self.assertEqual(run['run_receipt']['usage']['provider_calls'],1)
        self.assertEqual(project(run)['source_links'],[]);self.assertEqual(len(self.budget.calls),1)
    def test_followup_uses_permitted_original_input_not_generated_memory(self):
        first=self.say('虚构活动的纸灯是蓝色')
        second=self.say('刚才说的纸灯是什么颜色？')
        prompt=json.dumps(self.adapter.messages[-1],ensure_ascii=False)
        self.assertIn('纸灯是蓝色',prompt);self.assertNotIn(self.adapter.answer,prompt)
        self.assertEqual(second['history_source_refs'],[first['input_source_ref']])
        self.assertEqual(self.ctrl.context.records(self.tenant),{})
    def test_delete_unparsed_history_redacts_dependent_answer_and_future_prompt(self):
        first=self.say('原创秘密标记LANTERN_CANARY')
        second=self.say('请沿用刚才的设定')
        self.say('删除',live=False,type='revision',revisions=[{'action':'DELETE','target_ids':[first['input_source_ref']['source_id']]}])
        old=self.ctrl.read(self.tenant,second['run_id']);self.assertTrue(old['redacted']);self.assertIsNone(old['answer'])
        self.say('新的合成话题');self.assertNotIn('LANTERN_CANARY',json.dumps(self.adapter.messages[-1]))
    def test_stop_history_redacts_derivative(self):
        first=self.say('原创背景STOP_CANARY');second=self.say('继续')
        self.say('停止',live=False,type='revision',revisions=[{'action':'STOP_USING','target_ids':[first['input_source_ref']['source_id']]}])
        self.assertTrue(self.ctrl.read(self.tenant,second['run_id'])['redacted'])
    def test_correction_replaces_prompt_record_without_replaying_old_source(self):
        self.say('报告[虚构人]：纸灯是蓝色',live=False)
        self.say('更正：纸灯是蓝色 => 纸灯是红色',live=False)
        self.adapter.answer='现在是红色。[S1]';run=self.say('现在是什么颜色？')
        prompt=json.dumps(self.adapter.messages[-1],ensure_ascii=False)
        # The explicit correction message remains history, but superseded original report does not.
        self.assertNotIn('报告[虚构人]：纸灯是蓝色',prompt);self.assertIn('纸灯是红色',prompt)
        self.assertTrue(run['answer']['citation_refs']);self.assertTrue(project(run)['source_links'])
    def test_stale_during_stream_never_publishes_or_keeps_deltas(self):
        self.adapter.hook=lambda:self.say('更改背景',live=False)
        run=self.say('准备回答')
        self.assertIsNone(run['answer']);self.assertFalse(any(e['type'].startswith('answer.') for e in run['stream']))
        self.assertEqual(len(self.budget.finished),1)
    def test_failure_and_partial_not_masked_and_paid_retry_refused(self):
        for outcome in ['FAILED','PARTIAL','UNKNOWN']:
            self.adapter.outcome=outcome;run=self.say('合成失败测试'+outcome)
            self.assertIsNone(run['answer']);self.assertEqual(run['run_receipt']['outcome'],outcome)
            with self.assertRaises(Fault):self.ctrl.retry(self.tenant,run['run_id'],'paid-retry')
    def test_missing_service_and_unconfirmed_input_make_zero_calls(self):
        with self.assertRaises(Fault):Controller(self.store).handle_interaction(self.tenant,{'scope':{'conversation_id':self.c},'development_chat':True,'event':{'text':'合成'}})
        with self.assertRaises(Fault):self.ctrl.handle_interaction(self.tenant,{'scope':{'conversation_id':self.c},'development_chat':True,'event':{'text':'合成'}})
        self.assertEqual(self.adapter.messages,[])
    def test_no_mock_capability_is_advertised_as_real(self):
        base=self.say('报告[人]：原创',live=False)
        record=base['selected_context']['record_ids'][0]
        self.say('原创解释',live=False,records=[{'kind':'SYSTEM_INTERPRETATION','content':'原创解释','support_groups':[[record]]}])
        run=self.say('分析一下');self.assertEqual(run['selected_capability_ids'],[]);self.assertEqual(run['run_receipt']['capabilities'],[])
    @unittest.skipUnless(os.environ.get('HCL_DEVELOPMENT_ARTIFACT'),'fixed runtime required')
    def test_actual_provider_free_bridge_preparation_bound_to_fake_answer(self):
        self.ctrl.development_bridge=RuntimeBridge(os.environ['HCL_DEVELOPMENT_ARTIFACT'])
        self.adapter.answer='Ada explicitly expressed belief that the workshop starts Friday. [HCL1]'
        run=self.ctrl.handle_interaction(self.tenant,{'scope':{'conversation_id':self.c},'idempotency_key':'bridge','expected_state_version':0,'development_chat':True,'synthetic_input_confirmed':True,'event':{'text':'Ada said, "I believe that the workshop starts Friday."'},'development_execution':{'schema_version':'1.0','capability_id':'belief_interpretation','query':'What does Ada believe?','input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}})
        self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED')
        self.assertTrue(run['operation_receipts'][0]['used_in_answer']);self.assertTrue(project(run)['source_links'])
        self.assertIn('HCL1',json.dumps(self.adapter.messages[-1]));self.assertEqual(run['development_result']['provider_calls'],0)

if __name__=='__main__':unittest.main()
