# HCLA owner monthly Qwen budget

## Authorization and supersession

On 2026-10-02 the owner requested complete HCLA integration without repeatedly
entering credentials, and approved CNY 500 per calendar month for all HCLA testing
and owner use. The calendar is Asia/Shanghai. HCL core remains on its existing
provider. Public member/guest activation, new paid services, automatic recharge,
budget increases and real-private-data activation are not part of this scope.

This monthly continuation supersedes the earlier separate CNY 13/one-call funding
proposal. The first synthetic smoke and ordinary owner requests debit the SAME
monthly CNY 500 ledger from the first live call. The old one-off Qwen ledger is
not deployed as an intermediate live grant and must not be reset or repurposed.
The key was entered once by the owner in the existing Vercel Production secret
interface. No agent reads or copies its value; no further entry is needed.

## Frozen configuration

Use the existing `HCLA_QWEN_API_KEY`, `HCLA_PROVIDER=qwen` and non-secret
`HCLA_QWEN_MODEL_GRANT` fields from QWEN_PROVIDER.md. The monthly grant has:

- provider qwen; model qwen3.8-max; region cn-beijing; currency CNY
- exact reviewed Beijing base_url
- an explicit immutable authorization identity such as hcla-qwen-cny-monthly-owner-v1
- max_cost_cny "500"; finite max_requests 1000000 per month
- input_cny_per_million "12"; output_cny_per_million "36", verified uncached
  pay-as-you-go floors; no currency conversion or cache discount
- max_completion_tokens 8192 for both initial smoke and ordinary owner use;
  reserve the documented additional 10-token deviation
- monthly exactly {"timezone":"Asia/Shanghai","scope":"OWNER_ONLY","limit_cny":"500"}
- the exact initial Mira source/query fingerprints in smoke, with
  scope OWNER_ONLY_SYNTHETIC_SMOKE

The offline print_qwen_budget_policy helper prints the canonical version 2
metadata. It does not install authorization or make a model call. The recurring
financial policy is immutable. Period identity is the database-derived Shanghai
YYYY-MM, independent of deployment, session, key rotation or a caller's budget ID.
Changing authorization metadata cannot create another CNY 500 pool for a month.

## Database enforcement

The additive monthly migration creates an operator-owned singleton authorization
(policy + enabled flag), immutable monthly periods and period-bound attempts.
The runtime can read the authorization and cannot change/delete it. The operator
can disable admission with enabled=false without changing the financial policy.
No authorization row is created by migration or app startup.

Once the separately approved standing authorization is installed, the runtime
can create only the CURRENT database-clock Shanghai period, using exactly the
installed policy and CNY 500 ceiling. This needs no new monthly secret or user
form. No future/backdated period, carryover, reset, currency switch, amount edit
or reassignment of a historical attempt is allowed. App-row mutations are
protected by database triggers and the existing global transaction advisory lock.

All live tests and owner requests are included. Active/unconfirmed transports
across legacy USD, trial, one-off Qwen and monthly Qwen prevent parallel dispatch.
Installing the monthly authorization closes NEW legacy/one-off HCLA admissions,
including from old binaries, while allowing previously dispatched requests to
settle. No shared DeepSeek key is revoked and HCL core is unaffected. Existing
one-off Qwen spending, if unexpectedly present, prevents monthly authorization
installation until separately reconciled; it is never silently erased or moved.

The server refuses new dispatch within 300 seconds of the next Shanghai month,
matching the existing 300-second maximum hosting duration. Lock waits recheck the
database clock. The provider wall/absolute/lease deadlines remain 180/240/270s.
An attempt always belongs to its admission month, including later reconciliation.
Application accounting is not a promise about the provider's invoice-posting
month or exact invoice amount.

## Admission, verified settlement and smoke

Before dispatch, reserve the full documented 1M input context plus 8192+10 output
at the immutable reviewed prices, CNY 12.295272 per attempt. The complete prompt
and HTTP body remain limited to 8192 bytes with no silent Qwen history pruning.
This whole-context reservation is a worst case, not an expected short-prompt fee.

