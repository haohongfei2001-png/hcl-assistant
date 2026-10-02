"""Opt-in cloud application; each invocation owns its connections and work."""
import os
import time
from pathlib import Path
from packages.store.ledger import Ledger, Fault
from packages.store.registry import Stores
from packages.controller.interaction import Controller
from packages.controller.live_chat import LiveChat
from packages.adapter.deepseek import DeepSeekAdapter
from packages.adapter.provider import create_adapter
from packages.cloud.qwen_budget import QwenCloudBudget
from packages.cloud.qwen_monthly_budget import QwenMonthlyBudget
from packages.cloud.qwen_entitlements import QwenEntitlements,QwenMemberBudget
from packages.runtime_bridge.bridge import RuntimeBridge
from packages.cloud.auth import CloudAuth
from packages.cloud.config import CloudConfig
from packages.cloud.postgres import PostgresLedger,TENANT
from packages.cloud.budget import CloudBudget
from packages.cloud.lifecycle import Lifecycle,DurableCancellation
from packages.cloud.timing import PROVIDER_WALL_SECONDS,REQUEST_PROVIDER_DEADLINE_SECONDS
from packages.cloud.diagnostics import StartupCode,StartupDiagnostics,close_after_startup_failure

class CloudStores(Stores):
    def conversation(self,tenant,**kwargs):
        if kwargs.get('memory')=='TEMPORARY': raise Fault(409,'Temporary conversations use the request-bound tab-memory route')
        return self.persistent.conversation(tenant,**kwargs)

def verify_member_schema(store):
    # Compile metadata-only reads under the restricted role. LIMIT0 reads no
    # session, identity, ciphertext or budget row. Never create schema on startup.
    columns={
        'member_sessions':'session_key,tenant,issuer,subject,auth_epoch,auth_generation,expires_at,absolute_expires_at,refresh_ciphertext,refresh_state,refresh_owner,refresh_started_at',
        'member_login_attempts':'identity_key,attempted_at',
        'member_auth_generations':'tenant,generation,terminal_ticket,reset_pending,reset_owner,reset_phase,uncertainty_ticket',
        'member_entitlements':'tenant,grant_id,enabled,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_usd',
        'member_budget_attempts':'tenant,grant_id,run_key,attempt_key,charged_usd,outcome',
        'execution':'tenant', 'temporary_heads':'tenant',
    }
    fields=[];tables=[]
    for index,(table,names) in enumerate(columns.items()):
        alias='m'+str(index);tables.append(table+' AS '+alias)
        fields.extend(alias+'.'+name for name in names.split(','))
    with store.transaction():
        store.db.execute('SELECT '+','.join(fields)+' FROM '+' CROSS JOIN '.join(tables)+' LIMIT 0').fetchall()
        if not store.db.execute("SELECT has_sequence_privilege(current_user,'hcla.member_auth_order','USAGE') AS permitted").fetchone()['permitted']:raise Fault(503,'Account ordering metadata unavailable')

