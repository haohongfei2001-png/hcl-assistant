# Ordinary-account readiness and explicit testing rights

## Scope and product destination

The full consumer product includes public registration/email verification,
ordinary-account chat/history/isolation, membership purchase and verified payment
fulfilment, renewal/expiry, and the shared model budget. A personal testing account
is an intermediate verification path, not product completion. Payment provider,
merchant eligibility, commercial price/packages and live checkout remain undecided.
The initial market is domestic/CNY; payment adapters must remain replaceable.

## Default-closed transition

The installed V3 AUTHENTICATED_SHARED CNY500/Shanghai-month policy, historical
periods and attempts are immutable and are not rewritten. An additive GLOBAL (not tenant-bound)
`qwen_member_readiness_authorizations` row can explicitly delegate exactly one
fresh temporary readiness attempt to an already verified and explicitly entitled
ordinary account. The row binds the SHA256 of the original policy, has finite
starts/expiry, an approval-evidence digest, and max_attempts=1. Migration alone
creates no authorization row. No anonymous or newly registered account qualifies.

The same original Mira source/query hashes, temporary memory, Controller, reviewed
HCL slice, Qwen endpoint, output cap, conservative reservation, atomic global active
slot and shared CNY500 monthly limit remain mandatory. An explicit readiness-intent flag cannot silently turn into a second ordinary paid call when another member finishes first. Readiness attribution is
immutable in its attempt. Failed/unknown attempts consume the one authorization
and retain conservative cost; neither login nor polling retries them. A successful,
published, settled readiness attempt allows subsequent requests only under their
own current membership or explicitly approved testing rights.

A separate `qwen_member_test_entitlements` table records TEST_ONLY rights. These
are not paid memberships and never populate paid evidence. A grant binds one
verified account, the immutable parent policy, finite starts/expiry, a grant-lifetime
request/cost ceiling, and separate readiness/chat/temporary/persistent capability
flags. This TEST_ONLY entitlement, rather than the global readiness row, is account-bound. Defaults are closed. Its lifetime subcap does not reset when the shared
Shanghai month changes. Existing paid members retain their monthly subordinate
caps. Overlapping active paid/testing grants fail closed rather than sum capacity.
Application roles can only read their own test grant, never create/update it.
Authorization terms are immutable; operators may disable them, not extend or reset
them. A genuinely new grant requires separate explicit authorization.

## UI and account behavior

The ordinary member screen displays TEST_ONLY as testing access, expressly not a
paid membership, including expiry and grant-lifetime limits. Paid membership and
provider availability are independent facts. A first-use button appears only for
server-approved readiness and requires the existing synthetic-input confirmation.
It sends the exact sample, not the user's draft, using a fresh temporary chat.
Ordinary Send remains disabled until readiness is durably verified. Once verified,
normal testing requires the separately approved chat capability; expired/revoked
rights never erase the account's readable history or turn into paid status.

## Source verification

New actual-Postgres coverage exercises default closure, no signup grant, ordinary
TEST_ONLY readiness then chat, readiness-only grants, exact input refusal, paid
readiness attribution, unknown no-retry reservation, lifetime caps across monthly
rollover, expiry/revocation/overlap, and cross-tenant/read-only privileges. Existing
owner, paid-member, calendar, cancellation and shared-cap suites remain mandatory.
New browser/Node fixtures exercise explicit readiness, draft preservation and
truthful non-paid display. All fixtures are synthetic; they are not live accounts,
real payments, model efficacy, or permission to activate anything.

## One-time live activation checklist (no values chosen or applied here)

1. Verify the existing HCLA project and existing mail configuration. Apply the
   reviewed account and recovery/session-generation prerequisites plus this new
   transition migration only after the exact live schema/security approval.
   The recovery UI itself can remain disabled; login/refresh use its generation
   schema. Preserve all existing data and FORCE-RLS/private roles.
2. Verify email/password signup, email confirmation, exact Site URL/allowed
   redirects and delivery. Reuse a configured mail service if available. The default
   Supabase mailer can reach only authorized project-team recipients and is not
   public signup delivery. Never disable verification to work around email.
3. Configure the existing project origin/publishable Auth key and member selector
   through an authorized setup route. Reuse the saved Qwen key without reading it;
   install the exact Qwen selector/grant, retiring incompatible legacy provider/
   trial selectors if present. Do not reset the owner's credentials to enable the
   ordinary-user route. Respect any denied environment-management route.
4. The user creates their ordinary account and password themselves, then verifies
   email. Resolve the server-verified account ID; signup alone grants no spending.
5. Request one bounded approval containing these exact records:
   - Readiness: authorization_id, parent_policy_sha256, enabled, starts_at,
     expires_at, max_attempts=1, approval_evidence_digest.
   - Optional personal testing: verified tenant, unique grant_id,
     parent_policy_sha256, access_kind=TEST_ONLY, verification=OWNER_APPROVED_TEST,
     enabled, starts_at, expires_at, readiness_enabled, chat_enabled,
     temporary_enabled, persistent_enabled, max_requests, max_cost_cny,
     budget_window=GRANT_LIFETIME_WITHIN_SHARED_MONTHLY_CEILING,
     approval_evidence_digest.
   No live identity/duration/subcap is selected here. A useful subcap must cover at
   least the current CNY12.295272 conservative per-request reservation, and both
   readiness and subsequent chat debit this same grant and platform CNY500 pool.
6. Deploy once with the approved consistent schema/config. User explicitly starts
   the exact readiness sample; verify its real result/usage before any later call.
   Normal public users still need genuine paid membership. Commercial checkout,
   provider credentials/contracts/prices and real payment fulfilment are separate
   activation decisions, not granted by these testing records.
