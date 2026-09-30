"""Current reuse policy takes precedence over historical projections."""
import json
from datetime import datetime
from packages.context.revision import Context
from packages.store.ledger import Fault, canonical, digest, now, uid


class PolicyContext(Context):
    def allowed(self, tenant, record, at=None):
        current=self.records(tenant).get(record['record_id'])
        if not current or current['lifecycle_status'] in {'DELETED','STOPPED','RETRACTED','SUPERSEDED'}:
            return False
        expiry=record['retention_policy'].get('expires_at')
        if expiry and datetime.fromisoformat(expiry)<=datetime.fromisoformat(at or now()): return False
        return True

    def project(self, tenant, *args, **kwargs):
        return [r for r in super().project(tenant,*args,**kwargs) if self.allowed(tenant,r)]

    def selection(self, tenant, conversation, topic=None, branch='actual', perspective=None, at_time=None, seeds=None, limit=100):
        records=self.project(tenant,conversation,topic,branch,perspective=perspective,at_time=at_time)
        # Small L1/L2 corpus: full eligible closure, never a support-only top-k.
        # Inactive correction/retraction markers remain visible as metadata.
        if len(records)>limit:
            raise Fault(422,'Correction closure exceeds limit; narrow the declared scope')
        marker_ids=[r['record_id'] for r in records if r['kind']=='CORRECTION']
        retractions=[r['record_id'] for r in records if r['kind']=='RETRACTION']
        sources={canonical(ref):ref for r in records for ref in r['source_refs']}
        selection={'scope':{'tenant_id':tenant,'conversation_id':conversation,'topic_id':topic,'branch_id':branch,'perspective_id':perspective,'time':at_time},'state_version':self.store.version(tenant),'source_versions':list(sources.values()),'record_ids':[r['record_id'] for r in records],'correction_ids':marker_ids,'challenge_ids':sorted({i for r in records for i in r['challenges']}),'retraction_ids':retractions,'assumptions':[a for r in records for a in r['assumptions']],'missing_scope':[],'coverage':'PARTIAL','content_digest':digest(canonical(records)),'policy_revision':self.store.account(tenant)['policy'],'records':records}
        return selection

    def process(self, tenant, conversation, topic, command, version):
        action=command.get('action')
        if action not in {'STOP_USING','DELETE'}:
            return super().process(tenant,conversation,topic,command,version)
        targets=command.get('target_ids',[])
        if not targets: raise Fault(422,'Explicit target required')
        records=self.records(tenant); affected=set(targets)
        for identity in targets:
            self.check_scope(self.get(tenant,identity),conversation,topic,command.get('branch_id','actual'))
        source_ids={ref['source_id'] for identity in targets for ref in records[identity]['source_refs']}
        # Derived content and copied references are conservatively withheld/purged.
        while True:
            new={r['record_id'] for r in records.values() if any(ref['source_id'] in source_ids for ref in r['source_refs']) or set(r['read_dependencies'].get('records',[])) & affected or any(set(g)&affected for g in r['support_groups']) or set(r['challenges'])&affected}
            if new<=affected: break
            affected|=new
        for identity in affected:
            record=records[identity]
            if action=='STOP_USING':
                self.save(tenant,{**record,'lifecycle_status':'STOPPED'},version)
            else:
                self.store.db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(identity,tenant))
        self.store.db.execute('UPDATE accounts SET policy=policy+1 WHERE tenant=?',(tenant,))
        if action=='DELETE':
            for identity in source_ids:
                self.store.db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(identity,tenant))
            self.replay_deletions(tenant)
        else:
            self.redact_objects(tenant,affected|source_ids)
        receipt={'id':uid(),'new_state_version':version,'action':action,'changed_ids':sorted(affected),'invalidated_ids':sorted(affected),'recomputed_ids':[],'reused_ids':[],'unchanged_checked_ids':[],'not_evaluated_ids':[],'unresolved_ids':[],'deletion_status':'PURGED' if action=='DELETE' else 'STOPPED'}
        return self.store.put(tenant,'revision',receipt)

    def redact_objects(self, tenant, identities):
        for row in list(self.store.db.execute('SELECT * FROM objects WHERE tenant=?',(tenant,))):
            obj=json.loads(row['body'])
            if not any(identity in row['body'] for identity in identities): continue
            if row['type'] in {'conversation','topic','revision'}: continue
            if row['type']=='run':
                obj['answer']=None; obj['answer_preparation']=None; obj['explain_projection']=None
                obj['selected_context']={'record_ids':[],'records':[],'coverage':'UNAVAILABLE'}
                obj['stream']=[e for e in obj.get('stream',[]) if not e['type'].startswith('answer.')]
                obj['unresolved_updates']=[]; obj['errors']=['REDACTED']; obj['redacted']=True
                obj['operation_receipts']=[]
                self.store.put(tenant,'run',obj)
            else:
                self.store.db.execute('DELETE FROM objects WHERE id=? AND tenant=?',(row['id'],tenant))
        for row in list(self.store.db.execute('SELECT * FROM idempotency WHERE tenant=?',(tenant,))):
            if any(identity in row['result'] for identity in identities):
                obj=json.loads(row['result'])
                if 'run_id' in obj:
                    obj=self.store.get(tenant,'run',obj['run_id'])
                elif 'event' in obj:
                    obj={'event':obj['event'],'source':None,'state_version':obj['state_version'],'redacted':True}
                else:
                    obj={'redacted':True}
                self.store.db.execute('UPDATE idempotency SET result=? WHERE tenant=? AND conversation=? AND key=?',(canonical(obj),tenant,row['conversation'],row['key']))

    def replay_deletions(self, tenant, tombstones=None):
        if tombstones:
            for identity in tombstones:
                self.store.db.execute('INSERT OR IGNORE INTO tombstones VALUES(?,?)',(identity,tenant))
        identities={r['id'] for r in self.store.db.execute('SELECT id FROM tombstones WHERE tenant=?',(tenant,))}
        for identity in identities:
            for row in list(self.store.db.execute('SELECT * FROM records WHERE tenant=? AND id=?',(tenant,identity))):
                obj=json.loads(row['body'])
                obj={k:v for k,v in obj.items() if k in {'schema_version','record_id','tenant_id','conversation_id','topic_id','branch_id','revision','created_at','recorded_at'}}
                obj.update(content='',kind='RETRACTION',subject_refs=[],source_refs=[],origin='system',epistemic_status='UNRESOLVED',valid_time={},person_access_events=[],retention_policy={},reuse_policy={'memory':'CONVERSATION'},provenance_roots=[],support_groups=[],challenges=[],assumptions=[],read_dependencies={},lifecycle_status='DELETED')
                self.store.db.execute('UPDATE records SET body=? WHERE id=? AND version=?',(canonical(obj),identity,row['version']))
            for row in list(self.store.db.execute('SELECT * FROM sources WHERE tenant=? AND id=?',(tenant,identity))):
                obj=json.loads(row['body']); obj.update(text='',name='deleted',deleted=True)
                self.store.db.execute('UPDATE sources SET body=? WHERE id=? AND version=?',(canonical(obj),identity,row['version']))
        self.redact_objects(tenant,identities)

    def summary(self, tenant, conversation, topic=None):
        selected=self.selection(tenant,conversation,topic)
        body={'record_ids':selected['record_ids'],'text':'\n'.join(r['content'] for r in selected['records']),'provenance_roots':sorted({root for r in selected['records'] for root in r['provenance_roots']}),'policy_revision':selected['policy_revision'],'state_version':selected['state_version']}
        with self.store.transaction(): return self.store.put(tenant,'summary',body)
