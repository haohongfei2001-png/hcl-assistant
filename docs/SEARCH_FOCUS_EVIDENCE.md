# Search-result focus commitment

A bounded correction to existing historical search, based on main `2f76a762050e29200d6fcd83088454c37466fa69`. This does not adopt any upstream runtime candidate or change the reviewed lock.

## Retained initiating failure

[Upstream run36951354687](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36951354687) evaluated product `9f0aeb5f031da663337bf606052d1a2fc384dd4b` with candidate `5cc6abcef4df46db7f36641614aaef5f5433a1e8`. Acquisition, handshake, smoke, Python and build passed; browser validation passed75 cases and failed the existing historical-search result focus assertion in revision-loop.spec.js. Publication was skipped, provider calls/spend stayed0, and stable runtime remains `a8229fcf22eccb851c58502a09ae7cecb346faf5`. The retained artifact has logs and receipt but no trace, so it does not establish whether target absence or modal teardown caused that original failure.

Source review found that the shell focuses the target in one animation frame after asynchronous navigation resolves. The parent's requested run need not yet be committed to the DOM, and an older navigation can still finish after a newer selection. Independent review confirmed ProductDialog performs modal cleanup and normal trigger-focus restoration in layout cleanup, before surviving parent post-commit layout effects.

## Controlled browser reproduction

The first draft mounts the real AssistantShell with a browser-only synthetic parent that can resolve navigation separately from committing its target. It checks delayed target commitment, older-versus-newer search selection, and preserved ordinary dismissal plus newer input intent. The fixture makes zero application API calls and is served only through the test's intercepted HTML route; it is not a production entry. The existing end-to-end revision-loop focus assertion remains unchanged. [Run36955000662](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36955000662) at head `896091faa69d8bb1cfb3fdf4c42418048bc96144` reproduced missing committed-target focus in two controlled cases;81 other general browser cases passed. The second setup is being narrowed to isolate an older finalizer after a newer deliberate target focus, independently of the first commit-timing failure.

No live Auth/email, credential, schema, entitlement, provider call, trial clock or runtime-lock change is part of this work. Exact-head review/browser/capture evidence and exact-main gates remain required.

## Separate intermittent receipt view

The same run also repeated the previously retained cloud receipt-dialog miss from main run36952102582, with39 other cloud journeys passing. The existing expectation and invocation are unchanged. Cloud failures now retain traces/screenshots, and four repeats of only that existing fake-provider journey collect bounded click/dialog event metadata. This is a diagnostic product-only probe, not a full upstream sync rerun; no candidate or live activation is implied.

## Refined reproduction and correction

Diagnostic head `46e7847aadb9ff2f97ca407907704d477ce22b34` in [run36955707513](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36955707513) retains the original missing-commit failure and isolates the late older selection after a newer deliberate result focus. The full40-case cloud suite passed, but the separate diagnostic selector initially matched no tests because its beginning anchor included neither the file nor project prefix. That is recorded as a probe setup failure, not a product failure. The corrected selector was listed locally and selects exactly four repeats of the existing case. Diagnostic JSON is written to the artifact directory as well as attached to the report.

The correction retains an exact conversation/run focus intent and fulfills it only from a post-commit layout effect after modal cleanup and target presence. Newer search/navigation, pointer/key/wheel/input/composition intent, unexpected conversation change and unmount cancel it; an unresolved committed-target intent expires after15 seconds. New/open navigation completion is similarly fenced. The selected run is kept visible instead of immediately auto-scrolling to the new conversation bottom. Rejected search navigation stays in the search dialog with explicit retry feedback. No fallback first-article focus or repeated animation-frame polling is used.

Independent source review verified modal teardown ordering and found an input/IME cancellation gap, which is now covered without any preceding pointerdown or keydown. Added expiry and explicit read-only retry cases preserve ordinary dismissal behavior and existing end-to-end assertions. TypeScript and the synthetic fixture type check pass; both bundles and29 JavaScript tests pass, and the original synthetic parent canary is absent from both production bundles. Actual hosted focus/order/capture and final exact-head/main gates remain required.

## Input preservation correction

[Run36956366649](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36956366649), head `07c1840efc09a96339a415d96d9c0028b9bed111`, passed the delayed and superseded focus cases, ordinary dismissal, composition-start cancellation, expiry and explicit retry. It exposed a real regression from the first input-cancellation implementation: changing React state in a native capture-phase input listener could restore an old controlled value before React read the event. The no-pointer/key input case observed an empty draft, and existing composer growth and Pages search-input checks also failed. Those failures are retained.

Input/composition cancellation now runs in the actual React composer/search handlers, after copying the new value and within the same controlled-input update. Pointer/key/wheel intent still uses the existing capture ownership guard. The selected-run fixture now includes long trailing turns and additionally requires its focused target to remain in the viewport, preventing auto-bottom behavior from hiding the selected result. No failing assertion is removed.

The same run passed all40 cloud journeys and all4 selected receipt repeats. Persisted metadata shows each receipt click reached the action while the fake stream was still busy and opened its dialog with no page error. This does not explain or erase the earlier intermittent miss; failure tracing and the bounded diagnostic remain available.

## Corrected focus gate and retained separate receipt failure

At `5fb867d6126ec81505224bc28780d9e91abad6cc`, [run36957444572](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36957444572) passed all87 general browser checks (including the7 focus cases and both previously regressed input paths), all40 cloud checks,105 disposable-Postgres tests,379 Python tests with59 explicit database deferrals, and29 JavaScript tests. Independent source review accepted the controlled-input correction. The separate four-case receipt probe passed3 and failed1, so this is not an aggregate green or merge gate.

