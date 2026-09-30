"""Authored context/revision algorithms, not automatic language understanding."""
import json
from datetime import datetime
from packages.store.ledger import Fault, canonical, now, uid, locked

KINDS = {'USER_REPORTED_EVENT','USER_GUESS','CHARACTER_SELF_REPORT','THIRD_PARTY_REPORT','SYSTEM_INTERPRETATION','HYPOTHETICAL','CONDITIONAL_RULE','CORRECTION','RETRACTION'}
ACTIONS = {'ADD','CORRECT','RETRACT','SUPERSEDE','HYPOTHETICAL_BRANCH','STOP_USING','DELETE'}


class Context:
    def __init__(self, store):
        self.store=store; self.lock=store.lock

    @locked
    def records(self, tenant, version=None):
        rows=self.store.db.execute('SELECT id,version,body FROM records WHERE tenant=? ORDER BY version', (tenant,))
        latest={}
        for row in rows:
            if version is None or row['version']<=version:
                latest[row['id']]=json.loads(row['body'])
        return latest

    @locked
    def get(self, tenant, identity, version=None):
        result=self.records(tenant,version).get(identity)
        if result is None:
            raise Fault(403,'Context unavailable')
        return result

    def save(self, tenant, record, version):
        record={**record,'revision':version}
        self.store.db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(record['record_id'],tenant,version,canonical(record)))
        return record

    def add(self, tenant, conversation, topic, data, version, branch='actual'):
        membership=self.store.scope(tenant,conversation,topic)
        if data.get('memory',membership['memory'])!=membership['memory']: raise Fault(403,'Data cannot expand memory scope')
        if data.get('kind') not in KINDS or not isinstance(data.get('content'),str):
            raise Fault(400,'Typed kind and content required')
        times=[data.get('disclosure_time'),data.get('retention_policy',{}).get('expires_at')]
        times += [data.get('valid_time',{}).get(k) for k in ('start','end')]
        times += [e.get('learned_at') for e in data.get('person_access_events',[])]
        for stamp in times:
            if stamp is not None:
                try: parsed=datetime.fromisoformat(stamp)
                except (TypeError,ValueError): raise Fault(400,'ISO8601 time required')
                if parsed.tzinfo is None: raise Fault(400,'Timezone required')
        refs=data.get('source_refs',[])
        roots=set()
        for ref in refs:
            source=self.store.source(tenant,ref,conversation,topic); roots.add(source['family'])
        groups=data.get('support_groups',[])
        support_roots=set()
        for group in groups:
            if not group:
                raise Fault(422,'Empty support group')
            for identity in group:
                support=self.get(tenant,identity)
                self.check_scope(support,conversation,topic,branch)
                if support['lifecycle_status']!='ACTIVE':
                    raise Fault(422,'Inactive supporting record')
                roots.update(support['provenance_roots'])
                support_roots.update(support['provenance_roots'])
        if data['kind']=='SYSTEM_INTERPRETATION': roots=support_roots
        repetition=None
        if data['kind']=='USER_GUESS':
            prior=[r for r in self.records(tenant).values() if r['kind']=='USER_GUESS' and r['content']==data['content'] and r['subject_refs']==data.get('subject_refs',[]) and r['branch_id']==branch and (r['conversation_id']==conversation or (topic and r['topic_id']==topic)) and r['lifecycle_status'] not in {'DELETED','STOPPED'}]
            if prior:
                roots=set(prior[0]['provenance_roots']); repetition=prior[0]['record_id']
        if not roots:
            raise Fault(422,'Rootless context/cycle is unsupported')
        if data['kind']=='SYSTEM_INTERPRETATION' and not groups:
            raise Fault(422,'Interpretation requires registered support')
        record={'schema_version':'1.0','record_id':uid(),'tenant_id':tenant,'conversation_id':conversation,'topic_id':topic,'branch_id':branch,'kind':data['kind'],'content':data['content'],'subject_refs':data.get('subject_refs',[]),'source_refs':refs,'origin':'system' if data['kind']=='SYSTEM_INTERPRETATION' else data.get('origin','direct_user'),'epistemic_status':'CONDITIONAL_SUPPORT' if data['kind'] in {'SYSTEM_INTERPRETATION','HYPOTHETICAL','CONDITIONAL_RULE'} else 'REPORTED','valid_time':data.get('valid_time',{'start':None,'end':None,'before':[]}), 'recorded_at':now(), 'created_at':now(),'disclosure_time':data.get('disclosure_time'), 'person_access_events':data.get('person_access_events',[]),'retention_policy':data.get('retention_policy',{'expires_at':None}),'reuse_policy':{'memory':membership['memory']},'provenance_roots':sorted(roots),'support_groups':groups,'challenges':data.get('challenges',[]),'assumptions':data.get('assumptions',[]),'read_dependencies':data.get('read_dependencies',{'records':list({i for g in groups for i in g}),'absence':[]}), 'lifecycle_status':'ACTIVE'}
        for identity in record['challenges']+record['read_dependencies'].get('records',[]):
            self.check_scope(self.get(tenant,identity),conversation,topic,branch)
        if repetition: record['repetition_of']=repetition
        return self.save(tenant,record,version)

    def check_scope(self, record, conversation, topic, branch='actual'):
        if record['branch_id']!=branch or (record['conversation_id']!=conversation and not (topic and record['topic_id']==topic and record['reuse_policy']['memory']=='TOPIC' and self.store.get(record['tenant_id'],'conversation',conversation)['memory']=='TOPIC')):
            raise Fault(403,'Context outside scope/branch')

    @locked
    def project(self, tenant, conversation, topic=None, branch='actual', version=None, perspective=None, at_time=None):
        baseline=[]
        if branch!='actual':
            fork=self.store.get(tenant,'branch',branch)
            if fork['conversation_id']!=conversation or fork['topic_id']!=topic: raise Fault(403,'Branch outside scope')
            baseline=self.project(tenant,conversation,topic,'actual',fork['base_state_version'],perspective,at_time)
        self.store.scope(tenant,conversation,topic)
        result=[]
        for r in self.records(tenant,version).values():
            try: self.check_scope(r,conversation,topic,branch)
            except Fault: continue
            if r['lifecycle_status']!='ACTIVE':
                if not (r['lifecycle_status']=='SUPERSEDED' and r.get('revision_action')=='SUPERSEDE' and r.get('effective_time') and at_time and datetime.fromisoformat(at_time)<datetime.fromisoformat(r['effective_time'])): continue
            start=r['valid_time'].get('start'); end=r['valid_time'].get('end')
            if at_time and ((start and datetime.fromisoformat(at_time)<datetime.fromisoformat(start)) or (end and datetime.fromisoformat(at_time)>=datetime.fromisoformat(end))): continue
            if perspective:
                access=[e for e in r['person_access_events'] if e.get('person_id')==perspective and e.get('learned_at') and (at_time is None or datetime.fromisoformat(e['learned_at'])<=datetime.fromisoformat(at_time))]
                if not access: continue
            result.append(r)
        return baseline+result

    def process(self, tenant, conversation, topic, command, version):
        action=command.get('action'); targets=command.get('target_ids',[]); branch=command.get('branch_id','actual')
        if action not in ACTIONS: raise Fault(400,'Unknown revision action')
        if action in {'STOP_USING','DELETE'}: raise Fault(422,'Privacy actions implemented in L1-03')
        if action!='ADD' and not targets: raise Fault(422,'Explicit target required; no global name matching')
        changed=[]; additions=[]
        for identity in targets:
            record=self.get(tenant,identity); self.check_scope(record,conversation,topic,branch)
            if record['lifecycle_status'] in {'DELETED','STOPPED'}: raise Fault(403,'Target unavailable')
            if action=='HYPOTHETICAL_BRANCH': continue
            status={'CORRECT':'SUPERSEDED','SUPERSEDE':'SUPERSEDED','RETRACT':'RETRACTED'}.get(action)
            if status:
                self.save(tenant,{**record,'lifecycle_status':status,'effective_time':command.get('effective_time'),'revision_action':action},version); changed.append(identity)
        if action in {'ADD','CORRECT','SUPERSEDE','HYPOTHETICAL_BRANCH'}:
            data=command.get('new_record')
            if not data: raise Fault(400,'new_record required')
            if action=='HYPOTHETICAL_BRANCH':
                branch=uid(); data={**data,'kind':'HYPOTHETICAL'}
                self.store.put(tenant,'branch',{'id':branch,'conversation_id':conversation,'topic_id':topic,'base_state_version':version-1,'base_record_ids':[r['record_id'] for r in self.project(tenant,conversation,topic)]})
            if action=='SUPERSEDE' and command.get('effective_time'):
                data={**data,'valid_time':{**data.get('valid_time',{}),'start':command['effective_time']}}
            new=self.add(tenant,conversation,topic,data,version,branch)
            if action in {'CORRECT','SUPERSEDE'}:
                new['predecessor_ids']=targets; self.save(tenant,new,version)
            additions.append(new['record_id']); changed.append(new['record_id'])
        if action in {'CORRECT','RETRACT','SUPERSEDE'}:
            for target in targets:
                original=self.get(tenant,target)
                marker=self.add(tenant,conversation,topic,{'kind':'RETRACTION' if action=='RETRACT' else 'CORRECTION','content':action,'source_refs':original['source_refs'],'challenges':[target], 'memory':original['reuse_policy']['memory']},version,branch)
                marker['successor_ids']=additions; self.save(tenant,marker,version); changed.append(marker['record_id'])
        invalidated=set(); recomputed=set(); checked=[]; not_evaluated=[]
        # Conservative closure: every actual read and every absence query is checked.
        pending=set(changed)
        while pending:
            batch=pending; pending=set()
            for r in self.records(tenant).values():
                identity=r['record_id']
                try: self.check_scope(r,conversation,topic,branch)
                except Fault: continue
                if identity in changed or identity in invalidated: continue
                reads=set(r['read_dependencies'].get('records',[])) | {i for g in r['support_groups'] for i in g}
                hit=bool(reads & batch) or bool(additions and r['read_dependencies'].get('absence'))
                if not hit: continue
                invalidated.add(identity); pending.add(identity)
                groups=r['support_groups']
                active=self.records(tenant)
                viable=[g for g in groups if all(active.get(i,{}).get('lifecycle_status')=='ACTIVE' for i in g)]
                # Absence-based interpretations need explicit re-analysis, not guessed recomputation.
                status='ACTIVE' if viable and not r['read_dependencies'].get('absence') else 'STALE'
                roots=sorted({root for g in viable for i in g for root in active[i]['provenance_roots']})
                self.save(tenant,{**r,'lifecycle_status':status,'provenance_roots':roots or r['provenance_roots']},version)
                if status=='ACTIVE': recomputed.add(identity)
                else: not_evaluated.append(identity)
        for r in self.records(tenant).values():
            try: self.check_scope(r,conversation,topic,branch)
            except Fault: continue
            if r['record_id'] not in set(changed)|invalidated:
                checked.append(r['record_id'])
        receipt={'id':uid(),'schema_version':'1.0','tenant_id':tenant,'created_at':now(),'new_state_version':version,'action':action,'changed_ids':changed,'invalidated_ids':sorted(invalidated),'recomputed_ids':sorted(recomputed),'reused_ids':[],'unchanged_checked_ids':checked,'not_evaluated_ids':not_evaluated,'unresolved_ids':not_evaluated,'deletion_status':'NOT_REQUESTED','branch_id':branch}
        self.store.put(tenant,'revision',receipt)
        return receipt

    def revise(self, tenant, conversation, topic, command):
        if command.get('request_actor')!='authenticated_user': raise Fault(403,'Only authenticated user control may revise context')
        return self.store.atomic(tenant,conversation,command['idempotency_key'],command,command['expected_state_version'],lambda v:self.process(tenant,conversation,topic,command,v))
