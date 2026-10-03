"""Separate ordinary order access from the narrow financial worker connection.

No environment lookup, credentials, connection creation or adapter activation is
performed here. Construction needs explicit, already configured dependencies.
"""
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
import re
import uuid

from packages.billing.contracts import BillingError, PlanTerms


@dataclass(frozen=True)
class BillingActor:
    tenant: str
    session_hash: str


class BillingWorker:
    """A dedicated NOINHERIT financial login may assume the dormant worker role."""
    def __init__(self, connection):
        self.connection = connection
        row = connection.execute("SELECT rolsuper,rolbypassrls,pg_has_role(current_user,'hcla_billing_worker','member') AS worker,pg_has_role(current_user,'hcla_app','member') AS app FROM pg_roles WHERE rolname=current_user").fetchone()
        if not row or row['rolsuper'] or row['rolbypassrls'] or not row['worker'] or row['app']:
            raise BillingError('isolated_billing_worker_required')

    def call(self, function, values):
        counts = {'billing_claim_checkout':3, 'billing_complete_checkout':3,
                  'billing_mark_unknown':2, 'billing_apply_verified':2,
                  'billing_claim_query':2, 'billing_finish_query':2}
        if function not in counts or len(values) != counts[function]:
            raise BillingError('unknown_billing_operation')
        with self.connection.transaction():
            self.connection.execute("SET LOCAL lock_timeout='5s'")
            self.connection.execute("SET LOCAL statement_timeout='10s'")
            self.connection.execute('SET LOCAL ROLE hcla_billing_worker')
            placeholders = ','.join(['%s'] * counts[function])
            return self.connection.execute('SELECT hcla.'+function+'('+placeholders+') AS result', values).fetchone()['result']


