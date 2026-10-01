"""Explicit four-hour synthetic trial; separate guest identity and budget policy."""
from dataclasses import dataclass,replace
from decimal import Decimal
import hashlib
import hmac
from http.cookies import SimpleCookie
import json
import re
import secrets
import time

from packages.cloud.auth import CloudAuth
from packages.cloud.budget import CloudBudget
from packages.adapter.development_budget import BudgetError,DevelopmentBudget
from types import SimpleNamespace
from packages.store.ledger import Fault, digest

COOKIE = '__Host-hcla-trial'


@dataclass(frozen=True)
class TrialWindow:
    starts_at: int
    expires_at: int

    @classmethod
    def from_value(cls, value):
        if not isinstance(value, dict) or set(value) != {'starts_at', 'expires_at'}:
            raise ValueError('Explicit trial window required')
        start, end = value['starts_at'], value['expires_at']
        if type(start) is not int or type(end) is not int or not 0 < start < end or end-start > 14400:
            raise ValueError('Trial must have one fixed window of at most four hours')
        return cls(start, end)

    def identity(self): return {'starts_at': self.starts_at, 'expires_at': self.expires_at}


class TrialBudget(CloudBudget):
    policies = 'trial_budget_policy'
    attempts = 'trial_budget_attempts'

    def __init__(self, store, config, window):
        self.window = window
        if not isinstance(window, TrialWindow) or config.max_cost_usd > Decimal('10'):
            raise BudgetError('invalid_trial_bounds')
        TrialWindow.from_value(window.identity())
        super().__init__(store, config)

    def _policy(self):
        return trial_policy(self.config,self.window)

    def clock(self):
        with self.store.transaction():
            return float(self.store.db.execute('SELECT EXTRACT(EPOCH FROM clock_timestamp()) AS epoch').fetchone()['epoch'])

    def require_active(self):
        if not self.window.starts_at <= self.clock() < self.window.expires_at:
            raise BudgetError('trial_expired_or_not_started')

    def reserve(self, run_id, attempt_id, input_bytes):
        with self.store.transaction():
            self.require_active()
            return super().reserve(run_id, attempt_id, input_bytes)

    def reconcile_completed(self, run_id, attempt_id):
        # Called only after final Controller publication/cancellation validation.
        # A crash before this conservative release retains the full reservation.
        from packages.adapter.development_budget import _key
        with self.store.transaction():
            self.require_active()
            if self.store.fence is None:return
            execution,owner=self.store.fence
            row=self.store.db.execute('SELECT cancelled,finished FROM execution WHERE run_id=? AND owner=?',(execution,owner)).fetchone()
            # Uncached recheck under the same global transaction lock as cancel.
            if row is None or row['cancelled'] or row['finished']:return
            self.store.db.execute("UPDATE trial_budget_attempts SET charged_usd=actual_usd WHERE run_key=? AND attempt_key=? AND outcome='completed' AND policy_version=3 AND actual_usd IS NOT NULL AND input_tokens>0 AND input_tokens<=1048576 AND output_tokens>0 AND output_tokens<=? AND charged_usd>=actual_usd", (_key(run_id), _key(attempt_id), self.config.max_output_tokens))


def trial_policy(config,window):
    if not isinstance(window,TrialWindow) or config.max_cost_usd>Decimal('10'):raise BudgetError('invalid_trial_bounds')
    TrialWindow.from_value(window.identity())
    policy = json.loads(DevelopmentBudget._policy(SimpleNamespace(config=config)))
    policy.update(version=3, settlement='CONFIRMED_COMPLETED_PEAK_USAGE_ONLY',
                  trial=window.identity(), public_scope='TEMPORARY_SYNTHETIC_ONLY',grant_id=config.budget_id)
    return json.dumps(policy, sort_keys=True, separators=(',', ':'))


