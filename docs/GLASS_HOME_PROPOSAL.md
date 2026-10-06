# Home glass-material proposal

Status: candidate awaiting actual desktop/mobile captures and owner visual
acceptance. The previously proposed full-site color refresh was rejected and
has not been adopted. This proposal starts from main a7b7619718e301d43edfa4a71eeb3fdcfc667b2e.

The owner's two supplied close-ups establish material, not a promotional-card
layout: a milky translucent shell over a cool gray substrate, a fine purple-blue
rim and white inner highlight, recessed input, softly raised circular controls.
The implementation uses the actual Home composer, with attachment and Send;
it adds no microphone, third-party integration, avatar or security claim.
Reference images remain outside this public repository.

Scope is the empty Home screen only. Remove its decorative orb, reduce heavy
chrome, retain real environment/privacy/error information and three supported
actions. Input starts at one text line, grows through seven, and keeps the actual
IME/Enter, draft, attachment, consent, send, stop and disabled-state behavior.
Conversation rendering and account, membership, billing and server logic do not
change. Existing companion selections remain available on conversation answers.

CSS translucency affects surfaces only. Text stays opaque and readable. Buttons
retain at least 44px hit areas; keyboard focus, reduced motion, opaque and forced
color fallbacks remain available. Real synthetic Pages/browser captures at
1440px and 390px, empty and with an unsent draft, are required. Screenshots are
unedited and use no mask or injected presentation CSS. Existing behavior,
contrast and cloud/member admission regressions remain required.

Local browser launch is blocked by the executor's socket restriction; the
existing hosted synthetic browser workflow supplies actual pixel evidence.
No production adoption or extension to other screens follows from passing CI:
owner visual acceptance is still required.
