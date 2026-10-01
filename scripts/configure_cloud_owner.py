"""Run privately by the owner for one-time host setup; never by a chat agent.

Prints secret configuration for copying directly to the hosting provider's
secure environment UI. Do not paste output into chat, commit it, or screenshot it.
No network, database write, account creation, or provider invocation occurs.
"""
import getpass
import json
from pathlib import Path
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.cloud.auth import password_verifier

if __name__=='__main__':
    password=getpass.getpass('Choose the private HCLA owner password (12+ characters): ')
    confirmation=getpass.getpass('Confirm password: ')
    if password!=confirmation:raise SystemExit('Passwords do not match; nothing configured')
    verifier=password_verifier(password)
    del password,confirmation
    print('Copy only into your hosting provider secure environment form. Do not share this output.')
    print('HCLA_OWNER_CONFIG='+json.dumps({'schema_version':1,'login':'owner','verifier':verifier,'temporary_state_key':secrets.token_hex(32)},separators=(',',':')))
