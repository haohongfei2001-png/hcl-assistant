"""Read-only, current-permission product history and revision projections."""
from packages.store.ledger import Fault, canonical


def changes(controller, tenant, run):
    store=controller.store
    with store.lock:
        if run.get('redacted'): return []
        before=controller.context.records(tenant,run['state_version_before'])
        after=controller.context.records(tenant,run['state_version_after'])
        accepted=set(run['accepted_change_ids']); result=[]
        def visible(record):
            if not record or not controller.context.allowed(tenant,record): return None
            try:
                controller.context.check_scope(record,run['conversation_id'],run['topic_id'],record['branch_id'])
                for ref in record['source_refs']:store.source(tenant,ref,run['conversation_id'],run['topic_id'],allow_stopped=True)
            except Fault:return None
            return {k:record.get(k) for k in ('record_id','content','kind','source_refs','valid_time','person_access_events','branch_id')}
        for receipt in store.list(tenant,'revision'):
            action=receipt['action']
            if action=='ADD' or receipt['new_state_version']!=run['state_version_after'] or not accepted.intersection(receipt['changed_ids']):continue
            ids=set(receipt['changed_ids']); old=[visible(before[i]) for i in ids if i in before]
            new=[visible(after[i]) for i in ids if i not in before and i in after and after[i]['kind'] not in {'CORRECTION','RETRACTION'}]
            old=[r for r in old if r];new=[r for r in new if r]
            signature=lambda rows:sorted(canonical({k:r.get(k) for k in ('content','kind','valid_time','person_access_events')}) for r in rows)
            if action in {'CORRECT','SUPERSEDE'} and signature(old)==signature(new):continue
            if action=='CORRECT' and new and all(r['kind']=='USER_GUESS' for r in new) and any(r['kind']!='USER_GUESS' for r in old):label='GUESS'
            else:label=action
            result.append({'action':label,'old':old,'new':new,'actual_changed':action!='HYPOTHETICAL_BRANCH',
                           'invalidated_count':len(receipt['invalidated_ids']),'not_reevaluated_count':len(receipt['not_evaluated_ids']),
                           'impact':'假设分支不回写实际背景' if action=='HYPOTHETICAL_BRANCH' else '只更新指定记录及其依赖；旧回答未重写，未重评部分保持未知',
                           'recorded_version':receipt['new_state_version']})
        return result


def conversation(controller, tenant, conversation_id):
    with controller.store.lock:
        c=controller.store.get(tenant,'conversation',conversation_id)
        runs=[controller.read(tenant,r['id']) for r in controller.store.list(tenant,'run') if r['conversation_id']==c['id']]
        for run in runs:run['changes']=changes(controller,tenant,run)
        return {'conversation':c,'state_version':controller.store.version(tenant),'events':controller.store.history(tenant,c['id']),'runs':runs}


def search(application,tenant,query,limit=50):
    if not isinstance(query,str) or not 0<len(query.strip())<=200:raise Fault(400,'Search requires1–200 characters')
    needle=query.strip().casefold();hits=[]
    for store in (application.stores.persistent,application.stores.temporary):
        with store.lock:
            controller=application.controller(store)
            for c in store.list(tenant,'conversation'):
                view=conversation(controller,tenant,c['id'])
                related=[change for run in view['runs'] for change in run['changes']]
                for run in view['runs']:
                    if run.get('redacted'):continue
                    body=run.get('input_text','')+'\n'+(run.get('answer') or {}).get('text','')
                    offset=body.casefold().find(needle)
                    if offset<0:continue
                    hits.append({'conversation_id':c['id'],'title':c['title'],'run_id':run['run_id'],
                                 'snippet':body[max(0,offset-40):offset+len(query)+100],
                                 'historical':run['outdated'],'related_changes':related,
                                 'scope':c['memory'],'source':'CURRENT_PERMISSION_RUN_PROJECTION'})
                    if len(hits)>=limit:return hits
    return hits
