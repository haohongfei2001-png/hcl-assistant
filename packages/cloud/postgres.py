"""Request-scoped Postgres implementation of the existing Controller ledger.

All legacy SQL is static; the compatibility layer translates only its three
SQLite idioms. Every ledger lock is a short transaction-scoped advisory lock,
including reads spanning several queries. No session lock/prepared statement is
used, so Supabase transaction pooling is supported. No schema is created here.
"""
from contextlib import contextmanager
from pathlib import Path
import os
import hashlib
import re
import ssl
import threading
from urllib.parse import urlsplit
from packages.cloud.diagnostics import StartupCode, StartupDiagnostics, close_after_startup_failure
from packages.store.ledger import Ledger, Fault

SCHEMA = 'hcla'
TENANT = 'hcla-owner'
SUPABASE_CA_SHA256 = '700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7'


def system_root_cert():
    """Use the host Python trust bundle, not the wheel's build-machine path.

    psycopg-binary ships a separate OpenSSL whose `system` trust paths may not
    exist in the function image. This keeps full chain/hostname verification.
    No certificate or plaintext fallback is allowed when a bundle is absent.
    """
    path = ssl.get_default_verify_paths().cafile
    if path is not None and Path(path).is_file():return path
    # Standalone Python may have a build-time default absent from Amazon Linux.
    # Only existing platform CA bundles qualify, never a custom/downloaded CA.
    # An explicit broken override remains an error rather than being ignored.
    if 'SSL_CERT_FILE' not in os.environ and 'SSL_CERT_DIR' not in os.environ:
        for candidate in ('/etc/pki/tls/certs/ca-bundle.crt','/etc/ssl/certs/ca-certificates.crt'):
            if Path(candidate).is_file():return candidate
    raise Fault(503, 'System certificate bundle unavailable')


def database_root_cert(dsn):
    """Supabase's private CA is scoped to its database hosts, never global TLS."""
    host=urlsplit(dsn).hostname or ''
    if (re.fullmatch(r'aws-[0-9]+-[a-z0-9-]+\.pooler\.supabase\.com',host)
            or re.fullmatch(r'db\.[a-z0-9]+\.supabase\.co',host)):
        certificate=Path(__file__).with_name('certs')/'supabase-root-2021.crt'
        # Official dashboard certificate, pinned as a public deployment asset.
        if hashlib.sha256(certificate.read_bytes()).hexdigest()!=SUPABASE_CA_SHA256:
            raise Fault(503,'Database certificate bundle unavailable')
        return str(certificate)
    return system_root_cert()

class Row(dict):
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

class Result:
    def __init__(self, cursor): self.cursor = cursor
    def fetchone(self):
        row = self.cursor.fetchone()
        return Row(row) if row is not None else None
    def fetchall(self): return [Row(row) for row in self.cursor.fetchall()]
    def __iter__(self): return iter(self.fetchall())


def translate(sql):
    sql = sql.replace('?', '%s').replace('ORDER BY rowid', 'ORDER BY ordinal')
    if sql.startswith('INSERT OR IGNORE INTO '):
        return sql.replace('INSERT OR IGNORE INTO ', 'INSERT INTO ', 1) + ' ON CONFLICT DO NOTHING'
    for table, columns, conflict in (
        ('objects', 'id,tenant,type,body', 'id'),
        ('records', 'id,tenant,version,body', 'id,version'),
    ):
        prefix = 'INSERT OR REPLACE INTO ' + table + ' VALUES'
        if sql.startswith(prefix):
            updates = 'tenant=EXCLUDED.tenant,body=EXCLUDED.body'
            if table == 'objects': updates += ',type=EXCLUDED.type'
            return sql.replace(prefix, f'INSERT INTO {table} ({columns}) VALUES', 1) + f' ON CONFLICT ({conflict}) DO UPDATE SET {updates}'
    if 'OR REPLACE' in sql or 'OR IGNORE' in sql or 'PRAGMA' in sql:
        raise ValueError('Unsupported ledger SQL')
    return sql

class Driver:
    def __init__(self, store): self.store = store
    def execute(self, sql, params=()):
        # Standalone legacy reads still get the schema, RLS tenant and lock.
        with self.store.lock:
            return Result(self.store.connection.execute(translate(sql), params))
    def close(self): self.store.connection.close()

