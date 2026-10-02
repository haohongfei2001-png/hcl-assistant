-- Default-closed source transition. Apply only after explicit live approval.
-- No Auth identity, grant, credential, policy row or provider call is created.
-- Existing immutable V3 funding policy/periods/attempts are never rewritten.
BEGIN;
SET LOCAL search_path=hcla,pg_catalog;
CREATE TABLE qwen_member_readiness_authorizations(
 authorization_id text PRIMARY KEY CHECK(authorization_id ~ '^[a-z0-9][a-z0-9_-]{5,79}$'),
 parent_policy_sha256 text NOT NULL CHECK(parent_policy_sha256 ~ '^[0-9a-f]{64}$'),
 enabled boolean NOT NULL DEFAULT false,
 starts_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 max_attempts integer NOT NULL DEFAULT 1 CHECK(max_attempts=1),
 approval_evidence_digest text NOT NULL CHECK(approval_evidence_digest ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(expires_at>starts_at AND isfinite(starts_at) AND isfinite(expires_at))
);
CREATE TABLE qwen_member_test_entitlements(
 tenant text NOT NULL CHECK(tenant ~ '^member-[0-9a-f]{64}$'),
 grant_id text NOT NULL CHECK(grant_id ~ '^[a-z0-9][a-z0-9_-]{5,79}$'),
 parent_policy_sha256 text NOT NULL CHECK(parent_policy_sha256 ~ '^[0-9a-f]{64}$'),
 access_kind text NOT NULL DEFAULT 'TEST_ONLY' CHECK(access_kind='TEST_ONLY'),
 verification text NOT NULL DEFAULT 'OWNER_APPROVED_TEST' CHECK(verification='OWNER_APPROVED_TEST'),
 enabled boolean NOT NULL DEFAULT false,
 starts_at timestamptz NOT NULL, expires_at timestamptz NOT NULL,
 readiness_enabled boolean NOT NULL DEFAULT false, chat_enabled boolean NOT NULL DEFAULT false,
 temporary_enabled boolean NOT NULL DEFAULT false, persistent_enabled boolean NOT NULL DEFAULT false,
 max_requests integer NOT NULL CHECK(max_requests BETWEEN 1 AND 1000000),
 max_cost_cny numeric NOT NULL CHECK(max_cost_cny>0 AND max_cost_cny<=500),
 budget_window text NOT NULL DEFAULT 'GRANT_LIFETIME_WITHIN_SHARED_MONTHLY_CEILING'
  CHECK(budget_window='GRANT_LIFETIME_WITHIN_SHARED_MONTHLY_CEILING'),
 approval_evidence_digest text NOT NULL CHECK(approval_evidence_digest ~ '^[0-9a-f]{64}$'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(tenant,grant_id),
 CHECK(expires_at>starts_at AND isfinite(starts_at) AND isfinite(expires_at)),
 CHECK(NOT readiness_enabled OR temporary_enabled)
);
ALTER TABLE qwen_monthly_attempts ADD COLUMN entitlement_kind text CHECK(entitlement_kind IN('PAID_MEMBERSHIP','TEST_ONLY'));
ALTER TABLE qwen_monthly_attempts ADD COLUMN test_evidence_digest text CHECK(test_evidence_digest ~ '^[0-9a-f]{64}$');
ALTER TABLE qwen_monthly_attempts ADD COLUMN readiness_authorization_id text REFERENCES qwen_member_readiness_authorizations(authorization_id);
ALTER TABLE qwen_monthly_attempts ADD COLUMN readiness_input_digest text CHECK(readiness_input_digest ~ '^[0-9a-f]{64}$');
ALTER TABLE qwen_monthly_attempts ADD COLUMN readiness_query_digest text CHECK(readiness_query_digest ~ '^[0-9a-f]{64}$');
CREATE INDEX qwen_member_grant_lifetime ON qwen_monthly_attempts(actor_tenant,entitlement_grant_id,entitlement_kind);

CREATE FUNCTION guard_qwen_member_authorization() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE policy text;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'member_authorization_cannot_be_reset'; END IF;
 IF TG_OP='UPDATE' AND (to_jsonb(NEW)-'enabled') IS DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN RAISE EXCEPTION 'member_authorization_terms_are_immutable'; END IF;
 SELECT a.policy INTO policy FROM hcla.qwen_monthly_authorization a WHERE singleton=1;
 IF policy IS NULL OR policy::jsonb->'monthly'->>'scope'<>'AUTHENTICATED_SHARED'
  OR policy::jsonb->>'version'<>'3' OR policy::jsonb->>'max_cost_cny'<>'500'
  OR NEW.parent_policy_sha256 IS DISTINCT FROM encode(sha256(convert_to(policy,'UTF8')),'hex') THEN RAISE EXCEPTION 'exact_shared_v3_parent_required'; END IF;
 RETURN NEW;
END $body$;
CREATE TRIGGER immutable_member_readiness BEFORE INSERT OR UPDATE OR DELETE ON qwen_member_readiness_authorizations FOR EACH ROW EXECUTE FUNCTION guard_qwen_member_authorization();
CREATE TRIGGER immutable_member_test_grant BEFORE INSERT OR UPDATE OR DELETE ON qwen_member_test_entitlements FOR EACH ROW EXECUTE FUNCTION guard_qwen_member_authorization();
ALTER TABLE qwen_member_readiness_authorizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE qwen_member_readiness_authorizations FORCE ROW LEVEL SECURITY;
CREATE POLICY read_activation_metadata ON qwen_member_readiness_authorizations FOR SELECT TO hcla_app USING(true);
ALTER TABLE qwen_member_test_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE qwen_member_test_entitlements FORCE ROW LEVEL SECURITY;
CREATE POLICY read_own_test_grant ON qwen_member_test_entitlements FOR SELECT TO hcla_app USING(tenant=current_setting('hcla.tenant',true));
REVOKE ALL ON qwen_member_readiness_authorizations,qwen_member_test_entitlements FROM PUBLIC;
DO $body$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=name) THEN
   EXECUTE format('REVOKE ALL ON hcla.qwen_member_readiness_authorizations,hcla.qwen_member_test_entitlements FROM %I',name);
  END IF;
 END LOOP;
END $body$;
GRANT SELECT ON qwen_member_readiness_authorizations,qwen_member_test_entitlements TO hcla_app;
REVOKE ALL ON FUNCTION guard_qwen_member_authorization() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guard_qwen_member_authorization() TO hcla_app;

-- Invoker-only grant verification; no grant writing or cross-tenant lookup.
CREATE FUNCTION qwen_member_access(actor text,grant_key text,kind text,memory text,readiness boolean,evidence text DEFAULT NULL) RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE entitlement record; overlaps bigint; policy text;
BEGIN
 IF actor IS DISTINCT FROM current_setting('hcla.tenant',true) OR actor !~ '^member-[0-9a-f]{64}$' OR memory NOT IN('TEMPORARY','CONVERSATION','TOPIC') THEN RAISE EXCEPTION 'member_actor_required'; END IF;
 SELECT (SELECT count(*) FROM hcla.qwen_member_entitlements WHERE tenant=actor AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp())+
        (SELECT count(*) FROM hcla.qwen_member_test_entitlements WHERE tenant=actor AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp()) INTO overlaps;
 IF overlaps<>1 THEN RAISE EXCEPTION 'ambiguous_or_missing_member_access'; END IF;
 IF COALESCE(kind,'PAID_MEMBERSHIP')='PAID_MEMBERSHIP' THEN
  SELECT * INTO entitlement FROM hcla.qwen_member_entitlements WHERE tenant=actor AND grant_id=grant_key AND enabled AND paid_membership AND payment_verification IN('ADMIN_VERIFIED','TRUSTED_PAYMENT_EVENT') AND paid_evidence_digest IS NOT NULL AND paid_verified_at IS NOT NULL AND paid_verified_at<=clock_timestamp() AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND CASE WHEN memory='TEMPORARY' THEN temporary_enabled ELSE persistent_enabled END;
  IF NOT FOUND OR (evidence IS NOT NULL AND entitlement.paid_evidence_digest IS DISTINCT FROM evidence) THEN RAISE EXCEPTION 'paid_membership_required'; END IF;
 ELSE
  IF kind<>'TEST_ONLY' THEN RAISE EXCEPTION 'unknown_member_access_kind'; END IF;
  SELECT * INTO entitlement FROM hcla.qwen_member_test_entitlements WHERE tenant=actor AND grant_id=grant_key AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND CASE WHEN memory='TEMPORARY' THEN temporary_enabled ELSE persistent_enabled END;
  SELECT a.policy INTO policy FROM hcla.qwen_monthly_authorization a WHERE singleton=1;
  IF NOT FOUND OR entitlement.grant_id IS NULL OR entitlement.parent_policy_sha256 IS DISTINCT FROM encode(sha256(convert_to(policy,'UTF8')),'hex')
   OR (readiness AND (memory<>'TEMPORARY' OR NOT entitlement.readiness_enabled)) OR (NOT readiness AND NOT entitlement.chat_enabled)
   OR (evidence IS NOT NULL AND entitlement.approval_evidence_digest IS DISTINCT FROM evidence) THEN RAISE EXCEPTION 'explicit_test_access_required'; END IF;
 END IF;
 RETURN to_jsonb(entitlement);
END $body$;
REVOKE ALL ON FUNCTION qwen_member_access(text,text,text,text,boolean,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION qwen_member_access(text,text,text,text,boolean,text) TO hcla_app;

CREATE OR REPLACE FUNCTION qwen_monthly_shared_state() RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
DECLARE actor text:=current_setting('hcla.tenant',true); period text; shared boolean; parent text; readiness hcla.qwen_member_readiness_authorizations%ROWTYPE; readiness_count bigint; summary jsonb;
BEGIN
 SELECT policy::jsonb->'monthly'->>'scope'='AUTHENTICATED_SHARED' INTO shared FROM hcla.qwen_monthly_authorization WHERE singleton=1;
 IF actor IS NULL OR (actor<>'hcla-owner' AND (NOT COALESCE(shared,false) OR actor !~ '^member-[0-9a-f]{64}$')) THEN RAISE EXCEPTION 'monthly_actor_scope_required'; END IF;
 SELECT encode(sha256(convert_to(policy,'UTF8')),'hex') INTO parent FROM hcla.qwen_monthly_authorization WHERE singleton=1;
 SELECT count(*) INTO readiness_count FROM hcla.qwen_member_readiness_authorizations WHERE enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND parent_policy_sha256=parent;
 IF readiness_count=1 THEN SELECT * INTO readiness FROM hcla.qwen_member_readiness_authorizations WHERE enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND parent_policy_sha256=parent; END IF;
 period=to_char(hcla.qwen_monthly_clock() AT TIME ZONE 'Asia/Shanghai','YYYY-MM');
 summary=(SELECT jsonb_build_object('period',period,
  'charged_cny',COALESCE(sum(charged_cny) FILTER(WHERE period_key=period),0)::text,
  'request_count',count(*) FILTER(WHERE period_key=period),
  'active_requests',count(*) FILTER(WHERE outcome='active'),
  'known_cny',(sum(actual_cny) FILTER(WHERE period_key=period))::text,
  'unknown_usage_requests',count(*) FILTER(WHERE period_key=period AND actual_cny IS NULL),
  'actor_charged_cny',COALESCE(sum(charged_cny) FILTER(WHERE period_key=period AND actor_tenant=actor),0)::text,
  'actor_request_count',count(*) FILTER(WHERE period_key=period AND actor_tenant=actor),
  'member_access_schema',1,
  'smoke_ready',COALESCE(bool_or(kind='SMOKE' AND outcome='completed' AND settled AND (actor_tenant='hcla-owner' OR EXISTS(SELECT 1 FROM hcla.qwen_member_readiness_authorizations proof WHERE proof.authorization_id=readiness_authorization_id AND proof.parent_policy_sha256=parent))),false))
  FROM hcla.qwen_monthly_attempts);
 IF readiness_count=1 AND (SELECT count(*) FROM hcla.qwen_monthly_attempts WHERE readiness_authorization_id=readiness.authorization_id)<readiness.max_attempts THEN
  RETURN summary||jsonb_build_object('member_readiness_authorization',readiness.authorization_id,'member_readiness_expires_at',FLOOR(EXTRACT(EPOCH FROM readiness.expires_at)));
 END IF;
 RETURN summary;
END $body$;

CREATE OR REPLACE FUNCTION guard_qwen_monthly_attempt() RETURNS trigger
 LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE p record; a record; entitlement jsonb; readiness hcla.qwen_member_readiness_authorizations%ROWTYPE; cfg jsonb; state jsonb; expected numeric; actual numeric; total numeric; attempts bigint; ready boolean;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'monthly_attempt_cannot_be_reset'; END IF;
 IF NEW.actor_tenant IS DISTINCT FROM current_setting('hcla.tenant',true) THEN RAISE EXCEPTION 'monthly_actor_scope_required'; END IF;
 SELECT * INTO p FROM hcla.qwen_monthly_periods WHERE period_key=NEW.period_key;
 IF NOT FOUND THEN RAISE EXCEPTION 'monthly_period_required'; END IF;
 cfg=p.policy::jsonb;
 IF NEW.actor_tenant<>'hcla-owner' AND cfg->'monthly'->>'scope'<>'AUTHENTICATED_SHARED' THEN RAISE EXCEPTION 'monthly_owner_scope_required'; END IF;
 IF NEW.actor_tenant='hcla-owner' AND (NEW.entitlement_kind IS NOT NULL OR NEW.test_evidence_digest IS NOT NULL OR NEW.readiness_authorization_id IS NOT NULL OR NEW.readiness_input_digest IS NOT NULL OR NEW.readiness_query_digest IS NOT NULL OR NEW.entitlement_grant_id IS NOT NULL OR NEW.membership_evidence_digest IS NOT NULL OR NEW.membership_verification IS NOT NULL) THEN RAISE EXCEPTION 'owner_grant_mismatch'; END IF;
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
  IF (NOT ready AND NEW.kind<>'SMOKE') OR (ready AND NEW.kind<>CASE WHEN NEW.actor_tenant='hcla-owner' THEN 'OWNER' ELSE 'MEMBER' END) THEN RAISE EXCEPTION 'verified_smoke_gate'; END IF;
  IF NEW.actor_tenant<>'hcla-owner' AND NEW.kind='SMOKE' THEN
   SELECT * INTO readiness FROM hcla.qwen_member_readiness_authorizations WHERE authorization_id=NEW.readiness_authorization_id AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp();
   IF NOT FOUND OR state->>'member_readiness_authorization' IS DISTINCT FROM NEW.readiness_authorization_id OR NEW.readiness_authorization_id IS NULL
    OR readiness.parent_policy_sha256 IS DISTINCT FROM encode(sha256(convert_to(p.policy,'UTF8')),'hex')
    OR NEW.memory_scope<>'TEMPORARY' OR NEW.readiness_input_digest IS DISTINCT FROM cfg->'smoke'->>'input_sha256'
    OR NEW.readiness_query_digest IS DISTINCT FROM cfg->'smoke'->>'query_sha256' THEN RAISE EXCEPTION 'explicit_member_readiness_required'; END IF;
  ELSIF NEW.readiness_authorization_id IS NOT NULL OR NEW.readiness_input_digest IS NOT NULL OR NEW.readiness_query_digest IS NOT NULL THEN RAISE EXCEPTION 'unexpected_readiness_attribution'; END IF;
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
   entitlement=hcla.qwen_member_access(NEW.actor_tenant,NEW.entitlement_grant_id,NEW.entitlement_kind,NEW.memory_scope,NEW.kind='SMOKE',CASE WHEN NEW.entitlement_kind='TEST_ONLY' THEN NEW.test_evidence_digest ELSE NEW.membership_evidence_digest END);
   IF NEW.entitlement_kind='TEST_ONLY' THEN
    IF NEW.membership_evidence_digest IS NOT NULL OR NEW.membership_verification IS NOT NULL THEN RAISE EXCEPTION 'test_access_is_not_paid_membership'; END IF;
    NEW.test_evidence_digest=entitlement->>'approval_evidence_digest';
   ELSE
    IF NEW.test_evidence_digest IS NOT NULL OR (NEW.membership_verification IS NOT NULL AND NEW.membership_verification IS DISTINCT FROM entitlement->>'payment_verification') THEN RAISE EXCEPTION 'paid_membership_evidence_mismatch'; END IF;
    NEW.membership_evidence_digest=entitlement->>'paid_evidence_digest';NEW.membership_verification=entitlement->>'payment_verification';
   END IF;
   SELECT COALESCE(sum(charged_cny),0),count(*) INTO total,attempts FROM hcla.qwen_monthly_attempts WHERE actor_tenant=NEW.actor_tenant AND entitlement_grant_id=NEW.entitlement_grant_id AND COALESCE(entitlement_kind,'PAID_MEMBERSHIP')=COALESCE(NEW.entitlement_kind,'PAID_MEMBERSHIP') AND (NEW.entitlement_kind='TEST_ONLY' OR period_key=NEW.period_key);
   IF total+expected>(entitlement->>'max_cost_cny')::numeric OR attempts>=(entitlement->>'max_requests')::integer THEN RAISE EXCEPTION 'member_subcap_exhausted'; END IF;
  END IF;
 ELSE
  IF ROW(NEW.run_key,NEW.attempt_key,NEW.period_key,NEW.input_bytes,NEW.output_cap,NEW.kind,NEW.execution_run_id,NEW.execution_owner,NEW.reserved_cny,NEW.actor_tenant,NEW.entitlement_grant_id,NEW.memory_scope,NEW.membership_evidence_digest,NEW.membership_verification,NEW.entitlement_kind,NEW.test_evidence_digest,NEW.readiness_authorization_id,NEW.readiness_input_digest,NEW.readiness_query_digest)
   IS DISTINCT FROM ROW(OLD.run_key,OLD.attempt_key,OLD.period_key,OLD.input_bytes,OLD.output_cap,OLD.kind,OLD.execution_run_id,OLD.execution_owner,OLD.reserved_cny,OLD.actor_tenant,OLD.entitlement_grant_id,OLD.memory_scope,OLD.membership_evidence_digest,OLD.membership_verification,OLD.entitlement_kind,OLD.test_evidence_digest,OLD.readiness_authorization_id,OLD.readiness_input_digest,OLD.readiness_query_digest) THEN RAISE EXCEPTION 'monthly_attempt_identity_is_immutable'; END IF;
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
   IF NEW.actor_tenant<>'hcla-owner' THEN
    entitlement=hcla.qwen_member_access(NEW.actor_tenant,NEW.entitlement_grant_id,NEW.entitlement_kind,NEW.memory_scope,NEW.kind='SMOKE',CASE WHEN NEW.entitlement_kind='TEST_ONLY' THEN NEW.test_evidence_digest ELSE NEW.membership_evidence_digest END);
    IF NEW.entitlement_kind IS DISTINCT FROM 'TEST_ONLY' AND NEW.membership_verification IS DISTINCT FROM entitlement->>'payment_verification' THEN RAISE EXCEPTION 'paid_membership_evidence_mismatch'; END IF;
    IF NEW.kind='SMOKE' AND NOT EXISTS(SELECT 1 FROM hcla.qwen_member_readiness_authorizations WHERE authorization_id=NEW.readiness_authorization_id AND enabled AND starts_at<=clock_timestamp() AND expires_at>clock_timestamp() AND parent_policy_sha256=encode(sha256(convert_to(p.policy,'UTF8')),'hex')) THEN RAISE EXCEPTION 'member_readiness_authorization_expired'; END IF;
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $body$;

COMMIT;
