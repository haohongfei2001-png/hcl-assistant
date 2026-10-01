# D1-01 development chat evidence (in progress)

Baseline: adopted P1-02 main 905ff1fbb3b2264757931e8d9ff5fdff54e7a32f; exact-main planning36793205037 and Pages36793205067 passed. PR11 Continuum design draft is unmerged and not adopted here.

Implemented: same shared UI → loopback session auth → existing Interaction Controller → current permitted context/history → separate provider-free pinned HCL preparation when explicitly supported → gated DeepSeek streaming adapter → same-run answer/usage/provenance. Mock/Pages defaults and CI remain zero external provider calls. Ordinary Chinese explicitly has NO_TREATMENT when no supported HCL preparation was requested. Generated answers are not independent memory evidence.

Local verification before corrected browser batch:
- Full Python discovery with exact allowed runtime: 252 tests passed, including40 fake transport tests,25 durable budget/config tests,11 Controller tests,5 one-hosted-grant guard tests and4 loopback auth tests
- Both local/Pages builds, static bundle boundary, planning/root checks and diff whitespace passed
- Actual pinned HCL Bridge with original synthetic input plus fake provider exercised EXECUTED/result/explicit-used/source-span in one run
- One-command launcher --no-browser actually brought API/UI up; missing config correctly refused live mode; Ctrl-C stopped both service groups
- No local browser launch; hosted browser evidence is required separately

First hosted head a6093624, run36795442530: Python/build passed;42/46 browser cases passed. Three legacy test helpers raced asynchronous server-mode bootstrap and toggled the sidebar closed; one new fake fixture confused generic marker instruction with actual HCL output. Corrected helpers wait for the rendered composer, and the fake checks an actual supplied marker. Assertions were retained, not skipped.

Independent review found and addressed history-source dependency redaction, required Explain fields, mock capability-label leakage, hosted grant replay/deleted-history guarding, unconfirmed transport-stop concurrency, and ambiguous post-dispatch receipt reporting. Final scoped clearance and exact-final-head/main CI are adoption requirements, not claimed here yet.

Live user authorization: initial at most6 original synthetic calls, total USD10; repository secret entered directly by user, no key value read. Model deepseek-v4-pro with thinking enabled/high per latest explicit same-HCL choice,2048 completion cap. Official peak prices and full-context conservative reservation documented in DEVELOPMENT_CHAT.md. Manual-only workflow is not default CI and refuses automatic retries or second execution of this grant.

Actual live chat: NOT_YET_VERIFIED. Public HTTPS app URL: NOT_VERIFIED. Efficacy: NOT_TESTED. Secure repository secret presence confirmation and code are not proof of a connected chat product. D1 remains current until truthful acceptance or an explicit external blocker handoff; P1-03 is deferred, not discarded.
