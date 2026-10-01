"""Explicit opt-in loopback service; missing configuration never selects mock silently."""
import argparse
import os
from pathlib import Path
from apps.api.server import Application, serve
from apps.api.development_auth import DevelopmentAuth
from packages.adapter.development_budget import DevelopmentConfig, DevelopmentBudget, configuration_status
from packages.adapter.deepseek import DeepSeekAdapter
from packages.controller.live_chat import LiveChat


def application(database, budget_database, runtime=None, env=None):
    env=os.environ if env is None else env
    status=configuration_status(env);service=None;auth=None
    if status['configured']:
        config=DevelopmentConfig.from_env(env)
        from decimal import Decimal
        rates={'deepseek-v4-pro':('1.32','3.96'),'deepseek-flash':('0.30','1.20')}
        if config.model not in rates:raise ValueError('Explicit currently supported model required')
        minimum=rates[config.model]
        if config.input_usd_per_million<Decimal(minimum[0]) or config.output_usd_per_million<Decimal(minimum[1]):raise ValueError('Peak provider pricing contract required')
        budget=DevelopmentBudget(budget_database,config)
        service=LiveChat(config,budget,DeepSeekAdapter(base_url=config.base_url,model=config.model,api_key=config.api_key))
        auth=DevelopmentAuth(config.access_token)
    return Application(database,runtime,live_chat_service=service,development_auth=auth,real_chat=True,configuration=status)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--database',default='.local/development.sqlite');parser.add_argument('--budget-database',default='.local/development-budget.sqlite');args=parser.parse_args()
    for path in (args.database,args.budget_database):Path(path).parent.mkdir(parents=True,exist_ok=True)
    try:app=application(args.database,args.budget_database,os.environ.get('HCL_DEVELOPMENT_ARTIFACT'))
    except Exception:raise SystemExit('Development configuration or durable budget refused. Check configured variable names and unchanged budget policy; no provider call was made.') from None
    server=serve(app,args.port)
    try:server.serve_forever()
    finally:
        server.server_close();app.close()

if __name__=='__main__':main()
