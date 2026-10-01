"""Password recovery against synthetic Auth and disposable local Postgres only."""
import base64
import io
import json
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
from apps.api.cloud_server import CloudApplication,Unconfigured
from packages.cloud.config import CloudConfig
from packages.cloud.member_auth import MemberAuth,MemberProviderConfig,SupabaseAuthProvider,PasswordMutationRejected
from packages.cloud.recovery import RecoveryAuth,RecoveryVault
from packages.cloud.session_vault import SessionVault
from packages.cloud import auth_generation
from packages.adapter.deepseek import DeepSeekAdapter
from packages.store.ledger import Fault
from tests import test_cloud_postgres as baseline,test_cloud_members as members,test_cloud_trial as trial
from tests.support.member_provider import FakeMemberProvider
from tests.support.cloud_transport import CloudFakeTransport

class RecoveryUnitTests(unittest.TestCase):
    def setUp(self):
        self.config=MemberProviderConfig('https://abcdefghijklmnopqrst.supabase.co','sb_publishable_'+'a'*24)
        self.issuer=self.config.url+'/auth/v1';self.subject=FakeMemberProvider.identities['a@example.test']
    def test_disabled_status_and_mutations_do_not_open_account_recovery(self):
        status,body=trial.CloudTrialTests.http(self,Unconfigured(),'/v1/account/recovery/status')
        self.assertEqual(status,200);self.assertFalse(json.loads(body)['available'])
        for path in ['start','exchange','complete']:
            status,_=trial.CloudTrialTests.http(self,Unconfigured(),'/v1/account/recovery/'+path,body={})
            self.assertEqual(status,503)
    def test_recovery_configuration_is_explicit_and_requires_member_auth(self):
        from packages.cloud.auth import password_verifier
        owner={'schema_version':1,'login':'owner','verifier':password_verifier('offline configuration password'),'temporary_state_key':'1'*64}
        env={'HCLA_DATABASE_URL':'postgresql://fixture:fixture@db.example.test/postgres?sslmode=verify-full','HCLA_PUBLIC_ORIGIN':'https://hcla.example.test','HCLA_OWNER_CONFIG':json.dumps(owner)}
        self.assertFalse(CloudConfig.from_env(env).member_recovery)
        with self.assertRaises(ValueError):CloudConfig.from_env({**env,'HCLA_MEMBER_RECOVERY':'pkce'})
        enabled={**env,'HCLA_MEMBER_AUTH':'supabase','HCLA_SUPABASE_AUTH_URL':self.config.url,'HCLA_SUPABASE_PUBLISHABLE_KEY':self.config.publishable_key,'HCLA_MEMBER_RECOVERY':'pkce'}
        self.assertTrue(CloudConfig.from_env(enabled).member_recovery)
        with self.assertRaises(ValueError):CloudConfig.from_env({**enabled,'HCLA_MEMBER_RECOVERY':'true'})

    def test_provider_uses_pkce_body_fixed_redirect_and_verified_identity(self):
        claims={'iss':self.issuer,'sub':self.subject,'aud':'authenticated','role':'authenticated','exp':int(time.time())+300}
        access='header.'+base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')+'.signature'
        user={'id':self.subject,'email':'a@example.test','email_confirmed_at':'synthetic','is_anonymous':False};calls=[]
        def transport(path,body=None,token=None,method=None):
            calls.append((path,body,token,method))
            if path.startswith('/token'):return {'access_token':access,'refresh_token':'synthetic-unused-refresh'}
            return user if path=='/user' else {}
        provider=SupabaseAuthProvider(self.config,transport=transport)
        provider.request_recovery('a@example.test','synthetic-challenge','https://hcla.example.test/account/recovery')
        self.assertTrue(calls[0][0].startswith('/recover?redirect_to=https%3A%2F%2Fhcla.example.test%2Faccount%2Frecovery'))
        self.assertEqual(calls[0][1]['code_challenge_method'],'s256')
        verified=provider.exchange_recovery(str(uuid.uuid4()),'synthetic-verifier')
        self.assertEqual(verified.principal.subject,self.subject);self.assertEqual(verified.email,'a@example.test')
        self.assertEqual(calls[-2][0],'/token?grant_type=pkce');self.assertEqual(calls[-1][0],'/user')
        provider.update_password(access,'synthetic new password',self.subject)
        self.assertEqual(calls[-1][3],'PUT');self.assertEqual(set(calls[-1][1]),{'password'})
        self.assertNotIn(access,repr(verified));self.assertNotIn('a@example.test',repr(verified))
    def test_recovery_encryption_is_purpose_stage_and_request_bound(self):
        vault=RecoveryVault('1'*64);args=(self.issuer,'pkce:'+'a'*64,'b'*64,2000000000)
        first=vault.seal('SYNTHETIC_PRIVATE_VERIFIER',*args);second=vault.seal('SYNTHETIC_PRIVATE_VERIFIER',*args)
        self.assertNotEqual(first,second);self.assertNotIn('SYNTHETIC_PRIVATE_VERIFIER',first)
        self.assertEqual(vault.open(first,*args),'SYNTHETIC_PRIVATE_VERIFIER')
        for changed in [(args[0],'access:'+'a'*64,*args[2:]),(*args[:2],'c'*64,args[3]),(*args[:3],args[3]+1)]:
            with self.assertRaises(Exception):vault.open(first,*changed)
        with self.assertRaises(Exception):SessionVault('1'*64).open(first,*args)
        with self.assertRaises(Exception):RecoveryVault('2'*64).open(first,*args)
    def test_unknown_provider_rejection_remains_uncertain_and_redacted(self):
        from urllib.error import HTTPError
        failure=HTTPError(self.config.url+'/auth/v1/user',422,'PRIVATE_SENTINEL',{},io.BytesIO(b'{"error_code":"unrecognized","msg":"PRIVATE_PASSWORD_SENTINEL"}'))
        provider=SupabaseAuthProvider(self.config)
        with patch('packages.cloud.member_auth.build_opener') as opener:
            opener.return_value.open.side_effect=failure
            with self.assertRaises(Fault) as caught:provider.update_password('PRIVATE_TOKEN_SENTINEL','PRIVATE_PASSWORD_SENTINEL',self.subject)
        self.assertEqual(caught.exception.status,503);self.assertNotIn('PRIVATE',str(caught.exception))

    def test_recovery_cookie_is_distinct_and_does_not_accept_other_principals(self):
        recovery=RecoveryAuth(MemberAuth(None,'https://hcla.example.test','1'*64,FakeMemberProvider()),'1'*64)
        for name in ['__Host-hcla','__Host-hcla-member','__Host-hcla-trial']:
            with self.assertRaises(Fault):recovery.key(name+'='+'a'*43)
        self.assertIn('Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=900',recovery.cookie('a'*43))
        self.assertNotIn('Domain=',recovery.cookie('a'*43))
        for email in ['','x','x@x','bad address@example.test']:
            with self.assertRaises(Fault):recovery.identity(email)
    def test_provider_password_rejection_is_fixed_not_a_secret_body(self):
        from urllib.error import HTTPError
        failure=HTTPError(self.config.url+'/auth/v1/user',422,'PRIVATE_MESSAGE_SENTINEL',{},io.BytesIO(b'{"error_code":"weak_password","msg":"PASSWORD_SECRET_SENTINEL"}'))
        provider=SupabaseAuthProvider(self.config)
        with patch('packages.cloud.member_auth.build_opener') as opener:
            opener.return_value.open.side_effect=failure
            with self.assertRaises(PasswordMutationRejected) as caught:provider.update_password('PRIVATE_TOKEN_SENTINEL','PRIVATE_PASSWORD_SENTINEL',self.subject)
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(str(caught.exception),'Password update rejected')

