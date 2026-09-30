"""Isolated JSON process adapter. Never execute research package initializers."""
import importlib.util
import hashlib
import inspect
import os
import json
from pathlib import Path
import sys
import types

# -I excludes user site/PYTHONPATH; only this product root is added.
sys.dont_write_bytecode=True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from packages.runtime_bridge.contract import handshake, load_config, PATHS, CAPABILITIES, fingerprint
from packages.runtime_bridge.serialization import decode, validate_request, provenance


def load_runtime(directory):
    # Explicit package shells avoid the research __init__ object graph.
    for name in ('pinned_runtime', 'pinned_runtime.cognition'):
        module = types.ModuleType(name); module.__path__ = []; sys.modules[name] = module
    loaded = {}
    for path in PATHS:
        short = Path(path).stem; name = 'pinned_runtime.cognition.' + short
        spec = importlib.util.spec_from_file_location(name, Path(directory) / path)
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module
        data=(Path(directory)/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=load_config()['files'][path]['sha256']:raise ValueError('DIGEST_MISMATCH')
        exec(compile(data,str(Path(directory)/path),'exec'),module.__dict__); loaded[short] = module
    required = {'semantic': ('prepare_semantics', 'AuthorizedText'), 'epistemic': ('check_epistemic_candidates',), 'core': ('EvidenceCore',)}
    for module, names in required.items():
        for name in names:
            if not callable(getattr(loaded[module], name, None)): raise ValueError('INTERFACE_MISMATCH')
    if tuple(inspect.signature(loaded['epistemic'].check_epistemic_candidates).parameters) != ('core', 'query', 'semantic', 'max_depth'):
        raise ValueError('INTERFACE_MISMATCH')
    return loaded


def isolate():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(10,10))
    if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
    resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
    def audit(event,args):
        if event.startswith(('socket.','subprocess.','os.exec','os.spawn')) or event in {'os.system','os.fork','os.forkpty'}:
            raise PermissionError('Provider/network/child transport disabled')
        if event=='open':
            mode,flags=args[1:3]
            if (isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
                raise PermissionError('Runtime file writes disabled')
    sys.addaudithook(audit)


def normalized(tree):
    raw=tree.as_dict()
    def convert(node):
        return {'holder':node['holder'],'operator':node['attitude'],'polarity':node['polarity'],
                'content':convert(node['content']) if isinstance(node['content'],dict) else node['content']}
    return convert(raw)


def execute(modules,request,config,ready):
    validate_request(request)
    base={'schema_version':'1.0','request_id':request['request_id'],'status':'UNSUPPORTED','selected':False,'executed':False,
          'result_produced':False,'used_in_answer':False,'outputs':[],'diagnostics':[],'provider_calls':0,
          'provenance':provenance(config,ready['capability_manifest_digest']),'native_receipt_digest':None}
    if request['capability_id'] not in CAPABILITIES:
        return {**base,'diagnostics':[{'reason':'CAPABILITY_NOT_BRIDGED'}]}
    base.update(selected=True,executed=True)
    try:
        core=modules['core'].EvidenceCore()
        sources=tuple(modules['semantic'].AuthorizedText(s['source_id'],s['text'],s['version']) for s in request['sources'])
        # Original text and ordinary question are passed verbatim. No provider/backend.
        semantic=modules['semantic'].prepare_semantics(request['query'],sources,core=core)
        bundle=modules['epistemic'].check_epistemic_candidates(core,request['query'],semantic)
        base.update(executed=True,native_receipt_digest=fingerprint(core.receipt(bundle.scope)))
        originals={s['source_id']:s for s in request['sources']}
        outputs=[]
        for record in bundle.records:
            tree=record.tree
            if not isinstance(tree,modules['epistemic'].MentalProposition): continue
            if request['capability_id']=='information_access' and tree.attitude not in {
                modules['epistemic'].Attitude.EXPOSURE,modules['epistemic'].Attitude.UNDERSTANDING,modules['epistemic'].Attitude.KNOWLEDGE}: continue
            content=core.claims[record.expression_id].content;span=core.spans[content['source_span_id']];source=originals[record.source_id]
            body={'source_id':record.source_id,'source_version':source['version'],'source_sha256':source['sha256'],
                  'span':[span.start,span.end],'quote':span.quote,'expression':normalized(tree),
                  'epistemic_status':'REPORTED_EXPRESSION_NOT_PRIVATE_TRUTH','private_state':'NOT_ESTABLISHED','world_truth':'NOT_ESTABLISHED'}
            outputs.append({'output_id':fingerprint(body),**body})
        base.update(outputs=outputs,result_produced=bool(outputs),status='EXECUTED' if outputs else ('UNRESOLVED' if bundle.diagnostics else 'NO_TREATMENT'),
                    diagnostics=[{'reason':row['reason']} for row in bundle.diagnostics])
        if not outputs and not base['diagnostics']:base['diagnostics']=[{'reason':'NO_SUPPORTED_MODAL_EXPRESSION_IN_ORIGINAL_INPUT'}]
        return base
    except (ValueError,KeyError,TypeError):
        return {**base,'status':'FAILED','diagnostics':[{'reason':'RUNTIME_INPUT_OR_CAPACITY_FAILURE'}]}


def main():
    directory=sys.argv[1]
    request=decode(sys.stdin.buffer.read(131073),131072)
    if set(request) not in ({'config','action'},{'config','action','request'}): raise ValueError('Unknown envelope')
    config=request['config'];result=handshake(directory,config)
    if result['handshake_status']=='READY':
        try: modules=load_runtime(directory)
        except Exception as error:
            status='DIGEST_MISMATCH' if str(error)=='DIGEST_MISMATCH' else 'INTERFACE_MISMATCH'
            result.update(handshake_status=status,errors=[status],discovered_capabilities=[])
    if request['action']=='execute':
        if result['handshake_status']!='READY': raise ValueError('Non-ready execution refused')
        isolate();result=execute(modules,request['request'],config,result)
    elif request['action']!='handshake': raise ValueError('Unknown action')
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__=='__main__':main()
