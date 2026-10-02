"""One shared CNY500 month, private actor audit; fake auth/provider only."""
from decimal import Decimal
import json
import os
from types import SimpleNamespace
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import unittest

from packages.adapter.development_budget import BudgetError
from packages.cloud.qwen_config import QwenConfig
from packages.cloud.qwen_monthly_budget import QwenMonthlyBudget
from packages.cloud.qwen_entitlements import QwenMonthlyMemberBudget
from packages.cloud.config import CloudConfig
from packages.cloud.lifecycle import Lifecycle
from packages.adapter.provider import create_adapter
from apps.api.cloud_server import CloudApplication
from tests import test_cloud_postgres as baseline
from tests import test_qwen_monthly as monthly
from tests import test_cloud_trial as trial
from tests.test_qwen_provider import SECRET,FakeTransport,event,qchunk,DONE,usage
from tests.support.member_provider import FakeMemberProvider


def shared_grant():
    grant=monthly.monthly_grant()
    grant['monthly']['scope']='AUTHENTICATED_SHARED'
    return grant


class SharedConfigTests(unittest.TestCase):
    def test_shared_template_is_versioned_and_never_per_user_funding(self):
        cfg=QwenConfig.from_grant(shared_grant(),SECRET)
        policy=json.loads(cfg.policy())
        self.assertEqual(policy['version'],3)
        self.assertEqual(policy['member_subcaps'],'CALENDAR_MONTH_WITHIN_SHARED_CEILING')
        self.assertEqual(policy['membership_requirement'],'SERVER_VERIFIED_PAID_MEMBERSHIP')
        self.assertEqual(policy['monthly'],{'timezone':'Asia/Shanghai','scope':'AUTHENTICATED_SHARED','limit_cny':'500'})
        for scope in ('ANONYMOUS','PER_USER','ALL_USERS_UNLIMITED'):
            grant=shared_grant();grant['monthly']['scope']=scope
            with self.assertRaises(ValueError):QwenConfig.from_grant(grant,SECRET)


