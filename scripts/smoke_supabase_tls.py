"""Credential-free TLS-only probe of the owner's verified public shared pooler.

Sends only PostgreSQL SSLRequest and TLS negotiation. Never sends a Postgres
startup/authentication packet, username, password, query, body or provider call.
"""
import json
from pathlib import Path
import socket
import ssl
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from packages.cloud.postgres import database_root_cert

HOST='aws-0-us-west-2.pooler.supabase.com'

def main():
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=database_root_cert('postgresql://'+HOST+'/postgres?sslmode=verify-full'))
    assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname
    with socket.create_connection((HOST,6543),timeout=8) as connection:
        connection.sendall(struct.pack('!II',8,80877103))
        assert connection.recv(1)==b'S','Shared pooler must support TLS'
        with context.wrap_socket(connection,server_hostname=HOST) as secured:
            assert secured.getpeercert()
    print(json.dumps({'public_pooler_tls_only':'PASS','certificate_chain_verified':True,
                      'hostname_verified':True,'postgres_auth_packets':0,'queries':0,'provider_calls':0}))

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Public pooler TLS-only verification failed; no authentication attempted') from None
