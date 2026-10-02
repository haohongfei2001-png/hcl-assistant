"""Ordinary-account readiness and TEST_ONLY access; disposable fixtures only."""
import hashlib
import json
from decimal import Decimal
from types import SimpleNamespace
import unittest
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor

from packages.adapter.development_budget import BudgetError
from tests import test_cloud_postgres as baseline
from tests import test_qwen_shared as shared
from tests import test_qwen_monthly as monthly
from tests.test_qwen_provider import SMOKE_TEXT,SMOKE_QUERY

MIGRATION='20261002220025_member_readiness_and_test_entitlements.sql'


@unittest.skipUnless(baseline.DSN,'Disposable localhost Postgres required')
class MemberReadinessPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shared.SharedMonthlyPostgresTests.setUpClass.__func__(cls)
        with cls.connect(None) as admin:
            if admin.execute("SELECT to_regclass('hcla.qwen_member_test_entitlements') AS present").fetchone()['present'] is None:
                admin.execute((baseline.ROOT/'supabase/migrations'/MIGRATION).read_text())
    setUp=shared.SharedMonthlyPostgresTests.setUp
    tearDown=shared.SharedMonthlyPostgresTests.tearDown
    store=shared.SharedMonthlyPostgresTests.store
    app=shared.SharedMonthlyPostgresTests.app
    member=shared.SharedMonthlyPostgresTests.member
    claim=shared.SharedMonthlyPostgresTests.claim
    ready=shared.SharedMonthlyPostgresTests.ready
    budget=shared.SharedMonthlyPostgresTests.budget
    complete=shared.SharedMonthlyPostgresTests.complete
    request=shared.SharedMonthlyPostgresTests.request
    http=shared.SharedMonthlyPostgresTests.http

    def parent(self):return hashlib.sha256(self.monthly_config.policy().encode()).hexdigest()
    def authorize(self,key='readiness-fixture'):
        self.admin.execute("INSERT INTO hcla.qwen_member_readiness_authorizations(authorization_id,parent_policy_sha256,enabled,starts_at,expires_at,approval_evidence_digest) VALUES(%s,%s,true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',repeat('d',64))",(key,self.parent()))
    def grant_member(self,name='a',*,readiness=True,chat=True,requests=100,cost='500',expired=False):
        app,cookie,tenant,fake=self.member(name,grant=False)
        self.admin.execute("INSERT INTO hcla.qwen_member_test_entitlements(tenant,grant_id,parent_policy_sha256,enabled,starts_at,expires_at,readiness_enabled,chat_enabled,temporary_enabled,persistent_enabled,max_requests,max_cost_cny,approval_evidence_digest) VALUES(%s,%s,%s,true,clock_timestamp()-interval '1 hour',clock_timestamp()+%s::interval,%s,%s,true,true,%s,%s,repeat('e',64))",(tenant,'test-grant-'+name,self.parent(),'-1 minute' if expired else '1 hour',readiness,chat,requests,cost))
        return app,cookie,tenant,fake
    def fresh(self,cookie):
        app,fake=self.app()
        app.authenticate_member(SimpleNamespace(headers={'Cookie':cookie,'Host':'hcla.example.test','Origin':'https://hcla.example.test','X-HCLA-Request':'1'},command='POST'))
        return app,fake
    def smoke(self,app,cookie,text=SMOKE_TEXT):
        cid='temp-'+str(uuid.uuid4());request=self.request({'id':cid,'memory':'TEMPORARY'},text);request['member_readiness_check']=True
        request['development_execution']={'schema_version':'1.0','capability_id':'belief_interpretation','query':SMOKE_QUERY,'input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}
        return self.http(app,'/v1/member/temporary/execute',cookie=cookie,body={'conversation_id':cid,'request_id':str(uuid.uuid4()),'snapshot':None,'request':request})

    def test_default_closed_and_signup_never_grants_testing_or_readiness(self):
        app,cookie,tenant,fake=self.member('a',grant=False)
        app.member_auth.register({'email':'a@example.test','password':'offline member password'})
        status=app.member_status(cookie)
        self.assertFalse(status['model_enabled']);self.assertFalse(status['readiness_available'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_test_entitlements').fetchone()['n'],0)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_readiness_authorizations').fetchone()['n'],0)
        self.assertEqual(fake.post_calls,0)

    def test_test_only_member_runs_one_exact_smoke_then_authorized_ordinary_chat(self):
        self.authorize();app,cookie,tenant,fake=self.grant_member()
        status=app.member_status(cookie)
        self.assertTrue(status['readiness_available']);self.assertFalse(status['model_enabled'])
        self.assertEqual(status['entitlements']['access_kind'],'TEST_ONLY')
        code,raw=self.smoke(app,cookie);self.assertEqual(code,200,raw)
        packet=[json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith('data: ')][-1]['payload']
        run=packet['view']['runs'][-1]
        self.assertEqual(run['run_receipt']['outcome'],'COMPLETED',run)
        self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED');self.assertEqual(fake.post_calls,1)
        app2,fake2=self.fresh(cookie);status=app2.member_status(cookie)
        self.assertTrue(status['model_enabled']);self.assertFalse(status['readiness_required'])
        store=app2.stores.persistent;conv=store.conversation(tenant)
        run=app2.controller(store).handle_interaction(tenant,self.request(conv,'ORIGINAL_ORDINARY_TEST_CHAT'),defer=True)
        result=app2.execute(tenant,run['run_id']);self.assertEqual(result['run_receipt']['outcome'],'COMPLETED',result)
        self.assertEqual(fake2.post_calls,1)
        rows=self.admin.execute('SELECT actor_tenant,kind,entitlement_kind,membership_evidence_digest,membership_verification,test_evidence_digest,settled FROM hcla.qwen_monthly_attempts').fetchall()
        self.assertEqual({r['actor_tenant'] for r in rows},{tenant});self.assertEqual({r['kind'] for r in rows},{'SMOKE','MEMBER'})
        self.assertTrue(all(r['settled'] and r['entitlement_kind']=='TEST_ONLY' and r['membership_evidence_digest'] is None and r['membership_verification'] is None for r in rows))
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)
        self.assertEqual(self.admin.execute('SELECT policy FROM hcla.qwen_monthly_authorization').fetchone()['policy'],self.monthly_config.policy())
        self.assertNotIn(SMOKE_TEXT,str(rows))

    def test_readiness_grant_does_not_create_paid_or_unapproved_chat_rights(self):
        self.authorize();app,cookie,tenant,fake=self.grant_member(chat=False)
        self.assertEqual(self.smoke(app,cookie)[0],200)
        next_app,_=self.fresh(cookie);status=next_app.member_status(cookie)
        self.assertFalse(status['model_enabled']);self.assertFalse(status['entitlements']['enabled'])
        self.assertEqual(status['entitlements']['access_kind'],'TEST_ONLY')
        self.assertFalse(status['entitlements']['test_chat_enabled'])
        with self.assertRaises(Exception):next_app.entitlements.require('CONVERSATION')

    def test_exact_fresh_smoke_and_verified_account_are_required(self):
        self.authorize();app,cookie,tenant,fake=self.grant_member()
        code,_=self.smoke(app,cookie,'Arbitrary text must not become the readiness call')
        self.assertEqual(code,403);self.assertEqual(fake.post_calls,0)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_attempts').fetchone()['n'],0)
        outsider,out_cookie,_,out_fake=self.member('b',grant=False)
        self.assertFalse(outsider.member_status(out_cookie)['readiness_available'])
        self.assertEqual(self.smoke(outsider,out_cookie)[0],403);self.assertEqual(out_fake.post_calls,0)
        unsigned,_=self.app();self.assertEqual(self.smoke(unsigned,None)[0],401)

    def test_paid_member_bootstrap_remains_paid_and_has_immutable_attribution(self):
        self.authorize();app,cookie,tenant,fake=self.member('a')
        self.assertTrue(app.member_status(cookie)['readiness_available'])
        code,raw=self.smoke(app,cookie);self.assertEqual(code,200,raw)
        row=self.admin.execute('SELECT entitlement_kind,readiness_authorization_id,membership_evidence_digest,test_evidence_digest FROM hcla.qwen_monthly_attempts').fetchone()
        self.assertEqual(row['entitlement_kind'],'PAID_MEMBERSHIP');self.assertEqual(row['readiness_authorization_id'],'readiness-fixture')
        self.assertIsNotNone(row['membership_evidence_digest']);self.assertIsNone(row['test_evidence_digest'])
        with self.assertRaises(Exception):
            with app.stores.persistent.transaction():app.stores.persistent.db.execute("UPDATE qwen_monthly_attempts SET entitlement_kind='TEST_ONLY'")

    def test_unknown_readiness_consumes_the_single_attempt_without_releasing_cost(self):
        self.authorize();app,cookie,tenant,_=self.grant_member()
        budget=self.claim(app,'unknown-readiness')
        budget.memory='TEMPORARY';app.entitlements.readiness=True
        budget.authorize_request({'member_readiness_check':True,'expected_state_version':0,'event':{'text':SMOKE_TEXT},'development_execution':{'capability_id':'belief_interpretation','query':SMOKE_QUERY}},{'memory':'TEMPORARY'})
        budget.reserve('unknown-readiness','attempt',100);budget.finish('unknown-readiness','attempt','unknown')
        fresh,_=self.fresh(cookie)
        self.assertFalse(fresh.member_status(cookie)['readiness_available'])
        self.assertFalse(fresh.member_status(cookie)['model_enabled'])
        row=self.admin.execute('SELECT charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts').fetchone()
        self.assertEqual(row['charged_cny'],Decimal('12.295272'));self.assertEqual(row['charged_cny'],row['reserved_cny'])

    def test_two_entitled_accounts_contend_for_exactly_one_readiness_call(self):
        self.authorize();a,ca,_,fa=self.grant_member('a');b,cb,_,fb=self.grant_member('b')
        barrier=threading.Barrier(2)
        def execute(item):
            app,cookie=item;barrier.wait();return self.smoke(app,cookie)
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(execute,((a,ca),(b,cb))))
        self.assertEqual(fa.post_calls+fb.post_calls,1)
        rows=self.admin.execute('SELECT kind,readiness_authorization_id FROM hcla.qwen_monthly_attempts').fetchall()
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['kind'],'SMOKE')
        # A stale explicit readiness click cannot become an ordinary second call.
        self.smoke(a,ca);self.assertEqual(fa.post_calls+fb.post_calls,1)

    def interrupt_before_publication(self,target,expired=False):
        self.authorize();app,cookie,tenant,fake=self.grant_member('a')
        generate=app.live_chat_service.adapter.generate
        def revoke(*args,**kwargs):
            result=generate(*args,**kwargs)
            table='qwen_member_readiness_authorizations' if target=='readiness' else 'qwen_member_test_entitlements'
            if expired:
                # Disposable-fixture time travel only: change the synthetic row,
                # atomically restoring the immutable trigger before app reads.
                # Production immutable-term rejection is tested separately.
                trigger='immutable_member_readiness' if target=='readiness' else 'immutable_member_test_grant'
                with self.admin.transaction():
                    self.admin.execute('ALTER TABLE hcla.'+table+' DISABLE TRIGGER '+trigger)
                    self.admin.execute("UPDATE hcla."+table+" SET starts_at=clock_timestamp()-interval '2 hours',expires_at=clock_timestamp()-interval '1 hour'")
                    self.admin.execute('ALTER TABLE hcla.'+table+' ENABLE TRIGGER '+trigger)
            else:self.admin.execute('UPDATE hcla.'+table+' SET enabled=false')
            return result
        app.live_chat_service.adapter.generate=revoke
        code,raw=self.smoke(app,cookie)
        self.assertEqual(code,200,raw);self.assertEqual(fake.post_calls,1)
        row=self.admin.execute('SELECT settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts').fetchone()
        self.assertFalse(row['settled']);self.assertEqual(row['charged_cny'],row['reserved_cny'])
        self.assertNotIn('"type": "cloud.completed"',raw.decode())
        emitted=[json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith('data: ') and 'cloud.run' in line]
        self.assertFalse(any(event['payload'].get('answer') is not None for event in emitted))
        self.assertFalse(app.live_chat_service.budget.smoke_ready())

    def test_readiness_revocation_before_publication_withholds_answer_and_cost_release(self):
        self.interrupt_before_publication('readiness')

    def test_test_grant_revocation_before_publication_withholds_answer_and_cost_release(self):
        self.interrupt_before_publication('test')

    def test_readiness_expiry_before_publication_withholds_answer_and_cost_release(self):
        self.interrupt_before_publication('readiness',expired=True)

    def test_test_grant_expiry_before_publication_withholds_answer_and_cost_release(self):
        self.interrupt_before_publication('test',expired=True)

    def test_test_caps_are_lifetime_and_do_not_reset_with_shared_month(self):
        self.ready();app,cookie,tenant,_=self.grant_member(requests=1,cost='13')
        budget=self.claim(app,'lifetime-one');budget.reserve('lifetime-one','attempt',100);budget.finish('lifetime-one','attempt','unknown')
        monthly.MonthlyPostgresTests.clock(self,'2032-02-15 00:00:00+00')
        try:
            fresh,_=self.fresh(cookie);budget=self.claim(fresh,'lifetime-two')
            self.admin.execute("UPDATE hcla.execution SET expires_at=hcla.qwen_monthly_clock()+interval '270 seconds' WHERE run_id='lifetime-two'")
            with self.assertRaises(BudgetError):budget.reserve('lifetime-two','attempt',100)
        finally:self.admin.execute("CREATE OR REPLACE FUNCTION hcla.qwen_monthly_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS 'SELECT clock_timestamp()'")

    def test_expired_revoked_overlapping_and_changed_authorization_fail_closed(self):
        self.authorize();expired,cookie,_,_=self.grant_member('a',expired=True)
        self.assertFalse(expired.member_status(cookie)['readiness_available'])
        app,cookie,tenant,_=self.grant_member('b')
        self.admin.execute('UPDATE hcla.qwen_member_test_entitlements SET enabled=false WHERE tenant=%s',(tenant,))
        self.assertFalse(app.member_status(cookie)['readiness_available'])
        self.admin.execute('UPDATE hcla.qwen_member_test_entitlements SET enabled=true WHERE tenant=%s',(tenant,))
        self.authorize('overlap-fixture');self.assertFalse(app.member_status(cookie)['readiness_available'])
        for sql in ("UPDATE hcla.qwen_member_test_entitlements SET max_cost_cny=501", "UPDATE hcla.qwen_member_test_entitlements SET expires_at=expires_at+interval '1 day'", "DELETE FROM hcla.qwen_member_readiness_authorizations"):
            with self.assertRaises(Exception):self.admin.execute(sql)

    def test_runtime_role_cannot_self_grant_or_read_other_test_accounts(self):
        self.ready();app,_,tenant,_=self.grant_member('a');other,_,other_tenant,_=self.grant_member('b')
        store=app.stores.persistent
        with store.transaction():self.assertEqual({r['tenant'] for r in store.db.execute('SELECT tenant FROM qwen_member_test_entitlements').fetchall()},{tenant})
        for sql in ('UPDATE qwen_member_test_entitlements SET enabled=true','DELETE FROM qwen_member_test_entitlements',"INSERT INTO qwen_member_readiness_authorizations(authorization_id) VALUES('self-grant')"):
            with self.assertRaises(Exception):
                with store.transaction():store.db.execute(sql)
        for role in ('anon','authenticated'):
            if not self.admin.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():continue
            self.assertFalse(self.admin.execute("SELECT has_table_privilege(%s,'hcla.qwen_member_test_entitlements','SELECT') AS permitted",(role,)).fetchone()['permitted'])
