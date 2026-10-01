"""Provider-free public guest isolation, expiry and settlement regressions."""
import io
import json
import time
import unittest
import uuid
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from apps.api.server import handler
from apps.api.cloud_server import CloudApplication
from packages.adapter.deepseek import DeepSeekAdapter
from packages.adapter.development_budget import BudgetError
from packages.cloud.config import CloudConfig
from packages.cloud.trial import TrialWindow,TrialAuth,TrialBudget,TrialCancellation,trial_policy
from packages.cloud.temporary import execute,unpack
from packages.store.ledger import Fault
from tests import test_cloud_postgres as postgres_tests
DSN=postgres_tests.DSN
from tests.test_vercel_entrypoint import Socket
from tests.support.cloud_transport import CloudFakeTransport


class TrialUnitTests(unittest.TestCase):
    def budget(self):
        window=TrialWindow(100,14500)
        return SimpleNamespace(window=window,clock=lambda:101,require_active=lambda:None,_policy=lambda:'synthetic-fixed-policy')
    def test_window_must_be_explicit_fixed_and_at_most_four_hours(self):
        for value in ({},{'starts_at':True,'expires_at':2},{'starts_at':100,'expires_at':14501},{'starts_at':100,'expires_at':99}):
            with self.assertRaises(ValueError):TrialWindow.from_value(value)
        self.assertEqual(TrialWindow.from_value({'starts_at':100,'expires_at':14500}),TrialWindow(100,14500))
    def test_cookie_is_purpose_policy_and_deadline_bound(self):
        budget=self.budget();auth=TrialAuth('https://trial.example.test','1'*64,budget)
        cookie=auth.issue();key=auth.require(cookie)
        self.assertIn('Secure; HttpOnly; SameSite=Strict; Path=/',cookie)
        self.assertNotIn(key,cookie)
        with self.assertRaises(Fault):auth.require(cookie.replace('__Host-hcla-trial','__Host-hcla'))
        with self.assertRaises(Fault):auth.require(cookie.replace('.14500.','.14501.'))
        budget._policy=lambda:'another-grant'
        with self.assertRaises(Fault):auth.require(cookie)
        budget.require_active=lambda:(_ for _ in ()).throw(BudgetError('trial_expired_or_not_started'))
        with self.assertRaises(Fault):auth.issue()
    def test_execution_keys_are_separate_between_guests(self):
        auth=TrialAuth('https://trial.example.test','1'*64,self.budget());request=str(uuid.uuid4())
        a,b=auth.require(auth.issue()),auth.require(auth.issue())
        self.assertNotEqual(auth.execution_key(a,request),auth.execution_key(b,request))
        with self.assertRaises(Fault):auth.execution_key(a,'arbitrary')
    def test_expiry_and_clock_failure_cancel_in_flight_work(self):
        class Cancel:
            stopped=False
            def set(self):self.stopped=True
            def is_set(self):return self.stopped
        budget=self.budget();cancel=Cancel();probe=TrialCancellation(cancel,budget)
        self.assertFalse(probe.is_set())
        budget.clock=lambda:budget.window.expires_at
        with patch('packages.cloud.trial.time.monotonic',return_value=10**20):self.assertTrue(probe.is_set())

    def test_malformed_final_usage_never_reuses_prior_consistent_counts(self):
        for invalid in (None,{'prompt_tokens':'invalid','completion_tokens':24,'total_tokens':88},
                        {'prompt_tokens':64,'completion_tokens':24,'total_tokens':88,'completion_tokens_details':{'reasoning_tokens':999}}):
            class Transport(CloudFakeTransport):
                def post(self,body,headers):
                    result=super().post(body,headers)
                    self.data=self.data.replace(b'"completion_tokens": 24',b'"completion_tokens": 24, "total_tokens": 88')
                    if invalid is not None:
                        final=json.dumps({'choices':[],'usage':invalid}).encode()
                        self.data=self.data.replace(b'data: [DONE]',b'data: '+final+b'\n\ndata: [DONE]')
                    return result
            adapter=DeepSeekAdapter(base_url='https://api.deepseek.com',model='deepseek-v4-pro',api_key='offline-fixture',transport_factory=Transport)
            result=adapter.generate([{'role':'user','content':'original synthetic fixture'}],max_tokens=512)
            self.assertEqual(result.outcome,'SUCCEEDED');self.assertTrue(result.transport_stopped)
            self.assertEqual(result.usage_consistent,invalid is None)


