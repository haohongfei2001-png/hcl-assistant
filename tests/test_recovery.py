import tempfile
import unittest
from pathlib import Path
from apps.api.server import Application
from packages.store.pagination import page
from packages.store.ledger import Fault


class RecoveryTests(unittest.TestCase):
    def test_restart_pending_run_unknown_no_auto_transport_and_replay_seq(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=str(Path(tmp)/'state.sqlite');app=Application(path);s=app.stores.persistent;c=s.conversation('a')['id'];ctrl=app.controller(s)
            request={'scope':{'conversation_id':c,'topic_id':None},'event':{'text':'synthetic pending'},'expected_state_version':0,'idempotency_key':'pending'}
            run=ctrl.handle_interaction('a',request,defer=True);app.close()
            restored=Application(path);ctrl=restored.controller(restored.stores.persistent);actual=ctrl.read('a',run['run_id'])
            self.assertEqual(actual['run_receipt']['outcome'],'UNKNOWN');self.assertFalse(actual['pending']);self.assertEqual(ctrl.adapter.invocations,0)
            self.assertEqual(len(restored.stores.persistent.history('a',c)),1);self.assertEqual(actual['stream'][-1]['seq'],3)
            self.assertEqual(ctrl.handle_interaction('a',request)['run_id'],run['run_id']);self.assertEqual(ctrl.adapter.invocations,0);restored.close()
    def test_opaque_cursor_scope_version_and_policy_bound(self):
        first=page([1,2,3],'a',1,0,2,scope='Topic')
        self.assertEqual(page([1,2,3],'a',1,0,2,first['next_cursor'],scope='Topic')['items'],[3])
        for tenant,version,policy,scope in [('b',1,0,'Topic'),('a',2,0,'Topic'),('a',1,1,'Topic'),('a',1,0,'other')]:
            with self.assertRaises(Fault):page([1,2,3],tenant,version,policy,2,first['next_cursor'],scope)
