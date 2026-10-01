"""Original synthetic provider-free tests. No environment credentials or network."""
import dataclasses
import json
import threading
import time
import unittest
from unittest.mock import patch

from packages.adapter.deepseek import DeepSeekAdapter, _HTTPSStream


MODEL = "configured-development-model"
SECRET = "synthetic-private-key-sentinel"
REASONING = "SENTINEL_HIDDEN_REASONING_DO_NOT_RETAIN"
MESSAGES = [{"role": "system", "content": "Synthetic instructions"},
            {"role": "user", "content": "Synthetic question"}]


def event(value, ending="\n"):
    return ("data: " + json.dumps(value, ensure_ascii=False) + ending + ending).encode()


def chunk(text=None, *, reasoning=None, finish=None, model=MODEL, usage=None):
    return {"id": "synthetic-request-1", "model": model,
            "choices": [{"index": 0, "delta": {"content": text,
                        "reasoning_content": reasoning}, "finish_reason": finish}],
            "usage": usage}


DONE = b"data: [DONE]\n\n"
USAGE = {"prompt_tokens": 10, "completion_tokens": 7, "total_tokens": 17,
         "prompt_cache_hit_tokens": 4, "prompt_cache_miss_tokens": 6,
         "prompt_tokens_details": {"cached_tokens": 4},
         "completion_tokens_details": {"reasoning_tokens": 5}}


class FakeTransport:
    def __init__(self, chunks=(), *, status=200, error=None, send_state=False,
                 block_post=False, block_read=False, keepalive=False):
        self.chunks = list(chunks)
        self.status = status
        self.error = error
        self.sent = send_state
        self.block_post = block_post
        self.block_read = block_read
        self.keepalive = keepalive
        self.closed = threading.Event()
        self.read_started = threading.Event()
        self.post_calls = self.read_calls = self.close_calls = 0
        self.body = self.headers = None

    def post(self, body, headers):
        self.post_calls += 1
        self.body, self.headers = body, headers
        if self.block_post:
            self.closed.wait(3)
            raise TimeoutError(SECRET + REASONING)
        if self.error:
            raise self.error
        self.sent = True
        return self.status, {"x-request-id": "synthetic-header-request", "content-type": "text/event-stream"}

    def read(self, size):
        self.read_started.set()
        self.read_calls += 1
        if self.block_read:
            self.closed.wait(3)
            # A deliberately uncooperative late event must never be emitted.
            return event(chunk("late output"))
        if self.keepalive:
            time.sleep(0.002)
            return b": heartbeat\n\n"
        if self.chunks:
            item = self.chunks.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return b""

    def close(self):
        self.close_calls += 1
        self.closed.set()


