"""Single-owner HTTPS authentication; credentials never enter product storage."""
import hashlib
import hmac
import secrets
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from packages.store.ledger import Fault
from packages.cloud.postgres import TENANT

COOKIE='__Host-hcla'

def password_verifier(password, salt=None):
    if not isinstance(password,str) or not 12<=len(password)<=1024: raise ValueError('Use a password between 12 and 1024 characters')
    salt=salt or secrets.token_bytes(16)
    key=hashlib.scrypt(password.encode(),salt=salt,n=131072,r=8,p=1,dklen=32,maxmem=256*1024*1024)
    return 'scrypt$131072$8$1$'+salt.hex()+'$'+key.hex()

def valid_verifier(value):
    try:
        algorithm,n,r,p,salt,key=value.split('$')
        return (algorithm,n,r,p)==('scrypt','131072','8','1') and len(bytes.fromhex(salt))==16 and len(bytes.fromhex(key))==32
    except (ValueError,AttributeError): return False

class CloudAuth:
    def __init__(self,store,origin,login,verifier):
        self.store=store;self.origin=origin;self.login_name=login;self.verifier=verifier
        self.epoch=hashlib.sha256((login+'\n'+verifier).encode()).hexdigest()
        self.host=urlsplit(origin).netloc
        if not valid_verifier(verifier): raise ValueError('Owner password verifier required')
    def boundary(self,request,mutation=False):
        # Exact configured origin, not forwarded client-supplied host allowlists.
        if request.headers.get('Host')!=self.host: raise Fault(403,'Untrusted host')
        if request.headers.get('Origin') not in (None,self.origin): raise Fault(403,'Untrusted origin')
        if request.headers.get('Sec-Fetch-Site')=='cross-site': raise Fault(403,'Cross-site request refused')
        if mutation and (request.headers.get('Origin')!=self.origin or request.headers.get('X-HCLA-Request')!='1'): raise Fault(403,'Same-app request required')
    def login(self,credentials):
        if not isinstance(credentials,dict): raise Fault(401,'Sign-in failed')
        password=credentials.get('password');login=credentials.get('login')
        # Reserve an attempt before the costly KDF, globally across instances.
        with self.store.transaction():
            self.store.db.execute('DELETE FROM login_attempts WHERE attempted_at < clock_timestamp() - interval \'1 minute\'')
            count=self.store.db.execute('SELECT count(*) AS n FROM login_attempts').fetchone()['n']
            if count>=5: raise Fault(429,'Too many sign-in attempts; wait one minute')
            self.store.db.execute('INSERT INTO login_attempts DEFAULT VALUES')
        try:
            salt=bytes.fromhex(self.verifier.split('$')[4])
            candidate=password_verifier(password,salt)
            matches=hmac.compare_digest(candidate,self.verifier) and isinstance(login,str) and hmac.compare_digest(login.encode(),self.login_name.encode())
        except (ValueError,TypeError): matches=False
        if not matches: raise Fault(401,'Sign-in failed')
        token=secrets.token_urlsafe(32)
        with self.store.transaction():
            self.store.db.execute('DELETE FROM sessions WHERE expires_at <= clock_timestamp() OR epoch != ?',(self.epoch,))
            self.store.db.execute('INSERT INTO sessions(session_key,epoch,expires_at) VALUES(?,?,clock_timestamp()+interval \'12 hours\')',(hashlib.sha256(token.encode()).hexdigest(),self.epoch))
        return token
    def key(self,cookie):
        parsed=SimpleCookie()
        try:
            parsed.load(cookie or '');token=parsed[COOKIE].value
            if len(token)>128: raise ValueError()
        except (KeyError,ValueError): raise Fault(401,'Sign-in required') from None
        return hashlib.sha256(token.encode()).hexdigest()
    def require(self,cookie):
        key=self.key(cookie)
        with self.store.transaction():
            row=self.store.db.execute('SELECT session_key FROM sessions WHERE session_key=? AND epoch=? AND expires_at>clock_timestamp()',(key,self.epoch)).fetchone()
        if row is None: raise Fault(401,'Sign-in required')
        return TENANT
    def logout(self,cookie):
        key=self.key(cookie)
        with self.store.transaction(): self.store.db.execute('DELETE FROM sessions WHERE session_key=?',(key,))
    @staticmethod
    def cookie(token): return COOKIE+'='+token+'; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'
