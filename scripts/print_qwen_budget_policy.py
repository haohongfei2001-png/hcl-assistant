"""Offline metadata conversion only. Never reads a key, installs policy or calls Qwen."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.cloud.config import strict_json
from packages.cloud.qwen_config import QwenConfig


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--approved-grant', required=True, help='Explicit approved non-secret Beijing CNY grant JSON')
    args = parser.parse_args()
    try:
        print(QwenConfig.from_grant(strict_json(args.approved_grant), 'offline-policy-placeholder').policy())
    except Exception:
        raise SystemExit('Explicit bounded Qwen CNY grant required; no policy installed or provider called') from None