def from_database_policy(store,config):
    """Only immutable operator-installed metadata can activate a new trial.

    Key alone has no effect; it stays in the server config, never in the policy.
    Explicit legacy owner grants and test-injected configs are not reinterpreted.
    """
    if config.provider is not None or not getattr(config,'cloud_api_key',''):return config
    with store.transaction():
        present=store.db.execute("SELECT to_regclass('hcla.trial_budget_policy') AS present").fetchone()['present']
        if present is None:return config
        row=store.db.execute('SELECT policy FROM trial_budget_policy WHERE singleton=1').fetchone()
    if row is None:return config
    from packages.cloud.config import strict_json,provider_from_grant
    policy=strict_json(row['policy'])
    window=TrialWindow.from_value(policy['trial'])
    provider=provider_from_grant({'budget_id':policy['grant_id'],'max_requests':policy['max_requests'],
                                 'max_cost_usd':policy['max_cost_usd']},config.cloud_api_key)
    if trial_policy(provider,window)!=row['policy']:raise BudgetError('budget_policy_mismatch')
    return replace(config,provider=provider,trial=window)

class TrialAuth:
    """Purpose-signed cookie grants only the four explicit guest routes."""
    def __init__(self, origin, state_key, budget):
        from urllib.parse import urlsplit
        self.origin = origin; self.host = urlsplit(origin).netloc
        self._key = bytes.fromhex(state_key); self.budget = budget

    def boundary(self, request, mutation=False):
        CloudAuth.boundary(self, request, mutation)

    def _signature(self, value):
        return hmac.new(self._key, ('hcla-public-trial-v1\n'+self.budget._policy()+'\n'+value).encode(), hashlib.sha256).hexdigest()

    def issue(self,cookie=None):
        self.require_active()
        token=None
        if cookie:
            try:
                self.require(cookie)
                parsed=SimpleCookie();parsed.load(cookie);token=parsed[COOKIE].value
            except Fault:pass
        if token is None:
            value = secrets.token_hex(32)+'.'+str(self.budget.window.expires_at)
            token = value+'.'+self._signature(value)
        remaining = max(0, int(self.budget.window.expires_at-self.budget.clock()))
        return COOKIE+'='+token+'; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age='+str(remaining)

    def require(self, cookie):
        self.require_active()
        try:
            parsed = SimpleCookie(); parsed.load(cookie or '')
            value = parsed[COOKIE].value
            if not re.fullmatch(r'[0-9a-f]{64}\.[0-9]{1,12}\.[0-9a-f]{64}', value): raise ValueError()
            nonce, expiry, signature = value.split('.')
            if int(expiry) != self.budget.window.expires_at or not hmac.compare_digest(self._signature(nonce+'.'+expiry), signature): raise ValueError()
            return digest('trial-session\n'+value)
        except (KeyError, ValueError):
            raise Fault(401, 'Temporary trial session required') from None

    def require_active(self):
        try:self.budget.require_active()
        except BudgetError:raise Fault(403,'Temporary trial ended or not started') from None

    def status(self, cookie):
        active = self.budget.window.starts_at <= self.budget.clock() < self.budget.window.expires_at
        authenticated = False
        if active:
            try: self.require(cookie); authenticated = True
            except Fault: pass
        return {'available': active, 'authenticated': authenticated,
                'expires_at': self.budget.window.expires_at, 'temporary_only': True}

    def execution_key(self, session, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9-]{36}', request_id):
            raise Fault(400, 'Request identifier required')
        return digest('trial-execution\n'+session+'\n'+request_id)


class TrialCancellation:
    def __init__(self, cancellation, budget):
        self.cancellation=cancellation;self.budget=budget;self.next_check=0;self.deadline=float('inf')
    def set(self): self.cancellation.set()
    def is_set(self):
        started=time.monotonic()
        if started>=self.deadline:self.cancellation.set()
        if started>=self.next_check:
            try:
                now=self.budget.clock()
                if not self.budget.window.starts_at<=now<self.budget.window.expires_at:self.cancellation.set()
                # Use the time before the DB read: network latency may shorten,
                # but can never extend, the fixed deadline. Never move it later.
                self.deadline=min(self.deadline,started+self.budget.window.expires_at-now)
                self.next_check=started+.25
            except Exception:self.cancellation.set()
        return self.cancellation.is_set()
