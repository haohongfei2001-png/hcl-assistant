# U1-01: six-point Continuum chat refinement

## Scope and identity

Owner approved this bounded refinement after reviewing the 2026-10-01 screenshot. Baseline main: `51c9b1025ab0b62e62d6c76811a3a1b33f374cb4`. The final application/test implementation is `4fc086aa097dad7df201794f72453b1f67c99e5d`, tree `e50ba4c20a417efb9bf9a6704b40e9ee0bd5c635`. [Exact implementation CI](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36869816780) passed both `planning` and `cloud-postgres`.

The completion-record commit changes only documentation and the current queue. Its exact-head CI and the merged exact-main CI remain adoption requirements, recorded on [PR #18](https://github.com/haohongfei2001-png/hcl-assistant/pull/18). This implementation checkpoint does not substitute for either gate.

## Delivered U01–U06

| Item | Implementation and observed coverage |
|---|---|
| U01 | Composer starts at two text lines, grows from actual content/wrapping to seven lines, then scrolls internally; width changes recalculate height. Reading/input alignment is narrower. Resting border is neutral; focus uses the existing visible dark-blue focus token and restrained glow. Drafts, IME, Shift+Enter and repeated-submit guards remain intact. |
| U02 | Home copy, companion and composer form a tighter group. The approved companion derivatives and A/B/off controls are unchanged. Accepted conversation removes Home and suggestions, with only a small working identity. |
| U03 | Pages distinguishes new, fully cleared and independently surviving history. Deleted-source titles become neutral historical titles, with no retained deleted body. A completed deletion gives a six-second, dismissible status. Closing a fully cleared history returns to the new view without creating or erasing a conversation. Body-free history remains reopenable/exportable; independently surviving source/run/branch data prevents automatic detachment. |
| U04 | One navigation search remains in the header with Ctrl/Cmd+K, explicit input focus and focus restoration. Conversation scope/background is an on-demand disclosure, clearly separate from per-answer evidence. Attachment requirements appear in the keyboard-accessible picker dialogue and errors; native file selection still stages before deliberate submission. |
| U05 | Three supported actions replace six vague prompts. Mock starts from the supported `2+2` example, stages original synthetic text material, and opens actual scope/environment details. Development mode can prepare a general synthetic planning request. No card sends automatically, fabricates prior history, claims unsupported continuation, or upgrades mock semantics. |
| U06 | Reading and input surfaces are more neutral; cold-blue/lavender material, translucent chrome, companion identity and active blue controls remain. Evidence panels stay opaque throughout entry; no fading text overlaps underlying messages. Heading grouping and mobile subtitle wrapping are corrected, including a matching accessible heading label. |

Deletion/navigation details are behavioral repairs, not cosmetic hiding. Legacy cleanup-title normalization runs inside the existing serialized storage path and optimistic revision checks. No old title/body is used to reconstruct a new one. Independent drafts remain recoverable and source-derived drafts still clear. Repeated clears use distinct transfer events. When a prior Home attachment already exists, both file objects remain with their owners and an explicit filename-bearing notice explains where to return. Closing before a delayed delete acknowledgement and navigating to another conversation are separately tested and fenced.

After viewport changes, the return-to-answer anchor keeps its semantic identity and clamps only the resized viewport offset into view. Unchanged-viewport precision and deliberate user-scroll cancellation remain enforced rather than weakening their assertions.

## Actual verification

### Local execution

- `npm run build`: TypeScript, application/Pages builds, static-bundle boundary check and 24 view tests passed
- `python3 scripts/check_planning.py` and `python3 scripts/check_repository.py`: passed
- `python3 -m unittest discover -s tests`: 289 tests, passed with 13 isolated-Postgres skips
- The 13 Postgres tests ran separately against a disposable loopback database and passed
- `node --test tests/javascript/*.test.js`: all 61 tests passed, including independent STOPPED/UNRESOLVED/branch preservation, title migration and cleared-history retention
- `python3 scripts/smoke_development_bridge.py /tmp/hcla-cloud-runtime`: reviewed pinned provider-free slice passed

Local Chromium could not launch because of the execution environment's process/socket limitation; the separate cloud browser refused loopback access. These attempts are retained as infrastructure failures, not browser passes. Browser acceptance below was actually executed by the hosted exact-SHA workflow.

### Hosted exact implementation

[Run 36869816780](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36869816780), head `4fc086aa097dad7df201794f72453b1f67c99e5d`:

- `planning`: success; 289 Python tests (13 database skips), build/24 Node view tests, 75 local/Pages browser tests passed; the seven cloud-only tests are intentionally skipped in that job
- `cloud-postgres`: success; actual independent Postgres instances and all seven cloud browser journeys passed using an injected offline model transport, never the external model provider
- Existing long reading, evidence/source return, precise revision, delete/stop-use, two-tab privacy, export, interrupted/cancelled flows, 320/390/1024/1280/1448 widths, reduced motion, keyboard and 200% CSS text-enlargement regressions remain
- Eight new browser tests cover compact/growing input, one search, actual keyboard file chooser, true card effects, transient deletion notice, repeated clearing, legacy/partial/failed deletion, staged-file collision and close-before-ack/newer-navigation races

Useful [run artifacts](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36869816780#artifacts): `chat-refinement-captures`, `continuum-local-visual-captures`, `continuum-pages-visual-captures`, `continuum-reference-comparisons`, `continuum-replay-videos`, and `cloud-synthetic-browser-evidence`. Captures retain actual pixels, implementation metadata and computed surface measurements. Finite UI animations settle before screenshots and effective text opacity is asserted as one; replay videos retain real transitions. No original reference payload or snapshot baseline was replaced.

## Review and preserved iterations

Independent source review found and prompted repairs for repeated staged-file transfer, an existing Home-file collision, close-before-delete-ack, and duplicate search. Later review found no remaining concrete blocker in the final application tree.

The initial [run 36867313403](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36867313403) had four browser failures: two search-focus cases, a resized Pages anchor and an export test that still assumed a cleared conversation remained selected. The focus and anchor implementations were fixed; export is disabled without a selected conversation, and the regression explicitly reopens the preserved tombstone before verifying the original deletion canary is absent. These assertions were not removed or weakened.

Independent actual-pixel review found whole-panel opacity causing mobile evidence bleed-through and orphaned Home text. The implementation removed whole-panel opacity fading and grouped the heading/subtitle. [Run 36868698257](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36868698257) then passed 73 browser cases but retained two heading-accessibility-name failures caused by inline-block whitespace. The explicit matching heading label fixed those. The final implementation run passed all 75 cases. Intermediate cancelled work is not acceptance evidence.

Visual review of the repaired captures confirmed readable desktop/narrow/mobile Home, compact working identity, opaque evidence/source layers and explicit cleared-history recovery. Final exact-application review of run 36869816780 confirmed the stronger focused-composer boundary, 1448/390 Home, 320 heading grouping and fully opaque 320 evidence, with no new clipping or spacing regression. Capture metadata matched `4fc086aa097dad7df201794f72453b1f67c99e5d`; no further application change was needed. The review is recorded on PR #18 before merge; documentation-only completion does not change those pixels.

## Limits and stop

This is bounded UI/behavior acceptance, not semantic understanding, native-browser zoom certification, real-provider latency, production privacy or HCL efficacy evidence. The recorded 200% capture is labelled CSS text enlargement; sidebar brand/badge wrapping remains a non-blocking cosmetic limitation. Existing long source previews remain verbose and are outside this six-point scope.

Provider calls: **0**. No accounts, credentials, provider transport/configuration, reviewed Bridge lock, security permissions, original design assets, research mechanism or production-HCL activation changed. L3 remains gated. After U1-01's exact-head/merge/exact-main verification, the sole product queue returns to `STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED`.
