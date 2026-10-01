"""Server-owned account rights and atomic user + operator admission.

No membership claim from a request/JWT can grant rights. Unknown costs retain
the same full reservation as the operator budget. No billing is implemented.
"""
from decimal import Decimal, localcontext
import threading
import time
from packages.adapter.development_budget import BudgetError, _key, _money
from packages.store.ledger import Fault


class Entitlements:
    def __init__(self, store): self.store=store

    def current(self):
        with self.store.transaction():
            rows=self.store.db.execute('SELECT * FROM member_entitlements WHERE tenant=? AND enabled=true AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp()',(self.store.tenant,)).fetchall()
        # Ambiguous overlapping grants fail closed instead of summing capacity.
        return rows[0] if len(rows)==1 else None

    def require(self, memory):
        row=self.current()
        if row is None or not row['temporary_enabled' if memory=='TEMPORARY' else 'persistent_enabled']:
            raise Fault(403,'当前账号没有此项使用权限，请联系管理员')
        return row

    def status(self):
        row=self.current()
        if row is None:return {'enabled':False,'temporary':False,'persistent':False,'reason':'尚无有效使用权限'}
        return {'enabled':True,'temporary':row['temporary_enabled'],'persistent':row['persistent_enabled'],
                'expires_at':int(row['expires_at'].timestamp()),'reason':None}


class MemberBudget:
    def __init__(self, operator, entitlements, auth, session_key, memory):
        self.operator=operator;self.config=operator.config;self.store=operator.store
        self.entitlements=entitlements;self.auth=auth;self.session_key=session_key;self.memory=memory
        self._held=None

    def reserve(self, run_id, attempt_id, input_bytes):
        keys=(_key(run_id),_key(attempt_id))
        with self.store.transaction():
            if not self.auth.active(self.session_key):raise BudgetError('account_session_expired')
            try:grant=self.entitlements.require(self.memory)
            except Fault:raise BudgetError('account_entitlement_required') from None
            existing=self.store.db.execute('SELECT grant_id FROM member_budget_attempts WHERE tenant=? AND run_key=? AND attempt_key=?',(self.store.tenant,*keys)).fetchone()
            if existing is None:
                rows=self.store.db.execute('SELECT charged_usd FROM member_budget_attempts WHERE tenant=? AND grant_id=?',(self.store.tenant,grant['grant_id'])).fetchall()
                reserve=self.operator._cost(1048576,self.config.max_output_tokens)
                with localcontext() as context:
                    context.prec=64
                    if len(rows)>=grant['max_requests'] or sum((Decimal(row['charged_usd']) for row in rows),Decimal(0))+reserve>Decimal(grant['max_cost_usd']):
                        raise BudgetError('account_budget_exhausted')
            admitted=self.operator.reserve(run_id,attempt_id,input_bytes)
            if admitted.granted:
                if existing is not None:raise BudgetError('account_attempt_conflict')
                self.store.db.execute("INSERT INTO member_budget_attempts(tenant,grant_id,run_key,attempt_key,charged_usd,outcome) VALUES(?,?,?,?,?,'active')",(self.store.tenant,grant['grant_id'],*keys,_money(admitted.reserved_cost_usd)))
                self._held=keys
            elif existing is None:raise BudgetError('account_attempt_owner_required')
            return admitted

    def finish(self, run_id, attempt_id, outcome, input_tokens=None, output_tokens=None, actual_cost_usd=None):
        keys=(_key(run_id),_key(attempt_id))
        if keys!=self._held:raise BudgetError('account_attempt_owner_required')
        with self.store.transaction():
            self.operator.finish(run_id,attempt_id,outcome,input_tokens,output_tokens,actual_cost_usd)
            row=self.store.db.execute('SELECT charged_usd FROM budget_attempts WHERE run_key=? AND attempt_key=?',keys).fetchone()
            if row is None:raise BudgetError('operator_attempt_missing')
            self.store.db.execute('UPDATE member_budget_attempts SET charged_usd=?,outcome=? WHERE tenant=? AND run_key=? AND attempt_key=?',(row['charged_usd'],outcome,self.store.tenant,*keys))
            self._held=None

    def snapshot(self):
        with self.store.transaction():
            grant=self.entitlements.current()
            rows=self.store.db.execute('SELECT charged_usd,outcome FROM member_budget_attempts WHERE tenant=? AND grant_id=?',(self.store.tenant,grant['grant_id'] if grant else '')).fetchall()
        return {'request_count':len(rows),'active_requests':sum(row['outcome']=='active' for row in rows),
                'charged_cost_usd':_money(sum((Decimal(row['charged_usd']) for row in rows),Decimal(0))),
                'max_requests':grant['max_requests'] if grant else 0,
                'max_cost_usd':_money(grant['max_cost_usd']) if grant else '0',
                'actual_provider_cost_usd':None,'cost_basis':'CONFIGURED_PEAK_RATES_NOT_PROVIDER_INVOICE'}

    def close(self):pass


class MemberCancellation:
    def __init__(self, cancellation, auth, session_key, entitlements, memory):
        self.cancellation=cancellation;self.auth=auth;self.session_key=session_key
        self.entitlements=entitlements;self.memory=memory;self.next_check=0;self.lock=threading.RLock()
    def set(self):self.cancellation.set()
    def is_set(self):
        # Store lock precedes event lock, matching Controller callbacks.
        with self.auth.store.lock,self.lock:
            if time.monotonic()>=self.next_check:
                try:
                    if not self.auth.active(self.session_key):self.set()
                    self.entitlements.require(self.memory)
                except Exception:self.set()
                self.next_check=time.monotonic()+.25
        return self.cancellation.is_set()
