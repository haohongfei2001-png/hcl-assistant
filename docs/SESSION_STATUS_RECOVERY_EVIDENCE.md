# Late session-status admission recovery

Bounded consumer maintenance from adopted main
`b083ac25e22176a58eb048068b90ceb485800c8c` (PR60).
The current M3 queue, live merchant decisions, activation gates, runtime lock and
shared budget remain unchanged. Ordinary real-provider acceptance is still open.

## Retained reproduction and repair

A controlled actual-component lifecycle test failed on the base: a late
`authenticated=true` status with an already expired session cleared `renewing`,
reopening write admission. Server authentication remained authoritative; this
was a frontend recovery/admission defect, not a demonstrated server bypass.

The same deadline check now covers both status and session-renewal responses
before accepting them. An expired response leaves the current view and draft
read-only; existing bounded polling can accept a subsequently fresh session.
No new provider call, automatic model retry, account grant or paid action is added.

## Verification boundary

Local lifecycle tests: 22 passed, zero skipped, including the retained failure
now passing and the equivalent delayed renewal response. TypeScript, both Vite
builds, preview bundle boundary and all 86 Node view tests pass. Base Python
regressions with the exact reviewed runtime and locked dependencies: 502 collected,
375 passed, 127 disposable-Postgres/owner-schema deferrals; these skips are not passes.

An actual-App browser case verifies the expired response was consumed via its
specific notice, blocks Send and Enter without POST, retains the draft and
recovers only after a fresh status. It is collected but not locally executed:
Chromium fails before test bodies with process-singleton socket EPERM. Hosted
exact-head browser and isolated-Postgres checks and independent review remain
required, followed by exact-main verification after adoption. No production
account, real model, email, payment or complete-plan acceptance is claimed.