@unittest.skipUnless(DSN,'Disposable local Postgres required in cloud CI')
class CloudTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        postgres_tests.CloudPostgresTests.setUpClass.__func__(cls)
        cls.config=replace(cls.config,budget_id='offline-four-hour-trial',max_cost_usd=Decimal('10'),max_requests=999999999,max_output_tokens=8192)
    def setUp(self):
        postgres_tests.CloudPostgresTests.setUp(self)
        now=int(time.time());self.window=TrialWindow(now-1,now-1+14400)
    tearDown=postgres_tests.CloudPostgresTests.tearDown
    store=postgres_tests.CloudPostgresTests.store
    request=postgres_tests.CloudPostgresTests.request

    def app(self,window=None,transport=CloudFakeTransport):
        window=window or self.window
        policy=trial_policy(self.config,window)
        self.admin.execute('INSERT INTO hcla.trial_budget_policy VALUES(1,%s) ON CONFLICT(singleton) DO NOTHING',(policy,))
        cfg=CloudConfig('', 'https://hcla.example.test','owner',self.verifier,'1'*64,self.config,window)
        adapter=DeepSeekAdapter(base_url=self.config.base_url,model=self.config.model,api_key=self.config.api_key,transport_factory=transport,wall_timeout=3)
        return CloudApplication(cfg,store=self.store(),adapter=adapter)

    def http(self,app,path,*,cookie='',body=None,origin='https://hcla.example.test'):
        method='GET' if body is None else 'POST';data=b'' if body is None else json.dumps(body).encode()
        request=f'{method} {path} HTTP/1.0\r\nHost: hcla.example.test\r\nOrigin: {origin}\r\nX-HCLA-Request: 1\r\nCookie: {cookie}\r\nContent-Length: {len(data)}\r\n\r\n'.encode()+data
        sock=Socket(request);handler(app)(sock,('127.0.0.1',1),SimpleNamespace(server_port=443))
        head,payload=sock.output.getvalue().split(b'\r\n\r\n',1)
        return int(head.split()[1]),payload

    def execute(self,app,cookie,text='TRIAL_ORIGINAL_SYNTHETIC_CANARY',data=None):
        conversation='temp-'+str(uuid.uuid4())
        data=data or {'conversation_id':conversation,'request_id':str(uuid.uuid4()),'request':self.request({'id':conversation,'memory':'TEMPORARY'},text),'snapshot':None}
        status,payload=self.http(app,'/v1/trial/execute',cookie=cookie,body=data)
        events=[json.loads(line[6:]) for line in payload.decode().splitlines() if line.startswith('data: ')]
        return status,events,data

    def test_guest_cannot_reach_owner_routes_or_owner_status(self):
        app=self.app();cookie=app.trial_auth.issue()
        for path in ['/v1/conversations','/v1/topics','/v1/history/search?q=private','/v1/context?conversation_id=private','/v1/sources/private','/v1/runs/private','/v1/runs/private/events','/v1/answers/private/explain','/v1/lab/runs/private','/v1/lab/export/private']:
            self.assertEqual(self.http(app,path,cookie=cookie)[0],401,path)
        for path in ['/v1/development/logout','/v1/conversations','/v1/topics','/v1/sources','/v1/runs/private/execute','/v1/temporary/execute']:
            self.assertEqual(self.http(app,path,cookie=cookie,body={})[0],401,path)
        status,payload=self.http(app,'/v1/development/status',cookie=cookie)
        self.assertEqual(status,200);self.assertFalse(json.loads(payload)['authenticated'])
        self.assertEqual(self.http(app,'/v1/trial/unknown',cookie=cookie,body={})[0],404)
        self.assertEqual(self.http(app,'/v1/trial/start',body={},origin='https://other.example.test')[0],403)

    def test_two_guests_snapshot_cancel_and_request_ids_stay_isolated(self):
        app=self.app();a,b=app.trial_auth.issue(),app.trial_auth.issue();request=str(uuid.uuid4())
        key=app.trial_auth.execution_key(app.trial_auth.require(a),request)
        app.lifecycle.claim(key,temporary=True)
        self.assertEqual(self.http(app,'/v1/trial/cancel',cookie=b,body={'request_id':request})[0],200)
        self.assertFalse(self.admin.execute('SELECT cancelled FROM hcla.execution WHERE run_id=%s',(key,)).fetchone()['cancelled'])
        status,events,data=self.execute(app,a)
        self.assertEqual(status,200);packet=events[-1]['payload'];self.assertEqual(events[-1]['type'],'cloud.completed')
        with self.assertRaises(Fault):unpack(packet['snapshot'],'1'*64,app.trial_auth.require(b),data['conversation_id'])
        data['snapshot']=packet['snapshot'];data['request_id']=str(uuid.uuid4())
        self.assertEqual(self.http(app,'/v1/trial/execute',cookie=b,body=data)[0],403)
        for table in ['objects','sources','records','events','trial_budget_attempts','execution','temporary_heads']:
            self.assertNotIn('TRIAL_ORIGINAL_SYNTHETIC_CANARY',str(self.admin.execute('SELECT * FROM hcla.'+table).fetchall()))

    def test_trial_rejects_persistent_scope_and_owner_provider_bypass(self):
        app=self.app();cookie=app.trial_auth.issue();conversation='temp-'+str(uuid.uuid4())
        data={'conversation_id':conversation,'request_id':str(uuid.uuid4()),'request':self.request({'id':conversation,'memory':'CONVERSATION'}),'snapshot':None}
        self.assertEqual(self.http(app,'/v1/trial/execute',cookie=cookie,body=data)[0],403)
        data['request']['allowed_memory_scope']='TEMPORARY';data['request']['scope']['topic_id']='private'
        self.assertEqual(self.http(app,'/v1/trial/execute',cookie=cookie,body=data)[0],403)
        with self.assertRaises(Fault):app.execute('hcla-owner','private')
        owner_cookie=app.development_auth.cookie(app.development_auth.login({'login':'owner','password':'offline password fixture'}))
        self.assertEqual(self.http(app,'/v1/temporary/execute',cookie=owner_cookie,body=data)[0],403)
        self.assertIsNone(app.controller(app.stores.persistent).live_chat)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.trial_budget_attempts').fetchone()['n'],0)

    def test_fixed_deadline_and_policy_cannot_reset_on_new_instance(self):
        window=TrialWindow(int(time.time())-1,int(time.time())+100)
        app=self.app(window);cookie=app.trial_auth.issue()
        again=self.app(window);self.assertEqual(app.trial_auth.require(cookie),again.trial_auth.require(cookie))
        with patch.object(again.trial_auth.budget,'clock',return_value=window.expires_at):
            with self.assertRaises(Fault):again.trial_auth.require(cookie)
            with self.assertRaises(Fault):again.trial_auth.issue()
            with self.assertRaises(BudgetError):again.trial_auth.budget.reserve('expired','attempt',100)
        with self.assertRaises(BudgetError):self.app(TrialWindow(window.starts_at,window.expires_at+1))
        with app.stores.persistent.transaction():
            with self.assertRaises(Exception):app.stores.persistent.db.execute("UPDATE trial_budget_policy SET policy='reset'")

    def settle_fixture(self,app,outcome='completed',input_tokens=100,output_tokens=10):
        store=app.stores.persistent;budget=app.trial_auth.budget;identity=str(uuid.uuid4())
        owner=app.lifecycle.claim(identity,temporary=True);store.fence=(identity,owner)
        budget.reserve(identity,'attempt',512)
        budget.finish(identity,'attempt',outcome,input_tokens=input_tokens,output_tokens=output_tokens)
        return identity,budget

    def test_new_policy_settles_confirmed_completion_once_without_changing_v2(self):
        app=self.app();before=self.admin.execute('SELECT * FROM hcla.budget_policy').fetchall()
        identity,budget=self.settle_fixture(app);budget.reconcile_completed(identity,'attempt')
        row=self.admin.execute('SELECT * FROM hcla.trial_budget_attempts').fetchone()
        self.assertLess(row['charged_usd'],row['reserved_usd']);self.assertEqual(row['charged_usd'],Decimal('0.0001716'))
        budget.reconcile_completed(identity,'attempt');self.assertEqual(row,self.admin.execute('SELECT * FROM hcla.trial_budget_attempts').fetchone())
        self.assertEqual(before,self.admin.execute('SELECT * FROM hcla.budget_policy').fetchall())
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)

    def test_late_cancel_missing_usage_and_unknown_keep_full_reservation(self):
        for outcome,tokens,cancel in [('completed',(100,10),True),('completed',(0,0),False),('completed',(None,None),False),('unknown',(100,10),False),('cancelled',(100,10),False)]:
            app=self.app();identity,budget=self.settle_fixture(app,outcome,*tokens)
            if cancel:self.admin.execute('UPDATE hcla.execution SET cancelled=true WHERE run_id=%s',(identity,))
            budget.reconcile_completed(identity,'attempt')
            row=self.admin.execute('SELECT * FROM hcla.trial_budget_attempts ORDER BY run_key').fetchall()
            self.assertTrue(all(r['charged_usd']==r['reserved_usd'] for r in row))
            app.stores.persistent.fence=None

    def test_global_budget_concurrency_and_new_session_do_not_add_capacity(self):
        app=self.app();other=self.app();a=app.trial_auth.budget;b=other.trial_auth.budget
        a.reserve('one','attempt',100)
        with self.assertRaises(BudgetError):b.reserve('two','attempt',100)
        self.assertFalse(b.reserve('one','attempt',100).granted)
        a.finish('one','attempt','unknown')
        for i in range(1,7):a.reserve('run'+str(i),'attempt',100);a.finish('run'+str(i),'attempt','unknown')
        app.trial_auth.issue()
        with self.assertRaises(BudgetError):b.reserve('over-cap','attempt',100)
        self.assertLessEqual(Decimal(a.snapshot()['charged_cost_usd']),Decimal('10'))

    def test_real_controller_validated_usage_settles_and_bad_totals_do_not(self):
        for total in (88,None,99,'malformed-final'):
            class UsageTransport(CloudFakeTransport):
                def post(self,body,headers):
                    result=super().post(body,headers)
                    if total is not None:self.data=self.data.replace(b'"completion_tokens": 24',b'"completion_tokens": 24, "total_tokens": '+str(88 if total=='malformed-final' else total).encode())
                    if total=='malformed-final':
                        corrupt=json.dumps({'choices':[],'usage':{'prompt_tokens':'invalid','completion_tokens':24,'total_tokens':88}}).encode()
                        self.data=self.data.replace(b'data: [DONE]',b'data: '+corrupt+b'\n\ndata: [DONE]')
                    return result
            app=self.app(transport=UsageTransport);status,events,_=self.execute(app,app.trial_auth.issue())
            self.assertEqual(status,200);self.assertEqual(events[-1]['type'],'cloud.completed')
            rows=self.admin.execute('SELECT * FROM hcla.trial_budget_attempts').fetchall()
            settled=[row for row in rows if row['charged_usd']<row['reserved_usd']]
            self.assertEqual(len(settled),1)

    def test_database_metadata_and_key_required_without_duplicate_owner_fields(self):
        app=self.app();self.assertIsNotNone(app.trial_auth)
        from packages.cloud.trial import from_database_policy
        base=CloudConfig('', 'https://hcla.example.test','owner',self.verifier,'1'*64,None)
        self.assertIs(from_database_policy(app.stores.persistent,base),base)
        configured=from_database_policy(app.stores.persistent,replace(base,cloud_api_key='offline-fixture'))
        self.assertEqual(configured.trial,self.window);self.assertEqual(configured.provider.budget_id,self.config.budget_id)
        self.admin.execute("UPDATE hcla.trial_budget_policy SET policy=replace(policy,'TEMPORARY_SYNTHETIC_ONLY','PERSISTENT')")
        with self.assertRaises(BudgetError):from_database_policy(app.stores.persistent,replace(base,cloud_api_key='offline-fixture'))
