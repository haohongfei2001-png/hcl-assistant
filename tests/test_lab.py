import json
import unittest
from packages.store.ledger import Ledger, Fault
from packages.controller.interaction import Controller
from packages.controller.lab import inspect


class LabTests(unittest.TestCase):
    def setUp(self): self.s=Ledger();self.c=self.s.conversation('a')['id'];self.ctrl=Controller(self.s)
    def tearDown(self): self.s.close()
    def say(self,text,**event): return self.ctrl.handle_interaction('a',{'scope':{'conversation_id':self.c,'topic_id':None},'event':{'text':text,**event},'expected_state_version':self.s.version('a'),'idempotency_key':str(self.s.version('a'))})
    def test_read_only_identity_usage_and_failure_records(self):
        direct=self.say('2+2');before=self.s.version('a');calls=self.ctrl.adapter.invocations
        lab=inspect(self.ctrl,'a',direct['run_id']);self.assertTrue(lab['read_only']);self.assertFalse(lab['compare_enabled']);self.assertEqual(lab['mode'],'MOCK')
        self.assertEqual(self.s.version('a'),before);self.assertEqual(self.ctrl.adapter.invocations,calls)
        failed=self.say('unparsed',simulation='failed');unknown=self.say('unparsed',simulation='unknown')
        self.assertEqual(inspect(self.ctrl,'a',failed['run_id'])['run']['run_receipt']['outcome'],'FAILED')
        self.assertEqual(inspect(self.ctrl,'a',unknown['run_id'])['run']['run_receipt']['outcome'],'UNKNOWN')
        self.assertIsNone(unknown['run_receipt']['usage']['reasoning_tokens']);self.assertEqual(unknown['run_receipt']['usage']['provider_calls'],0)
        with self.assertRaises(Fault): inspect(self.ctrl,'b',direct['run_id'])
    def test_export_after_delete_has_no_body(self):
        report=self.say('报告[合成人]：PURGE_FROM_EXPORT');record=report['accepted_change_ids'][0]
        self.say('delete',revisions=[{'action':'DELETE','target_ids':[record]}])
        exported=inspect(self.ctrl,'a',report['run_id']);self.assertNotIn('PURGE_FROM_EXPORT',json.dumps(exported));self.assertTrue(exported['run']['redacted'])