class CloudApplication:
    cloud=True
    request_bound=True
    real_chat=True
    def __init__(self,config,*,store=None,adapter=None,runtime=None,startup=None,member_provider=None,request_deadline=None):
        request_deadline=request_deadline if request_deadline is not None else time.monotonic()+REQUEST_PROVIDER_DEADLINE_SECONDS
        startup=startup or StartupDiagnostics()
        self.cloud_config=config
        store=store or PostgresLedger(config.database_url,startup=startup)
        try:
            startup.mark(StartupCode.TEMPORARY_STORE)
            self.stores=CloudStores(store)
            startup.mark(StartupCode.OWNER_AUTH)
            self.development_auth=CloudAuth(store,config.origin,config.login,config.verifier)
            self.member_auth=None;self.member_context=None;self.entitlements=None;self.recovery_auth=None
            if getattr(config,'member_provider',None) or member_provider:
                from packages.cloud.member_auth import MemberAuth,SupabaseAuthProvider
                startup.mark(StartupCode.MEMBER_SCHEMA)
                verify_member_schema(store)
                startup.mark(StartupCode.MEMBER_AUTH)
                self.member_auth=MemberAuth(store,config.origin,config.state_key,member_provider or SupabaseAuthProvider(config.member_provider))
                if getattr(config,'member_recovery',False):
                    startup.mark(StartupCode.RECOVERY_SCHEMA)
                    with store.transaction():store.db.execute('SELECT request_key,identity_key,issuer,auth_epoch,start_ticket,expires_at,phase,secret_ciphertext,tenant,subject,access_expires_at,operation_key,reset_generation,bound_generation,attempts,outcome FROM member_recovery LIMIT 0').fetchall()
                    startup.mark(StartupCode.RECOVERY_AUTH)
                    from packages.cloud.recovery import RecoveryAuth
                    self.recovery_auth=RecoveryAuth(self.member_auth,config.state_key)
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
                qwen=getattr(c,'provider_id','deepseek')=='qwen'
                if qwen and trial:raise ValueError('Qwen guest trial is not authorized')
                budget=(QwenMonthlyBudget(store,c) if c.monthly else QwenCloudBudget(store,c)) if qwen else TrialBudget(store,c,trial) if trial else CloudBudget(store,c)
                if trial:self.trial_auth=TrialAuth(config.origin,config.state_key,budget)
                startup.mark(StartupCode.PROVIDER_ADAPTER)
                adapter=adapter or create_adapter(c,deepseek_factory=DeepSeekAdapter,wall_timeout=PROVIDER_WALL_SECONDS,request_deadline=request_deadline)
                self.live_chat_service=LiveChat(c,budget,adapter,cancellation_factory=lambda identity:TrialCancellation(DurableCancellation(store,identity),budget) if trial else DurableCancellation(store,identity))
            self.configuration={'configured':True,'provider_enabled':config.provider is not None}
            if getattr(config,'selected_provider','deepseek')=='qwen':
                self.configuration['provider']='qwen'
                if config.provider and config.provider.smoke:
                    self.configuration['owner_smoke_only']=not (config.provider.monthly and self.live_chat_service.budget.smoke_ready())
                if config.provider and config.provider.monthly:self.configuration['owner_only']=True
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
        qwen=getattr(self.cloud_config,'selected_provider','deepseek')=='qwen'
        self.entitlements=(QwenEntitlements if qwen else Entitlements)(self.stores.persistent)
        self.controllers={};self.lifecycle.recover()
        service=self.live_chat_service
        # The separately authorized public trial never grants member spending.
        if service and not self.trial_auth and not getattr(service.config,'smoke',None) and not getattr(service.config,'monthly',None):
            budget=(QwenMemberBudget if qwen else MemberBudget)(service.budget,self.entitlements,self.member_auth,session_key,'CONVERSATION')
            self.live_chat_service=LiveChat(service.config,budget,service.adapter,cancellation_factory=lambda identity:MemberCancellation(DurableCancellation(self.stores.persistent,identity),self.member_auth,session_key,self.entitlements,'CONVERSATION'))
        else:self.live_chat_service=None
        return principal.tenant
    def member_status(self,cookie):
        if self.member_auth is None:return {'available':False,'authenticated':False}
        try:
            principal=self.member_auth.require(cookie)
        except Fault as error:
            if error.status==401:return {'available':True,'authenticated':False,'renewable':self.member_auth.renewable(cookie),'recovery_available':self.recovery_auth is not None}
            raise
        from packages.cloud.entitlements import Entitlements
        qwen=getattr(self.cloud_config,'selected_provider','deepseek')=='qwen'
        smoke_only=bool(self.live_chat_service and (getattr(self.live_chat_service.config,'smoke',None) or getattr(self.live_chat_service.config,'monthly',None)))
        rights=({'enabled':False,'temporary':False,'persistent':False,'reason':'千问人民币额度尚未启用'}
                if qwen and (self.live_chat_service is None or smoke_only) else
                (QwenEntitlements if qwen else Entitlements)(self.stores.persistent).status())
        return {'available':True,'authenticated':True,'expires_at':principal.expires_at,
                'account_scope':principal.tenant,
                'renewable':True,
                'entitlements':rights,'model_enabled':self.live_chat_service is not None and not self.trial_auth and not smoke_only}
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
    request_deadline=time.monotonic()+REQUEST_PROVIDER_DEADLINE_SECONDS
    env=os.environ if env is None else env
    # Fail closed; never select local SQLite/mock on a cloud setup error.
    startup=StartupDiagnostics()
    try:
        startup.mark(StartupCode.CONFIG)
        config=CloudConfig.from_env(env)
        return CloudApplication(config,runtime=env.get('HCL_DEVELOPMENT_ARTIFACT','.hcla-runtime'),startup=startup,request_deadline=request_deadline)
    except Exception:
        startup.report()
        return Unconfigured()
