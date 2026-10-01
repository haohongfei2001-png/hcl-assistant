"""No live auth/provider calls: verified identity and two-account regressions."""
import base64
import io
import json
import time
import threading
import unittest
import uuid
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from apps.api.cloud_server import CloudApplication,Unconfigured
from apps.api.server import handler
from packages.adapter.deepseek import DeepSeekAdapter
from packages.adapter.development_budget import BudgetError
from packages.cloud.member_auth import MemberAuth,MemberProviderConfig,SupabaseAuthProvider,VerifiedPrincipal
from packages.cloud.entitlements import Entitlements,MemberBudget,MemberCancellation
from packages.cloud.config import CloudConfig
from packages.cloud.lifecycle import DurableCancellation
from packages.cloud.temporary import member_execution_key
from packages.cloud.session_vault import SessionVault
from packages.store.ledger import Fault
from tests import test_cloud_postgres as baseline
from tests import test_cloud_trial as trial_tests
from tests.support.member_provider import FakeMemberProvider
from tests.support.cloud_transport import CloudFakeTransport
from tests.test_vercel_entrypoint import Socket


class MemberAuthUnitTests(unittest.TestCase):
    def setUp(self):
        self.config=MemberProviderConfig('https://abcdefghijklmnopqrst.supabase.co','sb_publishable_'+'a'*24)
        self.issuer=self.config.url+'/auth/v1';self.subject=FakeMemberProvider.identities['a@example.test']
        self.claims={'iss':self.issuer,'sub':self.subject,'aud':'authenticated','role':'authenticated','exp':int(time.time())+300}
        self.user={'id':self.subject,'is_anonymous':False,'email_confirmed_at':'2026-10-01T00:00:00Z','user_metadata':{'tenant':'hcla-owner','plan':'unlimited'}}
    def provider(self,claims=None,user=None):
        token='header.'+base64.urlsafe_b64encode(json.dumps(claims or self.claims).encode()).decode().rstrip('=')+'.signature'
        calls=[]
        def transport(path,body=None,token=None):
            calls.append(path)
            if path.startswith('/token'):return {'access_token':self.token,'refresh_token':'PRIVATE_REFRESH_SENTINEL'}
            if path=='/user':return user or self.user
            return {}
        self.token=token
        return SupabaseAuthProvider(self.config,transport=transport),calls
    def test_auth_is_explicitly_disabled_and_rejects_secret_or_other_project_urls(self):
        self.assertIsNone(MemberProviderConfig.from_env({}))
        self.assertIsNone(MemberProviderConfig.from_env({'HCLA_SUPABASE_AUTH_URL':self.config.url}))
        good={'HCLA_MEMBER_AUTH':'supabase','HCLA_SUPABASE_AUTH_URL':self.config.url,'HCLA_SUPABASE_PUBLISHABLE_KEY':self.config.publishable_key}
        self.assertEqual(MemberProviderConfig.from_env(good),self.config)
        for key,value in [('HCLA_MEMBER_AUTH','other'),('HCLA_SUPABASE_AUTH_URL','https://elsewhere.test'),('HCLA_SUPABASE_AUTH_URL',self.config.url+'/'),('HCLA_SUPABASE_PUBLISHABLE_KEY','sb_secret_PRIVATE_SENTINEL')]:
            with self.assertRaises(ValueError):MemberProviderConfig.from_env({**good,key:value})
    def test_exact_upstream_token_is_verified_before_subject_binding(self):
        provider,calls=self.provider();principal=provider.login('a@example.test','offline member password').principal
        self.assertEqual(calls,['/token?grant_type=password','/user'])
        self.assertEqual(principal.subject,self.subject);self.assertTrue(principal.tenant.startswith('member-'));self.assertNotEqual(principal.tenant,'hcla-owner')
        self.assertNotIn('user_metadata',repr(principal));self.assertNotIn(self.subject,repr(principal))
    def test_wrong_issuer_audience_subject_expiry_anonymous_or_unconfirmed_fail(self):
        for changes in [{'iss':'https://evil.test/auth/v1'},{'aud':'service_role'},{'sub':str(uuid.uuid4())},{'exp':0},{'exp':True},{'role':'service_role'}]:
            provider,_=self.provider(claims={**self.claims,**changes})
            with self.assertRaises(Fault):provider.login('a@example.test','offline member password')
        for changes in [{'email_confirmed_at':None},{'is_anonymous':True},{'id':'hcla-owner'}]:
            provider,_=self.provider(user={**self.user,**changes})
            with self.assertRaises(Fault):provider.login('a@example.test','offline member password')
    def test_registration_never_issues_session_even_if_upstream_returns_one(self):
        provider=SupabaseAuthProvider(self.config,transport=lambda *a,**k:{'access_token':'SENTINEL_PRIVATE_TOKEN','refresh_token':'SENTINEL_REFRESH'})
        self.assertIsNone(provider.register('a@example.test','offline member password'))
    def test_cookie_domain_and_client_scope_fields_rejected(self):
        auth=MemberAuth(None,'https://hcla.example.test','1'*64,FakeMemberProvider())
        for cookie in ['', '__Host-hcla='+'a'*43,'__Host-hcla-trial='+'a'*43,'__Host-hcla-member=short']:
            with self.assertRaises(Fault):auth.key(cookie)
        with self.assertRaises(Fault):auth.credentials({'email':'a@example.test','password':'offline member password','tenant':'hcla-owner'})
        self.assertIn('Secure; HttpOnly; SameSite=Strict; Path=/',auth.cookie('a'*43))
        for headers in [{'Host':'wrong.test'},{'Host':'hcla.example.test','Origin':'https://evil.test'},{'Host':'hcla.example.test','Origin':'https://hcla.example.test'}]:
            with self.assertRaises(Fault):auth.boundary(SimpleNamespace(headers=headers),True)
    def test_disabled_public_routes_do_not_create_sessions(self):
        app=Unconfigured()
        status,payload=trial_tests.CloudTrialTests.http(self,app,'/v1/account/status')
        self.assertEqual(status,200);self.assertFalse(json.loads(payload)['available'])
        for path in ['/v1/account/login','/v1/account/register','/v1/member/conversations']:
            status,_=trial_tests.CloudTrialTests.http(self,app,path,body={})
            self.assertEqual(status,503)
    def test_refresh_encryption_is_randomized_and_bound_to_full_session_context(self):
        vault=SessionVault('1'*64);args=(self.issuer,self.subject,'a'*64,2000000000)
        first=vault.seal('PRIVATE_REFRESH_CANARY',*args);second=vault.seal('PRIVATE_REFRESH_CANARY',*args)
        self.assertNotEqual(first,second);self.assertNotIn('PRIVATE_REFRESH_CANARY',first)
        self.assertEqual(vault.open(first,*args),'PRIVATE_REFRESH_CANARY')
        for changed in [('https://other.test',*args[1:]),(args[0],str(uuid.uuid4()),*args[2:]),(*args[:2],'b'*64,args[3]),(*args[:3],2000000001)]:
            with self.assertRaises(Exception):vault.open(first,*changed)
        with self.assertRaises(Exception):SessionVault('2'*64).open(first,*args)
        with self.assertRaises(Exception):vault.open(first[:-5]+'AAAA=',*args)