class DeepSeekAdapterTests(unittest.TestCase):
    def setUp(self):
        # An accidental live transport in any test fails before opening a socket.
        self.network_guard = patch("socket.create_connection", side_effect=AssertionError("network forbidden"))
        self.network_guard.start()
        self.addCleanup(self.network_guard.stop)

    def adapter(self, fake, **kwargs):
        def factory(endpoint, timeout):
            fake.endpoint, fake.timeout = endpoint, timeout
            return fake
        return DeepSeekAdapter(base_url=kwargs.pop("base_url", "https://api.deepseek.com/v1/"),
                               model=MODEL, api_key=SECRET, transport_factory=factory, **kwargs)

    def generate(self, fake, *, deltas=None, **kwargs):
        return self.adapter(fake, **kwargs).generate(MESSAGES, max_tokens=64,
                                        on_delta=deltas.append if deltas is not None else None)

    def assert_private(self, result, deltas=()):
        rendered = repr(dataclasses.asdict(result)) + repr(deltas)
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn(REASONING, rendered)
        self.assertNotIn("reasoning_content", rendered)

    def test_fragmented_utf8_sse_and_final_normal_usage(self):
        wire = (b"\xef\xbb\xbf: heartbeat\r\n\r\ndata:\r\n\r\n" + event(None, "\r\n") +
                event(chunk(reasoning=REASONING + SECRET), "\r\n") +
                event(chunk("你好 🌟"), "\r\n") + event(chunk(finish="stop", usage=USAGE), "\r\n") + DONE)
        fake = FakeTransport([bytes([byte]) for byte in wire])
        deltas = []
        result = self.generate(fake, deltas=deltas)
        self.assertEqual(result.outcome, "SUCCEEDED")
        self.assertEqual(result.content, "你好 🌟")
        self.assertEqual("".join(deltas), result.content)
        self.assertEqual(result.usage, {"prompt_tokens": 10, "completion_tokens": 7,
                         "total_tokens": 17, "prompt_cache_hit_tokens": 4,
                         "prompt_cache_miss_tokens": 6, "cached_tokens": 4, "reasoning_tokens": 5})
        self.assertEqual(result.request_id, "synthetic-request-1")
        self.assertEqual(result.actual_model, MODEL)
        self.assertEqual(result.send_state, "sent")
        self.assertIsNone(result.cost)
        self.assert_private(result, deltas)
        self.assertTrue(fake.closed.is_set())

    def test_wire_request_has_only_explicit_supported_fields(self):
        fake = FakeTransport([event(chunk("answer", finish="stop")), DONE])
        adapter = self.adapter(fake)
        result = adapter.generate(MESSAGES, max_tokens=64)
        self.assertEqual(result.outcome, "SUCCEEDED")
        self.assertEqual(json.loads(fake.body), {"model": MODEL, "messages": MESSAGES,
                         "stream": True, "stream_options": {"include_usage": True}, "max_tokens": 64})
        self.assertEqual(fake.headers["Authorization"], "Bearer " + SECRET)
        self.assertNotIn(SECRET, repr(adapter))
        self.assertEqual(fake.endpoint, "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(fake.post_calls, 1)

    def test_usage_only_chunk_supported_and_no_assumed_zeros(self):
        fake = FakeTransport([event(chunk("answer", finish="stop")),
                              event({"choices": [], "usage": USAGE}), DONE])
        result = self.generate(fake)
        self.assertEqual(result.outcome, "SUCCEEDED")
        self.assertEqual(result.usage["reasoning_tokens"], 5)
        no_usage = self.generate(FakeTransport([event(chunk("answer", finish="stop")), DONE]))
        self.assertEqual(no_usage.usage, {})
        self.assertIsNone(no_usage.cost)

    def test_usage_accepts_only_nonnegative_integer_allowlist(self):
        usage = {"prompt_tokens": True, "completion_tokens": -1, "total_tokens": "17",
                 "prompt_cache_hit_tokens": 2.5, "prompt_cache_miss_tokens": 0,
                 "completion_tokens_details": {"reasoning_tokens": 3, "text": REASONING},
                 "extra": SECRET}
        result = self.generate(FakeTransport([event(chunk("answer", finish="stop", usage=usage)), DONE]))
        self.assertEqual(result.usage, {"prompt_cache_miss_tokens": 0, "reasoning_tokens": 3})
        self.assert_private(result)

    def test_length_is_partial_and_retains_usage(self):
        result = self.generate(FakeTransport([event(chunk("unfinished", finish="length", usage=USAGE)), DONE]))
        self.assertEqual((result.outcome, result.finish_reason), ("PARTIAL", "length"))
        self.assertEqual(result.usage["total_tokens"], 17)

    def test_early_eof_and_missing_terminal_or_finish_are_never_success(self):
        for wire, error in [([event(chunk("answer"))], "early_eof"),
                            ([event(chunk("answer", finish="stop"))], "early_eof"),
                            ([event(chunk("answer")), DONE], "missing_finish_reason")]:
            with self.subTest(error=error, wire=wire):
                result = self.generate(FakeTransport(wire))
                self.assertEqual((result.outcome, result.error_code), ("UNKNOWN", error))

    def test_empty_and_reasoning_only_are_failed(self):
        for text in (None, "", "  \n"):
            with self.subTest(text=text):
                result = self.generate(FakeTransport([event(chunk(text, reasoning=REASONING + SECRET,
                                                          finish="stop", usage=USAGE)), DONE]))
                self.assertEqual((result.outcome, result.error_code), ("FAILED", "empty_answer"))
                self.assert_private(result)

    def test_http_errors_sanitized_without_body_read_or_retry(self):
        for status in (401, 402, 422, 429, 500, 503):
            with self.subTest(status=status):
                fake = FakeTransport([SECRET.encode() + REASONING.encode()], status=status)
                result = self.generate(fake)
                self.assertEqual((result.outcome, result.error_code, result.http_status), ("FAILED", "http_error", status))
                self.assertEqual(fake.post_calls, 1)
                self.assertEqual(fake.read_calls, 0)
                self.assert_private(result)

    def test_connection_failure_is_not_sent(self):
        fake = FakeTransport(error=OSError(SECRET + REASONING))
        result = self.generate(fake)
        self.assertEqual((result.outcome, result.send_state), ("FAILED", "not_sent"))
        self.assert_private(result)

    def test_ambiguous_send_is_unknown_no_retry(self):
        fake = FakeTransport(error=OSError(SECRET + REASONING), send_state=None)
        result = self.generate(fake)
        self.assertEqual((result.outcome, result.send_state), ("UNKNOWN", "unknown"))
        self.assertEqual(fake.post_calls, 1)
        self.assert_private(result)

    def test_sent_timeout_unknown(self):
        fake = FakeTransport([event(chunk("part")), TimeoutError(SECRET + REASONING)])
        result = self.generate(fake)
        self.assertEqual((result.outcome, result.send_state, result.error_code), ("UNKNOWN", "sent", "timeout"))
        self.assertEqual(result.content, "part")
        self.assert_private(result)

    def test_connection_deadline_interrupts_blocked_connect(self):
        fake = FakeTransport(block_post=True)
        started = time.monotonic()
        result = self.generate(fake, connect_timeout=0.04, wall_timeout=0.6)
        self.assertLess(time.monotonic() - started, 0.4)
        self.assertEqual((result.outcome, result.error_code, result.send_state), ("FAILED", "connect_timeout", "not_sent"))
        self.assertTrue(fake.closed.is_set())

    def test_wall_deadline_is_absolute_despite_keepalives(self):
        fake = FakeTransport(keepalive=True)
        started = time.monotonic()
        result = self.generate(fake, wall_timeout=0.06)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertEqual((result.outcome, result.error_code), ("UNKNOWN", "wall_timeout"))
        self.assertTrue(fake.closed.is_set())
        self.assertGreater(fake.read_calls, 2)

    def test_wall_deadline_closes_blocked_read_and_suppresses_late_emission(self):
        fake = FakeTransport(block_read=True)
        deltas = []
        result = self.generate(fake, deltas=deltas, wall_timeout=0.04)
        self.assertEqual(result.error_code, "wall_timeout")
        self.assertTrue(fake.closed.is_set())
        time.sleep(0.03)
        self.assertEqual(deltas, [])

    def test_pre_cancel_does_not_create_transport(self):
        cancel = threading.Event()
        cancel.set()
        factory = unittest.mock.Mock(side_effect=AssertionError("must not create"))
        adapter = DeepSeekAdapter(base_url="https://api.deepseek.com", model=MODEL, api_key=SECRET,
                                  transport_factory=factory)
        result = adapter.generate(MESSAGES, max_tokens=1, cancel_event=cancel)
        self.assertEqual((result.outcome, result.send_state), ("CANCELLED", "not_sent"))
        factory.assert_not_called()

    def test_cancel_actively_closes_transport_and_prevents_late_callback(self):
        fake = FakeTransport(block_read=True)
        cancel = threading.Event()
        deltas = []
        def cancel_when_reading():
            fake.read_started.wait(1)
            cancel.set()
        helper = threading.Thread(target=cancel_when_reading)
        helper.start()
        result = self.adapter(fake).generate(MESSAGES, max_tokens=64, cancel_event=cancel, on_delta=deltas.append)
        helper.join(1)
        self.assertEqual(result.outcome, "CANCELLED")
        self.assertTrue(fake.closed.is_set())
        time.sleep(0.03)
        self.assertEqual(deltas, [])

    def test_cancel_in_callback_suppresses_later_deltas_in_same_network_chunk(self):
        fake = FakeTransport([event(chunk("first")) + event(chunk("second", finish="stop")) + DONE])
        cancel, deltas = threading.Event(), []
        def callback(text):
            deltas.append(text)
            cancel.set()
        result = self.adapter(fake).generate(MESSAGES, max_tokens=64, cancel_event=cancel, on_delta=callback)
        self.assertEqual(result.outcome, "CANCELLED")
        self.assertEqual(deltas, ["first"])

    def test_output_limit_counts_utf8_bytes(self):
        fake = FakeTransport([event(chunk("你")), event(chunk("好", finish="stop")), DONE])
        result = self.generate(fake, max_output_bytes=5)
        self.assertEqual((result.outcome, result.content, result.error_code), ("PARTIAL", "你", "output_limit"))
        self.assertTrue(fake.closed.is_set())

    def test_model_mismatch_fails_explicitly_without_fallback(self):
        fake = FakeTransport([event(chunk("wrong model answer", model="unexpected-model", finish="stop", usage=USAGE)), DONE])
        deltas = []
        result = self.generate(fake, deltas=deltas)
        self.assertEqual((result.outcome, result.error_code, result.content), ("FAILED", "model_mismatch", ""))
        self.assertEqual((result.requested_model, result.actual_model), (MODEL, "unexpected-model"))
        self.assertEqual(deltas, [])
        self.assertEqual(fake.post_calls, 1)

    def test_missing_model_does_not_emit_content(self):
        fake = FakeTransport([event(chunk("answer", model=None, finish="stop")), DONE])
        deltas = []
        result = self.generate(fake, deltas=deltas)
        self.assertEqual(result.error_code, "missing_model")
        self.assertEqual(deltas, [])

    def test_key_echo_blocked_even_when_split_across_content_deltas(self):
        fake = FakeTransport([event(chunk("safe " + SECRET[:12])),
                              event(chunk(SECRET[12:], finish="stop")), DONE])
        deltas = []
        result = self.generate(fake, deltas=deltas)
        self.assertEqual(result.error_code, "credential_echo")
        self.assertEqual(deltas, ["safe "])
        self.assert_private(result, deltas)

    def test_key_prefix_in_ordinary_output_is_flushed_at_completion(self):
        result = self.generate(FakeTransport([event(chunk("ordinary synt", finish="stop")), DONE]))
        self.assertEqual((result.outcome, result.content), ("SUCCEEDED", "ordinary synt"))

    def test_callback_errors_sanitized_and_transport_closed(self):
        fake = FakeTransport([event(chunk("answer", finish="stop")), DONE])
        def callback(_):
            raise RuntimeError(SECRET + REASONING)
        result = self.adapter(fake).generate(MESSAGES, max_tokens=1, on_delta=callback)
        self.assertEqual(result.error_code, "callback_error")
        self.assert_private(result)
        self.assertTrue(fake.closed.is_set())

    def test_malformed_json_utf8_and_oversized_event_sanitized(self):
        cases = [b"data: {" + SECRET.encode() + b"\n\n", b"data: \xff\n\n",
                 b"data: " + b"x" * (1024 * 1024 + 1)]
        for wire in cases:
            with self.subTest(size=len(wire)):
                result = self.generate(FakeTransport([wire]))
                self.assertEqual(result.outcome, "FAILED")
                self.assert_private(result)

    def test_unexpected_finish_and_tools_not_success(self):
        for reason in ("content_filter", "tool_calls", "insufficient_system_resource", "aborted"):
            with self.subTest(reason=reason):
                result = self.generate(FakeTransport([event(chunk("answer", finish=reason)), DONE]))
                self.assertEqual((result.outcome, result.error_code), ("FAILED", "finish_" + reason))
        data = chunk("answer", finish="stop")
        data["choices"][0]["delta"]["tool_calls"] = [{"arguments": SECRET + REASONING}]
        result = self.generate(FakeTransport([event(data), DONE]))
        self.assertEqual(result.error_code, "unexpected_tool_call")
        self.assert_private(result)

    def test_content_after_finish_is_rejected(self):
        result = self.generate(FakeTransport([event(chunk("first", finish="stop")), event(chunk("late")), DONE]))
        self.assertEqual((result.outcome, result.error_code), ("FAILED", "content_after_finish"))

    def test_no_developer_tools_or_reasoning_input(self):
        for message in ({"role": "developer", "content": "x"}, {"role": "tool", "content": "x"},
                        {"role": "assistant", "content": "x", "reasoning_content": REASONING}):
            fake = FakeTransport()
            result = self.adapter(fake).generate([message], max_tokens=1)
            self.assertEqual((result.outcome, result.send_state), ("FAILED", "not_sent"))
            self.assertEqual(fake.post_calls, 0)

    def test_invalid_input_limits_and_configuration(self):
        for maximum in (0, -1, True, "20"):
            result = self.adapter(FakeTransport()).generate(MESSAGES, max_tokens=maximum)
            self.assertEqual(result.error_code, "invalid_request")
        for value in (0, -1, float("nan"), float("inf"), True):
            with self.assertRaisesRegex(ValueError, "positive_finite_deadline_required"):
                self.adapter(FakeTransport(), wall_timeout=value)
        for key, value in (("model", ""), ("api_key", "")):
            kwargs = {"base_url": "https://api.deepseek.com", "model": MODEL, "api_key": SECRET}
            kwargs[key] = value
            with self.assertRaises(ValueError):
                DeepSeekAdapter(**kwargs)

    def test_official_https_only_without_injected_transport(self):
        for base in ("http://api.deepseek.com", "https://evil.invalid", "https://api.deepseek.com.evil.invalid",
                     "https://api.deepseek.com:444", "https://user:password@api.deepseek.com", "https://api.deepseek.com?x=1",
                     "https://api.deepseek.com/#x", "https://api.deepseek.com/../evil"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                DeepSeekAdapter(base_url=base, model=MODEL, api_key=SECRET)

    def test_endpoint_path_preserved_and_no_duplicate_suffix(self):
        for base, expected in [("https://api.deepseek.com", "https://api.deepseek.com/chat/completions"),
                               ("https://api.deepseek.com/v1/", "https://api.deepseek.com/v1/chat/completions"),
                               ("https://api.deepseek.com/v1/chat/completions/", "https://api.deepseek.com/v1/chat/completions"),
                               ("http://fake.invalid/v2", "http://fake.invalid/v2/chat/completions")]:
            with self.subTest(base=base):
                adapter = self.adapter(FakeTransport(), base_url=base)
                self.assertEqual(adapter.endpoint, expected)

    def test_cr_only_terminal_at_eof_is_supported(self):
        wire = event(chunk("answer", finish="stop"), "\r") + b"data: [DONE]\r\r"
        result = self.generate(FakeTransport([bytes([byte]) for byte in wire]))
        self.assertEqual(result.outcome, "SUCCEEDED")

    def test_multiline_data_and_comments(self):
        data = json.dumps(chunk("answer", finish="stop"))
        wire = b": ignored\nevent: completion\nid: ignored\n" + (
            "data: " + data[:1] + "\ndata: " + data[1:] + "\n\n").encode() + DONE
        result = self.generate(FakeTransport([wire]))
        self.assertEqual((result.outcome, result.content), ("SUCCEEDED", "answer"))

    def test_actual_https_stream_contract_with_in_memory_connection(self):
        class Socket:
            def __init__(self):
                self.shutdown_called = False
            def settimeout(self, value):
                self.timeout = value
            def shutdown(self, _):
                self.shutdown_called = True
        class Response:
            status = 200
            def getheader(self, key):
                return {"content-type": "text/event-stream", "x-request-id": "test-id"}.get(key)
            def read1(self, size):
                return DONE
        class Connection:
            def __init__(self, host, port, timeout):
                self.target = (host, port, timeout)
                self.sock = None
                self.closed = False
                self.requested = None
            def connect(self):
                self.sock = Socket()
            def request(self, method, path, body, headers):
                self.requested = (method, path, body, headers)
            def getresponse(self):
                return Response()
            def close(self):
                self.closed = True
        with patch("packages.adapter.deepseek.http.client.HTTPSConnection", Connection):
            stream = _HTTPSStream("https://api.deepseek.com/v1/chat/completions", 3)
            status, headers = stream.post(b"{}", {"Authorization": "Bearer " + SECRET})
            self.assertEqual(status, 200)
            self.assertEqual(headers["x-request-id"], "test-id")
            self.assertEqual(stream._connection.target, ("api.deepseek.com", 443, 3))
            self.assertEqual(stream._connection.requested[:2], ("POST", "/v1/chat/completions"))
            self.assertTrue(stream.sent)
            self.assertIsNone(stream._connection.sock.timeout)
            self.assertEqual(stream.read(1024), DONE)
            stream.close()
            self.assertTrue(stream._socket.shutdown_called)
            self.assertTrue(stream._connection.closed)

    def test_https_close_during_connect_never_sends_after_connect_returns(self):
        connecting, release = threading.Event(), threading.Event()
        class Socket:
            def shutdown(self, _):
                pass
        class Connection:
            def __init__(self, *args, **kwargs):
                self.sock = None
                self.requests = 0
            def connect(self):
                connecting.set()
                release.wait(1)
                self.sock = Socket()
            def request(self, *args, **kwargs):
                self.requests += 1
            def close(self):
                pass
        with patch("packages.adapter.deepseek.http.client.HTTPSConnection", Connection):
            stream = _HTTPSStream("https://api.deepseek.com/chat/completions", 3)
            errors = []
            def post():
                try:
                    stream.post(b"{}", {})
                except OSError:
                    errors.append("closed")
            worker = threading.Thread(target=post)
            worker.start()
            self.assertTrue(connecting.wait(1))
            stream.close()
            release.set()
            worker.join(1)
            self.assertEqual(stream._connection.requests, 0)
            self.assertFalse(stream.sent)
            self.assertEqual(errors, ["closed"])

    def test_default_transport_constructed_without_connect_or_secret_repr(self):
        stream = _HTTPSStream("https://api.deepseek.com/v1/chat/completions", 2)
        self.assertFalse(stream.sent)
        self.assertEqual(stream._connection.auto_open, 0)
        stream.close()
        stream.close()


if __name__ == "__main__":
    unittest.main()
