# Bounded temporary guest trial

User-requested engineering scope (2026-10-01): no-login temporary synthetic trial, a single shared window of at most four hours, and a total new-grant ceiling of USD10. This is not membership, production HCL activation, real-private-data permission or an automatic renewal of any historical grant. Code/CI does not activate the trial or make real provider requests.

## Isolation and limits

- The guest has a separate purpose- and policy-signed Secure/HttpOnly/SameSite cookie. It is never accepted as the owner cookie. Starting another tab reuses a valid guest cookie without extending its fixed deadline
- Only GET `/v1/trial/status` and POST `/v1/trial/start`, `/v1/trial/execute`, `/v1/trial/cancel` are guest routes. Exact HTTPS host/origin and same-app request checks remain mandatory. Guest routes cannot fall through to owner routes
- The browser uses the existing temporary Controller/Bridge packet in tab RAM. Temporary memory and no Topic are enforced by the server. Lists/search/Explain/source inspection use only that tab's packet; the guest client does not fetch owner history. Refresh loses content
- Snapshot signatures, replay heads, execution leases and cancellation are bound to the guest session. A client-supplied UUID alone cannot cancel another guest's request. Temporary bodies never enter the persistent ledger
- With a trial-only grant, owner persistent model dispatch and the owner temporary transport are disabled. The owner cookie cannot bypass guest scope or trial expiry
- Database time enforces the immutable start/end before issuance and budget admission. In-flight probes use a conservative monotonic deadline and bounded database refresh; the deadline can move earlier, never later. Publication rechecks the active window. Expiry or permission uncertainty clears guest tab RAM and aborts streams
- All guests share the same new USD10 grant and global concurrency rule. New tabs, cookies, cold starts and redeploys do not reset time, spend or unknown transport holds. There is no extra small per-user request-count limit

## Versioned budget settlement

Migration `20261001174151_bounded_temporary_trial.sql` adds separate RLS-protected `trial_budget_policy` and `trial_budget_attempts` metadata tables. No existing v2 policy, attempt row, check constraint or historical reservation is rewritten. Runtime role can read but cannot create/change the immutable trial policy.

Policy version3 still reserves the full documented 1,048,576 input tokens plus configured maximum completion tokens at the existing reviewed peak prices before dispatch. There is no byte/token billing heuristic. Only a completed, stopped, uncancelled response with positive consistent full usage within those bounds can release unused admission reserve to the peak-priced known usage. Settlement rechecks the execution ownership fence and uncached cancellation under the same database transaction lock. Repeating settlement is idempotent. Any malformed or conflicting usage record permanently disqualifies that response from settlement, so later invalid fields cannot reuse earlier valid counts. Unknown, failed, cancelled, missing/inconsistent usage and unconfirmed transport retain the full reservation; uncertain transport retains the concurrency block. This is internal admission accounting, not a claim of a provider invoice or a financial refund.

## Separate activation

1. Apply the additive migration only to the dedicated HCLA database
2. Select a new approved grant ID, USD10 maximum and a nonbinding large request bound; historical consumed grants stay rejected
3. Once actual server/key readiness is established, choose fixed UTC epoch `starts_at` and `expires_at` values, no more than14,400 seconds apart. Install the matching immutable v3 metadata in `trial_budget_policy` using `scripts/print_cloud_budget_policy.py --approved-grant ... --approved-trial-window ...`. The application reads this exact server-controlled policy; the owner does not need duplicate grant/window environment fields. The runtime role cannot write it
4. The model key stays owner-entered in the secure server interface. Key alone enables nothing; the validated immutable database policy is required. No key appears in a page, repository, URL, log or chat
5. Rebuild, verify the real public endpoint, and report the actual usable start/end. A failed startup does not establish a usable trial. No live test call is implied by offline CI

Normal activation is through the immutable database policy. An existing explicit environment grant remains compatibility-only; `HCLA_TRIAL_WINDOW` is accepted only together with such a separately validated grant. A missing key or absent trial policy leaves model execution disabled; policy mismatch or invalid bounds fail closed. The deployment operator must not silently replace an existing grant or begin the clock while setup remains blocked.

## Verification

Provider-free unit tests cover cookie/domain separation, fixed windows, policy binding, expiry and cancellation. Disposable Postgres tests cover owner-route denial, two-guest snapshot/cancel isolation, persistent-scope refusal, immutable policy, v2 preservation, global budget admission and actual Controller usage settlement. Browser fixtures cover no-login temporary chat, no owner-history requests, two-browser isolation and expiry/refresh RAM clearing. Existing owner, Vercel entrypoint, CA, Controller/Bridge and broad UI regressions remain required. Actual hosted trial verification and live-budget activation remain separate completion gates.