`finish()` retains that conservative reservation. Only after the Controller has
published a COMPLETED answer with exact model identity, final completion, confirmed
transport termination, consistent positive bounded usage, current permissions and
no cancellation can `reconcile_completed()` settle to usage priced at the fixed
uncached rates. Database guards recheck immutable identity, execution ownership,
usage bounds and permitted transitions. This releases only that attempt's excess
reservation, never more authorization than the same 500 monthly ceiling. Failed,
partial, cancelled, unknown and unverified attempts retain their full reservation.
The provider invoice remains unknown.

Until a durably settled original synthetic smoke exists, only the exact fresh
temporary Mira belief_interpretation source/query is admitted. The first planned
live verification is one explicit call; the transport never automatically retries.
Any later explicitly initiated diagnostic request remains inside the same monthly
ceiling. Once verified smoke settlement is durable, ordinary authenticated owner
use is enabled without new credentials or a second financial grant. Member/guest
admission and model availability stay closed even if old entitlement rows exist.

Owner-only GET /v1/development/budget provides the current period, charged/reserved
accounting and remaining CNY capacity without any provider call or key disclosure.
Settings can refresh that read-only counter. Authentication uses the existing
secure owner login and its normal session; no new auth bypass is introduced.

## Activation sequence after final review/CI

Use one coherent final deployment, not a live one-off smoke intermediate:

1. Verify both frozen code/SQL reviews and exact-head PostgreSQL/browser CI.
2. Check existing HCLA budget/attempt metadata, without reading body data/secrets.
   The original owner-only cloud + trial schema is supported directly: no member
   account/recovery migration or broader tenant RLS activation is required.
   Monthly lease checks distinguish an absent legacy tenant column from an
   explicit NULL or non-owner value, which remains rejected.
3. With the required action-time approval for live database/security changes,
   apply the two additive Qwen migrations and install only the reviewed monthly
   authorization row. Do not install a one-off qwen_budget_policy grant.
4. Set the matching non-secret monthly JSON and selector in the already verified
   HCLA Vercel project. Leave the stored key untouched; do not alter TodayAction
   settings or the HCL core provider. Remove conflicting legacy HCLA selector
   variables only within the approved cutover scope.
5. Redeploy the reviewed commit, verify non-secret status and database guards,
   then authenticate to the existing HCLA owner UI using secure entry if needed.
6. Run one fresh original synthetic pinned-HCL smoke. Record actual finish, usage,
   currency, monthly period and outcome. A failure is not success and does not
   trigger automatic resubmission. Continue diagnosis only within the approved
   monthly scope; do not increase or reset the ceiling.
7. Verify that successful smoke unlocks ordinary owner requests while the same
   monthly counter remains, and that public member/guest routes remain closed.

## Tests and limits

Monthly tests cover immutable policy/currency/calendar scope, aggregate cap,
verified-versus-unknown settlement, exact synthetic gate, real PostgreSQL period
creation/row guards/RLS, month-end pause, Shanghai rollover/leap February, old
binary fences, member denial and publication/cancellation failure. They are added
to the mandatory disposable-Postgres CI job. Local skips are not PostgreSQL proof.
The previous candidate's failed cloud-browser CI is retained: its fixture carried
a synthetic Qwen policy into DeepSeek browser tests. Only the guarded disposable
localhost hcla_test fixture cleanup is corrected; production protection and test
assertions are preserved.

## Original deployment compatibility follow-up

Production read-only preflight on 2026-10-02 found only the original owner/trial
schema, with no execution.tenant column. The unapplied monthly migration now
supports this owner-only shape without adding columns or changing existing RLS,
roles or grants. Hosted CI first exercises initial cloud + trial + both Qwen
migrations in a fresh guarded localhost hcla_test database, including temporary
Mira smoke, verified settlement, ordinary owner continuation, unchanged legacy
policies, and explicit NULL/member tenant rejection. The existing full member
schema regression suite runs afterward. This does not enable membership.

PR38 merged at 3034658 with the reviewed tree; its normal production auto-deploy
was blocked by Vercel at 2026-10-02 18:28:45 UTC with “Deployment rate limited —
retry in 24 hours.” No deployment retry, live schema/grant/config activation or
provider call was made. The compatible follow-up must pass exact-head CI and
review before any later coherent production setup.
