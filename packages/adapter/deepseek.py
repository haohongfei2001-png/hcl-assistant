"""Development-only DeepSeek HTTPS/SSE transport; policy and pricing belong to callers.

No credentials are loaded here. No retry, fallback, tools, raw-response retention,
reasoning replay, or provider exception messages are exposed. ``on_delta`` receives
provisional answer text only; a caller must check the final outcome before using it.

Tests inject ``transport_factory(endpoint, connect_timeout)``. A transport has
``post(body: bytes, headers: dict) -> (status: int, headers: dict)``, ``read(size)``
returning bytes, idempotent/nonblocking ``close()``, and ``sent``: False before any
send, None when transmission is ambiguous, True once the request was sent. A new
transport is made for every call. Production uses only the official HTTPS origin.
"""
from __future__ import annotations

import codecs
from dataclasses import dataclass, field
import http.client
import json
import math
import queue
import re
import socket
import threading
import time
from typing import Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}\Z")
_USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens",
                 "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
_FINISH_REASONS = {"stop", "length", "content_filter", "tool_calls",
                   "insufficient_system_resource", "aborted"}
_MAX_EVENT_BYTES = 1024 * 1024
_WORKER_STOP_TIMEOUT = 0.05


@dataclass(frozen=True)
class DeepSeekResult:
    outcome: str
    content: str
    requested_model: str
    actual_model: str | None = None
    request_id: str | None = None
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    usage_consistent: bool = False
    cost: None = None
    send_state: str = "not_sent"
    error_code: str | None = None
    http_status: int | None = None
    transport_stopped: bool = False
    stream_counts: dict[str, int] = field(default_factory=dict)


class _ProtocolError(Exception):
    """A fixed public error code only, never provider content."""


def _endpoint(base_url: str, injected: bool) -> str:
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("invalid_base_url") from None
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query
            or parsed.fragment or "\\" in base_url or any(c.isspace() for c in base_url)):
        raise ValueError("invalid_base_url")
    if not injected and (parsed.scheme != "https" or parsed.hostname != "api.deepseek.com"
                         or port not in (None, 443)):
        raise ValueError("official_https_endpoint_required")
    if injected and parsed.scheme not in ("http", "https"):
        raise ValueError("invalid_base_url")
    # Never urljoin('/chat/completions'): that would discard an explicit /v1.
    path = parsed.path.rstrip("/")
    if "%" in path or "//" in path or any(p in (".", "..") for p in path.split("/")):
        raise ValueError("invalid_base_url")
    if path.endswith("/chat/completions"):
        endpoint = path
    else:
        endpoint = path + "/chat/completions"
    return urlunsplit((parsed.scheme, parsed.netloc, endpoint, "", ""))


class _HTTPSStream:
    """One request; no redirects, environment proxy, or automatic reconnect."""
    def __init__(self, endpoint: str, connect_timeout: float):
        parsed = urlsplit(endpoint)
        self._path = parsed.path
        self._connection = http.client.HTTPSConnection(
            parsed.hostname, parsed.port or 443, timeout=connect_timeout)
        self._connection.auto_open = 0
        self._response = None
        self._socket = None
        self._closed = threading.Event()
        self.sent: bool | None = False

    def post(self, body: bytes, headers: dict) -> tuple[int, dict]:
        if self._closed.is_set():
            raise OSError("transport_closed")
        self._connection.connect()
        self._socket = self._connection.sock
        if self._closed.is_set():
            self.close()
            raise OSError("transport_closed")
        # A write failure can occur after a partial send. It is never safe to retry.
        self.sent = None
        self._connection.request("POST", self._path, body=body, headers=headers)
        self.sent = True
        # The caller's watchdog supplies the absolute deadline for headers/reads.
        if self._connection.sock is not None:
            self._connection.sock.settimeout(None)
        self._response = self._connection.getresponse()
        return self._response.status, {
            "x-request-id": self._response.getheader("x-request-id"),
            "content-type": self._response.getheader("content-type"),
        }

    def read(self, size: int) -> bytes:
        return self._response.read1(size)

    def close(self) -> None:
        self._closed.set()
        # shutdown interrupts a blocked read; closing only HTTPResponse may block.
        sock = self._socket or self._connection.sock
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._connection.close()


