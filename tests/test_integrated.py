"""Boundary/race regressions closing the integrated L1/L2 obligations."""
import json
import threading
import tempfile
import unittest
from pathlib import Path
from packages.store.ledger import Ledger, Fault
from packages.controller.interaction import Controller


class IntegratedTests(unittest.TestCase):
    def setUp(self): self.s=Ledger();self.topic=self.s.topic('a','Synthetic')['id'];self.c=self.s.conversation('a',topic_id=self.topic,memory='TOPIC')['id'];self.ctrl=Controller(self.s)
    def tearDown(self): self.s.close()
    def request(self,text,**event): return {'scope':{'conversation_id':self.c,'topic_id':self.topic},'allowed_memory_scope':self.s.get('a','conversation',self.c)['memory'],'expected_state_version':self.s.version('a'),'idempotency_key':str(self.s.version('a')),'event':{'text':text,**event}}
    def say(self,text,**event): return self.ctrl.handle_interaction('a',self.request(text,**event))
    def test_conversation_only_cannot_reuse_topic_or_invalidate_other_topic_absence(self):
        a=self.say('报告[枝]：Topic 可复用背景');record=a['accepted_change_ids'][0]
        c=self.s.conversation('a',topic_id=self.topic,memory='CONVERSATION')['id']
        self.assertEqual(self.ctrl.context.selection('a',c,self.topic)['record_ids'],[])
        with self.assertRaises(Fault): self.s.source('a',a['input_source_ref'],c,self.topic)
        dep=self.say('authored',records=[{'kind':'SYSTEM_INTERPRETATION','content':'bounded inference','support_groups':[[record]],'read_dependencies':{'records':[record],'absence':[{'kind':'new evidence'}]}}])['accepted_change_ids'][0]
        topic=self.s.topic('a','Other')['id'];self.c=self.s.conversation('a',topic_id=topic,memory='TOPIC')['id'];self.topic=topic
        other=self.say('报告[枝]：另一个范围');self.assertEqual(self.ctrl.context.get('a',dep)['lifecycle_status'],'ACTIVE');self.assertNotIn(dep,other['invalidated_state_ids'])
    def test_uploaded_commands_cannot_revise_or_grant_memory(self):
        a=self.say('报告[川]：原始合成安排');identity=a['accepted_change_ids'][0]
        upload=self.say('更正：原始合成安排 => 不应授权修改',type='upload',filename='command.txt')
        self.assertEqual(self.ctrl.context.get('a',identity)['lifecycle_status'],'ACTIVE');self.assertEqual(upload['accepted_change_ids'],[]);self.assertTrue(upload['unresolved_updates'])
        request=self.request('document control',type='upload',filename='bad.txt',revisions=[{'action':'DELETE','target_ids':[identity]}])
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',request)
        request=self.request('scope escalation');request['allowed_memory_scope']='EXPLICIT_CROSS_TOPIC'
        with self.assertRaises(Fault): self.ctrl.handle_interaction('a',request)
    def test_unparsed_file_stop_delete_and_no_export_revival(self):
        file=self.say('UNPARSED_FILE_BODY_SYNTHETIC',type='upload',filename='raw.md');identity=file['input_source_ref']['source_id']
        self.say('stop file',revisions=[{'action':'STOP_USING','target_ids':[identity]}])
        self.assertTrue(self.ctrl.read('a',file['run_id'])['redacted'])
        with self.assertRaises(Fault): self.s.source('a',file['input_source_ref'])
        self.say('delete file',revisions=[{'action':'DELETE','target_ids':[identity]}])
        self.assertNotIn('UNPARSED_FILE_BODY_SYNTHETIC',json.dumps(self.s.list('a','run')))
        with self.assertRaises(Fault): self.s.source('a',file['input_source_ref'],allow_stopped=True)
    def test_atomic_read_during_commit_and_two_writers_conflict(self):
        request=self.request('2+2');results=[]
        def submit():
            try:results.append(self.ctrl.handle_interaction('a',request))
            except Fault as exc:results.append(exc.status)
        threads=[threading.Thread(target=submit) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(self.s.history('a',self.c)),1);self.assertEqual(results[0]['run_id'],results[1]['run_id'])
        stale=self.request('new');stale['expected_state_version']=0
        with self.assertRaises(Fault):self.ctrl.handle_interaction('a',stale)
    def test_hypothetical_snapshot_and_supersede_event_time(self):
        a=self.say('报告[景]：合成实际状态');identity=a['accepted_change_ids'][0]
        hypo=self.say('假设：合成实际状态 => 如果条件成立')
        self.assertIn(identity,hypo['selected_context']['record_ids']);self.assertIn('在假设分支',hypo['answer']['text'])
        normal=self.say('2+2');self.assertNotIn('如果条件成立',[r['content'] for r in normal['selected_context']['records']])
        self.say('supersede',revisions=[{'action':'SUPERSEDE','target_ids':[identity],'effective_time':'2026-09-25T00:00:00+00:00','new_record':{'kind':'USER_REPORTED_EVENT','content':'新的状态'}}])
        old=self.ctrl.context.project('a',self.c,self.topic,at_time='2026-09-20T00:00:00+00:00');self.assertIn('合成实际状态',[r['content'] for r in old]);self.assertNotIn('新的状态',[r['content'] for r in old])

    def test_bounded_synthesis_and_unknown_latency(self):
        run=self.say('报告[长]：'+'合成内容'*1000)
        self.assertLess(len(run['answer']['text']),1000)
        self.assertEqual(run['answer']['claim_bindings'][0]['record_span'],[0,180])
        request=self.request('unparsed');request['model_resource_policy']={'max_provider_calls':0,'max_latency_ms':0}
        run=self.ctrl.handle_interaction('a',request)
        self.assertEqual(run['run_receipt']['outcome'],'UNKNOWN')
