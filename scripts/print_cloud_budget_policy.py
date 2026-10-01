"""Owner-only metadata helper. Never installs or renews a budget automatically.

Use only after a NEW bounded grant has been explicitly approved. It prints the
immutable policy JSON for the operator's restricted database setup step, without
printing keys, endpoint, account password or raw grant identifier.
"""
from pathlib import Path
import os
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.cloud.config import CloudConfig
from packages.adapter.development_budget import DevelopmentBudget

if __name__=='__main__':
    try:
        config=CloudConfig.from_env(os.environ)
        if config.provider is None:raise ValueError()
        print(DevelopmentBudget._policy(SimpleNamespace(config=config.provider)))
    except Exception:raise SystemExit('Approved cloud provider policy configuration required; no budget installed') from None
