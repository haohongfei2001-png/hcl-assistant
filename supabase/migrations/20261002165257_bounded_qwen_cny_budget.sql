-- Additive schema only. No model grant, member entitlement, trial, key or role is created.
-- Apply only to the existing authorized HCLA database after explicit activation approval.
BEGIN;
SET LOCAL search_path = hcla, pg_catalog;
CREATE TABLE qwen_budget_policy(singleton integer PRIMARY KEY CHECK(singleton=1),policy text NOT NULL);
CREATE TABLE qwen_budget_attempts(
 run_key text NOT NULL,attempt_key text NOT NULL,input_bytes integer NOT NULL,
 reserved_cny numeric NOT NULL CHECK(reserved_cny>=0),
 charged_cny numeric NOT NULL CHECK(charged_cny>=reserved_cny),
 outcome text NOT NULL CHECK(outcome IN ('active','completed','failed','cancelled','unknown')),
 input_tokens bigint,output_tokens bigint,actual_cny numeric,
 PRIMARY KEY(run_key,attempt_key)
);
CREATE TABLE qwen_member_entitlements(
 tenant text NOT NULL,grant_id text NOT NULL,enabled boolean NOT NULL DEFAULT false,
 starts_at timestamptz NOT NULL,expires_at timestamptz NOT NULL,
 temporary_enabled boolean NOT NULL DEFAULT false,persistent_enabled boolean NOT NULL DEFAULT false,
 max_requests integer NOT NULL CHECK(max_requests>0),max_cost_cny numeric NOT NULL CHECK(max_cost_cny>0),
 PRIMARY KEY(tenant,grant_id),CHECK(tenant ~ '^member-[0-9a-f]{64}$'),CHECK(expires_at>starts_at)
);
CREATE TABLE qwen_member_budget_attempts(
 tenant text NOT NULL,grant_id text NOT NULL,run_key text NOT NULL,attempt_key text NOT NULL,
 charged_cny numeric NOT NULL CHECK(charged_cny>=0),
 outcome text NOT NULL CHECK(outcome IN ('active','completed','failed','cancelled','unknown')),
 PRIMARY KEY(tenant,run_key,attempt_key),
 FOREIGN KEY(tenant,grant_id) REFERENCES qwen_member_entitlements(tenant,grant_id)
);
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['qwen_budget_policy','qwen_budget_attempts'] LOOP
  EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('CREATE POLICY operator_metadata ON hcla.%I TO hcla_app USING(true) WITH CHECK(true)',name);
 END LOOP;
 FOREACH name IN ARRAY ARRAY['qwen_member_entitlements','qwen_member_budget_attempts'] LOOP
  EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('CREATE POLICY isolated_tenant ON hcla.%I TO hcla_app USING(tenant=current_setting(''hcla.tenant'',true) AND tenant ~ ''^member-[0-9a-f]{64}$'') WITH CHECK(tenant=current_setting(''hcla.tenant'',true) AND tenant ~ ''^member-[0-9a-f]{64}$'')',name);
 END LOOP;
END $body$;
REVOKE ALL ON qwen_budget_policy,qwen_budget_attempts,qwen_member_entitlements,qwen_member_budget_attempts FROM PUBLIC;
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN
   EXECUTE format('REVOKE ALL ON qwen_budget_policy,qwen_budget_attempts,qwen_member_entitlements,qwen_member_budget_attempts FROM %I',name);
  END IF;
 END LOOP;
END $body$;
GRANT SELECT ON qwen_budget_policy,qwen_member_entitlements TO hcla_app;
GRANT SELECT,INSERT,UPDATE ON qwen_budget_attempts,qwen_member_budget_attempts TO hcla_app;
-- Database-side admission fence also protects old HCLA binaries. This never
-- changes a legacy row or revokes the shared provider credential. Installing an
-- explicit Qwen policy later closes NEW HCLA USD admissions; settlement remains
-- allowed. With no Qwen policy row, the migration alone does not select Qwen.
CREATE FUNCTION guard_qwen_provider_admission() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, hcla AS $body$
DECLARE target text; held boolean;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_TABLE_NAME <> 'qwen_budget_attempts' AND EXISTS(SELECT 1 FROM hcla.qwen_budget_policy WHERE singleton=1) THEN
  RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='legacy_hcla_provider_admission_closed';
 END IF;
 FOREACH target IN ARRAY ARRAY['budget_attempts','trial_budget_attempts','qwen_budget_attempts'] LOOP
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM hcla.%I WHERE outcome=''active'' AND NOT($1=$2 AND run_key=$3 AND attempt_key=$4))',target)
   INTO held USING TG_TABLE_NAME,target,NEW.run_key,NEW.attempt_key;
  IF held THEN RAISE EXCEPTION USING ERRCODE='P0001', MESSAGE='provider_active_slot_held'; END IF;
 END LOOP;
 RETURN NEW;
END $body$;
REVOKE ALL ON FUNCTION guard_qwen_provider_admission() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guard_qwen_provider_admission() TO hcla_app;
CREATE TRIGGER qwen_admission_fence BEFORE INSERT OR UPDATE OF outcome ON budget_attempts
 FOR EACH ROW WHEN(NEW.outcome='active') EXECUTE FUNCTION guard_qwen_provider_admission();
CREATE TRIGGER qwen_admission_fence BEFORE INSERT OR UPDATE OF outcome ON trial_budget_attempts
 FOR EACH ROW WHEN(NEW.outcome='active') EXECUTE FUNCTION guard_qwen_provider_admission();
CREATE TRIGGER qwen_admission_fence BEFORE INSERT OR UPDATE OF outcome ON qwen_budget_attempts
 FOR EACH ROW WHEN(NEW.outcome='active') EXECUTE FUNCTION guard_qwen_provider_admission();
-- Legacy USD and expired guest-trial policy/attempt rows remain unchanged.
COMMIT;
