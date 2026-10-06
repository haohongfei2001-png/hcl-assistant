# Visual System — Consumer refresh, 2026-10-06

The user requested the supplied minimal consumer reference across the existing HCLA interface. This is the current visual direction for the same [Assistant-first product](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), with the existing [UX contract](UX_SPEC.md). It replaces the former large ice-blue surfaces and decorative scale; it does not change product capabilities or operating authority.

## Shared visual language

Use a cool light-gray canvas, white rounded surfaces, near-black headings, medium-gray supporting text and generous but functional spacing. Keep violet-blue emphasis concentrated around the composer focus and primary action. Navigation, metadata and secondary controls are quiet neutral tones. Do not copy third-party logos, integration claims, microphone controls or promotional capability text from the reference.

The reference image stays outside the public repository. These implementation values are chosen starting points, not measurements claimed to come from its design source:

- Canvas: #F4F5F8; surface: #FFFFFF; secondary surface: #F7F8FA
- Main text: #171923; supporting text: #626875; borders: #E5E7ED
- Focus: #5F58C8; primary action: #615BC9; subdued selected surface: #EEEDF8
- Control/card corners: 12–16px; composer and major panels: 22–28px
- Soft, low-opacity shadows; no blurred text or dominant background illustration

`apps/web/src/consumer.css` supplies shared tokens and the final presentation layer for Web and Pages. `account-entry.css` uses the same tokens for existing account screens. The earlier structural styles remain in place so the refresh retains proven scrolling, selection, modal and responsive behavior.

## Existing surfaces covered

1. Home and conversation: one shared workspace, compact growing composer, existing three supported suggestions, stable long-answer reading and file staging.
2. Navigation and search: recent conversations, current selection, keyboard search, mobile sidebar and recovery messages.
3. Evidence, source and changes: attached desktop detail panel, mobile full-screen detail, readable original text and explicit return to the answer.
4. Memory: current records, corrections, stop-use/delete controls and their real pending/error states.
5. Settings, membership and orders: the same sections and controls, truthful closed purchase/expiry/budget states and existing order reconciliation.
6. Account, registration, recovery and existing advanced views: shared surfaces and forms without changing any authentication, recovery, provider or payment operation.

No new screen, integration, permission or simulated success is introduced as a visual feature. M3-01 remains incomplete until its own commercial acceptance; visual adoption cannot close that package.

## Layout and interaction

Chat stays central. On desktop, a quiet side navigation sits beside a white workspace; the composer is a compact horizontal object. On smaller screens its actions move beneath the input, with no document-wide horizontal scrolling. Textarea growth retains its existing two-to-seven-line behavior. File controls and required consent remain visible and keyboard reachable.

Keep Chinese body text at 16px with comfortable line height; supporting text remains legible. Interactive targets retain at least 44px. Preserve visible keyboard focus, selection contrast, reduced motion, opaque surfaces and forced-colors support. Code and tables may scroll within their own regions. Dialog dismissal, Back/Forward, interrupted requests, drafts, error recovery and reading anchors keep their existing semantics.

Optional companion A/B/off controls stay available. Their original assets and vector content are not rewritten; the visible slot is smaller and less saturated so decoration does not compete with conversation. Decoration never communicates listening, understanding or completion.

## Evidence and adoption

Required evidence is actual browser rendering for desktop and narrow phone Home, focused composer, conversation, source/evidence, settings/memory, login/recovery and closed membership. Retain the full synthetic behavioral regressions, contrast/target measurements and exact-head/main checks. Screenshots are unedited actual application captures; mock/Pages/account fixtures must be labelled as such and never described as working live chat or checkout.

`CONTINUUM-V1-20261001` assets, earlier captures and [original implementation specifications](design/continuum-v1/IMPLEMENTATION_SPEC.md) remain historical provenance and interaction coverage. They are no longer the current color/scale target. Existing tests retaining those names still exercise behavior and accessibility; old-reference comparison artifacts are historical, not proof of fidelity to the new reference.

The refresh is a candidate until independent source/visual review, hosted browser acceptance and exact-main adoption. It authorizes no new provider calls, live grants, payment service, account configuration, private-data use or production activation.
