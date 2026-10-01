"""Secret-sentinel startup diagnostics with no database or provider access."""
from contextlib import nullcontext, redirect_stdout
import io
import json
import os
import ssl
import sys
import tempfile
import threading
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from apps.api import cloud_server
from packages.cloud.diagnostics import StartupCode, StartupDiagnostics
from packages.cloud.postgres import PostgresLedger, system_root_cert
from packages.store.ledger import Fault

SENTINEL = 'SECRET_DSN_PASSWORD_OWNER_HASH_QUERY_HOST_CANARY'


class SecretFailure(Exception):
    def __str__(self): raise AssertionError('Exception string must never be inspected')
    def __repr__(self): raise AssertionError('Exception repr must never be inspected')


class Connection:
    def __init__(self, failure=None, role=None, version=1):
        self.failure = failure; self.role = role; self.version = version
        self.closed = 0
    def transaction(self): return nullcontext()
    def execute(self, sql, params=()):
        stage = 'role' if sql.startswith('SELECT rolsuper') else 'schema'
        if self.failure == stage: raise SecretFailure(SENTINEL)
        value = (self.role if self.role is not None else
                 {'rolsuper': False, 'rolbypassrls': False, 'member': True}) if stage == 'role' else {'version': self.version}
        return SimpleNamespace(fetchone=lambda: value)
    def close(self): self.closed += 1


