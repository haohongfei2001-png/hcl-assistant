"""The exact browser fixture must exercise the adapter deadline, not fake a receipt."""
import unittest
from packages.adapter.deepseek import DeepSeekAdapter
from tests.support.cloud_transport import CloudFakeTransport

class DiagnosticFixtureTests(unittest.TestCase):
    def test_thinking_only_fixture_returns_sanitized_unknown_without_body_or_usage(self):
        adapter=DeepSeekAdapter(base_url='https://api.deepseek.com',model='deepseek-v4-pro',api_key='offline-fixture',transport_factory=CloudFakeTransport,wall_timeout=.3)
        result=adapter.generate([{'role':'user','content':'ORIGINAL_THINKING_TIMEOUT_FIXTURE'}],max_tokens=512)
        self.assertEqual(result.outcome,'UNKNOWN')
        self.assertEqual(result.error_code,'wall_timeout')
        self.assertEqual(result.actual_model,'deepseek-v4-pro')
        self.assertEqual(result.http_status,200)
        self.assertEqual(result.send_state,'sent')
        self.assertTrue(result.transport_stopped)
        self.assertEqual(result.content,'')
        self.assertEqual(result.usage,{})
        self.assertNotIn('OFFLINE_HIDDEN_REASONING_MUST_NOT_RENDER',repr(result))
