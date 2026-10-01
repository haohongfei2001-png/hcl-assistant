"""Metadata-only helper for an explicitly approved grant; never reads secrets."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.cloud.config import provider_from_grant
from packages.adapter.development_budget import DevelopmentBudget

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--approved-grant',required=True,help='Non-secret JSON: budget_id, max_requests, max_cost_usd');args=parser.parse_args()
    try:
        config=provider_from_grant(json.loads(args.approved_grant),'offline-policy-placeholder')
        print(DevelopmentBudget._policy(SimpleNamespace(config=config)))
    except Exception:raise SystemExit('Explicit approved bounded grant required; no budget installed') from None
