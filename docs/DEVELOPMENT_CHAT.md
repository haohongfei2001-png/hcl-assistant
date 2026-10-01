# D1-01 development-only real chat

Authority: explicit user request 2026-09-30 23:48 UTC. Same writer after P1-02. This amendment takes precedence over older blanket provider-free product-development wording only for this package. Historical mock/Pages tests, existing runtime lock, production activation, research efficacy and private-data gates are unchanged.

## Acceptance

- D01: Same UI → authenticated server → Interaction Controller → current permitted context → product-owned DeepSeek adapter → natural answer. Ordinary Chinese may use general model with explicit NO_TREATMENT, never fabricated HCL execution.
- D02: Same-conversation follow-up and explicit correction/withdrawal preserve valid context; changed policy/state cancels or withholds stale output. Generated text is never independent reusable evidence.
- D03: An original synthetic supported input uses the pinned provider-free HCL Bridge as transient answer preparation. Record selected/executed/result-produced/used separately, exact source/version/span and same-run provenance. Used means explicit output marker bound in response, not a causal efficacy claim.
- D04: Server-only existing credential, explicit provider/base/model/pricing/request and dollar budget; durable reservation before dispatch; authenticated loopback entry, no automatic billed retries. Missing configuration makes zero calls. No reasoning text retained. Unknown usage/cost is unknown, not zero.
- D05: Streaming, cancellation, timeout, rate/credit/provider errors and partial/unknown states remain truthful. Offline mocks/fakes cover interrupted flows; mock/Pages CI stays zero-call.
- D06: One command starts local API and UI and opens browser when run by user. Report whether real live smoke and controlled HTTPS URL were actually verified. No public deployment without approved persistent host, server authentication/TLS and budget storage.

## Live acceptance gate

Live smoke remains unverified. User approved on 2026-10-01 00:10 UTC: at most six original synthetic requests, 2048 output tokens each, bounded 8 KiB prompt, total at most USD 10, no automatic retry. The initial six-request bound remains; server key/model/pricing/access configuration is still required. Research experiment grants are not reusable. A missing key must be entered by the user through a secure server secret interface, never chat, VITE, browser storage, git or logs.

Existing account/model configuration can be reused when explicitly available to this product server. Public HCL code shows a client adapter, not an existing hosted HCL service. No new model default or fallback is inferred.

## Local entry and external configuration

Run `npm run chat` from this checkout after the ordinary `npm ci --ignore-scripts` setup. It starts and supervises both API and shared UI, waits for both, then opens http://127.0.0.1:5173/. Ctrl-C stops both. `npm run chat -- --check` prints only missing/invalid variable names and makes no provider request; `--no-browser` is available for supervised/headless use.

The single external setup is a securely configured, approved product server environment. `.env.example` lists its required fields; the launcher reads process environment and does not automatically source a file. Use the existing DeepSeek account credential only through a secure server configuration interface. The local access secret must already be configured by the operator, never generated or provisioned by this task without approval. Runtime sessions are ephemeral and HttpOnly; server restarts require sign-in again.

The budget database is separate from body storage. Keep `.local/development-budget.sqlite` and its lock on durable storage; do not delete/reset them to replenish budget. An existing database rejects changed caps/model/prices/ID. Unknown/cancelled attempts retain their conservative reservations and require no automatic retry. A new budget requires a new explicit authorization and intentional operator setup.

No controlled HTTPS deployment URL has been verified. This implementation binds loopback only and refuses external hosts. Public hosting is blocked pending an approved durable Python host, proper public user identity/session/TLS protection and server secret configuration; Pages remains a static zero-provider demonstration. Do not expose this loopback development server with a tunnel or treat CORS/synthetic identity as public authentication.

An operator at the local computer can run `npm run chat -- --configure` to enter all configuration directly. Provider key and local access password are masked terminal prompts, retained only in server process environment, not files or browser storage. This requires a terminal on an actual computer; it is not an iOS/web-hosted configuration URL. Stop/restart requires entering credentials again. The assistant must not fill these prompts with a key posted in chat.

## Initial approved model and pricing snapshot

User instruction 2026-10-01 00:22 UTC: use the same model as current HCL. Latest verified HCL requested and returned `deepseek-v4-pro`; this product uses that exact ID with thinking enabled and reasoning effort high. Hidden reasoning is discarded, never stored or displayed. The bounded smoke uses max2048 completion tokens; reaching length without an answer is not success and does not trigger a retry.

Official pricing checked 2026-10-01: https://api-docs.deepseek.com/quick_start/pricing/ . Peak cache-miss input USD1.32 / million and output USD3.96 / million for pro. No off-peak/cache discount is assumed. Admission reserves all 1,048,576 input tokens (rounding the documented 1M context upward) plus configured completion cap per call, rather than treating UTF-8 bytes as an official framing bound. For pro/2048 this is at most USD1.3922304 reserved per attempt, six at most USD8.3533824 within the USD10 grant. Actual paid usage is expected far below this; unknown actual cost remains unknown. Rates are a dated provider contract, not a permanent guarantee; refresh official pricing before a later authorized grant.

## Phone-compatible bounded verification

The user can add the replacement key directly as repository Actions secret `DEEPSEEK_API_KEY`; the assistant must never retrieve its value. After reviewed main/offline acceptance, the manual-only `Manual development chat smoke` workflow can inject that secret into one original-synthetic product verification. It has no schedule, PR trigger or default-CI provider access. The initial grant is `hcla-20261001-six-requests-usd10`; at most six calls, USD10 ceiling, no rerun/retry. The workflow requires its first retained run and run-number1; a refused/failed/cancelled first attempt consumes that hosted grant's execution slot. Do not delete workflow/run records to replenish it. A new attempt requires new explicit authorization and reviewed grant handling.

This verifies the backend chain and returns sanitized synthetic receipts. It does not host a persistent mobile chat website or verify a public HTTPS app URL.