class Guard:
    def __init__(self, store): self.store=store; self.mutex=threading.RLock(); self.depth=0
    def __enter__(self):
        self.mutex.acquire()
        try:
            if self.depth == 0:
                self.transaction = self.store.connection.transaction()
                self.transaction.__enter__()
                c=self.store.connection
                c.execute('SET LOCAL search_path = hcla, pg_catalog')
                c.execute("SELECT set_config('hcla.tenant', %s, true)", (self.store.tenant,))
                c.execute("SELECT set_config('hcla.member_session', %s, true)", (self.store.member_session_key or '',))
                c.execute("SELECT set_config('hcla.recovery_session', %s, true)", (self.store.recovery_session_key or '',))
                c.execute("SELECT set_config('hcla.recovery_gc', 'off', true)")
                c.execute("SET LOCAL lock_timeout = '5s'")
                c.execute("SET LOCAL statement_timeout = '10s'")
                c.execute('SELECT pg_advisory_xact_lock(171956945, 1)')
                self.store.check_fence()
            self.depth += 1
            return self
        except BaseException:
            if hasattr(self,'transaction'):
                import sys
                self.transaction.__exit__(*sys.exc_info())
            self.mutex.release()
            raise
    def __exit__(self, typ, value, traceback):
        self.depth-=1
        try:
            if self.depth == 0: return self.transaction.__exit__(typ,value,traceback)
        finally: self.mutex.release()

class PostgresLedger(Ledger):
    def __init__(self, dsn, *, connection=None, tenant=TENANT, startup=None):
        startup = startup or StartupDiagnostics()
        startup.mark(StartupCode.DATABASE_ROLE)
        if tenant != TENANT: raise Fault(403,'Cloud owner identity required')
        if connection is None:
            startup.mark(StartupCode.DATABASE_DRIVER)
            import psycopg
            from psycopg.rows import dict_row
            startup.mark(StartupCode.DATABASE_TLS)
            root_cert=database_root_cert(dsn)
            startup.mark(StartupCode.DATABASE_CONNECT)
            try:
                connection=psycopg.connect(dsn,sslmode='verify-full',sslrootcert=root_cert,autocommit=True,prepare_threshold=None,row_factory=dict_row,connect_timeout=5)
            except ssl.SSLError:
                startup.mark(StartupCode.DATABASE_TLS)
                raise
        self.connection=connection; self.tenant=tenant; self.volatile=False; self.member_session_key=None; self.recovery_session_key=None
        try:
            startup.mark(StartupCode.DATABASE_ROLE)
            role=connection.execute("SELECT rolsuper,rolbypassrls,pg_has_role(current_user,'hcla_app','member') AS member FROM pg_roles WHERE rolname=current_user").fetchone()
            if role is None or role['rolsuper'] or role['rolbypassrls'] or not role['member']:
                raise Fault(503,'Restricted cloud database role required')
            self.fence=None; self.lock=Guard(self); self.db=Driver(self)
            startup.mark(StartupCode.DATABASE_SCHEMA)
            with self.lock:
                row=self.connection.execute('SELECT version FROM schema_version WHERE singleton=1').fetchone()
                if row is None or row['version'] != 1: raise Fault(503,'Cloud schema migration required')
        except Exception:
            close_after_startup_failure(connection)
            raise
    def check_fence(self):
        if self.fence is None: return
        run_id, owner=self.fence
        row=self.connection.execute('SELECT owner,expires_at > clock_timestamp() AS valid FROM execution WHERE run_id=%s',(run_id,)).fetchone()
        if row is None or row['owner'] != owner or not row['valid']:
            raise Fault(409,'EXECUTION_OWNERSHIP_EXPIRED')
    def bind_member(self, principal):
        from packages.cloud.member_auth import VerifiedPrincipal
        import uuid
        if (not isinstance(principal,VerifiedPrincipal)
                or not re.fullmatch(r'https://[a-z0-9]{20}\.supabase\.co/auth/v1',principal.issuer)
                or str(uuid.UUID(principal.subject))!=principal.subject
                or type(principal.expires_at) is not int or principal.expires_at<=0
                or self.lock.depth or self.fence is not None
                or self.tenant not in (TENANT,principal.tenant)):
            raise Fault(403,'Verified account identity required')
        self.tenant=principal.tenant
    @contextmanager
    def transaction(self):
        with self.lock: yield
    def close(self): self.connection.close()
