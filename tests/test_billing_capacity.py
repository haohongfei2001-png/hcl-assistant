"""Actual Postgres sales/admission alignment; isolated synthetic fixtures only."""
from decimal import Decimal
import unittest

from packages.adapter.development_budget import BudgetError
from packages.cloud.qwen_config import QwenConfig
from tests import test_billing_postgres as billing
from tests import test_cloud_postgres as baseline
from tests import test_qwen_monthly as monthly
from tests import test_qwen_shared as shared
from tests.test_qwen_provider import SECRET

MIGRATION='20261003011612_billing_sales_admission_alignment.sql'


@unittest.skipUnless(baseline.DSN,'Disposable localhost Postgres required')
class BillingCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        billing.BillingPostgresTests.setUpClass.__func__(cls)
        with cls.connect(None) as admin:
            admin.execute((baseline.ROOT/'supabase/migrations'/MIGRATION).read_text())

    def setUp(self):
        # Choose a small immutable request policy before insertion, never
        # mutate an installed grant merely to manufacture exhaustion.
        self.monthly_config=QwenConfig.from_grant(shared.shared_grant()|{'max_requests':2},SECRET)
        billing.BillingPostgresTests.setUp(self)
        self.clock('2032-01-15 00:00:00+00')

    tearDown=monthly.MonthlyPostgresTests.tearDown
    clock=monthly.MonthlyPostgresTests.clock
    store=billing.BillingPostgresTests.store
    app=billing.BillingPostgresTests.app
    member=billing.BillingPostgresTests.member
    budget=billing.BillingPostgresTests.budget
    complete=billing.BillingPostgresTests.complete
    ready=billing.BillingPostgresTests.ready
    enabled=billing.BillingPostgresTests.enabled
    repository=billing.BillingPostgresTests.repository
    new_order=billing.BillingPostgresTests.new_order
    proof=billing.BillingPostgresTests.proof

    def capacity(self,repo):
        with repo.store.transaction():
            return repo.store.db.execute('SELECT billing_capacity() AS result').fetchone()['result']

    def assert_sales_closed(self,repo,actor,order,reason):
        capacity=self.capacity(repo)
        self.assertIs(capacity['available'],False)
        self.assertEqual(capacity['reason'],reason)
        self.assertEqual(repo.catalog(actor),[])
        with self.assertRaisesRegex(Exception,'shared_capacity_unavailable_no_new_sale'):
            self.new_order(repo,actor)
        with self.assertRaisesRegex(Exception,'shared_capacity_unavailable_no_new_sale'):
            repo.claim_checkout(actor,order['order_id'])
        # Re-reading an existing idempotent order and history remains possible.
        self.assertEqual(self.new_order(repo,actor,order['idempotency_key'])['order_id'],order['order_id'])
        self.assertIn(order['order_id'],[o['order_id'] for o in repo.history(actor)])

    def test_request_cap_closes_catalog_order_and_checkout_with_money_remaining(self):
        self.enabled();repo,actor=self.repository();order=self.new_order(repo,actor)
        self.assertTrue(self.capacity(repo)['available'])
        self.complete(self.budget(),2)
        self.assert_sales_closed(repo,actor,order,'SHARED_REQUEST_LIMIT')
        row=self.admin.execute('SELECT count(*) AS n,sum(charged_cny) AS cost FROM hcla.qwen_monthly_attempts').fetchone()
        self.assertEqual(row['n'],2);self.assertLess(row['cost'],Decimal('1'))
        with self.assertRaises(BudgetError):self.budget().reserve('cap-refusal','attempt',100)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_orders').fetchone()['n'],1)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.billing_verified_payments').fetchone()['n'],0)

    def test_exact_month_pause_blocks_sales_and_next_month_reopens_without_writing_budget(self):
        self.enabled();repo,actor=self.repository()
        self.clock('2032-01-31 15:54:59+00')
        self.assertTrue(self.capacity(repo)['available']);self.assertEqual(len(repo.catalog(actor)),1)
        order=self.new_order(repo,actor)
        self.clock('2032-01-31 15:55:00+00')
        self.assert_sales_closed(repo,actor,order,'MONTH_BOUNDARY_PAUSE')
        with self.assertRaises(BudgetError):self.budget().reserve('boundary-refusal','attempt',100)
        before=self.admin.execute('SELECT period_key,max_cost_cny,policy FROM hcla.qwen_monthly_periods ORDER BY period_key').fetchall()
        self.clock('2032-01-31 16:00:01+00')
        self.assertTrue(self.capacity(repo)['available']);self.assertEqual(len(repo.catalog(actor)),1)
        self.assertEqual(repo.claim_checkout(actor,order['order_id'])['state'],'CREATING')
        self.assertEqual(self.admin.execute('SELECT period_key,max_cost_cny,policy FROM hcla.qwen_monthly_periods ORDER BY period_key').fetchall(),before)
        self.assertEqual(self.admin.execute('SELECT policy FROM hcla.qwen_monthly_authorization').fetchone()['policy'],self.monthly_config.policy())

    def test_verified_prior_payment_fulfils_once_after_request_cap(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        self.complete(self.budget(),2)
        self.assertFalse(self.capacity(repo)['available'])
        self.assertTrue(repo.apply_verified(proof)['membership_changed'])
        self.assertFalse(repo.apply_verified(proof)['membership_changed'])
        self.assertEqual(repo.order(actor,proof.order_id)['state'],'FULFILLED')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],1)

    def test_verified_prior_payment_fulfils_once_during_month_pause(self):
        self.enabled();repo,actor=self.repository();proof=self.proof(repo,actor)
        self.clock('2032-01-31 15:55:00+00')
        self.assertFalse(self.capacity(repo)['available'])
        self.assertTrue(repo.apply_verified(proof)['membership_changed'])
        self.assertFalse(repo.apply_verified(proof)['membership_changed'])
        self.assertEqual(repo.order(actor,proof.order_id)['state'],'FULFILLED')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_member_entitlements').fetchone()['n'],1)

    def test_replacement_preserves_invoker_and_private_execution_acl(self):
        row=self.admin.execute("SELECT p.prosecdef,has_function_privilege('hcla_app',p.oid,'EXECUTE') AS app,EXISTS(SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS public FROM pg_proc p WHERE p.oid='hcla.billing_capacity()'::regprocedure").fetchone()
        self.assertFalse(row['prosecdef']);self.assertTrue(row['app']);self.assertFalse(row['public'])
