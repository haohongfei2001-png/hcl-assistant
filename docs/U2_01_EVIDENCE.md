# U2-01 consumer journey acceptance

Reviewed source: `0f69943863b3046177dd148b8a38abad59f62da7` in [PR26](https://github.com/haohongfei2001-png/hcl-assistant/pull/26). Both jobs passed in [run36930491847](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36930491847). The final head additionally corrects the desktop entry canvas width and captures settled CSS transitions; exact-head and exact-main checks remain required for adoption.

## Verified behavior

- U07: actual 390px login and first-message captures were inspected. Entry follows the adopted colors/surfaces, primary controls fit, the password input has an exact accessible name, and its explicit show/hide control works. The desktop connection-retry capture exposed the generic main element's inherited width; the final CSS removes that limit for the entry canvas only
- U08: a503 initial account-status response has explicit connection recovery. A real held sign-in response times out, clears the password, keeps the email and never automatically repeats the submission; a deliberate second login works. Existing automatic renewal and fixed-lifetime tests remain intact
- U09: a phone browser sends its first message without opening Settings. Before inline consent, both Send and Enter dispatch zero events and keep the draft; after consent exactly one event completes. Member HCL sample controls are in existing Advanced settings. Owner controls and server synthetic-use checks remain unchanged
- U10: reported model unavailability leaves the draft editable, disables Send/Enter and produces zero member mutations. Attachment submission and the explicit sample share the displayed availability/consent gate; the server still owns all authorization and paid admission

The cloud gate passed78 tests on disposable Postgres with no skips and25 browser journeys covering owner, guest and member paths. The broad gate passed the complete Python, TypeScript, both Vite builds,24 JavaScript tests and76 browser regressions. Local Python discovery ran351 tests,311 passed with40 database-dependent cases deferred to the real Postgres gate. Independent source review found no auth/tenant/budget weakening and prompted the explicit password label correction.

The prior screenshots established concrete gaps: bare account controls unlike the adopted chat and a first-send consent hidden inside Settings. Source review also found an unbounded login/register request and no manual recovery after an initial status outage. No failed browser assertion was removed or weakened. The package-count assertion was updated from8 to9 to validate the newly authorized canonical package, while the historical11 packages and all L3 assertions remain unchanged.

## Live status remains separate

No live Auth/email settings, account, entitlement, key, model call or guest window is activated. Public registration delivery, password recovery, billing and real-private-data use remain incomplete capabilities. Passing these injected-provider journeys does not establish a live consumer-ready service.
