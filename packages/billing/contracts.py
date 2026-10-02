"""Provider-neutral CNY contracts. Webhook bodies are hints, never payment proof."""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import re
from urllib.parse import urlsplit

MIN_MODEL_RESERVATION_CNY=Decimal('12.295272')
MAX_SHARED_CNY=Decimal('500')
IDENTIFIER=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$')

class BillingError(ValueError):pass
class PaymentState(str,Enum):
    PENDING='PENDING'
    CAPTURED='CAPTURED'
    REFUNDED='REFUNDED'
    PARTIAL_REFUND='PARTIAL_REFUND'
    DISPUTED='DISPUTED'
    FAILED='FAILED'


def identifier(value):
    if not isinstance(value,str) or not IDENTIFIER.fullmatch(value):raise BillingError('invalid_identifier')
    return value


def minor_units(value):
    if type(value) is not int or not 1<=value<=100_000_000:raise BillingError('integer_cny_minor_units_required')
    return value


@dataclass(frozen=True)
class PlanTerms:
    plan_id:str
    version:int
    title:str
    amount_minor:int
    currency:str
    duration_days:int
    max_requests:int
    max_cost_cny:Decimal
    temporary:bool
    persistent:bool
    terms_digest:str
    shared_capacity_limited:bool=True
    renewal_mode:str='USER_INITIATED_FIXED_DURATION'

    def validate(self):
        identifier(self.plan_id);minor_units(self.amount_minor)
        if type(self.version) is not int or self.version<1:raise BillingError('invalid_plan_version')
        if not isinstance(self.title,str) or not 1<=len(self.title)<=80:raise BillingError('invalid_plan_title')
        if self.currency!='CNY':raise BillingError('unapproved_currency')
        if type(self.duration_days) is not int or not 1<=self.duration_days<=366:raise BillingError('finite_duration_required')
        if type(self.max_requests) is not int or not 1<=self.max_requests<=1_000_000:raise BillingError('finite_request_cap_required')
        if not isinstance(self.max_cost_cny,Decimal) or not self.max_cost_cny.is_finite() or not MIN_MODEL_RESERVATION_CNY<=self.max_cost_cny<=MAX_SHARED_CNY:raise BillingError('usable_bounded_model_subcap_required')
        if type(self.temporary) is not bool or type(self.persistent) is not bool or not (self.temporary or self.persistent):raise BillingError('explicit_chat_capabilities_required')
        if not isinstance(self.terms_digest,str) or not re.fullmatch('[0-9a-f]{64}',self.terms_digest):raise BillingError('immutable_terms_required')
        if self.shared_capacity_limited is not True or self.renewal_mode!='USER_INITIATED_FIXED_DURATION':raise BillingError('no_unlimited_or_automatic_debit_authority')
        return self

    def public(self):
        self.validate()
        return {'plan_id':self.plan_id,'version':self.version,'title':self.title,'amount_minor':self.amount_minor,'currency':self.currency,'duration_days':self.duration_days,'max_requests':self.max_requests,'max_cost_cny':str(self.max_cost_cny),'temporary':self.temporary,'persistent':self.persistent,'terms_digest':self.terms_digest,'shared_capacity_limited':True,'renewal_mode':self.renewal_mode,'usage_period':'ASIA_SHANGHAI_CALENDAR_MONTH'}


@dataclass(frozen=True)
class Checkout:
    provider:str
    merchant:str
    order_id:str
    external_order_id:str
    url:str

    def validate(self,order,allowed_origins):
        for value in (self.provider,self.merchant,self.order_id,self.external_order_id):identifier(value)
        parsed=urlsplit(self.url)
        origin=parsed.scheme+'://'+parsed.netloc
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.fragment or origin not in allowed_origins:raise BillingError('unapproved_checkout_destination')
        if (self.provider,self.merchant,self.order_id)!=(order['provider'],order['merchant'],order['order_id']):raise BillingError('checkout_binding_mismatch')
        return self


@dataclass(frozen=True)
class VerifiedPayment:
    provider:str
    merchant:str
    order_id:str
    external_order_id:str
    payment_id:str|None
    product_id:str
    amount_minor:int
    currency:str
    state:PaymentState
    paid_at:int|None
    refunded_minor:int
    evidence_digest:str
    verification_source:str='AUTHENTICATED_SERVER_ORDER_QUERY'

    def validate(self,order):
        # Only a selected server adapter constructs this after its authenticated
        # query. No public endpoint parses a callback JSON into this class.
        for value in (self.provider,self.merchant,self.order_id,self.external_order_id,self.product_id):identifier(value)
        minor_units(self.amount_minor)
        if self.verification_source!='AUTHENTICATED_SERVER_ORDER_QUERY':raise BillingError('authoritative_order_query_required')
        if (self.provider,self.merchant,self.order_id,self.product_id,self.amount_minor,self.currency)!=(order['provider'],order['merchant'],order['order_id'],order['product_id'],order['amount_minor'],order['currency']):raise BillingError('payment_binding_mismatch')
        if order.get('external_order_id') not in (None,self.external_order_id):raise BillingError('payment_binding_mismatch')
        if not order.get('external_order_id') and order.get('state') not in {'CREATING','UNCERTAIN'}:raise BillingError('checkout_not_created')
        if not isinstance(self.state,PaymentState):raise BillingError('verified_payment_state_required')
        if type(self.refunded_minor) is not int or not 0<=self.refunded_minor<=self.amount_minor:raise BillingError('invalid_refund_amount')
        if self.state==PaymentState.REFUNDED and self.refunded_minor!=self.amount_minor:raise BillingError('full_refund_proof_required')
        if self.state in {PaymentState.CAPTURED,PaymentState.PENDING,PaymentState.FAILED} and self.refunded_minor:raise BillingError('inconsistent_capture')
        if self.state==PaymentState.PARTIAL_REFUND and not 0<self.refunded_minor<self.amount_minor:raise BillingError('partial_refund_proof_required')
        if self.state in {PaymentState.CAPTURED,PaymentState.REFUNDED,PaymentState.PARTIAL_REFUND,PaymentState.DISPUTED}:
            identifier(self.payment_id)
            if type(self.paid_at) is not int or self.paid_at<=0:raise BillingError('verified_payment_time_required')
            if not order['created_at']<=self.paid_at<=order['expires_at']:raise BillingError('payment_outside_quote_window')
        if not isinstance(self.evidence_digest,str) or not re.fullmatch('[0-9a-f]{64}',self.evidence_digest):raise BillingError('safe_payment_evidence_digest_required')
        return self
