"""Original synthetic Qwen contract tests. Sockets fail before any live dispatch."""
from dataclasses import asdict, replace
from contextlib import contextmanager
from decimal import Decimal
import json
import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from packages.adapter.deepseek import DeepSeekAdapter
from packages.adapter.provider import create_adapter
from packages.adapter.qwen import QwenAdapter, MODEL, endpoint
from packages.adapter.development_budget import BudgetError
from packages.cloud.config import CloudConfig
from packages.cloud.qwen_config import QwenConfig
from packages.cloud.qwen_budget import QwenCloudBudget
from packages.controller.interaction import Controller
from packages.controller.live_chat import LiveChat
from packages.store.ledger import Ledger
from tests.test_deepseek_adapter import FakeTransport, event, chunk, DONE, SECRET, REASONING, MESSAGES
from tests import test_cloud as cloud_tests


def grant(**changes):
    result = {'provider': 'qwen', 'model': MODEL, 'region': 'cn-beijing', 'currency': 'CNY',
              'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
              'budget_id': 'hcla-qwen-cny-offline-only', 'max_requests': 2,
              'max_cost_cny': '26', 'input_cny_per_million': '12',
              'output_cny_per_million': '36', 'max_completion_tokens': 8192}
    return {**result, **changes}


SMOKE_TEXT='Mira said, "I believe that the team meeting was moved to Thursday."'
SMOKE_QUERY='What does Mira believe, and does this establish the actual meeting date?'


def smoke_policy():
    return {'scope':'OWNER_ONLY_SYNTHETIC_SMOKE',
            'input_sha256':hashlib.sha256(SMOKE_TEXT.encode()).hexdigest(),
            'query_sha256':hashlib.sha256(SMOKE_QUERY.encode()).hexdigest()}


def qchunk(*args, **kwargs):
    return chunk(*args, model=MODEL, **kwargs)


def usage(prompt=10, completion=12):
    return {'prompt_tokens': prompt, 'completion_tokens': completion,
            'total_tokens': prompt+completion, 'completion_tokens_details': {'reasoning_tokens': 5}}


def wire(completion=12, finish='stop', include_usage=True):
    return [event(qchunk(reasoning=REASONING)), event(qchunk('原创纸灯活动方案')),
            event(qchunk(finish=finish)),
            event({'id': 'qwen-offline-request', 'model': MODEL, 'choices': [],
                   'usage': usage(completion=completion) if include_usage else None}), DONE]


class QwenTransportTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.create_connection', side_effect=AssertionError('network forbidden'))
        guard.start(); self.addCleanup(guard.stop)

    def adapter(self, fake, **kwargs):
        return QwenAdapter(base_url=grant()['base_url'], model=MODEL, api_key=SECRET,
                           transport_factory=lambda *_: fake, **kwargs)

    def test_native_thinking_and_total_output_wire_contract(self):
        fake = FakeTransport(wire()); deltas = []
        result = self.adapter(fake).generate(MESSAGES, max_tokens=8192, on_delta=deltas.append)
        self.assertEqual(result.outcome, 'SUCCEEDED')
        self.assertLessEqual(len(fake.body),8192)
        body = json.loads(fake.body)
        self.assertEqual(body, {'model': MODEL, 'messages': MESSAGES, 'stream': True,
                               'stream_options': {'include_usage': True}, 'enable_thinking': True,
                               'reasoning_effort': 'xhigh', 'max_completion_tokens': 8192})
        self.assertEqual(result.usage['reasoning_tokens'], 5)
        for private in (SECRET, REASONING, 'reasoning_content'):
            self.assertNotIn(private, repr(asdict(result))+repr(deltas))

    def test_region_origin_and_path_are_exact_even_for_injected_transport(self):
        self.assertEqual(endpoint('https://demo-workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/'),
                         'https://demo-workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions')
        for base in ('http://dashscope.aliyuncs.com/compatible-mode/v1',
                     'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com@evil.test/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com/compatible-mode/v1?key=sentinel',
                     'https://dashscope.aliyuncs.com/compatible-mode/v1#fragment',
                     'https://dashscope.aliyuncs.com:444/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com/compatible-mode/v1/../v1',
                     'https://dashscope.aliyuncs.com/compatible-mode/v1//',
                     'https://dashscope.aliyuncs.com/api/v1',
                     'https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1'):
            with self.subTest(base=base), self.assertRaises(ValueError):
                QwenAdapter(base_url=base, model=MODEL, api_key=SECRET, transport_factory=lambda *_: FakeTransport())

    def test_finish_usage_and_model_evidence_fail_closed(self):
        for values, expected, error in ((wire(finish='length'), 'PARTIAL', 'length'),
                                        (wire(include_usage=False), 'UNKNOWN', 'usage_unverified'),
                                        (wire(completion=8203), 'UNKNOWN', 'usage_limit'),
                                        (wire()[:-1], 'UNKNOWN', 'early_eof')):
            with self.subTest(error=error):
                fake = FakeTransport(values)
                result = self.adapter(fake).generate(MESSAGES, max_tokens=8192)
                self.assertEqual((result.outcome, result.error_code), (expected, error))
                self.assertEqual(fake.post_calls, 1)
        self.assertEqual(self.adapter(FakeTransport(wire(completion=8202))).generate(MESSAGES, max_tokens=8192).outcome, 'SUCCEEDED')
        result = self.adapter(FakeTransport([event(chunk('wrong model')), DONE])).generate(MESSAGES, max_tokens=8192)
        self.assertEqual(result.error_code, 'model_mismatch')

    def test_caps_and_cancel_refuse_without_dispatch(self):
        import threading
        for cap in (0, -1, True, 131073):
            fake = FakeTransport(wire())
            result = self.adapter(fake).generate(MESSAGES, max_tokens=cap)
            self.assertEqual(result.outcome, 'FAILED'); self.assertEqual(fake.post_calls, 0)
        cancel = threading.Event(); cancel.set(); fake = FakeTransport(wire())
        result = self.adapter(fake).generate(MESSAGES, max_tokens=8192, cancel_event=cancel)
        self.assertEqual(result.outcome, 'CANCELLED'); self.assertEqual(fake.post_calls, 0)
        fake = FakeTransport(wire())
        result = self.adapter(fake).generate([{'role':'user','content':'界'*3000}],max_tokens=8192)
        self.assertEqual(result.outcome,'FAILED'); self.assertEqual(fake.post_calls,0)

    def test_provider_factory_does_not_switch_or_fallback(self):
        deepseek = SimpleNamespace(base_url='https://api.deepseek.com', model='explicit-model', api_key=SECRET)
        self.assertIsInstance(create_adapter(deepseek), DeepSeekAdapter)
        self.assertNotIsInstance(create_adapter(deepseek), QwenAdapter)
        self.assertIsInstance(create_adapter(QwenConfig.from_grant(grant(), SECRET)), QwenAdapter)
        with self.assertRaises(ValueError):
            create_adapter(SimpleNamespace(provider_id='unapproved', **vars(deepseek)))


