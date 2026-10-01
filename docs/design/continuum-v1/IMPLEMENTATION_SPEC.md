# Continuum V1 implementation specification

Applies after the gated adoption in [README](README.md). References are UI-01/02/03 and both M-01/02; these are one product family, not alternative UI strategies. Product architecture and runtime/data boundaries remain Canonical 1.2 / A2-Product.

## 1. Layout and surfaces

Reproduce the reference viewport at 1448 × 1086 CSS pixels, DPR 1 for baseline comparison. This is a QA coordinate system, not a fixed desktop-only app size. Preserve the lightweight left navigation, top search/identity/actions, central reading space, aligned composer and attached right detail surfaces visible in the approved images. Do not turn all content into outlined cards or rebuild the previous gray-green interface.

The Home composition has modest left-aligned prompt text, an optional companion in the adjacent reserved area, a substantial unified composer and low-weight suggestion rows. The conversation uses the same shell and composer: file references belong to the request; the long answer has its own generous reading region; source actions belong to the relevant answer. The evidence/revision state keeps the selected answer visible and uses a connected detail region, not an unrelated centered dialog.

Initial implementation measurements to calibrate against the images: header 56–64 px; navigation approximately 200–240 px on a full desktop; normal answer text approximately 680–760 px; a usable evidence layer approximately 380–440 px. UI-03 can devote more width to the contextual region after reducing navigation. Preserve reference proportions at the baseline viewport rather than forcing these ranges to override the pictures. Readability takes precedence over fitting simultaneous tiny columns; use the explicit responsive rules below and record deviations.

The background is a quiet pale blue/lavender field. No landscape, object, grid spectacle, particles crossing text, moving background or full-page glow. Frosting is confined to appropriate chrome/panel surfaces. Body text and selected source text remain opaque and sharp; never blur text or make the user's scroll move behind highly transparent paragraphs.

### Starting visual tokens

These are implementation starting values inferred from the approved rendered images, not measured original design-file tokens. Calibrate once using corresponding screenshots; the target is the image family, not these approximate values in isolation.

| Role | Initial value |
|---|---|
| Background | `#EDF3FD` |
| Frosted navigation/header | `rgba(230,239,255,0.84)` |
| Reading / composer surface | `rgba(255,255,255,0.94)` |
| Secondary inner surface | `#F1F5FF` |
| Primary text | `#151D43` |
| Secondary text | `#576486` |
| Primary action / active selection edge | `#526BEE` |
| Light selected surface | `#E5ECFF` |
| Dark primary action | `#283047` |
| Decorative soft outline | `#DCE5F8` |
| Focus boundary | `#3958C4`, visible independent of glow |
| Attention / not reevaluated | `#946100` plus explicit text/icon |
| Error | `#AC3547` plus explicit text/icon |

Use the image's blue-violet light behavior only within active controls, panel edges and companion materials. Preserve white highlights and soft depth, not cheap neon. Approximate surface radii: 14–18 px inner objects, 20–24 px reading/detail surfaces, 24–28 px composer. Avoid imposing a generic uniform pill radius on every item. Soft panel elevation may start at `0 12px 36px rgba(70,91,147,0.08)` with a local white inset edge. If blur is unavailable or reduced transparency is requested, use an opaque color-matched fallback and verify it; do not change to a different visual theme.

Chinese sans-serif body 16–17 px / 27–28 px line height; controls 14 px / 20 px; explanatory text at least 12–13 px / 18–20 px; code 14–15 px / 22 px. Use medium weight for hierarchy, not ultralight text. Home headline scale follows UI-01 but must not become promotional typography. Keep source excerpts and tables legible at 100% and text zoom. Icons use one coherent optical weight; illustrations must not substitute for button labels.

The approved first-release reference is light. Do not invent a parallel dark art direction in this package or silently auto-invert the reference. Preserve existing real theme controls honestly; a dark implementation requires color/contrast and corresponding visual evidence in the same material family, not a new exploration. Light-mode delivery is not blocked by an unapproved dark theme.

## 2. Components and page mapping

