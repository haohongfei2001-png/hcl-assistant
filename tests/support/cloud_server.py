"""Local-only cloud browser fixture. Disposable Postgres + injected model bytes.

The loopback adapter normalizes test Host/Origin to exercise the HTTPS boundary
without installing a certificate. This is never imported by the deploy entry.
"""
import os
import threading
import time
from dataclasses import replace
from decimal import Decimal
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlsplit
import psycopg
from psycopg.rows import dict_row
from packages.cloud.auth import CloudAuth,password_verifier
from packages.cloud.config import CloudConfig
from packages.cloud.postgres import PostgresLedger
from packages.cloud.trial import TrialWindow,TrialAuth,trial_policy
from packages.cloud.member_auth import MemberAuth,VerifiedPrincipal
from tests.support.member_provider import FakeMemberProvider
from packages.adapter.development_budget import DevelopmentConfig,DevelopmentBudget
from packages.adapter.deepseek import DeepSeekAdapter
from apps.api.cloud_server import CloudApplication
from apps.api.server import handler as make_handler
from tests.support.cloud_transport import CloudFakeTransport as FakeTransport

DSN=os.environ['HCLA_TEST_POSTGRES_DSN']
parsed=urlsplit(DSN)
if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.path!='/hcla_test':raise RuntimeError('Disposable localhost database required')
config=DevelopmentConfig.from_env({'HCLA_DEEPSEEK_API_KEY':'offline-fixture','HCLA_DEEPSEEK_BASE_URL':'https://api.deepseek.com','HCLA_DEEPSEEK_MODEL':'deepseek-v4-pro','HCLA_DEV_ACCESS_TOKEN':'offline-browser-cloud-auth','HCLA_DEV_MAX_REQUESTS':'100','HCLA_DEV_MAX_COST_USD':'1000','HCLA_DEV_INPUT_USD_PER_MILLION':'1.32','HCLA_DEV_OUTPUT_USD_PER_MILLION':'3.96','HCLA_DEV_MAX_OUTPUT_TOKENS':'512','HCLA_DEV_BUDGET_ID':'offline-cloud-browser'})
verifier=password_verifier('offline password fixture')
trial_config=replace(config,budget_id='offline-browser-trial',max_cost_usd=Decimal('10'),max_requests=999999999)
trial_window=TrialWindow(int(time.time())-1,int(time.time())-1+14400)
trial_mode=False
trial_expired=False
member_mode=False
with psycopg.connect(DSN,autocommit=True) as admin:
 admin.execute('TRUNCATE hcla.member_sessions,hcla.member_login_attempts,hcla.member_budget_attempts,hcla.member_entitlements,hcla.budget_policy,hcla.budget_attempts,hcla.login_attempts,hcla.sessions,hcla.execution,hcla.temporary_heads,hcla.idempotency,hcla.events,hcla.records,hcla.sources,hcla.objects,hcla.accounts')
 admin.execute('INSERT INTO hcla.budget_policy VALUES(1,%s)',(DevelopmentBudget._policy(SimpleNamespace(config=config)),))
 admin.execute('TRUNCATE hcla.trial_budget_policy,hcla.trial_budget_attempts')
 admin.execute('INSERT INTO hcla.trial_budget_policy VALUES(1,%s)',(trial_policy(trial_config,trial_window),))

class FixtureAuth(CloudAuth):
 def boundary(self,request,mutation=False):
  if request.client_address[0]!='127.0.0.1' or request.headers.get('Origin') not in (None,'http://127.0.0.1:5173'):raise ValueError('Loopback fixture only')
  headers={'Host':self.host,'Origin':self.origin if mutation else None,'X-HCLA-Request':request.headers.get('X-HCLA-Request'),'Sec-Fetch-Site':request.headers.get('Sec-Fetch-Site')}
  return CloudAuth.boundary(self,SimpleNamespace(headers=headers),mutation)

class FixtureTrialAuth(TrialAuth):
 boundary=FixtureAuth.boundary

class FixtureMemberAuth(MemberAuth):
 boundary=FixtureAuth.boundary

class CompletionWriter:
 def __init__(self,original,mode):self.original=original;self.mode=mode;self.done=False
 def write(self,value):
  if b'"type": "cloud.completed"' in value and self.mode:
   time.sleep(1.5)
   if self.mode=='interrupt':self.done=True;raise BrokenPipeError()
  if self.done:raise BrokenPipeError()
  return self.original.write(value)
 def __getattr__(self,name):return getattr(self.original,name)