@unittest.skipUnless(baseline.DSN,'Disposable local Postgres required in cloud CI')
class RecoveryPostgresTests(unittest.TestCase):
    setUpClass=classmethod(baseline.CloudPostgresTests.setUpClass.__func__)
    tearDown=baseline.CloudPostgresTests.tearDown
    store=baseline.CloudPostgresTests.store
    request=baseline.CloudPostgresTests.request
    grant=members.MemberPostgresTests.grant
    login=members.MemberPostgresTests.login
    http=trial.CloudTrialTests.http
    make_refresh_due=members.MemberPostgresTests.make_refresh_due
    def setUp(self):
        FakeMemberProvider.reset();baseline.CloudPostgresTests.setUp(self)
    def app(self,transport=CloudFakeTransport,provider=None,enabled=True):
        cfg=CloudConfig('','https://hcla.example.test','owner',self.verifier,'1'*64,self.config,member_recovery=enabled)
        adapter=DeepSeekAdapter(base_url=self.config.base_url,model=self.config.model,api_key=self.config.api_key,transport_factory=transport,wall_timeout=3)
        return CloudApplication(cfg,store=self.store(),adapter=adapter,member_provider=provider or FakeMemberProvider())
    def begin(self,email='a@example.test'):
        app=self.app();token,result=app.recovery_auth.begin({'email':email});return app.recovery_auth.cookie(token),result
    def ready(self,email='a@example.test'):
        cookie,_=self.begin(email);code=FakeMemberProvider.recovery_code(email)
        self.assertTrue(self.app().recovery_auth.exchange({'code':code},cookie)['ready']);return cookie
    def complete(self,cookie,password='offline changed password',provider=None):
        return self.app(provider=provider).recovery_auth.complete({'password':password,'confirmation':password},cookie)
    def sign_in(self,password,user='a',provider=None):
        app=self.app(provider=provider);token,_=app.member_auth.login({'email':user+'@example.test','password':password});return app.member_auth.cookie(token)
    def test_known_unknown_email_have_same_public_state_and_no_plaintext_store(self):
        a,known=self.begin();b,unknown=self.begin('unknown@example.test')
        self.assertEqual(set(known),set(unknown));self.assertEqual(known['message'],unknown['message'])
        self.assertEqual(self.app().recovery_auth.status(a)['requested'],True);self.assertEqual(self.app().recovery_auth.status(b)['requested'],True)
        rows=str(self.admin.execute('SELECT * FROM hcla.member_recovery').fetchall())
        self.assertNotIn('a@example.test',rows);self.assertNotIn('unknown@example.test',rows);self.assertNotIn(a.split(';')[0].split('=')[1],rows)
        with self.assertRaises(Fault):self.app().recovery_auth.begin({'email':'a@example.test','redirect_to':'https://evil.test'})
    def test_code_cookie_binding_one_use_and_product_routes_remain_denied(self):
        a,_=self.begin();code=FakeMemberProvider.recovery_code('a@example.test');b,_=self.begin('b@example.test')
        with self.assertRaises(Fault):self.app().recovery_auth.exchange({'code':code},b)
        self.assertTrue(self.app().recovery_auth.exchange({'code':code},a)['ready'])
        with self.assertRaises(Fault):self.app().recovery_auth.exchange({'code':code},a)
        for path in ['/v1/conversations','/v1/member/conversations','/v1/member/topics','/v1/member/history/search?q=synthetic','/v1/member/runs/private/events']:
            status,_=self.http(self.app(),path,cookie=a);self.assertIn(status,(401,403))
        member=self.sign_in('offline member password')
        with self.assertRaises(Fault):self.app().recovery_auth.complete({'password':'offline changed password','confirmation':'offline changed password'},member)
    def test_expiry_rotation_and_tampered_envelope_never_change_password(self):
        cookie=self.ready();key=self.app().recovery_auth.key(cookie)
        self.admin.execute("UPDATE hcla.member_recovery SET secret_ciphertext='tampered' WHERE request_key=%s",(key,))
        with self.assertRaises(Fault):self.complete(cookie)
        self.assertNotIn('update',FakeMemberProvider.calls)
        changed=RecoveryAuth(self.app().member_auth,'2'*64);self.assertFalse(changed.status(cookie)['ready'])
        self.admin.execute("UPDATE hcla.member_recovery SET expires_at=clock_timestamp()-interval '1 second'")
        with self.assertRaises(Fault):self.complete(cookie)
        self.assertNotIn('update',FakeMemberProvider.calls)
    def test_success_revokes_all_old_a_sessions_and_keeps_b_isolated(self):
        a1=self.sign_in('offline member password');a2=self.sign_in('offline member password');b=self.sign_in('offline member password','b')
        cookie=self.ready();self.assertTrue(self.complete(cookie)['updated'])
        for old in [a1,a2]:
            with self.assertRaises(Fault):self.app().member_auth.require(old)
            self.assertFalse(self.app().member_auth.renewable(old))
        self.assertTrue(self.app().member_auth.require(b).tenant.startswith('member-'))
        self.assertTrue(self.app().member_auth.require(self.sign_in('offline changed password')))
        with self.assertRaises(Fault):self.sign_in('offline member password')
        row=self.admin.execute('SELECT * FROM hcla.member_recovery').fetchone();self.assertEqual(row['outcome'],'updated');self.assertIsNone(row['secret_ciphertext'])
        with self.assertRaises(Fault):self.complete(cookie)
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
    def test_uncertain_update_blocks_new_login_and_fresh_recovery_mutations(self):
        old=self.sign_in('offline member password');cookie=self.ready()
        with self.assertRaises(Fault) as refused:self.complete(cookie,'uncertain-fixture new password')
        self.assertEqual(refused.exception.status,503)
        with self.assertRaises(Fault):self.app().member_auth.require(old)
        with self.assertRaises(Fault):self.sign_in('uncertain-fixture new password')
        row=self.admin.execute('SELECT * FROM hcla.member_auth_generations').fetchone();self.assertTrue(row['reset_pending'])
        replacement,_=self.begin();code=FakeMemberProvider.recovery_code('a@example.test')
        with self.assertRaises(Fault):self.app().recovery_auth.exchange({'code':code},replacement)
        state=self.app().recovery_auth.status(replacement);self.assertTrue(state['locked']);self.assertFalse(state['ready'])
        with self.assertRaises(Fault):self.complete(replacement,'offline final password')
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
        with self.assertRaises(Fault):self.complete(cookie)
    def test_known_rejection_permits_only_explicit_bounded_attempts(self):
        cookie=self.ready();deadline=self.app().recovery_auth.status(cookie)['expires_at']
        for index in range(3):
            with self.assertRaises(Fault):self.complete(cookie,'weak-fixture password')
            self.assertEqual(self.app().recovery_auth.status(cookie)['ready'],index<2)
            self.assertFalse(self.admin.execute('SELECT reset_pending FROM hcla.member_auth_generations').fetchone()['reset_pending'])
        with self.assertRaises(Fault):self.complete(cookie,'offline next password')
        self.assertEqual(FakeMemberProvider.calls.count('update'),3)
        self.assertEqual(self.app().recovery_auth.status(cookie)['expires_at'],deadline)
    def test_login_begun_before_reset_cannot_inherit_new_generation(self):
        entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def login(self,*args):
                result=super().login(*args);entered.set();release.wait(5);return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            attempt=pool.submit(self.sign_in,'offline member password','a',Slow())
            try:
                self.assertTrue(entered.wait(3));self.complete(self.ready())
            finally:release.set()
            with self.assertRaises(Fault):attempt.result(3)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_sessions').fetchone()['n'],0)
    def test_login_during_reset_cannot_survive_or_return_after_terminal_result(self):
        updating=threading.Event();release_update=threading.Event();logging_in=threading.Event();release_login=threading.Event();cookie=self.ready()
        class SlowUpdate(FakeMemberProvider):
            def update_password(self,*args):updating.set();release_update.wait(5);return super().update_password(*args)
        class SlowLogin(FakeMemberProvider):
            def login(self,*args):
                result=super().login(*args);logging_in.set();release_login.wait(5);return result
        with ThreadPoolExecutor(max_workers=2) as pool:
            reset=pool.submit(self.complete,cookie,'offline changed password',SlowUpdate())
            try:
                self.assertTrue(updating.wait(3))
                with self.assertRaises(Fault):self.sign_in('offline member password')
                attempt=pool.submit(self.sign_in,'offline member password','a',SlowLogin());self.assertTrue(logging_in.wait(3))
                release_update.set();self.assertTrue(reset.result(3)['updated'])
            finally:release_update.set();release_login.set()
            with self.assertRaises(Fault):attempt.result(3)
        self.assertTrue(self.app().member_auth.require(self.sign_in('offline changed password')))
    def test_inflight_refresh_cannot_commit_after_reset(self):
        cookie=self.sign_in('offline member password');principal=self.app().member_auth.require(cookie);self.make_refresh_due(principal.tenant)
        entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def refresh(self,*args):
                result=super().refresh(*args);entered.set();release.wait(5);return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            attempt=pool.submit(self.app(provider=Slow()).member_auth.refresh,cookie)
            try:self.assertTrue(entered.wait(3));self.complete(self.ready())
            finally:release.set()
            with self.assertRaises(Fault):attempt.result(3)
        self.assertFalse(self.app().member_auth.renewable(cookie))
    def test_other_tenant_login_is_not_blocked_by_reset_ordering(self):
        entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def login(self,*args):
                result=super().login(*args);entered.set();release.wait(5);return result
        with ThreadPoolExecutor(max_workers=1) as pool:
            attempt=pool.submit(self.sign_in,'offline member password','b',Slow())
            try:self.assertTrue(entered.wait(3));self.complete(self.ready())
            finally:release.set()
            self.assertEqual(self.app().member_auth.require(attempt.result(3)).subject,FakeMemberProvider.identities['b@example.test'])
    def test_concurrent_completion_dispatches_one_password_mutation(self):
        cookie=self.ready();entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def update_password(self,*args):entered.set();release.wait(5);return super().update_password(*args)
        with ThreadPoolExecutor(max_workers=1) as pool:
            update=pool.submit(self.complete,cookie,'offline changed password',Slow())
            try:
                self.assertTrue(entered.wait(3))
                with self.assertRaises(Fault):self.complete(cookie)
            finally:release.set()
            self.assertTrue(update.result(3)['updated'])
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
    def test_distinct_verified_cookies_cannot_mutate_password_concurrently(self):
        first=self.ready();second=self.ready();entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def update_password(self,*args):entered.set();release.wait(5);return super().update_password(*args)
        with ThreadPoolExecutor(max_workers=1) as pool:
            update=pool.submit(self.complete,first,'offline first password',Slow())
            try:
                self.assertTrue(entered.wait(3))
                with self.assertRaises(Fault) as refused:self.complete(second,'offline second password')
                self.assertEqual(refused.exception.status,409)
                self.assertEqual(FakeMemberProvider.calls.count('update'),0)
            finally:release.set()
            self.assertTrue(update.result(3)['updated'])
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
        with self.assertRaises(Fault):self.complete(second,'offline second password')
        self.assertFalse(self.app().recovery_auth.status(second)['ready'])
        fresh=self.ready();self.assertTrue(self.complete(fresh,'offline second password')['updated'])
        self.assertEqual(FakeMemberProvider.calls.count('update'),2)

    def test_reset_cancels_old_session_and_refuses_budget_admission(self):
        from packages.cloud.entitlements import MemberCancellation
        from packages.adapter.development_budget import BudgetError
        app,cookie,tenant=self.login()
        class Cancel:
            stopped=False
            def set(self):self.stopped=True
            def is_set(self):return self.stopped
        probe=MemberCancellation(Cancel(),app.member_auth,app.member_auth.key(cookie),app.entitlements,'CONVERSATION')
        self.assertFalse(probe.is_set());self.complete(self.ready())
        with patch('packages.cloud.entitlements.time.monotonic',return_value=10**20):self.assertTrue(probe.is_set())
        with self.assertRaises(BudgetError):app.live_chat_service.budget.reserve('reset-revoked-run','reset-revoked-attempt',10)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)

    def test_link_requested_before_a_reset_cannot_become_fresh_afterward(self):
        pending,_=self.begin();old_code=FakeMemberProvider.recovery_code('a@example.test')
        self.complete(self.ready())
        with self.assertRaises(Fault):self.app().recovery_auth.exchange({'code':old_code},pending)
        self.assertFalse(self.app().recovery_auth.status(pending)['ready'])
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
        self.assertTrue(self.complete(self.ready(),'offline fresh proof password')['updated'])

    def held_update_survives_cleanup(self,password,rejected=False):
        cookie=self.ready();key=self.app().recovery_auth.key(cookie);entered=threading.Event();release=threading.Event()
        class Slow(FakeMemberProvider):
            def update_password(self,*args):entered.set();release.wait(5);return super().update_password(*args)
        with ThreadPoolExecutor(max_workers=1) as pool:
            update=pool.submit(self.complete,cookie,password,Slow())
            try:
                self.assertTrue(entered.wait(3))
                self.app().recovery_auth.begin({'email':'a@example.test'},cookie)
                self.assertEqual(self.admin.execute('SELECT phase FROM hcla.member_recovery WHERE request_key=%s',(key,)).fetchone()['phase'],'updating')
                self.admin.execute("UPDATE hcla.member_recovery SET expires_at=clock_timestamp()-interval '1 second' WHERE request_key=%s",(key,))
                self.begin('unknown@example.test')
                self.assertEqual(self.admin.execute('SELECT phase FROM hcla.member_recovery WHERE request_key=%s',(key,)).fetchone()['phase'],'updating')
            finally:release.set()
            if rejected:
                with self.assertRaises(Fault):update.result(3)
            else:self.assertTrue(update.result(3)['updated'])
        self.assertFalse(self.admin.execute('SELECT reset_pending FROM hcla.member_auth_generations').fetchone()['reset_pending'])
        self.assertEqual(FakeMemberProvider.calls.count('update'),1)
        self.begin('unknown@example.test')
        self.assertIsNone(self.admin.execute('SELECT phase FROM hcla.member_recovery WHERE request_key=%s',(key,)).fetchone())

    def test_cookie_rotation_and_expiry_cleanup_preserve_live_success_record(self):
        self.held_update_survives_cleanup('offline changed password')

    def test_cookie_rotation_and_expiry_cleanup_preserve_live_rejection_record(self):
        self.held_update_survives_cleanup('weak-fixture password',rejected=True)

    def test_cleanup_and_pool_reuse_do_not_expose_other_recovery_state(self):
        a,_=self.begin();b,_=self.begin('b@example.test');a_key=self.app().recovery_auth.key(a);b_key=self.app().recovery_auth.key(b)
        store=self.store();store.recovery_session_key=a_key
        with store.transaction():self.assertEqual(len(store.db.execute('SELECT * FROM member_recovery').fetchall()),1)
        store.recovery_session_key=None
        with store.transaction():self.assertEqual(store.db.execute('SELECT * FROM member_recovery').fetchall(),[])
        self.admin.execute("UPDATE hcla.member_recovery SET expires_at=clock_timestamp()-interval '1 second' WHERE request_key=%s",(b_key,))
        self.begin('unknown@example.test')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_recovery WHERE request_key=%s',(b_key,)).fetchone()['n'],0)
        with store.transaction():self.assertEqual(store.db.execute("SELECT current_setting('hcla.recovery_gc',true) AS value").fetchone()['value'],'off')
    def test_generation_cannot_rewind_or_be_modified_for_another_tenant(self):
        cookie=self.ready();self.complete(cookie);a=self.app();a.member_auth.require(self.sign_in('offline changed password'))
        with self.assertRaises(Exception):
            with a.stores.persistent.transaction():a.stores.persistent.db.execute('UPDATE member_auth_generations SET generation=0')
        b=self.app();b.member_auth.require(self.sign_in('offline member password','b'))
        with b.stores.persistent.transaction():self.assertEqual(b.stores.persistent.db.execute('SELECT * FROM member_auth_generations').fetchall(),[])
    def test_private_provider_failure_never_appears_in_http_response(self):
        cookie=self.ready()
        class Secret(FakeMemberProvider):
            def update_password(self,*args):raise RuntimeError('SECRET_TOKEN_PASSWORD_URL_SENTINEL')
        status,payload=self.http(self.app(provider=Secret()),'/v1/account/recovery/complete',cookie=cookie,body={'password':'offline changed password','confirmation':'offline changed password'})
        self.assertEqual(status,503);self.assertNotIn(b'SECRET_TOKEN_PASSWORD_URL_SENTINEL',payload)
        self.assertTrue(self.admin.execute('SELECT reset_pending FROM hcla.member_auth_generations').fetchone()['reset_pending'])
