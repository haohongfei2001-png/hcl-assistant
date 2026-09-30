import json
import unittest
from packages.store.ledger import Ledger
from packages.controller.interaction import Controller
from packages.explain.projection import project


class ExplainTests(unittest.TestCase):
    def setUp(self): self.s=Ledger();self.c=self.s.conversation('a')['id'];self.ctrl=Controller(self.s)
    def tearDown(self): self.s.close()
    def say(self,text,**event):
        return self.ctrl.handle_interaction('a',{'scope':{'conversation_id':self.c,'topic_id':None},'expected_state_version':self.s.version('a'),'idempotency_key':str(self.s.version('a')),'event':{'text':text,**event}})
    def test_frozen_bindings_no_calls_and_new_run(self):
        old=self.say('报告[青]：周一收到通知');identity=old['accepted_change_ids'][0]
        before=self.ctrl.adapter.invocations; explain=project(self.ctrl.read('a',old['run_id']))
        self.assertEqual(self.ctrl.adapter.invocations,before);self.assertEqual(explain['answer_id'],old['answer']['answer_id']);self.assertEqual(explain['snapshot_id'],old['snapshot_id'])
        new=self.say('更正：周一收到通知 => 周二收到通知')
        historical=project(self.ctrl.read('a',old['run_id']))
        self.assertEqual(historical['judgment_basis'],explain['judgment_basis']);self.assertTrue(historical['outdated'])
        self.assertNotEqual(old['run_id'],new['run_id']);self.assertNotEqual(old['snapshot_id'],new['snapshot_id'])
    def test_policy_redaction_and_corrected_copy_purge(self):
        old=self.say('报告[青]：SYNTHETIC_DELETABLE_BODY');identity=old['accepted_change_ids'][0]
        corrected=self.say('kind correction',revisions=[{'action':'CORRECT','target_ids':[identity],'new_record':{'kind':'USER_GUESS','content':'SYNTHETIC_DELETABLE_BODY'}}])
        successor=next(i for i in corrected['accepted_change_ids'] if self.ctrl.context.get('a',i)['kind']=='USER_GUESS')
        self.say('remove',revisions=[{'action':'DELETE','target_ids':[identity]}])
        self.assertEqual(self.ctrl.context.get('a',successor)['content'],'')
        redacted=project(self.ctrl.read('a',old['run_id']));self.assertEqual(redacted['answer_id'],old['answer']['answer_id']);self.assertTrue(redacted['redactions'])
        self.assertNotIn('SYNTHETIC_DELETABLE_BODY',json.dumps(self.s.list('a','run')))
