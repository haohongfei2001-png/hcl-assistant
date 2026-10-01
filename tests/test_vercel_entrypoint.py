"""Provider-free contract tests for the exported production HTTP handler."""
import io
import threading
from http.server import BaseHTTPRequestHandler
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from api import index
from apps.api.cloud_server import Unconfigured


class Socket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()

    def makefile(self, *args):
        return self.input

    def sendall(self, data):
        self.output.write(data)


class EntrypointTests(unittest.TestCase):
    def test_only_http_handler_is_exported_for_vercel_discovery(self):
        self.assertFalse(hasattr(index, 'application'))
        self.assertFalse(hasattr(index, 'app'))
        self.assertTrue(issubclass(index.handler, BaseHTTPRequestHandler))

    def test_same_instance_preserves_host_wrapper_and_closes_each_request(self):
        calls = []
        class App(Unconfigured):
            def close(self): calls.append('closed')
        class RuntimeWrapper(BaseHTTPRequestHandler):
            def handle_one_request(self):
                calls.append('host-start')
                super().handle_one_request()
                calls.append('host-end')
            def log_message(self, *args):
                raise AssertionError('Host logger must not receive request paths')
        class Wrapped(RuntimeWrapper, index.handler):
            pass
        for request, code in [
            (b'GET /v1/development/status?query=PRIVATE_CANARY HTTP/1.0\r\n\r\n', b'200 OK'),
            (b'GET /v1/conversations HTTP/1.0\r\n\r\n', b'503 Service Unavailable'),
            (b'POST /v1/development/login HTTP/1.0\r\nContent-Length: 2\r\n\r\n{}', b'503 Service Unavailable'),
        ]:
            with self.subTest(code=code), patch.object(index, '_create_application', side_effect=App):
                sock = Socket(request)
                Wrapped(sock, ('127.0.0.1', 1), SimpleNamespace(server_port=443))
                self.assertIn(code, sock.output.getvalue())
                self.assertIn(b'Content-Type: application/json; charset=utf-8', sock.output.getvalue())
        self.assertEqual(calls, ['host-start', 'closed', 'host-end'] * 3)

    def test_dispatch_cleanup_even_when_handler_raises(self):
        app = Unconfigured()
        with patch.object(index, '_create_application', return_value=app), patch.object(app, 'close') as close:
            obj = index.handler.__new__(index.handler)
            def fail(): raise RuntimeError('synthetic failure')
            with self.assertRaises(RuntimeError): obj._dispatch(fail)
            close.assert_called_once()
            self.assertIsNone(obj.application)

    def test_malformed_request_never_reaches_host_logger_or_application(self):
        class RuntimeWrapper(BaseHTTPRequestHandler):
            def log_message(self, *args):
                raise AssertionError('Malformed request leaked to host logger')
        class Wrapped(RuntimeWrapper, index.handler):
            pass
        sock = Socket(b'GET /v1/development/status?canary=PRIVATE_QUERY_CANARY EXTRA HTTP/1.1\r\n\r\n')
        with patch.object(index, '_create_application', side_effect=AssertionError('No app for malformed request')):
            Wrapped(sock, ('127.0.0.1', 1), SimpleNamespace(server_port=443))
        self.assertIn(b'400 Bad request syntax', sock.output.getvalue())

    def test_concurrent_instances_keep_separate_applications(self):
        barrier = threading.Barrier(2)
        seen, closed, errors = [], [], []
        class App(Unconfigured):
            def close(self): closed.append(self)
        def run():
            try:
                obj = index.handler.__new__(index.handler)
                def method():
                    own = obj.application
                    barrier.wait(timeout=3)
                    self.assertIs(obj.application, own)
                    seen.append(own)
                obj._dispatch(method)
            except BaseException as error: errors.append(error)
        with patch.object(index, '_create_application', side_effect=App):
            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=5)
        self.assertEqual(errors, [])
        self.assertEqual(len({id(app) for app in seen}), 2)
        self.assertEqual(set(seen), set(closed))

    def test_event_stream_writes_before_application_is_closed(self):
        writes, closed = [], []
        class Controller:
            count = 0
            def read(self, *args): return {'pending': self.count < 2}
            def events(self, *args):
                self.count += 1
                return [{'seq': self.count, 'type': 'synthetic.delta'}]
        controller = Controller()
        class App(Unconfigured):
            real_chat = False
            stores = SimpleNamespace(for_run=lambda *args: None)
            def controller(self, store): return controller
            def close(self): closed.append(True)
        class StreamingSocket(Socket):
            def sendall(self, data):
                self.assert_open()
                writes.append(data)
                super().sendall(data)
            def assert_open(self):
                if closed: raise AssertionError('Application closed before response write')
        sock = StreamingSocket(b'GET /v1/runs/synthetic/events HTTP/1.0\r\n\r\n')
        with patch.object(index, '_create_application', side_effect=App):
            index.handler(sock, ('127.0.0.1', 1), SimpleNamespace(server_port=443))
        self.assertEqual(len([part for part in writes if part.startswith(b'id: ')]), 2)
        self.assertIn(b'Content-Type: text/event-stream', sock.output.getvalue())
        self.assertEqual(closed, [True])
