"""One command supervises the local product API and UI. No provider readiness call."""
import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--configure',action='store_true',help='Operator-only masked terminal setup, process lifetime only');args=parser.parse_args()
    os.chdir(ROOT)
    from packages.adapter.development_budget import configuration_status
    server_env=dict(os.environ)
    if args.configure:
        print('Enter only in this local terminal. Credentials stay in process memory and are not saved. Ctrl-C cancels.')
        for name in ('HCLA_DEEPSEEK_BASE_URL','HCLA_DEEPSEEK_MODEL','HCLA_DEV_INPUT_USD_PER_MILLION','HCLA_DEV_OUTPUT_USD_PER_MILLION','HCLA_DEV_MAX_REQUESTS','HCLA_DEV_MAX_COST_USD','HCLA_DEV_MAX_OUTPUT_TOKENS','HCLA_DEV_BUDGET_ID'):
            value=input(name+' (required): ').strip()
            if value:server_env[name]=value
        server_env['HCLA_DEEPSEEK_API_KEY']=getpass.getpass('DeepSeek API key (hidden; operator enters directly): ')
        server_env['HCLA_DEV_ACCESS_TOKEN']=getpass.getpass('Local access password (hidden, at least 24 characters): ')
    status=configuration_status(server_env)
    print('Development configuration: '+('ready' if status['configured'] else 'required'))
    for name in status.get('missing',[])+status.get('invalid',[]):print(' - '+name)
    if args.check:return 0 if status['configured'] else 2
    if not (ROOT/'node_modules/.bin/vite').exists():
        raise SystemExit('Dependencies missing. Run npm ci --ignore-scripts once, then npm run chat.')
    # UI process must not inherit the provider credential or development access token.
    frontend_env={k:v for k,v in os.environ.items() if not k.startswith(('HCLA_','DEEPSEEK_'))}
    children=[]
    try:
        children.append(subprocess.Popen([sys.executable,'-m','apps.api.development_server'],cwd=ROOT,env=server_env))
        children.append(subprocess.Popen(['npm','run','dev'],cwd=ROOT,env=frontend_env,stdout=subprocess.DEVNULL))
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if any(child.poll() is not None for child in children):raise RuntimeError('A service exited during startup')
            try:
                for url in ['http://127.0.0.1:8765/v1/development/status','http://127.0.0.1:5173/']:
                    with urllib.request.urlopen(url,timeout=1) as response:
                        if response.status!=200:raise RuntimeError('Readiness failed')
                break
            except (OSError,RuntimeError):time.sleep(.2)
        else:raise RuntimeError('Local services did not become ready')
        print('Open http://127.0.0.1:5173/ — Ctrl-C stops both services. Readiness made no model call.',flush=True)
        if not args.no_browser:webbrowser.open('http://127.0.0.1:5173/')
        while all(child.poll() is None for child in children):time.sleep(.25)
        raise RuntimeError('A local service stopped; both services are shutting down')
    except KeyboardInterrupt:return 0
    except Exception:print('Local startup stopped. Check the service error above; no automatic retry.',file=sys.stderr);return 1
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait()

if __name__=='__main__':
    sys.path.insert(0,str(ROOT));raise SystemExit(main())
