"""Strict JSON envelopes for original synthetic sources, never input templating."""
import hashlib
import json
from pathlib import Path
from packages.runtime_bridge.contract import CAPABILITIES, fingerprint, load_config

VERSION = '1.0'
OUTCOMES = {'EXECUTED', 'UNSUPPORTED', 'NO_TREATMENT', 'FAILED', 'UNRESOLVED', 'CANCELLED'}
REQUEST_FIELDS = {'schema_version','request_id','capability_id','query','sources','input_class','fixture_family','purpose','timeout_ms'}
RESPONSE_FIELDS = {'schema_version','request_id','status','selected','executed','result_produced','used_in_answer','outputs','diagnostics','provider_calls','provenance','native_receipt_digest'}


def decode(raw, maximum=262144):
    if len(raw) > maximum: raise ValueError('SERIALIZATION_BOUND_EXCEEDED')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('DUPLICATE_JSON_FIELD')
            result[key] = value
        return result
    def constant(value): raise ValueError('NONFINITE_JSON_VALUE')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value,dict): raise ValueError('JSON_OBJECT_REQUIRED')
    return value


def validate_request(request):
    if not isinstance(request,dict) or set(request) != REQUEST_FIELDS or request['schema_version'] != VERSION:
        raise ValueError('REQUEST_INTERFACE_MISMATCH')
    if request['input_class'] != 'SYNTHETIC_NON_CONFIRMATION' or request['purpose'] != 'DEVELOPMENT_INTEGRATION_ONLY':
        raise ValueError('INPUT_POLICY_REFUSED')
    for key in ('request_id','fixture_family','query'):
        if not isinstance(request[key],str) or not request[key].strip() or len(request[key]) > (8000 if key=='query' else 100):
            raise ValueError('INVALID_'+key.upper())
    if not isinstance(request['capability_id'],str) or len(request['capability_id']) > 100:
        raise ValueError('INVALID_CAPABILITY')
    if type(request['timeout_ms']) is not int or not 1 <= request['timeout_ms'] <= load_config()['timeout_policy']['maximum_ms']:
        raise ValueError('INVALID_TIMEOUT')
    sources = request['sources']
    if not isinstance(sources,list) or not 1 <= len(sources) <= 16: raise ValueError('SOURCE_BOUND_EXCEEDED')
    seen=set(); size=0
    for source in sources:
        if not isinstance(source,dict) or set(source) != {'source_id','version','sha256','text'}: raise ValueError('UNKNOWN_SOURCE_FIELD')
        if not isinstance(source['source_id'],str) or not source['source_id'] or len(source['source_id'])>100 or source['source_id'] in seen: raise ValueError('INVALID_SOURCE_ID')
        seen.add(source['source_id'])
        if type(source['version']) is not int or source['version'] < 1 or not isinstance(source['text'],str) or not source['text']:
            raise ValueError('INVALID_SOURCE')
        data=source['text'].encode();size+=len(data)
        if source['sha256'] != hashlib.sha256(data).hexdigest(): raise ValueError('SOURCE_DIGEST_MISMATCH')
    if size > 64000: raise ValueError('SOURCE_BOUND_EXCEEDED')
    if len(json.dumps(request,ensure_ascii=False).encode())>131072: raise ValueError('REQUEST_BOUND_EXCEEDED')
    return request


def provenance(config, manifest_digest):
    return {**{k: config[k] for k in ('bridge_version','source_repository','source_commit_sha','artifact_digest','interface_version','interface_digest','implementation_id','receipt_version')},
            'runtime_version':'git:'+config['source_commit_sha'],'native_runtime_version':None,
            'bridge_artifact_digest':fingerprint({name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('contract.py','serialization.py','bridge.py','worker.py')}),
            'serialization_version':VERSION,'config_hash':fingerprint(config),'capability_manifest_digest':manifest_digest,
            'mode':'EXPERIMENTAL','production_enabled':False,'evidence_class':'DEVELOPMENT_INTEGRATION_ONLY','efficacy':'NOT_TESTED'}


