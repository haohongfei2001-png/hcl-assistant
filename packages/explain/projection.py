"""Projection of one recorded run. No adapter or provider dependency."""

from packages.store.ledger import canonical


def claim_source_links(records, claims):
    """Select exact pinned refs of bound records, never the wider read closure."""
    used = {claim['record_id'] for claim in claims if 'record_id' in claim}
    sources = {canonical(ref): ref for record in records if record['record_id'] in used
               for ref in record['source_refs']}
    return list(sources.values())


def project(run):
    identity=run.get('answer_identity') or ({k:run['answer'][k] for k in ('answer_id','run_id','snapshot_id')} if run.get('answer') else None)
    if not identity: return {'redactions':['UNAVAILABLE'],'judgment_basis':[],'source_links':[]}
    if run.get('redacted') or not run.get('answer'):
        return {**identity,'judgment_basis':[],'known_information':[],'source_links':[],'redactions':['CURRENT_POLICY_REDACTED'],'recorded_at':None}
    prep=run['answer_preparation']; original=run['explain_projection']
    claims=original['judgment_basis']; used={c['record_id'] for c in claims if 'record_id' in c}
    source_links = original['source_links']
    if not run.get('development_request'):
        # Older mock runs may have recorded the full selected closure. Narrow it
        # using only their own frozen records/claims; never add current evidence.
        bound = {canonical(ref) for ref in claim_source_links(run['selected_context']['records'], claims)}
        source_links = [ref for ref in source_links if canonical(ref) in bound]
    return {**identity,'known_information':[r for r in run['selected_context']['records'] if r['record_id'] in used],'judgment_basis':claims,'alternative_explanations':prep['alternatives'],'uncertainties':prep['material_uncertainties'],'key_premise':prep['assumptions'],'discriminating_information':[],'source_links':source_links,'recorded_at':original['recorded_at'],'redactions':[],'outdated':run['outdated'],'mode':run['run_receipt']['mode'],'development_only':run['run_receipt'].get('development_only',False),'operation_outputs':run.get('runtime_outputs',[]),'extraction':'PINNED_BOUNDED_RUNTIME_SYNTAX' if run.get('development_request') else 'EXPLICIT_PREFIX_GRAMMAR_ONLY','new_model_calls':0}
