# M1-01 engineering acceptance

Source implementation: `b067283a5dd654c64c74e2a32236156b37aff7b2` in [PR24](https://github.com/haohongfei2001-png/hcl-assistant/pull/24). Both jobs passed in [run36923258592](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36923258592). The final closure head and merged main must independently pass their checks before adoption.

## Verified behavior

- M01: explicit disabled default, canonical issuer/UUID verification, email confirmation without signup auto-login, separate member cookie, exact origin/CSRF boundary, login rotation and immediate application logout
- M02: real disposable PostgreSQL proves A/B/owner route separation, tenant RLS, pooled transaction reset, scoped run execution/cancellation, snapshot/session isolation and temporary-body absence from persistent tables. Member temporary execution still uses the reviewed pinned HCL runtime
- M03: server-only entitlement changes, absent/revoked/expired rights refusal, atomic user plus operator reservations, concurrency ownership, current-grant usage display and retained historical operator charges
- M04: encrypted refresh envelopes bind issuer/subject/session/deadline with fresh nonces. Real database cases cover rotation, contention, lost-worker refusal, logout during refresh, wrong-subject/uncertain-result revocation, absolute-lifetime cap and server-key rotation. Browser automatic renewal preserves the active temporary packet and draft
- M05: all18 cloud browser tests passed, including existing owner/guest regressions and eight new account journeys. Separate browsers prove the authenticated B principal before A-resource denial; account switch clears drafts; delayed exports cannot download after logout; status reads are serialized/abortable; failed logout is visible; absolute expiry clears temporary content. Desktop and390px entry captures were inspected and showed no clipping or horizontal overflow
- M06: the complete broad Python/TypeScript/Vite/Pages and76-browser acceptance job passed. Local full Python checks ran349 tests with310 passed and39 database-dependent cases deferred to the real database gate. The cloud gate ran76 tests without skips. Planning, repository boundary and diff checks passed; no live Auth/provider call was made

## Failed attempts retained

The first cloud-browser run had two signed-in probes using Playwright's separate APIRequestContext against the HTTP localhost fixture. Those returned401 while Chromium's signed-in page worked with the unchanged Secure cookie. The probes now use the product's browser transport and verify the expected account identity, keeping exact403 cross-account denial and empty B-history assertions. [Original run](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36921357289) and its failure artifacts remain intact.

An added member-HCL isolation case initially configured the reviewed runtime for A alone, causing B to stop at the503 runtime prerequisite before snapshot verification. Both accounts now have matching reviewed runtime prerequisites; the403 snapshot assertion remains. [Original run](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36922814079) is retained. No failed assertion or access boundary was removed.

Independent security review found no blocking issue in tenant/session/budget/refresh boundaries. UI review identified delayed export and stale status races; both were corrected and covered. Minor current-grant accounting presentation was corrected without deleting history.

## Live status remains separate

Member Auth is disabled, the member migration is not installed on the live database, and no member entitlement/user/credential or email service was created. Existing owner/guest deployment behavior remains subject to actual post-merge checks. The guest4h/USD10 window has not started; no model budget was activated or spent. Public registration/email delivery, password recovery, paid billing and real-private-data use are not established by these offline tests.
