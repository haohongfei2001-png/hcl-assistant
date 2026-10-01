"""Fixed server-only startup codes; never inspect or format failure details."""
from enum import Enum
import sys


class StartupCode(Enum):
    CONFIG = 'CONFIG'
    DATABASE_DRIVER = 'DATABASE_DRIVER'
    DATABASE_CONNECT = 'DATABASE_CONNECT'
    DATABASE_TLS = 'DATABASE_TLS'
    DATABASE_ROLE = 'DATABASE_ROLE'
    DATABASE_SCHEMA = 'DATABASE_SCHEMA'
    TEMPORARY_STORE = 'TEMPORARY_STORE'
    OWNER_AUTH = 'OWNER_AUTH'
    MEMBER_SCHEMA = 'MEMBER_SCHEMA'
    MEMBER_AUTH = 'MEMBER_AUTH'
    RUNTIME_BRIDGE = 'RUNTIME_BRIDGE'
    LIFECYCLE = 'LIFECYCLE'
    PROVIDER_BUDGET = 'PROVIDER_BUDGET'
    PROVIDER_ADAPTER = 'PROVIDER_ADAPTER'
    UNKNOWN = 'UNKNOWN'


class StartupDiagnostics:
    """One instance per startup, including overlapping serverless requests."""
    def __init__(self):
        self.code = StartupCode.UNKNOWN

    def mark(self, code):
        self.code = code if type(code) is StartupCode else StartupCode.UNKNOWN

    def report(self):
        code = self.code if type(self.code) is StartupCode else StartupCode.UNKNOWN
        # Bypass logging handlers: their handleError path can print the active
        # exception traceback if a sink fails. Only a literal bounded line is
        # given to stderr (captured as a server log by the hosting runtime).
        try:
            sys.stderr.write('HCLA_STARTUP_FAILED code=' + code.value + '\n')
        except Exception:
            pass


def close_after_startup_failure(resource):
    """Best-effort cleanup must not expose or replace the original category."""
    if resource is not None:
        try:
            resource.close()
        except Exception:
            pass
