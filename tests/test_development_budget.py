"""Original synthetic, offline-only configuration and admission-budget checks."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from packages.adapter.development_budget import (
    BudgetError, ConfigurationError, DevelopmentBudget, DevelopmentConfig,
    MAX_INPUT_BYTES, configuration_status,
)


def fake_env(**changes):
    env = {
        'HCLA_DEEPSEEK_API_KEY': 'synthetic-provider-key-not-a-credential',
        'HCLA_DEEPSEEK_BASE_URL': 'https://api.deepseek.com/v1',
        'HCLA_DEEPSEEK_MODEL': 'synthetic-test-model',
        'HCLA_DEV_ACCESS_TOKEN': 'synthetic-local-access-token-not-a-credential',
        'HCLA_DEV_MAX_REQUESTS': '3',
        'HCLA_DEV_MAX_COST_USD': '1.00',
        'HCLA_DEV_INPUT_USD_PER_MILLION': '1',
        'HCLA_DEV_OUTPUT_USD_PER_MILLION': '2',
        'HCLA_DEV_MAX_OUTPUT_TOKENS': '100',
        'HCLA_DEV_BUDGET_ID': 'synthetic-approved-budget-001',
    }
    env.update(changes)
    return env


class DevelopmentConfigurationTests(unittest.TestCase):
    def test_all_settings_are_explicit_no_live_defaults(self):
        env = fake_env()
        self.assertEqual(configuration_status(env), {'configured': True, 'missing': [], 'invalid': []})
        for name in env:
            with self.subTest(name=name):
                partial = dict(env)
                del partial[name]
                with self.assertRaises(ConfigurationError) as caught:
                    DevelopmentConfig.from_env(partial)
                self.assertEqual(caught.exception.missing, (name,))
                self.assertEqual(configuration_status(partial)['missing'], [name])

    def test_missing_config_does_not_read_os_environment_open_db_or_network(self):
        with mock.patch('os.getenv', side_effect=AssertionError('environment access')), \
             mock.patch('sqlite3.connect', side_effect=AssertionError('database access')), \
             mock.patch('socket.socket', side_effect=AssertionError('network access')):
            status = configuration_status({})
        self.assertFalse(status['configured'])
        self.assertEqual(set(status['missing']), set(fake_env()))

    def test_repr_status_and_errors_do_not_disclose_values(self):
        env = fake_env()
        config = DevelopmentConfig.from_env(env)
        outputs = [repr(config), str(config), json.dumps(configuration_status(env))]
        bad = dict(env, HCLA_DEEPSEEK_BASE_URL='https://secret-synthetic-token@example.test')
        try:
            DevelopmentConfig.from_env(bad)
        except ConfigurationError as error:
            outputs += [str(error), repr(error), json.dumps(configuration_status(bad))]
        else:
            self.fail('unsafe endpoint accepted')
        for value in (env['HCLA_DEEPSEEK_API_KEY'], env['HCLA_DEV_ACCESS_TOKEN'],
                      env['HCLA_DEEPSEEK_MODEL'], env['HCLA_DEEPSEEK_BASE_URL'],
                      env['HCLA_DEV_BUDGET_ID'], bad['HCLA_DEEPSEEK_BASE_URL']):
            self.assertNotIn(value, '\n'.join(outputs))

    def test_numeric_configuration_rejects_nonfinite_zero_negative_and_unbounded(self):
        for name in ('HCLA_DEV_MAX_REQUESTS', 'HCLA_DEV_MAX_OUTPUT_TOKENS'):
            for value in ('0', '-1', '1.2', 'True', '10000000000', ' 1'):
                with self.subTest(name=name, value=value), self.assertRaises(ConfigurationError):
                    DevelopmentConfig.from_env(fake_env(**{name: value}))
        for name in ('HCLA_DEV_MAX_COST_USD', 'HCLA_DEV_INPUT_USD_PER_MILLION',
                     'HCLA_DEV_OUTPUT_USD_PER_MILLION'):
            for value in ('NaN', 'Infinity', '-1', '0', '1e10', '0.0000000000001', ' 1'):
                with self.subTest(name=name, value=value), self.assertRaises(ConfigurationError):
                    DevelopmentConfig.from_env(fake_env(**{name: value}))

    def test_secrets_cannot_inject_headers_and_endpoint_cannot_redirect_credentials(self):
        for name in ('HCLA_DEEPSEEK_API_KEY', 'HCLA_DEV_ACCESS_TOKEN'):
            for value in ('unsafe\r\nheader', 'has a space', 'unsafe\x00'):
                with self.subTest(name=name), self.assertRaises(ConfigurationError):
                    DevelopmentConfig.from_env(fake_env(**{name: value}))
        for url in ('http://api.deepseek.com', 'https://api.deepseek.com.evil.test',
                    'https://api.deepseek.com@evil.test', 'https://api.deepseek.com?token=x',
                    'https://api.deepseek.com/#fragment', 'https://api.deepseek.com/v2'):
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                DevelopmentConfig.from_env(fake_env(HCLA_DEEPSEEK_BASE_URL=url))


class DevelopmentBudgetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'development-budget.sqlite'
        self.config = DevelopmentConfig.from_env(fake_env())
        self.budgets = []

    def tearDown(self):
        for budget in self.budgets:
            if budget._held is not None:
                # Every test must explicitly finish its worker; do not silently
                # repair a real budget or refund a failed test's reservation.
                self.fail('test left an active transport owner')
            budget.close()
        self.directory.cleanup()

    def budget(self, config=None):
        budget = DevelopmentBudget(self.path, config or self.config)
        self.budgets.append(budget)
        return budget

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(BudgetError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_exact_conservative_decimal_reservation_and_known_usage(self):
        budget = self.budget()
        reservation = budget.reserve('run-1', 'attempt-1', 1000)
        self.assertTrue(reservation.granted)
        self.assertEqual(reservation.reserved_cost_usd, Decimal('0.0012'))
        self.assertEqual(budget.snapshot()['active_requests'], 1)
        self.assertIsNone(budget.snapshot()['known_usage_priced_upper_bound_usd'])
        budget.finish('run-1', 'attempt-1', 'completed', input_tokens=250, output_tokens=10)
        state = budget.snapshot()
        self.assertEqual(state['known_usage_priced_upper_bound_usd'], '0.00027')
        self.assertEqual(state['charged_cost_usd'], '0.0012')
        self.assertEqual(state['unknown_usage_requests'], 0)
        self.assertEqual(state['active_requests'], 0)

    def test_duplicate_attempt_is_idempotent_never_grants_a_second_dispatch(self):
        budget = self.budget()
        self.assertTrue(budget.reserve('run-1', 'attempt-1', 10).granted)
        self.assertFalse(budget.reserve('run-1', 'attempt-1', 10).granted)
        self.assert_code('attempt_payload_mismatch', budget.reserve, 'run-1', 'attempt-1', 11)
        budget.finish('run-1', 'attempt-1', 'unknown')
        self.assertFalse(budget.reserve('run-1', 'attempt-1', 10).granted)
        self.assertEqual(budget.snapshot()['request_count'], 1)

    def test_input_is_bounded_in_utf8_bytes_including_multibyte_messages(self):
        budget = self.budget()
        for size in (0, -1, MAX_INPUT_BYTES + 1, True, 1.0, b'payload'):
            self.assert_code('input_byte_limit', budget.reserve, 'run-1', 'attempt-1', size)
        text = '合成' * 1366
        self.assertGreater(len(text.encode('utf-8')), MAX_INPUT_BYTES)
        self.assert_code('input_byte_limit', budget.reserve, 'run-1', 'attempt-1', len(text.encode('utf-8')))
        self.assertTrue(budget.reserve('run-1', 'attempt-1', MAX_INPUT_BYTES).granted)
        budget.finish('run-1', 'attempt-1', 'completed')

    def test_caps_survive_restart_unknown_failure_and_cancellation_are_not_refunded(self):
        budget = self.budget()
        for index, outcome in enumerate(('unknown', 'failed', 'cancelled')):
            self.assertTrue(budget.reserve('run-' + str(index), 'attempt-1', 100).granted)
            budget.finish('run-' + str(index), 'attempt-1', outcome)
        expected = budget.snapshot()
        budget.close()
        restarted = self.budget()
        self.assertEqual(restarted.snapshot(), expected)
        self.assertEqual(expected['unknown_usage_requests'], 3)
        self.assertEqual(expected['charged_cost_usd'], '0.0009')
        self.assert_code('request_budget_exhausted', restarted.reserve, 'run-4', 'attempt-1', 1)

    def test_known_lower_cost_does_not_automatically_refund_capacity(self):
        budget = self.budget(replace(self.config, max_cost_usd=Decimal('0.0003')))
        budget.reserve('run-1', 'attempt-1', 100)
        budget.finish('run-1', 'attempt-1', 'completed', input_tokens=0, output_tokens=0, actual_cost_usd='0')
        self.assertEqual(budget.snapshot()['known_usage_priced_upper_bound_usd'], '0')
        self.assert_code('cost_budget_exhausted', budget.reserve, 'run-2', 'attempt-1', 1)
        self.assertEqual(budget.snapshot()['request_count'], 1)

    def test_higher_actual_usage_or_cost_is_recorded_and_blocks_over_cap(self):
        budget = self.budget(replace(self.config, max_cost_usd=Decimal('0.001')))
        budget.reserve('run-1', 'attempt-1', 100)
        budget.finish('run-1', 'attempt-1', 'completed', input_tokens=1000, output_tokens=100,
                      actual_cost_usd='0.0015')
        state = budget.snapshot()
        self.assertTrue(state['over_budget'])
        self.assertEqual(state['charged_cost_usd'], '0.0015')
        self.assert_code('cost_budget_exhausted', budget.reserve, 'run-2', 'attempt-1', 1)
        budget.finish('run-1', 'attempt-1', 'completed', input_tokens=1000, output_tokens=100,
                      actual_cost_usd='0.0001')
        self.assertEqual(budget.snapshot()['charged_cost_usd'], '0.0015')

    def test_cost_at_exact_cap_is_allowed_but_one_byte_more_is_rejected(self):
        budget = self.budget(replace(self.config, max_cost_usd=Decimal('0.0003')))
        self.assert_code('cost_budget_exhausted', budget.reserve, 'run-1', 'attempt-1', 101)
        self.assertEqual(budget.snapshot()['request_count'], 0)
        budget.reserve('run-1', 'attempt-1', 100)
        budget.finish('run-1', 'attempt-1', 'completed')

    def test_real_model_reserves_full_context_within_initial_ten_dollar_grant(self):
        config=DevelopmentConfig.from_env(fake_env(HCLA_DEEPSEEK_MODEL='deepseek-v4-pro',HCLA_DEV_MAX_REQUESTS='6',HCLA_DEV_MAX_COST_USD='10',HCLA_DEV_MAX_OUTPUT_TOKENS='2048',HCLA_DEV_INPUT_USD_PER_MILLION='1.32',HCLA_DEV_OUTPUT_USD_PER_MILLION='3.96'))
        budget=self.budget(config)
        for n in range(6):
            r=budget.reserve('r'+str(n),'a'+str(n),100)
            self.assertEqual(r.reserved_cost_usd,Decimal('1.3922304'))
            budget.finish('r'+str(n),'a'+str(n),'unknown')
        with self.assertRaises(BudgetError):budget.reserve('r7','a7',100)
        self.assertEqual(budget.snapshot()['reserved_cost_usd'],'8.3533824')
    def test_policy_changes_cannot_reset_or_expand_the_same_database(self):
        budget = self.budget()
        budget.reserve('run-1', 'attempt-1', 10)
        budget.finish('run-1', 'attempt-1', 'unknown')
        for changes in ({'max_requests': 4}, {'max_requests': 1}, {'max_cost_usd': Decimal('2')},
                        {'budget_id': 'another-budget'}, {'model': 'another-model'},
                        {'input_usd_per_million': Decimal('0.1')},
                        {'output_usd_per_million': Decimal('0.1')},
                        {'max_output_tokens': 50}, {'base_url': 'https://api.deepseek.com'}):
            with self.subTest(changes=changes):
                self.assert_code('budget_policy_mismatch', DevelopmentBudget, self.path, replace(self.config, **changes))
        self.assertEqual(budget.snapshot()['request_count'], 1)
        # Credential rotation does not create a new budget or store new secrets.
        rotated = self.budget(replace(self.config, api_key='fake.rotation.placeholder', access_token='fake.rotation.placeholder.token'))
        self.assertEqual(rotated.snapshot()['request_count'], 1)

    def test_same_object_concurrency_one_and_close_cannot_release_live_worker(self):
        budget = self.budget()
        budget.reserve('run-1', 'attempt-1', 100)
        self.assert_code('concurrency_limit', budget.reserve, 'run-2', 'attempt-1', 100)
        self.assert_code('active_attempt_must_finish', budget.close)
        budget.finish('run-1', 'attempt-1', 'cancelled')
        self.assertTrue(budget.reserve('run-2', 'attempt-1', 100).granted)
        budget.finish('run-2', 'attempt-1', 'completed')

    def test_second_instance_cannot_recover_or_finish_a_live_owner(self):
        owner = self.budget()
        owner.reserve('run-1', 'attempt-1', 100)
        observer = self.budget()
        self.assertEqual(observer.snapshot()['active_requests'], 1)
        self.assertFalse(observer.reserve('run-1', 'attempt-1', 100).granted)
        self.assert_code('concurrency_limit', observer.reserve, 'run-2', 'attempt-1', 100)
        self.assert_code('attempt_owner_required', observer.finish, 'run-1', 'attempt-1', 'unknown')
        owner.finish('run-1', 'attempt-1', 'completed')
        self.assertTrue(observer.reserve('run-2', 'attempt-1', 100).granted)
        observer.finish('run-2', 'attempt-1', 'completed')

    def test_concurrent_independent_instances_grant_exactly_one_dispatch(self):
        budgets = [self.budget() for _ in range(8)]
        barrier = threading.Barrier(len(budgets))
        def contender(index):
            barrier.wait()
            try:
                return index, budgets[index].reserve('run-' + str(index), 'attempt-1', 100).granted
            except BudgetError as error:
                return index, error.code
        with ThreadPoolExecutor(max_workers=len(budgets)) as pool:
            results = list(pool.map(contender, range(len(budgets))))
        winners = [index for index, result in results if result is True]
        self.assertEqual(len(winners), 1)
        self.assertEqual(sum(result == 'concurrency_limit' for _, result in results), 7)
        self.assertEqual(budgets[0].snapshot()['request_count'], 1)
        budgets[winners[0]].finish('run-' + str(winners[0]), 'attempt-1', 'unknown')

    def test_concurrent_identical_attempts_are_idempotent(self):
        budgets = [self.budget() for _ in range(8)]
        barrier = threading.Barrier(len(budgets))
        def contender(index):
            barrier.wait()
            try:
                return index, budgets[index].reserve('run-1', 'attempt-1', 100).granted
            except BudgetError as error:
                return index, error.code
        with ThreadPoolExecutor(max_workers=len(budgets)) as pool:
            results = list(pool.map(contender, range(len(budgets))))
        winners = [index for index, result in results if result is True]
        self.assertEqual(len(winners), 1)
        self.assertEqual(budgets[0].snapshot()['request_count'], 1)
        budgets[winners[0]].finish('run-1', 'attempt-1', 'unknown')
        self.assertFalse(budgets[1].reserve('run-1', 'attempt-1', 100).granted)

    def test_process_crash_recovers_as_unknown_without_refund_or_retry(self):
        script = '''import json, os, sys
from packages.adapter.development_budget import DevelopmentBudget, DevelopmentConfig
budget=DevelopmentBudget(sys.argv[1], DevelopmentConfig.from_env(json.loads(sys.argv[2])))
assert budget.reserve('interrupted-run', 'attempt-1', 100).granted
os._exit(0)
'''
        result = subprocess.run([sys.executable, '-c', script, str(self.path), json.dumps(fake_env())],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        budget = self.budget()
        self.assertEqual(budget.snapshot()['request_count'], 1)
        self.assertEqual(budget.snapshot()['active_requests'], 0)
        self.assertEqual(budget.snapshot()['charged_cost_usd'], '0.0003')
        duplicate = budget.reserve('interrupted-run', 'attempt-1', 100)
        self.assertFalse(duplicate.granted)
        self.assertEqual(duplicate.outcome, 'unknown')
        self.assertTrue(budget.reserve('new-run', 'attempt-1', 100).granted)
        budget.finish('new-run', 'attempt-1', 'completed')

    def test_live_process_keeps_lock_and_is_never_recovered_as_unknown(self):
        script = """import json, sys
