"""Fail-closed development configuration and a durable, metadata-only budget.

This module neither reads the process environment nor contacts a provider. The
caller supplies a mapping and must reserve the complete serialized prompt size
before dispatch. Reservations are never refunded, including on known success.
The POSIX lock is held until the transport worker has actually stopped, not when
a UI cancellation arrives. Process death releases it; the next opener recovers
unfinished attempts as unknown without replaying or refunding them.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
from typing import Mapping

try:
    import fcntl
except ImportError:  # Fail closed if a non-POSIX host lacks the durable lock.
    fcntl = None

MAX_INPUT_BYTES = 8192
_REQUIRED = (
    'HCLA_DEEPSEEK_API_KEY', 'HCLA_DEEPSEEK_BASE_URL', 'HCLA_DEEPSEEK_MODEL',
    'HCLA_DEV_ACCESS_TOKEN', 'HCLA_DEV_MAX_REQUESTS', 'HCLA_DEV_MAX_COST_USD',
    'HCLA_DEV_INPUT_USD_PER_MILLION', 'HCLA_DEV_OUTPUT_USD_PER_MILLION',
    'HCLA_DEV_MAX_OUTPUT_TOKENS', 'HCLA_DEV_BUDGET_ID',
)
_INTEGER = re.compile(r'[0-9]{1,9}\Z', re.ASCII)
_DECIMAL = re.compile(r'(?:0|[1-9][0-9]{0,8})(?:\.[0-9]{1,12})?\Z', re.ASCII)
_IDENTIFIER = re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z', re.ASCII)
_MODEL = re.compile(r'[A-Za-z0-9_./-]{1,128}\Z', re.ASCII)
_TERMINAL = frozenset(('completed', 'failed', 'cancelled', 'unknown'))


class ConfigurationError(ValueError):
    """Contains variable names only; never interpolates configuration values."""
    def __init__(self, missing=(), invalid=()):
        self.missing = tuple(missing)
        self.invalid = tuple(invalid)
        labels = []
        if self.missing:
            labels.append('missing: ' + ', '.join(self.missing))
        if self.invalid:
            labels.append('invalid: ' + ', '.join(self.invalid))
        super().__init__('Development configuration unavailable (' + '; '.join(labels) + ')')


class BudgetError(ValueError):
    """A stable, non-secret reason code safe to pass to a bounded receipt."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class DevelopmentConfig:
    api_key: str = field(repr=False)
    base_url: str = field(repr=False)
    model: str = field(repr=False)
    access_token: str = field(repr=False)
    max_requests: int
    max_cost_usd: Decimal
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    max_output_tokens: int
    budget_id: str = field(repr=False)

    def __repr__(self):
        return 'DevelopmentConfig(configured=True)'

    @classmethod
    def from_env(cls, env: Mapping[str, str]):
        """Validate only this explicit mapping, with no implicit live defaults."""
        missing = tuple(name for name in _REQUIRED
                        if not isinstance(env.get(name), str) or not env[name].strip())
        if missing:
            raise ConfigurationError(missing=missing)
        values = {name: env[name] for name in _REQUIRED}
        invalid = []
        for name in ('HCLA_DEEPSEEK_API_KEY', 'HCLA_DEV_ACCESS_TOKEN'):
            value = values[name]
            if value != value.strip() or len(value) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
                invalid.append(name)
        if len(values['HCLA_DEV_ACCESS_TOKEN']) < 24:invalid.append('HCLA_DEV_ACCESS_TOKEN')
        # Credentials may only go to the explicitly supported provider origin.
        base = values['HCLA_DEEPSEEK_BASE_URL'].rstrip('/')
        if base not in ('https://api.deepseek.com', 'https://api.deepseek.com/v1'):
            invalid.append('HCLA_DEEPSEEK_BASE_URL')
        if not _MODEL.fullmatch(values['HCLA_DEEPSEEK_MODEL']):
            invalid.append('HCLA_DEEPSEEK_MODEL')
        if not _IDENTIFIER.fullmatch(values['HCLA_DEV_BUDGET_ID']):
            invalid.append('HCLA_DEV_BUDGET_ID')
        integers = {}
        for name in ('HCLA_DEV_MAX_REQUESTS', 'HCLA_DEV_MAX_OUTPUT_TOKENS'):
            value = values[name]
            if not _INTEGER.fullmatch(value) or int(value) <= 0:
                invalid.append(name)
            else:
                integers[name] = int(value)
        decimals = {}
        for name in ('HCLA_DEV_MAX_COST_USD', 'HCLA_DEV_INPUT_USD_PER_MILLION',
                     'HCLA_DEV_OUTPUT_USD_PER_MILLION'):
            value = values[name]
            if not _DECIMAL.fullmatch(value) or Decimal(value) <= 0:
                invalid.append(name)
            else:
                decimals[name] = Decimal(value)
        if invalid:
            raise ConfigurationError(invalid=invalid)
        return cls(values['HCLA_DEEPSEEK_API_KEY'], base, values['HCLA_DEEPSEEK_MODEL'],
                   values['HCLA_DEV_ACCESS_TOKEN'], integers['HCLA_DEV_MAX_REQUESTS'],
                   decimals['HCLA_DEV_MAX_COST_USD'], decimals['HCLA_DEV_INPUT_USD_PER_MILLION'],
                   decimals['HCLA_DEV_OUTPUT_USD_PER_MILLION'],
                   integers['HCLA_DEV_MAX_OUTPUT_TOKENS'], values['HCLA_DEV_BUDGET_ID'])


