"""Read-only Lab projection. No state mutation or experiment arms."""
from packages.store.ledger import Fault


def inspect(controller, tenant, run_id):
    run=controller.read(tenant,run_id)
    return {'mode':'MOCK','read_only':True,'compare_enabled':False,'compare_gate':['I06_DISPOSITION','PINNED_PERMITTED_RUNTIME_ARTIFACT','PRODUCT_ADAPTER_SCOPE_VALIDATION','EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION'],'run':run,'usage_scope':'THIS_ATTEMPT; provider-free mock; tokens unknown=null; all attempts are separate receipts','efficacy':'NOT_TESTED'}
