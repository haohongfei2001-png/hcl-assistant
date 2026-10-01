"""Load the selected host CA bundle through the pinned wheel's actual TLS library.

Linux cloud CI only. No socket, database authentication, query or provider call.
This verifies local trust loading, not a remote server certificate or connection.
"""
import ctypes
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psycopg
import psycopg_binary
from psycopg.conninfo import conninfo_to_dict
from packages.cloud.postgres import system_root_cert


def main():
    assert psycopg.__version__ == '3.2.12'
    assert psycopg.pq.__impl__ == 'binary'
    for query in ('sslmode=verify-full&requiressl=0', 'sslmode=verify-full&sslmode='):
        parsed = conninfo_to_dict('postgresql://synthetic@db.example.test/postgres?'+query,
                                 sslmode='verify-full', sslrootcert=system_root_cert())
        assert parsed['sslmode'] == 'verify-full'
    libs = Path(psycopg_binary.__file__).parent.parent / 'psycopg_binary.libs'
    ssl_paths, crypto_paths = list(libs.glob('libssl-*.so.*')), list(libs.glob('libcrypto-*.so.*'))
    assert len(ssl_paths) == len(crypto_paths) == 1
    tls, crypto = ctypes.CDLL(str(ssl_paths[0])), ctypes.CDLL(str(crypto_paths[0]))
    pointer = ctypes.c_void_p
    tls.TLS_client_method.restype = pointer
    tls.SSL_CTX_new.argtypes = [pointer]; tls.SSL_CTX_new.restype = pointer
    tls.SSL_CTX_load_verify_locations.argtypes = [pointer, ctypes.c_char_p, ctypes.c_char_p]
    tls.SSL_CTX_load_verify_locations.restype = ctypes.c_int
    tls.SSL_CTX_get_cert_store.argtypes = [pointer]; tls.SSL_CTX_get_cert_store.restype = pointer
    tls.SSL_CTX_free.argtypes = [pointer]; tls.SSL_CTX_free.restype = None
    crypto.X509_STORE_get0_objects.argtypes = [pointer]; crypto.X509_STORE_get0_objects.restype = pointer
    crypto.OPENSSL_sk_num.argtypes = [pointer]; crypto.OPENSSL_sk_num.restype = ctypes.c_int
    context = tls.SSL_CTX_new(tls.TLS_client_method())
    assert context
    try:
        assert tls.SSL_CTX_load_verify_locations(context, system_root_cert().encode(), None) == 1
        count = crypto.OPENSSL_sk_num(crypto.X509_STORE_get0_objects(tls.SSL_CTX_get_cert_store(context)))
        assert count > 0, 'Host trust bundle must contain certificates'
    finally:
        tls.SSL_CTX_free(context)
    print(json.dumps({'pinned_client': 'psycopg-binary==3.2.12',
                      'explicit_host_ca_load': 'PASS', 'nonempty_trust_store': True,
                      'explicit_verify_full_overrides_uri_aliases': 'PASS',
                      'network_connections': 0, 'provider_calls': 0}))


if __name__ == '__main__': main()
