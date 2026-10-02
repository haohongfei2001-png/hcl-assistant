# Guest run diagnostics and scoped inspection

## Observed production boundary

One explicitly approved original-synthetic guest request on 2026-10-02 ended UNKNOWN without a complete answer. The existing receipt displayed requested/actual `deepseek-v4-pro`, `NO_TREATMENT`, and unknown token/cost values. The shared trial ledger retained one conservative US$1.41656064 reservation, not a known invoice charge. No automatic or manual provider retry was made. The cloud adapter has a 60-second wall deadline; the production result alone did not prove its exact error code. Neither the model, thinking settings, provider timeout, fixed trial window nor budget is changed by this repair.

The same guest's Lab control returned 401 because its frontend reader used an unscoped owner path rather than the legitimate current-tab projection. Server access protection was correct. This repair must not grant guest access to owner/member data or try an alternative server endpoint around that refusal.

## Bounded correction

The consumer receipt exposes only fixed allowlisted protocol reason codes, status numbers, send/finish enums and bounded numeric latency already present in the sanitized run. It never renders arbitrary upstream error bodies, headers, credentials or hidden reasoning. Unknown cost stays unknown, and incomplete answers explicitly state that the request is not automatically repeated.

Lab resolves the current-tab RAM projection first, preserving the exact run identity check. A missing/expired guest projection refuses locally; ordinary/member reads use their current account route with the original no-store and AbortSignal behavior. Export obtains a fresh projection/read rather than exporting the earlier displayed copy. Existing run-change, close, cancellation and permission-denial fences remain.

## Evidence

Three new controlled Lab cases failed before the fix: guest inspect/export sent an owner request, missing guest inspection fell through instead of refusing locally, and member inspection used the owner URL. All thirteen lifecycle cases then passed, including suspended-member inspect/export admission and readiness loss during a local projection. Three strict projection tests cover sent timeout versus proven no-send, malformed/untrusted metadata exclusion, and unconfirmed-transport reservation wording. The actual offline stream fixture emits only synthetic thinking metadata and heartbeats until the real adapter deadline, producing UNKNOWN/wall_timeout without persisting or rendering its hidden-text canary. This is a controlled reproduction of the timeout category, not evidence that it caused the earlier live result.

Local root checks, TypeScript/build, 39 JavaScript cases and 383 Python cases (59 disposable-database deferrals) pass. Hosted cases cover guest Lab+fresh export with zero owner inspection requests, member-only inspection routing and suspended-member refusal, and one synthetic thinking-only timeout showing safe receipt/Lab diagnostics with no repeated execution. Their exact-head result and actual captures remain required. This is provider-free engineering; no account activation, live credential access, trial restart, new grant, runtime repin or extra paid model request is included.

Resume verification (2026-10-02): root checks and build/39 JavaScript cases passed. Initial Python execution omitted the required runtime environment and failed; after using the verified locked artifact, 383 cases passed with 59 disposable-Postgres deferrals. Local Chromium could not launch because its process-singleton socket is prohibited by the execution sandbox; browser assertions therefore remain unverified locally and require hosted CI. Main 7aabd5a3 had successful Planning and Pages runs before this change.
