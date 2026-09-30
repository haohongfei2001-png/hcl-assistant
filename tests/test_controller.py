import unittest
from packages.store.ledger import Ledger, Fault
from packages.controller.interaction import Controller


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.s=Ledger(); self.c=self.s.conversation('a')['id']; self.ctrl=Controller(self.s)
    def tearDown(self): self.s.close()
    def req(self, text='2+2', **event):
        return {'scope':{'conversation_id':self.c,'topic_id':None,'branch_id':'actual'},'expected_state_version':self.s.version('a'),'allowed_memory_scope':'CONVERSATION','source_refs':[],'model_resource_policy':{'max_provider_calls':0},'idempotency_key':str(self.s.version('a')),'event':{'type':'message','text':text,**event}}

    def test_direct_governed_idempotent_reconnect(self):
        request=self.req(); run=self.ctrl.handle_interaction('a',request)
        self.assertEqual(run['route'],'DIRECT'); self.assertEqual(run['answer']['text'],'2 + 2 = 4。')
        self.assertTrue(run['run_receipt']['controller_receipt_id'])
        again=self.ctrl.handle_interaction('a',request); self.assertEqual(again['run_id'],run['run_id'])
        self.assertEqual(self.ctrl.adapter.invocations,0)
        events=self.ctrl.events('a',run['run_id']); self.assertEqual([e['seq'] for e in events],list(range(1,len(events)+1)))
        self.assertEqual(self.ctrl.events('a',run['run_id'],events[-1]['seq']),[])

    def test_correction_before_arithmetic_cancel_keeps_changes(self):
        a=self.ctrl.handle_interaction('a',self.req('authored',records=[{'kind':'USER_GUESS','content':'A'}]))['accepted_change_ids'][0]
        run=self.ctrl.handle_interaction('a',self.req('更正昨天为B；2+2',revisions=[{'action':'CORRECT','target_ids':[a],'new_record':{'kind':'USER_REPORTED_EVENT','content':'B'}}]),defer=True)
        self.assertEqual(self.ctrl.context.get('a',a)['lifecycle_status'],'SUPERSEDED')
        self.ctrl.cancel('a',run['run_id']); self.ctrl.finish('a',run['run_id'])
        self.assertEqual(self.ctrl.read('a',run['run_id'])['run_receipt']['outcome'],'CANCELLED')
        self.assertIn('B',[r['content'] for r in self.ctrl.context.project('a',self.c)])

    def test_failure_unknown_and_input_survival(self):
        run=self.ctrl.handle_interaction('a',self.req('unparsed',simulation='failed'))
        self.assertEqual(run['run_receipt']['outcome'],'FAILED'); self.assertEqual(len(self.s.history('a',self.c)),1)
        retry=self.ctrl.retry('a',run['run_id'],'retry'); self.assertEqual(retry['run_receipt']['outcome'],'FAILED')
        self.assertNotEqual(run['run_receipt']['attempt_id'],retry['run_receipt']['attempt_id']); self.assertEqual(len(self.s.history('a',self.c)),1)
        u=self.ctrl.handle_interaction('a',self.req('unparsed',simulation='unknown'))
        self.assertEqual(u['run_receipt']['outcome'],'UNKNOWN')
        with self.assertRaises(Fault): self.ctrl.retry('a',u['run_id'],'unsafe')

    def test_no_bypass_budget_scope_half_json(self):
        with self.assertRaises(Fault): self.ctrl.adapter.generate({},'fake')
        bad=self.req(); bad['model_resource_policy']['max_provider_calls']=1
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',bad)
        bad=self.req(); bad['scope']['tenant_id']='b'
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',bad)
        bad=self.req(records=[{'kind':'SYSTEM_INTERPRETATION','content':'bad'}])
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',bad)
        self.assertEqual(self.s.version('a'),0)
        self.assertEqual(self.s.history('a',self.c),[])

    def test_stale_finish_and_deleted_old_run_redaction(self):
        stale=self.ctrl.handle_interaction('a',self.req('2+2'),defer=True)
        self.ctrl.handle_interaction('a',self.req('new'))
        self.ctrl.finish('a',stale['run_id']); self.assertIsNone(self.ctrl.read('a',stale['run_id'])['answer'])
        old=self.ctrl.handle_interaction('a',self.req('SENSITIVE_SYNTHETIC',records=[{'kind':'USER_REPORTED_EVENT','content':'SENSITIVE_SYNTHETIC'}]))
        identity=old['accepted_change_ids'][0]
        self.ctrl.handle_interaction('a',self.req('',revisions=[{'action':'DELETE','target_ids':[identity]}]))
        self.assertTrue(self.ctrl.read('a',old['run_id']).get('redacted'))
        self.assertNotIn('SENSITIVE_SYNTHETIC',__import__('json').dumps(self.ctrl.read('a',old['run_id'])))

    def test_selected_mock_budget_zero_and_current_policy(self):
        base=self.ctrl.handle_interaction('a',self.req('typed report',records=[{'kind':'USER_REPORTED_EVENT','content':'report'}]))
        record=base['accepted_change_ids'][0]
        selected=self.ctrl.handle_interaction('a',self.req('typed interpretation',records=[{'kind':'SYSTEM_INTERPRETATION','content':'possible explanation','support_groups':[[record]]}]))
        self.assertEqual(selected['route'],'SELECTED_COGNITION')
        op=selected['operation_receipts'][0]; self.assertTrue(op['selected']); self.assertTrue(op['executed']); self.assertTrue(op['result_produced']); self.assertFalse(op['cache_reused'])
        request=self.req('unparsed'); request['model_resource_policy']['max_adapter_calls']=0
        before=self.ctrl.adapter.invocations; result=self.ctrl.handle_interaction('a',request)
        self.assertEqual(self.ctrl.adapter.invocations,before); self.assertEqual(result['run_receipt']['usage']['provider_calls'],0)
        pending=self.ctrl.handle_interaction('a',self.req('still pending'),defer=True)
        self.ctrl.handle_interaction('a',self.req('',revisions=[{'action':'STOP_USING','target_ids':[record]}]))
        self.ctrl.finish('a',pending['run_id']); self.assertIsNone(self.ctrl.read('a',pending['run_id'])['answer'])
        bad=self.req(); bad['source_refs']=[base['input_source_ref']]
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',bad)
