-- Standing CNY500/month authorization is installed separately by the operator.
-- This migration creates no grant, key, public access or paid request.
BEGIN;
SET LOCAL search_path=hcla,pg_catalog;
CREATE TABLE qwen_monthly_authorization(
 singleton integer PRIMARY KEY CHECK(singleton=1), policy text NOT NULL,
 enabled boolean NOT NULL DEFAULT false,
 CHECK((policy::jsonb->>'provider')='qwen'),CHECK((policy::jsonb->>'model')='qwen3.8-max'),
 CHECK((policy::jsonb->>'region')='cn-beijing'),CHECK((policy::jsonb->>'currency')='CNY'),
 CHECK((policy::jsonb->'monthly'->>'timezone')='Asia/Shanghai'),
 CHECK((policy::jsonb->'monthly'->>'scope')='OWNER_ONLY'),
 CHECK((policy::jsonb->'monthly'->>'limit_cny')='500'),
 CHECK((policy::jsonb->>'max_cost_cny')::numeric=500)
);
CREATE TABLE qwen_monthly_periods(
 period_key text PRIMARY KEY CHECK(period_key ~ '^[0-9]{4}-[0-9]{2}$'),
 policy text NOT NULL DEFAULT '',starts_at timestamptz,ends_at timestamptz,
 max_cost_cny numeric NOT NULL DEFAULT 500 CHECK(max_cost_cny=500),
 CHECK(starts_at<ends_at)
);
CREATE TABLE qwen_monthly_attempts(
 run_key text NOT NULL CHECK(run_key ~ '^[0-9a-f]{64}$'),
 attempt_key text NOT NULL CHECK(attempt_key ~ '^[0-9a-f]{64}$'),
 period_key text NOT NULL REFERENCES qwen_monthly_periods(period_key),
 input_bytes integer NOT NULL CHECK(input_bytes BETWEEN 1 AND 8192),
 output_cap integer NOT NULL CHECK(output_cap BETWEEN 1 AND 131072),
 kind text NOT NULL CHECK(kind IN('SMOKE','OWNER')),
 execution_run_id text NOT NULL,execution_owner text NOT NULL,
 reserved_cny numeric NOT NULL CHECK(reserved_cny>0),charged_cny numeric NOT NULL CHECK(charged_cny>=0),
 outcome text NOT NULL CHECK(outcome IN('active','completed','failed','cancelled','unknown')),
 input_tokens bigint,output_tokens bigint,actual_cny numeric,
 settled boolean NOT NULL DEFAULT false,
 PRIMARY KEY(run_key,attempt_key),
 CHECK((input_tokens IS NULL)=(output_tokens IS NULL)),
 CHECK(input_tokens IS NULL OR input_tokens BETWEEN 0 AND 1000000000000),
 CHECK(output_tokens IS NULL OR output_tokens BETWEEN 0 AND 1000000000000)
);
CREATE INDEX qwen_monthly_period_attempts ON qwen_monthly_attempts(period_key);
CREATE FUNCTION qwen_monthly_clock() RETURNS timestamptz
 LANGUAGE sql VOLATILE SECURITY INVOKER SET search_path=pg_catalog AS 'SELECT clock_timestamp()';
REVOKE ALL ON FUNCTION qwen_monthly_clock() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION qwen_monthly_clock() TO hcla_app;

CREATE FUNCTION guard_qwen_monthly_authorization() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP='INSERT' AND EXISTS(SELECT 1 FROM hcla.qwen_budget_attempts) THEN
  RAISE EXCEPTION 'existing_oneoff_qwen_requires_separate_reconciliation';
 END IF;
 IF TG_OP='UPDATE' AND NEW.policy IS DISTINCT FROM OLD.policy THEN RAISE EXCEPTION 'monthly_policy_is_immutable'; END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'monthly_authorization_cannot_be_reset'; END IF;
 RETURN NEW;
END $body$;
CREATE TRIGGER immutable_qwen_monthly_authorization BEFORE INSERT OR UPDATE OR DELETE ON qwen_monthly_authorization
 FOR EACH ROW EXECUTE FUNCTION guard_qwen_monthly_authorization();

