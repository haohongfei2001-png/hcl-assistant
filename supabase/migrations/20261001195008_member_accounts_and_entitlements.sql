-- Apply separately after account activation approval. No auth users, provider
-- settings, public API rights, credentials or entitlements are created here.
BEGIN;
SET LOCAL search_path = hcla, pg_catalog;
CREATE TABLE member_sessions(
 session_key text PRIMARY KEY, tenant text NOT NULL, issuer text NOT NULL,
 subject uuid NOT NULL, expires_at timestamptz NOT NULL,absolute_expires_at timestamptz NOT NULL,
 refresh_ciphertext text NOT NULL,refresh_state text NOT NULL DEFAULT 'idle' CHECK(refresh_state IN ('idle','inflight')),
 refresh_owner text,refresh_started_at timestamptz,
 CHECK(expires_at<=absolute_expires_at),
 CHECK(tenant ~ '^member-[0-9a-f]{64}$'), CHECK(session_key ~ '^[0-9a-f]{64}$')
);
CREATE INDEX member_sessions_expiry ON member_sessions(expires_at);
ALTER TABLE member_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_sessions FORCE ROW LEVEL SECURITY;
-- Before tenant is known, only the hash of this request's opaque cookie can
-- select its session. Every pooled transaction explicitly resets both settings.
CREATE POLICY member_session_lookup ON member_sessions TO hcla_app
 USING(session_key=current_setting('hcla.member_session',true))
 WITH CHECK(session_key=current_setting('hcla.member_session',true)
            AND tenant=current_setting('hcla.tenant',true));
CREATE TABLE member_login_attempts(identity_key text NOT NULL,attempted_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE INDEX member_login_attempts_time ON member_login_attempts(attempted_at);
ALTER TABLE member_login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_login_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY member_rate_gate ON member_login_attempts TO hcla_app USING(true) WITH CHECK(true);
CREATE TABLE member_entitlements(
 tenant text NOT NULL, grant_id text NOT NULL, enabled boolean NOT NULL DEFAULT false,
 starts_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 temporary_enabled boolean NOT NULL DEFAULT false, persistent_enabled boolean NOT NULL DEFAULT false,
 max_requests integer NOT NULL CHECK(max_requests>0), max_cost_usd numeric NOT NULL CHECK(max_cost_usd>0),
 PRIMARY KEY(tenant,grant_id), CHECK(tenant ~ '^member-[0-9a-f]{64}$'), CHECK(expires_at>starts_at)
);
CREATE TABLE member_budget_attempts(
 tenant text NOT NULL,grant_id text NOT NULL,run_key text NOT NULL,attempt_key text NOT NULL,
 charged_usd numeric NOT NULL CHECK(charged_usd>=0),
 outcome text NOT NULL CHECK(outcome IN ('active','completed','failed','cancelled','unknown')),
 PRIMARY KEY(tenant,run_key,attempt_key),
 FOREIGN KEY(tenant,grant_id) REFERENCES member_entitlements(tenant,grant_id)
);
ALTER TABLE execution ADD COLUMN tenant text NOT NULL DEFAULT 'hcla-owner';
ALTER TABLE temporary_heads ADD COLUMN tenant text NOT NULL DEFAULT 'hcla-owner';
CREATE INDEX execution_tenant_expiry ON execution(tenant,expires_at) WHERE NOT finished;
CREATE INDEX temporary_heads_tenant ON temporary_heads(tenant);
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['accounts','objects','sources','events','idempotency','records','tombstones'] LOOP
  EXECUTE format('DROP POLICY owner_rows ON hcla.%I',name);
 END LOOP;
 FOREACH name IN ARRAY ARRAY['execution','temporary_heads'] LOOP
  EXECUTE format('DROP POLICY owner_metadata ON hcla.%I',name);
 END LOOP;
 FOREACH name IN ARRAY ARRAY['accounts','objects','sources','events','idempotency','records','tombstones','execution','temporary_heads','member_entitlements','member_budget_attempts'] LOOP
  EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('CREATE POLICY isolated_tenant ON hcla.%I TO hcla_app USING(tenant=current_setting(''hcla.tenant'',true) AND (tenant=''hcla-owner'' OR tenant ~ ''^member-[0-9a-f]{64}$'')) WITH CHECK(tenant=current_setting(''hcla.tenant'',true) AND (tenant=''hcla-owner'' OR tenant ~ ''^member-[0-9a-f]{64}$''))',name);
 END LOOP;
END $body$;
REVOKE ALL ON member_sessions,member_login_attempts,member_entitlements,member_budget_attempts FROM PUBLIC;
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN
   EXECUTE format('REVOKE ALL ON member_sessions,member_login_attempts,member_entitlements,member_budget_attempts FROM %I',name);
  END IF;
 END LOOP;
END $body$;
GRANT SELECT,INSERT,UPDATE,DELETE ON member_sessions TO hcla_app;
GRANT SELECT,INSERT,DELETE ON member_login_attempts TO hcla_app;
GRANT SELECT ON member_entitlements TO hcla_app;
GRANT SELECT,INSERT,UPDATE ON member_budget_attempts TO hcla_app;
-- Existing global operator and trial caps remain separate and unchanged.
COMMIT;
