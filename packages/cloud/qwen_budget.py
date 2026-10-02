"""Separate, non-refundable CNY ledger. No USD rows or grants are reinterpreted."""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from packages.adapter.development_budget import BudgetError, MAX_INPUT_BYTES, _key, _money
from packages.adapter.qwen import INPUT_TOKEN_RESERVATION
from packages.cloud.qwen_config import QwenConfig


@dataclass(frozen=True)
class CnyReservation:
    granted: bool
    reserved_cost_cny: Decimal
    outcome: str


class QwenCloudBudget:
    currency = 'CNY'
    attempts = 'qwen_budget_attempts'

    def __init__(self, store, config):
        if not isinstance(config, QwenConfig):
            raise BudgetError('qwen_configuration_required')
        self.store = store
        self.config = QwenConfig.from_grant(config.as_grant(), config.api_key)
        self._held = None
        with store.transaction():
            row = store.db.execute('SELECT policy FROM qwen_budget_policy WHERE singleton=1').fetchone()
            if row is None:
                raise BudgetError('qwen_budget_not_authorized')
            if row['policy'] != config.policy():
                raise BudgetError('budget_policy_mismatch')

    def _cost(self, input_tokens, output_tokens):
        with localcontext() as context:
            context.prec = 64
            return (Decimal(input_tokens) * self.config.input_cny_per_million
                    + Decimal(output_tokens) * self.config.output_cny_per_million) / Decimal(1000000)

    def reservation_cost(self):
        return self._cost(INPUT_TOKEN_RESERVATION, self.config.reserved_output_tokens)

    def reserve(self, run_id, attempt_id, input_bytes):
        keys = (_key(run_id), _key(attempt_id))
        if type(input_bytes) is not int or not 1 <= input_bytes <= MAX_INPUT_BYTES:
            raise BudgetError('input_byte_limit')
        with self.store.transaction():
            old = self.store.db.execute('SELECT * FROM qwen_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
            if old:
                if old['input_bytes'] != input_bytes:
                    raise BudgetError('attempt_payload_mismatch')
                return CnyReservation(False, Decimal(old['reserved_cny']), old['outcome'])
            rows = self.store.db.execute('SELECT * FROM qwen_budget_attempts').fetchall()
            if any(r['outcome'] == 'active' for r in rows):
                raise BudgetError('concurrency_or_unconfirmed_transport')
            # An already-dispatched old deployment can still own a USD slot.
            # Currency separation must not become a parallel-dispatch bypass.
            if self.store.db.execute("SELECT 1 FROM budget_attempts WHERE outcome='active' LIMIT 1").fetchone():
                raise BudgetError('concurrency_or_unconfirmed_transport')
            trial = self.store.db.execute("SELECT to_regclass('hcla.trial_budget_attempts') AS present").fetchone()['present']
            if trial and self.store.db.execute("SELECT 1 FROM trial_budget_attempts WHERE outcome='active' LIMIT 1").fetchone():
                raise BudgetError('concurrency_or_unconfirmed_transport')
            if len(rows) >= self.config.max_requests:
                raise BudgetError('request_budget_exhausted')
            reservation = self.reservation_cost()
            with localcontext() as context:
                context.prec = 64
                if sum((Decimal(r['charged_cny']) for r in rows), Decimal(0)) + reservation > self.config.max_cost_cny:
                    raise BudgetError('cost_budget_exhausted')
            self.store.db.execute("INSERT INTO qwen_budget_attempts(run_key,attempt_key,input_bytes,reserved_cny,charged_cny,outcome) VALUES(?,?,?,?,?,'active')",
                                  (*keys, input_bytes, _money(reservation), _money(reservation)))
            self._held = keys
            return CnyReservation(True, reservation, 'active')

    def finish(self, run_id, attempt_id, outcome, input_tokens=None,
               output_tokens=None, actual_cost_usd=None):
        keys = (_key(run_id), _key(attempt_id))
        if outcome not in {'completed', 'failed', 'cancelled', 'unknown'}:
            raise BudgetError('invalid_attempt_outcome')
        if keys != self._held:
            raise BudgetError('attempt_owner_required')
        for tokens in (input_tokens, output_tokens):
            if tokens is not None and (type(tokens) is not int or not 0 <= tokens <= 10**12):
                raise BudgetError('invalid_usage')
        if (input_tokens is None) != (output_tokens is None):
            raise BudgetError('incomplete_usage')
        if actual_cost_usd is not None:
            raise BudgetError('provider_invoice_not_supported')
        actual = self._cost(input_tokens, output_tokens) if input_tokens is not None else None
        with self.store.transaction():
            old = self.store.db.execute('SELECT * FROM qwen_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
            if not old or old['outcome'] != 'active':
                raise BudgetError('attempt_already_finished')
            charged = max(Decimal(old['charged_cny']), actual or Decimal(0))
            self.store.db.execute('UPDATE qwen_budget_attempts SET outcome=?,charged_cny=?,actual_cny=?,input_tokens=?,output_tokens=? WHERE run_key=? AND attempt_key=?',
                                  (outcome, _money(charged), _money(actual) if actual is not None else None,
                                   input_tokens, output_tokens, *keys))
            self._held = None

    def snapshot(self):
        with self.store.transaction():
            rows = self.store.db.execute('SELECT * FROM qwen_budget_attempts').fetchall()
        with localcontext() as context:
            context.prec = 64
            charged = sum((Decimal(r['charged_cny']) for r in rows), Decimal(0))
            known = [Decimal(r['actual_cny']) for r in rows if r['actual_cny'] is not None]
            return {'currency': 'CNY', 'request_count': len(rows),
                    'max_requests': self.config.max_requests,
                    'active_requests': sum(r['outcome'] == 'active' for r in rows),
                    'reserved_cost_cny': _money(sum((Decimal(r['reserved_cny']) for r in rows), Decimal(0))),
                    'charged_cost_cny': _money(charged), 'max_cost_cny': _money(self.config.max_cost_cny),
                    'actual_provider_cost_cny': None,
                    'cost_basis': 'CONFIGURED_UNCACHED_CNY_RATES_NOT_PROVIDER_INVOICE',
                    'known_usage_priced_upper_bound_cny': _money(sum(known, Decimal(0))) if known else None,
                    'unknown_usage_requests': len(rows) - len(known),
                    'over_budget': charged > self.config.max_cost_cny}

    def close(self):
        pass
