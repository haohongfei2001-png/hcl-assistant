# C1-01: isolated owner-only cloud hosting

Authorized engineering amendment: 2026-10-01 08:36 UTC. This is a Vercel deployment adaptation of the same Assistant-first UI, Controller, DeepSeek adapter and pinned HCL Bridge. It is not a production HCL/efficacy activation, permission to use real private data, account provisioning, or a renewed provider grant. The historical six-call/$10 grant remains exhausted.

## Architecture and guarantees

- Ordinary conversations use a dedicated `hcla` schema in a new, isolated Postgres/Supabase project. No TodayAction or existing authentication project is reused
- Owner signs in over the exact configured HTTPS origin. The browser sees no model, rate, grant-ID or API-key form. Server-only configuration is one-time operator setup
- Passwords use a fixed-cost scrypt verifier; sessions are opaque, hash-only database records with Secure/HttpOnly/SameSite cookies. Rotation invalidates prior sessions. Mutations require exact origin and same-app header
- POST accepts a durable Controller run. An explicit POST execute request owns bounded execution until completion; GET/SSE only reads/replays. Cold starts do not kill pending runs. Database ownership fences prevent duplicate dispatch and stale publication
- Atomic immutable budget reservations share the Controller transaction. No cold-start reset, no automatic paid retry/refund. Unconfirmed transport keeps the concurrency slot blocked; expiry is UNKNOWN rather than evidence of transport termination
- Cancel and source-policy changes are checked during silent model thinking as well as answer deltas. Output is withheld immediately on cancellation or withdrawal. Provider cancellation may still cost money
- Temporary conversations use the same volatile Controller and reviewed Bridge inside a single HTTP request. Signed state returns only to tab RAM; the database stores only opaque hashes, revision/head, ownership and budget metadata. Snapshot head checking prevents reuse of an earlier signed pre-deletion snapshot. Refresh/close loses the temporary conversation; interrupted delivery may require a new one
- HCL sample requests preserve the exact synthetic-only temporary/no-Topic contract. Authenticated owner identity is checked before the internal synthetic fixture tag is used. Ordinary unsupported language remains explicit NO_TREATMENT, without blocking ordinary model chat
- No hidden reasoning is logged, stored or streamed. Same-run explicit results and truthful treatment/usage receipts remain inspectable

## Setup and activation gates

No hosted endpoint has been verified. Do not describe repository readiness as a live website.

1. Owner approves/creates a dedicated project and selects a Vercel account/project, after reviewing costs and terms. Never reuse an existing app database
2. Apply the checked-in migration only to that new project. Create a separate login role inheriting `hcla_app`, without superuser, BYPASSRLS, schema ownership or public-table privileges. Credential creation/entry remains owner-controlled
3. In Vercel secure settings, set HCLA_DATABASE_URL to the isolated transaction-pooler URL with sslmode=verify-full, HCLA_PUBLIC_ORIGIN to the exact HTTPS origin, HCLA_OWNER_LOGIN, HCLA_OWNER_PASSWORD_HASH and a 32-byte hex HCLA_TEMPORARY_STATE_KEY. No configuration value belongs in chat, a screenshot, Git or frontend variables
4. The build runs `npm run build:cloud` and acquires only the three already-reviewed runtime files to `.hcla-runtime`; no research checkout, repin or provider call. api/index.py is the Vercel handler, maxDuration 300 seconds; adapter deadline 60 seconds and ownership deadline 120 seconds leave cleanup headroom
5. Model use stays disabled unless a new bounded grant is explicitly approved, installed as an immutable budget_policy row, and HCLA_CLOUD_PROVIDER_ENABLED=true. Requested model is deepseek-v4-pro, thinking enabled, reasoning effort high; no fallback. Existing server-side D1 budget/rate/output variables apply; HCLA_DEV_ACCESS_TOKEN is not needed for cloud login. The owner can privately run scripts/configure_cloud_owner.py once for hidden password entry, and scripts/print_cloud_budget_policy.py for approved metadata; neither helper contacts a service or installs configuration
6. Verify the actual preview HTTPS endpoint: unauthenticated denial, owner login/logout, cross-origin denial, persistence across invocations, streaming/replay/cancel, temporary refresh loss and approved HCL synthetic preparation. Live provider requests require their own remaining approved budget

Schema migration does not create a login credential, seed a model budget or grant access to anon/authenticated. `hcla_app` has no budget-policy write privilege. Supabase Data API exposure is unnecessary; keep the private schema unexposed. Configure backup retention and log redaction for the eventual data authorization before enabling real personal use. Logical deletion purges application copies but is not a claim of immediate provider/backup erasure.

## Acceptance

C01: Postgres/tenant/idempotency/policy/delete compatibility and immutable budget
C02: owner-only HTTPS sessions, revocation, cross-origin denial and rate limits
C03: independent-instance request ownership, lease recovery/fence and zero duplicate dispatch
C04: durable cancellation, source withdrawal, replay and unknown-usage accounting
C05: shared UI plus tab-memory-only temporary Controller/Bridge, signed-state replay denial
C06: offline full regression/build/browser, real disposable Postgres CI, exact-head and exact-main

Actual commands/results are recorded in C1_01_EVIDENCE.md. Cloud readiness, account setup and hosted endpoint verification remain distinct.

Primary references checked 2026-10-01: [Vercel Python](https://vercel.com/docs/functions/runtimes/python), [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security). Transaction pooling uses no prepared statements or session advisory locks.
