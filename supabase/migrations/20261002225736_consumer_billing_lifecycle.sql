-- Source-only consumer commerce. No live configuration, price, account, credential,
-- payment, grant or public database access is created by this migration.
BEGIN;
SET LOCAL search_path=hcla,pg_catalog;
DO $body$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='hcla_billing_worker') THEN
  CREATE ROLE hcla_billing_worker NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
 END IF;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='hcla_billing_worker' AND (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolcanlogin)) THEN RAISE EXCEPTION 'dedicated_no_login_billing_role_required'; END IF;
END $body$;
GRANT USAGE ON SCHEMA hcla TO hcla_billing_worker;
CREATE TABLE billing_configuration(
 singleton integer PRIMARY KEY CHECK(singleton=1),enabled boolean NOT NULL DEFAULT false,
 provider text NOT NULL CHECK(provider ~ '^[a-z0-9_-]{3,60}$'),
 merchant text NOT NULL CHECK(merchant ~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$'),
 checkout_origins text[] NOT NULL DEFAULT '{}' CHECK(cardinality(checkout_origins)<=8),
 approval_digest text NOT NULL CHECK(approval_digest ~ '^[0-9a-f]{64}$')
);
CREATE FUNCTION guard_billing_configuration() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
BEGIN
 IF TG_OP='DELETE' OR TG_OP='UPDATE' AND (to_jsonb(NEW)-'enabled') IS DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN RAISE EXCEPTION 'billing_configuration_is_immutable'; END IF;
 IF NEW.enabled AND (cardinality(NEW.checkout_origins)=0 OR EXISTS(SELECT 1 FROM unnest(NEW.checkout_origins) origin WHERE origin !~ '^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$')) THEN RAISE EXCEPTION 'approved_checkout_origins_required'; END IF;
 RETURN NEW;
END $body$;
CREATE TRIGGER immutable_billing_configuration BEFORE INSERT OR UPDATE OR DELETE ON billing_configuration FOR EACH ROW EXECUTE FUNCTION guard_billing_configuration();
CREATE TABLE billing_plan_versions(
 plan_id text NOT NULL CHECK(plan_id ~ '^[a-z0-9_-]{3,60}$'),version integer NOT NULL CHECK(version>0),
 title text NOT NULL CHECK(length(title) BETWEEN 1 AND 80),enabled boolean NOT NULL DEFAULT false,
 currency text NOT NULL DEFAULT 'CNY' CHECK(currency='CNY'),amount_minor bigint NOT NULL CHECK(amount_minor BETWEEN 1 AND 100000000),
 duration_days integer NOT NULL CHECK(duration_days BETWEEN 1 AND 366),
 max_requests integer NOT NULL CHECK(max_requests BETWEEN 1 AND 1000000),
 max_cost_cny numeric NOT NULL CHECK(max_cost_cny>=12.295272 AND max_cost_cny<=500),
 temporary_enabled boolean NOT NULL,persistent_enabled boolean NOT NULL,
 terms_digest text NOT NULL CHECK(terms_digest ~ '^[0-9a-f]{64}$'),
 shared_capacity_limited boolean NOT NULL DEFAULT true CHECK(shared_capacity_limited),
 renewal_mode text NOT NULL DEFAULT 'USER_INITIATED_FIXED_DURATION' CHECK(renewal_mode='USER_INITIATED_FIXED_DURATION'),
 approved_at timestamptz NOT NULL,PRIMARY KEY(plan_id,version),CHECK(temporary_enabled OR persistent_enabled)
);
CREATE FUNCTION guard_billing_plan() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
BEGIN
 IF TG_OP='DELETE' OR TG_OP='UPDATE' AND (to_jsonb(NEW)-'enabled') IS DISTINCT FROM (to_jsonb(OLD)-'enabled') THEN RAISE EXCEPTION 'billing_plan_terms_are_immutable'; END IF;
 RETURN NEW;
END $body$;
CREATE TRIGGER immutable_billing_plan BEFORE UPDATE OR DELETE ON billing_plan_versions FOR EACH ROW EXECUTE FUNCTION guard_billing_plan();
CREATE TABLE billing_orders(
 order_id text PRIMARY KEY CHECK(order_id ~ '^[a-f0-9-]{36}$'),tenant text NOT NULL CHECK(tenant ~ '^member-[0-9a-f]{64}$'),
 plan_id text NOT NULL,plan_version integer NOT NULL,idempotency_key text NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 120),
 accepted_terms_digest text NOT NULL,provider text NOT NULL DEFAULT '',merchant text NOT NULL DEFAULT '',
 product_id text NOT NULL DEFAULT '',currency text NOT NULL DEFAULT 'CNY',amount_minor bigint NOT NULL DEFAULT 0,
 duration_days integer NOT NULL DEFAULT 0,max_requests integer NOT NULL DEFAULT 0,max_cost_cny numeric NOT NULL DEFAULT 0,
 temporary_enabled boolean NOT NULL DEFAULT false,persistent_enabled boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),expires_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 state text NOT NULL DEFAULT 'PENDING' CHECK(state IN('PENDING','CREATING','CHECKOUT_READY','UNCERTAIN','FULFILLED','REFUNDED','DISPUTED','REVIEW_REQUIRED','EXPIRED')),
 external_order_id text,checkout_url text,grant_id text,payment_id text,verification_state text NOT NULL DEFAULT 'NOT_QUERIED',
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(plan_id,plan_version) REFERENCES billing_plan_versions(plan_id,version),
 UNIQUE(tenant,idempotency_key),UNIQUE(provider,merchant,external_order_id)
);
CREATE INDEX billing_orders_tenant_created ON billing_orders(tenant,created_at DESC);
CREATE TABLE billing_verified_payments(
 provider text NOT NULL,merchant text NOT NULL,payment_id text NOT NULL,
 order_id text NOT NULL REFERENCES billing_orders(order_id),external_order_id text NOT NULL,
 evidence_digest text NOT NULL CHECK(evidence_digest ~ '^[0-9a-f]{64}$'),
 amount_minor bigint NOT NULL,currency text NOT NULL CHECK(currency='CNY'),
 state text NOT NULL CHECK(state IN('CAPTURED','REFUNDED','PARTIAL_REFUND','DISPUTED')),
 paid_at timestamptz NOT NULL,refunded_minor bigint NOT NULL CHECK(refunded_minor>=0),
 verification_source text NOT NULL CHECK(verification_source='AUTHENTICATED_SERVER_ORDER_QUERY'),
 observed_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(provider,merchant,payment_id),UNIQUE(order_id)
);
CREATE TABLE billing_audit(
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,order_id text NOT NULL REFERENCES billing_orders(order_id),
 action text NOT NULL CHECK(action IN('CHECKOUT_CLAIMED','CHECKOUT_READY','CHECKOUT_UNKNOWN','VERIFICATION_UNKNOWN','FULFILLED','REFUNDED','DISPUTED','REVIEW_REQUIRED')),
 evidence_digest text,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE FUNCTION billing_capacity() RETURNS jsonb LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE policy jsonb; state jsonb; reserve numeric;
BEGIN
 SELECT a.policy::jsonb INTO policy FROM hcla.qwen_monthly_authorization a WHERE singleton=1 AND enabled AND a.policy::jsonb->'monthly'->>'scope'='AUTHENTICATED_SHARED';
 IF NOT FOUND THEN RETURN jsonb_build_object('available',false,'reason','MODEL_NOT_CONFIGURED'); END IF;
 state=hcla.qwen_monthly_shared_state();
 reserve=((policy->>'input_token_reservation')::numeric*(policy->>'input_cny_per_million')::numeric+((policy->>'max_completion_tokens')::integer+10)*(policy->>'output_cny_per_million')::numeric)/1000000;
 RETURN jsonb_build_object('available',(state->>'smoke_ready')::boolean AND 500-(state->>'charged_cny')::numeric>=reserve,'reservation_cny',reserve::text,'reason',CASE WHEN NOT (state->>'smoke_ready')::boolean THEN 'READINESS_REQUIRED' WHEN 500-(state->>'charged_cny')::numeric<reserve THEN 'SHARED_BUDGET_EXHAUSTED' ELSE NULL END);
END $body$;
CREATE FUNCTION guard_billing_order_insert() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE plan hcla.billing_plan_versions%ROWTYPE; config hcla.billing_configuration%ROWTYPE; capacity jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF NEW.tenant IS DISTINCT FROM current_setting('hcla.tenant',true) OR NOT EXISTS(
  SELECT 1 FROM hcla.member_sessions s LEFT JOIN hcla.member_auth_generations g ON g.tenant=s.tenant
  WHERE s.tenant=NEW.tenant AND s.session_key=current_setting('hcla.member_session',true) AND s.expires_at>clock_timestamp() AND s.absolute_expires_at>clock_timestamp()
   AND (s.refresh_state='idle' OR s.refresh_started_at>clock_timestamp()-interval '20 seconds')
   AND s.auth_generation=COALESCE(g.generation,0) AND NOT COALESCE(g.reset_pending,false)
 ) THEN RAISE EXCEPTION 'verified_member_checkout_required'; END IF;
 SELECT * INTO plan FROM hcla.billing_plan_versions WHERE plan_id=NEW.plan_id AND version=NEW.plan_version AND enabled AND approved_at<=clock_timestamp();
 IF NOT FOUND OR NEW.accepted_terms_digest IS DISTINCT FROM plan.terms_digest THEN RAISE EXCEPTION 'approved_current_plan_terms_required'; END IF;
 SELECT * INTO config FROM hcla.billing_configuration WHERE singleton=1 AND enabled;
 IF NOT FOUND THEN RAISE EXCEPTION 'billing_not_enabled'; END IF;
 capacity=hcla.billing_capacity();
 IF (capacity->>'available')::boolean IS DISTINCT FROM true OR plan.max_cost_cny<(capacity->>'reservation_cny')::numeric THEN RAISE EXCEPTION 'shared_capacity_unavailable_no_new_sale'; END IF;
 NEW.provider=config.provider;NEW.merchant=config.merchant;NEW.product_id=plan.plan_id||':'||plan.version;
 NEW.amount_minor=plan.amount_minor;NEW.currency=plan.currency;NEW.duration_days=plan.duration_days;
 NEW.max_requests=plan.max_requests;NEW.max_cost_cny=plan.max_cost_cny;NEW.temporary_enabled=plan.temporary_enabled;NEW.persistent_enabled=plan.persistent_enabled;
 NEW.created_at=clock_timestamp();NEW.expires_at=NEW.created_at+interval '30 minutes';NEW.updated_at=NEW.created_at;
 NEW.state='PENDING';NEW.external_order_id=NULL;NEW.checkout_url=NULL;NEW.grant_id=NULL;NEW.payment_id=NULL;NEW.verification_state='NOT_QUERIED';
 RETURN NEW;
END $body$;
CREATE TRIGGER insert_bound_billing_order BEFORE INSERT ON billing_orders FOR EACH ROW EXECUTE FUNCTION guard_billing_order_insert();
CREATE FUNCTION guard_billing_order_update() RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'billing_order_cannot_be_erased'; END IF;
 IF (to_jsonb(NEW)-ARRAY['state','external_order_id','checkout_url','grant_id','payment_id','verification_state','updated_at']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['state','external_order_id','checkout_url','grant_id','payment_id','verification_state','updated_at']) THEN RAISE EXCEPTION 'billing_order_terms_are_immutable'; END IF;
 IF OLD.external_order_id IS NOT NULL AND NEW.external_order_id IS DISTINCT FROM OLD.external_order_id THEN RAISE EXCEPTION 'payment_order_binding_is_immutable'; END IF;
 IF OLD.grant_id IS NOT NULL AND NEW.grant_id IS DISTINCT FROM OLD.grant_id THEN RAISE EXCEPTION 'membership_grant_binding_is_immutable'; END IF;
 IF OLD.payment_id IS NOT NULL AND NEW.payment_id IS DISTINCT FROM OLD.payment_id THEN RAISE EXCEPTION 'payment_identity_is_immutable'; END IF;
 IF OLD.state IN('REFUNDED','DISPUTED') AND NEW.state IS DISTINCT FROM OLD.state THEN RAISE EXCEPTION 'terminal_payment_cannot_resurrect'; END IF;
 NEW.updated_at=clock_timestamp();RETURN NEW;
END $body$;
CREATE TRIGGER immutable_billing_order BEFORE UPDATE OR DELETE ON billing_orders FOR EACH ROW EXECUTE FUNCTION guard_billing_order_update();

-- These private functions execute only for the separately provisioned, narrow
-- billing worker. The ordinary runtime has no membership-write capability.
CREATE FUNCTION billing_require_member(actor text,session_hash text) RETURNS void
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
BEGIN
 IF actor IS NULL OR actor !~ '^member-[0-9a-f]{64}$' OR NOT EXISTS(
  SELECT 1 FROM hcla.member_sessions s LEFT JOIN hcla.member_auth_generations g ON g.tenant=s.tenant
  WHERE s.tenant=actor AND s.session_key=session_hash AND s.expires_at>clock_timestamp() AND s.absolute_expires_at>clock_timestamp()
   AND (s.refresh_state='idle' OR s.refresh_started_at>clock_timestamp()-interval '20 seconds')
   AND s.auth_generation=COALESCE(g.generation,0) AND NOT COALESCE(g.reset_pending,false)
 ) THEN RAISE EXCEPTION 'verified_member_checkout_required'; END IF;
END $body$;
CREATE FUNCTION billing_claim_checkout(oid text,actor text,session_hash text) RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
DECLARE o hcla.billing_orders%ROWTYPE; capacity jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 PERFORM hcla.billing_require_member(actor,session_hash);
 SELECT * INTO o FROM hcla.billing_orders WHERE order_id=oid AND tenant=actor FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'order_not_found'; END IF;
 IF o.expires_at<=clock_timestamp() THEN RAISE EXCEPTION 'checkout_quote_expired'; END IF;
 IF NOT EXISTS(SELECT 1 FROM hcla.billing_configuration WHERE singleton=1 AND enabled AND provider=o.provider AND merchant=o.merchant)
 OR NOT EXISTS(SELECT 1 FROM hcla.billing_plan_versions WHERE plan_id=o.plan_id AND version=o.plan_version AND enabled) THEN RAISE EXCEPTION 'billing_not_enabled'; END IF;
 PERFORM set_config('hcla.tenant',actor,true);
 capacity=hcla.billing_capacity();
 IF (capacity->>'available')::boolean IS DISTINCT FROM true THEN RAISE EXCEPTION 'shared_capacity_unavailable_no_new_sale'; END IF;
 IF o.state='CHECKOUT_READY' THEN RETURN to_jsonb(o); END IF;
 IF o.state<>'PENDING' THEN RAISE EXCEPTION 'checkout_creation_already_claimed_query_only'; END IF;
 UPDATE hcla.billing_orders SET state='CREATING' WHERE order_id=oid RETURNING * INTO o;
 INSERT INTO hcla.billing_audit(order_id,action) VALUES(oid,'CHECKOUT_CLAIMED');
 RETURN to_jsonb(o);
END $body$;
CREATE FUNCTION billing_complete_checkout(oid text,external_id text,destination text) RETURNS void
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
DECLARE o hcla.billing_orders%ROWTYPE;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 SELECT * INTO o FROM hcla.billing_orders WHERE order_id=oid FOR UPDATE;
 IF NOT FOUND OR o.state NOT IN('CREATING','UNCERTAIN','CHECKOUT_READY') THEN RAISE EXCEPTION 'checkout_claim_required'; END IF;
 IF external_id IS NULL OR external_id !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$' OR destination IS NULL OR length(destination)>2048
  OR destination !~ '^https://[^/?#@]+(/[^#]*)?$' OR NOT EXISTS(
   SELECT 1 FROM hcla.billing_configuration WHERE singleton=1 AND provider=o.provider AND merchant=o.merchant
    AND substring(destination from '^(https://[^/?#]+)')=ANY(checkout_origins)
  ) THEN RAISE EXCEPTION 'approved_checkout_binding_required'; END IF;
 IF o.external_order_id IS NOT NULL AND (o.external_order_id<>external_id OR o.checkout_url IS DISTINCT FROM destination) THEN RAISE EXCEPTION 'checkout_binding_is_immutable'; END IF;
 UPDATE hcla.billing_orders SET state='CHECKOUT_READY',external_order_id=external_id,checkout_url=destination WHERE order_id=oid;
 INSERT INTO hcla.billing_audit(order_id,action) VALUES(oid,'CHECKOUT_READY');
END $body$;
CREATE FUNCTION billing_mark_unknown(oid text,phase text) RETURNS void
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 IF phase='CHECKOUT' THEN
  UPDATE hcla.billing_orders SET state='UNCERTAIN' WHERE order_id=oid AND state='CREATING';
 ELSIF phase='VERIFICATION' THEN
  UPDATE hcla.billing_orders SET verification_state='UNCONFIRMED' WHERE order_id=oid;
 ELSE RAISE EXCEPTION 'invalid_billing_phase'; END IF;
 IF FOUND THEN INSERT INTO hcla.billing_audit(order_id,action) VALUES(oid,CASE WHEN phase='CHECKOUT' THEN 'CHECKOUT_UNKNOWN' ELSE 'VERIFICATION_UNKNOWN' END); END IF;
END $body$;
CREATE FUNCTION billing_apply_verified(oid text,proof jsonb) RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,hcla SET row_security=off AS $body$
DECLARE o hcla.billing_orders%ROWTYPE; previous hcla.billing_verified_payments%ROWTYPE;
 paid_time timestamptz; starts timestamptz; ends timestamptz; gid text; status text; refund bigint;
BEGIN
 PERFORM pg_advisory_xact_lock(171956945,1);
 SELECT * INTO o FROM hcla.billing_orders WHERE order_id=oid FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'order_not_found'; END IF;
 IF jsonb_typeof(proof) IS DISTINCT FROM 'object'
  OR proof->>'verification_source' IS DISTINCT FROM 'AUTHENTICATED_SERVER_ORDER_QUERY'
  OR proof->>'provider' IS DISTINCT FROM o.provider OR proof->>'merchant' IS DISTINCT FROM o.merchant
  OR proof->>'order_id' IS DISTINCT FROM o.order_id OR proof->>'product_id' IS DISTINCT FROM o.product_id
  OR jsonb_typeof(proof->'amount_minor') IS DISTINCT FROM 'number'
  OR proof->>'currency' IS DISTINCT FROM o.currency OR proof->>'amount_minor' IS DISTINCT FROM o.amount_minor::text
  OR COALESCE(proof->>'external_order_id','') !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$'
  OR COALESCE(proof->>'evidence_digest','') !~ '^[0-9a-f]{64}$'
  OR (o.external_order_id IS NOT NULL AND proof->>'external_order_id' IS DISTINCT FROM o.external_order_id)
  OR (o.external_order_id IS NULL AND o.state NOT IN('CREATING','UNCERTAIN')) THEN RAISE EXCEPTION 'verified_payment_binding_mismatch'; END IF;
 status=proof->>'state';
 IF status IS NULL OR status NOT IN('PENDING','FAILED','CAPTURED','REFUNDED','PARTIAL_REFUND','DISPUTED')
  OR jsonb_typeof(proof->'refunded_minor') IS DISTINCT FROM 'number'
  OR COALESCE(proof->>'refunded_minor','') !~ '^(0|[1-9][0-9]{0,8})$' THEN RAISE EXCEPTION 'verified_payment_state_required'; END IF;
 refund=(proof->>'refunded_minor')::bigint;
 IF refund>o.amount_minor OR (status IN('PENDING','FAILED','CAPTURED') AND refund<>0)
  OR (status='REFUNDED' AND refund<>o.amount_minor)
  OR (status='PARTIAL_REFUND' AND (refund=0 OR refund=o.amount_minor)) THEN RAISE EXCEPTION 'complete_financial_state_required'; END IF;
 IF o.external_order_id IS NULL THEN
  UPDATE hcla.billing_orders SET external_order_id=proof->>'external_order_id' WHERE order_id=oid RETURNING * INTO o;
 END IF;
 IF status IN('PENDING','FAILED') THEN RETURN jsonb_build_object('order_id',oid,'state',o.state,'membership_changed',false); END IF;
 IF COALESCE(proof->>'payment_id','') !~ '^[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}$'
  OR jsonb_typeof(proof->'paid_at') IS DISTINCT FROM 'number'
  OR COALESCE(proof->>'paid_at','') !~ '^[1-9][0-9]{0,10}$' THEN RAISE EXCEPTION 'verified_payment_identity_and_time_required'; END IF;
 paid_time=to_timestamp((proof->>'paid_at')::bigint);
 IF paid_time<date_trunc('second',o.created_at) OR paid_time>o.expires_at THEN RAISE EXCEPTION 'payment_outside_quote_window'; END IF;
 IF o.payment_id IS NOT NULL AND o.payment_id IS DISTINCT FROM proof->>'payment_id' THEN RAISE EXCEPTION 'payment_identity_is_immutable'; END IF;
 SELECT * INTO previous FROM hcla.billing_verified_payments WHERE provider=o.provider AND merchant=o.merchant AND payment_id=proof->>'payment_id' FOR UPDATE;
 IF FOUND AND (previous.order_id<>oid OR previous.paid_at<>paid_time) THEN RAISE EXCEPTION 'payment_already_bound'; END IF;
 -- A delayed capture or stale refund snapshot must not undo a later event.
 IF o.state IN('REFUNDED','DISPUTED') OR (previous.payment_id IS NOT NULL AND (previous.refunded_minor>refund OR (previous.state='PARTIAL_REFUND' AND status='CAPTURED'))) THEN
  RETURN jsonb_build_object('order_id',oid,'state',o.state,'membership_changed',false);
 END IF;
 INSERT INTO hcla.billing_verified_payments(provider,merchant,payment_id,order_id,external_order_id,evidence_digest,amount_minor,currency,state,paid_at,refunded_minor,verification_source)
 VALUES(o.provider,o.merchant,proof->>'payment_id',oid,o.external_order_id,proof->>'evidence_digest',o.amount_minor,o.currency,status,paid_time,refund,'AUTHENTICATED_SERVER_ORDER_QUERY')
 ON CONFLICT(provider,merchant,payment_id) DO UPDATE SET state=EXCLUDED.state,refunded_minor=EXCLUDED.refunded_minor,evidence_digest=EXCLUDED.evidence_digest,observed_at=clock_timestamp();
 IF status='CAPTURED' THEN
  IF o.grant_id IS NOT NULL THEN RETURN jsonb_build_object('order_id',oid,'state',o.state,'membership_changed',false); END IF;
  -- Global lock serializes simultaneous purchases. Periods never overlap and
  -- existing grant evidence/expiry is never rewritten for a renewal.
  SELECT greatest(clock_timestamp(),COALESCE(max(expires_at),clock_timestamp())) INTO starts FROM hcla.qwen_member_entitlements WHERE tenant=o.tenant AND enabled AND expires_at>clock_timestamp();
  ends=starts+make_interval(days=>o.duration_days);gid='order-'||o.order_id;
  INSERT INTO hcla.qwen_member_entitlements(tenant,grant_id,enabled,paid_membership,payment_verification,paid_evidence_digest,paid_verified_at,starts_at,expires_at,temporary_enabled,persistent_enabled,max_requests,max_cost_cny)
  VALUES(o.tenant,gid,true,true,'TRUSTED_PAYMENT_EVENT',proof->>'evidence_digest',clock_timestamp(),starts,ends,o.temporary_enabled,o.persistent_enabled,o.max_requests,o.max_cost_cny);
  UPDATE hcla.qwen_member_test_entitlements SET enabled=false WHERE tenant=o.tenant AND enabled;
  UPDATE hcla.billing_orders SET state='FULFILLED',grant_id=gid,payment_id=proof->>'payment_id',verification_state='VERIFIED' WHERE order_id=oid;
  INSERT INTO hcla.billing_audit(order_id,action,evidence_digest) VALUES(oid,'FULFILLED',proof->>'evidence_digest');
  RETURN jsonb_build_object('order_id',oid,'state','FULFILLED','membership_changed',true,'starts_at',starts,'expires_at',ends);
 ELSE
  -- Authoritative refund/dispute events revoke only this order's grant. A
  -- partial refund is suspended for review; no proration/refund payment exists.
  UPDATE hcla.qwen_member_entitlements SET enabled=false WHERE tenant=o.tenant AND grant_id=o.grant_id;
  UPDATE hcla.billing_orders SET state=CASE WHEN status='PARTIAL_REFUND' THEN 'REVIEW_REQUIRED' ELSE status END,
   payment_id=proof->>'payment_id',verification_state=CASE WHEN status='PARTIAL_REFUND' THEN 'PARTIAL_REFUND_REVIEW' ELSE 'VERIFIED' END WHERE order_id=oid;
  INSERT INTO hcla.billing_audit(order_id,action,evidence_digest) VALUES(oid,CASE WHEN status='PARTIAL_REFUND' THEN 'REVIEW_REQUIRED' ELSE status END,proof->>'evidence_digest');
 END IF;
 RETURN jsonb_build_object('order_id',oid,'state',CASE WHEN status='PARTIAL_REFUND' THEN 'REVIEW_REQUIRED' ELSE status END,'membership_changed',o.grant_id IS NOT NULL);
END $body$;

DO $body$ DECLARE name text; BEGIN
 FOREACH name IN ARRAY ARRAY['billing_configuration','billing_plan_versions','billing_orders','billing_verified_payments','billing_audit'] LOOP
  EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
  EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
  EXECUTE format('REVOKE ALL ON hcla.%I FROM PUBLIC',name);
  EXECUTE format('CREATE POLICY billing_worker_read ON hcla.%I FOR SELECT TO hcla_billing_worker USING(true)',name);
 END LOOP;
END $body$;
CREATE POLICY billing_config_metadata ON billing_configuration FOR SELECT TO hcla_app USING(true);
CREATE POLICY billing_plan_metadata ON billing_plan_versions FOR SELECT TO hcla_app USING(true);
CREATE POLICY own_billing_orders ON billing_orders TO hcla_app USING(tenant=current_setting('hcla.tenant',true)) WITH CHECK(tenant=current_setting('hcla.tenant',true));
GRANT SELECT ON billing_configuration,billing_plan_versions,billing_orders TO hcla_app;
GRANT INSERT(order_id,tenant,plan_id,plan_version,idempotency_key,accepted_terms_digest) ON billing_orders TO hcla_app;
GRANT SELECT ON billing_configuration,billing_plan_versions,billing_orders,billing_verified_payments,billing_audit TO hcla_billing_worker;
REVOKE ALL ON FUNCTION guard_billing_configuration(),billing_require_member(text,text),billing_claim_checkout(text,text,text),billing_complete_checkout(text,text,text),billing_mark_unknown(text,text),guard_billing_plan(),billing_capacity(),guard_billing_order_insert(),guard_billing_order_update(),billing_apply_verified(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION billing_capacity(),guard_billing_order_insert() TO hcla_app;
GRANT EXECUTE ON FUNCTION billing_claim_checkout(text,text,text),billing_complete_checkout(text,text,text),billing_mark_unknown(text,text),billing_apply_verified(text,jsonb) TO hcla_billing_worker;
DO $body$ DECLARE role_name text; BEGIN
 FOREACH role_name IN ARRAY ARRAY['anon','authenticated'] LOOP
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname=role_name) THEN
   EXECUTE format('REVOKE ALL ON hcla.billing_configuration,hcla.billing_plan_versions,hcla.billing_orders,hcla.billing_verified_payments,hcla.billing_audit FROM %I',role_name);
  END IF;
 END LOOP;
END $body$;
COMMIT;