class BillingRepository:
    def __init__(self, store, worker):
        self.store = store
        self.worker = worker

    def _member(self, actor):
        if not isinstance(actor, BillingActor) or not re.fullmatch(r'member-[0-9a-f]{64}', actor.tenant):
            raise BillingError('verified_member_required')
        if (actor.tenant, actor.session_hash) != (self.store.tenant, self.store.member_session_key):
            raise BillingError('billing_account_changed')
        row = self.store.db.execute("SELECT 1 FROM member_sessions s LEFT JOIN member_auth_generations g ON g.tenant=s.tenant WHERE s.tenant=? AND s.session_key=? AND s.expires_at>clock_timestamp() AND s.absolute_expires_at>clock_timestamp() AND (s.refresh_state='idle' OR s.refresh_started_at>clock_timestamp()-interval '20 seconds') AND s.auth_generation=COALESCE(g.generation,0) AND NOT COALESCE(g.reset_pending,false)", (actor.tenant, actor.session_hash)).fetchone()
        if not row:
            raise BillingError('verified_member_required')

    @staticmethod
    def _order(row):
        result = dict(row)
        for key in ('created_at', 'expires_at','access_starts_at','access_expires_at'):
            if hasattr(result.get(key), 'timestamp'):
                result[key] = int(result[key].timestamp())
        return result

    def catalog(self, actor):
        with self.store.transaction():
            self._member(actor)
            config = self.store.db.execute('SELECT enabled FROM billing_configuration WHERE singleton=1').fetchone()
            capacity = self.store.db.execute('SELECT billing_capacity() AS result').fetchone()['result']
            if not config or not config['enabled'] or capacity.get('available') is not True:
                return []
            rows = self.store.db.execute('SELECT * FROM billing_plan_versions WHERE enabled AND approved_at<=clock_timestamp() AND max_cost_cny>=? ORDER BY plan_id,version', (Decimal(capacity['reservation_cny']),)).fetchall()
            return [PlanTerms(r['plan_id'],r['version'],r['title'],r['amount_minor'],r['currency'],r['duration_days'],r['max_requests'],r['max_cost_cny'],r['temporary_enabled'],r['persistent_enabled'],r['terms_digest']).public() for r in rows]

    def create_order(self, actor, plan_id, version, key, digest, provider, merchant):
        if type(version) is not int or version < 1 or not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise BillingError('approved_current_plan_terms_required')
        with self.store.transaction():
            self._member(actor)
            old = self.store.db.execute('SELECT * FROM billing_orders WHERE tenant=? AND idempotency_key=?', (actor.tenant,key)).fetchone()
            if old:
                if (old['plan_id'],old['plan_version'],old['accepted_terms_digest'],old['provider'],old['merchant']) != (plan_id,version,digest,provider,merchant):
                    raise BillingError('idempotency_key_conflict')
                return self._order(old)
            row = self.store.db.execute('INSERT INTO billing_orders(order_id,tenant,plan_id,plan_version,idempotency_key,accepted_terms_digest) VALUES(?,?,?,?,?,?) RETURNING *', (str(uuid.uuid4()),actor.tenant,plan_id,version,key,digest)).fetchone()
            if (row['provider'],row['merchant']) != (provider,merchant):
                raise BillingError('billing_adapter_configuration_mismatch')
            return self._order(row)

    def order(self, actor, order_id):
        with self.store.transaction():
            self._member(actor)
            row = self.store.db.execute('SELECT o.*,e.starts_at AS access_starts_at,e.expires_at AS access_expires_at,e.enabled AS access_enabled FROM billing_orders o LEFT JOIN qwen_member_entitlements e ON e.tenant=o.tenant AND e.grant_id=o.grant_id WHERE o.order_id=? AND o.tenant=?', (order_id,actor.tenant)).fetchone()
            if not row:
                raise BillingError('order_not_found')
            return self._order(row)

    def history(self, actor):
        with self.store.transaction():
            self._member(actor)
            return [self._order(r) for r in self.store.db.execute('SELECT o.*,e.starts_at AS access_starts_at,e.expires_at AS access_expires_at,e.enabled AS access_enabled FROM billing_orders o LEFT JOIN qwen_member_entitlements e ON e.tenant=o.tenant AND e.grant_id=o.grant_id WHERE o.tenant=? ORDER BY o.created_at DESC,o.order_id LIMIT 50', (actor.tenant,)).fetchall()]

    def claim_checkout(self, actor, order_id):
        self.order(actor,order_id)
        result = self.worker.call('billing_claim_checkout', (order_id,actor.tenant,actor.session_hash))
        # JSON timestamps returned by Postgres preserve the quote window.
        from datetime import datetime
        for key in ('created_at','expires_at'):
            result[key] = int(datetime.fromisoformat(result[key]).timestamp())
        return result

    def complete_checkout(self, order_id, checkout):
        self.worker.call('billing_complete_checkout',(order_id,checkout.external_order_id,checkout.url))

    def checkout_unknown(self, order_id):
        self.worker.call('billing_mark_unknown',(order_id,'CHECKOUT'))

    def verification_unconfirmed(self, order_id):
        self.worker.call('billing_mark_unknown',(order_id,'VERIFICATION'))

    def by_external_reference(self, provider, merchant, reference):
        with self.worker.connection.transaction():
            self.worker.connection.execute('SET LOCAL ROLE hcla_billing_worker')
            row = self.worker.connection.execute('SELECT * FROM hcla.billing_orders WHERE provider=%s AND merchant=%s AND external_order_id=%s', (provider,merchant,reference)).fetchone()
            return self._order(row) if row else None

    def claim_verification(self, order_id):
        owner=str(uuid.uuid4())
        return owner if self.worker.call('billing_claim_query',(order_id,owner)) else None

    def finish_verification(self, order_id, owner):
        self.worker.call('billing_finish_query',(order_id,owner))

    def apply_verified(self, proof):
        return self.worker.call('billing_apply_verified',(proof.order_id,json.dumps(asdict(proof))))
