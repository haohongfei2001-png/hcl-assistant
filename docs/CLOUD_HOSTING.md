# C1-01: isolated owner-only cloud hosting

Authorized engineering amendment: 2026-10-01 08:36 UTC. This is a Vercel deployment adaptation of the same Assistant-first UI, Controller, DeepSeek adapter and pinned HCL Bridge. It is not a production HCL/efficacy activation, permission to use real private data, account provisioning, or a renewed provider grant. The historical six-call/$10 grant remains exhausted.

## Architecture and guarantees

- Ordinary conversations use a dedicated `hcla` schema in a new, isolated Postgres/Supabase project. No TodayAction or existing authentication project is reused
- Owner signs in over the exact configured HTTPS origin. The browser sees no model, rate, grant-ID or API-key form. Server-only configuration is one-time operator setup
- Passwords use a fixed-cost salted scrypt or PBKDF2 verifier; sessions are opaque, hash-only database records with Secure/HttpOnly/SameSite cookies. Rotation invalidates prior sessions. Mutations require exact origin and same-app header
- POST accepts a durable Controller run. An explicit POST execute request owns bounded execution until completion; GET/SSE only reads/replays. Cold starts do not kill pending runs. Database ownership fences prevent duplicate dispatch and stale publication
- Atomic immutable budget reservations share the Controller transaction. No cold-start reset, no automatic paid retry/refund. Unconfirmed transport keeps the concurrency slot blocked; expiry is UNKNOWN rather than evidence of transport termination
- Cancel and source-policy changes are checked during silent model thinking as well as answer deltas. Output is withheld immediately on cancellation or withdrawal. Provider cancellation may still cost money
- Temporary conversations use the same volatile Controller and reviewed Bridge inside a single HTTP request. Signed state returns only to tab RAM; the database stores only opaque hashes, revision/head, ownership and budget metadata. Snapshot head checking prevents reuse of an earlier signed pre-deletion snapshot. Refresh/close loses the temporary conversation; interrupted delivery may require a new one
- HCL sample requests preserve the exact synthetic-only temporary/no-Topic contract. Authenticated owner identity is checked before the internal synthetic fixture tag is used. Ordinary unsupported language remains explicit NO_TREATMENT, without blocking ordinary model chat
- No hidden reasoning is logged, stored or streamed. Same-run explicit results and truthful treatment/usage receipts remain inspectable

## One-time setup and activation gates

No hosted endpoint has been verified. Repository readiness is not a live website.

The normal setup has **three sensitive entries**, all personally controlled by the owner. Model names, rates, output limit and build defaults are versioned in `control/cloud-profile.json` and `vercel.json`; they are not a user form. No model grant is enabled by default.

1. Approve the isolated target and bounds together: a NEW HCLA Supabase/Postgres project, a Vercel project from this repository, owner-only access, selected free/paid plan, and a NEW request-count/total-USD/data-scope grant. Confirm actual costs/terms shown by providers; persistent credential/access steps retain their required action-time approval
2. The operator applies the migration only to the new project, prepares a restricted database login inheriting hcla_app, configures the verified HTTPS origin, and installs the explicitly approved immutable budget-policy metadata. No existing app/auth database is reused
3. The owner privately enters HCLA_DATABASE_URL in Vercel's secure environment interface. It must be the restricted login's transaction-pooler connection string, with sslmode=verify-full; system CA trust is used. The app refuses superuser/BYPASSRLS connections
4. The owner opens the verified site's /owner-setup.html, chooses a login/password, and explicitly clicks Generate. Web Crypto computes a salted PBKDF2-HMAC-SHA256 verifier (600,000 iterations) and CSPRNG signing key in that browser only. One masked HCLA_OWNER_CONFIG value is explicitly copied by the owner directly into Vercel's secure environment field. No terminal, manual hash computation, download, network submission, third-party script, analytics, URL/query propagation or browser storage is used. Do not screenshot or share the result. This does not create an account or configure the server by itself
5. The owner privately enters the newly secured HCLA_DEEPSEEK_API_KEY. The operator fills HCLA_PUBLIC_ORIGIN and HCLA_MODEL_GRANT from verified non-secret setup/approval information. A key alone never enables paid calls; grant metadata plus its matching database policy are required. The exhausted historical grant is explicitly rejected
6. Rebuild and verify the actual HTTPS endpoint: denial before login, login/logout, cross-origin denial, persistent reload, streaming/replay/cancel, temporary refresh loss and actual approved HCL preparation. Real provider requests require remaining explicit budget. Real-private-data and production HCL activation remain separate gates

The owner-only setup helper loads only same-origin static code/style assets. After password entry it makes no requests, writes no storage/history/logs, and creates no file. Browser tests use deterministic synthetic bytes and never render the private output in screenshots or test artifacts. A legacy private command-line helper remains optional for operators; it is not the normal user path.

Schema migration creates no login credential, model budget or anon/authenticated access. hcla_app cannot write budget_policy. Supabase Data API exposure is unnecessary; keep hcla unexposed. Before enabling any real personal-data scope, verify backup retention and log redaction. Logical application deletion is not a claim of immediate provider/backup erasure.

## Acceptance

C01: Postgres/tenant/idempotency/policy/delete compatibility and immutable budget
C02: owner-only HTTPS sessions, revocation, cross-origin denial and rate limits
C03: independent-instance request ownership, lease recovery/fence and zero duplicate dispatch
C04: durable cancellation, source withdrawal, replay and unknown-usage accounting
C05: shared UI plus tab-memory-only temporary Controller/Bridge, signed-state replay denial
C06: offline full regression/build/browser, real disposable Postgres CI, exact-head and exact-main

Actual commands/results are recorded in C1_01_EVIDENCE.md. Cloud readiness, account setup and hosted endpoint verification remain distinct.

Primary references checked 2026-10-01: [Vercel Python](https://vercel.com/docs/functions/runtimes/python), [Supabase connections](https://supabase.com/docs/guides/database/connecting-to-postgres), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security). Transaction pooling uses no prepared statements or session advisory locks.

## Exact deployment fields

Owner-managed sensitive fields, entered only in Vercel secure settings:
- HCLA_DATABASE_URL
- HCLA_DEEPSEEK_API_KEY
- HCLA_OWNER_CONFIG, generated locally by the explicit browser setup action

Operator-managed non-secret fields:
- HCLA_PUBLIC_ORIGIN: verified HTTPS origin without trailing slash
- HCLA_MODEL_GRANT: JSON object containing budget_id, max_requests (integer), max_cost_usd (decimal string), matching the user's new approval. It has no default value

The metadata-only scripts/print_cloud_budget_policy.py --approved-grant helper converts that same non-secret JSON to the immutable database policy. It reads no credentials and does not install anything. Historical per-field D1 configuration remains compatibility-only; it is not required for normal setup.

Safe blank deployment template: docs/CLOUD_ENV_TEMPLATE.txt (the existing .env.example remains local-mode only) (never commit a filled copy). Committed defaults: Vite, build npm run build:cloud, output dist, Python function maximum 300 seconds, DeepSeek official HTTPS endpoint, deepseek-v4-pro, thinking enabled/high, 8192 output-token cap and the existing reviewed peak-rate floor. Recheck official peak rates at new grant approval. The build copies/reuses only an exact verified three-file runtime slice and performs its real subprocess handshake.

Cryptographic reference: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). The existing server scrypt verifier remains supported; browser setup uses the fixed Web Crypto-compatible PBKDF2 parameters, not a fast unsalted hash.
