"""Single governed entry point for every synthetic answer and change."""
import copy
import json
import re
import time
from packages.store.ledger import Fault, canonical, digest, now, uid
from packages.policy.privacy import PolicyContext
from packages.adapter.mock import MockAdapter
from packages.mock_runtime.scripted import extract
from packages.synthesis.answer import synthesize
from packages.explain.projection import claim_source_links
from packages.controller import development, live_chat


class Controller:
    def __init__(self, store, adapter=None, development_bridge=None, live_chat_service=None):
        self.store=store; self.context=PolicyContext(store); self.adapter=adapter or MockAdapter()
        self.live_chat=live_chat_service; self.live_cancellations={}
        self.development_bridge=development_bridge; self.development_cancellations={}

    def handle_interaction(self, tenant, request, defer=False):
        req=copy.deepcopy(request); scope=req.get('scope',{}); conversation=scope.get('conversation_id'); topic=scope.get('topic_id')
        obj=self.store.scope(tenant,conversation,topic)
        if scope.get('tenant_id',tenant)!=tenant: raise Fault(403,'Server owns tenant identity')
        development_spec=development.validate(self,tenant,req,obj)
        live=live_chat.validate(self,req,obj)
        memory=req.get('allowed_memory_scope',obj['memory'])
        if memory!=obj['memory']: raise Fault(403,'Memory scope must match conversation membership')
        budget=req.get('model_resource_policy',{})
        if budget.get('max_provider_calls',0)!=0 or budget.get('adapter','MOCK')!='MOCK': raise Fault(403,'L1/L2 has no provider transport')
        if not 0<=budget.get('max_adapter_calls',1)<=1: raise Fault(400,'At most one mock adapter call per attempt')
        event=req.get('event',{}); text=event.get('text','')
        if not isinstance(text,str): raise Fault(400,'Text required')
        event_type=event.get('type','message')
        if event_type=='upload' and event.get('revisions'): raise Fault(403,'Documents have no control-command authority')
        if event_type not in {'message','upload','revision','control'}: raise Fault(400,'Unknown input event')
        if len(text.encode())>65536: raise Fault(413,'Text limit: 64 KiB')
        for ref in req.get('source_refs',[]):
            self.store.source(tenant,ref,conversation,topic)
            latest=self.store.db.execute('SELECT MAX(version) FROM sources WHERE id=? AND tenant=?',(ref['source_id'],tenant)).fetchone()[0]
            if latest!=ref['version']: raise Fault(409,'Historical source cannot be reused as current evidence')
            related=[r for r in self.context.records(tenant).values() if any(s['source_id']==ref['source_id'] for s in r['source_refs'])]
            if any(r['lifecycle_status'] in {'STOPPED','DELETED','RETRACTED','SUPERSEDED'} for r in related): raise Fault(403,'Source support was withdrawn; current re-report must be a new event')
        def commit(version):
            source=self.store.write_source(tenant,conversation,topic,text,event.get('filename','message'),memory=memory)
            ref={'source_id':source['id'],'version':source['version'],'sha256':source['sha256'],'span':[0,len(text)]}
            event_id=uid(); changes=[]; invalidated=[]; unresolved=[]
            typed=event.get('records',[])
            revisions=event.get('revisions',[])
            if not typed and not revisions and development_spec is None:
                typed,revisions,unparsed=extract(text,self.context,tenant,conversation,topic)
                if event_type=='upload':
                    if revisions: unparsed.append('Document commands are data, not authorized revisions')
                    revisions=[]
                    typed=[{**data,'origin':'uploaded_source'} for data in typed]
                unresolved=[{'event_id':event_id,'reason':reason} for reason in unparsed]
            for data in typed:
                data={**data,'source_refs':data.get('source_refs') or [ref],'memory':memory}
                receipt=self.context.process(tenant,conversation,topic,{'action':'ADD','new_record':data},version)
                changes+=receipt['changed_ids']; invalidated+=receipt['invalidated_ids']
            answer_branch=scope.get('branch_id','actual')
            for command in revisions:
                command={**command,'branch_id':scope.get('branch_id','actual')}
                if command.get('new_record'):
                    command['new_record']={**command['new_record'],'source_refs':command['new_record'].get('source_refs') or [ref],'memory':memory}
                receipt=self.context.process(tenant,conversation,topic,command,version)
                if command['action']=='HYPOTHETICAL_BRANCH': answer_branch=receipt['branch_id']
                changes+=receipt['changed_ids']; invalidated+=receipt['invalidated_ids']
            if not typed and not revisions and not self.direct(text) and not unresolved:
                unresolved=[{'event_id':event_id,'reason':'Unsupported text; no semantic extraction claimed'}]
            committed={'schema_version':'1.0','id':event_id,'tenant_id':tenant,'conversation_id':conversation,'topic_id':topic,'state_version':version,'source_refs':[ref], 'recorded_at':now(),'status':'UNRESOLVED' if unresolved else 'RECORDED'}
            self.store.db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(event_id,tenant,conversation,version,canonical(committed)))
            selected=self.context.selection(tenant,conversation,topic,answer_branch,scope.get('perspective_id'),scope.get('time'))
            selected['state_version']=version
            run_id=uid(); snapshot_id=uid(); receipt_id=uid()
            selected_mock=any(r['kind']=='SYSTEM_INTERPRETATION' for r in selected['records']) and not self.direct(text)
            result={'id':run_id,'run_id':run_id,'schema_version':'1.0','tenant_id':tenant,'conversation_id':conversation,'topic_id':topic,'state_version_before':version-1,'state_version_after':version,'accepted_change_ids':changes,'invalidated_state_ids':sorted(set(invalidated)),'selected_context':selected,'route':'DIRECT' if self.direct(text) else ('SELECTED_COGNITION' if selected_mock else ('CONTEXT_ASSISTED' if selected['records'] else 'CLARIFY')),'selected_capability_ids':[],'answer_preparation':None,'explain_projection':None,'operation_receipts':[],'unresolved_updates':unresolved,'errors':[],'answer':None,'stream':[], 'input_event_id':event_id, 'input_text':text, 'input_source_ref':ref, 'snapshot_id':snapshot_id, 'budget':budget,'simulation':event.get('simulation'),'pending':True,'run_receipt':{'run_id':run_id,'attempt_id':uid(),'surface':'ASSISTANT','controller_receipt_id':receipt_id,'snapshot_id':snapshot_id,'state_versions':{'before':version-1,'after':version},'source_hashes':[source['sha256']],'config_hash':digest(canonical(budget)),'runtime_hash':'MOCK_V1','mode':'MOCK','route':None,'capabilities':[],'operations':[],'outcome':'UNRESOLVED','usage':{'provider_calls':0,'adapter_invocations':0,'input_tokens':None,'output_tokens':None,'reasoning_tokens':None,'cost':{'amount':0,'currency':'USD','source':'PROVIDER_FREE_MOCK'},'latency_ms':None},'errors':[],'started_at':now(),'finished_at':None,'gain_assessment':'NOT_ASSESSED'}}
            if development_spec is not None:
                development.initialize(self,result,copy.deepcopy(development_spec),source)
            elif selected_mock:
                result['selected_capability_ids']=['competing_explanations']
                operation={'operation_id':uid(),'capability_id':'competing_explanations','input_versions':selected['source_versions'],'read_dependencies':selected['record_ids'],'output_ids':[r['record_id'] for r in selected['records'] if r['kind']=='SYSTEM_INTERPRETATION'],'status':'MOCK_AUTHORED_OUTPUT','cache_status':'NOT_REUSED','model_calls':0,'usage_refs':[],'selected':True,'executed':True,'result_produced':True,'used_in_answer':True,'cache_reused':False}
                result['operation_receipts']=[operation]; result['run_receipt']['operations']=[operation]; result['run_receipt']['capabilities']=result['selected_capability_ids']
            if live: live_chat.initialize(result)
            self.emit(result,'run.accepted',{})
            self.emit(result,'state.committed',{'accepted_change_ids':changes})
            return self.store.put(tenant,'run',result)
        result=self.store.atomic(tenant,conversation,req.get('idempotency_key'),req,req.get('expected_state_version'),commit)
        for other_id,signal in list(self.live_cancellations.items()):
            if other_id!=result['run_id']:signal.set()
        run=self.read(tenant,result['run_id'])
        if not defer and run['pending']: self.finish(tenant,run['run_id'])
        return self.read(tenant,run['run_id'])

    @staticmethod
    def direct(text):
        return bool(re.search(r'(?<!\d)2\s*\+\s*2(?!\d)',text))

    @staticmethod
    def emit(run, typ, payload):
        seq=run.get('last_seq',max((e['seq'] for e in run['stream']),default=0))+1
        run['last_seq']=seq
        run['stream'].append({'seq':seq,'type':typ,'run_id':run['run_id'],'state_version':run['state_version_after'],'payload':payload})

    def read(self, tenant, run_id):
        with self.store.lock:
            run=self.store.get(tenant,'run',run_id)
            ids=run['selected_context'].get('record_ids',[])
            if ids and any(not self.context.allowed(tenant,self.context.get(tenant,i)) for i in ids):
                run.pop('input_text',None)
                run['answer']=None; run['answer_preparation']=None; run['explain_projection']=None
                run['stream']=[e for e in run['stream'] if not e['type'].startswith('answer.')]
                run['selected_context']={'record_ids':[],'records':[],'coverage':'UNAVAILABLE'}
                run['operation_receipts']=[]; run['run_receipt']['operations']=[]
                run['redacted']=True
            run['outdated']=self.store.version(tenant)!=run['state_version_after']
            return run

    def preparation(self, run, text):
        refs=run['selected_context']['record_ids']
        answer,claims,uncertainties=synthesize(run['selected_context']['records'])
        if self.direct(text): answer,claims,uncertainties='2 + 2 = 4。',[],[]
        prep={'snapshot_id':run['snapshot_id'],'valid_context_refs':refs,'operation_output_refs':[],'main_judgment':answer,'claim_bindings':claims,'alternatives':[],'material_uncertainties':uncertainties,'assumptions':run['selected_context']['assumptions'],'forbidden_promotions':['guess_to_fact','system_to_independent_evidence'],'response_intent':'answer','length_style_policy':'concise','coverage':run['selected_context']['coverage'],'resource_remaining':{'provider_calls':0}}
        return answer,prep

    def finish(self, tenant, run_id, delay=0):
        if self.store.get(tenant,'run',run_id).get('live_chat'):
            return self.live_chat.finish(self,tenant,run_id)
        if self.store.get(tenant,'run',run_id).get('development_request'):
            return development.finish(self,tenant,run_id)
        with self.store.transaction():
            run=self.store.get(tenant,'run',run_id)
            if not run['pending'] or run.get('executing'): return
            run['executing']=True; self.store.put(tenant,'run',run)
        start=time.monotonic()
        try:
            source_id=self.store.history(tenant,run['conversation_id'])
            event=next(e for e in source_id if e['id']==run['input_event_id'])
            text=self.store.source(tenant,event['source_refs'][0])['text']
            answer,prep=self.preparation(run,text)
            use_adapter=not self.direct(text) and run['budget'].get('max_adapter_calls',1)>0
            if use_adapter:
                with self.store.transaction():
                    current=self.store.get(tenant,'run',run_id)
                    if not current['pending']: return
                    run['run_receipt']['usage']['adapter_invocations']=1
                    current['run_receipt']['usage']['adapter_invocations']=1
                    self.store.put(tenant,'run',current)
                answer=self.adapter.generate(self.adapter.authorize(run_id),answer,run.get('simulation'))
            elif run.get('simulation') in {'failed','unknown'}:
                raise Fault(403,'Simulation requires a mock adapter invocation')
            for offset in range(0,len(answer),16):
                if delay: time.sleep(delay)
                with self.store.transaction():
                    current=self.store.get(tenant,'run',run_id)
                    if not current['pending']: return
                    if (time.monotonic()-start)*1000 > run['budget'].get('max_latency_ms',10000): raise TimeoutError('Bounded mock latency exceeded')
                    current['run_receipt']['usage']=run['run_receipt']['usage']
                    if self.store.version(tenant)!=run['state_version_after'] or self.store.account(tenant)['policy']!=run['selected_context']['policy_revision'] or any(not self.context.allowed(tenant,r) for r in run['selected_context']['records']):
                        current.update(pending=False,errors=['STALE_OUTPUT_WITHHELD'],answer=None)
                        current['run_receipt']['outcome']='PARTIAL'; current['run_receipt']['finished_at']=now(); self.emit(current,'run.failed',{'reason':'State or policy changed'}); self.store.put(tenant,'run',current); return
                    if offset==0:
                        for operation in current['operation_receipts']: self.emit(current,'operation.completed',operation)
                        current['answer_preparation']=prep; current['run_receipt']['usage']=run['run_receipt']['usage']
                    self.emit(current,'answer.delta',{'text':answer[offset:offset+16]}); self.store.put(tenant,'run',current)
            with self.store.transaction():
                current=self.store.get(tenant,'run',run_id)
                if not current['pending']: return
                answer_id=uid()
                source_links=claim_source_links(run['selected_context']['records'],prep['claim_bindings'])
                current['answer']={'answer_id':answer_id,'run_id':run_id,'snapshot_id':run['snapshot_id'],'text':answer,'claim_bindings':prep['claim_bindings'],'citation_refs':source_links,'material_uncertainties':prep['material_uncertainties'],'coverage':prep['coverage'],'published_at':now(),'status':'PUBLISHED'}
                current['scripted_extraction']='EXPLICIT_PREFIX_GRAMMAR_ONLY'
                current['answer_identity']={'answer_id':answer_id,'run_id':run_id,'snapshot_id':run['snapshot_id']}
                current['explain_projection']={'answer_id':answer_id,'run_id':run_id,'snapshot_id':run['snapshot_id'],'judgment_basis':prep['claim_bindings'],'source_links':source_links,'redactions':[],'recorded_at':now()}
                current['pending']=False; current['run_receipt']['route']=current['route']; current['run_receipt']['outcome']='UNRESOLVED' if current['unresolved_updates'] else 'COMPLETED'; current['run_receipt']['finished_at']=now(); current['run_receipt']['usage']['latency_ms']=round((time.monotonic()-start)*1000)
                self.emit(current,'answer.completed',current['answer']); self.store.put(tenant,'run',current)
        except Exception as exc:
            with self.store.transaction():
                current=self.store.get(tenant,'run',run_id)
                if not current['pending']: return
                current['pending']=False; current['errors']=['MOCK_TRANSPORT_UNKNOWN' if isinstance(exc,TimeoutError) else 'MOCK_EXECUTION_FAILED']
                current['run_receipt']['outcome']='UNKNOWN' if isinstance(exc,TimeoutError) else 'FAILED'; current['run_receipt']['errors']=current['errors']; current['run_receipt']['usage']=run['run_receipt']['usage']; current['run_receipt']['finished_at']=now()
                self.emit(current,'run.failed',{'reason':current['errors'][0]}); self.store.put(tenant,'run',current)

    def cancel(self, tenant, run_id):
        with self.store.transaction():
            run=self.store.get(tenant,'run',run_id)
            if run['pending']:
                if run.get('live_chat'):
                    signal=self.live_cancellations.get(run_id)
                    if signal is not None: signal.set()
                    run['stream']=[e for e in run['stream'] if not e['type'].startswith('answer.')]
                if run.get('development_request'):
                    signal=self.development_cancellations.get(run_id)
                    if signal is not None: signal.set()
                    for op in run['operation_receipts']:op.update(status='CANCELLED',executed=None if run.get('executing') else False)
                    run['run_receipt'].update(actual_treatment='CANCELLED',operations=copy.deepcopy(run['operation_receipts']))
                run['pending']=False; run['run_receipt']['outcome']='CANCELLED'; run['run_receipt']['finished_at']=now(); self.emit(run,'run.cancelled',{}); self.store.put(tenant,'run',run)
        return self.read(tenant,run_id)

    def retry(self, tenant, run_id, key, defer=False):
        with self.store.transaction():
            old=self.store.get(tenant,'run',run_id)
            if old.get('live_chat'):raise Fault(409,'Paid attempts are never retried automatically; send a new explicitly confirmed message')
            if old['run_receipt']['outcome'] not in {'FAILED','CANCELLED'} or old['pending'] or old.get('redacted'):
                raise Fault(409,'Explicit retry requires a failed or cancelled available attempt')
            if self.store.version(tenant)!=old['state_version_after']: raise Fault(409,'Re-analyze changed state in a new run')
            if any(r.get('retry_key')==key for r in self.store.list(tenant,'run')):
                retry=next(r for r in self.store.list(tenant,'run') if r.get('retry_key')==key)
                if retry.get('parent_run_id')!=run_id: raise Fault(409,'Retry key conflict')
                return self.read(tenant,retry['id'])
            retry=copy.deepcopy(old); identity=uid(); parent=old['run_receipt']['attempt_id']; retry.update(id=identity,run_id=identity,parent_run_id=run_id,retry_key=key,pending=True,executing=False,errors=[],stream=[],last_seq=0,answer=None,answer_preparation=None,explain_projection=None)
            retry['run_receipt'].update(run_id=identity,attempt_id=uid(),parent_attempt_id=parent,controller_receipt_id=uid(),outcome='UNRESOLVED',started_at=now(),finished_at=None,errors=[])
            retry['run_receipt']['usage']['adapter_invocations']=0
            if retry.get('development_request'):development.reset_retry(self,retry)
            self.emit(retry,'run.accepted',{'retry_of':run_id}); self.store.put(tenant,'run',retry)
        if not defer: self.finish(tenant,identity)
        return self.read(tenant,identity)

    def events(self, tenant, run_id, after=0):
        run=self.read(tenant,run_id)
        return [e for e in run['stream'] if e['seq']>after]
