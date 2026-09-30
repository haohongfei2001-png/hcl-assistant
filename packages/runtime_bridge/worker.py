"""Isolated JSON process adapter. Never execute research package initializers."""
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import types

# -I excludes user site/PYTHONPATH; only this product root is added.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from packages.runtime_bridge.contract import handshake, load_config, PATHS


def load_runtime(directory):
    # Explicit package shells avoid the research __init__ object graph.
    for name in ('pinned_runtime', 'pinned_runtime.cognition'):
        module = types.ModuleType(name); module.__path__ = []; sys.modules[name] = module
    loaded = {}
    for path in PATHS:
        short = Path(path).stem; name = 'pinned_runtime.cognition.' + short
        spec = importlib.util.spec_from_file_location(name, Path(directory) / path)
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module
        spec.loader.exec_module(module); loaded[short] = module
    required = {'semantic': ('prepare_semantics', 'AuthorizedText'), 'epistemic': ('check_epistemic_candidates',), 'core': ('EvidenceCore',)}
    for module, names in required.items():
        for name in names:
            if not callable(getattr(loaded[module], name, None)): raise ValueError('INTERFACE_MISMATCH')
    if tuple(inspect.signature(loaded['epistemic'].check_epistemic_candidates).parameters) != ('core', 'query', 'semantic', 'max_depth'):
        raise ValueError('INTERFACE_MISMATCH')
    return loaded


def main():
    directory = sys.argv[1]
    request = json.loads(sys.stdin.buffer.read(131073))
    result = handshake(directory, request.get('config'))
    if result['handshake_status'] == 'READY':
        try: load_runtime(directory)
        except Exception:
            result.update(handshake_status='INTERFACE_MISMATCH', errors=['INTERFACE_MISMATCH'], discovered_capabilities=[])
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__': main()
