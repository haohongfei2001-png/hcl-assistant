"""Actual isolated Postgres integration. No external DB or provider may be used.

CI supplies a disposable localhost Postgres service. A local PGlite compatibility
run is useful, but is explicitly not accepted as multi-process locking evidence.
"""
import io
import json
import os
from pathlib import Path
import threading
import time
import unittest
from types import SimpleNamespace
from urllib.parse import urlsplit
from packages.adapter.development_budget import DevelopmentConfig,DevelopmentBudget,BudgetError
from packages.adapter.deepseek import DeepSeekAdapter
from packages.cloud.auth import password_verifier
from packages.cloud.config import CloudConfig
from packages.cloud.postgres import PostgresLedger,TENANT
from packages.cloud.budget import CloudBudget
from packages.cloud.lifecycle import Lifecycle,DurableCancellation
from packages.cloud.temporary import execute as execute_temporary
from packages.store.ledger import Fault
from apps.api.cloud_server import CloudApplication
from tests.support.cloud_transport import CloudFakeTransport as FakeTransport

DSN=os.environ.get('HCLA_TEST_POSTGRES_DSN')
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(DSN,'Disposable local Postgres not configured; required in cloud CI')
class CloudPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg.rows import dict_row
        parsed=urlsplit(DSN)
        if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.path!='/hcla_test': raise ValueError('Disposable localhost hcla_test database required')
        cls.connect=lambda self:psycopg.connect(DSN,autocommit=True,row_factory=dict_row,prepare_threshold=None)
        with psycopg.connect(DSN,autocommit=True) as c:
            if c.execute("SELECT to_regnamespace('hcla')").fetchone()[0] is None:
                c.execute((ROOT/'supabase/migrations/20261001084651_isolated_hcla_cloud.sql').read_text())
            if c.execute("SELECT to_regclass('hcla.trial_budget_policy')").fetchone()[0] is None:
                c.execute((ROOT/'supabase/migrations/20261001174151_bounded_temporary_trial.sql').read_text())
            if c.execute("SELECT to_regclass('hcla.member_sessions')").fetchone()[0] is None:
                c.execute((ROOT/'supabase/migrations/20261001195008_member_accounts_and_entitlements.sql').read_text())
            if c.execute("SELECT to_regclass('hcla.member_recovery')").fetchone()[0] is None:
                c.execute((ROOT/'supabase/migrations/20261001222410_bounded_member_recovery.sql').read_text())
        cls.verifier=password_verifier('offline password fixture')
        cls.config=DevelopmentConfig.from_env({'HCLA_DEEPSEEK_API_KEY':'offline-fixture','HCLA_DEEPSEEK_BASE_URL':'https://api.deepseek.com','HCLA_DEEPSEEK_MODEL':'deepseek-v4-pro','HCLA_DEV_ACCESS_TOKEN':'offline-owner-access-fixture','HCLA_DEV_MAX_REQUESTS':'10','HCLA_DEV_MAX_COST_USD':'100','HCLA_DEV_INPUT_USD_PER_MILLION':'1.32','HCLA_DEV_OUTPUT_USD_PER_MILLION':'3.96','HCLA_DEV_MAX_OUTPUT_TOKENS':'512','HCLA_DEV_BUDGET_ID':'offline-isolated-cloud-grant'})
    def setUp(self):
        self.admin=self.connect()
        tables=self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla' AND tablename!='schema_version'").fetchall()
        self.admin.execute('TRUNCATE '+','.join('hcla.'+row['tablename'] for row in tables)+' RESTART IDENTITY')
        policy=DevelopmentBudget._policy(SimpleNamespace(config=self.config))
        self.admin.execute('INSERT INTO hcla.budget_policy VALUES(1,%s)',(policy,))
        self.open=[]
    def tearDown(self):
        for store in self.open:store.close()
        self.admin.close()
    def store(self):
        connection=self.connect();connection.execute('SET ROLE hcla_app')
        store=PostgresLedger('',connection=connection);self.open.append(store);return store
    def app(self,transport=FakeTransport,runtime=None):
        cfg=CloudConfig('', 'https://hcla.example.test','owner',self.verifier,'1'*64,self.config)
        adapter=DeepSeekAdapter(base_url=self.config.base_url,model=self.config.model,api_key=self.config.api_key,transport_factory=transport,wall_timeout=2)
        return CloudApplication(cfg,store=self.store(),adapter=adapter,runtime=runtime)
    def request(self,conv,text='original synthetic workshop'):
        return {'scope':{'conversation_id':conv['id'],'topic_id':None},'allowed_memory_scope':conv['memory'],'expected_state_version':0,'idempotency_key':'first','synthetic_input_confirmed':True,'development_chat':True,'event':{'text':text}}
    def accepted(self,app):
        c=app.stores.conversation(TENANT);ctrl=app.controller(app.stores.persistent)
        return c,ctrl.handle_interaction(TENANT,self.request(c),defer=True)
    def test_postgres_controller_roundtrip_cold_start_idempotency(self):
        app=self.app();c,run=self.accepted(app)
        self.assertTrue(run['pending'])
        second=self.app();self.assertTrue(second.controller(second.stores.persistent).read(TENANT,run['run_id'])['pending'])
        result=app.execute(TENANT,run['run_id']);self.assertEqual(result['run_receipt']['outcome'],'COMPLETED',result['run_receipt'])
        replay=second.execute(TENANT,run['run_id']);self.assertEqual(replay['answer'],result['answer'])
        duplicate=second.controller(second.stores.persistent).handle_interaction(TENANT,self.request(c),defer=True)
        self.assertEqual(duplicate['run_id'],run['run_id'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],1)
    def test_privileged_connection_and_cross_tenant_are_rejected(self):
        with self.assertRaises(Fault):PostgresLedger('',connection=self.connect())
        store=self.store();conv=store.conversation(TENANT)
        with self.assertRaises(Fault):store.get('intruder','conversation',conv['id'])
        with self.assertRaises(Exception):store.put('intruder','conversation',{'id':'intruder'})
        with store.transaction():
            with self.assertRaises(Exception):store.connection.execute("INSERT INTO budget_policy VALUES(1,'reset')")
    def test_budget_unknown_blocks_across_instances_and_is_not_refunded(self):
        a=self.app();b=self.app();budget=a.live_chat_service.budget
        r=budget.reserve('a','one',512);self.assertTrue(r.granted)
        with self.assertRaises(BudgetError):b.live_chat_service.budget.reserve('b','two',512)
        self.assertFalse(b.live_chat_service.budget.reserve('a','one',512).granted)
        budget.finish('a','one','unknown')
        row=self.admin.execute('SELECT * FROM hcla.budget_attempts').fetchone();self.assertEqual(row['charged_usd'],row['reserved_usd']);self.assertIsNone(row['actual_usd'])
    def test_expired_owner_cannot_write_or_repeat(self):
        app=self.app();_,run=self.accepted(app);store=app.stores.persistent
        owner=app.lifecycle.claim(run['run_id']);store.fence=(run['run_id'],owner)
        self.admin.execute("UPDATE hcla.execution SET expires_at=clock_timestamp()-interval '1 second'")
        with self.assertRaises(Fault):store.put(TENANT,'run',run)
        store.fence=None;second=self.app();after=second.execute(TENANT,run['run_id'])
        self.assertEqual(after['run_receipt']['outcome'],'UNKNOWN');self.assertIsNone(after['answer'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)
    def test_durable_cancel_probe_observes_another_instance(self):
        app=self.app();_,run=self.accepted(app);app.lifecycle.claim(run['run_id'])
        probe=DurableCancellation(app.stores.persistent,run['run_id']);self.assertFalse(probe.is_set())
        other=self.app();other.controller(other.stores.persistent).cancel(TENANT,run['run_id']);time.sleep(.26)
        self.assertTrue(probe.is_set());self.assertFalse(app.execute(TENANT,run['run_id'])['pending'])
    def test_https_owner_login_cookie_revocation_throttle(self):
        app=self.app();auth=app.development_auth
        request=SimpleNamespace(headers={'Host':'hcla.example.test','Origin':'https://hcla.example.test','X-HCLA-Request':'1'})
        auth.boundary(request,True)
        token=auth.login({'login':'owner','password':'offline password fixture'});cookie=auth.cookie(token)
        self.assertIn('Secure; HttpOnly; SameSite=Strict',cookie)
        other=self.app().development_auth;self.assertEqual(other.require(cookie),TENANT)
        self.assertNotIn(token,str(self.admin.execute('SELECT * FROM hcla.sessions').fetchall()))
        other.logout(cookie)
        with self.assertRaises(Fault):auth.require(cookie)
        request.headers['Origin']='https://untrusted.example.test'
        with self.assertRaises(Fault):auth.boundary(request,True)
        for _ in range(4):
            with self.assertRaises(Fault):auth.login({'login':'owner','password':'wrong'})
        with self.assertRaises(Fault) as failure:auth.login({'login':'owner','password':'offline password fixture'})
        self.assertEqual(failure.exception.status,429)
    def test_missing_budget_policy_cannot_bootstrap_itself(self):
        self.admin.execute('DELETE FROM hcla.budget_policy')
        with self.assertRaises(BudgetError):self.app()
    def test_temporary_roundtrip_stores_no_body_and_rejects_old_snapshot(self):
        app=self.app();auth=app.development_auth;cookie=auth.cookie(auth.login({'login':'owner','password':'offline password fixture'}))
        import uuid
        conversation='temp-'+str(uuid.uuid4());c={'id':conversation,'memory':'TEMPORARY'}
        data={'conversation_id':conversation,'request_id':str(uuid.uuid4()),'request':self.request(c,'TEMPORARY_SECRET_CANARY'),'snapshot':None}
        class Handler:
            headers={'Cookie':cookie}
            def __init__(self):self.wfile=io.BytesIO()
            def send_response(self,*a):pass
            def send_header(self,*a):pass
            def end_headers(self):pass
        h=Handler();execute_temporary(app,h,data)
        messages=[json.loads(line[6:]) for line in h.wfile.getvalue().decode().splitlines() if line.startswith('data: ')]
        self.assertEqual(messages[-1]['type'],'cloud.completed');packet=messages[-1]['payload']
        self.assertEqual(packet['view']['runs'][-1]['run_receipt']['outcome'],'COMPLETED',packet['view']['runs'][-1]['run_receipt'])
        dump=[]
        for row in self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla'").fetchall():dump+=self.admin.execute('SELECT * FROM hcla.'+row['tablename']).fetchall()
        self.assertNotIn('TEMPORARY_SECRET_CANARY',str(dump));self.assertNotIn('HIDDEN_REASONING_CANARY',h.wfile.getvalue().decode())
        with self.assertRaises(Fault):execute_temporary(app,Handler(),data)
        data['snapshot']=packet['snapshot'];data['request_id']=str(uuid.uuid4());data['request']['expected_state_version']=1;data['request']['idempotency_key']='second'
        second=Handler();execute_temporary(app,second,data)
        data['request_id']=str(uuid.uuid4())
        with self.assertRaises(Fault):execute_temporary(app,Handler(),data)
    def test_temporary_validation_failure_preserves_previous_head(self):
        app=self.app();cookie=app.development_auth.cookie(app.development_auth.login({'login':'owner','password':'offline password fixture'}))
        import uuid
        c={'id':'temp-'+str(uuid.uuid4()),'memory':'TEMPORARY'}
        data={'conversation_id':c['id'],'request_id':str(uuid.uuid4()),'request':self.request(c),'snapshot':None}
        class Handler:
            headers={'Cookie':cookie}
            def __init__(self):self.wfile=io.BytesIO()
            def send_response(self,*a):pass
            def send_header(self,*a):pass
            def end_headers(self):pass
        h=Handler();execute_temporary(app,h,data)
        packet=[json.loads(line[6:]) for line in h.wfile.getvalue().decode().splitlines() if line.startswith('data: ')][-1]['payload']
        before=self.admin.execute('SELECT snapshot_hash FROM hcla.temporary_heads').fetchone()
        data.update(snapshot=packet['snapshot'],request_id=str(uuid.uuid4()))
        data['request']['synthetic_input_confirmed']=False
        with self.assertRaises(Fault):execute_temporary(app,Handler(),data)
        self.assertEqual(self.admin.execute('SELECT snapshot_hash FROM hcla.temporary_heads').fetchone(),before)
    def test_temporary_real_pinned_hcl_preparation_no_body_in_postgres(self):
        runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT')
        self.assertTrue(runtime,'Cloud integration CI must supply the reviewed runtime')
        app=self.app(runtime=os.path.relpath(runtime,ROOT));self.assertTrue(app.development_bridge.directory.is_absolute());cookie=app.development_auth.cookie(app.development_auth.login({'login':'owner','password':'offline password fixture'}))
        import uuid
        c={'id':'temp-'+str(uuid.uuid4()),'memory':'TEMPORARY'}
        request=self.request(c,'Ada said, "I believe that the workshop starts Friday."')
        request['development_execution']={'schema_version':'1.0','capability_id':'belief_interpretation','query':'What does Ada believe?','input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}
        class Handler:
            headers={'Cookie':cookie}
            def __init__(self):self.wfile=io.BytesIO()
            def send_response(self,*a):pass
            def send_header(self,*a):pass
            def end_headers(self):pass
        h=Handler();execute_temporary(app,h,{'conversation_id':c['id'],'request_id':str(uuid.uuid4()),'request':request,'snapshot':None})
        messages=[json.loads(line[6:]) for line in h.wfile.getvalue().decode().splitlines() if line.startswith('data: ')]
        self.assertEqual(messages[-1]['type'],'cloud.completed')
        run=messages[-1]['payload']['view']['runs'][-1]
        self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED')
        self.assertTrue(run['operation_receipts'][0]['used_in_answer'])
        for row in self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla'").fetchall():
            self.assertNotIn('workshop',str(self.admin.execute('SELECT * FROM hcla.'+row['tablename']).fetchall()))
    def test_persistent_delete_purges_body_copies_and_survives_new_instance(self):
        app=self.app();c=app.stores.conversation(TENANT);ctrl=app.controller(app.stores.persistent)
        req=self.request(c,'报告[合成]：CLOUD_PERSISTENT_DELETE_CANARY')
        run=ctrl.handle_interaction(TENANT,req,defer=True);app.execute(TENANT,run['run_id'])
        record=next(iter(ctrl.context.records(TENANT).values()))
        revision={'scope':{'conversation_id':c['id'],'topic_id':None},'allowed_memory_scope':'CONVERSATION','expected_state_version':1,'idempotency_key':'delete','event':{'type':'revision','text':'delete original synthetic record','revisions':[{'action':'DELETE','target_ids':[record['record_id']]}]}}
        ctrl.handle_interaction(TENANT,revision,defer=True)
        for row in self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla'").fetchall():
            self.assertNotIn('CLOUD_PERSISTENT_DELETE_CANARY',str(self.admin.execute('SELECT * FROM hcla.'+row['tablename']).fetchall()))
        other=self.app();old=other.controller(other.stores.persistent).read(TENANT,run['run_id'])
        self.assertTrue(old['redacted']);self.assertIsNone(old['answer'])
    def test_silent_thinking_cancel_never_publishes_or_refunds_unknown_transport(self):
        started=threading.Event();release=threading.Event()
        class Silent(FakeTransport):
            def post(self,body,headers):
                result=super().post(body,headers);started.set();release.wait(3);return result
        app=self.app(Silent);_,run=self.accepted(app);error=[]
        worker=threading.Thread(target=lambda:app.execute(TENANT,run['run_id']))
        worker.start();self.assertTrue(started.wait(3))
        other=self.app();other.controller(other.stores.persistent).cancel(TENANT,run['run_id'])
        worker.join(2)
        self.assertFalse(worker.is_alive(),'Durable cancellation must interrupt silent thinking')
        after=other.controller(other.stores.persistent).read(TENANT,run['run_id'])
        self.assertIsNone(after['answer']);self.assertFalse(any(e['type'].startswith('answer.') for e in after['stream']))
        row=self.admin.execute('SELECT * FROM hcla.budget_attempts').fetchone()
        self.assertEqual(row['outcome'],'active');self.assertEqual(row['reserved_usd'],row['charged_usd'])
        with self.assertRaises(BudgetError):other.live_chat_service.budget.reserve('new','attempt',512)
        release.set();time.sleep(.05)
    @unittest.skipIf(os.environ.get('HCLA_TEST_POSTGRES_KIND')=='pglite','PGlite is not concurrency evidence')
    def test_two_instances_cannot_dispatch_duplicate(self):
        calls=[]
        class Slow(FakeTransport):
            def post(self,body,headers):calls.append(1);time.sleep(.2);return super().post(body,headers)
        a=self.app(Slow);b=self.app(Slow);_,run=self.accepted(a);errors=[]
        def call(app):
            try:app.execute(TENANT,run['run_id'])
            except Exception as error:errors.append(type(error).__name__)
        threads=[threading.Thread(target=call,args=(app,)) for app in (a,b)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(10)
        self.assertFalse(any(t.is_alive() for t in threads));self.assertEqual(errors,[]);self.assertEqual(len(calls),1)
