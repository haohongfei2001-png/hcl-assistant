"""Local-only cloud browser fixture. Disposable Postgres + injected model bytes.

The loopback adapter normalizes test Host/Origin to exercise the HTTPS boundary
without installing a certificate. This is never imported by the deploy entry.
"""
import os
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlsplit
import psycopg
from psycopg.rows import dict_row
from packages.cloud.auth import CloudAuth,password_verifier
from packages.cloud.config import CloudConfig
from packages.cloud.postgres import PostgresLedger
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
with psycopg.connect(DSN,autocommit=True) as admin:
 admin.execute('TRUNCATE hcla.budget_policy,hcla.budget_attempts,hcla.login_attempts,hcla.sessions,hcla.execution,hcla.temporary_heads,hcla.idempotency,hcla.events,hcla.records,hcla.sources,hcla.objects,hcla.accounts')
 admin.execute('INSERT INTO hcla.budget_policy VALUES(1,%s)',(DevelopmentBudget._policy(SimpleNamespace(config=config)),))

class FixtureAuth(CloudAuth):
 def boundary(self,request,mutation=False):
  if request.client_address[0]!='127.0.0.1' or request.headers.get('Origin') not in (None,'http://127.0.0.1:5173'):raise ValueError('Loopback fixture only')
  headers=dict(request.headers);headers['Host']=self.host
  if mutation:headers['Origin']=self.origin
  return super().boundary(SimpleNamespace(headers=headers),mutation)

class Handler(BaseHTTPRequestHandler):
 def __init__(self,*args,**kwargs):
  connection=psycopg.connect(DSN,autocommit=True,row_factory=dict_row,prepare_threshold=None);connection.execute('SET ROLE hcla_app')
  cfg=CloudConfig('', 'https://hcla.example.test','owner',verifier,'1'*64,config)
  adapter=DeepSeekAdapter(base_url=config.base_url,model=config.model,api_key=config.api_key,transport_factory=FakeTransport,wall_timeout=10)
  app=CloudApplication(cfg,store=PostgresLedger('',connection=connection),adapter=adapter,runtime=os.environ.get('HCL_DEVELOPMENT_ARTIFACT'))
  app.development_auth=FixtureAuth(app.stores.persistent,cfg.origin,cfg.login,cfg.verifier)
  try:make_handler(app)(*args,**kwargs)
  finally:app.close()
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8771),Handler).serve_forever()
