# Shared Beijing Qwen monthly budget

## Current user decision

On2026-10-02 the user clarified that HCLA is a reusable multiuser product and
selected one SHARED CNY500 per Asia/Shanghai calendar month for all eligible users
and integration tests. The user then chose open registration with model access
restricted to active, server-verified PAID membership; registration grants no model
access or free trial. This supersedes the uninstalled owner-only preparation.
No500-per-user pool, automatic recharge, provider fallback or automatic retry is
permitted. HCL core and historical USD/trial accounting remain unchanged.

Version3 policy uses monthly scope AUTHENTICATED_SHARED, timezone Asia/Shanghai,
limit_cny500, model qwen3.8-max, Beijing, uncached CNY12/36 per million,8192 combined
thinking+answer tokens plus documented10 accounting margin. The same conservative
CNY12.295272 reservation covers each call; actual expected short-request spend is
much smaller and is not claimed as the provider invoice.

Version2 owner-only parsing remains for historical compatibility, but V2 and V3
cannot create separate funded pools or reset a month. The authorization singleton
is immutable; do not change an installed V2 template to V3. Production preflight
must confirm no Qwen authorization/attempts were installed before initial V3 setup.

## Isolation and global authority

One database-derived YYYY-MM period and one monthly attempt table cover all actors.
Each attempt binds immutable actor_tenant, entitlement_grant_id, memory_scope,
period, execution owner, reservation and original rates. Members can read/mutate
only their own attempts. Owner has audit SELECT, not cross-member UPDATE authority.
No conversation content, raw reasoning, credential or provider key is in this ledger.

The mutation guard remains SECURITY INVOKER and holds the existing global advisory
lock. A narrow private SECURITY DEFINER read-only helper returns only current-month
global totals, the caller's totals and verified owner-smoke readiness. It accepts no
period/actor arguments and exposes no other actor identifiers or attempt rows.
VOLATILE guarantees fresh visibility after lock waits; SET row_security=off makes an
insufficiently privileged function owner fail rather than silently sum partial rows.
PUBLIC, anon and authenticated cannot execute it. Activation verifies its owner has
BYPASSRLS/superuser and its fixed search_path/row_security settings.

All actors, including failed/revoked/hidden actors, count toward the same global
CNY500 cap and global one-active slot. Per-member CNY entitlements are subordinate
permissions/monthly sublimits only: they cannot replenish shared capacity.
V3 records CALENDAR_MONTH_WITHIN_SHARED_CEILING explicitly; the same member grant
can continue next month while valid, without a new provider setup or budget pool. No USD entitlement
is reinterpreted as CNY. Both application and DB admission recheck member session,
expiry, generation, grant and memory rights under the lock. Settlement rechecks the
same immutable grant/session while retaining full reservation on uncertainty.

The initial exact fresh temporary Mira HCL smoke is owner-only. Until it is durably
published and settled, every member dispatch is closed. Successful smoke enables
ordinary owner and eligible authenticated member requests under the SAME500 pool.
This never enables anonymous or unpaid spending. Public signup must be configured
explicitly with verified email and non-anonymous identity; it creates no entitlement.

## Existing account integration

Use the already implemented verified Supabase account path and tenant RLS. Member
sessions/entitlements require the existing account+recovery schema prerequisites
and explicitly configured HCLA_MEMBER_AUTH, HCLA_SUPABASE_AUTH_URL and
HCLA_SUPABASE_PUBLISHABLE_KEY. They are distinct from the already saved Qwen key.
Paid membership additionally requires paid_membership=true plus a trusted
ADMIN_VERIFIED or TRUSTED_PAYMENT_EVENT source, verification time and evidence
digest. Defaults are unpaid/NONE; client/JWT metadata cannot set these fields.
Each admitted member attempt binds the original evidence digest and verifier
source immutably. Expiry/revocation/payment-evidence changes are rechecked before
settlement. No agent-created identity, new credential, copied secret or automatic
account grant is part of this code. Member CNY rights are server-owned qwen_member_entitlements.
The generic route needs no new provider deployment or financial grant per user.

Authenticated GET /v1/budget (member /v1/member/budget) returns shared capacity and
only that actor's aggregate use. The legacy owner-only /v1/development/budget remains
supported. UI says all eligible users/tests share the total; it does not advertise
500 separately to each user. Persistent/TOPIC and temporary paths use one wrapper;
temporary text remains in tab/request memory only.

## Batched activation

Complete final review and exact-head PostgreSQL/browser gates before publication
and one coherent production activation. Install only reviewed prerequisites and
V3 policy on the verified existing HCLA project under exact live authorization.
Never retry a denied migration through a different SQL route. Set nonsecret selector
HCLA_PROVIDER=qwen and matching HCLA_QWEN_MODEL_GRANT, reusing the user's stored
Production HCLA_QWEN_API_KEY without reading or re-entering it. Where safe, prepare
approved schema/config before the final merge so one deployment captures the whole
candidate; current immutable deployment env stays unchanged until that deployment.

Installing the monthly authorization closes NEW old HCLA USD/trial/one-off-provider
admissions, including old binaries, while keeping history and old settlement intact.
Do not revoke the shared DeepSeek key or alter the HCL research project.

Only after deployed-code/schema/currency/period/session preflight should one planned
original synthetic request run. Inspect its exact finish/usage/outcome before any
separately planned diagnosis. All real attempts use the same shared monthly ledger.

## Tests

Synthetic-only tests cover one owner plus two members sharing one cap; cross-actor
active-slot/near-cap races; hidden-row accounting; actor read/update isolation;
immutable attribution; revoked/expired/wrong-memory rights; owner-smoke gating;
delayed member publication; real temporary and TOPIC routes; preserved unknown
reservations; calendar rollover; and closed anonymous routes. No fake/provider-free
result is evidence of live model efficacy or private-data activation.

## Payment and onboarding limits

Open registration is the chosen onboarding policy, but live Auth signup settings,
email confirmation, allowed origins and mail delivery must be verified/configured
under explicit security authorization. At read-only preflight the project had zero
Auth users and the dashboard required login. Do not disable email confirmation to
bypass delivery or claim live registration has passed without real end-to-end proof.

Membership checkout, prices, payment provider and payment webhooks are deliberately
NOT configured. A future payment callback must verify its provider signature,
original event identity/idempotency and payment state on a trusted server before
creating/updating a paid grant. No public grant endpoint exists. An authorized
operator may record externally verified paid membership; merely creating an account
or toggling generic enabled cannot grant model use. Actual payment setup requires
the user's later provider/pricing decision, not an invented paid service.
