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
 CHECK((policy::jsonb->'monthly'->>'scope') IN ('OWNER_ONLY','AUTHENTICATED_SHARED')),
 CHECK((policy::jsonb->'monthly'->>'limit_cny')='500'),
 CHECK((policy::jsonb->>'max_cost_cny')::numeric=500),
 CHECK(((policy::jsonb->'monthly'->>'scope')='OWNER_ONLY' AND (policy::jsonb->>'version')::integer=2) OR ((policy::jsonb->'monthly'->>'scope')='AUTHENTICATED_SHARED' AND (policy::jsonb->>'version')::integer=3))
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
 kind text NOT NULL CHECK(kind IN('SMOKE','OWNER','MEMBER')),
 actor_tenant text NOT NULL DEFAULT 'hcla-owner' CHECK(actor_tenant='hcla-owner' OR actor_tenant ~ '^member-[0-9a-f]{64}$'),
 entitlement_grant_id text, membership_evidence_digest text, membership_verification text, memory_scope text NOT NULL DEFAULT 'CONVERSATION' CHECK(memory_scope IN('TEMPORARY','CONVERSATION','TOPIC')),
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

-- One narrow global aggregate capability: private schema, no row/actor data,
-- no writes, no caller-supplied period. Required because actor RLS must not turn
-- the shared ceiling/active slot/smoke gate into per-actor limits.
CREATE FUNCTION qwen_monthly_shared_state() RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
DECLARE actor text:=current_setting('hcla.tenant',true); period text; shared boolean;
BEGIN
 SELECT policy::jsonb->'monthly'->>'scope'='AUTHENTICATED_SHARED' INTO shared FROM hcla.qwen_monthly_authorization WHERE singleton=1;
 IF actor IS NULL OR (actor<>'hcla-owner' AND (NOT COALESCE(shared,false) OR actor !~ '^member-[0-9a-f]{64}$')) THEN RAISE EXCEPTION 'monthly_actor_scope_required'; END IF;
 period=to_char(hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai','YYYY-MM');
 RETURN (SELECT jsonb_build_object('period',period,
  'charged_cny',COALESCE(sum(charged_cny) FILTER(WHERE period_key=period),0)::text,
  'request_count',count(*) FILTER(WHERE period_key=period),
  'active_requests',count(*) FILTER(WHERE outcome='active'),
  'known_cny',(sum(actual_cny) FILTER(WHERE period_key=period))::text,
  'unknown_usage_requests',count(*) FILTER(WHERE period_key=period AND actual_cny IS NULL),
  'actor_charged_cny',COALESCE(sum(charged_cny) FILTER(WHERE period_key=period AND actor_tenant=actor),0)::text,
  'actor_request_count',count(*) FILTER(WHERE period_key=period AND actor_tenant=actor),
  'smoke_ready',COALESCE(bool_or(kind='SMOKE' AND actor_tenant='hcla-owner' AND outcome='completed' AND settled),false))
  FROM hcla.qwen_monthly_attempts);
END $body$;
REVOKE ALL ON FUNCTION qwen_monthly_shared_state() FROM PUBLIC;
DO $body$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN EXECUTE format('REVOKE ALL ON FUNCTION hcla.qwen_monthly_shared_state() FROM %I',name); END IF;
 END LOOP;
END $body$;
GRANT EXECUTE ON FUNCTION qwen_monthly_shared_state() TO hcla_app;

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
 SELECT * INTO a FROM hcla.qwen_monthly_authorization WHERE singleton=1 AND enabled=true;
 IF NOT FOUND THEN RAISE EXCEPTION 'monthly_authorization_required'; END IF;
 IF current_setting('hcla.tenant',true) IS DISTINCT FROM 'hcla-owner' AND (a.policy::jsonb->'monthly'->>'scope'<>'AUTHENTICATED_SHARED' OR COALESCE(current_setting('hcla.tenant',true),'') !~ '^member-[0-9a-f]{64}$') THEN RAISE EXCEPTION 'monthly_actor_scope_required'; END IF;
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
DECLARE p record; a record; entitlement record; cfg jsonb; state jsonb; expected numeric; actual numeric; total numeric; attempts bigint; ready boolean;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'monthly_attempt_cannot_be_reset'; END IF;
 IF NEW.actor_tenant IS DISTINCT FROM current_setting('hcla.tenant',true) THEN RAISE EXCEPTION 'monthly_actor_scope_required'; END IF;
 SELECT * INTO p FROM hcla.qwen_monthly_periods WHERE period_key=NEW.period_key;
 IF NOT FOUND THEN RAISE EXCEPTION 'monthly_period_required'; END IF;
 cfg=p.policy::jsonb;
 IF NEW.actor_tenant<>'hcla-owner' AND cfg->'monthly'->>'scope'<>'AUTHENTICATED_SHARED' THEN RAISE EXCEPTION 'monthly_owner_scope_required'; END IF;
 IF NEW.actor_tenant='hcla-owner' AND (NEW.entitlement_grant_id IS NOT NULL OR NEW.membership_evidence_digest IS NOT NULL OR NEW.membership_verification IS NOT NULL) THEN RAISE EXCEPTION 'owner_grant_mismatch'; END IF;
 IF NEW.actor_tenant<>'hcla-owner' AND (TG_OP='INSERT' OR NEW.settled) THEN
  IF NOT EXISTS(SELECT 1 FROM hcla.member_sessions ms LEFT JOIN hcla.member_auth_generations g ON g.tenant=ms.tenant
   WHERE ms.session_key=current_setting('hcla.member_session',true) AND ms.tenant=NEW.actor_tenant
    AND ms.expires_at>clock_timestamp() AND ms.absolute_expires_at>clock_timestamp()
    AND (ms.refresh_state='idle' OR ms.refresh_started_at>clock_timestamp()-interval '20 seconds')
    AND ms.auth_generation=COALESCE(g.generation,0) AND NOT COALESCE(g.reset_pending,false)) THEN RAISE EXCEPTION 'member_session_required'; END IF;
 END IF;
 IF TG_OP='INSERT' THEN
  SELECT * INTO a FROM hcla.qwen_monthly_authorization WHERE singleton=1 AND enabled=true;
  IF NOT FOUND OR a.policy IS DISTINCT FROM p.policy THEN RAISE EXCEPTION 'monthly_policy_mismatch'; END IF;
  IF NEW.period_key<>to_char(hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai','YYYY-MM')
    OR hcla.qwen_monthly_clock()+interval '300 seconds'>=p.ends_at THEN RAISE EXCEPTION 'monthly_boundary_pause'; END IF;
  IF NEW.outcome<>'active' OR NEW.settled OR NEW.actual_cny IS NOT NULL OR NEW.input_tokens IS NOT NULL OR NEW.output_tokens IS NOT NULL THEN RAISE EXCEPTION 'fresh_reservation_required'; END IF;
  IF NEW.output_cap>(cfg->>'max_completion_tokens')::integer THEN RAISE EXCEPTION 'monthly_output_cap'; END IF;
  state=hcla.qwen_monthly_shared_state();ready=(state->>'smoke_ready')::boolean;
  IF (NOT ready AND (NEW.kind<>'SMOKE' OR NEW.actor_tenant<>'hcla-owner')) OR (ready AND NEW.kind<>CASE WHEN NEW.actor_tenant='hcla-owner' THEN 'OWNER' ELSE 'MEMBER' END) THEN RAISE EXCEPTION 'verified_smoke_gate'; END IF;
  IF EXISTS(SELECT 1 FROM hcla.budget_attempts WHERE outcome='active')
    OR EXISTS(SELECT 1 FROM hcla.trial_budget_attempts WHERE outcome='active')
    OR EXISTS(SELECT 1 FROM hcla.qwen_budget_attempts WHERE outcome='active')
    OR (state->>'active_requests')::bigint>0 THEN RAISE EXCEPTION 'provider_active_slot_held'; END IF;
  IF NOT EXISTS(SELECT 1 FROM hcla.execution e WHERE e.run_id=NEW.execution_run_id AND e.owner=NEW.execution_owner AND ((NEW.actor_tenant='hcla-owner' AND NOT (to_jsonb(e) ? 'tenant')) OR to_jsonb(e)->>'tenant'=NEW.actor_tenant) AND e.expires_at>hcla.qwen_monthly_clock() AND NOT e.cancelled AND NOT e.finished) THEN RAISE EXCEPTION 'execution_owner_required'; END IF;
  expected=((cfg->>'input_token_reservation')::numeric*(cfg->>'input_cny_per_million')::numeric+(NEW.output_cap+10)*(cfg->>'output_cny_per_million')::numeric)/1000000;
  IF NEW.reserved_cny<>expected OR NEW.charged_cny<>expected THEN RAISE EXCEPTION 'monthly_reservation_mismatch'; END IF;
  total=(state->>'charged_cny')::numeric;attempts=(state->>'request_count')::bigint;
  IF total+expected>500 OR attempts>=(cfg->>'max_requests')::bigint THEN RAISE EXCEPTION 'monthly_budget_exhausted'; END IF;
  IF NEW.actor_tenant<>'hcla-owner' THEN
   SELECT * INTO entitlement FROM hcla.qwen_member_entitlements WHERE tenant=NEW.actor_tenant AND grant_id=NEW.entitlement_grant_id AND enabled AND paid_membership AND payment_verification IN('ADMIN_VERIFIED','TRUSTED_PAYMENT_EVENT') AND paid_evidence_digest IS NOT NULL AND paid_verified_at IS NOT NULL AND paid_verified_at<=clock_timestamp() AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND CASE WHEN NEW.memory_scope='TEMPORARY' THEN temporary_enabled ELSE persistent_enabled END;
   IF NOT FOUND OR (SELECT count(*) FROM hcla.qwen_member_entitlements WHERE tenant=NEW.actor_tenant AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp())<>1 THEN RAISE EXCEPTION 'member_entitlement_required'; END IF;
   IF (NEW.membership_evidence_digest IS NOT NULL AND NEW.membership_evidence_digest IS DISTINCT FROM entitlement.paid_evidence_digest) OR (NEW.membership_verification IS NOT NULL AND NEW.membership_verification IS DISTINCT FROM entitlement.payment_verification) THEN RAISE EXCEPTION 'paid_membership_evidence_mismatch'; END IF;
   NEW.membership_evidence_digest=entitlement.paid_evidence_digest;NEW.membership_verification=entitlement.payment_verification;
   SELECT COALESCE(sum(charged_cny),0),count(*) INTO total,attempts FROM hcla.qwen_monthly_attempts WHERE actor_tenant=NEW.actor_tenant AND entitlement_grant_id=NEW.entitlement_grant_id AND period_key=NEW.period_key;
   IF total+expected>entitlement.max_cost_cny OR attempts>=entitlement.max_requests THEN RAISE EXCEPTION 'member_subcap_exhausted'; END IF;
  END IF;
 ELSE
  IF ROW(NEW.run_key,NEW.attempt_key,NEW.period_key,NEW.input_bytes,NEW.output_cap,NEW.kind,NEW.execution_run_id,NEW.execution_owner,NEW.reserved_cny,NEW.actor_tenant,NEW.entitlement_grant_id,NEW.memory_scope,NEW.membership_evidence_digest,NEW.membership_verification)
   IS DISTINCT FROM ROW(OLD.run_key,OLD.attempt_key,OLD.period_key,OLD.input_bytes,OLD.output_cap,OLD.kind,OLD.execution_run_id,OLD.execution_owner,OLD.reserved_cny,OLD.actor_tenant,OLD.entitlement_grant_id,OLD.memory_scope,OLD.membership_evidence_digest,OLD.membership_verification) THEN RAISE EXCEPTION 'monthly_attempt_identity_is_immutable'; END IF;
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
    OR NOT EXISTS(SELECT 1 FROM hcla.execution e WHERE e.run_id=NEW.execution_run_id AND e.owner=NEW.execution_owner AND ((NEW.actor_tenant='hcla-owner' AND NOT (to_jsonb(e) ? 'tenant')) OR to_jsonb(e)->>'tenant'=NEW.actor_tenant) AND e.expires_at>hcla.qwen_monthly_clock() AND NOT e.cancelled AND NOT e.finished)
   THEN RAISE EXCEPTION 'verified_completed_settlement_required'; END IF;
   IF NEW.actor_tenant<>'hcla-owner' AND NOT EXISTS(SELECT 1 FROM hcla.qwen_member_entitlements WHERE tenant=NEW.actor_tenant AND grant_id=NEW.entitlement_grant_id AND paid_evidence_digest=NEW.membership_evidence_digest AND payment_verification=NEW.membership_verification AND enabled AND paid_membership AND payment_verification IN('ADMIN_VERIFIED','TRUSTED_PAYMENT_EVENT') AND paid_evidence_digest IS NOT NULL AND paid_verified_at IS NOT NULL AND paid_verified_at<=clock_timestamp() AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND CASE WHEN NEW.memory_scope='TEMPORARY' THEN temporary_enabled ELSE persistent_enabled END) THEN RAISE EXCEPTION 'member_entitlement_required'; END IF;
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
-- Periods contain only one shared financial policy, never actor/conversation data.
DROP POLICY owner_only ON qwen_monthly_periods;
CREATE POLICY shared_period_metadata ON qwen_monthly_periods TO hcla_app USING(true) WITH CHECK(current_setting('hcla.tenant',true)='hcla-owner' OR current_setting('hcla.tenant',true) ~ '^member-[0-9a-f]{64}$');
DROP POLICY owner_only ON qwen_monthly_attempts;
CREATE POLICY actor_read ON qwen_monthly_attempts FOR SELECT TO hcla_app USING(actor_tenant=current_setting('hcla.tenant',true) OR current_setting('hcla.tenant',true)='hcla-owner');
CREATE POLICY actor_insert ON qwen_monthly_attempts FOR INSERT TO hcla_app WITH CHECK(actor_tenant=current_setting('hcla.tenant',true));
CREATE POLICY actor_update ON qwen_monthly_attempts FOR UPDATE TO hcla_app USING(actor_tenant=current_setting('hcla.tenant',true)) WITH CHECK(actor_tenant=current_setting('hcla.tenant',true));
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
