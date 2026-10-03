# M3-01 Consumer membership lifecycle (source preparation)

The user adopted the complete consumer product on 2026-10-02: ordinary public
registration and verified email, membership purchase and order/payment
confirmation, user-initiated renewal and expiry, chat/history, isolation and the
existing shared budget. The developer is an individual and the primary market is
domestic. This supersedes earlier documents' billing deferral only for reusable
engineering. No live price, plan, merchant provider, contract, charge, recurring
commitment, credential, grant or database permission is adopted by this document.

## Current deliverable and outstanding work

This slice prepares the provider-neutral CNY financial boundary, authenticated
purchase/order API, ordinary membership/order UI and disposable contract/database/
browser tests. No live adapter is registered, no configuration or offer rows are
seeded, and no account receives membership. The selected merchant integration
and eligible live activation remain M3-01 work; source fixtures are not a working
commercial checkout and cannot close M3-01.

The single canonical queue remains `control/plan.json.product_development`.
Historical packages/evidence and the L3/private-data/Controller/runtime gates are
unchanged. Source tests use injected offline payment fixtures and no money/model
calls. Price values in tests are synthetic examples, not proposed prices.

## Financial contract

- CNY minor units are integers. Offers have immutable versioned terms, finite
  duration and bounded request/cost subcaps. The current shared-budget policy
  resets those paid subcaps per Asia/Shanghai calendar month. Each subcap must
  accommodate the current conservative model reservation (currently CNY12.295272)
  and may never exceed the all-user CNY500 monthly ceiling.
- An offer explicitly discloses shared-capacity suspension and cannot promise
  unlimited use. New order/checkout admission checks model readiness and at least
  one conservative reservation's remaining shared capacity. This is a point-in-
  time sales gate, not reserved future compute or a guarantee of availability.
  An already-issued merchant checkout may settle after capacity changes; genuine
  payment is still recorded and fulfilled without lifting the model budget.
- Account sessions and accepted terms bind each immutable order. Same-account
  idempotency keys return the same order; a changed payload conflicts. At most
  five unexpired unfinished quotes per account bound unpaid-order accumulation;
  rereading/retrying the same key remains available. The browser
  cannot set price, currency, provider, product, state or entitlement.
- Checkout creation is durably claimed once before transport. A lost response
  becomes uncertain; no blind second creation or automatic payment retry occurs.
  The chosen adapter must support an authenticated query by the stored internal
  merchant order ID so an uncertain creation can be reconciled.
- Redirects, screenshots, callback bodies and claimed payment amounts are never
  financial authority. Notification data supplies only a bounded reference. The
  server queries the selected provider and verifies merchant, internal order,
  external order, product/version, integer amount, currency, immutable quote
  window and payment ID before a dedicated worker applies the receipt.
- Renewal is a new user-initiated payment. No automatic debit is implemented or
  promised. Atomic fulfilment creates a new immutable entitlement period starting
  after the latest enabled paid period; simultaneous renewals cannot overlap.
  Replaying a payment never extends duration or creates another entitlement.
- Full refunds/disputes revoke only the matching order's entitlement. A partial
  refund suspends that entitlement for review, without choosing proration or
  initiating a refund payment. Stale captures/refund snapshots never restore it.
  Other purchased periods retain their original dates; no silent reshuffling of
  paid terms occurs. A later decision is required for customer-support remediation.
- TEST_ONLY remains visibly non-paid. A genuine fulfilled purchase disables the
  account's exceptional testing grant, avoiding ambiguous simultaneous rights.

## Notification/query admission

Unsigned-looking notifications are wake-up hints only. The public notification
body is capped at 8 KiB. Before any selected adapter query, a private database
claim coalesces the same order for 10 seconds, permits at most four active query
leases globally, and admits at most 60 queries in a rolling minute. Completed
queries still count against the rate limit. Independent instances share these
limits and admission is serialized; rejected wakes do not contact the provider
or alter membership. Deferred public notifications return retryable HTTP429 with
Retry-After 60 rather than acknowledging unperformed verification; the selected
adapter must verify its merchant retry contract. A lease expires after 30 seconds
for crash recovery. A finish/connection failure can occur after fulfilment has
already committed. The UI directs the account to reread/reconcile the same order,
never to assume payment failed, create another checkout or pay again.

