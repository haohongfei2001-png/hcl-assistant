# C1-01 cloud adaptation evidence

Baseline: PR16 main 1dc14fe207495cf587f8c33ca11f793f9d456803. Changes are product-owned cloud hosting adaptation; the reviewed runtime lock and capability manifest are unchanged.

## Verified locally so far

- Existing complete Python suite plus new cloud unit tests: 281 tests, PASS with 9 cloud-Postgres tests skipped in this generic invocation (those run separately against real Postgres)
- PGlite was used only for initial SQL compatibility; it is not concurrency evidence. Its default single-connection listener rejected multi-connection tests; those failures were retained and the test was moved to an actual disposable PostgreSQL 16.2 process
- Real PostgreSQL independent-connection tests: initial 9 passed, including one-dispatch racing callers, durable budget lock, expired-owner fencing, session revocation, cross-tenant denial and temporary state round trip
- Additional actual pinned HCL temporary preparation and validation-error head-preservation regressions passed in the expanded run
- npm run build passed: TypeScript, both Vite targets, Pages boundary scan and 24 Node tests
- Local browser launch is NOT verified: the bundled browser download returned invalid zip payloads; system Chromium then failed because this executor disallows its Unix socket, including a reviewed elevated retry. No app assertion was reached in those attempts. Hosted exact-SHA CI runs the complete baseline browser suite and separate cloud/Postgres browser flow

## Review corrections

Independent read-only review identified two temporary-state bugs during development: consuming the snapshot before input validation, and retaining an old client packet after an interrupted privacy mutation. Validation now occurs first in the volatile Controller; only then does a database CAS consume the head. Privacy acceptance clears cached bodies, and ambiguous stream interruption clears/poisons the tab entry. A non-ASCII login comparison edge was also fixed.

Temporary mutations during active generation are refused with a Stop-first explanation. This is a disclosed bounded limitation, not a false deletion success. Temporary interruption may lose the conversation because no body is persisted remotely.

## Remaining acceptance

Draft implementation, final regression additions, cloud browser proof, independent final review and exact-head/exact-main CI remain required before completion. Actual hosted endpoint, configured owner project/credentials and a new live provider budget remain separately gated. No Supabase/Vercel account was mutated; no real provider request was made; no exposed key was read or used.
