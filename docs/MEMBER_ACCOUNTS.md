# M1-01: ordinary accounts without shared-owner access

Authorized 2026-10-01 19:40 UTC. One ordinary-user registration/login slice in the existing Assistant UI. The guest trial remains independent and inactive until its own approved activation. No paid billing, real-private-data permission, production HCL activation or provider call follows from this engineering work.

## Acceptance and boundaries

- M01: separate account registration/login/logout routes and `__Host-hcla-member` opaque Secure/HttpOnly/SameSite cookie. Supabase verifies the exact access token at `/auth/v1/user`; issuer is fixed server configuration, subject is the canonical verified UUID. Email and user-editable metadata never grant identity or rights. Registration requires email confirmation and never logs in from an unverified signup response
- M02: `/v1/member/*` is an explicit product-route allowlist. Member cookies cannot access owner or guest routes. Every pooled transaction resets tenant and session-hash context. Product rows, execution leases/cancellation/recovery, temporary snapshot heads and account accounting are tenant isolated by RLS. Temporary execution keys/signatures also bind the member session
- M03: account entitlements are server-owned, default absent, time bounded and runtime read-only. Per-user admission and the existing global operator cap commit in one database transaction under the same lock. Unknown/failed/cancelled costs retain conservative full reservations. Existing guest trial grants cannot fund member persistent or temporary dispatch; no request/JWT plan field grants capacity
- M04: only an opaque cookie reaches the browser. Upstream refresh material is AES-GCM encrypted server-side with a versioned HKDF key derived from the existing high-entropy application signing key; AAD binds issuer, subject, session hash and immutable absolute deadline. Fresh nonces are required. Verified windows last at most15 minutes and never exceed the upstream token expiry. Automatic renewal has a fixed12-hour absolute limit. A durable fenced refresh lease prevents duplicate rotation; uncertain/crashed refreshes require reauthentication, never blind token reuse. Logout or expiry during refresh prevents commit/resurrection
- M05: provider-free tests cover two users, cross-account IDs and operations, sessions, origin/CSRF, quota races, stale/revoked rights, automatic renewal, logout/refresh races, and delayed frontend responses/export after logout. Browser verification uses injected Auth/provider fixtures and disposable localhost Postgres, never live accounts or models
- M06: exact-head review/CI, merge, exact-main CI and inactive hosted checks are required. A passing synthetic fixture is not evidence that public registration or real email delivery has been enabled

## Revocation contract

Application logout immediately removes its server session and cancels in-flight member dispatch/publication through live session probes. Provider-side logout/revocation is observed at the next upstream renewal; an already verified short application window may remain valid until then, at most15 minutes. We do not claim immediate provider-wide revocation or paid Supabase session-control features. Short windows renew automatically during normal use; a12-hour deadline, explicit logout, ciphertext/key mismatch or uncertain refresh ends the session. New login creates a new opaque session and revokes this browser's prior member session. Account changes/expiry/logout invalidate tab drafts, temporary packets, pending exports and stale async results.

## Separate live activation

The default is disabled. The new migration `20261001195008_member_accounts_and_entitlements.sql` is reviewed/tested here but must not be applied to the live database as an implicit auth activation. It preserves existing owner/trial data and metadata, adds private account tables, and extends tenant RLS; it creates no live users, credentials, entitlements, Auth settings or public API rights.

After separate approval, operators must verify the dedicated Supabase project's email/password/confirmation and delivery configuration and apply the reviewed migration. Server fields are `HCLA_MEMBER_AUTH=supabase`, the exact `HCLA_SUPABASE_AUTH_URL`, and its existing publishable `HCLA_SUPABASE_PUBLISHABLE_KEY`; secret/service-role keys are rejected. No public frontend Supabase client/storage is introduced. Provider keys and the global model authorization remain their existing separate gates. Member entitlements are explicit operator metadata, not self-service billing. No default quota is silently granted on signup.

Supabase's [default mail service](https://supabase.com/docs/guides/auth/auth-smtp) is restricted to project-team recipients and currently two messages/hour. Public email signup therefore requires separately verified mail delivery; code/fixture success does not establish it. This work has not read secret-bearing Auth configuration or enabled a mail provider. Password recovery and paid subscription checkout are not included in M1-01.

Implementation and verification evidence: [M1-01 evidence](M1_01_EVIDENCE.md).

## Primary references

[Supabase identity verification](https://supabase.com/docs/guides/auth/jwts), [session limits and logout caveats](https://supabase.com/docs/guides/auth/sessions), [RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/aead/), [HKDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf). Checked 2026-10-01. The Supabase shared JWT-signing secret is never configured or used; user_metadata never authorizes access.
