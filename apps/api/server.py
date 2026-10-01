"""Loopback-only synthetic HTTP/SSE API. Not production authentication."""
import argparse
import base64
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse
from packages.store.ledger import Ledger, Fault, now
from packages.store.registry import Stores
from packages.controller.interaction import Controller
from packages.explain.projection import project
from packages.explain.product import conversation as conversation_view, search as history_search
from packages.controller.lab import inspect
from packages.store.pagination import page
from packages.runtime_bridge.bridge import RuntimeBridge


class Application:
    def __init__(self, path=':memory:', development_runtime_directory=None, live_chat_service=None, development_auth=None, real_chat=False, configuration=None):
        self.live_chat_service=live_chat_service;self.development_auth=development_auth;self.real_chat=real_chat;self.configuration=configuration or {}
        self.development_bridge=RuntimeBridge(development_runtime_directory) if development_runtime_directory is not None else None
        self.stores=Stores(Ledger(path)); self.controllers={}; self.lock=threading.RLock()
        store=self.stores.persistent
        with store.transaction():
            for account in store.db.execute('SELECT tenant FROM accounts').fetchall():
                tenant=account['tenant']
                for run in store.list(tenant,'run'):
                    if run['pending']:
                        run['pending']=False; run['errors']=['PROCESS_RESTART_UNKNOWN']; run['run_receipt'].update(outcome='UNKNOWN',errors=run['errors'],finished_at=now())
                        if run.get('executing'): run['run_receipt']['usage']['adapter_invocations']=None
                        Controller.emit(run,'run.failed',{'reason':'Process restart; transport not automatically repeated'})
                        store.put(tenant,'run',run)

    def controller(self, store):
        with self.lock:
            if store not in self.controllers: self.controllers[store]=Controller(store,development_bridge=self.development_bridge,live_chat_service=self.live_chat_service)
            return self.controllers[store]

    def start(self, ctrl, tenant, run):
        if run['pending']:
            threading.Thread(target=ctrl.finish,args=(tenant,run['run_id'],0.08),daemon=True).start()
        return run

    def close(self):
        self.stores.persistent.close(); self.stores.temporary.close()