def configuration_status(env: Mapping[str, str]):
    """No configuration value, endpoint, credential or budget ID is disclosed."""
    try:
        DevelopmentConfig.from_env(env)
    except ConfigurationError as error:
        return {'configured': False, 'missing': list(error.missing), 'invalid': list(error.invalid)}
    return {'configured': True, 'missing': [], 'invalid': []}


@dataclass(frozen=True)
class Reservation:
    granted: bool
    reserved_cost_usd: Decimal
    outcome: str


def _key(value):
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise BudgetError('invalid_attempt_identifier')
    # Even caller identifiers are not stored verbatim in the metadata database.
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def _money(value):
    return format(value, 'f')


class DevelopmentBudget:
    """One immutable authorization policy per dedicated, durable SQLite file.

    Opening with changed ID, caps, rates, model, endpoint or output limit is
    rejected. Key/access-token rotation is allowed. There is no reset API.
    Usage reconciliation records actual cost but uses max(reserved, actual) for
    admission: cheaper completions never create extra authorization capacity.
    """
    def __init__(self, db_path, config: DevelopmentConfig):
        self._mutex = threading.RLock()
        self._held = None
        self._closed = False
        self._db = None
        self._lock_fd = None
        if not isinstance(config, DevelopmentConfig):
            raise BudgetError('configuration_required')
        # Validate constructor-supplied configs too; callers cannot bypass bounds.
        self.config = DevelopmentConfig.from_env({
            'HCLA_DEEPSEEK_API_KEY': config.api_key,
            'HCLA_DEEPSEEK_BASE_URL': config.base_url,
            'HCLA_DEEPSEEK_MODEL': config.model,
            'HCLA_DEV_ACCESS_TOKEN': config.access_token,
            'HCLA_DEV_MAX_REQUESTS': str(config.max_requests),
            'HCLA_DEV_MAX_COST_USD': _money(config.max_cost_usd),
            'HCLA_DEV_INPUT_USD_PER_MILLION': _money(config.input_usd_per_million),
            'HCLA_DEV_OUTPUT_USD_PER_MILLION': _money(config.output_usd_per_million),
            'HCLA_DEV_MAX_OUTPUT_TOKENS': str(config.max_output_tokens),
            'HCLA_DEV_BUDGET_ID': config.budget_id,
        })
        if fcntl is None:
            raise BudgetError('durable_lock_unavailable')
        try:
            raw_path = os.fspath(db_path)
            if not raw_path or raw_path == ':memory:' or raw_path.startswith('file:'):
                raise BudgetError('durable_database_required')
            path = Path(raw_path).resolve()
            # Do not create directories or mix budget data with the body ledger.
            self._lock_fd = os.open(str(path) + '.lock', os.O_RDWR | os.O_CREAT, 0o600)
            self._db = sqlite3.connect(str(path), isolation_level=None, timeout=5,
                                       check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._db.execute('PRAGMA synchronous=FULL')
            with self._transaction():
                tables = {row[0] for row in self._db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                if tables - {'development_budget_policy', 'development_budget_attempts'}:
                    raise BudgetError('dedicated_budget_database_required')
                self._db.execute('''CREATE TABLE IF NOT EXISTS development_budget_policy(
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), policy TEXT NOT NULL)''')
                self._db.execute('''CREATE TABLE IF NOT EXISTS development_budget_attempts(
                    run_key TEXT NOT NULL, attempt_key TEXT NOT NULL,
                    input_bytes INTEGER NOT NULL, reserved_usd TEXT NOT NULL,
                    charged_usd TEXT NOT NULL, outcome TEXT NOT NULL,
                    input_tokens INTEGER, output_tokens INTEGER, actual_usd TEXT,
                    PRIMARY KEY(run_key,attempt_key))''')
                expected = self._policy()
                current = self._db.execute('SELECT policy FROM development_budget_policy WHERE singleton=1').fetchone()
                if current is not None and current['policy'] != expected:
                    raise BudgetError('budget_policy_mismatch')
                if current is None:
                    self._db.execute('INSERT INTO development_budget_policy VALUES(1,?)', (expected,))
            # A live worker holds the lock even while SQLite is idle. Only a
            # process whose owner disappeared can have its active row recovered.
            if self._acquire_dispatch_lock():
                try:
                    with self._transaction():
                        self._db.execute("UPDATE development_budget_attempts SET outcome='unknown' WHERE outcome='active'")
                finally:
                    self._release_dispatch_lock()
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            self._dispose()
            if isinstance(error, (BudgetError, ConfigurationError)):
                raise
            raise BudgetError('budget_database_unavailable') from None

    def __repr__(self):
        return 'DevelopmentBudget(metadata_only=True)'

    def _policy(self):
        c = self.config
        return json.dumps({'version': 2, 'input_reservation': 'FULL_DOCUMENTED_CONTEXT_FOR_SUPPORTED_MODELS', 'budget_key': _key(c.budget_id),
                           'endpoint_model_key': hashlib.sha256((c.base_url + '\n' + c.model).encode()).hexdigest(),
                           'max_requests': c.max_requests, 'max_cost_usd': _money(c.max_cost_usd),
                           'input_usd_per_million': _money(c.input_usd_per_million),
                           'output_usd_per_million': _money(c.output_usd_per_million),
                           'max_output_tokens': c.max_output_tokens, 'max_input_bytes': MAX_INPUT_BYTES},
                          sort_keys=True, separators=(',', ':'))

    @contextmanager
    def _transaction(self):
        self._db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self._db.execute('COMMIT')
        except BaseException:
            self._db.execute('ROLLBACK')
            raise

    def _check_open(self):
        if self._closed:
            raise BudgetError('budget_closed')

    def _acquire_dispatch_lock(self):
        try:
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def _release_dispatch_lock(self):
        fcntl.flock(self._lock_fd, fcntl.LOCK_UN)

    def _cost(self, input_tokens, output_tokens):
        with localcontext() as context:
            context.prec = 64
            return (Decimal(input_tokens) * self.config.input_usd_per_million +
                    Decimal(output_tokens) * self.config.output_usd_per_million) / Decimal(1000000)

    def reserve(self, run_id, attempt_id, input_bytes):
        """Reserve once. Only granted=True authorizes exactly one dispatch.

        input_bytes is the UTF-8 byte count of the complete serialized request
        messages plus any caller-added framing, bounded by MAX_INPUT_BYTES.
        One byte is conservatively treated as one input token; output reserves
        the configured maximum. Caller must enforce that same output limit.
        """
        keys = (_key(run_id), _key(attempt_id))
        if type(input_bytes) is not int or not 1 <= input_bytes <= MAX_INPUT_BYTES:
            raise BudgetError('input_byte_limit')
        with self._mutex:
            self._check_open()
            try:
                row = self._db.execute('SELECT * FROM development_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
                if row:
                    if row['input_bytes'] != input_bytes:
                        raise BudgetError('attempt_payload_mismatch')
                    return Reservation(False, Decimal(row['reserved_usd']), row['outcome'])
                if self._held is not None or not self._acquire_dispatch_lock():
                    raise BudgetError('concurrency_limit')
                keep_lock = False
                try:
                    with self._transaction():
                        # Recheck idempotency and caps after the cross-process lock.
                        row = self._db.execute('SELECT * FROM development_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
                        if row:
                            if row['input_bytes'] != input_bytes:
                                raise BudgetError('attempt_payload_mismatch')
                            return Reservation(False, Decimal(row['reserved_usd']), row['outcome'])
                        rows = self._db.execute('SELECT charged_usd,outcome FROM development_budget_attempts').fetchall()
                        if any(row['outcome'] == 'active' for row in rows):
                            # Lock ownership proves no other worker remains.
                            self._db.execute("UPDATE development_budget_attempts SET outcome='unknown' WHERE outcome='active'")
                        if len(rows) >= self.config.max_requests:
                            raise BudgetError('request_budget_exhausted')
                        # Reserve the entire documented 1M context (rounded upward), not an undocumented byte/token framing estimate.
                        input_upper = 1048576 if self.config.model in {'deepseek-v4-pro','deepseek-flash'} else input_bytes
                        reservation = self._cost(input_upper, self.config.max_output_tokens)
                        with localcontext() as context:
                            context.prec = 64
                            total = sum((Decimal(row['charged_usd']) for row in rows), Decimal(0))
                            if total + reservation > self.config.max_cost_usd:
                                raise BudgetError('cost_budget_exhausted')
                        self._db.execute('''INSERT INTO development_budget_attempts
                            (run_key,attempt_key,input_bytes,reserved_usd,charged_usd,outcome)
                            VALUES(?,?,?,?,?,'active')''', (*keys, input_bytes, _money(reservation), _money(reservation)))
                    self._held = keys
                    keep_lock = True
                    return Reservation(True, reservation, 'active')
                finally:
                    if not keep_lock:
                        self._release_dispatch_lock()
            except (OSError, sqlite3.Error):
                raise BudgetError('budget_database_unavailable') from None

    def finish(self, run_id, attempt_id, outcome, input_tokens=None,
               output_tokens=None, actual_cost_usd=None):
        """Release concurrency only after the worker has stopped.

        Unknown/failed/cancelled attempts retain their conservative reservation.
        Actual usage, when supplied, is charged at the explicit configured rates.
        Provider-reported actual cost can only raise that cost. No return value
        ever constitutes permission to retry or dispatch.
        """
        keys = (_key(run_id), _key(attempt_id))
        if outcome not in _TERMINAL:
            raise BudgetError('invalid_attempt_outcome')
        for tokens in (input_tokens, output_tokens):
            if tokens is not None and (type(tokens) is not int or not 0 <= tokens <= 10**12):
                raise BudgetError('invalid_usage')
        if (input_tokens is None) != (output_tokens is None):
            raise BudgetError('incomplete_usage')
        actual = None
        if input_tokens is not None:
            actual = self._cost(input_tokens, output_tokens)
        if actual_cost_usd is not None:
            try:
                if isinstance(actual_cost_usd, bool):
                    raise ValueError()
                supplied = Decimal(str(actual_cost_usd))
                if not supplied.is_finite() or supplied < 0 or supplied > Decimal('1000000000'):
                    raise ValueError()
            except (InvalidOperation, ValueError, TypeError):
                raise BudgetError('invalid_actual_cost') from None
            actual = supplied if actual is None else max(actual, supplied)
        with self._mutex:
            self._check_open()
            try:
                with self._transaction():
                    row = self._db.execute('SELECT * FROM development_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
                    if row is None:
                        raise BudgetError('attempt_not_reserved')
                    if row['outcome'] == 'active' and self._held != keys:
                        raise BudgetError('attempt_owner_required')
                    if row['outcome'] != 'active' and row['outcome'] != outcome:
                        raise BudgetError('attempt_already_finished')
                    if (input_tokens is not None and row['input_tokens'] is not None
                            and (row['input_tokens'], row['output_tokens']) != (input_tokens, output_tokens)):
                        raise BudgetError('usage_already_recorded')
                    previous_actual = Decimal(row['actual_usd']) if row['actual_usd'] is not None else None
                    if previous_actual is not None:
                        actual = previous_actual if actual is None else max(previous_actual, actual)
                    charged = max(Decimal(row['charged_usd']), actual or Decimal(0))
                    self._db.execute('''UPDATE development_budget_attempts SET outcome=?,
                        input_tokens=COALESCE(input_tokens,?), output_tokens=COALESCE(output_tokens,?),
                        actual_usd=?, charged_usd=? WHERE run_key=? AND attempt_key=?''',
                        (outcome, input_tokens, output_tokens,
                         _money(actual) if actual is not None else None, _money(charged), *keys))
                if self._held == keys:
                    self._held = None
                    self._release_dispatch_lock()
            except (OSError, sqlite3.Error):
                raise BudgetError('budget_database_unavailable') from None

    def snapshot(self):
        """Return aggregate metadata only; absent actual cost stays unknown."""
        with self._mutex:
            self._check_open()
            try:
                rows = self._db.execute('SELECT charged_usd,reserved_usd,outcome,actual_usd FROM development_budget_attempts').fetchall()
                with localcontext() as context:
                    context.prec = 64
                    charged = sum((Decimal(row['charged_usd']) for row in rows), Decimal(0))
                    reserved = sum((Decimal(row['reserved_usd']) for row in rows), Decimal(0))
                    known = [Decimal(row['actual_usd']) for row in rows if row['actual_usd'] is not None]
                    return {'request_count': len(rows), 'max_requests': self.config.max_requests,
                            'active_requests': sum(row['outcome'] == 'active' for row in rows),
                            'reserved_cost_usd': _money(reserved), 'charged_cost_usd': _money(charged),
                            'max_cost_usd': _money(self.config.max_cost_usd),
                            'actual_provider_cost_usd': None,
                            'cost_basis': 'CONFIGURED_PEAK_RATES_NOT_PROVIDER_INVOICE',
                            'known_usage_priced_upper_bound_usd': _money(sum(known, Decimal(0))) if known else None,
                            'unknown_usage_requests': len(rows) - len(known),
                            'over_budget': charged > self.config.max_cost_usd}
            except sqlite3.Error:
                raise BudgetError('budget_database_unavailable') from None

    def _dispose(self):
        if self._db is not None:
            self._db.close()
            self._db = None
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None
        self._closed = True

    def close(self):
        with self._mutex:
            if self._held is not None:
                raise BudgetError('active_attempt_must_finish')
            if not self._closed:
                self._dispose()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