class CloudStartupTests(unittest.TestCase):
    def setUp(self):
        self.capture = io.StringIO()
        capture = patch('sys.stderr', self.capture); capture.start()
        self.addCleanup(capture.stop)
        self.config = SimpleNamespace(database_url=SENTINEL, origin='https://synthetic.example.test',
                                      login=SENTINEL, verifier=SENTINEL, provider=None)

    def check_record(self, code):
        self.assertEqual(self.capture.getvalue(), 'HCLA_STARTUP_FAILED code=' + code + '\n')
        self.assertNotIn(SENTINEL, self.capture.getvalue())

    def check_unconfigured(self, app):
        self.assertIsInstance(app, cloud_server.Unconfigured)
        self.assertEqual(json.dumps(app.configuration), '{"configured": false}')
        self.assertIsNone(app.development_auth)

    def test_config_failure_never_formats_details_or_opens_database(self):
        output = io.StringIO()
        with patch.object(cloud_server.CloudConfig, 'from_env', side_effect=SecretFailure(SENTINEL)), \
             patch.object(cloud_server, 'PostgresLedger') as postgres, redirect_stdout(output):
            self.check_unconfigured(cloud_server.application({'PRIVATE': SENTINEL}))
        postgres.assert_not_called(); self.assertEqual(output.getvalue(), '')
        self.check_record('CONFIG')

    def test_invalid_real_configuration_logs_only_config_code(self):
        self.check_unconfigured(cloud_server.application({'HCLA_DATABASE_URL': SENTINEL,
                                                        'HCLA_PUBLIC_ORIGIN': SENTINEL,
                                                        'HCLA_OWNER_CONFIG': SENTINEL}))
        self.check_record('CONFIG')

    def fake_driver(self, connect):
        driver = ModuleType('psycopg'); driver.connect = connect
        rows = ModuleType('psycopg.rows'); rows.dict_row = object()
        return patch.dict(sys.modules, {'psycopg': driver, 'psycopg.rows': rows})

    def test_connect_and_native_tls_failures_are_safely_distinguished(self):
        for failure, code in [(SecretFailure(SENTINEL), 'DATABASE_CONNECT'),
                              (ssl.SSLError(SENTINEL), 'DATABASE_TLS')]:
            self.capture.seek(0); self.capture.truncate()
            connect = Mock(side_effect=failure)
            with self.fake_driver(connect), patch.object(cloud_server.CloudConfig, 'from_env', return_value=self.config):
                self.check_unconfigured(cloud_server.application({}))
            self.check_record(code)
            self.assertEqual(connect.call_args.kwargs['sslrootcert'], system_root_cert())
            self.assertEqual(connect.call_args.kwargs['sslmode'], 'verify-full')
            self.assertEqual(connect.call_args.kwargs['connect_timeout'], 5)

    def test_missing_database_driver_has_fixed_code(self):
        with patch.dict(sys.modules, {'psycopg': None}), \
             patch.object(cloud_server.CloudConfig, 'from_env', return_value=self.config):
            self.check_unconfigured(cloud_server.application({}))
        self.check_record('DATABASE_DRIVER')

    def test_missing_system_bundle_refuses_without_connect_or_tls_downgrade(self):
        connect=Mock()
        with patch.dict(os.environ,{'SSL_CERT_FILE':'/synthetic/missing-explicit-ca'}), \
             patch('packages.cloud.postgres.ssl.get_default_verify_paths', return_value=SimpleNamespace(cafile=None)), \
             self.fake_driver(connect), patch.object(cloud_server.CloudConfig, 'from_env', return_value=self.config):
            self.check_unconfigured(cloud_server.application({}))
        connect.assert_not_called();self.check_record('DATABASE_TLS')

    def test_ca_discovery_requires_an_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle=Path(directory)/'synthetic-public-ca.pem';bundle.write_text('synthetic fixture')
            for path in (None, str(Path(directory)/'missing'), directory):
                with patch.dict(os.environ,{'SSL_CERT_FILE':'/synthetic/explicit-ca'}),patch('packages.cloud.postgres.ssl.get_default_verify_paths',return_value=SimpleNamespace(cafile=path)):
                    with self.assertRaises(Fault):system_root_cert()
            with patch('packages.cloud.postgres.ssl.get_default_verify_paths',return_value=SimpleNamespace(cafile=str(bundle))):
                self.assertEqual(system_root_cert(),str(bundle))

    def test_standalone_python_can_use_only_existing_os_bundles(self):
        candidate='/etc/pki/tls/certs/ca-bundle.crt'
        with patch.dict(os.environ,{},clear=True), \
             patch('packages.cloud.postgres.ssl.get_default_verify_paths',return_value=SimpleNamespace(cafile=None)), \
             patch('packages.cloud.postgres.Path.is_file',lambda path:str(path)==candidate):
            self.assertEqual(system_root_cert(),candidate)
        with patch.dict(os.environ,{},clear=True), \
             patch('packages.cloud.postgres.ssl.get_default_verify_paths',return_value=SimpleNamespace(cafile=None)), \
             patch('packages.cloud.postgres.Path.is_file',return_value=False):
            with self.assertRaises(Fault):system_root_cert()

    def test_explicit_verify_full_overrides_legacy_uri_tls_aliases(self):
        for query in ('sslmode=verify-full&requiressl=0', 'sslmode=verify-full&sslmode='):
            self.capture.seek(0);self.capture.truncate()
            self.config.database_url='postgresql://synthetic@db.example.test/postgres?'+query
            connect=Mock(side_effect=SecretFailure(SENTINEL))
            with self.fake_driver(connect),patch.object(cloud_server.CloudConfig,'from_env',return_value=self.config):
                self.check_unconfigured(cloud_server.application({}))
            self.assertEqual(connect.call_args.kwargs['sslmode'],'verify-full')
            self.check_record('DATABASE_CONNECT')

    def test_database_role_and_schema_failures_close_partial_connections(self):
        for failure, code in [('role', 'DATABASE_ROLE'), ('schema', 'DATABASE_SCHEMA')]:
            self.capture.seek(0); self.capture.truncate(); connection = Connection(failure=failure)
            with self.fake_driver(Mock(return_value=connection)), \
                 patch.object(cloud_server.CloudConfig, 'from_env', return_value=self.config):
                self.check_unconfigured(cloud_server.application({}))
            self.assertEqual(connection.closed, 1); self.check_record(code)

    def test_restricted_role_and_schema_validation_are_unchanged(self):
        for connection, code in [(Connection(role={'rolsuper':True,'rolbypassrls':False,'member':True}), StartupCode.DATABASE_ROLE),
                                  (Connection(version=2), StartupCode.DATABASE_SCHEMA)]:
            startup = StartupDiagnostics()
            with self.assertRaises(Fault): PostgresLedger(SENTINEL, connection=connection, startup=startup)
            self.assertIs(startup.code, code); self.assertEqual(connection.closed, 1)

    def application_patches(self, stage=None, provider=None):
        from contextlib import ExitStack
        stack = ExitStack(); self.addCleanup(stack.close)
        store = Mock(); temporary = Mock()
        stores = SimpleNamespace(persistent=store, temporary=temporary)
        self.config.provider = provider
        stack.enter_context(patch.object(cloud_server.CloudConfig, 'from_env', return_value=self.config))
        stack.enter_context(patch.object(cloud_server, 'PostgresLedger', return_value=store))
        for name, result in [('CloudStores', stores), ('CloudAuth', Mock()), ('RuntimeBridge', Mock()),
                             ('Lifecycle', Mock()), ('CloudBudget', Mock()), ('DeepSeekAdapter', Mock()), ('LiveChat', Mock())]:
            mocked = Mock(return_value=result)
            if stage == name: mocked.side_effect = SecretFailure(SENTINEL)
            stack.enter_context(patch.object(cloud_server, name, mocked))
        return store, temporary, stack

    def test_every_application_phase_is_fail_closed_with_partial_cleanup(self):
        for stage, code in [('CloudStores','TEMPORARY_STORE'), ('CloudAuth','OWNER_AUTH'),
                            ('RuntimeBridge','RUNTIME_BRIDGE'), ('Lifecycle','LIFECYCLE'),
                            ('CloudBudget','PROVIDER_BUDGET'), ('DeepSeekAdapter','PROVIDER_ADAPTER'),
                            ('LiveChat','PROVIDER_ADAPTER')]:
            with self.subTest(stage=stage):
                self.capture.seek(0); self.capture.truncate()
                provider = SimpleNamespace(base_url=SENTINEL, model=SENTINEL, api_key=SENTINEL)
                store, temporary, stack = self.application_patches(stage, provider=provider)
                self.check_unconfigured(cloud_server.application({}))
                store.close.assert_called_once()
                self.assertEqual(temporary.close.call_count, 0 if stage == 'CloudStores' else 1)
                self.check_record(code)
                stack.close()

    def test_lifecycle_recovery_and_cleanup_failure_do_not_escape(self):
        store, temporary, _ = self.application_patches()
        cloud_server.Lifecycle.return_value.recover.side_effect = SecretFailure(SENTINEL)
        store.close.side_effect = SecretFailure(SENTINEL)
        temporary.close.side_effect = SecretFailure(SENTINEL)
        self.check_unconfigured(cloud_server.application({}))
        store.close.assert_called_once(); temporary.close.assert_called_once(); self.check_record('LIFECYCLE')

    def test_no_grant_never_constructs_provider_or_budget(self):
        store, temporary, _ = self.application_patches()
        app = cloud_server.application({})
        self.assertEqual(app.configuration, {'configured':True,'provider_enabled':False})
        cloud_server.CloudBudget.assert_not_called(); cloud_server.DeepSeekAdapter.assert_not_called()
        cloud_server.LiveChat.assert_not_called(); self.assertEqual(self.capture.getvalue(), '')
        app.close(); store.close.assert_called_once(); temporary.close.assert_called_once()

    def test_unknown_code_and_broken_log_sink_never_leak_or_escape(self):
        startup = StartupDiagnostics(); startup.mark(SENTINEL); startup.report()
        self.check_record('UNKNOWN')
        class BrokenStream:
            def write(self, message): raise SecretFailure(SENTINEL)
        with patch('sys.stderr', BrokenStream()), \
             patch.object(cloud_server.CloudConfig, 'from_env', side_effect=SecretFailure(SENTINEL)):
            self.check_unconfigured(cloud_server.application({}))

    def test_concurrent_startups_keep_independent_categories(self):
        barrier = threading.Barrier(2); results = []
        def run(code):
            startup = StartupDiagnostics(); startup.mark(code); barrier.wait(timeout=2)
            results.append(startup.code)
        threads = [threading.Thread(target=run, args=(code,)) for code in (StartupCode.CONFIG, StartupCode.RUNTIME_BRIDGE)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=3)
        self.assertCountEqual(results, [StartupCode.CONFIG, StartupCode.RUNTIME_BRIDGE])
