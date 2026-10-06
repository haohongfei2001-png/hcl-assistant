"""Exercise real fixture bytes at explicit consumer-side deadline boundaries."""
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from packages.adapter import deepseek
from packages.adapter.deepseek import DeepSeekAdapter
from tests.support.cloud_transport import CloudFakeTransport


class DiagnosticFixtureTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.create_connection', side_effect=AssertionError('network forbidden'))
        guard.start()
        self.addCleanup(guard.stop)

    def generate_at_deadline(self, *, after_metadata):
        clock = [100.0]

        class DeadlineQueue(queue.Queue):
            """Real FIFO; only the adapter clock advances at the chosen read."""
            event_returned = False
            tail = b''

            def get(self, *args, **kwargs):
                # The preceding get returned the final bytes of the first SSE
                # event. The caller has now parsed it before asking for more.
                if after_metadata and self.event_returned:
                    clock[0] = 101.0
                item = super().get(*args, **kwargs)
                kind, value, _ = item
                if kind == 'bytes':
                    if not after_metadata:
                        # Headers were consumed first, but no model event has
                        # been parsed when the caller checks its deadline.
                        clock[0] = 101.0
                    else:
                        self.event_returned |= b'\n\n' in self.tail + value
                        self.tail = value[-1:]
                return item

        # Keep the exact fragmented browser transport and production parser.
        # Do not advance time in its worker: enqueueing is not consumption.
        adapter = DeepSeekAdapter(
            base_url='https://api.deepseek.com', model='deepseek-v4-pro',
            api_key='offline-fixture', transport_factory=CloudFakeTransport,
            wall_timeout=.3)
        fifo = SimpleNamespace(Queue=DeadlineQueue, Empty=queue.Empty, Full=queue.Full)
        with patch.object(deepseek, 'queue', fifo), patch.object(
                deepseek, 'time', SimpleNamespace(monotonic=lambda: clock[0])):
            return adapter.generate(
                [{'role': 'user', 'content': 'ORIGINAL_THINKING_TIMEOUT_FIXTURE'}],
                max_tokens=512)

    def assert_unknown_without_private_output(self, result):
        self.assertEqual(result.outcome, 'UNKNOWN')
        self.assertEqual(result.error_code, 'wall_timeout')
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.send_state, 'sent')
        self.assertTrue(result.transport_stopped)
        self.assertEqual(result.content, '')
        self.assertEqual(result.usage, {})
        self.assertFalse(result.usage_consistent)
        self.assertIsNone(result.cost)
        self.assertNotIn('OFFLINE_HIDDEN_REASONING_MUST_NOT_RENDER', repr(result))

    def test_thinking_only_fixture_returns_sanitized_unknown_without_body_or_usage(self):
        result = self.generate_at_deadline(after_metadata=True)
        self.assert_unknown_without_private_output(result)
        self.assertEqual(result.actual_model, 'deepseek-v4-pro')
        self.assertEqual(result.stream_counts,
                         {'chunks': 1, 'reasoning_chunks': 1, 'answer_chunks': 0})
        self.assertIn('first_reasoning_ms', result.stream_timing_ms)

    def test_timeout_before_metadata_keeps_actual_model_unknown(self):
        result = self.generate_at_deadline(after_metadata=False)
        self.assert_unknown_without_private_output(result)
        self.assertIsNone(result.actual_model)
        self.assertEqual(result.stream_counts,
                         {'chunks': 0, 'reasoning_chunks': 0, 'answer_chunks': 0})
        self.assertNotIn('first_event_ms', result.stream_timing_ms)
