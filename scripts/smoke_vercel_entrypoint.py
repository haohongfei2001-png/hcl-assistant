"""Exercise the shipped handler through the real pinned Vercel streaming runtime.

Run after installing vercel-runtime==0.22.1 (CI-only dependency). The subprocess
gets no inherited app configuration or secrets and can only serve unconfigured
responses. This verifies discovery, readiness, dispatch and lifecycle IPC, not
database setup, authenticated use, or provider execution.
"""
from collections import Counter
import base64
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from api import index
    from http.server import BaseHTTPRequestHandler
    from vercel_runtime.resolver import resolve_app

    # Vercel's AST build detector recognizes imported app/application names
    # before the handler class. Keep the shipped module unambiguous.
    assert not hasattr(index, 'app') and not hasattr(index, 'application')
    name, cls = resolve_app(index, 'api.index', 'handler')
    assert name == 'handler' and issubclass(cls, BaseHTTPRequestHandler)
    assert importlib.metadata.version('vercel-runtime') == '0.22.1'

    with tempfile.TemporaryDirectory(prefix='hcla-vercel-smoke-') as directory:
        ipc_path = str(Path(directory) / 'ipc.sock')
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(ipc_path)
        listener.listen(1)
        listener.settimeout(15)
        env = {
            'PATH': os.defpath,
            'PYTHONPATH': os.pathsep.join(sys.path),
            'PYTHONDONTWRITEBYTECODE': '1',
            'VERCEL_IPC_PATH': ipc_path,
            '__VC_HANDLER_MODULE_NAME': 'api.index',
            '__VC_HANDLER_ENTRYPOINT': 'api/index.py',
            '__VC_HANDLER_ENTRYPOINT_ABS': str(ROOT / 'api/index.py'),
            '__VC_HANDLER_VARIABLE_NAME': 'handler',
            # Synthetic invalid values exercise real startup-log redaction.
            'HCLA_DATABASE_URL': 'PRIVATE_SETUP_CANARY',
            'HCLA_PUBLIC_ORIGIN': 'PRIVATE_SETUP_CANARY',
            'HCLA_OWNER_CONFIG': 'PRIVATE_SETUP_CANARY',
        }
        process = subprocess.Popen(
            [sys.executable, '-c', 'import vercel_runtime.vc_init'],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        connection = None
        messages, pending = [], b''
        decoded_logs = []

        def receive_until(predicate):
            nonlocal pending
            deadline = time.monotonic() + 15
            while not predicate():
                if time.monotonic() >= deadline:
                    raise AssertionError('Vercel lifecycle IPC timed out')
                chunk = connection.recv(65536)
                if not chunk:
                    raise AssertionError('Vercel runtime closed before expected IPC')
                pending += chunk
                while b'\0' in pending:
                    payload, pending = pending.split(b'\0', 1)
                    if payload:
                        message = json.loads(payload)
                        assert message['type'] != 'unrecoverable-error', message
                        messages.append(message)

        try:
            connection, _ = listener.accept()
            connection.settimeout(15)
            receive_until(lambda: any(m['type'] == 'server-started' for m in messages))
            port = next(m['payload']['httpPort'] for m in messages if m['type'] == 'server-started')

            def request(path, method='GET', body=None, request_id=0):
                client = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
                headers = {'x-vercel-internal-invocation-id': f'synthetic-{request_id}',
                           'x-vercel-internal-request-id': str(request_id)}
                if body is not None: headers['Content-Type'] = 'application/json'
                try:
                    client.request(method, path, body=body, headers=headers)
                    response = client.getresponse()
                    return response.status, response.read(), dict(response.getheaders())
                finally:
                    client.close()

            assert request('/_vercel/ping')[0] == 200
            status, payload, headers = request('/v1/development/status?canary=PRIVATE_QUERY_CANARY', request_id=1)
            assert status == 200
            assert json.loads(payload) == {
                'enabled': True, 'authenticated': False, 'configuration': {'configured': False},
                'production_enabled': False, 'cloud': True, 'request_bound': True,
            }
            assert headers.get('Cache-Control') == 'no-store'
            assert headers.get('Content-Type') == 'application/json; charset=utf-8'
            assert request('/v1/conversations', request_id=2)[0] == 503
            assert request('/v1/development/login', method='POST', body='{}', request_id=3)[0] == 503
            receive_until(lambda: sum(m['type'] == 'end' for m in messages) == 3)
            starts = [m['payload']['context']['requestId'] for m in messages if m['type'] == 'handler-started']
            ends = [m['payload']['context']['requestId'] for m in messages if m['type'] == 'end']
            assert Counter(starts) == Counter({1: 1, 2: 1, 3: 1}), starts
            assert Counter(ends) == Counter(starts), ends
            assert 'PRIVATE_QUERY_CANARY' not in json.dumps(messages)
            for message in messages:
                if message['type'] == 'log':
                    decoded = base64.b64decode(message['payload']['message']).decode('utf-8')
                    decoded_logs.append(decoded)
                    assert 'PRIVATE_QUERY_CANARY' not in decoded
                    assert 'PRIVATE_SETUP_CANARY' not in decoded
        finally:
            process.terminate()
            try: out, err = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                out, err = process.communicate(timeout=5)
            if connection is not None: connection.close()
            listener.close()
        assert b'PRIVATE_QUERY_CANARY' not in out + err
        assert b'PRIVATE_SETUP_CANARY' not in out + err
        logs = ''.join(decoded_logs) + (out + err).decode('utf-8')
        assert 'HCLA_STARTUP_FAILED code=CONFIG' in logs
        assert 'Traceback' not in logs
        print(json.dumps({'runtime': 'vercel-runtime==0.22.1', 'readiness': 'PASS',
                          'unconfigured_status': 'PASS', 'private_route_denial': 'PASS',
                          'lifecycle_ipc': 'PASS', 'request_url_redaction': 'PASS',
                          'startup_code_redaction': 'PASS',
                          'provider_calls': 0, 'database_connections': 0}))


if __name__ == '__main__':
    main()