from packages.adapter.development_budget import DevelopmentBudget, DevelopmentConfig
budget=DevelopmentBudget(sys.argv[1], DevelopmentConfig.from_env(json.loads(sys.argv[2])))
assert budget.reserve('live-process-run', 'attempt-1', 100).granted
print('reserved', flush=True)
sys.stdin.readline()
budget.finish('live-process-run', 'attempt-1', 'unknown')
budget.close()
"""
        process = subprocess.Popen([sys.executable, '-c', script, str(self.path), json.dumps(fake_env())],
                                   cwd=Path(__file__).resolve().parents[1], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), 'reserved')
            budget = self.budget()
            self.assertEqual(budget.snapshot()['active_requests'], 1)
            self.assert_code('concurrency_limit', budget.reserve, 'run-2', 'attempt-1', 100)
            self.assert_code('attempt_owner_required', budget.finish, 'live-process-run', 'attempt-1', 'unknown')
            _, errors = process.communicate('finish\n', timeout=10)
            self.assertEqual(process.returncode, 0, errors)
            self.assertTrue(budget.reserve('run-2', 'attempt-1', 100).granted)
            budget.finish('run-2', 'attempt-1', 'completed')
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)

    def test_late_usage_can_reconcile_without_resetting_unknown_attempt(self):
        budget = self.budget()
        budget.reserve('run-1', 'attempt-1', 100)
        budget.finish('run-1', 'attempt-1', 'unknown')
        budget.finish('run-1', 'attempt-1', 'unknown', input_tokens=20, output_tokens=10)
        self.assertEqual(budget.snapshot()['known_usage_priced_upper_bound_usd'], '0.00004')
        self.assertEqual(budget.snapshot()['charged_cost_usd'], '0.0003')
        self.assert_code('usage_already_recorded', budget.finish, 'run-1', 'attempt-1', 'unknown',
                         input_tokens=21, output_tokens=10)
        self.assertFalse(budget.reserve('run-1', 'attempt-1', 100).granted)

    def test_database_contains_metadata_only_no_secret_prompt_or_raw_identifiers(self):
        budget = self.budget()
        text = 'Original synthetic meeting prompt that must never be persisted'
        budget.reserve('raw-run-identifier', 'raw-attempt-identifier', len(text.encode('utf-8')))
        budget.finish('raw-run-identifier', 'raw-attempt-identifier', 'completed', input_tokens=10, output_tokens=2)
        public = repr(budget) + json.dumps(budget.snapshot())
        budget.close()
        with sqlite3.connect(self.path) as connection:
            dump = '\n'.join(connection.iterdump())
        for value in (text, 'raw-run-identifier', 'raw-attempt-identifier', self.config.api_key,
                      self.config.access_token, self.config.model, self.config.base_url, self.config.budget_id):
            self.assertNotIn(value, dump)
            self.assertNotIn(value, public)

    def test_budget_refuses_memory_uri_or_content_ledger_database(self):
        for path in (':memory:', '', 'file:memory?mode=memory&cache=shared'):
            self.assert_code('durable_database_required', DevelopmentBudget, path, self.config)
        with sqlite3.connect(self.path) as connection:
            connection.execute('CREATE TABLE bodies(body TEXT)')
            connection.execute('INSERT INTO bodies VALUES(?)', ('synthetic existing body',))
        self.assert_code('dedicated_budget_database_required', DevelopmentBudget, self.path, self.config)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute('SELECT body FROM bodies').fetchone()[0], 'synthetic existing body')
            self.assertEqual(connection.execute("SELECT count(*) FROM sqlite_master WHERE name='development_budget_policy'").fetchone()[0], 0)

    def test_invalid_usage_never_releases_an_active_attempt(self):
        budget = self.budget()
        budget.reserve('run-1', 'attempt-1', 100)
        for kwargs in ({'input_tokens': -1, 'output_tokens': 1}, {'input_tokens': True, 'output_tokens': 1},
                       {'input_tokens': 1}, {'actual_cost_usd': 'NaN'}, {'actual_cost_usd': '-1'},
                       {'actual_cost_usd': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(BudgetError):
                budget.finish('run-1', 'attempt-1', 'completed', **kwargs)
        self.assertEqual(budget.snapshot()['active_requests'], 1)
        budget.finish('run-1', 'attempt-1', 'unknown')
        self.assert_code('attempt_already_finished', budget.finish, 'run-1', 'attempt-1', 'completed')

    def test_small_explicit_decimal_prices_remain_exact(self):
        config = DevelopmentConfig.from_env(fake_env(HCLA_DEV_INPUT_USD_PER_MILLION='0.000000000001'))
        budget = self.budget(config)
        reservation = budget.reserve('run-1', 'attempt-1', 1)
        self.assertEqual(reservation.reserved_cost_usd, Decimal('0.000200000000000001'))
        budget.finish('run-1', 'attempt-1', 'unknown')


if __name__ == '__main__':
    unittest.main()
