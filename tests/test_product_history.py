"""Original provider-free R13–R16 history/change projection contracts."""
import json
import unittest
from apps.api.server import Application
from packages.explain.product import changes,conversation,search
from packages.store.ledger import Fault
class ProductHistoryTests(unittest.TestCase):
    def setUp(self):
        self.app=Application();self.tenant='history-a';self.c=self.app.stores.conversation(self.tenant)['id'];self.store=self.app.stores.for_conversation(self.tenant,self.c);self.ctrl=self.app.controller(self.store)
    def tearDown(self):self.app.close()
    def say(self,text,**event):return self.ctrl.handle_interaction(self.tenant,{'scope':{'conversation_id':self.c},'expected_state_version':self.store.version(self.tenant),'idempotency_key':str(self.store.version(self.tenant)),'event':{'text':text,**event}})
    def test_no_insight_from_ordinary_version_increment(self):
        a=self.say('报告[榛]：原创纸灯周四送达');b=self.say('2+2')
        self.assertEqual(changes(self.ctrl,self.tenant,a),[]);self.assertEqual(changes(self.ctrl,self.tenant,b),[])
    def test_explicit_change_binds_old_new_without_rewriting_history(self):
        old=self.say('报告[榛]：P1_ORIGINAL_BEFORE_PEBBLE');new=self.say('更正：P1_ORIGINAL_BEFORE_PEBBLE => P1_CORRECTED_AFTER_PEBBLE')
        delta=changes(self.ctrl,self.tenant,new);self.assertEqual(len(delta),1);self.assertEqual(delta[0]['old'][0]['content'],'P1_ORIGINAL_BEFORE_PEBBLE');self.assertEqual(delta[0]['new'][0]['content'],'P1_CORRECTED_AFTER_PEBBLE')
        self.assertEqual(self.ctrl.read(self.tenant,old['run_id'])['input_text'],old['input_text'])
        hits=search(self.app,self.tenant,'P1_ORIGINAL_BEFORE_PEBBLE');self.assertTrue(hits);self.assertTrue(any(c['new'][0]['content']=='P1_CORRECTED_AFTER_PEBBLE' for h in hits for c in h['related_changes'] if c['new']))
    def test_same_content_correction_is_not_material_insight(self):
        self.say('报告[榛]：原创相同内容');run=self.say('更正：原创相同内容 => 原创相同内容');self.assertEqual(changes(self.ctrl,self.tenant,run),[])
    def test_deleted_search_and_export_do_not_revive_original_body(self):
        self.say('报告[榛]：P1_DELETE_FERN');self.say('报告[杉]：INDEPENDENT_ORIGINAL');record=next(r for r in self.ctrl.context.project(self.tenant,self.c) if r['content']=='P1_DELETE_FERN');self.say('明确删除合成记录',type='revision',revisions=[{'action':'DELETE','target_ids':[record['record_id']]}])
        self.assertEqual(search(self.app,self.tenant,'P1_DELETE_FERN'),[]);encoded=json.dumps(conversation(self.ctrl,self.tenant,self.c));self.assertNotIn('P1_DELETE_FERN',encoded);self.assertIn('INDEPENDENT_ORIGINAL',encoded)
    def test_cross_tenant_and_query_limits(self):
        other=self.app.stores.conversation('other')['id'];store=self.app.stores.for_conversation('other',other);self.app.controller(store).handle_interaction('other',{'scope':{'conversation_id':other},'expected_state_version':store.version('other'),'idempotency_key':'1','event':{'text':'报告[乙]：OTHER_TENANT_CANARY'}})
        self.assertEqual(search(self.app,self.tenant,'OTHER_TENANT_CANARY'),[])
        for query in ('',' ' ,'a'*201):
            with self.assertRaises(Fault):search(self.app,self.tenant,query)
    def test_hypothesis_changes_are_not_actual_writeback(self):
        self.say('报告[榛]：原创实际蓝纸');run=self.say('假设：原创实际蓝纸 => 原创假设白纸');delta=changes(self.ctrl,self.tenant,run);self.assertFalse(delta[0]['actual_changed']);self.assertEqual(delta[0]['action'],'HYPOTHETICAL_BRANCH');self.assertNotIn('原创假设白纸',json.dumps(self.ctrl.context.project(self.tenant,self.c)))
