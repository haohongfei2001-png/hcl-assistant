"""One global CNY500 owner budget per database-derived Shanghai calendar month.

Immutable template/period/attempt guards are also enforced by the additive SQL
migration. Old grants and attempts are never reinterpreted or reset.
"""
from decimal import Decimal, localcontext
from packages.adapter.development_budget import BudgetError, MAX_INPUT_BYTES, _key, _money
from packages.cloud.qwen_budget import CnyReservation
from packages.cloud.qwen_config import QwenConfig


class QwenMonthlyBudget:
    currency='CNY'

    def __init__(self,store,config):
        if not isinstance(config,QwenConfig) or config.monthly is None:
            raise BudgetError('monthly_qwen_configuration_required')
        self.store=store;self.config=QwenConfig.from_grant(config.as_grant(),config.api_key)
        self._held=None;self._dispatch_cap=config.max_output_tokens
        with store.transaction():
            row=store.db.execute('SELECT policy FROM qwen_monthly_authorization WHERE singleton=1').fetchone()
            if row is None:raise BudgetError('monthly_qwen_not_authorized')
            if row['policy']!=self.config.policy():raise BudgetError('budget_policy_mismatch')

    def _owner(self):
        if self.store.tenant!='hcla-owner':raise BudgetError('monthly_owner_scope_required')

    def _cost(self,input_tokens,output_tokens):
        with localcontext() as context:
            context.prec=64
            return (Decimal(input_tokens)*self.config.input_cny_per_million+
                    Decimal(output_tokens)*self.config.output_cny_per_million)/Decimal(1000000)

    def _period(self):
        return self.store.db.execute("SELECT to_char(hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai','YYYY-MM') AS period_key").fetchone()['period_key']

    def smoke_ready(self):
        with self.store.transaction():
            return self.store.db.execute("SELECT 1 FROM qwen_monthly_attempts WHERE kind='SMOKE' AND outcome='completed' AND settled=true LIMIT 1").fetchone() is not None

    def authorize_request(self,request,conversation):
        self._owner()
        if not self.smoke_ready():self.config.authorize_request(request,conversation)

    def dispatch_output_tokens(self):
        return self._dispatch_cap

    def reserve(self,run_id,attempt_id,input_bytes):
        self._owner();keys=(_key(run_id),_key(attempt_id))
        if type(input_bytes) is not int or not 1<=input_bytes<=MAX_INPUT_BYTES:raise BudgetError('input_byte_limit')
        if self.store.fence is None:raise BudgetError('execution_owner_required')
        execution,owner=self.store.fence
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM qwen_monthly_attempts WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if old:
                if old['input_bytes']!=input_bytes:raise BudgetError('attempt_payload_mismatch')
                return CnyReservation(False,Decimal(old['reserved_cny']),old['outcome'],old['period_key'])
            ready=self.smoke_ready();self._dispatch_cap=self.config.max_output_tokens
            period=self._period()
            self.store.db.execute('INSERT INTO qwen_monthly_periods(period_key) VALUES(?) ON CONFLICT(period_key) DO NOTHING',(period,))
            reservation=self._cost(self.config.input_token_reservation,self._dispatch_cap+10)
            window=self.store.db.execute("SELECT ends_at>hcla.qwen_monthly_clock()+interval '300 seconds' AS open FROM qwen_monthly_periods WHERE period_key=?",(period,)).fetchone()
            if not window or not window['open']:raise BudgetError('monthly_boundary_pause')
            rows=self.store.db.execute('SELECT charged_cny,outcome FROM qwen_monthly_attempts WHERE period_key=?',(period,)).fetchall()
            with localcontext() as context:
                context.prec=64
                if sum((Decimal(r['charged_cny']) for r in rows),Decimal(0))+reservation>500:
                    raise BudgetError('cost_budget_exhausted')
            if len(rows)>=self.config.max_requests:raise BudgetError('request_budget_exhausted')
            # Database trigger derives policy/period, enforces the aggregate cap,
            # owner scope, calendar cutoff, immutable row and cross-provider slot.
            try:
                self.store.db.execute("INSERT INTO qwen_monthly_attempts(run_key,attempt_key,period_key,input_bytes,output_cap,kind,execution_run_id,execution_owner,reserved_cny,charged_cny,outcome) VALUES(?,?,?,?,?,?,?,?,?,?,'active')",
                    (*keys,period,input_bytes,self._dispatch_cap,'OWNER' if ready else 'SMOKE',execution,owner,_money(reservation),_money(reservation)))
            except Exception:
                # Never expose provider/database exception text. The transaction
                # rolls back completely; no transport has been constructed here.
                raise BudgetError('monthly_budget_or_execution_gate_refused') from None
            self._held=keys
            return CnyReservation(True,reservation,'active',period)

    def finish(self,run_id,attempt_id,outcome,input_tokens=None,output_tokens=None,actual_cost_usd=None):
        keys=(_key(run_id),_key(attempt_id))
        if keys!=self._held:raise BudgetError('attempt_owner_required')
        if outcome not in {'completed','failed','cancelled','unknown'}:raise BudgetError('invalid_attempt_outcome')
        for tokens in (input_tokens,output_tokens):
            if tokens is not None and (type(tokens) is not int or not 0<=tokens<=10**12):raise BudgetError('invalid_usage')
        if (input_tokens is None)!=(output_tokens is None):raise BudgetError('incomplete_usage')
        if actual_cost_usd is not None:raise BudgetError('provider_invoice_not_supported')
        actual=self._cost(input_tokens,output_tokens) if input_tokens is not None else None
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM qwen_monthly_attempts WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if not old or old['outcome']!='active':raise BudgetError('attempt_already_finished')
            charged=max(Decimal(old['reserved_cny']),actual or Decimal(0))
            self.store.db.execute('UPDATE qwen_monthly_attempts SET outcome=?,charged_cny=?,input_tokens=?,output_tokens=?,actual_cny=? WHERE run_key=? AND attempt_key=?',
                (outcome,_money(charged),input_tokens,output_tokens,_money(actual) if actual is not None else None,*keys))
            self._held=None

    def reconcile_completed(self,run_id,attempt_id):
        # Called only after Controller publication and cancellation validation.
        # Database guard rechecks execution ownership, usage and row transitions.
        keys=(_key(run_id),_key(attempt_id))
        with self.store.transaction():
            row=self.store.db.execute('SELECT * FROM qwen_monthly_attempts WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if not row or row['outcome']!='completed' or row['settled']:return
            if row['actual_cny'] is None:return
            self.store.db.execute('UPDATE qwen_monthly_attempts SET charged_cny=actual_cny,settled=true WHERE run_key=? AND attempt_key=?',keys)

    def snapshot(self):
        with self.store.transaction():
            period=self._period()
            rows=self.store.db.execute('SELECT * FROM qwen_monthly_attempts WHERE period_key=?',(period,)).fetchall()
        with localcontext() as context:
            context.prec=64
            charged=sum((Decimal(r['charged_cny']) for r in rows),Decimal(0))
            known=[Decimal(r['actual_cny']) for r in rows if r['actual_cny'] is not None]
            return {'currency':'CNY','period':period,'timezone':'Asia/Shanghai','scope':'OWNER_ONLY',
                    'request_count':len(rows),'max_requests':self.config.max_requests,
                    'active_requests':sum(r['outcome']=='active' for r in rows),
                    'charged_cost_cny':_money(charged),'max_cost_cny':'500',
                    'remaining_cny':_money(max(Decimal(0),Decimal(500)-charged)),
                    'actual_provider_cost_cny':None,'cost_basis':'CONFIGURED_UNCACHED_CNY_RATES_NOT_PROVIDER_INVOICE',
                    'known_usage_priced_upper_bound_cny':_money(sum(known,Decimal(0))) if known else None,
                    'unknown_usage_requests':len(rows)-len(known),'over_budget':charged>500}

    def close(self):pass
