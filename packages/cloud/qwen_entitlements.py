"""Member Qwen spending requires a separate explicit CNY entitlement."""
from decimal import Decimal, localcontext
from packages.adapter.development_budget import BudgetError, _key, _money
from packages.cloud.entitlements import Entitlements
from packages.store.ledger import Fault


class QwenEntitlements(Entitlements):
    table = 'qwen_member_entitlements'

    def __init__(self,store,*,readiness=False,readiness_authorization=None):
        super().__init__(store);self.readiness=readiness;self.readiness_authorization=readiness_authorization;self._test_schema=None

    def test_schema(self):
        if self._test_schema is None:
            self._test_schema=bool(self.store.db.execute("SELECT to_regclass('hcla.qwen_member_test_entitlements') IS NOT NULL AS present").fetchone()['present'])
        return self._test_schema

    def current(self):
        with self.store.transaction():
            paid=self.store.db.execute('SELECT * FROM qwen_member_entitlements WHERE tenant=? AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp()',(self.store.tenant,)).fetchall()
            tests=self.store.db.execute('SELECT * FROM qwen_member_test_entitlements WHERE tenant=? AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp()',(self.store.tenant,)).fetchall() if self.test_schema() else []
            # No preference or summing across overlapping paid/testing grants.
            if len(paid)+len(tests)!=1:return None
            if tests:
                row=tests[0]
                verified=self.store.db.execute("SELECT parent_policy_sha256=encode(sha256(convert_to(policy,'UTF8')),'hex') AS verified FROM qwen_member_test_entitlements CROSS JOIN qwen_monthly_authorization WHERE tenant=? AND grant_id=? AND singleton=1",(self.store.tenant,row['grant_id'])).fetchone()
                return dict(row,access_kind='TEST_ONLY') if verified and verified['verified'] else None
            row=paid[0]
            if not (row['paid_membership'] and row['payment_verification'] in {'ADMIN_VERIFIED','TRUSTED_PAYMENT_EVENT'} and row['paid_evidence_digest'] and row['paid_verified_at']):return None
            verified=self.store.db.execute('SELECT paid_verified_at<=clock_timestamp() AS verified FROM qwen_member_entitlements WHERE tenant=? AND grant_id=?',(self.store.tenant,row['grant_id'])).fetchone()
            return dict(row,access_kind='PAID_MEMBERSHIP') if verified and verified['verified'] else None

    def require(self,memory):
        row=super().require(memory)
        if self.readiness:
            if memory!='TEMPORARY' or not self.readiness_authorization:raise Fault(403,'模型连接验证尚未获准')
            authorization=self.store.db.execute("SELECT 1 FROM qwen_member_readiness_authorizations r JOIN qwen_monthly_authorization a ON a.singleton=1 WHERE r.authorization_id=? AND r.enabled AND r.starts_at<=clock_timestamp() AND r.expires_at>clock_timestamp() AND r.parent_policy_sha256=encode(sha256(convert_to(a.policy,'UTF8')),'hex')",(self.readiness_authorization,)).fetchone()
            if not authorization:raise Fault(403,'模型连接验证授权已失效')
        if row['access_kind']=='TEST_ONLY' and ((self.readiness and (memory!='TEMPORARY' or not row['readiness_enabled'])) or (not self.readiness and not row['chat_enabled'])):
            raise Fault(403,'当前测试资格不包含这项使用权限')
        return row

    def status(self):
        row=self.current()
        result={'enabled':False,'temporary':False,'persistent':False,'membership_required':True,'reason':'会员或测试资格未开通、已到期或已停用；注册账号不包含模型使用权限'}
        if row is None:return result
        enabled=row['access_kind']=='PAID_MEMBERSHIP' or bool(row['readiness_enabled' if self.readiness else 'chat_enabled'])
        result.update(enabled=enabled,temporary=bool(enabled and row['temporary_enabled']),persistent=bool(enabled and row['persistent_enabled'] and not self.readiness),expires_at=int(row['expires_at'].timestamp()),access_kind=row['access_kind'],reason=None if enabled else '测试资格有效，但未获准日常聊天；已有记录仍可查看')
        if row['access_kind']=='TEST_ONLY':
            result.update(test_max_requests=row['max_requests'],test_max_cost_cny=str(row['max_cost_cny']),test_chat_enabled=row['chat_enabled'],test_readiness_enabled=row['readiness_enabled'])
        return result


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


class QwenMonthlyMemberBudget:
    """Existing member rights restrict, never replenish, the shared monthly pool.

    Audit and charges live once in the actor-isolated monthly attempt row. There
    is no independently funded per-member monthly ledger or mirrored settlement.
    """
    currency='CNY'
    def __init__(self,operator,entitlements,auth,session_key,memory):
        self.operator=operator;self.config=operator.config;self.store=operator.store
        self.entitlements=entitlements;self.auth=auth;self.session_key=session_key;self.memory=memory
        self._grant_id=None
    def _require(self):
        if not self.auth.active(self.session_key):raise BudgetError('account_session_expired')
        try:grant=self.entitlements.require(self.memory)
        except Fault:raise BudgetError('account_entitlement_required') from None
        if self._grant_id is not None and grant['grant_id']!=self._grant_id:raise BudgetError('account_entitlement_changed')
        return grant
    def authorize_request(self,request,conversation):
        actual=conversation.get('memory')
        if actual not in {'TEMPORARY','CONVERSATION','TOPIC'} or (actual=='TEMPORARY')!=(self.memory=='TEMPORARY'):
            raise BudgetError('account_memory_scope_mismatch')
        self.memory=actual
        with self.store.transaction():
            self._require()
            self.operator.authorize_request(request,conversation)
    def dispatch_output_tokens(self):return self.operator.dispatch_output_tokens()
    def smoke_ready(self):return self.operator.smoke_ready()
    def member_readiness(self):return self.operator.member_readiness()
    def reserve(self,run_id,attempt_id,input_bytes):
        with self.store.transaction():
            grant=self._require();self._grant_id=grant['grant_id']
            if not self.operator.smoke_ready() and not self.operator.member_readiness():raise BudgetError('owner_smoke_required')
            self.operator.member_grant_id=self._grant_id;self.operator.memory_scope=self.memory
            self.operator.member_entitlement_kind=grant['access_kind']
            return self.operator.reserve(run_id,attempt_id,input_bytes)
    def finish(self,*args,**kwargs):
        # Terminal accounting must be recorded even if access was revoked while
        # transport ran. Only verified settlement below can release reservation.
        return self.operator.finish(*args,**kwargs)
    def reconcile_completed(self,*args,**kwargs):
        with self.store.transaction():
            self._require()
            return self.operator.reconcile_completed(*args,**kwargs)
    def snapshot(self):return self.operator.snapshot()
    def close(self):pass
