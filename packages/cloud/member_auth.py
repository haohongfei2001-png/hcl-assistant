"""Disabled-by-default account authentication, independent of owner/trial auth.

Only the Auth service verifies passwords. Browser cookies are opaque. Refresh
material is encrypted server-side; passwords and upstream JWTs are not stored.
"""
from dataclasses import dataclass
import base64
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import json
import re
import secrets
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler
import uuid

from packages.cloud.auth import CloudAuth
from packages.store.ledger import Fault

COOKIE = '__Host-hcla-member'
SESSION_SECONDS = 900
ABSOLUTE_SECONDS = 43200


@dataclass(frozen=True, repr=False)
class VerifiedPrincipal:
    issuer: str
    subject: str
    expires_at: int

    @property
    def tenant(self):
        return 'member-' + hashlib.sha256((self.issuer+'\n'+self.subject).encode()).hexdigest()


@dataclass(frozen=True, repr=False)
class VerifiedSession:
    principal: VerifiedPrincipal
    refresh_token: str


@dataclass(frozen=True, repr=False)
class MemberProviderConfig:
    url: str
    publishable_key: str

    @classmethod
    def from_env(cls, env):
        if not env.get('HCLA_MEMBER_AUTH'): return None
        if env['HCLA_MEMBER_AUTH'] != 'supabase': raise ValueError('Unsupported account provider')
        url = env.get('HCLA_SUPABASE_AUTH_URL', '')
        key = env.get('HCLA_SUPABASE_PUBLISHABLE_KEY', '')
        if not re.fullmatch(r'https://[a-z0-9]{20}\.supabase\.co', url):
            raise ValueError('Exact Supabase project origin required')
        if not re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]{16,200}', key):
            raise ValueError('Publishable account key required')
        return cls(url, key)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class SupabaseAuthProvider:
    def __init__(self, config, *, transport=None):
        self.config=config; self.issuer=config.url+'/auth/v1'
        self.transport=transport or self._http

    def _http(self, path, body=None, token=None, method=None):
        headers={'apikey':self.config.publishable_key, 'Content-Type':'application/json'}
        if token: headers['Authorization']='Bearer '+token
        request=Request(self.issuer+path, data=None if body is None else json.dumps(body).encode(), headers=headers,method=method)
        try:
            with build_opener(NoRedirect()).open(request, timeout=5) as response:
                raw=response.read(65537)
                if response.status==204:return {}
                if response.status != 200 or len(raw)>65536: raise ValueError()
                value=json.loads(raw)
                if not isinstance(value,dict): raise ValueError()
                return value
        except HTTPError as error:
            # Never render or log provider bodies, credentials or exception text.
            if method=='PUT' and path=='/user':
                if error.code in (401,403,429):raise PasswordMutationRejected(error.code==429) from None
                if error.code in (400,422):
                    try:
                        raw=error.read(65537)
                        value=json.loads(raw) if len(raw)<=65536 else None
                        known=isinstance(value,dict) and value.get('error_code') in {'weak_password','same_password'}
                    except Exception:known=False
                    if known:raise PasswordMutationRejected(True) from None
                # Unknown error semantics cannot establish that a password
                # mutation was never applied. No raw response leaves here.
                raise Fault(503,'Password update could not be confirmed') from None
            if error.code in (400,401,403,422): raise Fault(401,'Account authentication failed') from None
            if error.code==429: raise Fault(429,'Too many account attempts; try later') from None
            raise Fault(503,'Account service temporarily unavailable') from None
        except Exception:
            raise Fault(503,'Account service temporarily unavailable') from None

    def register(self, email, password):
        self.transport('/signup', {'email':email,'password':password})
        # Confirmation is required; no signup response can issue an app session.

    def login(self, email, password):
        result=self.transport('/token?grant_type=password', {'email':email,'password':password})
        return self.verify_session(result)

    def refresh(self, token):
        return self.verify_session(self.transport('/token?grant_type=refresh_token',{'refresh_token':token}))

    def verify_access(self,token):
        if not isinstance(token,str) or not 20<len(token)<16384:raise Fault(401,'Account authentication failed')
        user=self.transport('/user',token=token)
        try:
            parts=token.split('.')
            if len(parts)!=3:raise ValueError()
            claims=json.loads(base64.urlsafe_b64decode(parts[1]+'='*(-len(parts[1])%4)))
            subject=str(uuid.UUID(user['id']))
            if (user['id']!=subject or claims.get('sub')!=subject or claims.get('iss')!=self.issuer
                    or claims.get('aud')!='authenticated' or claims.get('role')!='authenticated'
                    or type(claims.get('exp')) is not int or claims['exp']<=time.time()
                    or user.get('is_anonymous') is not False or not user.get('email_confirmed_at')):raise ValueError()
            return VerifiedPrincipal(self.issuer,subject,claims['exp']),user
        except (ValueError,TypeError,KeyError,AttributeError):raise Fault(401,'Account authentication failed') from None

    def verify_session(self,result):
        principal,_=self.verify_access(result.get('access_token'))
        refresh=result.get('refresh_token')
        if not isinstance(refresh,str) or not 8<=len(refresh)<=8192:raise Fault(401,'Account authentication failed')
        return VerifiedSession(principal,refresh)

    def request_recovery(self,email,challenge,redirect):
        from urllib.parse import urlencode
        self.transport('/recover?'+urlencode({'redirect_to':redirect}),{'email':email,'code_challenge':challenge,'code_challenge_method':'s256'})

    def exchange_recovery(self,code,verifier):
        result=self.transport('/token?grant_type=pkce',{'auth_code':code,'code_verifier':verifier})
        token=result.get('access_token');principal,user=self.verify_access(token)
        return VerifiedRecovery(principal,user.get('email'),token)

    def recovery_identity(self,token):
        principal,user=self.verify_access(token)
        return VerifiedRecovery(principal,user.get('email'),token)

    def update_password(self,token,password,subject):
        result=self.transport('/user',{'password':password},token=token,method='PUT')
        if result.get('id')!=subject:raise Fault(503,'Password update could not be confirmed')


