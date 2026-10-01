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

The first Vercel bootstrap at `96fc1d237b8da51555897f6d93390c00c4134c8c` served static assets, but `/v1/development/status` failed with `FUNCTION_INVOCATION_FAILED`. Vercel discovered the imported internal `application` factory instead of the HTTP handler. Static readiness did not establish hosted usability; an unconfigured deployment must return a truthful status, never bypass setup or authentication.

The entrypoint correction keeps only the explicit HTTP `handler` export, retains the same handler instance under Vercel's request wrapper, and opens/closes application resources inside each GET/POST dispatch. Readiness pings do not create an application. Access-log suppression remains below the host's `log_message` override. Existing owner, database, provider-budget, synthetic-only and production gates are unchanged.

Verification adds `tests/test_vercel_entrypoint.py` for wrapper dispatch, cleanup, isolation and streaming, plus `scripts/smoke_vercel_entrypoint.py` against the actual pinned `vercel-runtime==0.22.1` streaming/IPC runtime in CI. The smoke runs with no inherited app configuration, checks readiness, HTTP 200 unconfigured status, private-route denial, one start/end pair per request and URL-log redaction. The cloud workspace blocks local socket creation, including an elevated retry; local unit checks do not substitute for that hosted-runtime test or the post-merge public endpoint check. No credentials, database provisioning or provider calls are part of this fix.

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

The first fix head passed the actual Vercel runtime smoke, real Postgres and seven cloud browser flows. Its broader browser suite passed all 75 tests but exceeded the eight-minute job budget; a retry exposed an intermittent existing source-return focus assertion (74/75 passed). The follow-on correction restores focus in the React commit phase and adds a delayed-frame regression instead of weakening assertions. The planning job receives a bounded 12-minute allowance for installation, the complete suite and retained visual artifacts. Exact final-head/main and public endpoint verification remain adoption gates.

## Safe startup diagnostics

After owner configuration and a production redeploy of `ebfbcef14ab2a86230dc877ec94059ae195a95d0`, the public status still returned `configured=false`. The previous catch-all discarded all startup causes. A TLS trust-store mismatch is only a hypothesis; no TLS weakening, role expansion or credential change is justified by that response.

Startup failures now emit one bounded server-only line, `HCLA_STARTUP_FAILED code=<CODE>`. The code is a fixed enum: `CONFIG`, `DATABASE_DRIVER`, `DATABASE_CONNECT`, `DATABASE_TLS`, `DATABASE_ROLE`, `DATABASE_SCHEMA`, `TEMPORARY_STORE`, `OWNER_AUTH`, `RUNTIME_BRIDGE`, `LIFECYCLE`, `PROVIDER_BUDGET`, `PROVIDER_ADAPTER`, or `UNKNOWN`. Codes identify the failing stage, not an inferred root cause. `DATABASE_TLS` is used only for a native typed TLS exception; libpq connection failures without that structured type remain `DATABASE_CONNECT`, which may include network, authentication or TLS failures. No exception string/repr/traceback, SQLSTATE text, environment value, DSN, host, query, login, verifier or other identifier is logged. A direct bounded stderr write avoids logging-handler fallback tracebacks; a failed sink is safely ignored.

The public status payload and private-route denial are unchanged. Each invocation has an independent diagnostic object. Partial Postgres constructors and failed application initialization close any resources they obtained; cleanup failure cannot replace the safe unconfigured response. `verify-full`, system CA trust, restricted-role checks, RLS, budget authorization, synthetic-only data scope and production gates are unchanged. No grant still means no provider adapter or budget construction.

`tests/test_cloud_startup.py` uses secret sentinels and exceptions that refuse string/repr formatting, covering all startup phases, cleanup failures, log-sink failure, unchanged role/schema refusal, no-grant behavior and independent request codes. The actual Vercel runtime smoke uses only synthetic invalid setup values and verifies the safe code reaches server logs without the sentinel or traceback. CI also retains the real disposable Postgres and existing browser suites. Hosted root-cause diagnosis remains pending until the new deployment's fixed code is observed; the diagnostic change alone is not a claim that configured login or chat works.

