"""Postgres reservations share the Controller transaction and survive instances."""
from decimal import Decimal, localcontext
from packages.adapter.development_budget import (DevelopmentBudget, DevelopmentConfig,
    BudgetError, Reservation, MAX_INPUT_BYTES, _key, _money)

class CloudBudget(DevelopmentBudget):
    policies='budget_policy'
    attempts='budget_attempts'
    def __init__(self, store, config):
        self.store=store;self.config=config;self._held=None
        if not isinstance(config,DevelopmentConfig): raise BudgetError('configuration_required')
        with store.transaction():
            current=store.db.execute('SELECT policy FROM '+self.policies+' WHERE singleton=1').fetchone()
            expected=self._policy()
            if current is None:
                # Policy creation is an explicit operator setup step, never a cold start.
                raise BudgetError('cloud_budget_not_authorized')
            if current['policy'] != expected: raise BudgetError('budget_policy_mismatch')
    def reserve(self, run_id, attempt_id, input_bytes):
        keys=(_key(run_id),_key(attempt_id))
        if type(input_bytes) is not int or not 1<=input_bytes<=MAX_INPUT_BYTES: raise BudgetError('input_byte_limit')
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM '+self.attempts+' WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if old:
                if old['input_bytes']!=input_bytes: raise BudgetError('attempt_payload_mismatch')
                return Reservation(False,Decimal(old['reserved_usd']),old['outcome'])
            rows=self.store.db.execute('SELECT * FROM '+self.attempts).fetchall()
            if any(r['outcome']=='active' for r in rows): raise BudgetError('concurrency_or_unconfirmed_transport')
            qwen=self.store.db.execute("SELECT to_regclass('hcla.qwen_budget_attempts') AS present").fetchone()['present']
            if qwen and self.store.db.execute("SELECT 1 FROM qwen_budget_attempts WHERE outcome='active' LIMIT 1").fetchone():
                raise BudgetError('concurrency_or_unconfirmed_transport')
            if len(rows)>=self.config.max_requests: raise BudgetError('request_budget_exhausted')
            reservation=self._cost(1048576,self.config.max_output_tokens)
            with localcontext() as context:
                context.prec=64
                if sum((Decimal(r['charged_usd']) for r in rows),Decimal(0))+reservation>self.config.max_cost_usd: raise BudgetError('cost_budget_exhausted')
            self.store.db.execute("INSERT INTO "+self.attempts+"(run_key,attempt_key,input_bytes,reserved_usd,charged_usd,outcome) VALUES(?,?,?,?,?,'active')",(*keys,input_bytes,_money(reservation),_money(reservation)))
            self._held=keys
            return Reservation(True,reservation,'active')
    def finish(self, run_id, attempt_id, outcome, input_tokens=None, output_tokens=None, actual_cost_usd=None):
        keys=(_key(run_id),_key(attempt_id))
        if outcome not in {'completed','failed','cancelled','unknown'}: raise BudgetError('invalid_attempt_outcome')
        if keys!=self._held: raise BudgetError('attempt_owner_required')
        for tokens in (input_tokens,output_tokens):
            if tokens is not None and (type(tokens) is not int or not 0<=tokens<=10**12): raise BudgetError('invalid_usage')
        if (input_tokens is None)!=(output_tokens is None): raise BudgetError('incomplete_usage')
        if actual_cost_usd is not None: raise BudgetError('provider_invoice_not_supported')
        actual=self._cost(input_tokens,output_tokens) if input_tokens is not None else None
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM '+self.attempts+' WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if not old or old['outcome']!='active': raise BudgetError('attempt_already_finished')
            charged=max(Decimal(old['charged_usd']),actual or Decimal(0))
            self.store.db.execute('UPDATE '+self.attempts+' SET outcome=?,charged_usd=?,actual_usd=?,input_tokens=?,output_tokens=? WHERE run_key=? AND attempt_key=?',(outcome,_money(charged),_money(actual) if actual is not None else None,input_tokens,output_tokens,*keys))
            self._held=None
    def snapshot(self):
        with self.store.transaction():
            rows=self.store.db.execute('SELECT * FROM '+self.attempts).fetchall()
            with localcontext() as context:
                context.prec=64
                charged=sum((Decimal(r['charged_usd']) for r in rows),Decimal(0))
                reserved=sum((Decimal(r['reserved_usd']) for r in rows),Decimal(0))
                known=[Decimal(r['actual_usd']) for r in rows if r['actual_usd'] is not None]
                return {'request_count':len(rows),'max_requests':self.config.max_requests,
                        'active_requests':sum(r['outcome']=='active' for r in rows),
                        'reserved_cost_usd':_money(reserved),'charged_cost_usd':_money(charged),
                        'max_cost_usd':_money(self.config.max_cost_usd),'actual_provider_cost_usd':None,
                        'cost_basis':'CONFIGURED_PEAK_RATES_NOT_PROVIDER_INVOICE',
                        'known_usage_priced_upper_bound_usd':_money(sum(known,Decimal(0))) if known else None,
                        'unknown_usage_requests':len(rows)-len(known),'over_budget':charged>self.config.max_cost_usd}
    def close(self): pass
