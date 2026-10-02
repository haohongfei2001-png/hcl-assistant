"""Same Controller/Bridge, with temporary bodies only in request and tab RAM.

The signed snapshot is returned to browser memory, never to a database/cookie/
localStorage. A body-free Postgres head prevents replay of pre-deletion snapshots.
If a connection dies before the new snapshot reaches the tab, that temporary
conversation cannot be recovered. A new conversation is explicit, never a retry.
"""
import hashlib
import hmac
import json
import re
import time
from packages.store.ledger import Ledger,Fault,canonical,digest
from packages.controller.interaction import Controller
from packages.controller.live_chat import LiveChat
from packages.explain.product import conversation as conversation_view
from packages.explain.projection import project
from packages.controller.lab import inspect
from packages.cloud.lifecycle import DurableCancellation

SYNTHETIC_TENANT='synthetic-demo-a'  # Fixture tag, only after actual owner auth.
TABLES={'accounts':('tenant','version','policy'),'objects':('id','tenant','type','body'),
        'sources':('id','tenant','version','body'),'events':('id','tenant','conversation','version','body'),
        'idempotency':('tenant','conversation','key','hash','result'),'records':('id','tenant','version','body'),'tombstones':('id','tenant')}
MAX_STATE_BYTES=700000

def member_execution_key(application,request_id):
    if not isinstance(request_id,str) or not re.fullmatch(r'[a-f0-9-]{36}',request_id):raise Fault(400,'Request identifier required')
    tenant,session_key=application.member_context
    return digest('member-temporary\n'+tenant+'\n'+session_key+'\n'+request_id)

def pack(store,key,session,conversation,revision):
    state={'conversation':conversation,'revision':revision,'expires':int(time.time())+3600,
           'tables':{table:[dict(r) for r in store.db.execute('SELECT * FROM '+table)] for table in TABLES}}
    payload=canonical(state)
    if len(payload.encode())>MAX_STATE_BYTES: raise Fault(413,'Temporary conversation is full; start a new conversation')
    signature=hmac.new(bytes.fromhex(key),(session+'\n'+payload).encode(),hashlib.sha256).hexdigest()
    return {'state':state,'signature':signature}