| Component | Reference and responsibility |
|---|---|
| Shared frame / navigation / header | UI-01/02/03; one shell, visible current conversation/range, search and new chat. Canonical navigation labels replace illustrative platform labels. |
| Exchange / reading surface | UI-02/03; clear user/assistant identity, headings, paragraphs, lists, tables, code and attachments. Retain the latest images' grouping without card nesting. |
| Composer + context references | UI-01/02/03; same object through Home and conversation, draft, attachments, scope, send/stop and failure recovery. |
| File/source reference | UI-02/03; actual name/type/read status/scope, source identity/version. Registered is not understood or used. |
| Answer evidence layer | UI-02/03; opens from the selected answer, readable basis, conditions/gaps, source list. |
| Source detail | UI-03; excerpt highlight and surrounding original context, source/version locator, breadcrumb, back-to-evidence and return-to-answer. |
| Revision receipt | UI-03; old information, new information, affected analysis and not-yet-reevaluated items, tied to actual records. |
| Optional companion slot | M-01/M-02 and UI-01; A/B/off use the same layout contract. Both retained, no final selection. |
| Background / settings / Inspector | Existing UX semantics; inherit V1 spacing, typography and surface treatment. Lab remains a separate advanced environment. |

No new top-level product modules, graph editor, autonomous agent, model marketplace, data connector or parser is introduced by this mapping. All actual input/changes/answers still use existing controlled adapters; decorative view state cannot change product receipts.

## 3. Composer, long reading and file flows

Home and conversation preserve draft identity and selected context during the accepted-input transition. The text area grows to approximately 6–8 lines before internal scrolling. Send and stop occupy a stable position. Chinese composition confirmation must never submit; Enter/Shift+Enter behavior follows the actual setting. Attachments enter a staged list, show reading errors in place and are submitted deliberately; selection alone is not an external send.

A source chip states the current actual scope. Changing defaults for the next conversation never silently changes the present conversation. Drafts, input selection and staged files are isolated per conversation. Failure preserves the recoverable draft and target, and switching conversations cannot attach a completed upload to the wrong target.

Render real Markdown/structured content, not screenshots of text. Long Chinese paragraphs, table cells, code, quotations and link labels wrap correctly. Only wide tables/code have their own horizontal scrolling. No page-wide sideways scroll, permanently tiny text or automatic collapsing of earlier answers. User roles remain unambiguous even where the grouping is visually light.

Only follow streaming output while the user is already following the bottom. When the user reads earlier text, show a restrained new-content affordance instead of scrolling them away. Opening files, evidence or revisions must not resubmit the message or start paid analysis. Mock conversation examples must be original fixtures clearly marked as such, not fake live answers.

## 4. Answer → evidence → source → return

Capture a stable reading anchor before opening: conversation identity, answer/message identity, selected paragraph or source trigger identity, its offset within the viewport, current selection, keyboard focus and detail-stack state. A raw global scrollTop alone is insufficient across reflow.

Expand a contextual evidence region next to the selected answer at a wide viewport. Keep that answer and its selection recognizable. Source selection updates the existing detail region rather than piling modal dialogs. Preserve the evidence list's scroll and selected item when showing the excerpt. Breadcrumb/back reverses one level; Return to answer closes the context view and restores the initiating paragraph/trigger and focus. Escape closes one layer; it must not exit the entire conversation or discard drafts.

At unchanged viewport/zoom, returning to the same anchor should have no perceptible jump: acceptance target ≤2 CSS px relative offset error, measured after layout settles. At a changed viewport or font scale, return to the same semantic paragraph/trigger and keep it visible without fighting a user's deliberate scroll. If the user scrolls the main answer while the detail view is open, a normal close preserves their current position; the explicit Return to answer action restores the recorded trigger position. These are distinct actions.

Bind sources to the answer's actual recorded version. A removed, forbidden or unavailable source produces a truthful unavailable state; do not resurrect cached text. Current permissions apply to historical answers and exports. Empty evidence means no recorded evidence, not a reason to synthesize post-hoc explanations. Important uncertainty stays in the answer, not only in a panel. Explain remains a recorded projection, not hidden chain-of-thought or causal proof of a mechanism's contribution.

## 5. Revision states

Keep at least three independent facts in the view: revision commit status, affected-analysis reevaluation status, and answer completion status. Do not infer any of them from animation completion, a version increment or a button press.

| Actual condition | Visible result |
|---|---|
| Target ambiguous or unsupported | Ask for/select the exact target; do not edit the newest record as a guess. |
| Revision submitting | Local pending state; no success check. |
| Background committed, analyses not reevaluated | “这条背景已更正；相关旧回答尚未重新分析。” |
| Some affected analyses reevaluated | Separate confirmed changed/confirmed retained/pending items; never label pending as unchanged. |
| Commit failed | Original record remains; retain edit value and actionable error. |
| Commit succeeded, answer failed/stopped | “背景已更正；回答未完成。” Do not roll back the committed correction. |
| Result unknown | Show unconfirmed status and recover the recorded attempt; do not blind-retry a mutation. |
| Source removed while viewing | Remove disallowed excerpt/cached copies and state the unavailable scope. |

