-- Disabled application feature; apply separately with account activation.
BEGIN;
SET LOCAL search_path = hcla, pg_catalog;
CREATE SEQUENCE member_auth_order;
REVOKE ALL ON SEQUENCE member_auth_order FROM PUBLIC;
GRANT USAGE ON SEQUENCE member_auth_order TO hcla_app;
ALTER TABLE member_sessions ADD COLUMN auth_generation bigint NOT NULL DEFAULT 0 CHECK(auth_generation>=0);
CREATE TABLE member_auth_generations(
 tenant text PRIMARY KEY CHECK(tenant ~ '^member-[0-9a-f]{64}$'),
 generation bigint NOT NULL CHECK(generation>=0),
 terminal_ticket bigint NOT NULL CHECK(terminal_ticket>=0),
 reset_pending boolean NOT NULL DEFAULT false, reset_owner text,
 reset_phase text NOT NULL DEFAULT 'idle' CHECK(reset_phase IN ('idle','updating','uncertain')),
 uncertainty_ticket bigint NOT NULL DEFAULT 0 CHECK(uncertainty_ticket>=0),
 CHECK(reset_pending=(reset_phase<>'idle')),
 CHECK(reset_owner IS NULL OR reset_owner ~ '^[0-9a-f]{64}$')
);
ALTER TABLE member_auth_generations ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_auth_generations FORCE ROW LEVEL SECURITY;
CREATE POLICY member_generation_tenant ON member_auth_generations TO hcla_app
 USING(tenant=current_setting('hcla.tenant',true))
 WITH CHECK(tenant=current_setting('hcla.tenant',true));
CREATE FUNCTION prevent_auth_generation_rewind() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER AS $body$
BEGIN
 IF NEW.generation<OLD.generation OR NEW.terminal_ticket<OLD.terminal_ticket THEN
  RAISE EXCEPTION 'Authentication generation cannot decrease';
 END IF;
 RETURN NEW;
END $body$;
REVOKE ALL ON FUNCTION prevent_auth_generation_rewind() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION prevent_auth_generation_rewind() TO hcla_app;
CREATE TRIGGER auth_generation_monotonic BEFORE UPDATE ON member_auth_generations
 FOR EACH ROW EXECUTE FUNCTION prevent_auth_generation_rewind();
CREATE TABLE member_recovery(
 request_key text PRIMARY KEY CHECK(request_key ~ '^[0-9a-f]{64}$'),
 identity_key text NOT NULL CHECK(identity_key ~ '^[0-9a-f]{64}$'),
 issuer text NOT NULL, auth_epoch text NOT NULL, start_ticket bigint NOT NULL CHECK(start_ticket>0),
 expires_at timestamptz NOT NULL, phase text NOT NULL CHECK(phase IN ('requested','exchanging','ready','updating','used','uncertain')),
 secret_ciphertext text, tenant text, subject uuid, access_expires_at timestamptz,
 operation_key text, reset_generation bigint, bound_generation bigint, attempts integer NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 3),
 outcome text CHECK(outcome IN ('updated','rejected','uncertain')),
 CHECK(tenant IS NULL OR tenant ~ '^member-[0-9a-f]{64}$')
);
CREATE INDEX member_recovery_expiry ON member_recovery(expires_at);
ALTER TABLE member_recovery ENABLE ROW LEVEL SECURITY;
ALTER TABLE member_recovery FORCE ROW LEVEL SECURITY;
CREATE POLICY recovery_read ON member_recovery FOR SELECT TO hcla_app
 USING(request_key=current_setting('hcla.recovery_session',true)
  OR (current_setting('hcla.recovery_gc',true)='on' AND expires_at<=clock_timestamp()));
CREATE POLICY recovery_insert ON member_recovery FOR INSERT TO hcla_app
 WITH CHECK(request_key=current_setting('hcla.recovery_session',true) AND tenant IS NULL);
CREATE POLICY recovery_update ON member_recovery FOR UPDATE TO hcla_app
 USING(request_key=current_setting('hcla.recovery_session',true))
 WITH CHECK(request_key=current_setting('hcla.recovery_session',true)
  AND (tenant IS NULL OR tenant=current_setting('hcla.tenant',true)));
CREATE POLICY recovery_delete ON member_recovery FOR DELETE TO hcla_app
 USING(phase<>'updating' AND (request_key=current_setting('hcla.recovery_session',true)
  OR (current_setting('hcla.recovery_gc',true)='on' AND expires_at<=clock_timestamp())));
REVOKE ALL ON member_auth_generations,member_recovery FROM PUBLIC;
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN
   EXECUTE format('REVOKE ALL ON hcla.member_auth_generations,hcla.member_recovery FROM %I',name);
   EXECUTE format('REVOKE ALL ON SEQUENCE hcla.member_auth_order FROM %I',name);
   EXECUTE format('REVOKE ALL ON FUNCTION hcla.prevent_auth_generation_rewind() FROM %I',name);
  END IF;
 END LOOP;
END $body$;
GRANT SELECT,INSERT,UPDATE ON member_auth_generations TO hcla_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON member_recovery TO hcla_app;
COMMIT;
