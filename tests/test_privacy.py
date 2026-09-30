import shutil
from pathlib import Path
from tests.test_revision import RevisionTests
from packages.policy.privacy import PolicyContext
from packages.store.ledger import Ledger, Fault


class PrivacyTests(RevisionTests):
    def setUp(self):
        super().setUp(); self.ctx=PolicyContext(self.s)

    def test_stop_delete_history_summary_and_restore(self):
        a=self.add('SYNTHETIC_REMOVABLE_PHRASE'); d=self.add('DERIVED_REMOVABLE_PHRASE','SYSTEM_INTERPRETATION',support_groups=[[a]])
        summary=self.ctx.summary('a',self.c); old=self.s.version('a')
        backup=str(Path(self.tmp.name)/'backup.sqlite'); backup_db=__import__('sqlite3').connect(backup); self.s.db.backup(backup_db); backup_db.close()
        self.revise('STOP_USING',a); self.assertEqual(self.ctx.selection('a',self.c)['records'],[])
        self.assertEqual(self.ctx.project('a',self.c,version=old),[])
        self.revise('DELETE',a)
        self.assertEqual(self.ctx.get('a',a,old)['content'],'')
        self.assertEqual(self.s.list('a','summary'),[])
        self.assertNotIn('original authored',self.s.db.execute('SELECT body FROM sources').fetchone()['body'])
        self.s.db.execute('VACUUM')
        raw=Path(self.path).read_bytes(); self.assertNotIn(b'SYNTHETIC_REMOVABLE_PHRASE',raw); self.assertNotIn(b'DERIVED_REMOVABLE_PHRASE',raw)
        tombstones=[r['id'] for r in self.s.db.execute('SELECT id FROM tombstones')]
        restored=Ledger(backup); ctx=PolicyContext(restored)
        with restored.transaction(): ctx.replay_deletions('a',tombstones)
        self.assertEqual(ctx.get('a',a)['content'],''); self.assertEqual(ctx.get('a',d)['content'],''); restored.close()

    def test_expiry_not_negation_and_permission_dimensions(self):
        a=self.add(retention_policy={'expires_at':'2020-01-01T00:00:00+00:00'},person_access_events=[])
        self.assertEqual(self.ctx.selection('a',self.c)['records'],[])
        self.assertEqual(self.ctx.get('a',a)['lifecycle_status'],'ACTIVE')
        self.assertEqual(self.ctx.get('a',a)['epistemic_status'],'REPORTED')
        self.assertEqual(self.ctx.project('a',self.c,perspective='reader'),[])
        with self.assertRaises(Fault): self.s.conversation('a',memory='EXPLICIT_CROSS_TOPIC')
        with self.assertRaises(Fault): self.ctx.selection('other',self.c)

    def test_correction_and_counterevidence_closure_not_top_k(self):
        a=self.add('old guess','USER_GUESS'); challenge=self.add('counterevidence',challenges=[a])
        receipt=self.revise('CORRECT',a,new_record={'kind':'USER_REPORTED_EVENT','content':'corrected','source_refs':self.source})
        selection=self.ctx.selection('a',self.c,seeds=[a])
        self.assertIn(challenge,selection['record_ids']); self.assertTrue(selection['correction_ids'])
        with self.assertRaises(Fault): self.ctx.selection('a',self.c,limit=1)
        self.assertNotIn(a,selection['record_ids'])

    def test_independent_sources_survive_delete(self):
        a=self.add('remove')
        new=self.s.append('a',self.c,None,'independent synthetic source',self.s.version('a'),'independent')['event']['source_refs']
        b=self.add('retain',source_refs=new)
        self.revise('DELETE',a)
        self.assertIn(b,self.ctx.selection('a',self.c)['record_ids'])
        self.assertEqual(self.ctx.get('a',b)['content'],'retain')

    def test_temporary_no_persistent_copy_and_restart_loss(self):
        from packages.store.registry import Stores
        registry=Stores(self.s)
        c=registry.conversation('a',memory='TEMPORARY')['id']; volatile=registry.for_conversation('a',c)
        volatile.append('a',c,None,'VOLATILE_SYNTHETIC_BODY',0,'temporary')
        self.assertNotIn(b'VOLATILE_SYNTHETIC_BODY',Path(self.path).read_bytes())
        self.assertNotIn(c,[x['id'] for x in self.s.list('a','conversation')])
        volatile.close(); registry=Stores(self.s)
        with self.assertRaises(Fault): registry.for_conversation('a',c)
        registry.temporary.close()