@dataclass(frozen=True,repr=False)
class VerifiedRecovery:
    principal: VerifiedPrincipal
    email: str
    access_token: str


class PasswordMutationRejected(Exception):
    def __init__(self,retryable=False):
        self.retryable=retryable
        super().__init__('Password update rejected')


class MemberAuth:
    boundary=CloudAuth.boundary

    def __init__(self, store, origin, state_key, provider):
        from urllib.parse import urlsplit
        self.store=store; self.origin=origin; self.host=urlsplit(origin).netloc
        self.provider=provider; self._key=bytes.fromhex(state_key)
        self.epoch=hmac.new(self._key,b'hcla-member-session-epoch-v1',hashlib.sha256).hexdigest()
        from packages.cloud.session_vault import SessionVault
        self.vault=SessionVault(state_key)

    def credentials(self, data):
        if not isinstance(data,dict) or set(data)!={'email','password'}: raise Fault(400,'Email and password required')
        email,password=data['email'],data['password']
        if (not isinstance(email,str) or not re.fullmatch(r'[^\s@]{1,128}@[^\s@]{1,125}\.[^\s@]{1,63}',email)
                or len(email)>254 or not isinstance(password,str) or not 12<=len(password)<=1024):
            raise Fault(400,'Use a valid email and a password of 12–1024 characters')
        return email.strip(),password

    def throttle(self, email, purpose='login'):
        if purpose not in {'login','recovery'}:raise ValueError('Invalid throttle purpose')
        identity=hmac.new(self._key,('member-'+purpose+'\n'+email.casefold()).encode(),hashlib.sha256).hexdigest()
        with self.store.transaction():
            self.store.db.execute("DELETE FROM member_login_attempts WHERE attempted_at < clock_timestamp()-interval '1 minute'")
            count=self.store.db.execute('SELECT count(*) AS total,count(*) FILTER (WHERE identity_key=?) AS matching FROM member_login_attempts',(identity,)).fetchone()
            if count['total']>=30 or count['matching']>=5: raise Fault(429,'Too many account attempts; wait one minute')
            self.store.db.execute('INSERT INTO member_login_attempts(identity_key) VALUES(?)',(identity,))

    def register(self, data):
        email,password=self.credentials(data); self.throttle(email)
        try: self.provider.register(email,password)
        except Fault as error:
            if error.status!=401: raise
        return {'confirmation_required':True,'message':'请检查邮箱完成确认，再使用邮箱和密码登录。已有账号可直接登录。'}

    def login(self, data, previous_cookie=None):
        email,password=self.credentials(data); self.throttle(email)
        from packages.cloud import auth_generation
        started=auth_generation.ticket(self.store)
        verified=self.provider.login(email,password)
        if not isinstance(verified,VerifiedSession):raise Fault(401,'Account authentication failed')
        principal=verified.principal
        if not isinstance(principal,VerifiedPrincipal) or principal.issuer!=self.provider.issuer:
            raise Fault(401,'Account authentication failed')
        if previous_cookie:
            try:self.logout(previous_cookie)
            except Fault as error:
                if error.status!=401:raise
        token=secrets.token_urlsafe(32); session_key=hashlib.sha256(token.encode()).hexdigest()
        self.store.member_session_key=session_key
        self.store.bind_member(principal)
        with self.store.transaction():
            generation=auth_generation.current(self.store)['generation']
            auth_generation.require(self.store,generation,started)
            absolute=int(self.clock())+ABSOLUTE_SECONDS
            encrypted=self.vault.seal(verified.refresh_token,principal.issuer,principal.subject,session_key,absolute)
            row=self.store.db.execute("INSERT INTO member_sessions(session_key,tenant,issuer,subject,auth_epoch,auth_generation,expires_at,absolute_expires_at,refresh_ciphertext) VALUES(?,?,?,?,?,?,LEAST(to_timestamp(?),clock_timestamp()+interval '15 minutes'),to_timestamp(?),?) RETURNING FLOOR(EXTRACT(EPOCH FROM expires_at))::bigint AS expires",(session_key,principal.tenant,principal.issuer,principal.subject,self.epoch,generation,principal.expires_at,absolute,encrypted)).fetchone()
            if row['expires']<=self.clock(): raise Fault(401,'Account session expired')
        return token,row['expires']

    def clock(self):
        return float(self.store.db.execute('SELECT EXTRACT(EPOCH FROM clock_timestamp()) AS epoch').fetchone()['epoch'])

    def key(self, cookie):
        try:
            parsed=SimpleCookie(); parsed.load(cookie or '')
            token=parsed[COOKIE].value
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token): raise ValueError()
            return hashlib.sha256(token.encode()).hexdigest()
        except (KeyError,ValueError,CookieError): raise Fault(401,'Account sign-in required') from None

    def require(self, cookie):
        key=self.key(cookie); self.store.member_session_key=key
        with self.store.transaction():
            row=self.store.db.execute("SELECT tenant,issuer,subject,auth_generation,FLOOR(EXTRACT(EPOCH FROM expires_at))::bigint AS expires FROM member_sessions WHERE session_key=? AND issuer=? AND auth_epoch=? AND expires_at>clock_timestamp() AND absolute_expires_at>clock_timestamp() AND (refresh_state='idle' OR refresh_started_at>clock_timestamp()-interval '20 seconds')",(key,self.provider.issuer,self.epoch)).fetchone()
        if row is None: raise Fault(401,'Account sign-in required')
        principal=VerifiedPrincipal(row['issuer'],str(row['subject']),row['expires'])
        if principal.tenant!=row['tenant']: raise Fault(401,'Account sign-in required')
        self.store.bind_member(principal)
        from packages.cloud import auth_generation
        auth_generation.require(self.store,row['auth_generation'])
        return principal

    def active(self, key):
        from packages.cloud import auth_generation
        with self.store.transaction():
            row=self.store.db.execute("SELECT auth_generation FROM member_sessions WHERE session_key=? AND tenant=? AND issuer=? AND auth_epoch=? AND expires_at>clock_timestamp() AND absolute_expires_at>clock_timestamp() AND (refresh_state='idle' OR refresh_started_at>clock_timestamp()-interval '20 seconds')",(key,self.store.tenant,self.provider.issuer,self.epoch)).fetchone()
            if row is None:return False
            try:auth_generation.require(self.store,row['auth_generation'])
            except Fault:return False
            return True

    def renewable(self,cookie):
        from packages.cloud import auth_generation
        try:
            key=self.key(cookie);self.store.member_session_key=key
            with self.store.transaction():
                row=self.store.db.execute("SELECT tenant,issuer,subject,auth_generation,FLOOR(EXTRACT(EPOCH FROM absolute_expires_at))::bigint AS absolute FROM member_sessions WHERE session_key=? AND issuer=? AND auth_epoch=? AND absolute_expires_at>clock_timestamp() AND (refresh_state='idle' OR refresh_started_at>clock_timestamp()-interval '20 seconds')",(key,self.provider.issuer,self.epoch)).fetchone()
            if row is None:return False
            principal=VerifiedPrincipal(row['issuer'],str(row['subject']),row['absolute'])
            if principal.tenant!=row['tenant']:return False
            self.store.bind_member(principal);auth_generation.require(self.store,row['auth_generation']);return True
        except Fault:return False

    def refresh(self,cookie):
        from packages.cloud import auth_generation
        key=self.key(cookie);self.store.member_session_key=key;owner=secrets.token_hex(16)
        with self.store.transaction():
            identity=self.store.db.execute('SELECT tenant,issuer,subject,FLOOR(EXTRACT(EPOCH FROM absolute_expires_at))::bigint AS absolute FROM member_sessions WHERE session_key=? AND issuer=? AND auth_epoch=? AND absolute_expires_at>clock_timestamp()',(key,self.provider.issuer,self.epoch)).fetchone()
        if identity is None:raise Fault(401,'Account sign-in required')
        principal=VerifiedPrincipal(identity['issuer'],str(identity['subject']),identity['absolute'])
        if principal.tenant!=identity['tenant']:raise Fault(401,'Account sign-in required')
        self.store.bind_member(principal)
        with self.store.transaction():
            row=self.store.db.execute("SELECT *,FLOOR(EXTRACT(EPOCH FROM absolute_expires_at))::bigint AS absolute,expires_at>clock_timestamp()+interval '60 seconds' AS fresh,refresh_started_at>clock_timestamp()-interval '20 seconds' AS recent FROM member_sessions WHERE session_key=? AND issuer=? AND auth_epoch=? AND absolute_expires_at>clock_timestamp()",(key,self.provider.issuer,self.epoch)).fetchone()
            if row is None:raise Fault(401,'Account sign-in required')
            auth_generation.require(self.store,row['auth_generation'])
            if row['refresh_state']!='idle':
                if row['recent']:raise Fault(409,'Account renewal is already in progress')
                # Lost worker/response: a lease timeout never permits token reuse.
                raise Fault(401,'Account renewal interrupted; sign in again')
            if row['fresh']:return
            self.store.db.execute("UPDATE member_sessions SET refresh_state='inflight',refresh_owner=?,refresh_started_at=clock_timestamp() WHERE session_key=?",(owner,key))
        try:
            old=self.vault.open(row['refresh_ciphertext'],row['issuer'],str(row['subject']),key,row['absolute'])
            renewed=self.provider.refresh(old)
            principal=renewed.principal
            if principal.issuer!=row['issuer'] or principal.subject!=str(row['subject']) or principal.tenant!=row['tenant']:raise ValueError()
            encrypted=self.vault.seal(renewed.refresh_token,principal.issuer,principal.subject,key,row['absolute'])
            with self.store.transaction():
                auth_generation.require(self.store,row['auth_generation'])
                changed=self.store.db.execute("UPDATE member_sessions SET refresh_ciphertext=?,expires_at=LEAST(to_timestamp(?),absolute_expires_at,clock_timestamp()+interval '15 minutes'),refresh_state='idle',refresh_owner=NULL,refresh_started_at=NULL WHERE session_key=? AND refresh_owner=? AND refresh_state='inflight' AND refresh_started_at>clock_timestamp()-interval '20 seconds' AND absolute_expires_at>clock_timestamp() AND to_timestamp(?)>clock_timestamp() RETURNING session_key",(encrypted,principal.expires_at,key,owner,principal.expires_at)).fetchone()
                if changed is None:raise Fault(401,'Account session changed; sign in again')
        except Exception:
            # Do not persist/retry an uncertain token. Conditional deletion cannot
            # recreate a logged-out session or remove a different generation.
            with self.store.transaction():self.store.db.execute('DELETE FROM member_sessions WHERE session_key=? AND refresh_owner=?',(key,owner))
            raise Fault(401,'Account renewal interrupted; sign in again') from None

    def logout(self, cookie):
        key=self.key(cookie);self.store.member_session_key=key
        with self.store.transaction():
            self.store.db.execute('DELETE FROM member_sessions WHERE session_key=?',(key,))

    @staticmethod
    def cookie(token): return COOKIE+'='+token+'; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'

    @staticmethod
    def clear_cookie(): return COOKIE+'=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
