# P0-01 implementation evidence

Baseline: product main `7d36a78d4f6ab327109064cb47a371751eef662c`; implementation claim [PR8](https://github.com/haohongfei2001-png/hcl-assistant/pull/8). Synthetic fixtures are newly authored for this package, not research/evaluation sources. This is bounded product behavior evidence, not language understanding, efficacy or production privacy.

## Original failure reproduction

The original Pages JavaScript was executed in Node VM with a minimal DOM and storage test double before editing. This is **not browser evidence**. It reproduced:

- F01: `ORIGINAL_SYNTHETIC_TEMP_CANARY` occurred in persistent localStorage after TEMPORARY input
- F02: the same body remained after DELETE, including its original input/run copies
- F03: original upload handler explicitly used `text.slice(0,1800)`; full browser file behavior was not yet run on baseline
- F04: `这不是我要的问题` superseded the earlier independent synthetic deadline record
- F05: a fresh relationship question produced basis labels claiming current conflict/history without reading records

Failures are preserved here rather than converted into prior PASS claims.

## Implemented scope, verification pending

Current queue checker/report/advance use product_development, reject multiple ready states, unknown/changed dependencies, acceptance drift and document mirrors, and keep the original 11-package and four L3 assertions. Advance preserves canonical documents, runtime metadata and legacy history rather than overwriting them with the old plan.

Pages now uses a browser-only synthetic Controller module. Only exact demo arithmetic, explicit `记录：…`, exact-ID `更正 record-ID：…`, file registration and `演示：查看当前背景` are supported. Open questions and ambiguous targets are unsupported; no keyword-generated relationship/motive answer or unrecorded basis is manufactured.

Temporary conversations are excluded from every storage projection. Stop-use excludes future selection. Delete removes source body and transitively dependent runs/inputs/answers/revision copies plus derived titles; independent sources remain. v1 migration removes the incorrectly retained temporary/deleted copies and marks old untargeted records unparsed. Legacy generated answers remain historical and unverified where no deletion was requested.

UTF-8 TXT/Markdown up to 64 KiB is retained completely with byte counts; invalid UTF-8, binary NUL, unknown formats and oversize files fail explicitly. File contents cannot invoke correction commands. Explain resolves only exact actually-read record IDs/versions.

## Test surfaces

- Local Node model contract tests: temporary/persistent separation, delete/stop/reload/export lineage, 64 KiB boundary and full contents, file refusal, negation/ambiguous/exact correction, basis, cross-conversation isolation, v1 migration, and storage failure
- Existing and additional Python queue tests, historical Controller/SQLite and development bridge regressions remain required
- Hosted Playwright includes the original 12 local-product journeys plus separate Pages storage/reload/file/correction/basis/IME journeys
- Root checks, build, pinned development smoke, exact-head CI and exact-main CI remain required before package adoption

Local browser launch is not used in this environment; hosted CI is the actual browser verification path. No result is inferred from a screenshot or from the local backend to the Pages surface. See PR8 for exact commit/run links and actual results.

## Verification iteration retained

- Initial implementation `eb101635aa6c334b998e5030bf82a196dc6b1b64`: [CI36779184997](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36779184997) PASS, 151 Python tests/build/development smoke and 18 browser journeys. Independent review subsequently found stale-tab resurrection and residual-v1-storage risks; this initial pass was not accepted as closure.
- Storage serialization revision `432f623fe102591bb9b8b40754fc0006af722e20`: [CI36779632366](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36779632366) FAIL, 15 browser journeys passed and 5 Pages journeys failed; root/Python/build/smoke passed. Async save completion could clear a newer draft; tests also failed to wait for accepted saves. No failed test was removed or weakened. Fixes bind draft clearance to the submitted value, keep send disabled during saving, explicitly await save completion, and add a delayed-lock newer-draft/repeated-send regression.

Web Locks serialize browser storage writes; persisted revision checks reject stale copies. Cross-tab changes refresh visible records and dismiss cached panels while preserving unsent drafts and temporary in-memory conversations. Browsers without Web Locks fail explicitly without unsafe writes. Remaining exact-head/full browser verification is pending.

- Draft-race revision `cdf6550dc8be6191a8aeea3e3510b56c45081e84`: [CI36780312494](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36780312494) had 20 browser journeys PASS, including two-tab delete/stop and storage failure; only the new delayed-lock fixture failed because its release callback was invoked before lock acquisition. The fixture now creates its gate before acquisition and explicitly waits for the lock-entered signal; assertions are unchanged. Full final exact-head remains required.

## Verified implementation checkpoint

Exact `c3d35cff66ecbac39010ba0ad416d7c63146e871`: [hosted CI36780754470](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36780754470), Ubuntu24.04/headless Chromium. Root planning and repository-boundary checks PASS; 151 Python tests PASS (including 13 Node model contracts); TypeScript/Vite build PASS; all 21 browser journeys PASS (12 historical local product/development runtime, 9 separate Pages journeys). Original synthetic development smoke PASS: NO_TREATMENT / EXECUTED / NO_TREATMENT / UNSUPPORTED. Stable three-file runtime remains `a8229fcf22eccb851c58502a09ae7cecb346faf5`, digest `sha256:ced40fea69e33b4a817a288cb2eb6e59a12915039ad08699923474902c8956d0`.

R01: strict current queue, mirrors/phase/acceptance/dependencies and legacy safety checked. R02: Pages temporary raw/derived storage and reload tested separately from local process memory. R03: stop/delete/reload/export model lineage plus actual two-tab browser propagation, quota failure and migration cleanup. R04: original long Unicode file head/tail/full bytes, exact64KiB model boundary, invalid UTF-8/oversize refusal. R05: ordinary negation, ambiguous/unknown/cross-conversation target refusal and exact-record correction without unrelated changes. R06: no invented relationship/history basis; explicit background selection binds actual IDs/versions. R07: separate Pages/local browser suites plus original experimental smoke.

These results prove only bounded synthetic contracts. Open natural language remains unsupported; no general semantic capability, model answer, production data/privacy, efficacy, Judge or agent execution is certified. Independent review/final metadata-head/main adoption results are recorded on PR8; a checkpoint PASS is not itself merged adoption.

Independent re-review found a remaining hidden DOM copy when another tab had a memory/evidence panel open during deletion. Panel invalidation/close/reset now removes its content rather than merely hiding the dialog. The two-tab test opens the second tab's memory before deletion and checks complete DOM textContent (including hidden content), not visibility alone. Final revised-head CI is required.

Hidden-panel fix exact `131181fc120f3d9a11a93e00c812973ad87ce4cf`: [CI36781344760](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36781344760) PASS with all21 browser journeys, including full hidden-DOM canary removal. Final batch also uses unique storage revision tokens across reset and adds a 14th Node contract regression. P0 queue checkpoint is COMPLETE with next P1-01; final metadata-head and main remain separately verified on PR8 before starting P1.