class QwenConfigTests(unittest.TestCase):
    def test_optional_smoke_grant_requires_one_exact_fresh_temporary_request(self):
        cfg=QwenConfig.from_grant(grant(max_requests=1,max_cost_cny='13',max_completion_tokens=4096,smoke=smoke_policy()),SECRET)
        request={'expected_state_version':0,'event':{'text':SMOKE_TEXT},
                 'development_execution':{'capability_id':'belief_interpretation','query':SMOKE_QUERY}}
        cfg.authorize_request(request,{'memory':'TEMPORARY'})
        for changed,conversation in [({**request,'expected_state_version':1},{'memory':'TEMPORARY'}),
             ({**request,'event':{'text':'Other question'}},{'memory':'TEMPORARY'}),
             ({**request,'event':{'text':SMOKE_TEXT,'type':'upload'}},{'memory':'TEMPORARY'}),
             (request,{'memory':'CONVERSATION'})]:
            with self.assertRaises(ValueError):cfg.authorize_request(changed,conversation)
        self.assertEqual(json.loads(cfg.policy())['smoke'],smoke_policy())
        with self.assertRaises(ValueError):QwenConfig.from_grant(grant(smoke=smoke_policy()),SECRET)
    def test_explicit_exact_cny_contract_and_finite_bounds(self):
        cfg = QwenConfig.from_grant(grant(), SECRET)
        self.assertEqual(cfg.reserved_output_tokens, 8202)
        self.assertNotIn(SECRET, repr(cfg)+cfg.policy())
        self.assertEqual(json.loads(cfg.policy())['currency'], 'CNY')
        for field in grant():
            partial = grant(); partial.pop(field)
            with self.subTest(missing=field), self.assertRaises(ValueError): QwenConfig.from_grant(partial, SECRET)
        for field, value in [('currency','USD'), ('region','ap-southeast-1'), ('model','qwen3.8-max-0902'),
                             ('provider','deepseek'), ('max_requests',True), ('max_requests',0),
                             ('max_completion_tokens',131073), ('max_completion_tokens',True),
                             ('max_cost_cny','NaN'), ('max_cost_cny','0'), ('max_cost_cny','Infinity'),
                             ('input_cny_per_million','11.99'), ('output_cny_per_million','35.99'),
                             ('budget_id','old-deepseek-budget')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                QwenConfig.from_grant(grant(**{field:value}), SECRET)

    def test_key_selection_and_old_trial_cannot_activate_qwen(self):
        cloud_tests.CloudUnitTests.setUpClass()
        env = cloud_tests.CloudUnitTests().env()
        env.update(HCLA_PROVIDER='qwen', HCLA_QWEN_API_KEY=SECRET)
        cfg = CloudConfig.from_env(env)
        self.assertIsNone(cfg.provider); self.assertEqual(cfg.cloud_api_key, '')
        from packages.cloud.trial import from_database_policy
        store = SimpleNamespace(transaction=lambda: self.fail('No old trial lookup'))
        self.assertIs(from_database_policy(store, cfg), cfg)
        env['HCLA_QWEN_MODEL_GRANT'] = json.dumps(grant())
        cfg = CloudConfig.from_env(env); self.assertEqual(cfg.provider.currency, 'CNY')
        for key, value in [('HCLA_MODEL_GRANT', '{}'), ('HCLA_CLOUD_PROVIDER_ENABLED','true'),
                           ('HCLA_TRIAL_WINDOW','{}')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                CloudConfig.from_env({**env, key:value})
        with self.assertRaises(ValueError):
            CloudConfig.from_env({**env, 'HCLA_PROVIDER':'deepseek'})
        from apps.api.development_server import application
        from tests.test_development_budget import fake_env
        with self.assertRaisesRegex(ValueError,'cloud CNY policy'):
            application(':memory:',':memory:',env=fake_env(HCLA_PROVIDER='qwen'))


class BudgetStore(Ledger):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.db.create_function('to_regclass',1,lambda _:None)
        self.db.executescript('''
        CREATE TABLE qwen_budget_policy(singleton INTEGER PRIMARY KEY, policy TEXT);
        CREATE TABLE qwen_budget_attempts(run_key TEXT, attempt_key TEXT, input_bytes INTEGER,
        reserved_cny TEXT, charged_cny TEXT, outcome TEXT, input_tokens INTEGER,
        output_tokens INTEGER, actual_cny TEXT, PRIMARY KEY(run_key,attempt_key));
        CREATE TABLE budget_attempts(legacy_evidence TEXT,outcome TEXT);
        INSERT INTO budget_attempts VALUES('UNCHANGED_USD_HISTORY','unknown');
        ''')

    @contextmanager
    def transaction(self):
        # Simulate the cloud store's nested transaction shape, not its
        # PostgreSQL/RLS/multi-process guarantees (covered separately in CI).
        with self.lock:
            outer = self.depth == 0
            if outer: self.db.execute('BEGIN IMMEDIATE')
            self.depth += 1
            try:
                yield
                if outer: self.db.execute('COMMIT')
            except BaseException:
                if outer: self.db.execute('ROLLBACK')
                raise
            finally:
                self.depth -= 1


class QwenBudgetControllerTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.create_connection', side_effect=AssertionError('network forbidden'))
        guard.start(); self.addCleanup(guard.stop)
        self.store = BudgetStore(); self.addCleanup(self.store.close)
        self.config = QwenConfig.from_grant(grant(), SECRET)
        self.store.db.execute('INSERT INTO qwen_budget_policy VALUES(1,?)', (self.config.policy(),))
        self.budget = QwenCloudBudget(self.store, self.config)

    def test_separate_cny_policy_reservation_nonrefund_and_concurrency(self):
        reserved = self.budget.reserve('run1','attempt1',512)
        self.assertEqual(reserved.reserved_cost_cny, Decimal('12.295272'))
        self.assertFalse(self.budget.reserve('run1','attempt1',512).granted)
        with self.assertRaises(BudgetError): self.budget.reserve('run2','attempt2',512)
        self.budget.finish('run1','attempt1','completed',10,12)
        snapshot = self.budget.snapshot()
        self.assertEqual(snapshot['charged_cost_cny'], '12.295272')
        self.assertEqual(snapshot['currency'], 'CNY'); self.assertNotIn('max_cost_usd',snapshot)
        self.assertEqual(self.store.db.execute('SELECT * FROM budget_attempts').fetchone()[0], 'UNCHANGED_USD_HISTORY')
        self.budget.reserve('run2','attempt2',512); self.budget.finish('run2','attempt2','unknown')
        with self.assertRaises(BudgetError): self.budget.reserve('run3','attempt3',512)

    def test_policy_change_unsupported_price_and_small_budget_refuse(self):
        with self.assertRaises(BudgetError): QwenCloudBudget(self.store, replace(self.config,max_cost_cny=Decimal('27')))
        with self.assertRaises(ValueError): QwenCloudBudget(self.store, replace(self.config,input_cny_per_million=Decimal('1')))
        self.store.db.execute('DELETE FROM qwen_budget_policy')
        with self.assertRaises(BudgetError): QwenCloudBudget(self.store,self.config)
        cfg = QwenConfig.from_grant(grant(max_cost_cny='12'), SECRET)
        self.store.db.execute('INSERT INTO qwen_budget_policy VALUES(1,?)',(cfg.policy(),))
        with self.assertRaises(BudgetError): QwenCloudBudget(self.store,cfg).reserve('new','attempt',512)

    def test_active_legacy_transport_blocks_qwen_without_touching_usd_rows(self):
        self.store.db.execute("UPDATE budget_attempts SET outcome='active'")
        with self.assertRaisesRegex(BudgetError,'concurrency_or_unconfirmed_transport'):
            self.budget.reserve('new','attempt',512)
        self.assertEqual(self.budget.snapshot()['request_count'],0)
        self.assertEqual(self.store.db.execute('SELECT outcome FROM budget_attempts').fetchone()[0],'active')

    def test_same_controller_publishes_only_verified_answer_and_cny_receipt(self):
        fake = FakeTransport(wire())
        service = LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake))
        ctrl = Controller(self.store,live_chat_service=service)
        tenant = 'synthetic-demo-a'; conversation = self.store.conversation(tenant,memory='TEMPORARY')['id']
        run = ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'expected_state_version':self.store.version(tenant),'idempotency_key':'qwen-one',
            'development_chat':True,'synthetic_input_confirmed':True,
            'event':{'text':'请为虚构的纸灯节起一个名字。'}})
        self.assertEqual(run['run_receipt']['outcome'],'COMPLETED')
        provider = run['run_receipt']['provider']
        self.assertEqual((provider['actual_model'],provider['region'],provider['reasoning_effort']), (MODEL,'cn-beijing','xhigh'))
        self.assertEqual(run['run_receipt']['usage']['cost'], {'amount':None,'currency':'CNY','source':'UNKNOWN'})
        self.assertLessEqual(provider['admission_input_bytes'],8192)
        self.assertEqual(provider['input_token_basis'],'DOCUMENTED_MAX_CONTEXT_NOT_TOKENIZER_ESTIMATE')
        self.assertNotIn(REASONING,json.dumps(run,ensure_ascii=False))
        self.assertNotIn(SECRET,json.dumps(run,ensure_ascii=False))
        self.assertEqual(run['budget']['adapter'],'QWEN')

    def test_explicit_other_provider_policy_is_not_silently_reinterpreted(self):
        fake=FakeTransport(wire())
        ctrl=Controller(self.store,live_chat_service=LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake)))
        tenant='synthetic-demo-a'; conversation=self.store.conversation(tenant,memory='TEMPORARY')['id']
        with self.assertRaisesRegex(ValueError,'explicitly permitted provider'):
            ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
                'expected_state_version':0,'idempotency_key':'wrong-provider',
                'development_chat':True,'synthetic_input_confirmed':True,
                'model_resource_policy':{'adapter':'DEEPSEEK','max_provider_calls':1,'max_adapter_calls':1},
                'event':{'text':'虚构问题'}})
        self.assertEqual(fake.post_calls,0);self.assertEqual(self.budget.snapshot()['request_count'],0)

    def test_unverified_usage_withholds_provisional_answer_and_retains_reservation(self):
        fake = FakeTransport(wire(include_usage=False))
        service = LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake))
        ctrl = Controller(self.store,live_chat_service=service)
        tenant = 'synthetic-demo-a'; conversation = self.store.conversation(tenant,memory='TEMPORARY')['id']
        run = ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'expected_state_version':self.store.version(tenant),'idempotency_key':'qwen-unknown',
            'development_chat':True,'synthetic_input_confirmed':True,'event':{'text':'虚构活动'}})
        self.assertIsNone(run['answer']); self.assertEqual(run['run_receipt']['outcome'],'UNKNOWN')
        self.assertFalse(any(e['type'].startswith('answer.') for e in run['stream']))
        self.assertEqual(self.budget.snapshot()['charged_cost_cny'],'12.295272')

    def test_oversized_final_history_fails_before_reservation_instead_of_pruning(self):
        fake = FakeTransport(wire())
        service = LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake))
        ctrl = Controller(self.store,live_chat_service=service)
        tenant='synthetic-demo-a'; conversation=self.store.conversation(tenant,memory='TEMPORARY')['id']
        for i in range(3):
            ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
                'expected_state_version':self.store.version(tenant),'idempotency_key':'history-'+str(i),
                'event':{'text':'原创虚构说明。'*180}})
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'expected_state_version':self.store.version(tenant),'idempotency_key':'oversized-final',
            'development_chat':True,'synthetic_input_confirmed':True,'event':{'text':'请比较这些虚构报告。'}})
        self.assertIsNone(run['answer']); self.assertEqual(fake.post_calls,0)
        self.assertEqual(self.budget.snapshot()['request_count'],0)
        self.assertIn('8 KiB',run['errors'][0])

    def test_deferred_and_cancelled_before_dispatch_receipts_are_cny(self):
        fake=FakeTransport(wire())
        ctrl=Controller(self.store,live_chat_service=LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake)))
        tenant='synthetic-demo-a'; conversation=self.store.conversation(tenant,memory='TEMPORARY')['id']
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'expected_state_version':0,'idempotency_key':'cancel-before-execute',
            'development_chat':True,'synthetic_input_confirmed':True,'event':{'text':'虚构的人际报告'}},defer=True)
        self.assertEqual(run['run_receipt']['usage']['cost']['currency'],'CNY')
        cancelled=ctrl.cancel(tenant,run['run_id'])
        self.assertEqual(cancelled['run_receipt']['usage']['cost']['currency'],'CNY')
        self.assertEqual(cancelled['run_receipt']['outcome'],'CANCELLED')
        self.assertEqual(fake.post_calls,0)
        self.assertEqual(self.budget.snapshot()['request_count'],0)

    def test_contradictory_usage_does_not_become_known_priced_accounting(self):
        bad=usage(); bad['total_tokens']=999
        fake=FakeTransport([event(qchunk('provisional')),event(qchunk(finish='stop',usage=bad)),DONE])
        ctrl=Controller(self.store,live_chat_service=LiveChat(self.config,self.budget,create_adapter(self.config,transport_factory=lambda *_:fake)))
        tenant='synthetic-demo-a'; conversation=self.store.conversation(tenant,memory='TEMPORARY')['id']
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'expected_state_version':0,'idempotency_key':'contradictory-usage',
            'development_chat':True,'synthetic_input_confirmed':True,'event':{'text':'虚构报告'}})
        self.assertEqual(run['run_receipt']['outcome'],'UNKNOWN')
        snapshot=self.budget.snapshot()
        self.assertEqual(snapshot['unknown_usage_requests'],1)
        self.assertIsNone(snapshot['known_usage_priced_upper_bound_cny'])
        self.assertEqual(snapshot['charged_cost_cny'],'12.295272')

    @unittest.skipUnless(__import__('os').environ.get('HCL_DEVELOPMENT_ARTIFACT'),'Reviewed runtime required for Qwen integration')
    def test_original_social_belief_case_uses_pinned_hcl_without_reasoning_retention(self):
        import os
        from packages.runtime_bridge.bridge import RuntimeBridge
        answer='Mira explicitly said she believes the team meeting was moved to Thursday; this does not prove the meeting actually moved. [HCL1]'
        fake=FakeTransport([event(qchunk(reasoning=REASONING)),event(qchunk(answer)),
                            event(qchunk(finish='stop',usage=usage())),DONE])
        config=QwenConfig.from_grant(grant(max_requests=1,max_cost_cny='13',max_completion_tokens=4096,smoke=smoke_policy()),SECRET)
        self.store.db.execute('UPDATE qwen_budget_policy SET policy=?',(config.policy(),))
        budget=QwenCloudBudget(self.store,config)
        service=LiveChat(config,budget,create_adapter(config,transport_factory=lambda *_:fake))
        ctrl=Controller(self.store,live_chat_service=service,
                        development_bridge=RuntimeBridge(os.environ['HCL_DEVELOPMENT_ARTIFACT']))
        tenant='synthetic-demo-a'; conversation=self.store.conversation(tenant,memory='TEMPORARY')['id']
        run=ctrl.handle_interaction(tenant,{'scope':{'conversation_id':conversation},
            'idempotency_key':'qwen-original-belief','expected_state_version':0,
            'development_chat':True,'synthetic_input_confirmed':True,
            'event':{'text':SMOKE_TEXT},
            'development_execution':{'schema_version':'1.0','capability_id':'belief_interpretation',
                'query':SMOKE_QUERY,
                'input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'ORIGINAL_PRODUCT_SYNTHETIC',
                'purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':3000}})
        self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED')
        self.assertEqual(run['run_receipt']['outcome'],'COMPLETED')
        self.assertTrue(run['operation_receipts'][0]['used_in_answer'])
        self.assertEqual(run['development_result']['provider_calls'],0)
        self.assertNotIn(REASONING,json.dumps(run))
        self.assertEqual(budget.snapshot()['charged_cost_cny'],'12.147816')
