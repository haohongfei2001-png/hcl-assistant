# Bounded ordinary-account password recovery

This is an explicitly disabled engineering slice authorized after the consumer-entry and history-recovery work. It does not open Supabase Auth, send real email, change a real password, install a live migration, add MFA/social login/billing, or activate any model/trial grant.

## Recovery boundary

The exact `HCLA_MEMBER_RECOVERY=pkce` flag and existing member provider are required; the default is off. Future activation also requires the reviewed migration, the fixed callback in the provider redirect allowlist, and verified email delivery. None are performed by this implementation. The email request has a generic, enumeration-safe response and the same opaque-cookie/pending presentation for eligible and ineligible addresses. Throttling is bounded, with no automatic email or password mutation retries. Email is sent only to the configured Auth provider when the feature is separately activated.

PKCE verifiers are generated server-side. A distinct Secure, HttpOnly, SameSite cookie contains only an opaque random value; its hash selects one private FORCE-RLS recovery row. Purpose-separated authenticated encryption binds the verifier/access material to the fixed issuer, hashed email identity, request and original deadline. No password or upstream token is stored in browser storage; completed recovery clears encrypted material. Owner/member/trial cookies cannot substitute for a recovery cookie, and recovery cannot authorize product routes.

The fixed same-origin callback scrubs the one-use code from the URL before application assets, uses no-referrer/no-store policy, and submits the code in a POST body. No client-selected redirect or issuer is accepted. Application logs never record the code, URL, password, verifier, token, email or identity hash. This does not prove that the initial callback query is absent from the hosting provider's access logs; that visibility/retention remains a separate activation consideration. Standard PKCE requires the initiating browser; a wrong-browser link gets an explicit restart path.

## Mutation and session ordering

A recovery code is exchanged at most once and must match that request's unique PKCE verifier. Fixed issuer, canonical UUID and confirmed email identity are checked before a short-lived recovery-only grant is created. Expiry, reuse, cross-session substitution and uncertain exchange fail closed.

A private monotonic database ticket is captured before password-login transport and when the recovery request is created, before email transport. A link requested before or during a later reset cannot become a fresh grant simply by being exchanged afterward. Ready recovery grants also bind the verified tenant generation, so older cookies cannot overwrite a completed reset. Entering the verified password-update phase atomically increments the tenant's authentication generation and sets a recovery-in-progress barrier. Existing sessions, renewal completion and paid dispatch must match the original generation. Login grants begun before or during a reset cannot inherit the new generation: they must have a start ticket newer than the tenant's terminal reset ticket and no pending barrier.

A known password-policy rejection may allow at most three explicit stronger-password attempts within the unchanged recovery deadline; no mutation is automatically repeated. A confirmed terminal result records its ticket and releases the barrier atomically. An uncertain password mutation leaves the barrier pending; there is no timer-based unblock or blind replay. A fresh mailbox proof does not prove an earlier remote write has stopped. Uncertain or orphan-live mutations require authoritative provider reconciliation; this slice has no automated or public override. A second live per-tenant password mutation is refused, including from a distinct valid recovery cookie. Cookie rotation and expiry cleanup preserve in-flight mutation records until their owning worker records a known terminal result. Expiry stops new authority without erasing reconciliation evidence. The UI clearly states that updating the password ends existing app sessions and explains the exceptional locked state after uncertainty.

## Required evidence

- M07: disabled default, fixed provider/callback and generic email responses; no enumeration through pending state
- M08: expiry, one-use exchange, cookie/verifier binding, owner/member/trial separation and pooled-state reset
- M09: encrypted recovery material, purpose/AAD tamper refusal, no URL/body/exception secret leakage
- M10: reset versus login begun before/during/after mutation, refresh fencing and dispatch revocation; uncertain outcomes remain blocked
- M11: phone/desktop request, confirmation, wrong-browser/reused link and new-password error journeys with fake Auth only
- M12: real disposable Postgres, full regression/browser gates and exact-main verification; no live activation inferred

References checked for this slice: [Supabase PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow), [password authentication](https://supabase.com/docs/guides/auth/passwords), [Auth REST specification](https://github.com/supabase/auth/blob/master/openapi.yaml), and [current changelog](https://supabase.com/changelog). The hosted-project flow uses the existing default email template; no template or delivery configuration is changed here.
