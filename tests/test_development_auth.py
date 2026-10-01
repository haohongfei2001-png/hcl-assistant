import unittest
from types import SimpleNamespace
from apps.api.development_auth import DevelopmentAuth
from packages.store.ledger import Fault

class AuthTests(unittest.TestCase):
    def setUp(self):self.auth=DevelopmentAuth('synthetic-test-token-only-123456')
    def request(self,**headers):return SimpleNamespace(headers={'Host':'127.0.0.1:8765','Origin':'http://127.0.0.1:5173','X-HCLA-Request':'1',**headers},server=SimpleNamespace(server_port=8765),client_address=('127.0.0.1',100))
    def test_auth_is_not_synthetic_identity(self):
        with self.assertRaises(Fault):self.auth.require(None)
        session=self.auth.login('synthetic-test-token-only-123456');self.assertEqual(self.auth.require('hcla_development='+session),'synthetic-demo-a')
    def test_host_origin_cross_site_and_post_header(self):
        self.auth.boundary(self.request(),True)
        for headers in [{'Host':'evil.example'},{'Origin':'https://evil.example'},{'Sec-Fetch-Site':'cross-site'},{'X-HCLA-Request':''}]:
            with self.assertRaises(Fault):self.auth.boundary(self.request(**headers),True)
    def test_login_failure_rate_limit_and_no_secret_error(self):
        for _ in range(5):
            with self.assertRaisesRegex(Fault,'Development access denied'):self.auth.login('bad')
        with self.assertRaisesRegex(Fault,'Too many'):self.auth.login('synthetic-test-token-only-123456')
    def test_new_process_does_not_inherit_sessions(self):
        session=self.auth.login('synthetic-test-token-only-123456')
        with self.assertRaises(Fault):DevelopmentAuth('synthetic-test-token-only-123456').require('hcla_development='+session)
