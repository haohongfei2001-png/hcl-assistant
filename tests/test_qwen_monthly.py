"""Shanghai-month CNY accounting on disposable Postgres; zero model/auth calls."""
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from packages.adapter.development_budget import BudgetError
from packages.cloud.qwen_config import QwenConfig
from packages.cloud.qwen_monthly_budget import QwenMonthlyBudget
from tests.test_qwen_provider import grant, smoke_policy, SECRET, SMOKE_TEXT, SMOKE_QUERY
from tests import test_cloud_postgres as baseline
from tests import test_qwen_postgres as qwen_baseline


def monthly_grant(**changes):
    value=grant(max_requests=1000000,max_cost_cny='500',max_completion_tokens=8192,
                 smoke=smoke_policy(),monthly={'timezone':'Asia/Shanghai','scope':'OWNER_ONLY','limit_cny':'500'})
    value.update(changes);return value


class MonthlyConfigTests(unittest.TestCase):
    def test_fixed_native_currency_scope_calendar_and_limit(self):
        cfg=QwenConfig.from_grant(monthly_grant(),SECRET)
        policy=json.loads(cfg.policy())
        self.assertEqual(policy['monthly']['limit_cny'],'500')
        self.assertEqual(policy['initial_smoke_max_completion_tokens'],8192)
        for monthly in ({'timezone':'UTC','scope':'OWNER_ONLY','limit_cny':'500'},
                        {'timezone':'Asia/Shanghai','scope':'PUBLIC','limit_cny':'500'},
                        {'timezone':'Asia/Shanghai','scope':'OWNER_ONLY','limit_cny':'501'}):
            value=monthly_grant();value['monthly']=monthly
            with self.assertRaises(ValueError):QwenConfig.from_grant(value,SECRET)
        value=monthly_grant();value.pop('smoke')
        with self.assertRaises(ValueError):QwenConfig.from_grant(value,SECRET)


