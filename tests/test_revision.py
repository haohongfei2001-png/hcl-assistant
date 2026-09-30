import tempfile
import unittest
from pathlib import Path
from packages.store.ledger import Ledger, Fault
from packages.context.revision import Context


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=str(Path(self.tmp.name)/'state.sqlite'); self.s=Ledger(self.path); self.c=self.s.conversation('a')['id']; self.ctx=Context(self.s)
        self.source=self.s.append('a',self.c,None,'original authored synthetic evidence',0,'src')['event']['source_refs']

    def tearDown(self): self.s.close(); self.tmp.cleanup()

    def add(self, content='report', kind='USER_REPORTED_EVENT', **kw):
        cmd={'action':'ADD','new_record':{'kind':kind,'content':content,'source_refs':self.source,**kw},'request_actor':'authenticated_user','idempotency_key':str(self.s.version('a')),'expected_state_version':self.s.version('a')}
        return self.ctx.revise('a',self.c,None,cmd)['changed_ids'][0]

    def revise(self, action, target, **kw):
        cmd={'action':action,'target_ids':[target],'request_actor':'authenticated_user','idempotency_key':str(self.s.version('a')),'expected_state_version':self.s.version('a'),**kw}
        return self.ctx.revise('a',self.c,None,cmd)

    def test_or_of_and_independent_support_and_history(self):
        a=self.add(); b=self.add('independent')
        d=self.add('interpretation','SYSTEM_INTERPRETATION',support_groups=[[a],[b]])
        old=self.s.version('a'); receipt=self.revise('RETRACT',a)
        self.assertEqual(self.ctx.get('a',d)['lifecycle_status'],'ACTIVE')
        self.assertIn(d,receipt['recomputed_ids']); self.assertEqual(self.ctx.get('a',a,old)['lifecycle_status'],'ACTIVE')
        self.assertEqual(self.ctx.get('a',a)['epistemic_status'],'REPORTED')
        self.revise('RETRACT',b); self.assertEqual(self.ctx.get('a',d)['lifecycle_status'],'STALE')
        self.s.close(); self.s=Ledger(self.path); self.ctx=Context(self.s)
        self.assertEqual(self.ctx.get('a',a,old)['content'],'report')

    def test_and_support_absence_and_unrelated_checked(self):
        a=self.add(); b=self.add(); d=self.add('needs both','SYSTEM_INTERPRETATION',support_groups=[[a,b]])
        absence=self.add('no reply yet','SYSTEM_INTERPRETATION',support_groups=[[b]],read_dependencies={'records':[b],'absence':[{'kind':'reply'}]})
        self.revise('RETRACT',a); self.assertEqual(self.ctx.get('a',d)['lifecycle_status'],'STALE')
        self.add('reply'); self.assertEqual(self.ctx.get('a',absence)['lifecycle_status'],'STALE')

    def test_correction_subject_time_and_hypothesis_are_local(self):
        a=self.add(subject_refs=['local-alex'],person_access_events=[{'person_id':'local-alex','learned_at':'2026-09-20T12:00:00+00:00'}])
        same=self.add('different person',subject_refs=['other-alex'])
        self.assertEqual(self.ctx.project('a',self.c,perspective='local-alex',at_time='2026-09-19T12:00:00+00:00'),[])
        r=self.revise('CORRECT',a,new_record={'kind':'USER_GUESS','content':'uncertain','subject_refs':['local-bea'],'source_refs':self.source})
        self.assertEqual(self.ctx.get('a',same)['lifecycle_status'],'ACTIVE')
        self.assertIsNone(self.ctx.get('a',r['changed_ids'][0]).get('disclosure_time'))
        h=self.revise('HYPOTHETICAL_BRANCH',same,new_record={'content':'if this happened','source_refs':self.source})
        self.assertNotIn(h['changed_ids'][0],[x['record_id'] for x in self.ctx.project('a',self.c)])

    def test_family_dedup_rootless_and_conflict(self):
        a=self.add(); b=self.add('mirror','USER_GUESS'); d=self.add('summary','SYSTEM_INTERPRETATION',support_groups=[[a,b]])
        self.assertEqual(len(self.ctx.get('a',d)['provenance_roots']),1)
        with self.assertRaises(Fault): self.add('rootless','SYSTEM_INTERPRETATION',source_refs=[])
        with self.assertRaises(Fault): self.add('cycle','SYSTEM_INTERPRETATION',support_groups=[['self']])
        with self.assertRaises(Fault): self.ctx.revise('a',self.c,None,{'action':'RETRACT','target_ids':[a],'request_actor':'uploaded_source','expected_state_version':self.s.version('a'),'idempotency_key':'bad'})
        with self.assertRaises(Fault): self.ctx.revise('a',self.c,None,{'action':'RETRACT','target_ids':[a],'request_actor':'authenticated_user','expected_state_version':0,'idempotency_key':'stale'})

    def test_supersede_keeps_effective_time_and_add_does_not_overwrite(self):
        a=self.add(); old=self.s.version('a')
        self.revise('SUPERSEDE',a,effective_time='2026-09-30T00:00:00+00:00',new_record={'kind':'USER_REPORTED_EVENT','content':'new','source_refs':self.source})
        self.assertEqual(self.ctx.get('a',a)['effective_time'],'2026-09-30T00:00:00+00:00')
        self.assertEqual(self.ctx.get('a',a,old)['lifecycle_status'],'ACTIVE')
