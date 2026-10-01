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

class CloudStores(Stores):
    def conversation(self,tenant,**kwargs):
        if kwargs.get('memory')=='TEMPORARY': raise Fault(409,'Temporary conversations use the request-bound tab-memory route')
        return self.persistent.conversation(tenant,**kwargs)

class CloudApplication:
    cloud=True
    request_bound=True
    real_chat=True
    def __init__(self,config,*,store=None,adapter=None,runtime=None):
        self.cloud_config=config
        self.stores=CloudStores(store or PostgresLedger(config.database_url))
        self.development_auth=CloudAuth(self.stores.persistent,config.origin,config.login,config.verifier)
        self.configuration={'configured':True,'provider_enabled':config.provider is not None}
        self.development_bridge=RuntimeBridge(Path(runtime).absolute()) if runtime else None
        self.controllers={};self.lifecycle=Lifecycle(self.stores.persistent)
        self.lifecycle.recover()
        self.live_chat_service=None
        if config.provider:
            c=config.provider
            budget=CloudBudget(self.stores.persistent,c)
            adapter=adapter or DeepSeekAdapter(base_url=c.base_url,model=c.model,api_key=c.api_key,wall_timeout=60)
            self.live_chat_service=LiveChat(c,budget,adapter,cancellation_factory=lambda identity:DurableCancellation(self.stores.persistent,identity))
    def controller(self,store):
        if store not in self.controllers:
            # Persistent bodies never enter the volatile-only HCL bridge.
            self.controllers[store]=Controller(store,live_chat_service=self.live_chat_service)
        return self.controllers[store]
    def start(self,ctrl,tenant,run): return run
    def execute(self,tenant,run_id):
        store=self.stores.persistent;ctrl=self.controller(store)
        with store.transaction():
            run=ctrl.read(tenant,run_id)
            if not run['pending']: return run
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
    store=None
    try:
        config=CloudConfig.from_env(env)
        store=PostgresLedger(config.database_url)
        return CloudApplication(config,store=store,runtime=env.get('HCL_DEVELOPMENT_ARTIFACT','.hcla-runtime'))
    except Exception:
        if store is not None:store.close()
        return Unconfigured()