@unittest.skipUnless(baseline.DSN,'Disposable localhost Postgres required for monthly guards')
class MonthlyPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen_baseline.QwenPostgresTests.setUpClass.__func__(cls)
        with cls.connect(None) as admin:
            if admin.execute("SELECT to_regclass('hcla.qwen_monthly_authorization') AS present").fetchone()['present'] is None:
                admin.execute((baseline.ROOT/'supabase/migrations/20261002174149_qwen_monthly_owner_budget.sql').read_text())
        cls.monthly_config=QwenConfig.from_grant(monthly_grant(),SECRET)

    def setUp(self):
        baseline.CloudPostgresTests.setUp(self)
        self.clock('2032-01-15 00:00:00+00')
        self.admin.execute('INSERT INTO hcla.qwen_monthly_authorization VALUES(1,%s,true)',(self.monthly_config.policy(),))
        self.counter=0

    def tearDown(self):
        self.admin.execute("CREATE OR REPLACE FUNCTION hcla.qwen_monthly_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS 'SELECT clock_timestamp()'")
        baseline.CloudPostgresTests.tearDown(self)

    store=baseline.CloudPostgresTests.store

    def clock(self,value):
        # Administrator-only replacement on the disposable test database.
        import psycopg
        self.admin.execute(psycopg.sql.SQL("CREATE OR REPLACE FUNCTION hcla.qwen_monthly_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS {}").format(psycopg.sql.Literal('SELECT '+psycopg.sql.Literal(value).as_string(self.admin)+'::timestamptz')))

    def budget(self):
        self.counter+=1;identity='monthly-execution-'+str(self.counter);owner='owner-'+str(self.counter)
        self.admin.execute("INSERT INTO hcla.execution(run_id,owner,expires_at,tenant) VALUES(%s,%s,hcla.qwen_monthly_clock()+interval '270 seconds','hcla-owner')",(identity,owner))
        store=self.store();store.fence=(identity,owner)
        return QwenMonthlyBudget(store,self.monthly_config)

    def complete(self,budget,index=1,settle=True):
        run='monthly-run-'+str(index);attempt='attempt-'+str(index)
        budget.reserve(run,attempt,2048);budget.finish(run,attempt,'completed',100,20)
        if settle:budget.reconcile_completed(run,attempt)
        return run,attempt

    def test_smoke_and_regular_owner_share_one_cap_and_verified_settlement(self):
        b=self.budget();self.assertFalse(b.smoke_ready())
        b.authorize_request({'expected_state_version':0,'event':{'text':SMOKE_TEXT},'development_execution':{'capability_id':'belief_interpretation','query':SMOKE_QUERY}},{'memory':'TEMPORARY'})
        with self.assertRaises(ValueError):b.authorize_request({'event':{'text':'different'}},{'memory':'TEMPORARY'})
        run,attempt=self.complete(b,settle=False)
        self.assertFalse(b.smoke_ready());self.assertEqual(b.snapshot()['charged_cost_cny'],'12.295272')
        b.reconcile_completed(run,attempt);b.reconcile_completed(run,attempt)
        self.assertTrue(b.smoke_ready());self.assertEqual(Decimal(b.snapshot()['charged_cost_cny']),Decimal('0.00192'))
        b.authorize_request({'event':{'text':'ordinary owner question'}},{'memory':'CONVERSATION'})
        self.complete(self.budget(),2)
        rows=self.admin.execute('SELECT period_key,kind FROM hcla.qwen_monthly_attempts ORDER BY kind').fetchall()
        self.assertEqual({r['period_key'] for r in rows},{'2032-01'});self.assertEqual({r['kind'] for r in rows},{'SMOKE','OWNER'})
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_budget_attempts').fetchone()['n'],0)

    def test_unknowns_retain_reservation_and_monthly_sum_stops_before_500(self):
        count=0
        for i in range(50):
            b=self.budget()
            try:b.reserve('bounded-'+str(i),'attempt',2048)
            except BudgetError:break
            b.finish('bounded-'+str(i),'attempt','unknown');count+=1
        self.assertEqual(count,40)
        b=self.budget();snapshot=b.snapshot()
        self.assertLessEqual(Decimal(snapshot['charged_cost_cny']),500)
        self.assertGreater(Decimal(snapshot['charged_cost_cny']),Decimal('487'))
        self.assertEqual(snapshot['unknown_usage_requests'],40)
        self.assertFalse(b.smoke_ready())

    def test_current_database_month_immutable_fields_and_no_future_period(self):
        b=self.budget();self.complete(b)
        for statement in ("INSERT INTO qwen_monthly_periods(period_key) VALUES('2032-02')",
                          "UPDATE qwen_monthly_periods SET max_cost_cny=501",
                          "UPDATE qwen_monthly_attempts SET period_key='2032-02'",
                          "UPDATE qwen_monthly_attempts SET charged_cny=0",
                          "UPDATE qwen_monthly_authorization SET policy='{}'",
                          'DELETE FROM qwen_monthly_attempts'):
            with self.subTest(sql=statement),self.assertRaises(Exception):
                with b.store.transaction():b.store.db.execute(statement)
        self.assertEqual(b.snapshot()['period'],'2032-01')

    def test_calendar_cutoff_rollover_leap_february_and_no_credit_carryover(self):
        self.clock('2032-01-31 15:54:00+00');b=self.budget();self.complete(b)
        before=b.snapshot()['charged_cost_cny']
        self.clock('2032-01-31 15:55:00+00')
        blocked=self.budget()
        with self.assertRaises(BudgetError):blocked.reserve('near-boundary','attempt',100)
        self.clock('2032-01-31 16:00:01+00');new=self.budget()
        self.assertEqual(new.snapshot()['period'],'2032-02');self.assertEqual(new.snapshot()['charged_cost_cny'],'0')
        self.complete(new,2)
        feb=self.admin.execute("SELECT starts_at,ends_at FROM hcla.qwen_monthly_periods WHERE period_key='2032-02'").fetchone()
        self.assertEqual((feb['ends_at']-feb['starts_at']).days,29)
        self.assertEqual(str(self.admin.execute("SELECT sum(charged_cny) AS n FROM hcla.qwen_monthly_attempts WHERE period_key='2032-01'").fetchone()['n']),before)

    def test_old_binary_admissions_and_member_scope_stay_closed(self):
        b=self.budget()
        for table,columns in [('budget_attempts','reserved_usd,charged_usd'),('trial_budget_attempts','reserved_usd,charged_usd'),('qwen_budget_attempts','reserved_cny,charged_cny')]:
            with self.subTest(table=table),self.assertRaisesRegex(Exception,'monthly_hcla_provider_admission_only'):
                with b.store.transaction():b.store.db.execute("INSERT INTO "+table+"(run_key,attempt_key,input_bytes,"+columns+",outcome) VALUES('old','attempt',100,1,1,'active')")
        b.store.fence=None
        from packages.cloud.member_auth import VerifiedPrincipal
        b.store.bind_member(VerifiedPrincipal('https://abcdefghijklmnopqrst.supabase.co/auth/v1','00000000-0000-0000-0000-000000000001',9999999999))
        with self.assertRaises(BudgetError):b.reserve('member','attempt',100)
        with b.store.transaction():
            self.assertEqual(len(b.store.db.execute('SELECT * FROM qwen_monthly_authorization').fetchall()),1)
            self.assertEqual(b.store.db.execute('SELECT * FROM qwen_monthly_attempts').fetchall(),[])
        for table,columns in [('budget_attempts','reserved_usd,charged_usd'),('trial_budget_attempts','reserved_usd,charged_usd'),('qwen_budget_attempts','reserved_cny,charged_cny')]:
            with self.subTest(member_table=table),self.assertRaisesRegex(Exception,'monthly_hcla_provider_admission_only'):
                with b.store.transaction():b.store.db.execute("INSERT INTO "+table+"(run_key,attempt_key,input_bytes,"+columns+",outcome) VALUES('member-old','attempt',100,1,1,'active')")

    def test_cancelled_and_unpublished_completion_never_unlock_or_refund(self):
        b=self.budget();run,attempt=self.complete(b,settle=False)
        self.admin.execute('UPDATE hcla.execution SET cancelled=true WHERE run_id=%s',(b.store.fence[0],))
        with self.assertRaises(Exception):b.reconcile_completed(run,attempt)
        self.assertFalse(b.smoke_ready());self.assertEqual(Decimal(b.snapshot()['charged_cost_cny']),Decimal('12.295272'))

    def test_two_connection_cold_period_and_near_cap_admission_races(self):
        def race(budgets,label):
            barrier=threading.Barrier(2)
            def attempt(index):
                barrier.wait()
                try:return budgets[index].reserve(label+str(index),'attempt',512).granted
                except BudgetError:return False
            with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(attempt,(0,1)))
        budgets=[self.budget(),self.budget()]
        result=race(budgets,'cold-');self.assertEqual(sum(result),1)
        winner=result.index(True);budgets[winner].finish('cold-'+str(winner),'attempt','unknown')
        self.assertEqual(self.admin.execute('SELECT count(*) AS n FROM hcla.qwen_monthly_periods').fetchone()['n'],1)
        for i in range(38):
            b=self.budget();b.reserve('fill-'+str(i),'attempt',512);b.finish('fill-'+str(i),'attempt','unknown')
        result=race([self.budget(),self.budget()],'near-cap-')
        self.assertEqual(sum(result),1)
        total=self.admin.execute('SELECT sum(charged_cny) AS n FROM hcla.qwen_monthly_attempts').fetchone()['n']
        self.assertLessEqual(total,500);self.assertEqual(total,Decimal('491.81088'))

    def test_cloud_temporary_smoke_then_delayed_persistent_owner_publication_settles(self):
        import io,os,time,uuid
        from apps.api.cloud_server import CloudApplication
        from packages.cloud.config import CloudConfig
        from packages.cloud.temporary import execute as execute_temporary
        from packages.adapter.provider import create_adapter
        from tests.test_qwen_provider import FakeTransport,event,qchunk,DONE,usage,REASONING
        self.admin.execute("CREATE OR REPLACE FUNCTION hcla.qwen_monthly_clock() RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS 'SELECT clock_timestamp()'")
        runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT');self.assertTrue(runtime)
        def make_app():
            fake=FakeTransport([event(qchunk(reasoning=REASONING)),event(qchunk('Mira reports a belief, not an established meeting date. [HCL1]')),
                                event(qchunk(finish='stop',usage=usage())),DONE])
            cfg=CloudConfig('','https://hcla.example.test','owner',self.verifier,'1'*64,self.monthly_config,selected_provider='qwen')
            return CloudApplication(cfg,store=self.store(),adapter=create_adapter(self.monthly_config,transport_factory=lambda *_:fake),runtime=runtime),fake
        app,fake=make_app();cookie=app.development_auth.cookie(app.development_auth.login({'login':'owner','password':'offline password fixture'}))
        c={'id':'temp-'+str(uuid.uuid4()),'memory':'TEMPORARY'}
        request=baseline.CloudPostgresTests.request(self,c,SMOKE_TEXT)
        request['development_execution']={'schema_version':'1.0','capability_id':'belief_interpretation','query':SMOKE_QUERY,
            'input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}
        class Handler:
            headers={'Cookie':cookie}
            def __init__(self):self.wfile=io.BytesIO()
            def send_response(self,*a):pass
            def send_header(self,*a):pass
            def end_headers(self):pass
        handler=Handler();execute_temporary(app,handler,{'conversation_id':c['id'],'request_id':str(uuid.uuid4()),'snapshot':None,'request':request})
        packet=[json.loads(line[6:]) for line in handler.wfile.getvalue().decode().splitlines() if line.startswith('data: ')][-1]['payload']
        first=packet['view']['runs'][-1]
        self.assertEqual(first['run_receipt']['outcome'],'COMPLETED',first['run_receipt'])
        self.assertEqual(first['run_receipt']['actual_treatment'],'EXECUTED')
        self.assertEqual(first['run_receipt']['usage']['budget']['max_cost_cny'],'500')
        self.assertEqual(fake.post_calls,1);self.assertTrue(app.live_chat_service.budget.smoke_ready())
        second,fake2=make_app();store=second.stores.persistent;conv=store.conversation('hcla-owner')
        ctrl=second.controller(store)
        run=ctrl.handle_interaction('hcla-owner',baseline.CloudPostgresTests.request(self,conv,'原创虚构：怎样区分当事人的信念与已核实的事实？'),defer=True)
        put=store.put
        def slow_publication(tenant,typ,body):
            value=put(tenant,typ,body)
            if typ=='run' and body.get('run_receipt',{}).get('outcome')=='COMPLETED' and not body.get('pending'):time.sleep(.3)
            return value
        store.put=slow_publication
        result=second.execute('hcla-owner',run['run_id'])
        self.assertEqual(result['run_receipt']['outcome'],'COMPLETED',result['run_receipt'])
        self.assertEqual(fake2.post_calls,1)
        rows=self.admin.execute('SELECT kind,settled,charged_cny,reserved_cny FROM hcla.qwen_monthly_attempts').fetchall()
        self.assertEqual({r['kind'] for r in rows},{'SMOKE','OWNER'})
        self.assertTrue(all(r['settled'] and r['charged_cny']<r['reserved_cny'] for r in rows))
        self.assertNotIn(SMOKE_TEXT,str(self.admin.execute('SELECT * FROM hcla.qwen_monthly_attempts').fetchall()))
        self.assertNotIn(REASONING,handler.wfile.getvalue().decode())
