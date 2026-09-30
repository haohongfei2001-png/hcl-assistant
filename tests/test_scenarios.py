"""Original synthetic authored trajectories. No external/research fixtures."""
import tempfile
import unittest
from pathlib import Path
from packages.store.ledger import Ledger
from packages.controller.interaction import Controller


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=str(Path(self.tmp.name)/'state.sqlite'); self.s=Ledger(self.path)
        self.topic=self.s.topic('a','原创轨迹')['id']; self.c=self.s.conversation('a',topic_id=self.topic,memory='TOPIC')['id']; self.ctrl=Controller(self.s)
    def tearDown(self): self.s.close(); self.tmp.cleanup()
    def say(self, text):
        return self.ctrl.handle_interaction('a',{'scope':{'conversation_id':self.c,'topic_id':self.topic},'event':{'text':text},'allowed_memory_scope':'TOPIC','expected_state_version':self.s.version('a'),'idempotency_key':str(self.s.version('a'))})
    def assert_bindings(self,run):
        for claim in run['answer']['claim_bindings']:
            self.assertEqual(claim['claim'],self.ctrl.context.get('a',claim['record_id'])['content'])
        self.assertEqual(run['run_receipt']['usage']['provider_calls'],0)
        self.assertNotIn('%',run['answer']['text'])

    def test_cooperation_late_info_retraction_and_other_goal(self):
        self.say('报告[林]：林周三才收到会议改期信息')
        guess=self.say('猜测[乔]：乔没有回复可能是不想合作')
        self.say('报告[我]：周五要完成演示')
        repeated=self.say('猜测[乔]：乔没有回复可能是不想合作')
        self.assertIn('猜测仍是',repeated['answer']['text'])
        first=self.ctrl.context.get('a',guess['accepted_change_ids'][0]); repeat=self.ctrl.context.get('a',repeated['accepted_change_ids'][0])
        self.assertEqual(first['provenance_roots'],repeat['provenance_roots'])
        self.assertEqual(repeat['repetition_of'],first['record_id'])
        self.assertEqual(self.ctrl.context.get('a',guess['accepted_change_ids'][0])['kind'],'USER_GUESS')
        correction=self.say('更正：林周三才收到会议改期信息 => 林周四才收到会议改期信息；2+2')
        self.assertEqual(correction['answer']['text'],'2 + 2 = 4。');self.assertEqual(self.ctrl.context.get('a',correction['accepted_change_ids'][0])['lifecycle_status'],'SUPERSEDED')
        # Duplicate matching targets require clarification; never change all guesses by name.
        unresolved=self.say('撤回：乔没有回复可能是不想合作');self.assertTrue(unresolved['unresolved_updates'])
        record=guess['accepted_change_ids'][0]
        request={'scope':{'conversation_id':self.c,'topic_id':self.topic},'event':{'text':'撤回猜测','revisions':[{'action':'RETRACT','target_ids':[record]}]},'allowed_memory_scope':'TOPIC','expected_state_version':self.s.version('a'),'idempotency_key':'retract'}
        self.ctrl.handle_interaction('a',request)
        records=self.ctrl.context.project('a',self.c,self.topic)
        self.assertIn('周五要完成演示',[r['content'] for r in records]);self.assert_bindings(repeated)
        self.assertTrue(self.ctrl.read('a',guess['run_id'])['outdated']);self.assertEqual(self.ctrl.read('a',guess['run_id'])['answer']['text'],guess['answer']['text'])

    def test_goal_role_self_report_and_multi_session_restart(self):
        self.say('报告[安]：这周临时承担值班角色')
        report=self.say('自述[安]：我希望留出时间学习')
        self.assertIn('自述记录的是表达',report['answer']['text'])
        self.s.close();self.s=Ledger(self.path);self.ctrl=Controller(self.s)
        self.c=self.s.conversation('a',topic_id=self.topic,memory='TOPIC')['id']
        later=self.say('报告[安]：值班安排已结束');self.assertIn('留出时间学习',later['answer']['text']);self.assert_bindings(later)
        old=self.ctrl.context.get('a',report['accepted_change_ids'][0]);self.assertIsNone(old['valid_time']['start']);self.assertEqual(old['person_access_events'],[])
        self.say('撤回：我希望留出时间学习');self.assertNotIn(old['record_id'],self.ctrl.context.selection('a',self.c,self.topic)['record_ids'])

    def test_concept_hypothesis_returns_to_actual_and_uncovered_chinese(self):
        original=self.say('概念[策]：这里的公平指按投入分配')
        self.say('概念[伊]：这里的公平指按需要分配')
        hypothetical=self.say('假设：这里的公平指按投入分配 => 如果按需要分配')
        self.assertEqual(self.ctrl.context.get('a',hypothetical['accepted_change_ids'][0])['kind'],'HYPOTHETICAL')
        actual=self.say('2+2');self.assertNotIn('如果按需要分配',[r['content'] for r in actual['selected_context']['records']])
        ambiguous=self.say('他说她其实不想那样，你知道吧');self.assertTrue(ambiguous['unresolved_updates']);self.assertEqual(ambiguous['accepted_change_ids'],[])
        self.assert_bindings(original)
        mixed=self.say('更正：找不到的记录 => 新的说法；2+2');self.assertTrue(mixed['unresolved_updates']);self.assertEqual(mixed['answer']['text'],'2 + 2 = 4。')
