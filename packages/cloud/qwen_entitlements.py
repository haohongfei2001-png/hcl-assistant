"""Member Qwen spending requires a separate explicit CNY entitlement."""
from decimal import Decimal, localcontext
from packages.adapter.development_budget import BudgetError, _key, _money
from packages.cloud.entitlements import Entitlements
from packages.store.ledger import Fault


class QwenEntitlements(Entitlements):
    table = 'qwen_member_entitlements'


class QwenMemberBudget:
    currency = 'CNY'

    def __init__(self, operator, entitlements, auth, session_key, memory):
        self.operator = operator
        self.config = operator.config
        self.store = operator.store
        self.entitlements = entitlements
        self.auth = auth
        self.session_key = session_key
        self.memory = memory
        self._held = None

    def reserve(self, run_id, attempt_id, input_bytes):
        keys = (_key(run_id), _key(attempt_id))
        with self.store.transaction():
            if not self.auth.active(self.session_key):
                raise BudgetError('account_session_expired')
            try:
                grant = self.entitlements.require(self.memory)
            except Fault:
                raise BudgetError('account_entitlement_required') from None
            existing = self.store.db.execute('SELECT grant_id FROM qwen_member_budget_attempts WHERE tenant=? AND run_key=? AND attempt_key=?',
                                             (self.store.tenant, *keys)).fetchone()
            if existing is None:
                rows = self.store.db.execute('SELECT charged_cny FROM qwen_member_budget_attempts WHERE tenant=? AND grant_id=?',
                                             (self.store.tenant, grant['grant_id'])).fetchall()
                with localcontext() as context:
                    context.prec = 64
                    if (len(rows) >= grant['max_requests']
                            or sum((Decimal(r['charged_cny']) for r in rows), Decimal(0)) + self.operator.reservation_cost() > Decimal(grant['max_cost_cny'])):
                        raise BudgetError('account_budget_exhausted')
            admitted = self.operator.reserve(run_id, attempt_id, input_bytes)
            if admitted.granted:
                if existing is not None:
                    raise BudgetError('account_attempt_conflict')
                self.store.db.execute("INSERT INTO qwen_member_budget_attempts(tenant,grant_id,run_key,attempt_key,charged_cny,outcome) VALUES(?,?,?,?,?,'active')",
                                      (self.store.tenant, grant['grant_id'], *keys, _money(admitted.reserved_cost_cny)))
                self._held = keys
            elif existing is None:
                raise BudgetError('account_attempt_owner_required')
            return admitted

    def finish(self, run_id, attempt_id, outcome, input_tokens=None, output_tokens=None, actual_cost_usd=None):
        keys = (_key(run_id), _key(attempt_id))
        if keys != self._held:
            raise BudgetError('account_attempt_owner_required')
        with self.store.transaction():
            self.operator.finish(run_id, attempt_id, outcome, input_tokens, output_tokens, actual_cost_usd)
            row = self.store.db.execute('SELECT charged_cny FROM qwen_budget_attempts WHERE run_key=? AND attempt_key=?', keys).fetchone()
            if row is None:
                raise BudgetError('operator_attempt_missing')
            self.store.db.execute('UPDATE qwen_member_budget_attempts SET charged_cny=?,outcome=? WHERE tenant=? AND run_key=? AND attempt_key=?',
                                  (row['charged_cny'], outcome, self.store.tenant, *keys))
            self._held = None

    def snapshot(self):
        with self.store.transaction():
            grant = self.entitlements.current()
            rows = self.store.db.execute('SELECT charged_cny,outcome FROM qwen_member_budget_attempts WHERE tenant=? AND grant_id=?',
                                         (self.store.tenant, grant['grant_id'] if grant else '')).fetchall()
        with localcontext() as context:
            context.prec = 64
            return {'currency': 'CNY', 'request_count': len(rows),
                    'active_requests': sum(r['outcome'] == 'active' for r in rows),
                    'charged_cost_cny': _money(sum((Decimal(r['charged_cny']) for r in rows), Decimal(0))),
                    'max_requests': grant['max_requests'] if grant else 0,
                    'max_cost_cny': _money(Decimal(grant['max_cost_cny'])) if grant else '0',
                    'actual_provider_cost_cny': None,
                    'cost_basis': 'CONFIGURED_UNCACHED_CNY_RATES_NOT_PROVIDER_INVOICE'}

    def close(self):
        pass
