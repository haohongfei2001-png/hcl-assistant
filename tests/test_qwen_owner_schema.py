"""Original owner-only schema compatibility, on a fresh disposable CI database."""
import os
import unittest
from urllib.parse import urlsplit

from packages.adapter.development_budget import BudgetError
from packages.cloud.auth import password_verifier
from packages.cloud.qwen_config import QwenConfig
from packages.cloud.qwen_monthly_budget import QwenMonthlyBudget
from tests import test_cloud_postgres as baseline
from tests import test_qwen_monthly as monthly
from tests.test_qwen_provider import SECRET


@unittest.skipUnless(baseline.DSN and os.environ.get('HCLA_TEST_OWNER_SCHEMA_ONLY') == '1',
                     'Dedicated original-schema disposable Postgres CI step required')
class OriginalOwnerSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from psycopg.rows import dict_row
        parsed = urlsplit(baseline.DSN)
        if parsed.hostname not in {'127.0.0.1', 'localhost'} or parsed.path != '/hcla_test':
            raise ValueError('Fresh disposable localhost hcla_test database required')
        cls.connect = lambda self: psycopg.connect(baseline.DSN, autocommit=True,
                                                    row_factory=dict_row, prepare_threshold=None)
        with cls.connect(None) as admin:
            if admin.execute("SELECT to_regnamespace('hcla') AS present").fetchone()['present'] is not None:
                raise ValueError('Original-schema test must run FIRST on fresh disposable database')
            for name in ('20261001084651_isolated_hcla_cloud.sql',
                         '20261001174151_bounded_temporary_trial.sql',
                         '20261002165257_bounded_qwen_cny_budget.sql',
                         '20261002174149_qwen_monthly_owner_budget.sql'):
                if name == '20261002165257_bounded_qwen_cny_budget.sql':
                    cls.original_policies = admin.execute("SELECT tablename,policyname,qual,with_check FROM pg_policies WHERE schemaname='hcla' ORDER BY tablename,policyname").fetchall()
                admin.execute((baseline.ROOT / 'supabase/migrations' / name).read_text())
        cls.verifier = password_verifier('offline password fixture')
        cls.monthly_config = QwenConfig.from_grant(monthly.monthly_grant(), SECRET)

    store = baseline.CloudPostgresTests.store

    def test_original_owner_flow_and_tenant_absence_is_not_null(self):
        self.admin = self.connect(); self.open = []
        self.addCleanup(self.admin.close)
        self.addCleanup(lambda: [store.close() for store in self.open])
        self.admin.execute('INSERT INTO hcla.qwen_monthly_authorization VALUES(1,%s,true)',
                           (self.monthly_config.policy(),))
        def policies():
            return self.admin.execute("SELECT tablename,policyname,qual,with_check FROM pg_policies WHERE schemaname='hcla' AND tablename NOT LIKE 'qwen_%' ORDER BY tablename,policyname").fetchall()
        before = policies()
        self.assertEqual(before, self.original_policies)
        self.assertFalse(self.admin.execute("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema='hcla' AND table_name='execution' AND column_name='tenant') AS present").fetchone()['present'])
        # Exercises the real CloudApplication + Controller + temporary and
        # persistent publication paths, with fake transport and pinned runtime.
        monthly.MonthlyPostgresTests.test_cloud_temporary_smoke_then_delayed_persistent_owner_publication_settles(self)
        self.assertEqual(policies(), before)
        self.assertEqual(self.admin.execute("SELECT tablename FROM pg_tables WHERE schemaname='hcla' AND tablename LIKE 'member_%'").fetchall(), [])
        # On this disposable database only, simulate a malformed future nullable
        # column. An absent field is legacy owner; NULL/member fields are not.
        # The guarded finally removes this test-only column before the full schema suite.
        with self.admin.transaction():
            self.admin.execute('ALTER TABLE hcla.execution ADD COLUMN tenant text')
        try:
            for value in (None, 'member-' + 'a' * 64):
                identity = 'invalid-' + ('null' if value is None else 'member')
                self.admin.execute("INSERT INTO hcla.execution(run_id,owner,expires_at,tenant) VALUES(%s,'test-owner',clock_timestamp()+interval '270 seconds',%s)", (identity,value))
                store=self.store();store.fence=(identity,'test-owner')
                with self.assertRaises(BudgetError):
                    QwenMonthlyBudget(store,self.monthly_config).reserve(identity,'attempt',100)
            self.admin.execute("INSERT INTO hcla.execution(run_id,owner,expires_at,tenant) VALUES('settlement-test','test-owner',clock_timestamp()+interval '270 seconds','hcla-owner')")
            store=self.store();store.fence=('settlement-test','test-owner')
            budget=QwenMonthlyBudget(store,self.monthly_config)
            budget.reserve('settlement-test','attempt',100)
            budget.finish('settlement-test','attempt','completed',100,20)
            self.admin.execute("UPDATE hcla.execution SET tenant=NULL WHERE run_id='settlement-test'")
            with self.assertRaisesRegex(Exception,'verified_completed_settlement_required'):
                budget.reconcile_completed('settlement-test','attempt')
            row=self.admin.execute("SELECT settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts WHERE execution_run_id='settlement-test'").fetchone()
            self.assertFalse(row['settled']);self.assertEqual(row['charged_cny'],row['reserved_cny'])
        finally:
            self.admin.execute('ALTER TABLE hcla.execution DROP COLUMN tenant')
        self.assertEqual(policies(), before)
