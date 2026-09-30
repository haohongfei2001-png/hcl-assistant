# Continuum V1 visual and interaction acceptance

These are mandatory implementation exit conditions under **P1-03 / R19–R20**, with R08–R18 regressions. They are not a new feature queue, research evaluation or proof of cognitive efficacy. At specification adoption all V-items are **NOT_IMPLEMENTED / NOT_VERIFIED**. Existing P0/P1-01 evidence is not retrospectively relabeled a V1 visual pass.

## Evidence format

For each item provide: exact implementation commit SHA; surface (local controlled mock or browser-only Pages); browser/version; viewport and device pixel ratio; zoom/text scale; fonts and reduced-motion/transparency settings; synthetic fixture identity/hash; exact interaction steps; expected and observed result; raw screenshot/video/trace paths; and limitations.

At reference size use 1448×1086 CSS pixels, DPR 1. Publish (a) unedited actual browser screenshot, (b) the corresponding unchanged approved image, and (c) side-by-side or overlay comparison with differences identified. Do not put a full-screen reference image behind clickable hotspots and count that as implementation. Do not claim a generated mockup is an actual app screenshot.

File names and synthetic prose may differ for truthful semantics, but record those differences. Masks are narrowly documented for variable text/timestamps only; they may not hide layout, palette, material, typography, focus, state feedback or missing objects. A raw pixel score alone is not acceptance; text legibility and reviewed region-level correspondence are required. Preserve raw failures and previous comparison evidence.

## Required coverage

| ID | Target / reference | Required evidence and pass condition |
|---|---|---|
| V01 | Home, UI-01 | Actual Home screenshot with corresponding header/navigation/prompt/composer/suggestions/surfaces. Plain or quiet frosted background; no scenery; truthful environment notice. |
| V02 | Multi-turn reading, UI-02 | At least 3 user turns and 3 assistant responses in original synthetic fixtures. Include ≥2,000 Chinese characters across long responses, headings, table, code/quote and actual supported attached file bytes. Viewport and full-content captures; no clipping/tiny text/whole-page horizontal overflow. |
| V03 | Answer evidence, UI-02/03 | Open from a specific answer; selected answer remains identifiable, sources reflect the exact recorded versions and current permissions. Show empty/unavailable evidence too. |
| V04 | Source drill-in, UI-03 | Source list → selected excerpt → surrounding original text → back to evidence. Exact highlight/locator, list selection and its scroll preserved; no stacked modal pile. |
| V05 | Revision committed/pending, UI-03 | Correct a specific background. Old/new/affected/pending are distinct; committed change is not called completed reanalysis. Old answer remains historical. |
| V06 | Partial/error/unknown revision | Commit success plus answer failure, partial reevaluation, ambiguous target, unknown attempt and removed source all have truthful states. No fabricated “unchanged” result or automatic mutation retry. |
| V07 | Return to reading, UI-03 | Capture anchor/focus before opening, scroll inside source, return. Same viewport relative-anchor drift ≤2 CSS px after settling; after reflow/resize return to same semantic paragraph. Normal close respects deliberate main-content scrolling; explicit Return restores original trigger. |
| V08 | Responsive/accessibility, UI-01/02/03 | 1448×1086, 1280×800, 1024×768, 390×844 and 320 px width; 200% text/zoom; keyboard/IME, visible focus, touch targets, blur fallback and composited contrast. No three squeezed narrow columns. |
| V09 | Companion candidates, M-01/M-02 | Home and working-state A/B/off captures. Both retained; same optional slot; off leaves no broken spacing or lost status. Silhouette/material remain recognizable; no final selection implied. |
| V10 | Motion continuity and resilience | Actual playable recording or browser trace of Home→conversation, generation without scroll theft, evidence/source/back/return, correction commit→pending→explicit new analysis when supported. Include reduced-motion, interruption/reversal, failed load and draft recovery. No imaginary cognitive stage animation. |

For V02/V10, synthetic scripted text must be plainly identified as test content. Rendering a long answer from a fixture is allowed; falsely claiming that a live general-purpose model understood the file is not. If a runtime cannot perform a requested semantic step, show its truthful limitation rather than fabricating the step for the video.

## Reviewable playback, not storyboards

Publish two replayable journeys at minimum: (1) long conversation → chosen citation → original source → return to the exact answer, including keyboard focus; (2) precise correction → committed-background/pending-analysis display → supported explicit new attempt or truthful unsupported state, retaining old history. A video must show actual clicks/scrolls and the same app build as the screenshots. A set of generated static frames with arrows is not sufficient.

Local and Pages surfaces require separate evidence because their data adapters/boundaries differ. A shared UI build may reuse visual tests, but it cannot reuse one backend's persistence/deletion result as proof of another surface. Existing Python, build, browser, static boundary and pinned development smoke checks remain required; none are replaced by appearance tests.

## Difference register and merge rule

The implementation PR includes a table: reference ID / region / expected appearance or behavior / actual result / severity / cause / fallback / accepted-by / evidence path. “Library default” is not an accepted reason for changing the design. Unsupported functions pictured in the original are recorded semantic substitutions, not hidden failures or new feature authorizations.

All required captures and journeys must be supplied before claiming V1 implemented. A missing capture, unverified browser behavior, unresolved major visual discrepancy or dishonest state is a failed/pending criterion, not a silent PASS. The final companion winner is intentionally not an exit gate; A/B/off support is.

The existing checker validates the current four-package queue and its original acceptance IDs; it does not automatically inspect these new V-items. Review their evidence explicitly, and keep P1-03 incomplete until both its original R17–R20 obligations and the V-items are satisfied. No new queue or weakened assertion is introduced by this document.