class _SSE:
    """Incremental UTF-8 and all SSE line endings, with bounded event memory."""
    def __init__(self):
        self._decoder = codecs.getincrementaldecoder("utf-8-sig")("strict")
        self._buffer = ""
        self._data: list[str] = []
        self._event_bytes = 0
        self._skip_lf = False

    def feed(self, raw: bytes):
        self._buffer += self._decoder.decode(raw)
        if self._skip_lf and self._buffer:
            if self._buffer.startswith("\n"):
                self._buffer = self._buffer[1:]
            self._skip_lf = False
        if len(self._buffer.encode("utf-8")) > _MAX_EVENT_BYTES:
            raise _ProtocolError("event_too_large")
        while True:
            match = re.search(r"[\r\n]", self._buffer)
            if match is None:
                return
            index = match.start()
            self._skip_lf = self._buffer[index] == "\r" and index == len(self._buffer) - 1
            width = 2 if self._buffer[index:index + 2] == "\r\n" else 1
            line, self._buffer = self._buffer[:index], self._buffer[index + width:]
            if not line:
                data = "\n".join(self._data)
                self._data.clear()
                self._event_bytes = 0
                if data.strip():
                    yield data
            elif line.startswith("data:"):
                value = line[5:]
                if value.startswith(" "):
                    value = value[1:]
                self._event_bytes += len(value.encode("utf-8")) + 6
                if self._event_bytes > _MAX_EVENT_BYTES:
                    raise _ProtocolError("event_too_large")
                self._data.append(value)
            # All other fields (including comments) are ignored immediately.

    def finish(self):
        # Validate truncated UTF-8; don't dispatch an unterminated SSE event.
        self._decoder.decode(b"", final=True)