## Explicit host CA bundle correction

Credential-free inspection reproduced a packaging defect in the exact `psycopg-binary==3.2.12` Linux wheel: its bundled OpenSSL defaults refer to build-machine CA locations absent from the runtime. With no environment override, default trust loading can report success while loading zero certificates. An explicit host CA file loaded real trust anchors. PostgreSQL's `sslrootcert=system` uses that TLS library's defaults, not necessarily the host Python/OpenSSL defaults.

The Postgres connector now passes Python's existing `ssl.get_default_verify_paths().cafile` explicitly to libpq. If standalone Python's default is absent and no explicit SSL_CERT_FILE or SSL_CERT_DIR override exists, only an existing standard Amazon Linux or Debian CA bundle may be selected. An explicit broken override is not ignored. The selected file must exist; otherwise startup fails closed with `DATABASE_TLS` before connecting. `sslmode=verify-full` is passed explicitly as a driver keyword as well as required in configuration, overriding libpq legacy URI aliases such as `requiressl=0`. No certificate-validation downgrade, custom certificate, new dependency, environment-value disclosure or credential change is introduced. `scripts/smoke_cloud_ca.py` loads that selected file into the actual pinned wheel's TLS context in CI and asserts a nonempty trust store without opening a socket. Unit tests retain the connection policy and absent-bundle refusal. This establishes the local defect and correction, not the remote pooler's certificate or the deployed application's root cause; public status is rechecked after deployment.

Primary references: [PostgreSQL sslrootcert](https://www.postgresql.org/docs/17/libpq-connect.html#LIBPQ-CONNECT-SSLROOTCERT), [OpenSSL trust locations](https://docs.openssl.org/3.5/man3/SSL_CTX_load_verify_locations/), [Python default verify paths](https://docs.python.org/3/library/ssl.html#ssl.get_default_verify_paths).

## Supabase private CA requirement

After the OS-root correction, production still returned `configured=false`, and the owner-provided runtime log identified `DATABASE_CONNECT`. That code does not distinguish libpq TLS failure from authentication/network failure. Supabase's official [SSL guide](https://supabase.com/docs/guides/platform/ssl-enforcement) explicitly requires its downloadable CA for `verify-full`, including shared-pooler connections. OS public roots alone do not meet that documented requirement.

The public CA is obtained from the [production download](https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt) linked by the dashboard's [source](https://github.com/supabase/supabase/blob/be976bec49da3c92d030a526e7916688449a2638/apps/studio/hooks/custom-content/custom-content.json). It is bundled at `packages/cloud/certs/supabase-root-2021.crt`, SHA256(file) `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`, SHA256(certificate) `807025AD50D4ED219D2C9C7D299C004F824EB00CF7F65AFEF607D07B72E6CAFA`, valid 2021-04-28 through 2031-04-26. Its self-signature and CA key usage were inspected without credentials.

This pinned certificate is selected only for the exact Supabase shared-pooler/direct-database hostname patterns. Other Postgres hosts retain the existing OS-root policy. It is not installed into the OS, provider transport or browser trust store. Explicit `sslmode=verify-full` remains enforced, including hostname verification; no custom/insecure TLS mode or certificate-warning bypass is introduced. Certificate tampering fails closed.

CI loads the bundled root in the actual pinned psycopg TLS library, and runs `scripts/smoke_supabase_tls.py` against the owner's already verified public shared pooler. The latter sends only an SSLRequest plus TLS negotiation: no Postgres startup packet, username, password, SQL, body or model request. It verifies certificate chain and hostname. Local socket/DNS restrictions prevent a local remote-handshake claim; hosted CI and post-merge public status determine the actual result.

The preceding exact-main broad suite also exposed a revision-replay test waiting only five seconds for a deliberately streamed mock answer to finish. The screenshot showed accepted processing, not a rejected correction. The test now captures the single accepted revision POST, waits explicitly for that run's terminal `pending=false` state (bounded15seconds), and retains every existing editor, history and corrected-context assertion. No application timing or assertion is weakened.
