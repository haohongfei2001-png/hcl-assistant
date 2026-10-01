-- New policy/attempt tables only. Historical v2 grants and rows stay unchanged.
BEGIN;
SET LOCAL search_path = hcla, pg_catalog;
CREATE TABLE trial_budget_policy(singleton integer PRIMARY KEY CHECK(singleton=1),policy text NOT NULL);
CREATE TABLE trial_budget_attempts(
 run_key text NOT NULL,attempt_key text NOT NULL,input_bytes integer NOT NULL,
 reserved_usd numeric NOT NULL CHECK(reserved_usd>=0),
 charged_usd numeric NOT NULL CHECK(charged_usd>=0),
 outcome text NOT NULL CHECK(outcome IN ('active','completed','failed','cancelled','unknown')),
 input_tokens bigint,output_tokens bigint,actual_usd numeric,
 policy_version integer NOT NULL DEFAULT 3 CHECK(policy_version=3),
 PRIMARY KEY(run_key,attempt_key),
 CHECK(charged_usd>=reserved_usd OR
  (outcome='completed' AND actual_usd IS NOT NULL AND actual_usd>=0
   AND charged_usd>=actual_usd AND input_tokens IS NOT NULL AND output_tokens IS NOT NULL
   AND input_tokens>0 AND output_tokens>0))
);
ALTER TABLE trial_budget_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_budget_policy FORCE ROW LEVEL SECURITY;
ALTER TABLE trial_budget_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_budget_attempts FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_metadata ON trial_budget_policy TO hcla_app USING(true) WITH CHECK(true);
CREATE POLICY owner_metadata ON trial_budget_attempts TO hcla_app USING(true) WITH CHECK(true);
REVOKE ALL ON trial_budget_policy,trial_budget_attempts FROM PUBLIC;
GRANT SELECT ON trial_budget_policy TO hcla_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON trial_budget_attempts TO hcla_app;
-- No grant/window is installed; separate bounded activation is required.
COMMIT;