def handler(application):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass  # Never log user bodies or request URLs.

        def tenant(self):
            if application.real_chat:
                if application.development_auth is None:raise Fault(503,'Development configuration required')
                application.development_auth.boundary(self,mutation=self.command=='POST')
                return application.development_auth.require(self.headers.get('Cookie'))
            origin=self.headers.get('Origin')
            if origin and origin not in {'http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:'+str(self.server.server_port),'http://localhost:'+str(self.server.server_port)}: raise Fault(403,'Synthetic API accepts only loopback app origins')
            identity=self.headers.get('X-Synthetic-Identity','demo-a')
            if identity not in {'demo-a','demo-b'}: raise Fault(401,'Synthetic test identity required')
            return 'synthetic-'+identity

        def body(self):
            length=int(self.headers.get('Content-Length','0'))
            if length>262144: raise Fault(413,'Request too large')
            try: obj=json.loads(self.rfile.read(length))
            except (ValueError,UnicodeError): raise Fault(400,'Invalid complete JSON')
            if not isinstance(obj,dict): raise Fault(400,'JSON object required')
            return obj

        def json(self, status, obj, cookie=None):
            payload=json.dumps(obj,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(payload)));
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers(); self.wfile.write(payload)

        def do_POST(self):
            try:
                path=urlparse(self.path).path
                if path=='/v1/development/login' and application.real_chat:
                    if application.development_auth is None:raise Fault(503,'Development configuration required')
                    application.development_auth.boundary(self,mutation=True)
                    session=application.development_auth.login(self.body().get('access_token'))
                    self.json(200,{'authenticated':True},'hcla_development='+session+'; HttpOnly; SameSite=Strict; Path=/v1; Max-Age=3600');return
                tenant=self.tenant(); data=self.body(); parts=path.strip('/').split('/')
                if path=='/v1/topics': result=application.stores.persistent.topic(tenant,data.get('title','Topic'))
                elif path=='/v1/conversations': result=application.stores.conversation(tenant,title=data.get('title','新对话'),topic_id=data.get('topic_id'),memory=data.get('memory','CONVERSATION'))
                elif len(parts)==4 and parts[:2]==['v1','conversations'] and parts[3]=='events':
                    store=application.stores.for_conversation(tenant,parts[2]); ctrl=application.controller(store)
                    data.setdefault('scope',{})['conversation_id']=parts[2]
                    if application.real_chat and data.get('event',{}).get('type','message') in {'message','upload'}:data['development_chat']=True
                    result=application.start(ctrl,tenant,ctrl.handle_interaction(tenant,data,defer=True))
                elif path=='/v1/sources':
                    conversation=data['scope']['conversation_id']; store=application.stores.for_conversation(tenant,conversation); ctrl=application.controller(store)
                    data.setdefault('event',{})['type']='upload'
                    if application.real_chat:data['development_chat']=True
                    result=application.start(ctrl,tenant,ctrl.handle_interaction(tenant,data,defer=True))
                elif len(parts)==4 and parts[:2]==['v1','runs'] and parts[3] in {'cancel','retry'}:
                    ctrl=application.controller(application.stores.for_run(tenant,parts[2]))
                    result=ctrl.cancel(tenant,parts[2]) if parts[3]=='cancel' else application.start(ctrl,tenant,ctrl.retry(tenant,parts[2],data['idempotency_key'],defer=True))
                else: raise Fault(404,'Unknown API route')
                self.json(200,result)
            except Fault as exc: self.json(exc.status,{'error':str(exc)})
            except (KeyError,TypeError,ValueError): self.json(400,{'error':'Malformed request'})
            except Exception: self.json(500,{'error':'Internal failure; not a completed run'})

        def do_GET(self):
            try:
                if urlparse(self.path).path=='/v1/development/status':
                    authenticated=False
                    if application.real_chat and application.development_auth:
                        application.development_auth.boundary(self)
                        try:application.development_auth.require(self.headers.get('Cookie'));authenticated=True
                        except Fault:pass
                    self.json(200,{'enabled':application.real_chat,'authenticated':authenticated,'configuration':application.configuration,'production_enabled':False});return
                tenant=self.tenant(); parsed=urlparse(self.path); query=parse_qs(parsed.query); path=parsed.path; parts=path.strip('/').split('/')
                if path=='/v1/development/runtime':
                    result=application.development_bridge.handshake() if application.development_bridge is not None else {'handshake_status':'FAILED','errors':['DEVELOPMENT_BRIDGE_NOT_CONFIGURED'],'production_enabled':False}
                elif path=='/v1/conversations': result=application.stores.conversations(tenant)
                elif path=='/v1/topics': result=application.stores.persistent.list(tenant,'topic')
                elif path=='/v1/history/search': result=history_search(application,tenant,query.get('q',[''])[0])
                elif len(parts)==3 and parts[:2]==['v1','conversations']:
                    store=application.stores.for_conversation(tenant,parts[2]); c=store.get(tenant,'conversation',parts[2]); ctrl=application.controller(store)
                    result=conversation_view(ctrl,tenant,c['id'])
                elif len(parts)==3 and parts[:2]==['v1','runs']:
                    ctrl=application.controller(application.stores.for_run(tenant,parts[2])); result=ctrl.read(tenant,parts[2])
                elif len(parts)==4 and parts[:2]==['v1','runs'] and parts[3]=='events':
                    ctrl=application.controller(application.stores.for_run(tenant,parts[2])); ctrl.read(tenant,parts[2])
                    after=int(self.headers.get('Last-Event-ID',query.get('after',['0'])[0]))
                    self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.send_header('Cache-Control','no-store'); self.end_headers()
                    deadline=time.monotonic()+(50 if application.real_chat else 10)
                    try:
                        while time.monotonic()<deadline:
                            for event in ctrl.events(tenant,parts[2],after):
                                self.wfile.write(('id: '+str(event['seq'])+'\ndata: '+json.dumps(event,ensure_ascii=False)+'\n\n').encode()); self.wfile.flush(); after=event['seq']
                            if not ctrl.read(tenant,parts[2])['pending']: return
                            time.sleep(.03)
                    except (BrokenPipeError,ConnectionResetError): pass
                    return
                elif len(parts)==4 and parts[:2]==['v1','lab'] and parts[2] in {'runs','export'}:
                    ctrl=application.controller(application.stores.for_run(tenant,parts[3])); result=inspect(ctrl,tenant,parts[3])
                elif len(parts)==4 and parts[:2]==['v1','answers'] and parts[3]=='explain':
                    result=None
                    for store in [application.stores.persistent,application.stores.temporary]:
                        ctrl=application.controller(store)
                        for r in store.list(tenant,'run'):
                            identity=r.get('answer_identity') or r.get('answer') or {}
                            if identity.get('answer_id')==parts[2]:
                                result=project(ctrl.read(tenant,r['id']))
                    if result is None: result={'redactions':['UNAVAILABLE'],'judgment_basis':[],'source_links':[]}
                elif path=='/v1/context':
                    conversation=query['conversation_id'][0]; store=application.stores.for_conversation(tenant,conversation); c=store.get(tenant,'conversation',conversation)
                    context=application.controller(store).context
                    result=context.selection(tenant,conversation,c['topic_id'])
                    if query.get('manage')==['1']:
                        managed=[]
                        for record in context.records(tenant).values():
                            try: context.check_scope(record,conversation,c['topic_id'])
                            except Fault: continue
                            if record['lifecycle_status']!='DELETED': managed.append(record)
                        result['managed_records']=managed
                        sources={}
                        for row in store.db.execute('SELECT body FROM sources WHERE tenant=? ORDER BY version',(tenant,)):
                            source=json.loads(row['body'])
                            if source['conversation_id']==conversation and not source['deleted']: sources[source['id']]=source
                        result['managed_sources']=list(sources.values())
                elif len(parts)==3 and parts[:2]==['v1','sources']:
                    conversation=query['conversation_id'][0]; store=application.stores.for_conversation(tenant,conversation); c=store.get(tenant,'conversation',conversation)
                    ref={'source_id':parts[2],'version':int(query['version'][0]),'sha256':query['sha256'][0]}; result=store.source(tenant,ref,conversation,c['topic_id'],allow_stopped=True)
                else: raise Fault(404,'Unknown API route')
                if 'limit' in query and path in {'/v1/conversations','/v1/topics'}:
                    account=application.stores.persistent.account(tenant)
                    result=page(result,tenant,account['version'],account['policy'],int(query['limit'][0]),query.get('cursor',[None])[0],path)
                self.json(200,result)
            except Fault as exc: self.json(exc.status,{'error':str(exc)})
            except (KeyError,TypeError,ValueError): self.json(400,{'error':'Malformed query'})
            except Exception: self.json(500,{'error':'Internal failure'})
    return Handler


def serve(application, port=8765):
    return ThreadingHTTPServer(('127.0.0.1',port),handler(application))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8765); parser.add_argument('--database',default=':memory:'); parser.add_argument('--development-runtime-directory',default=os.environ.get('HCL_DEVELOPMENT_ARTIFACT')); args=parser.parse_args()
    app=Application(args.database,args.development_runtime_directory); server=serve(app,args.port)
    try: server.serve_forever()
    finally: server.server_close(); app.close()