Correction of an old error, change from now onward, downgrade to a guess and hypothetical branch retain their existing separate meanings. Display old source/new source/actual impact, not a fabricated cognition graph. Original answers remain historical. Explicit reanalysis creates a new run; new evidence must not be inserted as the old answer's original reason.

## 6. Motion contracts

Motion derives from real state transitions and preserves object identity. Numbers below are timing starting points, not an extra forced waiting period. Interrupt and reverse transitions from their current geometry; do not queue obsolete animations.

| Event | Motion and completion boundary |
|---|---|
| Press/send | Immediate 90–120 ms local response; the input becomes an exchange only after acceptance. Keep composer identity/draft recovery. |
| Home → conversation | The composer moves into its conversation position as one surface; existing text stays sharp. No scene/camera animation. |
| Waiting/generation | One localized activity indicator only when work is really pending. New text appears steadily; existing paragraphs do not ripple, blur or float. |
| Add context/file | Local reference enters the composer context region; no file flying into an AI mind or “knowledge absorbed” effect. |
| Evidence/source | Approximately 240–340 ms anchored surface expansion; source replaces the current detail content. The reading anchor is maintained throughout. |
| Revision | Highlight the exact affected record briefly after confirmed commit. Pending reevaluation remains visibly pending after the movement stops. |
| Close/return | Reverse the contextual layer and restore the appropriate anchor/focus; no scroll-to-bottom side effect. |
| Conversation switch | Retain shell geometry; restore that conversation's draft/reading state with a short content transition, not an arbitrary spatial carousel. |

Use restrained ease-out/convergent motion, not repeated elastic bounce. Do not animate Understand/Revise/Judge/Help/Act as stages, invent progress percentages or simulate private reasoning. Reduced-motion mode removes spatial transforms, continuous loops and shape morphs while keeping complete status/focus feedback. No decorative motion while idle in long reading. Low performance must use a documented color-matched static fallback, not a silent design replacement.

## 7. Responsive and accessibility behavior

Full desktop: preserve the approved shell and layered composition. When detail widths would squeeze reading, collapse/reduce navigation first. Around 1024–1279 px, use one evidence/detail stack and selected-source replacement rather than three tiny text columns. At widths below approximately 768 px, navigation becomes a drawer; evidence/source/Inspector become one full-screen detail route with explicit back/return and preserved conversation state. It is the same information path, not a mobile redesign.

Test 1448×1086, 1280×800, 1024×768, 390×844 and 320 px width, plus 200% text/zoom. Support keyboard/safe-area changes without a composer covering the last readable paragraph. Use viewport fitting and actual available width, not device-name assumptions.

All primary functions have visible text or accessible names, normal tab order, visible focus and touch targets approximately 44 px where practicable. Do not require hover, drag or keyboard shortcuts alone. Search is reachable as a visible control as well as an optional shortcut. In a modal mobile detail route, focus is contained and returned; the wider nonmodal evidence layer must not trap focus. Status/live announcements are concise and incremental, not the whole stream read aloud repeatedly.

Verify body contrast ≥4.5:1 and necessary control/focus contrast ≥3:1 in actual composited surfaces, including hover/disabled/error/selection and the blur fallback. Do not rely on color alone for changes, source types, successful commits or pending analyses.

## 8. Companion implementation, both retained

Retain M-01's floating core/asymmetric enclosure and M-02's receiver aperture/container form, materials and silhouette. Do not replace either with a stock AI ball, a human/animal face, or a new illustration. The original board is not a cutout asset: a production-ready extraction/reconstruction must be identified as a derivative, retain provenance and pass visual comparison without overwriting the original sheet.

Implement a shared optional slot with A/B/off review controls; selected final brand identity remains unset. On Home, its bounded area follows UI-01. In working conversation, use a small identity element or omit it; it cannot cover text, shift the composer or demand continuous attention. Presence and actual task-status feedback are separate. Both variants must work with reduced motion and a static fallback. Neither microphone use nor background analysis is implied by “listening” poses. The common UI's development does not depend on choosing between these variants.

## 9. Deviation control

If the reference cannot be faithfully reproduced, record reference ID, region, expected result, actual result, reason, user impact, proposed fallback and review disposition. Large layout/color/material substitutions remain unresolved until explicitly reviewed; never silently rebaseline the design with implementation screenshots. Correcting fake sample text and disabled capabilities is required, but must preserve the rest of the visual target.
