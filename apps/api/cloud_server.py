"""Opt-in cloud application; each invocation owns its connections and work."""
import os
from pathlib import Path
from packages.store.ledger import Ledger, Fault
from packages.store.registry import Stores
from packages.controller.interaction import Controller
from packages.controller.live_chat import LiveChat
from packages.adapter.deepseek import DeepSeekAdapter
from packages.runtime_bridge.bridge import RuntimeBridge
from packages.cloud.auth import CloudAuth
from packages.cloud.config import CloudConfig
from packages.cloud.postgres import PostgresLedger,TENANT
from packages.cloud.budget import CloudBudget
from packages.cloud.lifecycle import Lifecycle,DurableCancellation
from packages.cloud.diagnostics import StartupCode,StartupDiagnostics,close_after_startup_failure

class CloudStores(Stores):
    def conversation(self,tenant,**kwargs):
        if kwargs.get('memory')=='TEMPORARY': raise Fault(409,'Temporary conversations use the request-bound tab-memory route')
        return self.persistent.conversation(tenant,**kwargs)

class CloudApplication:
    cloud=True
    request_bound=True
    real_chat=True
    def __init__(self,config,*,store=None,adapter=None,runtime=None,startup=None,member_provider=None):
        startup=startup or StartupDiagnostics()
        self.cloud_config=config
        store=store or PostgresLedger(config.database_url,startup=startup)
        try:
            startup.mark(StartupCode.TEMPORARY_STORE)
            self.stores=CloudStores(store)
            startup.mark(StartupCode.OWNER_AUTH)
            self.development_auth=CloudAuth(store,config.origin,config.login,config.verifier)
            self.member_auth=None;self.member_context=None;self.entitlements=None
            if getattr(config,'member_provider',None) or member_provider:
                from packages.cloud.member_auth import MemberAuth,SupabaseAuthProvider
                self.member_auth=MemberAuth(store,config.origin,config.state_key,member_provider or SupabaseAuthProvider(config.member_provider))
            startup.mark(StartupCode.RUNTIME_BRIDGE)
            self.development_bridge=RuntimeBridge(Path(runtime).absolute()) if runtime else None
            startup.mark(StartupCode.LIFECYCLE)
            self.controllers={};self.lifecycle=Lifecycle(store)
            self.lifecycle.recover()
            self.live_chat_service=None
            self.trial_auth=None
            from packages.cloud.trial import from_database_policy
            startup.mark(StartupCode.PROVIDER_BUDGET)
            config=from_database_policy(store,config)
            self.cloud_config=config
            if config.provider:
                c=config.provider
                startup.mark(StartupCode.PROVIDER_BUDGET)
                from packages.cloud.trial import TrialBudget,TrialAuth,TrialCancellation
                trial=getattr(config,'trial',None)
                budget=TrialBudget(store,c,trial) if trial else CloudBudget(store,c)
                if trial:self.trial_auth=TrialAuth(config.origin,config.state_key,budget)
                startup.mark(StartupCode.PROVIDER_ADAPTER)
                adapter=adapter or DeepSeekAdapter(base_url=c.base_url,model=c.model,api_key=c.api_key,wall_timeout=60)
                self.live_chat_service=LiveChat(c,budget,adapter,cancellation_factory=lambda identity:TrialCancellation(DurableCancellation(store,identity),budget) if trial else DurableCancellation(store,identity))
            self.configuration={'configured':True,'provider_enabled':config.provider is not None}
            if self.trial_auth:self.configuration['temporary_trial']=True
            if self.member_auth:self.configuration['member_accounts']=True
        except Exception:
            close_after_startup_failure(store)
            if hasattr(self,'stores'):close_after_startup_failure(self.stores.temporary)
            raise
    def controller(self,store):
        if store not in self.controllers:
            # Persistent bodies never enter the volatile-only HCL bridge.
            self.controllers[store]=Controller(store,live_chat_service=None if self.trial_auth else self.live_chat_service)
        return self.controllers[store]
    def start(self,ctrl,tenant,run): return run
    def authenticate_member(self,request):
        if self.member_auth is None:raise Fault(503,'普通账号服务尚未启用')
        self.member_auth.boundary(request,mutation=request.command=='POST')
        principal=self.member_auth.require(request.headers.get('Cookie'))
        session_key=self.member_auth.key(request.headers.get('Cookie'))
        if self.member_context is not None:
            if self.member_context!=(principal.tenant,session_key):raise Fault(403,'Account changed during request')
            return principal.tenant
        self.member_context=(principal.tenant,session_key)
        from packages.cloud.entitlements import Entitlements,MemberBudget,MemberCancellation
        self.entitlements=Entitlements(self.stores.persistent)
        self.controllers={};self.lifecycle.recover()
        service=self.live_chat_service
        # The separately authorized public trial never grants member spending.
        if service and not self.trial_auth:
            budget=MemberBudget(service.budget,self.entitlements,self.member_auth,session_key,'CONVERSATION')
            self.live_chat_service=LiveChat(service.config,budget,service.adapter,cancellation_factory=lambda identity:MemberCancellation(DurableCancellation(self.stores.persistent,identity),self.member_auth,session_key,self.entitlements,'CONVERSATION'))
        else:self.live_chat_service=None
        return principal.tenant
    def member_status(self,cookie):
        if self.member_auth is None:return {'available':False,'authenticated':False}
        try:
            principal=self.member_auth.require(cookie)
        except Fault as error:
            if error.status==401:return {'available':True,'authenticated':False,'renewable':self.member_auth.renewable(cookie)}
            raise
        from packages.cloud.entitlements import Entitlements
        rights=Entitlements(self.stores.persistent).status()
        return {'available':True,'authenticated':True,'expires_at':principal.expires_at,
                'account_scope':principal.tenant,
                'renewable':True,
                'entitlements':rights,'model_enabled':self.live_chat_service is not None and not self.trial_auth}
    def execute(self,tenant,run_id):
        if self.trial_auth:raise Fault(403,'Trial grant supports only temporary request-bound conversations')
        store=self.stores.persistent;ctrl=self.controller(store)
        with store.transaction():
            run=ctrl.read(tenant,run_id)
            if not run['pending']: return run
            if self.member_context:self.entitlements.require('CONVERSATION')
            owner=self.lifecycle.claim(run_id)
        if owner is None: return ctrl.read(tenant,run_id)
        store.fence=(run_id,owner)
        try:
            ctrl.finish(tenant,run_id)
            self.lifecycle.finish(run_id,owner)
            return ctrl.read(tenant,run_id)
        finally: store.fence=None
    def close(self):
        self.stores.persistent.close();self.stores.temporary.close()

class Unconfigured:
    cloud=True;request_bound=True;real_chat=True;development_auth=None
    configuration={'configured':False}
    def close(self): pass

def application(env=None):
    env=os.environ if env is None else env
    # Fail closed; never select local SQLite/mock on a cloud setup error.
    startup=StartupDiagnostics()
    try:
        startup.mark(StartupCode.CONFIG)
        config=CloudConfig.from_env(env)
        return CloudApplication(config,runtime=env.get('HCL_DEVELOPMENT_ARTIFACT','.hcla-runtime'),startup=startup)
    except Exception:
        startup.report()
        return Unconfigured()
