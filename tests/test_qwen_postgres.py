"""Disposable PostgreSQL CNY policy/locking/RLS coverage; no provider network."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from packages.adapter.development_budget import BudgetError
from packages.cloud.qwen_budget import QwenCloudBudget
from packages.cloud.qwen_config import QwenConfig
from packages.cloud.qwen_entitlements import QwenEntitlements, QwenMemberBudget
from packages.cloud.budget import CloudBudget
from tests import test_cloud_postgres as baseline
from tests.test_qwen_provider import grant, SECRET


@unittest.skipUnless(baseline.DSN, 'Disposable local Postgres not configured; required in cloud CI')
class QwenPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline.CloudPostgresTests.setUpClass.__func__(cls)
        with cls.connect(None) as admin:
            if admin.execute("SELECT to_regclass('hcla.qwen_budget_policy') AS present").fetchone()['present'] is None:
                admin.execute((baseline.ROOT/'supabase/migrations/20261002165257_bounded_qwen_cny_budget.sql').read_text())
        cls.qwen_config = QwenConfig.from_grant(grant(), SECRET)

    def setUp(self):
        baseline.CloudPostgresTests.setUp(self)
        self.admin.execute('INSERT INTO hcla.qwen_budget_policy VALUES(1,%s)', (self.qwen_config.policy(),))
        guard = patch('http.client.HTTPSConnection', side_effect=AssertionError('provider network forbidden'))
        guard.start(); self.addCleanup(guard.stop)

    tearDown = baseline.CloudPostgresTests.tearDown
    store = baseline.CloudPostgresTests.store

    def test_real_transactions_single_dispatch_currency_isolation_and_restart(self):
        stores = [self.store(), self.store()]
        budgets = [QwenCloudBudget(s,self.qwen_config) for s in stores]
        def reserve(index):
            try: return budgets[index].reserve('qwen-run-'+str(index),'attempt',512).granted
            except BudgetError: return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, (0,1)))
        self.assertEqual(sum(results),1)
        winner = results.index(True)
        with self.assertRaises(BudgetError):
            CloudBudget(self.store(), self.config).reserve('legacy','attempt',512)
        budgets[winner].finish('qwen-run-'+str(winner),'attempt','unknown')
        snapshot = QwenCloudBudget(self.store(),self.qwen_config).snapshot()
        self.assertEqual(snapshot['currency'],'CNY')
        self.assertEqual(snapshot['charged_cost_cny'],'12.295272')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.budget_attempts').fetchone()['n'],0)
        with self.assertRaises(BudgetError):
            QwenCloudBudget(self.store(),replace(self.qwen_config,max_cost_cny=Decimal('27')))

    def test_runtime_role_cannot_create_reset_policy_or_member_grant(self):
        store = self.store()
        for query in ('DELETE FROM qwen_budget_policy',
                      "UPDATE qwen_budget_policy SET policy='{}'",
                      'DELETE FROM qwen_member_entitlements'):
            with self.subTest(query=query), self.assertRaises(Exception):
                with store.transaction(): store.db.execute(query)
        self.assertEqual(self.admin.execute('SELECT policy FROM hcla.qwen_budget_policy').fetchone()['policy'],self.qwen_config.policy())

    def test_old_deployment_raw_usd_admission_is_closed_only_after_qwen_policy(self):
        store=self.store()
        self.admin.execute('DELETE FROM hcla.qwen_budget_policy')
        # The old HCLA SQL knows nothing about Qwen. Migration alone preserves it.
        with store.transaction():
            store.db.execute("INSERT INTO budget_attempts(run_key,attempt_key,input_bytes,reserved_usd,charged_usd,outcome) VALUES('old','attempt',50,1,1,'active')")
        self.admin.execute('INSERT INTO hcla.qwen_budget_policy VALUES(1,%s)',(self.qwen_config.policy(),))
        # Already dispatched legacy requests can settle without rewriting history.
        with store.transaction():
            store.db.execute("UPDATE budget_attempts SET outcome='unknown' WHERE run_key='old'")
        for table in ('budget_attempts','trial_budget_attempts'):
            with self.subTest(table=table),self.assertRaisesRegex(Exception,'legacy_hcla_provider_admission_closed'):
                with store.transaction():
                    store.db.execute("INSERT INTO "+table+"(run_key,attempt_key,input_bytes,reserved_usd,charged_usd,outcome) VALUES('new','attempt',50,1,1,'active')")
        self.assertEqual(self.admin.execute("SELECT outcome FROM hcla.budget_attempts WHERE run_key='old'").fetchone()['outcome'],'unknown')
        self.assertTrue(QwenCloudBudget(store,self.qwen_config).reserve('qwen','attempt',512).granted)

    def test_member_requires_separate_cny_entitlement_and_tenant_rls(self):
        from packages.cloud.member_auth import VerifiedPrincipal
        issuer = 'https://abcdefghijklmnopqrst.supabase.co/auth/v1'
        principal = VerifiedPrincipal(issuer,'00000000-0000-0000-0000-000000000001',9999999999)
        other = VerifiedPrincipal(issuer,'00000000-0000-0000-0000-000000000002',9999999999)
        a,b = principal.tenant,other.tenant
        for tenant in (a,b):
            self.admin.execute("INSERT INTO hcla.qwen_member_entitlements(tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_cny) VALUES(%s,'separate-cny',true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',true,true,1,13)", (tenant,))
        store = self.store()
        # Explicit test principal binding; no real Auth or bearer credentials.
        store.bind_member(principal)
        rights = QwenEntitlements(store)
        self.assertEqual(rights.current()['tenant'],a)
        with store.transaction():
            self.assertEqual(len(store.db.execute('SELECT * FROM qwen_member_entitlements').fetchall()),1)
        budget = QwenMemberBudget(QwenCloudBudget(store,self.qwen_config),rights,SimpleNamespace(active=lambda _:True),'a'*64,'TEMPORARY')
        budget.reserve('member-run','attempt',512)
        budget.finish('member-run','attempt','completed',10,12)
        self.assertEqual(budget.snapshot()['charged_cost_cny'],'12.295272')
        with self.assertRaises(BudgetError): budget.reserve('second','attempt',512)
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.member_budget_attempts').fetchone()['n'],0)
