"""Injected account identity fixture. Never loaded by deployed code."""
import time
import base64
import hashlib
import hmac
import threading
import uuid
from packages.cloud.member_auth import VerifiedPrincipal,VerifiedSession,VerifiedRecovery,PasswordMutationRejected
from packages.store.ledger import Fault

class FakeMemberProvider:
    issuer='https://abcdefghijklmnopqrst.supabase.co/auth/v1'
    identities={'a@example.test':'10000000-0000-4000-8000-000000000001',
                'b@example.test':'10000000-0000-4000-8000-000000000002'}
    passwords={};pending={};access={};calls=[];lock=threading.RLock()
    @classmethod
    def reset(cls):
        with cls.lock:cls.passwords={};cls.pending={};cls.access={};cls.calls=[]
    @classmethod
    def recovery_code(cls,email):
        with cls.lock:return next(code for code,value in reversed(list(cls.pending.items())) if value['email']==email)
    def register(self,email,password):pass
    def login(self,email,password):
        if email not in self.identities or password!=self.passwords.get(email,'offline member password'):raise Fault(401,'Account authentication failed')
        return VerifiedSession(VerifiedPrincipal(self.issuer,self.identities[email],int(time.time())+3600),'offline-refresh-'+self.identities[email])
    def refresh(self,token):
        for subject in self.identities.values():
            if token.startswith('offline-refresh-'+subject):
                return VerifiedSession(VerifiedPrincipal(self.issuer,subject,int(time.time())+3600),token+'-rotated')
        raise Fault(401,'Account authentication failed')

    def request_recovery(self,email,challenge,redirect):
        with self.lock:
            self.calls.append('request')
            if email in self.identities:self.pending[str(uuid.uuid4())]={'email':email,'challenge':challenge,'used':False,'redirect':redirect}
    def exchange_recovery(self,code,verifier):
        with self.lock:
            self.calls.append('exchange');row=self.pending.get(code)
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            if row is None or row['used'] or not hmac.compare_digest(row['challenge'],challenge):raise Fault(401,'Invalid fixture recovery')
            row['used']=True;token='offline-recovery-access-'+str(uuid.uuid4());self.access[token]=row['email']
            return self.recovery_identity(token)
    def recovery_identity(self,token):
        with self.lock:
            email=self.access.get(token)
            if email is None:raise Fault(401,'Invalid fixture recovery')
            return VerifiedRecovery(VerifiedPrincipal(self.issuer,self.identities[email],int(time.time())+3600),email,token)
    def update_password(self,token,password,subject):
        with self.lock:
            self.calls.append('update');value=self.recovery_identity(token)
            if value.principal.subject!=subject:raise PasswordMutationRejected()
            if password.startswith('weak-fixture'):raise PasswordMutationRejected(True)
            self.passwords[value.email]=password
            if password.startswith('uncertain-fixture'):raise ConnectionError('SYNTHETIC_SECRET_ERROR_SENTINEL')
