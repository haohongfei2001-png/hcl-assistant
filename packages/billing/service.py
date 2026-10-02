"""Payment requests and callbacks remain disabled without an approved adapter.

A dedicated worker performs authoritative order queries outside DB locks. Its
repository atomically applies bound verified receipts/grants; ordinary hcla_app
cannot perform that operation. No live provider is registered in this slice.
"""
from packages.billing.contracts import BillingError,Checkout,VerifiedPayment,identifier

LIVE_PROVIDERS=frozenset()  # Provider selection, eligibility and activation pending.


class BillingService:
    def __init__(self,repository,provider=None,*,source_fixture=False):
        self.repository=repository;self.provider=provider
        self.available=bool(provider and (source_fixture or provider.name in LIVE_PROVIDERS))

    def _enabled(self):
        if not self.available:raise BillingError('membership_purchase_not_enabled')

    def catalog(self,actor):
        if not self.available:return {'available':False,'plans':[],'reason':'会员购买尚未开放；注册不会自动开通会员'}
        offers=self.repository.catalog(actor)
        return {'available':True,'plans':offers,'renewal_mode':'USER_INITIATED_FIXED_DURATION','capacity_notice':'模型额度为平台共享每月500元，到限暂停；不承诺无限使用','recurring_charge':False}

    def create_order(self,actor,plan_id,version,idempotency_key,terms_digest):
        self._enabled();identifier(plan_id);identifier(idempotency_key)
        return self.repository.create_order(actor,plan_id,version,idempotency_key,terms_digest,self.provider.name,self.provider.merchant)

    def checkout(self,actor,order_id):
        self._enabled();identifier(order_id)
        # A durable claim permits one remote creation. Unknown/crashed creation
        # remains unresolved; no second payment order is blindly created.
        order=self.repository.claim_checkout(actor,order_id)
        if order.get('checkout_url'):return {'checkout_url':order['checkout_url']}
        try:
            value=self.provider.create_checkout(order)
            if not isinstance(value,Checkout):raise BillingError('invalid_checkout_result')
            value.validate(order,self.provider.checkout_origins)
        except Exception:
            self.repository.checkout_unknown(order_id)
            raise BillingError('checkout_creation_unconfirmed_no_automatic_retry') from None
        self.repository.complete_checkout(order_id,value)
        return {'checkout_url':value.url}

    def notification(self,hint):
        self._enabled()
        # The adapter extracts only a bounded order reference; amount/status in
        # an unsigned-looking callback never becomes financial authority.
        reference=self.provider.notification_reference(hint)
        if reference is None:return {'accepted':True}
        identifier(reference)
        order=self.repository.by_external_reference(self.provider.name,self.provider.merchant,reference)
        if order is None:return {'accepted':True}
        return self._reconcile(order)

    def reconcile(self,actor,order_id):
        self._enabled();identifier(order_id)
        return self._reconcile(self.repository.order(actor,order_id))

    def _reconcile(self,order):
        if order.get('state')=='PENDING':raise BillingError('checkout_not_created')
        try:
            # Query stored internal merchant order ID even if a create response
            # was lost. The proof may bind the missing external reference once.
            # Never create a second remote order or query a callback URL.
            result=self.provider.query_order(order)
            if not isinstance(result,VerifiedPayment):raise BillingError('authoritative_order_query_required')
            result.validate(order)
        except Exception:
            self.repository.verification_unconfirmed(order['order_id'])
            raise BillingError('payment_not_verified_no_membership_change') from None
        # This operation revalidates all immutable bindings under its DB lock.
        return self.repository.apply_verified(result)
