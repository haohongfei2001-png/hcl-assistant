import tempfile
import unittest
from pathlib import Path
from packages.store.ledger import Ledger, Fault


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name)/'test.sqlite')
        self.store = Ledger(self.path)
        self.topic = self.store.topic('a','合成项目')['id']
        self.c = self.store.conversation('a', topic_id=self.topic)['id']

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def add(self, text='原创 synthetic 内容', key='one', expected=0, **kw):
        return self.store.append('a', self.c, self.topic, text, expected, key, **kw)

    def test_roundtrip_restart_hash_parse_and_history(self):
        result=self.add()
        self.store.close(); self.store=Ledger(self.path)
        self.assertEqual(self.store.history('a',self.c)[0],result['event'])
        self.assertEqual(self.store.source('a',result['event']['source_refs'][0])['text'],'原创 synthetic 内容')
        self.assertEqual(result['source']['parse_source_version'],1)
        self.assertEqual(self.store.version('a'),1)

    def test_idempotency_and_conflict(self):
        a=self.add(); self.assertEqual(a,self.add())
        with self.assertRaises(Fault) as cm: self.add(text='different')
        self.assertEqual(cm.exception.status,409)
        with self.assertRaises(Fault): self.add(key='two')
        self.assertEqual(len(self.store.history('a',self.c)),1)

    def test_half_commit_rollback(self):
        with self.assertRaises(RuntimeError): self.add(fail=True)
        self.assertEqual(self.store.version('a'),0)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM sources').fetchone()[0],0)
        self.add()

    def test_scope_hash_span_and_file_limits(self):
        r=self.add(); ref=r['event']['source_refs'][0]
        with self.assertRaises(Fault): self.store.source('b',ref)
        with self.assertRaises(Fault): self.store.source('a',{**ref,'sha256':'bad'})
        with self.assertRaises(Fault): self.store.source('a',{**ref,'span':[0,999]})
        other=self.store.topic('a','other')['id']
        with self.assertRaises(Fault): self.store.scope('a',self.c,other)
        with self.assertRaises(Fault): self.add(name='bad.pdf', key='bad', expected=1)
        with self.assertRaises(Fault): self.add(text='x'*65537,key='long',expected=1)

    def test_source_versions_preserve_original(self):
        r=self.add()
        with self.store.transaction():
            new=self.store.write_source('a',self.c,self.topic,'new',source_id=r['source']['id'])
        self.assertEqual(new['version'],2)
        self.assertEqual(self.store.source('a',r['event']['source_refs'][0])['text'],'原创 synthetic 内容')
