"""Bundle and actually handshake only the existing reviewed three-file slice."""
from pathlib import Path
import os
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.fetch_development_runtime import acquire
from packages.runtime_bridge.bridge import RuntimeBridge
from packages.runtime_bridge.contract import load_config,verify_artifact


def build(destination=Path('.hcla-runtime')):
    destination=Path(destination).absolute();config=load_config()
    if destination.exists():
        # Reuse only an exact verified cache. No extra network on repeat builds.
        verify_artifact(destination,config)
    elif os.environ.get('HCL_DEVELOPMENT_ARTIFACT'):
        source=Path(os.environ['HCL_DEVELOPMENT_ARTIFACT']).absolute()
        verify_artifact(source,config)
        for name in [*config['allowed_runtime_paths'],'identity.json']:
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/name,target)
        verify_artifact(destination,config)
    else:
        acquire(destination)
    if RuntimeBridge(destination).handshake()['handshake_status']!='READY':
        raise ValueError('Bundled reviewed runtime handshake failed')
    return destination

if __name__=='__main__':
    build()