That retained trace proves a different interaction race: the receipt handler had zero clicks and no receipt dialog ever opened; its target was at y462..506 when the click began, then the message scroller jumped from13 to155 during the click as another same-line answer chunk arrived. The menu remained open and the stream remained pending. The static message menu expands scroll height, while the turns effect still owns automatic scrolling. This is not evidence of a dialog closing after activation. Follow-up controlled cases exercise same-line streaming, wrapping growth, and completion shrink across a held pointer gesture, without changing any receipt expectation or repeating upstream sync.

## Deterministic menu reproduction and bounded repair

At `bfb9406ceba20e20404e688b375d7f3e4f5cbb62`, [run36958292417](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36958292417) failed exactly the three new held-gesture cases (same-line, wrapping and completion), with155px target displacement in each. All88 other general browser cases, including desktop/390px-phone delayed search visibility, passed. The cloud suite and bounded receipt probe passed on that head; these passing repeats do not erase the independently reproduced defect.

The repair gives an open message action bounded geometry ownership: it records an exact action/summary offset, prevents automatic bottom following while the actual details element is open, and compensates streaming layout changes before paint. A temporary answer min-height prevents completion shrink from pulling the pressed target upward at scrollTop zero. It retains no old body text and changes no receipt/provider behavior. Closing, explicit scrolling, resize, navigation, disconnected elements and unmount release ownership. Closed summaries only stage geometry for250ms without pinning a style. When an outside pointer gesture begins, ownership releases immediately but old geometry is restored after pointerup/click, with a15s fenced fallback and cleanup on unmount, so release cannot move a different target under the held pointer.

Completion/retry focus respects the user's open menu or dialog instead of unconditionally returning to the composer. Additional controlled cases cover keyboard activation and normal dismissal, manual scrolling while a menu remains open, close/reopen, resize, an outside gesture after completion shrink, closed-summary cancellation, and navigation even with a reused turn element. Independent source review found no remaining blocker in this bounded repair. Local TypeScript, fixture checks, both bundles and29 JavaScript tests pass; full hosted behavior, captures and exact-head/main checks remain required.

## Preserve the active viewport as well as the action offset

[Run36959112574](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36959112574), head `68a2a6ddc11beb96c0274079b9ae6af1280a77f9`, passed94 general cases, all40 cloud journeys and4 receipt repetitions. The three controlled held-gesture cases retained exactly the same y475 action position across each update, but still failed activation: the ordinary unread effect inserted the44px “有新内容” banner into the layout during the gesture, shrinking the message viewport over the action. The event log shows pointerup landing on that banner, so stable target geometry alone was insufficient. This intermediate failure is retained.

The open-menu guard now leaves both auto-bottom and unread-banner state unchanged while a menu is open; it does not insert or remove a competing surface under the pointer. The original geometry and activation assertions remain, with an additional exact element-at-pointer assertion. Other menu release, search, receipt and end-to-end acceptance gates remain intact.

## Successful navigation checks and distinct local readiness failures

At `b2b36e056405415ddf3461698c8db9d22c9ea087`, [run36960007719](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36960007719) passes all17 new search/menu cases. Each of the three held gestures retains y475 before/after, the pointerup/click targets the same intended action, and the handler count is exactly1. The full40 cloud cases and4 receipt repeats also pass. The aggregate remains red because two existing local cases fail: lost-ack retry keeps its draft, and the long context fixture reaches its generic5s final-readiness wait while its mock is still generating.

The context trace has a fourth accepted mock run at03:27:50.134 and continued successful reads with768 streamed characters at03:27:55.142; it is not a stopped stream or a UI anchor drift. The fixture now waits up to15s for the actual final server result before applying the unchanged5s UI-settle and2px activation/restoration checks. No outcome or geometric tolerance is weakened.

Source review identifies the lost-ack race: the catch handler enables Send before its reconciliation GET completes, but the hidden sending lock still rejects the click. Controlled tests hold that read and separately navigate to another conversation, requiring truthful retry availability, exactly one explicit retry with the original key, and no late old view restoration. This reproduction is staged before the implementation correction.

## Reconciliation reproduction and ownership correction

At `64864231680c8efc4bdab879062fdbfa7b080f6e`, [run36961062111](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36961062111) failed exactly the two new held-read cases: the old view exposed retry before reconciliation ended, and navigating to another conversation left its enabled Send silently ignored with zero new POSTs. All97 other general cases passed, including the unchanged2px context test after server completion; the full40 cloud journeys and4 receipt repeats passed.

The send path now retains its busy ownership during a bounded15s read-only reconciliation. It shows “正在核对” on a disabled Send and does not advertise Stop for an unknown run. It captures the navigation epoch at dispatch and fences accepted-result UI, watching, focus, error and finalizer effects, including A→B→A. History navigation and even a subsequently failed New-conversation intent abort the old reconciliation without replaying the write or dropping its original draft/key. Only the owning controller/epoch may release its state. A Stop already requested for the accepted send still cancels that run independently of whether its original view remains active; its subsequent load no longer has an unowned busy clear.

The five controlled cases cover successful read release, actual read timeout with no automatic POST, navigation to a different conversation, a late A→B→A failure, and failed creation while an old read is held. Explicit unchanged-draft retry must reuse the same key and retain one recorded event/run. Local type checks and builds pass. Independent source review found no remaining blocker; final hosted exact-head/main gates remain required. This does not change server writes, idempotency/budget policy, Auth or provider activation.
