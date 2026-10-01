"""Injected account identity fixture. Never loaded by deployed code."""
import time
from packages.cloud.member_auth import VerifiedPrincipal,VerifiedSession
from packages.store.ledger import Fault

class FakeMemberProvider:
    issuer='https://abcdefghijklmnopqrst.supabase.co/auth/v1'
    identities={'a@example.test':'10000000-0000-4000-8000-000000000001',
                'b@example.test':'10000000-0000-4000-8000-000000000002'}
    def register(self,email,password):pass
    def login(self,email,password):
        if email not in self.identities or password!='offline member password':raise Fault(401,'Account authentication failed')
        return VerifiedSession(VerifiedPrincipal(self.issuer,self.identities[email],int(time.time())+3600),'offline-refresh-'+self.identities[email])
    def refresh(self,token):
        for subject in self.identities.values():
            if token.startswith('offline-refresh-'+subject):
                return VerifiedSession(VerifiedPrincipal(self.issuer,subject,int(time.time())+3600),token+'-rotated')
        raise Fault(401,'Account authentication failed')