A selected live adapter must independently enforce an HTTP wall deadline of at
most 10 seconds, response-size bounds and its documented authentication/signature
checks. This deadline must be shorter than the lease. There is no registered live
adapter here; live activation cannot rely on an unbounded transport. Query audit
metadata has no automatic destructive retention policy in this source slice.

## Ordinary account interaction

Ordinary accounts can open membership/orders directly from the composer or
Settings, including before purchase or after expiry. A versioned offer requires explicit review of its
price, duration, capped usage and shared-capacity disclosure. Creation sends only
plan/version, accepted terms digest and a stable in-flight idempotency key. The
user opens the approved HTTPS merchant checkout themselves, then explicitly asks
the server to reconcile it. No client success flag grants membership. A successful
reconciliation rereads account status; drafts/history stay in place. Uncertain
creation is query-only, with no automatic payment or retry. Auth restoration aborts and invalidates in-flight UI work, removes stale checkout
links/order projections, and blocks mutation. After verified-session recovery it
only rereads account-owned orders; no checkout/query mutation is replayed. A failed
order-history read also prevents new purchase until prior orders can be checked.

Order history exposes only the current account's public order/entitlement-period
projection, never merchant receipts, tenant/session IDs or verification digests.
Future renewal dates are shown without silently advancing them after a refund.
The optional still-active trial is a collapsed secondary entry below login. An
expired trial is absent from the entry; its server history and admission rules are
unchanged and it is never reactivated by the UI.

## Least-privilege boundary

The ordinary `hcla_app` role can read public offer metadata and its own orders,
and insert only the account/plan/idempotency/accepted-terms fields. It cannot
write paid membership or payment receipts. The additive migration defines a
separate dormant `hcla_billing_worker` NOLOGIN role, with read-only order evidence
and narrow checkout/receipt functions in the unexposed `hcla` schema. The worker
cannot arbitrarily update tables. These functions are not executable by PUBLIC,
`anon`, `authenticated` or `hcla_app`.

A future worker is a trusted financial authority because it can submit verified
provider-query receipts. Its dedicated login/credential and deployment boundary
must be reviewed and explicitly approved; the ordinary application login must
not gain that role. Source constructors require explicit dependencies and read
no credentials/environment or live provider registry. No live role is changed.

## Acceptance M13–M19

| ID | Required proof before closure |
| --- | --- |
| M13 | Default closed; no seeded plans, live provider, self-grant or fake payment |
| M14 | Verified-account orders, immutable offer/amount/currency binding, idempotency and cross-tenant isolation |
| M15 | Single checkout claim, bounded trusted destinations and lost-response query recovery |
| M16 | Authenticated server-query proof, replay safety, missing/forged/cross-order evidence refusal |
| M17 | Concurrent nonoverlapping renewal, expiry, refund/dispute ordering and no automatic debit/refund |
| M18 | Consumer purchase/order/renewal UI, interrupted flows and truthful exhausted-budget handling |
| M19 | Selected eligible adapter contract tests, hosted real Postgres/browser evidence, independent review and exact-main verification |

## Minimum future commercial activation bundle

1. Select an eligible provider for the actual AI product and individual domestic
   developer. Confirm its terms, approved product category, payment-query trust
   mechanism, CNY/WeChat/Alipay support, refunds, settlement and fees. Research does
   not itself select or sign up for a provider.
2. Adopt exact versioned offer/price/duration/subcaps and truthful shared-capacity,
   renewal, cancellation/refund and support disclosures. No values are chosen here.
3. Review/apply the additive schema and provision the isolated worker access only
   with action-time approval. Users enter/submit merchant credentials themselves
   through a supported secure route. Keep secrets out of repository/browser/logs.
4. Configure approved merchant, destinations and immutable approval/terms digests,
   then explicitly enable the selected server adapter and offers after sandbox
   verification. Activate actual charges only under the adopted purchase terms.
5. Complete existing ordinary Auth/email and Qwen readiness gates from
   [member readiness](MEMBER_READINESS_TRANSITION.md). No admin login is needed
   for ordinary use; normal signup never grants paid/testing rights.
