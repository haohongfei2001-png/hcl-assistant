# Visual System — Canonical A2 / Clear Glass

Product architecture remains [Master Plan 1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)
and interaction semantics remain [UX](UX_SPEC.md). The owner accepted the actual
white/transparent Home at `d50dbec800389b9e788c42c03e873dbe6dffac69` and authorized
this language across the existing product. The [Home evidence](GLASS_HOME_PROPOSAL.md)
records that acceptance. Full-product implementation is under exact-head review;
passing Home checks alone is not full-product adoption.

## Current appearance

`CLEAR-GLASS-20261006` replaces conflicting Continuum color/surface targets.
Use bright white or transparent backgrounds and inputs, opaque near-black text,
fine purple-blue edges, white rim highlights and restrained soft shadows.
There is no gray page wash or gray inset input. Local light color may establish
transparent depth, but should not tint the whole page. Avoid heavy opaque cards,
large glows, unrelated decoration and promotional-card layouts.

The shared chat remains the center. Home geometry from the accepted capture is
preserved. Its compact glass composer extends to conversation with actual
attachment, Send and Stop controls. The input starts at one line and grows to
seven; long drafts scroll inside it. Preserve composition, Enter/Shift+Enter,
file staging, consent, account gates and independent drafts.

Conversation, sidebar/search, evidence/source/revision, memory, settings,
account/membership/login/recovery and the read-only inspector use this same
material. Detail layers keep source navigation, selected-answer association,
reading anchors and explicit return actions. On narrow screens the sidebar
collapses and detail layers use the full screen. A long dialog keeps its Close
control reachable while its content scrolls. Tables/code scroll locally rather
than widening the page or reducing body text.

## Readability and states

Reference implementation colors are primary text `#292A35` / `#34343E`, secondary
text `#585B68`, placeholder `#60616E`, and focus `#6257AA`. These are implementation
values, not measurements extracted from the supplied image. Surfaces are white
with alpha where supported. Inputs and account cards use thin light rims;
primary actions use local lavender light with dark readable labels.

Keep body text readable and fully opaque. Do not blur text or hide notices in
low contrast. At least 44px hit targets, visible keyboard focus, semantic labels,
normal selection/copy, Chinese IME, reduced motion, white opaque fallback and
system forced colors are required. Small checkbox visuals retain a 44px label
hit area. Failure, uncertainty, redaction, expiry and unavailable states remain
explicit; their semantic feedback is not replaced with a decorative success.

## Original references and capability boundaries

The original five Continuum image payloads, their hashes and historical adoption
receipts remain immutable in [the design archive](design/continuum-v1/README.md).
They remain history and behavioral context, not a competing current palette.
Conversation-answer companion A/B/off preferences are retained; Home has no orb.
Decorative forms do not imply listening, understanding or successful processing.

No visual request grants a new capability, opens an account, enables commerce,
changes budget/rights or activates a model. Synthetic/demo state, privacy notices,
member/owner route separation, server-owned admission, research isolation and
source truth remain authoritative. Do not add reference-image logos, microphone
or external integrations without real implemented and authorized functionality.

## Verification and adoption

Run existing planning/repository, build, Node, Python, actual PostgreSQL and
browser gates at the final head. Retain unchanged contrast thresholds (4.5 for
normal text, 3 for disabled controls) and 44px target checks. A conservative
composited-color calculation complements actual unedited pixels; neither replaces
the other. Do not mask screenshots or inject presentation-only CSS to pass.

Required current-head captures include Home default/focus/draft/fallback at
1440 and 390; conversation; desktop and narrow sidebar/search; populated memory;
settings including its scrolled Close control; evidence/source/revision and
return; account/login/register/recovery and membership/orders; empty, failure,
uncertain and expired states. Existing 320px, doubled-text, long-reading and
interrupted/repeated-flow tests remain in force. All fixtures remain synthetic.

Source review and actual pixel review precede merge. Verify exact main and the
existing deployment afterward. The owner's accepted direction authorizes routine
consistent implementation without repeated style confirmations; it does not
waive factual verification or authorize new live services.
