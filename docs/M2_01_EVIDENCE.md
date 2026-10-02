# M2-01 password recovery acceptance

Current source: `5345736662001a216ffa6848a883d535026907d0` in [PR28](https://github.com/haohongfei2001-png/hcl-assistant/pull/28). Independent security and UI source reviews are complete, including a fresh review of the exact source after continuation. Both jobs passed in [run36941191007](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36941191007). The final documentation/queue commit and merged main still require their own exact-SHA gates; this record does not claim adoption before those checks.

## Verified bounded evidence

- The exact-head broad gate ran 379 Python tests: 320 passed and 59 database-dependent cases deferred to the separate disposable PostgreSQL job. TypeScript, both Vite bundles, 24 JavaScript checks, planning and repository-boundary checks passed, followed by 76 general browser journeys
- The exact-head cloud gate passed all 105 cloud tests on real disposable PostgreSQL without skips and all 38 cloud browser journeys. Its successful callback-privacy assertion requires zero code-bearing non-document request URLs or referrers. The earlier privacy failure is retained below
- PostgreSQL cases cover two distinct recovery cookies, stale requested links and ready grants, login before/during/after reset, late refresh, cross-account isolation, budget/cancellation revocation, generation rewind, RLS/pool reset and preserving in-flight records through cookie rotation/expiry cleanup
- Browser cases establish generic unknown-email presentation, wrong-browser and replay refusal, expiry/restart, explicit retry after known rejection, uncertain-result locking even with fresh mailbox proof, revocation of another open browser, and malformed callback explanations
- Actual 390px password-form and completed-phone captures, and the settled 1280px locked-state capture, were downloaded from the successful exact-head [browser artifact](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36941191007/artifacts/11200242487) and visually inspected. Primary actions and readable text fit the adopted account surface without horizontal overflow; the locked view offers a read-only status check rather than a misleading restart. The phone completion visibly returns to login
- PGlite additionally checked all four migrations, SQL compatibility, recovery RLS, expiry cleanup and generation monotonicity. It is not multi-instance/concurrency evidence

## Failed attempts retained

[Run36940190315](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36940190315) stopped on one new test helper that called account authentication twice, passing a cookie string to a method expecting a request. The existing login helper already authenticates; the redundant call was removed. All denial and zero-paid-attempt assertions remain.

[Run36940416678](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36940416678) then detected a recovery code in a non-document request URL/referrer on the local Vite page. Vite injects its development client before the HTML referrer meta. Production already specifies the response-level no-referrer policy; local server and preview now share that policy too. The browser assertion still requires zero code-bearing non-document requests and records only redacted paths, types and booleans. The correction passed its exact-head browser test in run36941191007; the assertion was not weakened.

Source review also corrected stale recovery grants, concurrent remote mutation, loss of live mutation records during cleanup, and contradictory restart/status feedback. Unknown or orphan upstream mutations remain locked pending authoritative provider reconciliation; a fresh link or timer cannot establish that an earlier remote write has ended.

## Final review and adoption gate

The final independent source review rechecked the global transaction advisory lock around tenant reset claims, pre/during-reset login tickets, stale ready grants, generation monotonicity, uncertain and orphan upstream locks, cleanup preservation, issuer/callback restrictions, vault binding, disabled flags, early referrer protection and interrupted UI recovery. No remaining P1/P2 issue was found in that reviewed scope. The package is recorded complete within its disabled engineering scope; final-head and exact-main CI remain mandatory before adoption.

## Activation remains separate

No live email, Auth setting, credential, schema, entitlement, provider call or trial clock changed. Recovery defaults off and requires the explicit flag, reviewed schema, fixed callback allowance and verified email delivery at a separately approved activation. Hosting access-log handling of the initial callback query remains an activation consideration. This is provider-free engineering evidence, not live consumer readiness. Contract: [bounded password recovery](PASSWORD_RECOVERY.md).
