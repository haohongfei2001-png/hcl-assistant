"""Read-only Lab projection. No state mutation or experiment arms."""
from packages.store.ledger import Fault


def inspect(controller, tenant, run_id):
    run=controller.read(tenant,run_id)
    return {'mode':'DEVELOPMENT_CHAT' if run.get('live_chat') else 'EXPERIMENTAL' if run['run_receipt'].get('development_only') else 'MOCK','read_only':True,'compare_enabled':False,'compare_gate':['I06_DISPOSITION','PINNED_PERMITTED_RUNTIME_ARTIFACT','PRODUCT_ADAPTER_SCOPE_VALIDATION','EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION'],'run':run,'usage_scope':('THIS_ATTEMPT; real development provider receipt; unknown tokens/cost remain null; distinct attempts are not aggregated here' if run.get('live_chat') else 'THIS_ATTEMPT; provider-free preparation; tokens unknown=null; all attempts are separate receipts'),'efficacy':'NOT_TESTED'}
