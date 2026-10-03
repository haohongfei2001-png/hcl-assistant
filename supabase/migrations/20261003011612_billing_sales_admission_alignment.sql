-- New sales use the same shared request cap and Shanghai-month cutoff as
-- model admission. This neither reserves future service nor changes funding,
-- membership fulfilment, role privileges, or any existing immutable policy.
BEGIN;
CREATE OR REPLACE FUNCTION hcla.billing_capacity() RETURNS jsonb
 LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path=pg_catalog,hcla AS $body$
DECLARE policy jsonb; state jsonb; reserve numeric; month_end timestamptz; reason text;
BEGIN
 SELECT a.policy::jsonb INTO policy FROM hcla.qwen_monthly_authorization a
  WHERE singleton=1 AND enabled AND a.policy::jsonb->'monthly'->>'scope'='AUTHENTICATED_SHARED';
 IF NOT FOUND THEN RETURN jsonb_build_object('available',false,'reason','MODEL_NOT_CONFIGURED'); END IF;
 state=hcla.qwen_monthly_shared_state();
 reserve=((policy->>'input_token_reservation')::numeric*(policy->>'input_cny_per_million')::numeric
  +((policy->>'max_completion_tokens')::integer+10)*(policy->>'output_cny_per_million')::numeric)/1000000;
 -- Derive the boundary from the ledger snapshot's period. If the calendar
 -- rolls over between reads, this call closes conservatively; the next read
 -- uses the fresh period. No period row is created by this availability read.
 month_end=(((state->>'period')||'-01')::date+interval '1 month') AT TIME ZONE 'Asia/Shanghai';
 reason=CASE
  WHEN NOT (state->>'smoke_ready')::boolean THEN 'READINESS_REQUIRED'
  WHEN hcla.qwen_monthly_clock()+interval '300 seconds'>=month_end THEN 'MONTH_BOUNDARY_PAUSE'
  WHEN (state->>'request_count')::bigint>=(policy->>'max_requests')::bigint THEN 'SHARED_REQUEST_LIMIT'
  WHEN 500-(state->>'charged_cny')::numeric<reserve THEN 'SHARED_BUDGET_EXHAUSTED'
  ELSE NULL END;
 RETURN jsonb_build_object('available',reason IS NULL,'reservation_cny',reserve::text,'reason',reason);
END $body$;
COMMIT;
