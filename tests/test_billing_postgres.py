"""Actual isolated Postgres order/entitlement lifecycle; all prices are fixtures."""
from dataclasses import asdict, replace
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
import uuid
from unittest.mock import Mock
from packages.billing.service import BillingService

from packages.billing.contracts import BillingError, Checkout, PaymentState, VerifiedPayment
from packages.billing.postgres import BillingActor, BillingRepository, BillingWorker
from tests import test_cloud_postgres as baseline
from tests import test_qwen_member_readiness as readiness

MIGRATION='20261002225736_consumer_billing_lifecycle.sql'


@unittest.skipUnless(baseline.DSN,'Disposable localhost Postgres required')
class BillingPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        readiness.MemberReadinessPostgresTests.setUpClass.__func__(cls)
        with cls.connect(None) as admin:
            if admin.execute("SELECT to_regclass('hcla.billing_orders') AS present").fetchone()['present'] is None:
                admin.execute((baseline.ROOT/'supabase/migrations'/MIGRATION).read_text())
    setUp=readiness.MemberReadinessPostgresTests.setUp
    tearDown=readiness.MemberReadinessPostgresTests.tearDown
    store=readiness.MemberReadinessPostgresTests.store
    app=readiness.MemberReadinessPostgresTests.app
    member=readiness.MemberReadinessPostgresTests.member
    ready=readiness.MemberReadinessPostgresTests.ready
    budget=readiness.MemberReadinessPostgresTests.budget
    complete=readiness.MemberReadinessPostgresTests.complete
    http=readiness.MemberReadinessPostgresTests.http

    def enabled(self,amount=990):
        self.ready()
        self.admin.execute("INSERT INTO hcla.billing_configuration(singleton,enabled,provider,merchant,checkout_origins,approval_digest) VALUES(1,true,'fixture','offline-merchant',ARRAY['https://checkout.example.test'],repeat('a',64))")
        self.admin.execute("INSERT INTO hcla.billing_plan_versions(plan_id,version,title,enabled,amount_minor,duration_days,max_requests,max_cost_cny,temporary_enabled,persistent_enabled,terms_digest,approved_at) VALUES('fixture-plan',1,'Offline fixture',true,%s,30,20,25,true,true,repeat('b',64),clock_timestamp())",(amount,))

    def repository(self,name='a'):
        app,cookie,tenant,_=self.member(name,grant=False)
        connection=self.connect();connection.execute('SET ROLE hcla_billing_worker');self.addCleanup(connection.close)
        repo=BillingRepository(app.stores.persistent,BillingWorker(connection))
        repo.application=app;repo.cookie=cookie
        return repo,BillingActor(tenant,app.stores.persistent.member_session_key)

    def new_order(self,repo,actor,key=None):
        return repo.create_order(actor,'fixture-plan',1,key or str(uuid.uuid4()),'b'*64,'fixture','offline-merchant')

    def proof(self,repo,actor,o=None,*,checkout=True):
        o=o or self.new_order(repo,actor)
        claimed=repo.claim_checkout(actor,o['order_id'])
        external='external-'+o['order_id']
        if checkout:repo.complete_checkout(o['order_id'],Checkout('fixture','offline-merchant',o['order_id'],external,'https://checkout.example.test/pay/'+o['order_id']))
        return VerifiedPayment('fixture','offline-merchant',o['order_id'],external,'payment-'+o['order_id'],'fixture-plan:1',o['amount_minor'],'CNY',PaymentState.CAPTURED,claimed['created_at'],0,'c'*64)

    def test_default_closed_no_plan_config_or_membership(self):
        repo,actor=self.repository()
        self.assertEqual(repo.catalog(actor),[])
        with self.assertRaises(Exception):self.new_order(repo,actor)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)

    def test_terms_idempotency_session_and_tenant_bindings(self):
        self.enabled();repo,actor=self.repository();other,other_actor=self.repository('b')
        self.assertEqual(len(repo.catalog(actor)),1)
        first=self.new_order(repo,actor,'single-click');self.assertEqual(first,self.new_order(repo,actor,'single-click'))
        with self.assertRaises(BillingError):repo.create_order(actor,'fixture-plan',2,'single-click','b'*64,'fixture','offline-merchant')
        with self.assertRaises(BillingError):other.order(other_actor,first['order_id'])
        with self.assertRaises(BillingError):repo.order(other_actor,first['order_id'])
        with self.assertRaises(Exception):repo.create_order(actor,'fixture-plan',1,'bad-terms','d'*64,'fixture','offline-merchant')
        self.admin.execute('DELETE FROM hcla.member_sessions WHERE tenant=%s',(actor.tenant,))
        with self.assertRaises(BillingError):repo.order(actor,first['order_id'])

    def test_runtime_has_no_financial_or_membership_write_authority(self):
        self.enabled();repo,actor=self.repository();o=self.new_order(repo,actor)
        with self.assertRaises(BillingError):BillingWorker(repo.store.connection)
        for statement,args in [("UPDATE billing_orders SET state='FULFILLED'",()),("SELECT billing_apply_verified(?,?::jsonb)",(o['order_id'],'{}')),("UPDATE billing_plan_versions SET enabled=false",()),("UPDATE qwen_member_entitlements SET enabled=true",())]:
            with self.subTest(statement=statement),self.assertRaises(Exception):
                with repo.store.transaction():repo.store.db.execute(statement,args)
        worker=repo.worker.connection
        for table in ('billing_orders','qwen_member_entitlements','qwen_member_test_entitlements'):
            with self.subTest(table=table),self.assertRaises(Exception):worker.execute('UPDATE hcla.'+table+' SET enabled=true' if table!='billing_orders' else "UPDATE hcla.billing_orders SET state='FULFILLED'")
        self.assertFalse(worker.execute("SELECT EXISTS(SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE p.oid='hcla.billing_apply_verified(text,jsonb)'::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE') AS allowed").fetchone()['allowed'])

    def test_checkout_claim_is_single_and_unknown_creation_queries_stored_identity(self):
        self.enabled();repo,actor=self.repository();o=self.new_order(repo,actor)
        proof=self.proof(repo,actor,o,checkout=False)
        repo.checkout_unknown(o['order_id'])
        with self.assertRaises(Exception):repo.claim_checkout(actor,o['order_id'])
        result=repo.apply_verified(proof)
        self.assertTrue(result['membership_changed'])
        self.assertEqual(repo.order(actor,o['order_id'])['external_order_id'],proof.external_order_id)

    def test_capture_replay_renewal_and_refund_ordering(self):
        self.enabled();repo,actor=self.repository();first=self.proof(repo,actor)
        self.assertTrue(repo.apply_verified(first)['membership_changed'])
        self.assertFalse(repo.apply_verified(first)['membership_changed'])
        second=self.proof(repo,actor);repo.apply_verified(second)
        rows=self.admin.execute('SELECT * FROM hcla.qwen_member_entitlements WHERE tenant=%s ORDER BY starts_at',(actor.tenant,)).fetchall()
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['expires_at'],rows[1]['starts_at'])
        self.assertTrue(all(r['paid_membership'] and r['payment_verification']=='TRUSTED_PAYMENT_EVENT' for r in rows))
        before=[(r['grant_id'],r['starts_at'],r['expires_at']) for r in rows]
        repo.apply_verified(replace(first,state=PaymentState.REFUNDED,refunded_minor=990,evidence_digest='d'*64))
        self.assertFalse(repo.apply_verified(first)['membership_changed'])
        after=self.admin.execute('SELECT * FROM hcla.qwen_member_entitlements WHERE tenant=%s ORDER BY starts_at',(actor.tenant,)).fetchall()
        self.assertEqual(before,[(r['grant_id'],r['starts_at'],r['expires_at']) for r in after])
        self.assertFalse(after[0]['enabled']);self.assertTrue(after[1]['enabled'])

    def test_concurrent_renewal_fulfilment_has_no_overlapping_grants(self):
        self.enabled();repo,actor=self.repository();proofs=[self.proof(repo,actor),self.proof(repo,actor)]
        workers=[]
        for _ in range(2):
            conn=self.connect();conn.execute('SET ROLE hcla_billing_worker');self.addCleanup(conn.close);workers.append(BillingWorker(conn))
        barrier=threading.Barrier(2)
        def apply(index):
            barrier.wait();return workers[index].call('billing_apply_verified',(proofs[index].order_id,json.dumps(asdict(proofs[index]))))
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
        self.assertTrue(all(r['membership_changed'] for r in results))
        rows=self.admin.execute('SELECT starts_at,expires_at FROM hcla.qwen_member_entitlements WHERE tenant=%s ORDER BY starts_at',(actor.tenant,)).fetchall()
        self.assertEqual(rows[0]['expires_at'],rows[1]['starts_at'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements WHERE tenant=%s AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp()',(actor.tenant,)).fetchone()['n'],1)

    def test_partial_refund_is_review_only_and_stale_capture_does_not_restore(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor);repo.apply_verified(proof)
        result=repo.apply_verified(replace(proof,state=PaymentState.PARTIAL_REFUND,refunded_minor=100))
        self.assertEqual(result['state'],'REVIEW_REQUIRED');repo.apply_verified(proof)
        self.assertFalse(self.admin.execute('SELECT enabled FROM hcla.qwen_member_entitlements WHERE tenant=%s',(actor.tenant,)).fetchone()['enabled'])
        repo.apply_verified(replace(proof,state=PaymentState.REFUNDED,refunded_minor=990))
        self.assertEqual(repo.order(actor,proof.order_id)['state'],'REFUNDED')

    def test_missing_forged_and_cross_order_payment_proofs_never_grant(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor);raw=asdict(proof)
        variants=[{},raw|{'verification_source':None},raw|{'amount_minor':990.0},raw|{'refunded_minor':None},raw|{'paid_at':None},raw|{'external_order_id':'wrong'},raw|{'merchant':'wrong'},raw|{'product_id':'wrong'},raw|{'state':None},raw|{'paid_at':raw['paid_at']-10}]
        for value in variants:
            with self.subTest(value=value),self.assertRaises(Exception):repo.worker.call('billing_apply_verified',(proof.order_id,json.dumps(value)))
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)
        repo.apply_verified(proof)
        second=self.proof(repo,actor)
        with self.assertRaises(Exception):repo.apply_verified(replace(second,payment_id=proof.payment_id))
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],1)

    def test_disable_plan_blocks_new_sales_but_honors_previously_verified_payment(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        self.admin.execute('UPDATE hcla.billing_plan_versions SET enabled=false')
        self.assertEqual(repo.catalog(actor),[])
        with self.assertRaises(Exception):self.new_order(repo,actor)
        self.assertTrue(repo.apply_verified(proof)['membership_changed'])
        with self.assertRaises(Exception):self.admin.execute('UPDATE hcla.billing_plan_versions SET amount_minor=1000')

    def test_exhausted_shared_capacity_blocks_sale_without_changing_payment_history(self):
        self.enabled();repo,actor=self.repository();o=self.new_order(repo,actor)
        for index in range(40):
            budget=self.budget();run='capacity-'+str(index)
            budget.reserve(run,'attempt',100);budget.finish(run,'attempt','unknown')
            self.open.remove(budget.store);budget.store.close()
        self.assertEqual(repo.catalog(actor),[])
        with self.assertRaises(Exception):self.new_order(repo,actor)
        with self.assertRaises(Exception):repo.claim_checkout(actor,o['order_id'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_orders').fetchone()['n'],1)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_verified_payments').fetchone()['n'],0)

    def test_expired_checkout_quote_and_revoked_session_cannot_create_remote_order(self):
        self.enabled();repo,actor=self.repository();o=self.new_order(repo,actor)
        # Disposable-fixture clock movement only; restore immutable protection
        # in the same transaction before exercising the application role.
        with self.admin.transaction():
            self.admin.execute('ALTER TABLE hcla.billing_orders DISABLE TRIGGER immutable_billing_order')
            self.admin.execute("UPDATE hcla.billing_orders SET created_at=clock_timestamp()-interval '1 hour',expires_at=clock_timestamp()-interval '1 minute' WHERE order_id=%s",(o['order_id'],))
            self.admin.execute('ALTER TABLE hcla.billing_orders ENABLE TRIGGER immutable_billing_order')
        with self.assertRaises(Exception):repo.claim_checkout(actor,o['order_id'])
        newer=self.new_order(repo,actor)
        self.admin.execute('DELETE FROM hcla.member_sessions WHERE tenant=%s',(actor.tenant,))
        with self.assertRaises(Exception):repo.worker.call('billing_claim_checkout',(newer['order_id'],actor.tenant,actor.session_hash))
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_audit').fetchone()['n'],0)

    def test_refund_before_capture_and_capture_replay_never_create_membership(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        repo.apply_verified(replace(proof,state=PaymentState.REFUNDED,refunded_minor=990))
        result=repo.apply_verified(proof)
        self.assertEqual(result['state'],'REFUNDED');self.assertFalse(result['membership_changed'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)

    def test_exact_maximum_minor_units_capture_and_full_refund(self):
        self.enabled(amount=100_000_000);repo,actor=self.repository();proof=self.proof(repo,actor)
        self.assertEqual(proof.amount_minor,100_000_000)
        proof.validate(repo.order(actor,proof.order_id))
        self.assertTrue(repo.apply_verified(proof)['membership_changed'])
        refund=replace(proof,state=PaymentState.REFUNDED,refunded_minor=100_000_000)
        refund.validate(repo.order(actor,proof.order_id))
        self.assertEqual(repo.apply_verified(refund)['state'],'REFUNDED')
        self.assertFalse(self.admin.execute('SELECT enabled FROM hcla.qwen_member_entitlements WHERE tenant=%s',(actor.tenant,)).fetchone()['enabled'])

    def test_simultaneous_same_idempotency_key_returns_one_order(self):
        self.enabled();left,la=self.repository('a');right,ra=self.repository('a')
        self.assertEqual(la.tenant,ra.tenant)
        barrier=threading.Barrier(2)
        def create(pair):
            repo,actor=pair;barrier.wait();return self.new_order(repo,actor,'simultaneous-key')
        with ThreadPoolExecutor(max_workers=2) as pool:orders=list(pool.map(create,((left,la),(right,ra))))
        self.assertEqual(orders[0]['order_id'],orders[1]['order_id'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_orders').fetchone()['n'],1)

    def test_member_http_catalog_orders_and_confirmation_do_not_trust_client_payment(self):
        self.enabled();repo,actor=self.repository();app=repo.application
        provider=Mock();provider.name='fixture';provider.merchant='offline-merchant';provider.checkout_origins={'https://checkout.example.test'}
        provider.create_checkout.side_effect=lambda o:Checkout(provider.name,provider.merchant,o['order_id'],'external-'+o['order_id'],'https://checkout.example.test/pay/'+o['order_id'])
        app.billing=BillingService(repo,provider,source_fixture=True)
        code,raw=self.http(app,'/v1/member/billing/catalog',cookie=repo.cookie);self.assertEqual(code,200,raw)
        self.assertTrue(json.loads(raw)['available'])
        body={'plan_id':'fixture-plan','version':1,'idempotency_key':'api-order','terms_digest':'b'*64}
        code,raw=self.http(app,'/v1/member/billing/orders',cookie=repo.cookie,body=body);self.assertEqual(code,200,raw)
        public=json.loads(raw);oid=public['order_id']
        self.assertNotIn('tenant',public);self.assertNotIn('merchant',public);self.assertNotIn('payment_id',public)
        code,raw=self.http(app,'/v1/member/billing/orders/'+oid+'/checkout',cookie=repo.cookie,body={});self.assertEqual(code,200,raw)
        self.assertTrue(json.loads(raw)['checkout_url'].startswith('https://checkout.example.test/'))
        code,_=self.http(app,'/v1/member/billing/orders/'+oid+'/reconcile',cookie=repo.cookie,body={'paid':True});self.assertEqual(code,400)
        provider.query_order.assert_not_called()
        o=repo.order(actor,oid)
        provider.query_order.return_value=VerifiedPayment('fixture','offline-merchant',oid,o['external_order_id'],'payment-'+oid,o['product_id'],990,'CNY',PaymentState.CAPTURED,o['created_at'],0,'c'*64)
        code,raw=self.http(app,'/v1/member/billing/orders/'+oid+'/reconcile',cookie=repo.cookie,body={});self.assertEqual(code,200,raw);self.assertEqual(json.loads(raw)['state'],'FULFILLED')
        self.assertEqual(provider.create_checkout.call_count,1);self.assertEqual(provider.query_order.call_count,1)
        code,raw=self.http(app,'/v1/member/billing/orders',cookie=repo.cookie);self.assertEqual(code,200,raw);self.assertEqual(len(json.loads(raw)['orders']),1)
        outsider,_=self.app();self.assertEqual(self.http(outsider,'/v1/member/billing/orders')[0],401)
        other,other_actor=self.repository('b');other.application.billing=BillingService(other,provider,source_fixture=True)
        code,_=self.http(other.application,'/v1/member/billing/orders/'+oid,cookie=other.cookie);self.assertEqual(code,404)

    def test_member_http_default_closed_and_no_ordinary_owner_billing_bypass(self):
        repo,actor=self.repository();app=repo.application
        code,raw=self.http(app,'/v1/member/billing/catalog',cookie=repo.cookie);self.assertEqual(code,200,raw);self.assertFalse(json.loads(raw)['available'])
        code,raw=self.http(app,'/v1/member/billing/orders',cookie=repo.cookie,body={});self.assertEqual(code,503,raw)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_orders').fetchone()['n'],0)
        unsigned,_=self.app();self.assertEqual(self.http(unsigned,'/v1/billing/catalog')[0],401)

    def test_verified_pending_or_failed_does_not_create_or_undo_a_paid_grant(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        pending=replace(proof,state=PaymentState.PENDING,payment_id=None,paid_at=None)
        repo.apply_verified(pending)
        self.assertEqual(repo.order(actor,proof.order_id)['verification_state'],'VERIFIED_PENDING')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)
        repo.apply_verified(replace(pending,state=PaymentState.FAILED))
        self.assertEqual(repo.order(actor,proof.order_id)['verification_state'],'VERIFIED_FAILED')
        repo.apply_verified(proof);repo.apply_verified(pending)
        self.assertEqual(repo.order(actor,proof.order_id)['verification_state'],'VERIFIED')
        self.assertTrue(self.admin.execute('SELECT enabled FROM hcla.qwen_member_entitlements').fetchone()['enabled'])

    def test_public_notification_is_only_a_hint_and_never_echoes_order_or_grants(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        provider=Mock();provider.name='fixture';provider.merchant='offline-merchant'
        provider.notification_reference.return_value=proof.external_order_id
        provider.query_order.return_value=replace(proof,state=PaymentState.PENDING,payment_id=None,paid_at=None)
        app=repo.application;app.billing=BillingService(repo,provider,source_fixture=True)
        code,raw=self.http(app,'/v1/billing/notification/fixture',body={'state':'CAPTURED','amount_minor':1,'tenant':'forged'})
        self.assertEqual(code,202,raw);self.assertEqual(json.loads(raw),{'accepted':True})
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)
        self.assertEqual(provider.query_order.call_args.args[0]['amount_minor'],990)
        code,_=self.http(app,'/v1/billing/notification/unselected',body={});self.assertEqual(code,503)
        self.assertEqual(provider.query_order.call_count,1)
        self.admin.execute("UPDATE hcla.billing_query_attempts SET started_at=clock_timestamp()-interval '11 seconds' WHERE order_id=%s",(proof.order_id,))
        provider.query_order.side_effect=TimeoutError()
        code,raw=self.http(app,'/v1/billing/notification/fixture',body={});self.assertEqual(code,503,raw)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],0)

    def test_pending_order_limit_preserves_idempotent_recovery(self):
        self.enabled();repo,actor=self.repository()
        first=self.new_order(repo,actor,'first-pending')
        for index in range(4):self.new_order(repo,actor,'pending-'+str(index))
        with self.assertRaises(Exception):self.new_order(repo,actor,'sixth')
        self.assertEqual(self.new_order(repo,actor,'first-pending')['order_id'],first['order_id'])
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_orders').fetchone()['n'],5)

    def test_callback_body_limit_and_duplicate_hints_do_not_fan_out_queries(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        provider=Mock();provider.name='fixture';provider.merchant='offline-merchant';provider.notification_reference.return_value=proof.external_order_id
        provider.query_order.return_value=replace(proof,state=PaymentState.PENDING,payment_id=None,paid_at=None)
        repo.application.billing=BillingService(repo,provider,source_fixture=True)
        code,_=self.http(repo.application,'/v1/billing/notification/fixture',body={'payload':'x'*8193});self.assertEqual(code,413);provider.query_order.assert_not_called()
        codes=[self.http(repo.application,'/v1/billing/notification/fixture',body={'order':'hint'})[0] for _ in range(3)]
        self.assertEqual(codes,[202,429,429])
        self.assertEqual(provider.query_order.call_count,1)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_query_attempts').fetchone()['n'],1)

    def test_query_leases_coalesce_across_instances_and_bound_global_concurrency(self):
        self.enabled();repo,actor=self.repository();orders=[self.new_order(repo,actor) for _ in range(5)]
        workers=[]
        for _ in range(2):
            conn=self.connect();conn.execute('SET ROLE hcla_billing_worker');self.addCleanup(conn.close);workers.append(BillingWorker(conn))
        barrier=threading.Barrier(2)
        def claim(index):
            barrier.wait();return workers[index].call('billing_claim_query',(orders[0]['order_id'],str(uuid.uuid4())))
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sum(pool.map(claim,range(2))),1)
        for order in orders[1:4]:self.assertIsNotNone(repo.claim_verification(order['order_id']))
        self.assertIsNone(repo.claim_verification(orders[4]['order_id']))
        first=self.admin.execute('SELECT owner,order_id FROM hcla.billing_query_attempts LIMIT 1').fetchone()
        repo.finish_verification(first['order_id'],first['owner'])
        self.assertIsNotNone(repo.claim_verification(orders[4]['order_id']))
        self.assertIsNone(repo.claim_verification(first['order_id']))

    def test_global_query_rate_survives_fast_completed_calls(self):
        self.enabled();repo,actor=self.repository();first=self.new_order(repo,actor);second=self.new_order(repo,actor)
        # Synthetic pre-existing completed query audit, not provider calls.
        for _ in range(60):self.admin.execute("INSERT INTO hcla.billing_query_attempts(owner,order_id,expires_at,finished) VALUES(%s,%s,clock_timestamp()+interval '30 seconds',true)",(str(uuid.uuid4()),first['order_id']))
        self.assertIsNone(repo.claim_verification(second['order_id']))
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_query_attempts').fetchone()['n'],60)

    def test_owner_path_cannot_use_stale_member_application_context(self):
        repo,actor=self.repository();app=repo.application
        self.assertIsNotNone(app.member_context)
        # Synthetic authenticated owner request against a deliberately reused
        # application must still require the explicit member route boundary.
        app.development_auth.require=lambda cookie:'hcla-owner'
        app.development_auth.boundary=lambda request,mutation=False:None
        self.assertEqual(self.http(app,'/v1/billing/catalog')[0],403)
        self.assertEqual(self.http(app,'/v1/billing/orders',body={})[0],403)

    def test_query_finish_failure_does_not_turn_committed_payment_into_a_new_sale(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        provider=Mock();provider.name='fixture';provider.query_order.return_value=proof
        service=BillingService(repo,provider,source_fixture=True)
        def unavailable(*args):raise RuntimeError('offline cleanup uncertainty')
        repo.finish_verification=unavailable
        with self.assertRaises(RuntimeError):service.reconcile(actor,proof.order_id)
        self.assertEqual(repo.order(actor,proof.order_id)['state'],'FULFILLED')
        # The durable lease coalesces a repeated query; it does not create a
        # checkout, revoke payment truth or charge the customer again.
        self.assertTrue(service.reconcile(actor,proof.order_id)['verification_deferred'])
        self.assertEqual(provider.query_order.call_count,1);provider.create_checkout.assert_not_called()
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],1)
