# C1-01 cloud adaptation evidence

Baseline: PR16 main 1dc14fe207495cf587f8c33ca11f793f9d456803. Product-owned cloud hosting adaptation only; reviewed runtime lock and capability manifest unchanged. PR17 tracks the implementation and final exact-SHA adoption.

## Actual verification

- Complete generic Python suite before the final bundle regression: 285 tests, PASS, with 13 database cases explicitly skipped in that generic invocation and run separately against real Postgres
- Actual disposable PostgreSQL 16.2 locally: 13/13 PASS, including independent-instance one-dispatch races, immutable/no-self-bootstrap budget, expired-owner fencing, durable silent-thinking cancellation with unknown transport charge retained, session revocation/throttling, cross-tenant denial, raw-copy deletion, snapshot round trips/replay denial and validation-error preservation
- The actual reviewed three-file HCL runtime executed in the temporary cloud path, returned EXECUTED and used-in-answer true on an original synthetic fixture. All Postgres tables were inspected for the source canary: no temporary body persisted. Provider bytes were injected local fixtures, not live calls
- TypeScript, both Vite builds, Pages boundary scan and 24 Node tests PASS
- Hosted head 45abced3087201379856e8c325fd11bbe266ba80: [run 36841847839](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36841847839) passed both planning and cloud-postgres jobs (67 baseline browser journeys passed; cloud cases intentionally skipped there). Cloud job passed 18 Python tests (5 unit + 13 real Postgres) and five direct-proxy browser flows: owner login/reload/logout, temporary pinned HCL/refresh loss, multi-turn privacy deletion, and body invalidation before delayed or interrupted stream completion
- Final hardening adds a sixth browser flow: logout during a delayed temporary stream must not resurrect body-bearing state. Independent read-only reproduction deliberately ignored AbortSignal and confirmed handledAfterLogout=false / bodyRetainedAfterLogout=false

Final package adoption remains conditional on PR17 final-head CI, merge and exact-main CI. A prior green SHA is not substituted for the final code.

## Failures retained and fixed

- Initial PGlite compatibility tests could not establish concurrency: its default single-connection listener rejected simultaneous connections. Switched to actual disposable PostgreSQL 16.2; PGlite is not claimed as concurrency evidence
- Local Chromium download returned invalid zip payloads; system Chromium could not create its Unix socket, including a reviewed elevated retry. No application assertion ran in those attempts. Hosted CI supplied the actual browser evidence
- First hosted cloud browser run d2034020 failed login because the loopback-only test adapter lost header case-insensitivity; fixed the fixture, preserved the production HTTPS boundary, and switched to an unbuffered Vite proxy
- A repeated anonymous GitHub acquisition reached an HTTP 403 rate limit. The build now reuses only a verified pinned cache, or copies only the already-verified three-file CI artifact plus identity; it does not bypass the rate limit or read other research files
- The production build smoke found the bundled relative runtime directory broke the subprocess handshake. Cloud construction now resolves the path before invocation, and build:cloud performs the actual handshake; CI also runs that production build path
- Independent review found premature temporary-head consumption, stale cached bodies after interrupted deletion, delayed React redaction, and a late-packet logout race. All were corrected and covered with backend/browser or independent in-memory regressions

Temporary mutation while generation is active is explicitly refused with a Stop-first explanation; it is not reported as a successful deletion. Temporary interruption may lose the conversation because no body is persisted remotely. A stale or consumed snapshot is poisoned locally rather than served as valid state.

## One-time setup simplification

Non-secret provider/hosting defaults are versioned. The normal owner path has only the database connection, model key and locally generated owner-config bundle as sensitive entries; the operator supplies the verified origin and explicitly approved grant. Browser setup performs only local Web Crypto and explicit copy, with no secret download/network/storage/history/logging. Tests use deterministic synthetic placeholders, compare Web Crypto output to the standard library without printing it, and verify the browser/server Unicode boundary. Private output is masked and is not captured in test artifacts. Independent review found and verified fixes for UTF-16/code-point length mismatch and clear/pagehide completion fencing; no P0/P1 remained. Paid model use remains disabled without a matching new grant and database policy.

## Scope and handoff

Zero real provider calls. No credentials or live cloud account/database were read or mutated; no paid resource, public service or new grant was provisioned. The exposed historical key was not retrieved or used. No TodayAction data reuse, hidden reasoning storage, efficacy claim or production HCL activation.

Offline hosting adaptation is the completed package scope. The actual HTTPS deployment, isolated owner project/credentials, newly approved model budget and any real-private-data authorization remain external gates. Ordinary application use after secure operator setup requires URL/login/chat, not developer forms or a local terminal.