@unittest.skipUnless(baseline.DSN,'Disposable local Postgres required in cloud CI')
class MemberPostgresTests(unittest.TestCase):
    setUpClass=classmethod(baseline.CloudPostgresTests.setUpClass.__func__)
    setUp=baseline.CloudPostgresTests.setUp
    tearDown=baseline.CloudPostgresTests.tearDown
    store=baseline.CloudPostgresTests.store
    request=baseline.CloudPostgresTests.request
    http=trial_tests.CloudTrialTests.http

    def app(self,transport=CloudFakeTransport,provider=None):
        cfg=CloudConfig('','https://hcla.example.test','owner',self.verifier,'1'*64,self.config)
        adapter=DeepSeekAdapter(base_url=self.config.base_url,model=self.config.model,api_key=self.config.api_key,transport_factory=transport,wall_timeout=3)
        return CloudApplication(cfg,store=self.store(),adapter=adapter,member_provider=provider or FakeMemberProvider())
    def grant(self,tenant,*,requests=8,cost='10',temporary=True,persistent=True):
        self.admin.execute("INSERT INTO hcla.member_entitlements(tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_usd) VALUES(%s,'offline-account-grant',true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',%s,%s,%s,%s)",(tenant,temporary,persistent,requests,cost))
    def login(self,user='a',*,grant=True,transport=CloudFakeTransport):
        app=self.app(transport);token,_=app.member_auth.login({'email':user+'@example.test','password':'offline member password'});cookie=app.member_auth.cookie(token)
        if grant:self.grant(app.stores.persistent.tenant)
        app.authenticate_member(SimpleNamespace(headers={'Cookie':cookie,'Host':'hcla.example.test','Origin':'https://hcla.example.test','X-HCLA-Request':'1'},command='POST'))
        return app,cookie,app.stores.persistent.tenant
    def test_two_accounts_and_owner_routes_stay_separate(self):
        a,cookie_a,tenant_a=self.login();b,cookie_b,tenant_b=self.login('b')
        conv=a.stores.conversation(tenant_a,title='MEMBER_A_TITLE')
        ctrl=a.controller(a.stores.persistent);run=ctrl.handle_interaction(tenant_a,self.request(conv,'MEMBER_A_BODY'),defer=True)
        a.execute(tenant_a,run['run_id'])
        for path in [f'/v1/member/conversations/{conv["id"]}',f'/v1/member/runs/{run["run_id"]}',f'/v1/member/runs/{run["run_id"]}/events',f'/v1/member/lab/runs/{run["run_id"]}',f'/v1/member/context?conversation_id={conv["id"]}']:
            status,payload=self.http(b,path,cookie=cookie_b);self.assertEqual(status,403,path);self.assertNotIn(b'MEMBER_A_BODY',payload)
        for suffix in ['execute','cancel','retry']:
            self.assertEqual(self.http(b,f'/v1/member/runs/{run["run_id"]}/{suffix}',cookie=cookie_b,body={'idempotency_key':'cross'})[0],403)
        status,payload=self.http(b,'/v1/member/history/search?q=MEMBER_A',cookie=cookie_b);self.assertEqual(status,200);self.assertEqual(json.loads(payload),[])
        for path in ['/v1/conversations','/v1/topics','/v1/runs/'+run['run_id'],'/v1/history/search?q=A']:
            self.assertEqual(self.http(self.app(),path,cookie=cookie_a)[0],401)
        self.assertEqual(self.http(self.app(),'/v1/member/development/logout',cookie=cookie_a,body={})[0],404)
        self.assertEqual(b.stores.persistent.db.execute('SELECT count(*) AS n FROM objects').fetchone()['n'],0)
        self.assertNotEqual(tenant_a,tenant_b)
    def test_session_hash_rls_expiry_and_logout_survive_cold_start(self):
        a,cookie,tenant=self.login();key=a.member_auth.key(cookie)
        rows=self.admin.execute('SELECT * FROM hcla.member_sessions').fetchall()
        self.assertNotIn(cookie,str(rows));self.assertNotIn('offline member password',str(rows))
        self.assertLessEqual(rows[0]['expires_at'].timestamp()-time.time(),900)
        cold=self.app();self.assertEqual(cold.member_auth.require(cookie).tenant,tenant)
        cold.member_auth.logout(cookie)
        with self.assertRaises(Fault):self.app().member_auth.require(cookie)
        self.assertFalse(a.member_auth.active(key))
        _,b_cookie,b_tenant=self.login('b')
        unbound=self.store();self.assertEqual(unbound.db.execute('SELECT * FROM member_sessions').fetchall(),[])
        self.admin.execute("UPDATE hcla.member_sessions SET expires_at=clock_timestamp()-interval '1 second' WHERE tenant=%s",(b_tenant,))
        with self.assertRaises(Fault):self.app().member_auth.require(b_cookie)
    def test_upstream_expiry_caps_local_session_and_session_swap_is_refused(self):
        class Short(FakeMemberProvider):
            def login(self,*args):
                session=super().login(*args)
                return replace(session,principal=replace(session.principal,expires_at=int(time.time())+20))
        app=self.app(provider=Short());token,expiry=app.member_auth.login({'email':'a@example.test','password':'offline member password'})
        self.assertLessEqual(expiry,time.time()+20)
        with self.assertRaises(Fault):app.member_auth.login({'email':'b@example.test','password':'offline member password'})
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_sessions').fetchone()['n'],1)
    def test_no_entitlement_or_client_claim_can_grant_access(self):
        app,cookie,tenant=self.login(grant=False)
        self.assertEqual(self.http(app,'/v1/member/conversations',cookie=cookie,body={'title':'Denied','tenant':'hcla-owner'})[0],400)
        self.assertEqual(self.http(app,'/v1/member/conversations',cookie=cookie,body={'title':'Denied'})[0],403)
        with self.assertRaises(BudgetError):app.live_chat_service.budget.reserve('no-rights','attempt',128)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)
        self.grant(tenant)
        with self.assertRaises(Exception):app.stores.persistent.db.execute('UPDATE member_entitlements SET max_requests=999999')
    def test_per_account_cap_and_global_operator_cap_are_both_atomic(self):
        a,_,ta=self.login(grant=False);b,_,tb=self.login('b',grant=False)
        self.grant(ta,requests=1);self.grant(tb,requests=8)
        one=a.live_chat_service.budget;two=b.live_chat_service.budget
        self.assertTrue(one.reserve('a-one','attempt',128).granted)
        with self.assertRaises(BudgetError):two.reserve('b-race','attempt',128)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_budget_attempts WHERE tenant=%s',(tb,)).fetchone()['n'],0)
        one.finish('a-one','attempt','unknown')
        with self.assertRaises(BudgetError):one.reserve('a-two','attempt',128)
        self.assertTrue(two.reserve('b-one','attempt',128).granted)
        self.assertEqual(one.snapshot()['request_count'],1);self.assertEqual(two.snapshot()['request_count'],1)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],2)
    def test_member_operational_rows_and_temporary_snapshots_are_isolated(self):
        a,ca,ta=self.login();b,cb,tb=self.login('b');request_id=str(uuid.uuid4())
        key_a=member_execution_key(a,request_id);a.lifecycle.claim(key_a,temporary=True)
        self.assertEqual(self.http(b,'/v1/member/temporary/cancel',cookie=cb,body={'request_id':request_id})[0],200)
        self.assertFalse(self.admin.execute('SELECT cancelled FROM hcla.execution WHERE run_id=%s',(key_a,)).fetchone()['cancelled'])
        self.assertEqual(b.stores.persistent.db.execute('SELECT * FROM execution').fetchall(),[])
        from packages.runtime_bridge.bridge import RuntimeBridge
        import os
        runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT');self.assertTrue(runtime,'Reviewed runtime is mandatory in cloud CI')
        a.development_bridge=RuntimeBridge(runtime);b.development_bridge=RuntimeBridge(runtime)
        conv='temp-'+str(uuid.uuid4());request=self.request({'id':conv,'memory':'TEMPORARY'},'Ada said, "I believe that MEMBER_TEMP_BODY_CANARY starts Friday."')
        request['development_execution']={'schema_version':'1.0','capability_id':'belief_interpretation','query':'What does Ada believe?','input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}
        data={'conversation_id':conv,'request_id':str(uuid.uuid4()),'snapshot':None,'request':request}
        status,payload=self.http(a,'/v1/member/temporary/execute',cookie=ca,body=data);self.assertEqual(status,200,payload)
        messages=[json.loads(line[6:]) for line in payload.decode().splitlines() if line.startswith('data: ')];self.assertEqual(messages[-1]['type'],'cloud.completed',messages)
        self.assertEqual(messages[-1]['payload']['view']['runs'][-1]['run_receipt']['actual_treatment'],'EXECUTED')
        data['snapshot']=messages[-1]['payload']['snapshot'];data['request_id']=str(uuid.uuid4())
        self.assertEqual(self.http(b,'/v1/member/temporary/execute',cookie=cb,body=data)[0],403)
        for row in self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla'").fetchall():self.assertNotIn('MEMBER_TEMP_BODY_CANARY',str(self.admin.execute('SELECT * FROM hcla.'+row['tablename']).fetchall()))
    def test_entitlement_revocation_and_logout_cancel_inflight_admission(self):
        app,cookie,tenant=self.login();conv=app.stores.conversation(tenant);ctrl=app.controller(app.stores.persistent);run=ctrl.handle_interaction(tenant,self.request(conv),defer=True)
        app.lifecycle.claim(run['run_id'])
        probe=MemberCancellation(DurableCancellation(app.stores.persistent,run['run_id']),app.member_auth,app.member_context[1],app.entitlements,'CONVERSATION')
        self.assertFalse(probe.is_set())
        self.admin.execute('UPDATE hcla.member_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
        probe.next_check=0;self.assertTrue(probe.is_set())
        with self.assertRaises(BudgetError):app.live_chat_service.budget.reserve('revoked','attempt',128)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)
    def test_pool_transaction_context_is_reset_and_bad_client_tenant_cannot_bind(self):
        app,_,tenant=self.login();store=app.stores.persistent
        try:
            with store.transaction():
                self.assertEqual(store.connection.execute("SELECT current_setting('hcla.tenant') AS tenant").fetchone()['tenant'],tenant)
                raise RuntimeError('rollback fixture')
        except RuntimeError:pass
        with store.transaction():self.assertEqual(store.connection.execute("SELECT current_setting('hcla.tenant') AS tenant").fetchone()['tenant'],tenant)
        with self.assertRaises(Fault):store.bind_member('client-tenant')
        with self.assertRaises(Exception):store.put('hcla-owner','conversation',{'id':'wrong-tenant'})

    def make_refresh_due(self,tenant):
        self.admin.execute("UPDATE hcla.member_sessions SET expires_at=clock_timestamp()+interval '30 seconds' WHERE tenant=%s",(tenant,))

    def test_automatic_refresh_preserves_identity_rotates_ciphertext_and_caps_lifetime(self):
        app,cookie,tenant=self.login();before=self.admin.execute('SELECT * FROM hcla.member_sessions').fetchone()
        self.make_refresh_due(tenant)
        cold=self.app();cold.member_auth.refresh(cookie);principal=cold.member_auth.require(cookie)
        after=self.admin.execute('SELECT * FROM hcla.member_sessions').fetchone()
        self.assertEqual(principal.tenant,tenant);self.assertEqual(before['session_key'],after['session_key'])
        self.assertEqual(before['absolute_expires_at'],after['absolute_expires_at']);self.assertNotEqual(before['refresh_ciphertext'],after['refresh_ciphertext'])
        self.assertNotIn('offline-refresh',str(after));self.assertEqual(after['refresh_state'],'idle')
        # A changed immutable deadline also invalidates the authenticated envelope.
        self.admin.execute("UPDATE hcla.member_sessions SET absolute_expires_at=absolute_expires_at+interval '1 second',expires_at=clock_timestamp()+interval '1 second'")
        with self.assertRaises(Fault):self.app().member_auth.refresh(cookie)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_sessions').fetchone()['n'],0)

    def test_refresh_contention_and_lost_worker_never_replay_upstream_token(self):
        app,cookie,tenant=self.login();self.make_refresh_due(tenant)
        self.admin.execute("UPDATE hcla.member_sessions SET refresh_state='inflight',refresh_owner='lost',refresh_started_at=clock_timestamp() WHERE tenant=%s",(tenant,))
        with self.assertRaises(Fault) as busy:self.app().member_auth.refresh(cookie)
        self.assertEqual(busy.exception.status,409)
        self.admin.execute("UPDATE hcla.member_sessions SET refresh_started_at=clock_timestamp()-interval '21 seconds' WHERE tenant=%s",(tenant,))
        provider=FakeMemberProvider()
        with patch.object(provider,'refresh',side_effect=AssertionError('Uncertain token cannot replay')):
            with self.assertRaises(Fault) as ended:self.app(provider=provider).member_auth.refresh(cookie)
        self.assertEqual(ended.exception.status,401)
        with self.assertRaises(Fault):self.app().member_auth.require(cookie)

    def test_signing_key_rotation_invalidates_member_sessions_before_decryption(self):
        app,cookie,tenant=self.login();store=self.store()
        changed=MemberAuth(store,'https://hcla.example.test','2'*64,FakeMemberProvider())
        with self.assertRaises(Fault):changed.require(cookie)
        self.assertFalse(changed.renewable(cookie))
        with self.assertRaises(Fault):changed.refresh(cookie)

    def test_near_absolute_deadline_renewal_cannot_extend_it(self):
        app,cookie,tenant=self.login();key=app.member_auth.key(cookie)
        row=self.admin.execute('SELECT * FROM hcla.member_sessions').fetchone();absolute=int(time.time())+30
        token='offline-refresh-'+str(row['subject'])
        encrypted=app.member_auth.vault.seal(token,row['issuer'],str(row['subject']),key,absolute)
        self.admin.execute("UPDATE hcla.member_sessions SET absolute_expires_at=to_timestamp(%s),expires_at=clock_timestamp()+interval '1 second',refresh_ciphertext=%s",(absolute,encrypted))
        cold=self.app();cold.member_auth.refresh(cookie)
        self.assertEqual(cold.member_auth.require(cookie).expires_at,absolute)

    def test_logout_during_refresh_cannot_resurrect_session(self):
        app,cookie,tenant=self.login();self.make_refresh_due(tenant)
        started=threading.Event();release=threading.Event();errors=[]
        class Slow(FakeMemberProvider):
            def refresh(self,token):started.set();release.wait(3);return super().refresh(token)
        cold=self.app(provider=Slow())
        def renew():
            try:cold.member_auth.refresh(cookie)
            except Fault as error:errors.append(error.status)
        worker=threading.Thread(target=renew);worker.start();self.assertTrue(started.wait(2))
        self.app().member_auth.logout(cookie);release.set();worker.join(4)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[401])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_sessions').fetchone()['n'],0)

    def test_wrong_subject_or_failed_refresh_revokes_without_secret_output(self):
        for mode in ['wrong-subject','transport-uncertain']:
            app,cookie,tenant=self.login(grant=False);self.make_refresh_due(tenant)
            class Bad(FakeMemberProvider):
                def refresh(self,token):
                    if mode=='transport-uncertain':raise RuntimeError('PRIVATE_REFRESH_CANARY')
                    result=super().refresh(token)
                    return replace(result,principal=replace(result.principal,subject=self.identities['b@example.test']))
            with self.assertRaises(Fault) as error:self.app(provider=Bad()).member_auth.refresh(cookie)
            self.assertNotIn('PRIVATE_REFRESH_CANARY',str(error.exception))
            with self.assertRaises(Fault):self.app().member_auth.require(cookie)

    def test_separate_accounts_cannot_exceed_operator_cost_ceiling(self):
        from packages.adapter.development_budget import DevelopmentBudget
        self.config=replace(self.config,max_cost_usd=Decimal('2'))
        self.admin.execute('UPDATE hcla.budget_policy SET policy=%s',(DevelopmentBudget._policy(SimpleNamespace(config=self.config)),))
        a,_,ta=self.login();b,_,tb=self.login('b')
        a.live_chat_service.budget.reserve('a','attempt',128)
        a.live_chat_service.budget.finish('a','attempt','unknown')
        with self.assertRaises(BudgetError):b.live_chat_service.budget.reserve('b','attempt',128)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_budget_attempts WHERE tenant=%s',(tb,)).fetchone()['n'],0)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],1)

    def test_usage_snapshot_is_current_grant_only_without_resetting_operator_history(self):
        app,_,tenant=self.login();budget=app.live_chat_service.budget
        budget.reserve('old','attempt',128);budget.finish('old','attempt','unknown')
        self.admin.execute('UPDATE hcla.member_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
        self.admin.execute("INSERT INTO hcla.member_entitlements(tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_usd) VALUES(%s,'offline-next-grant',true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',true,true,2,3)",(tenant,))
        self.assertEqual(budget.snapshot()['request_count'],0);self.assertEqual(budget.snapshot()['max_requests'],2)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_budget_attempts').fetchone()['n'],1)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],1)

    def test_concurrent_account_admission_has_one_global_owner(self):
        a,_,_=self.login();b,_,_=self.login('b');outcomes=[];barrier=threading.Barrier(2)
        def reserve(app,key):
            barrier.wait()
            try:outcomes.append(app.live_chat_service.budget.reserve(key,'attempt',128).granted)
            except BudgetError:outcomes.append(False)
        workers=[threading.Thread(target=reserve,args=(a,'a')),threading.Thread(target=reserve,args=(b,'b'))]
        for worker in workers:worker.start()
        for worker in workers:worker.join(5)
        self.assertFalse(any(worker.is_alive() for worker in workers));self.assertEqual(sorted(outcomes),[False,True])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_budget_attempts').fetchone()['n'],1)
