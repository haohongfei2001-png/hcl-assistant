# Member logout lifecycle recovery

Bounded follow-up to the adopted ordinary account journey, based on main `52e85ed4ad15c196650ff62627d2e79c825c2926`. No server credential, cookie policy, Auth setting, permission, provider, trial window or database schema is changed.

## Reproduced before the correction

The exact prior MemberEntry source blob `04711b24a8a6326025924c685d231ee71357bd9c` failed three controlled component tests while the existing24 JavaScript cases passed:

- A status read begun during a held logout was neither cancelled nor fenced when logout succeeded. A separate controlled probe resolved that old authenticated snapshot afterward and observed the signed-in UI return, even though the server session had been revoked
- A healthy status poll silently erased the visible failure of an unsuccessful logout, even though no new logout had been submitted
- A superseded logout completion cleared the busy state of a newer sign-in submission after a cross-tab session notice

The initial test harness attempted to mock BroadcastChannel as an ordinary method and hit Node EventTarget initialization errors. The harness now replaces and restores the whole constructor, matching the existing controlled-hook test approach. These harness errors were not classified as product failures.

## Correction and scope

Successful logout now advances the UI revision and cancels a status read that began during logout before clearing the account view. A separate logout-error state survives healthy background polls until explicit retry or account identity clearance; a current connection/authorization error still takes precedence. Logout finalization updates busy state only while it owns the current revision, so a newer account submission remains locked against duplicate clicks. No auth mutation is automatically retried.

The five controlled component regressions cover the three failures, connection-error priority without losing the unresolved logout notice, and clearing stale connection feedback only after confirmed logout. All29 JavaScript checks, TypeScript and local builds pass;379 Python cases pass with59 database cases deferred to the separate real Postgres gate. Two injected-auth browser cases hold the real status transport across confirmed logout and verify failed-logout feedback after a healthy poll, with exact mutation counts and actual captures. Hosted browser, independent source review and exact-head/main checks remain required.

Controlled hooks establish UI orchestration only. They do not substitute for real database/session-revocation tests, certify every cookie ordering race, or prove live account readiness.

Independent source review found one additional feedback edge: confirmed logout after a connection outage retained the old read-only/renewal warning on the signed-out form. A focused controlled case failed on the reviewed draft and passed after confirmed completion also clears that stale connection error. Failed logout does not clear current connection uncertainty. The server cookie ordering contract is unchanged and is not certified by these UI-only tests.

## Reviewed implementation checkpoint

Exact source `9dac917418677c267258209cea788f962743f00d` passed both jobs in [run36953218454](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36953218454): all80 general browser journeys, all40 cloud browser journeys, 105 disposable PostgreSQL cases without skips, 379 Python cases with59 database deferrals in the broad job, TypeScript/both bundles and29 JavaScript checks.

The held-status browser test verified that the actual fetch aborts and settles before its old response is released, then remains signed out with the previous account body absent and exactly one logout write. The failed-logout test verified the error after a healthy poll, then exactly one explicit second write. Confirmed-signout and retained-error captures from [artifact11204788436](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36953218454/artifacts/11204788436) were visually inspected; signed-out entry and retry feedback remain clear. Independent source review has no remaining blocker in this bounded delta.

Implementation and review are complete; this documentation/claim closure commit and eventual merged main still require their exact-SHA checks. All live activation gates remain separate and unchanged.
