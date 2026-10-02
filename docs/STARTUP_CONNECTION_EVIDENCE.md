# Initial connection reliability

This is a bounded reliability follow-up to the adopted consumer-entry journey, not a new activation or product feature. Source inspection of main `9f0aeb5f031da663337bf606052d1a2fc384dd4b` found that the outer `/v1/development/status` read has no deadline or in-flight ownership while its always-enabled retry button can stack requests. This outer route must resolve before ordinary member entry can appear.

The first draft adds two provider-free browser regressions against injected status responses: a held initial request must end after 15 seconds, settle the actual fetch, show an explicit retry and recover to member entry; a pending read must be visible and cannot stack duplicate reads. [Before-fix run36948878951](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36948878951), exact head `af68fb400a3fe236da33386402f7a41e98cece18`, reproduced both defects: no timeout alert after 17 seconds and an enabled retry button during the still-pending read. The pre-existing 76 general browser journeys passed, as did the cloud job. The failures and before-fix screenshots remain retained in that run. No real credentials, accounts, provider, trial window or database configuration are involved.

Local browser execution is unavailable in the restored execution container because Chromium cannot create its singleton socket; no local browser pass is claimed. Normal exact-head CI remains the acceptance path. PR28 exact-main run36948246799 subsequently passed both jobs after one isolated retry of its repository-materialization transport failure; its cloud browser/Postgres job did not need a retry.

## Bounded correction under review

The outer connection now shares one 15-second AbortController budget across development readiness and optional guest-trial status. Duplicate checks coalesce; a live ownership/revision guard prevents stale or unmounted completion from changing the global request mode. Readiness and optional trial state are applied together after both reads succeed. Failure offers an explicit read-only retry and never repeats a login, registration, password reset, trial start or provider request.

Loading/error/owner-entry screens reuse the established account surface; no new visual system is introduced. Independent source review found no blocker within this delta and requested an optional-trial held-read regression, which was added together with a 390px inactive owner-entry capture. TypeScript, both bundles, 24 JavaScript checks and 379 local Python cases (59 database deferrals) pass. Final exact-head browser results, visual inspection and exact-main adoption remain required.

## Broad-suite failure investigated

[Run36949777374](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36949777374), source `c3f2ee6399942a3c9dd1e12db1da44174ce37e8d`, passed all four new startup browser cases, 105 disposable PostgreSQL cases and 38 cloud journeys. The broad suite passed 79 browser cases and failed the existing local context-panel return-position assertion with a 1050px difference. This is retained rather than relabeled a full pass.

Its trace distinguishes the timing: focus snapshots had message scrollTop990; the pre-click offset measurement sampled2040 while the fourth accepted run was still streaming; the actual pointerdown/click snapshot had990 again. The exact1050px difference came from measuring a transient pre-activation position. The test now waits for the final send/watch completion before measuring and records the actual pointerdown offset. It additionally requires that the measured baseline and activation agree within2px; the existing2px return-position limit and deliberate-reading, resize and interrupted-source assertions are unchanged. No anchor product code was changed.

Actual before-fix blank/pending phone and desktop captures and corrected phone timeout/owner-entry captures were inspected. The corrected entry fits the established account surface with no horizontal overflow, visible status and an explicit retry. Final full-suite verification remains required.

## Reviewed implementation checkpoint

Exact source `1a92182b024b5f4d2fd2d3dc260e211c7f91f008` passed both jobs in [run36950833867](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36950833867): 379 Python cases (59 database cases deferred by the broad job), 105 real disposable PostgreSQL cases without skips, TypeScript/both bundles/24 JavaScript checks, all80 general browser journeys and all38 cloud journeys. Both local and Pages context-panel tests passed with the additional activation consistency check and unchanged2px restoration limit. The focused startup capture artifact has the same467964-byte payload as the four corrected captures already visually reviewed; the application source was unchanged by the fixture correction.

Writer implementation is complete within this bounded follow-up. This documentation/claim closure commit and its merged main still require their exact-SHA checks before adoption; CI status on a prior head is not substituted. No live Auth, mail, credentials, schema, entitlements, model call, guest activation or trial clock changed.