def validate_response(response, request, expected_provenance):
    if (not isinstance(response,dict) or set(response)!=RESPONSE_FIELDS or response.get('schema_version')!=VERSION
            or response.get('request_id')!=request['request_id'] or response.get('status') not in OUTCOMES
            or response.get('provenance')!=expected_provenance or type(response.get('provider_calls')) is not int or response['provider_calls']!=0
            or response.get('used_in_answer') is not False):
        raise ValueError('RESPONSE_INTERFACE_MISMATCH')
    for key in ('selected','executed','result_produced'):
        if type(response.get(key)) is not bool: raise ValueError('INVALID_EXECUTION_FLAGS')
    if not isinstance(response['outputs'],list) or len(response['outputs'])>64 or not isinstance(response['diagnostics'],list): raise ValueError('INVALID_OUTPUT')
    if any(not isinstance(d,dict) or set(d)!={'reason'} or not isinstance(d['reason'],str) or len(d['reason'])>200 for d in response['diagnostics']):
        raise ValueError('INVALID_DIAGNOSTIC')
    native=response['native_receipt_digest']
    import re
    if native is not None and (not isinstance(native,str) or re.fullmatch('sha256:[0-9a-f]{64}',native) is None): raise ValueError('INVALID_NATIVE_RECEIPT')
    def expression(node,depth=1):
        if (not isinstance(node,dict) or set(node)!={'holder','operator','polarity','content'} or depth>4
                or not isinstance(node['holder'],str) or not 1<=len(node['holder'])<=100
                or node['operator'] not in {'BELIEF','EXPOSURE_CLAIM','UNDERSTANDING_CLAIM','KNOWLEDGE_CLAIM','REPORTED_ATTRIBUTION'}
                or node['polarity'] not in {'AFFIRM','DENY','UNCERTAIN'}):raise ValueError('INVALID_EXPRESSION')
        if isinstance(node['content'],dict):expression(node['content'],depth+1)
        elif not isinstance(node['content'],str) or not 1<=len(node['content'])<=4000:raise ValueError('INVALID_EXPRESSION_CONTENT')
    if response['result_produced'] != bool(response['outputs']) or (response['outputs'] and response['status']!='EXECUTED'):
        raise ValueError('FALSE_TREATMENT')
    if response['status'] in {'NO_TREATMENT','UNRESOLVED'} and (not response['selected'] or not response['executed'] or response['native_receipt_digest'] is None):
        raise ValueError('UNVERIFIED_NO_TREATMENT')
    if response['status']=='EXECUTED' and not (response['selected'] and response['executed'] and response['outputs']):
        raise ValueError('FALSE_EXECUTION')
    if response['status']=='UNSUPPORTED' and (response['selected'] or response['executed']): raise ValueError('FALSE_SELECTION')
    if response['selected'] != (request['capability_id'] in CAPABILITIES): raise ValueError('FALSE_CAPABILITY')
    by_id={s['source_id']:s for s in request['sources']}
    for output in response['outputs']:
        if not isinstance(output,dict) or set(output)!={'output_id','source_id','source_version','source_sha256','span','quote','expression','epistemic_status','private_state','world_truth'}:
            raise ValueError('UNKNOWN_OUTPUT_FIELD')
        source=by_id.get(output['source_id']);span=output['span']
        if (source is None or output['source_version']!=source['version'] or output['source_sha256']!=source['sha256']
                or not isinstance(span,list) or len(span)!=2 or any(type(x) is not int for x in span)
                or not 0 <= span[0] < span[1] <= len(source['text']) or source['text'][span[0]:span[1]] != output['quote']
                or output['epistemic_status']!='REPORTED_EXPRESSION_NOT_PRIVATE_TRUTH'
                or output['private_state']!='NOT_ESTABLISHED' or output['world_truth']!='NOT_ESTABLISHED'):
            raise ValueError('OUTPUT_SOURCE_OR_EPISTEMIC_MISMATCH')
        expression(output['expression'])
        body={k:v for k,v in output.items() if k!='output_id'}
        if output['output_id'] != fingerprint(body): raise ValueError('OUTPUT_DIGEST_MISMATCH')
    return response
