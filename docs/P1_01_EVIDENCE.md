# P1-01 shared Assistant-first shell

Baseline: adopted P0 main `ca97db4884c1a09dd662dcd3c67c866942826d3b`, [P0 exact-main CI](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36782221183). Single implementation writer [PR9](https://github.com/haohongfei2001-png/hcl-assistant/pull/9).

Both local and Pages import the same React AssistantShell, product-view contract, bounded safe Markdown renderer, dialog and visual stylesheet. The shell cannot select facts, mutate records or call providers. Local retains Controller/SSE/idempotency/cancel/retry and permission-filtered source/revision APIs; Pages retains the P0 browser-only Controller, Web Locks, unique storage revision, transactional rollback, migration cleanup and cross-tab panel invalidation. Pages does not advertise project reuse, which its adapter cannot perform.

Home directly accepts input. Navigation offers recent conversations, title search, memory and settings. Current scope remains separate from next-conversation defaults. A single truthful environment identity remains visible; routes/versions/each-turn Lab actions move to contextual details. Adopted reading typography/spacing, autosizing composer, Chinese IME handling, attachment status, newer-draft preservation, keyboard focus and narrow drawer are shared. Markdown handles text/list/code/quote/table without HTML execution or automatic remote images.

P1-01 does not claim the full P1-02 evidence/change/search loop or P1-03 integrated acceptance is complete. Existing bounded panels remain transitional views. No real private data, model/provider call, runtime repin, production activation, research write, efficacy, Judge or agent claim.

## Verification in progress

Local151Python, both TypeScript/Vite builds and actual static Pages bundle boundary PASS. Hosted browser suites preserve all21 P0/local/development journeys and add shared shell/IME/scope, interrupted drafts/uploads/evidence, safe Markdown/copy/scroll, responsive/zoom/reduced-motion and static request allowlist checks. Browser uses built Pages output, not legacy raw UI. Workflow publishes synthetic screenshots/failure context; screenshots certify appearance only.

Independent early review identified first-message creation draft overwrite, file payload entering composer, and stale request/panel response after navigation. These were repaired before the first hosted batch, with original synthetic regression cases. Exact-head/full hosted browser and exact-main remain required before package completion.

Shared editing copies original input into a new unsent controlled event, never rewrites history. Source-derived drafts are tracked separately from independently typed drafts: deletion/cross-tab invalidation purges the former when their source disappears, while unrelated drafts remain. Both surfaces have explicit regression coverage.

First hosted head8bb452b failed16/32 browser journeys (16 passed). Ten failures were the old non-exact composer selector matching the newly labelled transcript as well; assertions now target the exact composer. Other failures exposed create/save completion timing and a real auto-create expected-state-version bug in local send: the captured pre-create version was stale after account history grew. Version tracking now follows the loaded target; creation preserves intervening typing, and tests await actual ready scope. Retry/stop/revision continuations also obey navigation tokens. Failure evidence/screenshots remain in CI36784258151; no original assertions were dropped.

Second hosted head d67f225:34/35 browser journeys PASS; the remaining local edit/delete journey found a late memory refresh reopening an already-closed dialog. A panel-generation guard now invalidates pending panel results on close/navigation, while keeping the completed backend mutation and current conversation results. New-conversation loading also blocks premature sends and always releases its loading state on failure. Existing failing test is retained as the regression; final exact-head run required.

Head96e1d15 had34/35 browser journeys PASS, including the previously failing closed-panel case. The single failure read raw storage immediately after reload before asynchronous locked initialization completed. The preserved legacy-cleanup assertion now waits for its actual storage outcome; the Pages test helper also waits until storage-backed input is ready. The Pages model/cleanup code was unchanged from the prior run where that case passed. No body/cleanup assertion was removed.

## Scope checkpoint and final gate

R08–R12 are implemented on the review branch with separate local and built-Pages behavior coverage. Actual screenshots from hosted Chromium were inspected for desktop Markdown/code/table reading and both narrow surfaces; no horizontal overflow, readable layout and persistent environment identity were observed. Synthetic UI fixtures are display-only, not generated model/effectiveness evidence. Body/control colors follow adopted tokens; primary controls provide44px targets. Source-derived draft deletion, keyboard/IME, interrupted operations, narrowed viewport,200% zoom and reduced-motion are covered by actual browser assertions.

P1-01 checkpoint is complete pending one consolidated final exact-head35-browser/root/Python/build/bundle pass and exact-main verification; P1-02 does not start until these adoption gates pass. Final run links/results are on PR9. No production/privacy/efficacy or R13–R20 claim.