def _usage(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result = {name: value[name] for name in _USAGE_FIELDS
              if type(value.get(name)) is int and value[name] >= 0}
    for container, key, name in (
            ("prompt_tokens_details", "cached_tokens", "cached_tokens"),
            ("completion_tokens_details", "reasoning_tokens", "reasoning_tokens")):
        details = value.get(container)
        if isinstance(details, dict) and type(details.get(key)) is int and details[key] >= 0:
            result[name] = details[key]
    return result


def _consistent_usage(value):
    """Strict numeric accounting evidence, separate from answer validity."""
    if not isinstance(value,dict):return False
    required=('prompt_tokens','completion_tokens','total_tokens')
    if not all(type(value.get(k)) is int and value[k]>0 for k in required):return False
    if value['total_tokens']!=value['prompt_tokens']+value['completion_tokens']:return False
    if any(name in value and (type(value[name]) is not int or value[name]<0) for name in _USAGE_FIELDS):return False
    for container,key,ceiling in (('prompt_tokens_details','cached_tokens','prompt_tokens'),
                                  ('completion_tokens_details','reasoning_tokens','completion_tokens')):
        details=value.get(container)
        if details is not None:
            if not isinstance(details,dict):return False
            if key in details and (type(details[key]) is not int or not 0<=details[key]<=value[ceiling]):return False
    return True


class DeepSeekAdapter:
    def __init__(self, *, base_url: str, model: str, api_key: str,
                 connect_timeout: float = 10.0, wall_timeout: float = 120.0,
                 max_output_bytes: int = 262144, transport_factory: Callable | None = None,
                 thinking_enabled: bool = True, reasoning_effort: str = "high",
                 request_deadline: float | None = None):
        self.endpoint = _endpoint(base_url, transport_factory is not None)
        if not isinstance(model, str) or _TOKEN.fullmatch(model) is None:
            raise ValueError("explicit_model_required")
        if not isinstance(api_key, str) or not api_key or any(c.isspace() for c in api_key):
            raise ValueError("server_api_key_required")
        for value in (connect_timeout, wall_timeout):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("positive_finite_deadline_required")
        if request_deadline is not None and (isinstance(request_deadline, bool) or not isinstance(request_deadline, (int, float)) or not math.isfinite(request_deadline)):
            raise ValueError("finite_request_deadline_required")
        self.request_deadline = request_deadline
        if type(max_output_bytes) is not int or max_output_bytes < 1:
            raise ValueError("positive_output_limit_required")
        if type(thinking_enabled) is not bool:
            raise ValueError("boolean_thinking_mode_required")
        if reasoning_effort not in ("low", "high", "max"):
            raise ValueError("unsupported_reasoning_effort")
        self.thinking_enabled = thinking_enabled
        self.reasoning_effort = reasoning_effort
        self.model = model
        self._api_key = api_key
        self.connect_timeout = float(connect_timeout)
        self.wall_timeout = float(wall_timeout)
        self.max_output_bytes = max_output_bytes
        self._transport_factory = transport_factory or _HTTPSStream

    def generate(self, messages: Sequence[Mapping[str, str]], *, max_tokens: int,
                 cancel_event: threading.Event | None = None,
                 on_delta: Callable[[str], None] | None = None) -> DeepSeekResult:
        """Send one bounded request. Callbacks run on the caller, never IO threads.

        Callback code must be nonblocking; callback exceptions are sanitized and
        terminate this request. Stop/delete callers must also gate their own stores.
        Missing usage is unknown (an empty dict), not zero. Cost is always unknown.
        A false transport_stopped means worker termination is unconfirmed: callers
        must retain concurrency/budget reservations and an unknown attempt until
        independently reconciled. close() alone never proves IO has stopped.
        """
        cancel = cancel_event if cancel_event is not None else threading.Event()
        content: list[str] = []
        actual_model = request_id = finish_reason = None
        counts = {"chunks": 0, "reasoning_chunks": 0, "answer_chunks": 0}
        usage: dict[str, int] = {}
        complete_usage = None
        usage_invalid = False
        http_status = None
        transport = None
        stop = threading.Event()
        worker_done = threading.Event()
        worker_thread: threading.Thread | None = None
        worker_started = False

        def send_state():
            if transport is None:
                return "not_sent"
            sent = getattr(transport, "sent", None)
            return "sent" if sent is True else "not_sent" if sent is False else "unknown"

        def result(outcome, error=None, *, discard=False):
            # Close before reading send_state: a cancellation/deadline must not
            # report not_sent while a concurrent connect is about to write.
            stop.set()
            if transport is not None:
                try:
                    transport.close()
                except Exception:
                    pass
            transport_stopped = not worker_started
            if worker_started:
                # Bounded join: a stubborn transport may ignore close(). Never
                # claim its slot can be released merely because we requested stop.
                worker_thread.join(timeout=_WORKER_STOP_TIMEOUT)
                transport_stopped = worker_done.is_set() and not worker_thread.is_alive()
            state = send_state()
            if not transport_stopped and state != "sent":
                state = "unknown"
            if outcome == "FAILED" and error in ("connect_timeout", "wall_timeout", "transport_error", "timeout") and state != "not_sent":
                outcome = "UNKNOWN"
            return DeepSeekResult(outcome=outcome, content="" if discard else "".join(content),
                                  requested_model=self.model, actual_model=actual_model,
                                  request_id=request_id, finish_reason=finish_reason,
                                  usage=dict(usage), send_state=state,
                                  usage_consistent=complete_usage is not None and not usage_invalid,
                                  error_code=error, http_status=http_status,
                                  transport_stopped=transport_stopped, stream_counts=dict(counts))

        if cancel.is_set():
            return result("CANCELLED", "cancelled")
        if (type(max_tokens) is not int or max_tokens <= 0 or
                not isinstance(messages, (list, tuple)) or not messages):
            return result("FAILED", "invalid_request")
        clean_messages = []
        for message in messages:
            if (not isinstance(message, Mapping) or set(message) != {"role", "content"}
                    or message["role"] not in ("system", "user", "assistant")
                    or not isinstance(message["content"], str)):
                return result("FAILED", "unsupported_message")
            clean_messages.append({"role": message["role"], "content": message["content"]})
        try:
            body = json.dumps({"model": self.model, "messages": clean_messages,
                               "stream": True, "stream_options": {"include_usage": True},
                               "max_tokens": max_tokens,
                               "thinking": {"type": "enabled" if self.thinking_enabled else "disabled"},
                               "reasoning_effort": self.reasoning_effort}, ensure_ascii=False).encode("utf-8")
        except (ValueError, UnicodeError):
            return result("FAILED", "invalid_request")
        clean_messages.clear()
        started = time.monotonic()
        deadline = min(started + self.wall_timeout, self.request_deadline) if self.request_deadline is not None else started + self.wall_timeout
        if started >= deadline:
            return result("FAILED", "wall_timeout")
        connect_deadline = started + self.connect_timeout
        events: queue.Queue = queue.Queue(maxsize=8)

        def put(kind, value):
            while not stop.is_set():
                try:
                    events.put((kind, value), timeout=0.02)
                    return
                except queue.Full:
                    continue

        def worker():
            try:
                if stop.is_set() or cancel.is_set() or time.monotonic() >= deadline:
                    return
                status, headers = transport.post(body, {
                    "Authorization": "Bearer " + self._api_key,
                    "Content-Type": "application/json", "Accept": "text/event-stream"})
                put("headers", (status, headers))
                if status != 200:
                    return  # Do not read or retain error response bodies.
                while not stop.is_set():
                    raw = transport.read(8192)
                    if stop.is_set():
                        return
                    if not raw:
                        put("eof", None)
                        return
                    put("bytes", raw)
            except Exception as error:
                # No exception text, repr, traceback, response or request retained.
                put("error", "timeout" if isinstance(error, TimeoutError) else "transport_error")
            finally:
                worker_done.set()

        def metadata(value):
            return value if (isinstance(value, str) and _TOKEN.fullmatch(value)
                             and self._api_key not in value) else None

        parser = _SSE()
        output_bytes = 0
        terminal = False
        pending_text = ""

        def emit(text):
            if not text:
                return
            if cancel.is_set():
                raise _ProtocolError("cancelled")
            if time.monotonic() >= deadline:
                raise _ProtocolError("wall_timeout")
            content.append(text)
            if on_delta is not None:
                try:
                    on_delta(text)
                except Exception:
                    raise _ProtocolError("callback_error") from None
        try:
            try:
                transport = self._transport_factory(self.endpoint, self.connect_timeout)
            except Exception:
                return result("FAILED", "transport_setup_failed")
            worker_thread = threading.Thread(target=worker, daemon=True, name="deepseek-stream-io")
            try:
                worker_thread.start()
                worker_started = True
            except RuntimeError:
                return result("FAILED", "transport_setup_failed")
            while not terminal:
                if cancel.is_set():
                    return result("CANCELLED", "cancelled")
                if send_state() == "not_sent" and time.monotonic() >= connect_deadline:
                    return result("FAILED", "connect_timeout")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return result("FAILED" if send_state() == "not_sent" else "UNKNOWN", "wall_timeout")
                try:
                    kind, value = events.get(timeout=min(0.02, remaining))
                except queue.Empty:
                    continue
                if cancel.is_set():
                    return result("CANCELLED", "cancelled")
                if time.monotonic() >= deadline:
                    return result("FAILED" if send_state() == "not_sent" else "UNKNOWN", "wall_timeout")
                if kind == "headers":
                    status, headers = value
                    http_status = status if type(status) is int and 100 <= status <= 599 else None
                    if isinstance(headers, Mapping):
                        request_id = metadata(headers.get("x-request-id"))
                    if http_status != 200:
                        return result("FAILED", "http_error")
                    continue
                if kind == "error":
                    return result("FAILED" if send_state() == "not_sent" else "UNKNOWN", value)
                if kind == "eof":
                    parser.finish()
                    return result("UNKNOWN", "early_eof")
                if kind != "bytes" or not isinstance(value, bytes):
                    raise _ProtocolError("invalid_stream")
                for data in parser.feed(value):
                    if cancel.is_set():
                        return result("CANCELLED", "cancelled")
                    if time.monotonic() >= deadline:
                        return result("UNKNOWN", "wall_timeout")
                    if data.strip() == "[DONE]":
                        terminal = True
                        break
                    try:
                        chunk = json.loads(data)
                    except (ValueError, RecursionError):
                        raise _ProtocolError("invalid_json") from None
                    del data
                    if chunk is None:
                        continue
                    if not isinstance(chunk, dict):
                        raise _ProtocolError("invalid_chunk")
                    counts["chunks"] += 1
                    # Extract only allowlisted public metadata and numeric usage.
                    raw_usage=chunk.pop("usage",None)
                    if raw_usage is not None:
                        parsed_usage=_usage(raw_usage)
                        consistent=_consistent_usage(raw_usage)
                        if not consistent or complete_usage is not None and parsed_usage!=complete_usage:usage_invalid=True
                        if consistent:complete_usage=parsed_usage
                        # Replace rather than preserve stale numbers when a later
                        # usage record is incomplete/malformed. No raw values kept.
                        usage=parsed_usage
                    del raw_usage
                    model = chunk.pop("model", None)
                    if model is not None:
                        model = metadata(model)
                        if model is None:
                            raise _ProtocolError("invalid_model")
                        actual_model = model
                        if actual_model != self.model:
                            return result("FAILED", "model_mismatch", discard=True)
                    request_id = metadata(chunk.pop("id", None)) or request_id
                    choices = chunk.pop("choices", None)
                    chunk.clear()
                    if choices is None:
                        continue
                    if not isinstance(choices, list) or len(choices) > 1:
                        raise _ProtocolError("invalid_choices")
                    if not choices:
                        continue
                    choice = choices[0]
                    if not isinstance(choice, dict) or choice.get("index", 0) != 0:
                        raise _ProtocolError("invalid_choice")
                    delta = choice.pop("delta", None)
                    reason = choice.pop("finish_reason", None)
                    choice.clear()
                    if delta is None:
                        delta = {}
                    if not isinstance(delta, dict):
                        raise _ProtocolError("invalid_delta")
                    # Reasoning is discarded before anything can reach a callback.
                    if isinstance(delta.get("reasoning_content"), str) and delta["reasoning_content"]:
                        counts["reasoning_chunks"] += 1
                    delta.pop("reasoning_content", None)
                    text = delta.pop("content", None)
                    tools = bool(delta.pop("tool_calls", None) or delta.pop("function_call", None))
                    delta.clear()
                    if tools:
                        raise _ProtocolError("unexpected_tool_call")
                    previously_finished = finish_reason is not None
                    if reason is not None:
                        if reason not in _FINISH_REASONS or finish_reason not in (None, reason):
                            raise _ProtocolError("invalid_finish_reason")
                        finish_reason = reason
                    if text is not None and not isinstance(text, str):
                        raise _ProtocolError("invalid_content")
                    if text:
                        counts["answer_chunks"] += 1
                        if previously_finished:
                            raise _ProtocolError("content_after_finish")
                        if actual_model is None:
                            raise _ProtocolError("missing_model")
                        size = len(text.encode("utf-8"))
                        if output_bytes + size > self.max_output_bytes:
                            return result("PARTIAL", "output_limit")
                        output_bytes += size
                        # Guard even an unexpected credential echo across deltas.
                        pending_text += text
                        if self._api_key in pending_text:
                            return result("FAILED", "credential_echo", discard=True)
                        keep = 0
                        for length in range(min(len(self._api_key) - 1, len(pending_text)), 0, -1):
                            if pending_text.endswith(self._api_key[:length]):
                                keep = length
                                break
                        safe_text = pending_text[:-keep] if keep else pending_text
                        pending_text = pending_text[-keep:] if keep else ""
                        emit(safe_text)
            if cancel.is_set():
                return result("CANCELLED", "cancelled")
            emit(pending_text)
            if finish_reason is None:
                return result("UNKNOWN", "missing_finish_reason")
            if actual_model is None:
                return result("FAILED", "missing_model")
            if not "".join(content).strip():
                return result("FAILED", "empty_answer")
            if finish_reason == "length":
                return result("PARTIAL", "length")
            if finish_reason != "stop":
                return result("FAILED", "finish_" + finish_reason)
            return result("SUCCEEDED")
        except _ProtocolError as error:
            code = str(error)
            if code == "cancelled":
                return result("CANCELLED", code)
            if code == "wall_timeout":
                return result("UNKNOWN", code)
            return result("FAILED", code)
        except (UnicodeError, ValueError, TypeError):
            return result("FAILED", "invalid_stream")
        finally:
            stop.set()
            if transport is not None:
                try:
                    transport.close()
                except Exception:
                    pass
            while True:
                try:
                    events.get_nowait()
                except queue.Empty:
                    break