@unittest.skipUnless(baseline.DSN,'Disposable localhost Postgres required for shared-budget guards')
class SharedMonthlyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        monthly.MonthlyPostgresTests.setUpClass.__func__(cls)
        cls.monthly_config=QwenConfig.from_grant(shared_grant(),SECRET)
    def setUp(self):
        baseline.CloudPostgresTests.setUp(self);FakeMemberProvider.reset();self.counter=0
        self.admin.execute('INSERT INTO hcla.qwen_monthly_authorization VALUES(1,%s,true)',(self.monthly_config.policy(),))
    tearDown=baseline.CloudPostgresTests.tearDown
    store=baseline.CloudPostgresTests.store
    budget=monthly.MonthlyPostgresTests.budget
    complete=monthly.MonthlyPostgresTests.complete
    request=baseline.CloudPostgresTests.request
    http=trial.CloudTrialTests.http

    def app(self,*,members=True):
        fake=FakeTransport([event(qchunk('Synthetic answer.')),event(qchunk(finish='stop',usage=usage())),DONE])
        cfg=CloudConfig('','https://hcla.example.test','owner',self.verifier,'1'*64,self.monthly_config,selected_provider='qwen')
        app=CloudApplication(cfg,store=self.store(),adapter=create_adapter(self.monthly_config,transport_factory=lambda *_:fake),
                             runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT'),member_provider=FakeMemberProvider() if members else None)
        return app,fake
    def member(self,name='a',*,grant=True,temporary=True,persistent=True,requests=1000000,cost='500',paid=True):
        app,fake=self.app()
        token,_=app.member_auth.login({'email':name+'@example.test','password':'offline member password'})
        cookie=app.member_auth.cookie(token);tenant=app.stores.persistent.tenant
        if grant:
            self.admin.execute("INSERT INTO hcla.qwen_member_entitlements(tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_cny,paid_membership,payment_verification,paid_evidence_digest,paid_verified_at) VALUES(%s,%s,true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',%s,%s,%s,%s,%s,'ADMIN_VERIFIED',repeat('a',64),clock_timestamp())",(tenant,'shared-fixture-'+name,temporary,persistent,requests,cost,paid))
        app.authenticate_member(SimpleNamespace(headers={'Cookie':cookie,'Host':'hcla.example.test','Origin':'https://hcla.example.test','X-HCLA-Request':'1'},command='POST'))
        return app,cookie,tenant,fake
    def claim(self,app,label):
        store=app.stores.persistent;owner=app.lifecycle.claim(label)
        store.fence=(label,owner)
        return app.live_chat_service.budget
    def ready(self):self.complete(self.budget())

    def test_owner_smoke_unlocks_members_and_delayed_member_publication_settles(self):
        blocked,_,_,fake=self.member('a')
        self.assertIsNone(blocked.live_chat_service);self.assertEqual(fake.post_calls,0)
        # Real owner temporary HCL smoke and subsequent ordinary owner flow.
        monthly.MonthlyPostgresTests.test_cloud_temporary_smoke_then_delayed_persistent_owner_publication_settles(self)
        app,cookie,tenant,fake=self.member('b')
        status=app.member_status(cookie);self.assertTrue(status['model_enabled']);self.assertTrue(status['entitlements']['enabled'])
        store=app.stores.persistent;conv=store.conversation(tenant);ctrl=app.controller(store)
        run=ctrl.handle_interaction(tenant,self.request(conv,'MEMBER_B_SYNTHETIC_PRIVATE_CANARY'),defer=True)
        put=store.put
        def slow(tenant,kind,body):
            result=put(tenant,kind,body)
            if kind=='run' and body.get('run_receipt',{}).get('outcome')=='COMPLETED' and not body.get('pending'):time.sleep(.3)
            return result
        store.put=slow
        result=app.execute(tenant,run['run_id'])
        self.assertEqual(result['run_receipt']['outcome'],'COMPLETED',result['run_receipt'])
        self.assertEqual(fake.post_calls,1)
        row=self.admin.execute('SELECT actor_tenant,kind,settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts WHERE actor_tenant=%s',(tenant,)).fetchone()
        self.assertEqual(row['kind'],'MEMBER');self.assertTrue(row['settled']);self.assertLess(row['charged_cny'],row['reserved_cny'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_periods').fetchone()['n'],1)
        fresh,_=self.app();code,_=self.http(fresh,'/v1/member/budget')
        self.assertEqual(code,401)

    def test_cross_actor_concurrency_and_hidden_costs_share_one_500_cap(self):
        self.ready();a,_,ta,_=self.member('a');b,_,tb,_=self.member('b')
        def race(budgets,prefix):
            barrier=threading.Barrier(2)
            def reserve(i):
                barrier.wait()
                try:return budgets[i].reserve(prefix+str(i),'attempt',100).granted
                except BudgetError:return False
            with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(reserve,(0,1)))
        budgets=[self.claim(a,'a-first'),self.claim(b,'b-first')]
        results=race(budgets,'race-');self.assertEqual(sum(results),1)
        winner=results.index(True);budgets[winner].finish('race-'+str(winner),'attempt','unknown')
        # Hidden actor reservations count before a simultaneous near-cap race.
        for index in range(38):
            app=(a,b)[index%2];budget=self.claim(app,'fill-'+str(index))
            budget.reserve('fill-'+str(index),'attempt',100)
            budget.finish('fill-'+str(index),'attempt','unknown')
        budgets=[self.claim(a,'near-a'),self.claim(b,'near-b')]
        results=race(budgets,'near-');self.assertEqual(sum(results),1)
        winner=results.index(True);budgets[winner].finish('near-'+str(winner),'attempt','unknown')
        self.assertEqual(self.admin.execute("SELECT count(*) AS n FROM hcla.qwen_monthly_attempts WHERE kind='MEMBER'").fetchone()['n'],40)
        summary=a.live_chat_service.budget.snapshot();other=b.live_chat_service.budget.snapshot()
        self.assertEqual(summary['charged_cost_cny'],other['charged_cost_cny']);self.assertLessEqual(Decimal(summary['charged_cost_cny']),500)
        for app,tenant,not_tenant in ((a,ta,tb),(b,tb,ta)):
            store=app.stores.persistent;store.fence=None
            with store.transaction():
                rows=store.db.execute('SELECT actor_tenant FROM qwen_monthly_attempts').fetchall()
                self.assertEqual({r['actor_tenant'] for r in rows},{tenant})
                self.assertNotIn(not_tenant,json.dumps(store.db.execute('SELECT qwen_monthly_shared_state() AS state').fetchone()['state']))
                self.assertEqual(store.db.execute('UPDATE qwen_monthly_attempts SET charged_cny=0 WHERE actor_tenant=? RETURNING run_key',(not_tenant,)).fetchall(),[])
            with self.assertRaises(Exception):
                with store.transaction():store.db.execute('UPDATE qwen_monthly_authorization SET enabled=false')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_periods').fetchone()['n'],1)

    def test_revoked_expired_wrong_memory_and_changed_grants_stay_closed(self):
        self.ready();app,_,tenant,_=self.member('a');budget=self.claim(app,'revoked')
        self.admin.execute('UPDATE hcla.qwen_member_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
        with self.assertRaises(BudgetError):budget.reserve('revoked','attempt',100)
        self.admin.execute("UPDATE hcla.qwen_member_entitlements SET enabled=true,expires_at=clock_timestamp()-interval '1 second' WHERE tenant=%s",(tenant,))
        with self.assertRaises(BudgetError):budget.reserve('expired','attempt',100)
        self.admin.execute("UPDATE hcla.qwen_member_entitlements SET expires_at=clock_timestamp()+interval '1 hour',persistent_enabled=false WHERE tenant=%s",(tenant,))
        with self.assertRaises(BudgetError):budget.reserve('memory','attempt',100)
        self.admin.execute('UPDATE hcla.qwen_member_entitlements SET persistent_enabled=true WHERE tenant=%s',(tenant,))
        budget.reserve('permitted','attempt',100);budget.finish('permitted','attempt','completed',100,20)
        self.admin.execute('UPDATE hcla.qwen_member_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
        with self.assertRaises(BudgetError):budget.reconcile_completed('permitted','attempt')
        row=self.admin.execute('SELECT settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts WHERE actor_tenant=%s',(tenant,)).fetchone()
        self.assertFalse(row['settled']);self.assertEqual(row['charged_cny'],row['reserved_cny'])

    def test_database_actor_grant_and_global_helper_privileges(self):
        self.ready();a,_,ta,_=self.member('a');b,_,tb,_=self.member('b')
        budget=self.claim(a,'actor-a');budget.reserve('actor-a','attempt',100);budget.finish('actor-a','attempt','unknown')
        store=a.stores.persistent
        for sql in ("UPDATE qwen_monthly_attempts SET actor_tenant='hcla-owner'",
                    "UPDATE qwen_monthly_attempts SET entitlement_grant_id='invented'",
                    "UPDATE qwen_monthly_attempts SET memory_scope='TEMPORARY'",
                    "UPDATE qwen_monthly_attempts SET period_key='2100-01'"):
            with self.assertRaises(Exception):
                with store.transaction():store.db.execute(sql)
        helper=self.admin.execute("SELECT r.rolsuper,r.rolbypassrls,p.proconfig FROM pg_proc p JOIN pg_roles r ON r.oid=p.proowner WHERE p.oid='hcla.qwen_monthly_shared_state()'::regprocedure").fetchone()
        self.assertTrue(helper['rolsuper'] or helper['rolbypassrls'])
        self.assertIn('row_security=off',helper['proconfig'])
        for role in ('anon','authenticated'):
            present=self.admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone()
            if present:self.assertFalse(self.admin.execute("SELECT has_function_privilege(%s,'hcla.qwen_monthly_shared_state()','EXECUTE') AS allowed",(role,)).fetchone()['allowed'])
        # Neither a new budget identity nor a deployment may replace this policy.
        with self.assertRaises(Exception):self.admin.execute("UPDATE hcla.qwen_monthly_authorization SET policy=replace(policy,'AUTHENTICATED_SHARED','OWNER_ONLY')")

    def test_member_temporary_and_topic_audit_keep_scope_and_privacy(self):
        import uuid
        self.ready();app,cookie,tenant,fake=self.member('a')
        cid='temp-'+str(uuid.uuid4());request=self.request({'id':cid,'memory':'TEMPORARY'},'MEMBER_TEMP_SHARED_CANARY')
        code,payload=self.http(app,'/v1/member/temporary/execute',cookie=cookie,body={'conversation_id':cid,'request_id':str(uuid.uuid4()),'snapshot':None,'request':request})
        self.assertEqual(code,200,payload)
        packet=[json.loads(line[6:]) for line in payload.decode().splitlines() if line.startswith('data: ')][-1]['payload']
        self.assertEqual(packet['view']['runs'][-1]['run_receipt']['outcome'],'COMPLETED',packet)
        self.assertEqual(fake.post_calls,1)
        topic_app,_,topic_tenant,topic_fake=self.member('b')
        store=topic_app.stores.persistent;topic=store.topic(topic_tenant,'synthetic topic')
        conv=store.conversation(topic_tenant,topic_id=topic['id'],memory='TOPIC')
        request=self.request(conv,'MEMBER_TOPIC_SHARED_CANARY');request['scope']['topic_id']=topic['id']
        run=topic_app.controller(store).handle_interaction(topic_tenant,request,defer=True)
        result=topic_app.execute(topic_tenant,run['run_id'])
        self.assertEqual(result['run_receipt']['outcome'],'COMPLETED',result['run_receipt'])
        self.assertEqual(topic_fake.post_calls,1)
        rows=self.admin.execute("SELECT actor_tenant,memory_scope,settled FROM hcla.qwen_monthly_attempts WHERE kind='MEMBER'").fetchall()
        self.assertEqual({r['memory_scope'] for r in rows},{'TEMPORARY','TOPIC'});self.assertTrue(all(r['settled'] for r in rows))
        for table in ('qwen_monthly_attempts','objects','sources','events'):
            self.assertNotIn('MEMBER_TEMP_SHARED_CANARY',str(self.admin.execute('SELECT * FROM hcla.'+table).fetchall()))
        status,payload=self.http(app,'/v1/member/budget',cookie=cookie)
        self.assertEqual(status,200,payload);budget=json.loads(payload)
        self.assertEqual(budget['scope'],'AUTHENTICATED_SHARED');self.assertEqual(budget['max_cost_cny'],'500')
        self.assertEqual(budget['actor_request_count'],1);self.assertNotIn(topic_tenant,payload.decode())

    def test_shared_month_rollover_preserves_previous_actor_rows_and_subcaps(self):
        self.ready();a,_,ta,_=self.member('a',requests=1);b,_,tb,_=self.member('b',requests=1)
        clock=monthly.MonthlyPostgresTests.clock
        clock(self,'2032-01-15 00:00:00+00')
        try:
            for app,label in ((a,'month-a'),(b,'month-b')):
                budget=self.claim(app,label)
                self.admin.execute("UPDATE hcla.execution SET expires_at=hcla.qwen_monthly_clock()+interval '270 seconds' WHERE run_id=%s",(label,))
                budget.reserve(label,'attempt',100);budget.finish(label,'attempt','unknown')
            before=self.admin.execute("SELECT actor_tenant,charged_cny FROM hcla.qwen_monthly_attempts WHERE period_key='2032-01' ORDER BY actor_tenant").fetchall()
            clock(self,'2032-02-01 00:00:00+00')
            fresh=self.claim(a,'next-month')
            self.admin.execute("UPDATE hcla.execution SET expires_at=hcla.qwen_monthly_clock()+interval '270 seconds' WHERE run_id='next-month'")
            self.assertEqual(fresh.snapshot()['charged_cost_cny'],'0')
            fresh.reserve('next-month','attempt',100);fresh.finish('next-month','attempt','unknown')
            self.assertEqual(self.admin.execute("SELECT actor_tenant,charged_cny FROM hcla.qwen_monthly_attempts WHERE period_key='2032-01' ORDER BY actor_tenant").fetchall(),before)
            self.assertEqual(fresh.snapshot()['period'],'2032-02')
            self.assertEqual(fresh.snapshot()['max_cost_cny'],'500')
        finally:
            self.admin.execute("CREATE OR REPLACE FUNCTION hcla.qwen_monthly_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS 'SELECT clock_timestamp()'")

    def test_member_revocation_after_publication_never_releases_reservation(self):
        self.ready();app,_,tenant,fake=self.member('a');store=app.stores.persistent
        conv=store.conversation(tenant);run=app.controller(store).handle_interaction(tenant,self.request(conv),defer=True)
        put=store.put
        def revoke(tenant,kind,body):
            result=put(tenant,kind,body)
            if kind=='run' and body.get('run_receipt',{}).get('outcome')=='COMPLETED' and not body.get('pending'):
                self.admin.execute('UPDATE hcla.qwen_member_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
            return result
        store.put=revoke;app.execute(tenant,run['run_id'])
        self.assertEqual(fake.post_calls,1)
        row=self.admin.execute('SELECT settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts WHERE actor_tenant=%s',(tenant,)).fetchone()
        self.assertFalse(row['settled']);self.assertEqual(row['charged_cny'],row['reserved_cny'])

    def test_registered_and_enabled_but_unpaid_member_cannot_call_model(self):
        self.ready();app,cookie,tenant,fake=self.member('a',paid=False)
        self.admin.execute("UPDATE hcla.qwen_member_entitlements SET payment_verification='NONE',paid_evidence_digest=NULL,paid_verified_at=NULL WHERE tenant=%s",(tenant,))
        status=app.member_status(cookie);self.assertFalse(status['model_enabled']);self.assertFalse(status['entitlements']['enabled'])
        self.assertTrue(status['entitlements']['membership_required'])
        self.assertIn('注册账号不包含',status['entitlements']['reason'])
        budget=self.claim(app,'unpaid')
        with self.assertRaises(BudgetError):budget.reserve('unpaid','attempt',100)
        self.assertEqual(fake.post_calls,0)
        with self.assertRaises(Exception):self.admin.execute('UPDATE hcla.qwen_member_entitlements SET paid_membership=true WHERE tenant=%s',(tenant,))
        with app.stores.persistent.transaction():
            with self.assertRaises(Exception):app.stores.persistent.db.execute("UPDATE qwen_member_entitlements SET paid_membership=true,payment_verification='ADMIN_VERIFIED',paid_evidence_digest=repeat('a',64),paid_verified_at=clock_timestamp()")

    def test_registration_and_status_never_install_paid_rights_or_spend(self):
        self.ready();app,cookie,tenant,fake=self.member('a',grant=False)
        response=app.member_auth.register({'email':'a@example.test','password':'offline member password'})
        self.assertTrue(response['confirmation_required'])
        before=self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_attempts').fetchone()['n']
        status=app.member_status(cookie)
        self.assertFalse(status['model_enabled']);self.assertFalse(status['entitlements']['enabled'])
        self.assertTrue(status['entitlements']['membership_required'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_attempts').fetchone()['n'],before)
        self.assertEqual(fake.post_calls,0)

    def test_membership_expiry_keeps_identity_but_revokes_status_and_admission(self):
        self.ready();app,cookie,tenant,fake=self.member('a')
        status=app.member_status(cookie)
        self.assertTrue(status['model_enabled'])
        self.assertGreater(status['entitlements']['expires_at'],time.time())
        self.admin.execute("UPDATE hcla.qwen_member_entitlements SET expires_at=clock_timestamp()-interval '1 second' WHERE tenant=%s",(tenant,))
        expired=app.member_status(cookie)
        self.assertTrue(expired['authenticated']);self.assertEqual(expired['account_scope'],tenant)
        self.assertFalse(expired['model_enabled']);self.assertFalse(expired['entitlements']['enabled'])
        self.assertIn('已到期',expired['entitlements']['reason'])
        with self.assertRaises(BudgetError):self.claim(app,'expired-membership').reserve('expired-membership','attempt',100)
        self.assertEqual(fake.post_calls,0)