class Handler(BaseHTTPRequestHandler):
 def __init__(self,*args,**kwargs):
  connection=psycopg.connect(DSN,autocommit=True,row_factory=dict_row,prepare_threshold=None);connection.execute('SET ROLE hcla_app')
  selected=trial_config if trial_mode else config
  cfg=CloudConfig('', 'https://hcla.example.test','owner',verifier,'1'*64,selected,trial_window if trial_mode else None)
  adapter=DeepSeekAdapter(base_url=selected.base_url,model=selected.model,api_key=selected.api_key,transport_factory=FakeTransport,wall_timeout=10)
  app=CloudApplication(cfg,store=PostgresLedger('',connection=connection),adapter=adapter,runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT'),member_provider=FakeMemberProvider() if member_mode else None)
  app.development_auth=FixtureAuth(app.stores.persistent,cfg.origin,cfg.login,cfg.verifier)
  if app.member_auth:app.member_auth=FixtureMemberAuth(app.stores.persistent,cfg.origin,cfg.state_key,FakeMemberProvider())
  if app.trial_auth:
   app.trial_auth=FixtureTrialAuth(cfg.origin,cfg.state_key,app.live_chat_service.budget)
   actual_clock=app.trial_auth.budget.clock
   app.trial_auth.budget.clock=lambda:trial_window.expires_at+1 if trial_expired else actual_clock()
  try:
   class FixtureHandler(make_handler(app)):
    def do_POST(self):
     global trial_mode,trial_expired,member_mode
     if self.path=='/v1/fixture/member-mode' and self.client_address[0]=='127.0.0.1':
      trial_mode=False;member_mode=True
      with psycopg.connect(DSN,autocommit=True) as admin:
       admin.execute('TRUNCATE hcla.member_sessions,hcla.member_login_attempts,hcla.member_budget_attempts,hcla.member_entitlements,hcla.budget_attempts,hcla.execution,hcla.temporary_heads,hcla.idempotency,hcla.events,hcla.records,hcla.sources,hcla.objects,hcla.accounts')
       for subject in FakeMemberProvider.identities.values():
        tenant=VerifiedPrincipal(FakeMemberProvider.issuer,subject,1).tenant
        admin.execute("INSERT INTO hcla.member_entitlements(tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_usd) VALUES(%s,'offline-browser-member',true,clock_timestamp()-interval '1 minute',clock_timestamp()+interval '1 hour',true,true,100,1000)",(tenant,))
      self.json(200,{'fixture_members':True});return
     if self.path in {'/v1/fixture/member-renew','/v1/fixture/member-expire'} and self.client_address[0]=='127.0.0.1':
      with psycopg.connect(DSN,autocommit=True) as admin:
       if self.path.endswith('member-renew'):admin.execute("UPDATE hcla.member_sessions SET expires_at=clock_timestamp()+interval '30 seconds'")
       else:admin.execute("UPDATE hcla.member_sessions SET expires_at=clock_timestamp()-interval '2 seconds',absolute_expires_at=clock_timestamp()-interval '1 second'")
      self.json(200,{'fixture_changed':True});return
     if self.path=='/v1/fixture/trial-mode' and self.client_address[0]=='127.0.0.1':
      trial_mode=True;trial_expired=False;member_mode=False;self.json(200,{'fixture_trial':True});return
     if self.path=='/v1/fixture/trial-expire' and self.client_address[0]=='127.0.0.1':
      trial_expired=True;self.json(200,{'fixture_expired':True});return
     if self.path=='/v1/fixture/reset-throttle' and self.client_address[0]=='127.0.0.1':
      with psycopg.connect(DSN,autocommit=True) as admin:admin.execute('DELETE FROM hcla.login_attempts')
      self.json(200,{'fixture_reset':True});return
     mode=self.headers.get('X-HCLA-Fixture-Completion')
     if mode in {'delay','interrupt'}:self.wfile=CompletionWriter(self.wfile,mode)
     return super().do_POST()
   FixtureHandler(*args,**kwargs)
  finally:app.close()
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8771),Handler).serve_forever()
