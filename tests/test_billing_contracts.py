"""Offline financial contract tests; no merchant adapter, network or money."""
from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock
import unittest

from packages.billing.contracts import BillingError, Checkout, PaymentState, PlanTerms, VerifiedPayment
from packages.billing.service import BillingService


def plan():
    return PlanTerms('fixture-plan',1,'Offline fixture',990,'CNY',30,20,Decimal('25'),True,True,'a'*64)


def order():
    return dict(provider='fixture',merchant='offline-merchant',order_id='order-1',external_order_id='external-1',product_id='fixture-plan:1',amount_minor=990,currency='CNY',created_at=100,expires_at=1900,state='CHECKOUT_READY')


def payment():
    return VerifiedPayment('fixture','offline-merchant','order-1','external-1','payment-1','fixture-plan:1',990,'CNY',PaymentState.CAPTURED,110,0,'b'*64)


class BillingContractTests(unittest.TestCase):
    def test_no_live_provider_or_price_by_default(self):
        repository=Mock();provider=Mock(name='provider');provider.name='unselected'
        service=BillingService(repository,provider)
        self.assertFalse(service.catalog(None)['available'])
        with self.assertRaises(BillingError):service.create_order(None,'fixture',1,'once','a'*64)
        repository.create_order.assert_not_called();provider.create_checkout.assert_not_called()

    def test_plans_are_bounded_cny_and_truthful_about_monthly_shared_capacity(self):
        self.assertEqual(plan().public()['usage_period'],'ASIA_SHANGHAI_CALENDAR_MONTH')
        replace(plan(),amount_minor=100_000_000).validate()
        changes=({'amount_minor':100_000_001},{'amount_minor':True},{'amount_minor':9.9},{'currency':'USD'},{'duration_days':0},{'duration_days':367},{'max_requests':0},{'max_cost_cny':Decimal('12')},{'max_cost_cny':Decimal('501')},{'max_cost_cny':Decimal('NaN')},{'shared_capacity_limited':False},{'renewal_mode':'AUTO_DEBIT'},{'temporary':False,'persistent':False})
        for values in changes:
            with self.subTest(values=values),self.assertRaises(BillingError):replace(plan(),**values).validate()

    def test_checkout_exact_origin_and_order_binding(self):
        checkout=Checkout('fixture','offline-merchant','order-1','external-1','https://checkout.example.test/pay?id=1')
        self.assertEqual(checkout.validate(order(),{'https://checkout.example.test'}),checkout)
        for url in ('http://checkout.example.test/pay','https://checkout.example.test.evil.test/pay','https://user@checkout.example.test/pay','https://checkout.example.test/pay#token','//checkout.example.test/pay'):
            with self.subTest(url=url),self.assertRaises(BillingError):replace(checkout,url=url).validate(order(),{'https://checkout.example.test'})
        with self.assertRaises(BillingError):replace(checkout,order_id='other').validate(order(),{'https://checkout.example.test'})

    def test_verified_payment_binds_all_server_owned_terms(self):
        self.assertEqual(payment().validate(order()),payment())
        for field,value in [('provider','other'),('merchant','other'),('order_id','other'),('external_order_id','other'),('product_id','other'),('amount_minor',991),('currency','USD'),('paid_at',99),('paid_at',1901),('verification_source','CALLBACK'),('evidence_digest',None),('payment_id',None)]:
            with self.subTest(field=field),self.assertRaises(BillingError):replace(payment(),**{field:value}).validate(order())

    def test_unknown_checkout_can_only_bind_authoritative_query_and_never_uncreated_order(self):
        lost=order()|{'external_order_id':None,'state':'UNCERTAIN'}
        payment().validate(lost)
        with self.assertRaises(BillingError):payment().validate(lost|{'state':'PENDING'})
        replace(payment(),state=PaymentState.PENDING,payment_id=None,paid_at=None).validate(order())

    def test_refund_financial_states_require_consistent_amounts(self):
        replace(payment(),state=PaymentState.REFUNDED,refunded_minor=990).validate(order())
        replace(payment(),state=PaymentState.PARTIAL_REFUND,refunded_minor=10).validate(order())
        for state,amount in [(PaymentState.CAPTURED,1),(PaymentState.REFUNDED,989),(PaymentState.PARTIAL_REFUND,0),(PaymentState.PARTIAL_REFUND,990),(PaymentState.PENDING,1),(PaymentState.DISPUTED,-1)]:
            with self.subTest(state=state,amount=amount),self.assertRaises(BillingError):replace(payment(),state=state,refunded_minor=amount).validate(order())

    def test_checkout_transport_uncertainty_is_not_retried(self):
        repository=Mock();repository.claim_checkout.side_effect=[order(),BillingError('already claimed')]
        provider=Mock();provider.name='fixture';provider.merchant='offline-merchant';provider.create_checkout.side_effect=TimeoutError()
        service=BillingService(repository,provider,source_fixture=True)
        for _ in range(2):
            with self.assertRaises(BillingError):service.checkout(None,'order-1')
        self.assertEqual(provider.create_checkout.call_count,1);repository.checkout_unknown.assert_called_once_with('order-1')

    def test_forged_callback_state_never_grants_access(self):
        repository=Mock();repository.by_external_reference.return_value=order()
        provider=Mock();provider.name='fixture';provider.merchant='offline-merchant';provider.notification_reference.return_value='external-1';provider.query_order.side_effect=TimeoutError()
        service=BillingService(repository,provider,source_fixture=True)
        with self.assertRaises(BillingError):service.notification({'state':'CAPTURED','amount_minor':990})
        repository.apply_verified.assert_not_called();repository.verification_unconfirmed.assert_called_once()
        provider.query_order.side_effect=None;provider.query_order.return_value={'state':'CAPTURED'}
        with self.assertRaises(BillingError):service.notification({'state':'CAPTURED'})
        repository.apply_verified.assert_not_called()

    def test_unknown_order_query_uses_only_stored_reference(self):
        repository=Mock();repository.order.return_value=order()|{'external_order_id':None,'state':'UNCERTAIN'}
        provider=Mock();provider.name='fixture';provider.query_order.return_value=payment()
        service=BillingService(repository,provider,source_fixture=True)
        service.reconcile(None,'order-1')
        provider.query_order.assert_called_once_with(repository.order.return_value)
        repository.apply_verified.assert_called_once_with(payment());provider.create_checkout.assert_not_called()