def unpack(snapshot,key,session,conversation):
    if not isinstance(snapshot,dict) or set(snapshot)!={'state','signature'}: raise Fault(409,'Temporary state unavailable')
    payload=canonical(snapshot['state'])
    if len(payload.encode())>MAX_STATE_BYTES: raise Fault(413,'Temporary state limit')
    expected=hmac.new(bytes.fromhex(key),(session+'\n'+payload).encode(),hashlib.sha256).hexdigest()
    if not isinstance(snapshot['signature'],str) or not hmac.compare_digest(expected,snapshot['signature']): raise Fault(403,'Temporary state verification failed')
    state=snapshot['state']
    if state['conversation']!=conversation or state['expires']<time.time(): raise Fault(409,'Temporary conversation expired')
    store=Ledger()
    try:
        with store.transaction():
            for table,columns in TABLES.items():
                for row in state['tables'][table]:
                    if set(row)!=set(columns): raise Fault(403,'Invalid temporary state')
                    store.db.execute('INSERT INTO '+table+'('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',tuple(row[c] for c in columns))
        return store
    except BaseException: store.close();raise

class StreamingLedger(Ledger):
    pass

def projections(ctrl,conversation):
    tenant=SYNTHETIC_TENANT;store=ctrl.store
    view=conversation_view(ctrl,tenant,conversation)
    context=ctrl.context.selection(tenant,conversation,None)
    context['managed_records']=[r for r in ctrl.context.records(tenant).values() if r['lifecycle_status']!='DELETED']
    sources={}
    for row in store.db.execute('SELECT body FROM sources WHERE tenant=? ORDER BY version',(tenant,)):
        source=json.loads(row['body'])
        if not source['deleted']: sources[source['id']]=source
    context['managed_sources']=list(sources.values())
    return {'view':view,'context':context,'sources':list(sources.values()),
            'explains':{r['answer']['answer_id']:project(r) for r in view['runs'] if r.get('answer')},
            'inspections':{r['run_id']:inspect(ctrl,tenant,r['run_id']) for r in view['runs']}}

def execute(application,handler,data,*,guest_session=None):
    # The outer API has already authenticated HTTPS owner identity and CSRF.
    member=getattr(application,'member_context',None)
    if member is not None:
        principal=application.member_auth.require(handler.headers.get('Cookie'))
        if principal.tenant!=member[0] or application.member_auth.key(handler.headers.get('Cookie'))!=member[1]:raise Fault(403,'Account changed during request')
        if getattr(application,'trial_auth',None) is not None:raise Fault(403,'Public trial cannot grant account model access')
        application.entitlements.require('TEMPORARY')
        session='member\n'+member[0]+'\n'+member[1]
    elif guest_session is None:
        if getattr(application,'trial_auth',None) is not None:raise Fault(403,'Trial requires the isolated guest temporary route')
        auth=application.development_auth
        auth.require(handler.headers.get('Cookie'))
        session=auth.key(handler.headers.get('Cookie'))
    else:
        session=application.trial_auth.require(handler.headers.get('Cookie'))
        if session!=guest_session:raise Fault(403,'Temporary trial session changed')
    conversation=data.get('conversation_id');request_id=data.get('request_id');request=data.get('request')
    if not isinstance(conversation,str) or not re.fullmatch(r'temp-[a-f0-9-]{36}',conversation): raise Fault(400,'Temporary conversation identifier required')
    if not isinstance(request_id,str) or not re.fullmatch(r'[a-f0-9-]{36}',request_id): raise Fault(400,'Request identifier required')
    if guest_session is not None:request_id=application.trial_auth.execution_key(session,request_id)
    if member is not None:request_id=member_execution_key(application,request_id)
    if not isinstance(request,dict): raise Fault(400,'Temporary request required')
    if request.get('scope',{}).get('conversation_id')!=conversation or request.get('scope',{}).get('topic_id') is not None or request.get('allowed_memory_scope')!='TEMPORARY': raise Fault(403,'Temporary scope mismatch')
    if request.get('development_execution') and application.development_bridge is None: raise Fault(503,'Reviewed development bridge unavailable')
    if application.live_chat_service is None and request.get('event',{}).get('type','message') in {'message','upload'}: raise Fault(503,'Owner has not activated a new model budget')
    key=application.cloud_config.state_key;snapshot=data.get('snapshot')
    store=unpack(snapshot,key,session,conversation) if snapshot else Ledger()
    persistent=application.stores.persistent
    head_key=digest(session+'\n'+conversation);payload_hash=digest(canonical(data))
    try:
        if snapshot is None:
            with store.transaction():
                store.account(SYNTHETIC_TENANT)
                store.put(SYNTHETIC_TENANT,'conversation',{'id':conversation,'title':'临时对话','topic_id':None,'memory':'TEMPORARY'})
        cancellation=DurableCancellation(persistent,request_id,temporary=True)
        if guest_session is not None:
            from packages.cloud.trial import TrialCancellation
            cancellation=TrialCancellation(cancellation,application.trial_auth.budget)
        service=application.live_chat_service
        if member is not None:
            from packages.cloud.entitlements import MemberBudget,MemberCancellation
            cancellation=MemberCancellation(cancellation,application.member_auth,member[1],application.entitlements,'TEMPORARY')
            if service:
                budget=type(service.budget)(service.budget.operator,application.entitlements,application.member_auth,member[1],'TEMPORARY')
                service=LiveChat(service.config,budget,service.adapter)
        live=LiveChat(service.config,service.budget,service.adapter,cancellation_factory=lambda _:cancellation) if service else None
        ctrl=Controller(store,development_bridge=application.development_bridge,live_chat_service=live)
        request=dict(request)
        if request.get('event',{}).get('type','message') in {'message','upload'}: request['development_chat']=True
        run=ctrl.handle_interaction(SYNTHETIC_TENANT,request,defer=True)
        with persistent.transaction():
            head=persistent.db.execute('SELECT * FROM temporary_heads WHERE conversation_key=?',(head_key,)).fetchone()
            if snapshot is not None and (head is None or head['snapshot_hash']!=digest(canonical(snapshot))): raise Fault(409,'Temporary state changed or was interrupted; start a new conversation')
            if snapshot is None and head is not None: raise Fault(409,'Temporary conversation already started')
            owner=application.lifecycle.claim(request_id,payload_hash,temporary=True)
            if owner is None: raise Fault(409,'Temporary request already consumed; it is never automatically repeated')
            revision=(head['revision'] if head else 0)+1
            if head is None:
                if member is None:persistent.db.execute('INSERT INTO temporary_heads(conversation_key,revision,snapshot_hash) VALUES(?,?,NULL)',(head_key,revision))
                else:persistent.db.execute('INSERT INTO temporary_heads(conversation_key,tenant,revision,snapshot_hash) VALUES(?,?,?,NULL)',(head_key,member[0],revision))
            else: persistent.db.execute('UPDATE temporary_heads SET revision=?,snapshot_hash=NULL WHERE conversation_key=?',(revision,head_key))
        persistent.fence=(request_id,owner)
        handler.send_response(200);handler.send_header('Content-Type','text/event-stream');handler.send_header('Cache-Control','no-store');handler.send_header('X-Accel-Buffering','no');handler.end_headers()
        disconnected=False
        def send(typ,payload):
            nonlocal disconnected
            if disconnected:return
            if (guest_session is not None or member is not None) and cancellation.is_set() and typ!='cloud.error':
                disconnected=True
                return
            try:
                handler.wfile.write(('data: '+json.dumps({'type':typ,'payload':payload},ensure_ascii=False)+'\n\n').encode());handler.wfile.flush()
            except (BrokenPipeError,ConnectionResetError):
                disconnected=True;cancellation.set()
        send('cloud.accepted',ctrl.read(SYNTHETIC_TENANT,run['run_id']))
        original_put=store.put
        def put(tenant,typ,body):
            result=original_put(tenant,typ,body)
            if typ=='run' and body['run_id']==run['run_id']: send('cloud.run',ctrl.read(tenant,run['run_id']))
            return result
        store.put=put
        try:
            ctrl.finish(SYNTHETIC_TENANT,run['run_id'])
            if guest_session is not None:application.trial_auth.budget.require_active()
            if member is not None:
                if not application.member_auth.active(member[1]):raise Fault(401,'Account session expired')
                application.entitlements.require('TEMPORARY')
            next_snapshot=pack(store,key,session,conversation,revision)
            with persistent.transaction():
                persistent.db.execute('UPDATE temporary_heads SET snapshot_hash=? WHERE conversation_key=? AND revision=?',(digest(canonical(next_snapshot)),head_key,revision))
                application.lifecycle.finish(request_id,owner)
            send('cloud.completed',{'snapshot':next_snapshot,**projections(ctrl,conversation)})
        except Exception:
            cancellation.set()
            send('cloud.error',{'error':'Temporary request interrupted; start a new conversation. No automatic provider retry.'})
    finally:
        persistent.fence=None
        store.close()
