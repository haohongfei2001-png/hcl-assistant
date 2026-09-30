"""Bounded handshake over a process boundary; not a production adapter."""
import json
import os
from pathlib import Path
import subprocess
import sys
from packages.runtime_bridge.contract import handshake, load_config


class RuntimeBridge:
    def __init__(self, directory, config=None):
        self.directory = Path(directory); self.config = load_config() if config is None else config

    def handshake(self):
        checked = handshake(self.directory, self.config)
        if checked['handshake_status'] != 'READY': return checked
        try:
            process = subprocess.run([sys.executable, '-I', str(Path(__file__).with_name('worker.py')), str(self.directory)],
                input=json.dumps({'config': self.config}).encode(), capture_output=True, timeout=3,
                env={'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1'})
            if process.returncode or len(process.stdout) > 262144: raise ValueError('invalid response')
            result = json.loads(process.stdout)
            if result != checked: raise ValueError('unverified handshake')
            return result
        except (OSError, ValueError, subprocess.TimeoutExpired):
            checked.update(handshake_status='FAILED', errors=['HANDSHAKE_PROCESS_FAILED'], discovered_capabilities=[])
            return checked
