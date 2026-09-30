"""Check the actual static Pages artifact has no local API/runtime transport."""
from pathlib import Path
import json
import re
ROOT=Path(__file__).resolve().parents[1]

def check(root=ROOT):
    output=root/'pages-dist'
    html=(output/'index.html').read_text()
    assets=list(output.glob('assets/*'))
    assert assets and '未接入真实 HCL' in html, 'built static preview/environment required'
    scripts='\n'.join(p.read_text() for p in assets if p.suffix=='.js')
    for forbidden in ('/v1/', '127.0.0.1:8765', 'api.openai.com', 'api.anthropic.com', 'HCL_DEVELOPMENT_ARTIFACT'):
        assert forbidden not in scripts, 'forbidden preview transport: '+forbidden
    assert 'hcl-assistant-pages-preview-v2' in scripts, 'bounded browser Controller missing'
    assert '交互演示，不连接模型' in scripts, 'honest mock identity missing'
    assert 'Web Locks' in scripts, 'safe storage boundary missing'
    assert not re.search(r'(sk-[A-Za-z0-9_-]{20,}|github_pat_|BEGIN .*PRIVATE KEY)',scripts), 'secret pattern in static artifact'
    return {'static_preview_bundle':'PASS','assets':len(assets),'backend_provider_runtime_transport':'ABSENT_FROM_CHECKED_BUNDLE','provider_calls':0}
if __name__=='__main__':print(json.dumps(check(),indent=2))
