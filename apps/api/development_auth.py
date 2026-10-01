"""Ephemeral single-operator loopback sessions. Not a public deployment auth system."""
import hashlib
import hmac
import secrets
import threading
import time
from http.cookies import SimpleCookie
from packages.store.ledger import Fault


class DevelopmentAuth:
    def __init__(self, access_token):
        if not access_token or len(access_token)<24:raise ValueError('HCLA_DEV_ACCESS_TOKEN must be configured with at least 24 characters')
        self._token=access_token;self._sessions={};self._failures=[];self._lock=threading.RLock()

    def boundary(self, request, mutation=False):
        allowed={'127.0.0.1:8765','localhost:8765','127.0.0.1:5173','localhost:5173',f'127.0.0.1:{request.server.server_port}',f'localhost:{request.server.server_port}'}
        if request.client_address[0] not in {'127.0.0.1','::1'} or request.headers.get('Host') not in allowed:raise Fault(403,'Development server is loopback only')
        origin=request.headers.get('Origin')
        if origin and origin not in {'http://'+host for host in allowed}:raise Fault(403,'Untrusted development origin')
        if mutation and request.headers.get('X-HCLA-Request')!='1':raise Fault(403,'Same-app request required')
        if request.headers.get('Sec-Fetch-Site')=='cross-site':raise Fault(403,'Cross-site request refused')

    def login(self, token):
        with self._lock:
            now=time.monotonic();self._failures=[t for t in self._failures if now-t<60]
            if len(self._failures)>=5:raise Fault(429,'Too many sign-in attempts; wait one minute')
            if not isinstance(token,str) or not hmac.compare_digest(token,self._token):
                self._failures.append(now);raise Fault(401,'Development access denied')
            session=secrets.token_urlsafe(32)
            self._sessions[hashlib.sha256(session.encode()).hexdigest()]=now+3600
            return session

    def require(self, cookie):
        parsed=SimpleCookie()
        try:parsed.load(cookie or '');session=parsed['hcla_development'].value
        except (KeyError,ValueError):raise Fault(401,'Development sign-in required') from None
        key=hashlib.sha256(session.encode()).hexdigest()
        with self._lock:
            if self._sessions.get(key,0)<time.monotonic():self._sessions.pop(key,None);raise Fault(401,'Development sign-in required')
        return 'synthetic-demo-a'