CREATE FUNCTION guard_qwen_monthly_period() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE a record; local_start timestamp; current_key text;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'monthly_period_is_immutable'; END IF;
 IF current_setting('hcla.tenant',true) IS DISTINCT FROM 'hcla-owner' THEN RAISE EXCEPTION 'monthly_owner_scope_required'; END IF;
 SELECT * INTO a FROM hcla.qwen_monthly_authorization WHERE singleton=1 AND enabled=true;
 IF NOT FOUND THEN RAISE EXCEPTION 'monthly_authorization_required'; END IF;
 local_start=date_trunc('month',hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai');
 current_key=to_char(local_start,'YYYY-MM');
 IF NEW.period_key IS DISTINCT FROM current_key THEN RAISE EXCEPTION 'database_current_month_required'; END IF;
 IF NEW.policy NOT IN('',a.policy) OR NEW.max_cost_cny<>500 THEN RAISE EXCEPTION 'monthly_policy_mismatch'; END IF;
 NEW.policy=a.policy;NEW.starts_at=local_start AT TIME ZONE 'Asia/Shanghai';
 NEW.ends_at=(local_start+interval '1 month') AT TIME ZONE 'Asia/Shanghai';
 RETURN NEW;
END $body$;
CREATE TRIGGER immutable_qwen_monthly_period BEFORE INSERT OR UPDATE OR DELETE ON qwen_monthly_periods
 FOR EACH ROW EXECUTE FUNCTION guard_qwen_monthly_period();

-- The original owner-only deployment has no execution.tenant column. Treat only
-- an ABSENT column as that legacy owner schema; an explicit NULL/member tenant
-- is never owner. SECURITY INVOKER, existing RLS and owner context remain intact.
CREATE FUNCTION guard_qwen_monthly_attempt() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE p record; a record; cfg jsonb; expected numeric; actual numeric; total numeric; attempts bigint; ready boolean;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'monthly_attempt_cannot_be_reset'; END IF;
 IF current_setting('hcla.tenant',true) IS DISTINCT FROM 'hcla-owner' THEN RAISE EXCEPTION 'monthly_owner_scope_required'; END IF;
 SELECT * INTO p FROM hcla.qwen_monthly_periods WHERE period_key=NEW.period_key;
 IF NOT FOUND THEN RAISE EXCEPTION 'monthly_period_required'; END IF;
 cfg=p.policy::jsonb;
 IF TG_OP='INSERT' THEN
  SELECT * INTO a FROM hcla.qwen_monthly_authorization WHERE singleton=1 AND enabled=true;
  IF NOT FOUND OR a.policy IS DISTINCT FROM p.policy THEN RAISE EXCEPTION 'monthly_policy_mismatch'; END IF;
  IF NEW.period_key<>to_char(hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai','YYYY-MM')
    OR hcla.qwen_monthly_clock()+interval '300 seconds'>=p.ends_at THEN RAISE EXCEPTION 'monthly_boundary_pause'; END IF;
  IF NEW.outcome<>'active' OR NEW.settled OR NEW.actual_cny IS NOT NULL OR NEW.input_tokens IS NOT NULL OR NEW.output_tokens IS NOT NULL THEN RAISE EXCEPTION 'fresh_reservation_required'; END IF;
  IF NEW.output_cap>(cfg->>'max_completion_tokens')::integer THEN RAISE EXCEPTION 'monthly_output_cap'; END IF;
  SELECT EXISTS(SELECT 1 FROM hcla.qwen_monthly_attempts WHERE kind='SMOKE' AND outcome='completed' AND settled=true) INTO ready;
  IF (ready AND NEW.kind<>'OWNER') OR (NOT ready AND NEW.kind<>'SMOKE') THEN RAISE EXCEPTION 'verified_smoke_gate'; END IF;
  IF EXISTS(SELECT 1 FROM hcla.budget_attempts WHERE outcome='active')
    OR EXISTS(SELECT 1 FROM hcla.trial_budget_attempts WHERE outcome='active')
    OR EXISTS(SELECT 1 FROM hcla.qwen_budget_attempts WHERE outcome='active')
    OR EXISTS(SELECT 1 FROM hcla.qwen_monthly_attempts WHERE outcome='active') THEN RAISE EXCEPTION 'provider_active_slot_held'; END IF;
  IF NOT EXISTS(SELECT 1 FROM hcla.execution e WHERE e.run_id=NEW.execution_run_id AND e.owner=NEW.execution_owner AND (NOT (to_jsonb(e) ? 'tenant') OR to_jsonb(e)->>'tenant'='hcla-owner') AND e.expires_at>hcla.qwen_monthly_clock() AND NOT e.cancelled AND NOT e.finished) THEN RAISE EXCEPTION 'execution_owner_required'; END IF;
  expected=((cfg->>'input_token_reservation')::numeric*(cfg->>'input_cny_per_million')::numeric+(NEW.output_cap+10)*(cfg->>'output_cny_per_million')::numeric)/1000000;
  IF NEW.reserved_cny<>expected OR NEW.charged_cny<>expected THEN RAISE EXCEPTION 'monthly_reservation_mismatch'; END IF;
  SELECT COALESCE(sum(charged_cny),0),count(*) INTO total,attempts FROM hcla.qwen_monthly_attempts WHERE period_key=NEW.period_key;
  IF total+expected>500 OR attempts>=(cfg->>'max_requests')::bigint THEN RAISE EXCEPTION 'monthly_budget_exhausted'; END IF;
 ELSE
  IF ROW(NEW.run_key,NEW.attempt_key,NEW.period_key,NEW.input_bytes,NEW.output_cap,NEW.kind,NEW.execution_run_id,NEW.execution_owner,NEW.reserved_cny)
   IS DISTINCT FROM ROW(OLD.run_key,OLD.attempt_key,OLD.period_key,OLD.input_bytes,OLD.output_cap,OLD.kind,OLD.execution_run_id,OLD.execution_owner,OLD.reserved_cny) THEN RAISE EXCEPTION 'monthly_attempt_identity_is_immutable'; END IF;
  IF NEW IS NOT DISTINCT FROM OLD THEN RETURN NEW; END IF;
  IF NEW.input_tokens IS NOT NULL THEN actual=(NEW.input_tokens*(cfg->>'input_cny_per_million')::numeric+NEW.output_tokens*(cfg->>'output_cny_per_million')::numeric)/1000000; END IF;
  IF NEW.actual_cny IS DISTINCT FROM actual THEN RAISE EXCEPTION 'monthly_actual_cost_mismatch'; END IF;
  IF OLD.outcome='active' THEN
   IF NEW.outcome='active' OR NEW.settled OR NEW.charged_cny<>greatest(OLD.reserved_cny,COALESCE(actual,0)) THEN RAISE EXCEPTION 'conservative_terminal_settlement_required'; END IF;
  ELSE
   IF OLD.settled OR OLD.outcome<>'completed' OR NEW.outcome<>'completed' OR NOT NEW.settled
    OR ROW(NEW.input_tokens,NEW.output_tokens,NEW.actual_cny) IS DISTINCT FROM ROW(OLD.input_tokens,OLD.output_tokens,OLD.actual_cny)
    OR NEW.input_tokens IS NULL OR NEW.input_tokens<=0 OR NEW.input_tokens>(cfg->>'input_token_reservation')::bigint
    OR NEW.output_tokens<=0 OR NEW.output_tokens>NEW.output_cap+10 OR actual>OLD.reserved_cny OR NEW.charged_cny<>actual
    OR NOT EXISTS(SELECT 1 FROM hcla.execution e WHERE e.run_id=NEW.execution_run_id AND e.owner=NEW.execution_owner AND (NOT (to_jsonb(e) ? 'tenant') OR to_jsonb(e)->>'tenant'='hcla-owner') AND e.expires_at>hcla.qwen_monthly_clock() AND NOT e.cancelled AND NOT e.finished)
   THEN RAISE EXCEPTION 'verified_completed_settlement_required'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $body$;
CREATE TRIGGER bounded_qwen_monthly_attempt BEFORE INSERT OR UPDATE OR DELETE ON qwen_monthly_attempts
 FOR EACH ROW EXECUTE FUNCTION guard_qwen_monthly_attempt();

-- Backwards-compatible database fence: old deployments cannot open a second
-- USD/one-off ledger once the standing monthly authorization is installed.
CREATE OR REPLACE FUNCTION guard_qwen_provider_admission() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE target text; held boolean;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF EXISTS(SELECT 1 FROM hcla.qwen_monthly_authorization WHERE singleton=1) THEN RAISE EXCEPTION 'monthly_hcla_provider_admission_only'; END IF;
 IF TG_TABLE_NAME<>'qwen_budget_attempts' AND EXISTS(SELECT 1 FROM hcla.qwen_budget_policy WHERE singleton=1) THEN RAISE EXCEPTION 'legacy_hcla_provider_admission_closed'; END IF;
 FOREACH target IN ARRAY ARRAY['budget_attempts','trial_budget_attempts','qwen_budget_attempts','qwen_monthly_attempts'] LOOP
  EXECUTE format('SELECT EXISTS(SELECT 1 FROM hcla.%I WHERE outcome=''active'' AND NOT($1=$2 AND run_key=$3 AND attempt_key=$4))',target) INTO held USING TG_TABLE_NAME,target,NEW.run_key,NEW.attempt_key;
  IF held THEN RAISE EXCEPTION 'provider_active_slot_held'; END IF;
 END LOOP;
 RETURN NEW;
END $body$;
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['qwen_monthly_authorization','qwen_monthly_periods','qwen_monthly_attempts'] LOOP
  EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('CREATE POLICY owner_only ON hcla.%I TO hcla_app USING(current_setting(''hcla.tenant'',true)=''hcla-owner'') WITH CHECK(current_setting(''hcla.tenant'',true)=''hcla-owner'')',name);
 END LOOP;
END $body$;
-- Old member-capable binaries must see only the nonsecret standing-policy
-- existence through the existing app role. Periods and spend rows stay owner-only.
DROP POLICY owner_only ON qwen_monthly_authorization;
CREATE POLICY app_policy_metadata ON qwen_monthly_authorization TO hcla_app USING(true) WITH CHECK(false);
REVOKE ALL ON qwen_monthly_authorization,qwen_monthly_periods,qwen_monthly_attempts FROM PUBLIC;
DO $body$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN
   EXECUTE format('REVOKE ALL ON qwen_monthly_authorization,qwen_monthly_periods,qwen_monthly_attempts FROM %I',name);
  END IF;
 END LOOP;
END $body$;
REVOKE ALL ON FUNCTION guard_qwen_monthly_authorization(),guard_qwen_monthly_period(),guard_qwen_monthly_attempt() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guard_qwen_monthly_authorization(),guard_qwen_monthly_period(),guard_qwen_monthly_attempt() TO hcla_app;
GRANT SELECT ON qwen_monthly_authorization TO hcla_app;
GRANT SELECT,INSERT ON qwen_monthly_periods TO hcla_app;
GRANT SELECT,INSERT,UPDATE ON qwen_monthly_attempts TO hcla_app;
COMMIT;
