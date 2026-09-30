"""Projection of one recorded run. No adapter or provider dependency."""


def project(run):
    identity=run.get('answer_identity') or ({k:run['answer'][k] for k in ('answer_id','run_id','snapshot_id')} if run.get('answer') else None)
    if not identity: return {'redactions':['UNAVAILABLE'],'judgment_basis':[],'source_links':[]}
    if run.get('redacted') or not run.get('answer'):
        return {**identity,'judgment_basis':[],'known_information':[],'source_links':[],'redactions':['CURRENT_POLICY_REDACTED'],'recorded_at':None}
    prep=run['answer_preparation']; original=run['explain_projection']
    claims=original['judgment_basis']; used={c['record_id'] for c in claims if 'record_id' in c}
    return {**identity,'known_information':[r for r in run['selected_context']['records'] if r['record_id'] in used],'judgment_basis':claims,'alternative_explanations':prep['alternatives'],'uncertainties':prep['material_uncertainties'],'key_premise':prep['assumptions'],'discriminating_information':[],'source_links':original['source_links'],'recorded_at':original['recorded_at'],'redactions':[],'outdated':run['outdated'],'mode':run['run_receipt']['mode'],'development_only':run['run_receipt'].get('development_only',False),'operation_outputs':run.get('runtime_outputs',[]),'extraction':'PINNED_BOUNDED_RUNTIME_SYNTAX' if run.get('development_request') else 'EXPLICIT_PREFIX_GRAMMAR_ONLY','new_model_calls':0}
