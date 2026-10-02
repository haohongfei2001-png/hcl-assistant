# Ordinary entry and membership expiry

This bounded consumer-account follow-on keeps the adopted shared Assistant UI.
The public cloud root now shows ordinary accounts even while live Auth remains
closed. Maintenance login is explicitly at `/admin`; an existing owner session
never implicitly selects owner chat at `/`. The hosting rewrite preserves direct
navigation and reload. Local development-token and static mock entries retain
their existing behavior.

Registration, verified identity, paid membership and model availability remain
separate gates. The entry explains that registration does not create a membership
and online membership purchase is not open. No price, checkout, trial, free grant,
live identity, Auth setting, email service or credential is created by this slice.

For a server-reported paid membership, Settings displays its current state and
own expiry date in Beijing time. The existing authenticated account-status response
is the source; payment metadata and other users are never exposed. A known grant
expiry disables Send, Enter and the advanced sample while a status read is pending,
without logging out the member or discarding the current draft/history. Client
clock/date presentation cannot grant access: the existing server/DB rechecks of
session, membership, expiry, revocation and shared atomic budget remain mandatory.
The client does not extend expiry or retry a request automatically.

## Verification scope

- Added controlled Node lifecycle checks for expired membership and active
  membership with an unavailable model.
- Added browser journeys for closed ordinary entry, explicit admin navigation,
  reload/Back/Forward, owner-authenticated status on the ordinary route, email
  confirmation without auto-login, unpaid status/shared budget, and expiry during
  a delayed status response while retaining the draft.
- Updated existing owner-browser fixtures to enter `/admin` explicitly.
- Added disposable-Postgres tests proving registration/status create no CNY
  entitlement or provider attempt, and expiry preserves identity but denies use.
- Local TypeScript/build, 44 Node checks and Python discovery passed: 438 collected,
  355 passed and 83 Postgres-dependent skips. Local Chromium launch was blocked by
  the execution environment's local socket policy, including an approved retry;
  those browser checks are unverified locally, not test passes.
- Hosted exact-head Postgres/browser checks and independent review are required
  before adoption; final exact-main checks remain required after merge.

Synthetic fixtures only. No live provider/Auth calls, payment integration, public
signup delivery, real private-data permission or production HCL activation was
verified or enabled. Shared CNY500 policy and immutable accounting are unchanged.
