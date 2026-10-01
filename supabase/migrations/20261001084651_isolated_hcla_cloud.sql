-- Apply only to a NEW, dedicated HCLA Postgres/Supabase project after owner approval.
-- No public API grants, auth account, login credential or paid resource is created.
BEGIN;
CREATE SCHEMA hcla;
REVOKE ALL ON SCHEMA hcla FROM PUBLIC;
CREATE ROLE hcla_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA hcla TO hcla_app;
SET LOCAL search_path = hcla, pg_catalog;
CREATE TABLE schema_version(singleton integer PRIMARY KEY CHECK(singleton=1),version integer NOT NULL);
INSERT INTO schema_version VALUES(1,1);
CREATE TABLE accounts(tenant text PRIMARY KEY,version integer NOT NULL DEFAULT 0,policy integer NOT NULL DEFAULT 0);
CREATE TABLE objects(id text PRIMARY KEY,tenant text NOT NULL,type text NOT NULL,body text NOT NULL,ordinal bigint GENERATED ALWAYS AS IDENTITY);
CREATE INDEX objects_scope ON objects(tenant,type,ordinal);
CREATE TABLE sources(id text NOT NULL,tenant text NOT NULL,version integer NOT NULL,body text NOT NULL,PRIMARY KEY(id,version));
CREATE INDEX sources_scope ON sources(tenant,id,version);
CREATE TABLE events(id text PRIMARY KEY,tenant text NOT NULL,conversation text NOT NULL,version integer NOT NULL,body text NOT NULL);
CREATE INDEX events_scope ON events(tenant,conversation,version);
CREATE TABLE idempotency(tenant text NOT NULL,conversation text NOT NULL,key text NOT NULL,hash text NOT NULL,result text NOT NULL,PRIMARY KEY(tenant,conversation,key));
CREATE TABLE records(id text NOT NULL,tenant text NOT NULL,version integer NOT NULL,body text NOT NULL,PRIMARY KEY(id,version));
CREATE INDEX records_scope ON records(tenant,version);
CREATE TABLE tombstones(id text PRIMARY KEY,tenant text NOT NULL);
-- Body-free, single-owner coordination and budget metadata. No user text or raw token.
CREATE TABLE execution(run_id text PRIMARY KEY,owner text NOT NULL,expires_at timestamptz NOT NULL,payload_hash text,temporary boolean NOT NULL DEFAULT false,cancelled boolean NOT NULL DEFAULT false,finished boolean NOT NULL DEFAULT false);
CREATE INDEX execution_expiry ON execution(expires_at) WHERE NOT finished;
CREATE TABLE budget_policy(singleton integer PRIMARY KEY CHECK(singleton=1),policy text NOT NULL);
CREATE TABLE budget_attempts(run_key text NOT NULL,attempt_key text NOT NULL,input_bytes integer NOT NULL,reserved_usd numeric NOT NULL CHECK(reserved_usd>=0),charged_usd numeric NOT NULL CHECK(charged_usd>=reserved_usd),outcome text NOT NULL CHECK(outcome IN ('active','completed','failed','cancelled','unknown')),input_tokens bigint,output_tokens bigint,actual_usd numeric,PRIMARY KEY(run_key,attempt_key));
CREATE TABLE sessions(session_key text PRIMARY KEY,epoch text NOT NULL,expires_at timestamptz NOT NULL);
CREATE INDEX sessions_expiry ON sessions(expires_at);
CREATE TABLE login_attempts(attempted_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE INDEX login_attempts_time ON login_attempts(attempted_at);
CREATE TABLE temporary_heads(conversation_key text PRIMARY KEY,revision bigint NOT NULL,snapshot_hash text);
DO $body$
DECLARE name text;
BEGIN
  FOREACH name IN ARRAY ARRAY['accounts','objects','sources','events','idempotency','records','tombstones'] LOOP
    EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
    EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
    EXECUTE format('CREATE POLICY owner_rows ON hcla.%I TO hcla_app USING (tenant = current_setting(''hcla.tenant'',true) AND tenant = ''hcla-owner'') WITH CHECK (tenant = current_setting(''hcla.tenant'',true) AND tenant = ''hcla-owner'')',name);
  END LOOP;
  FOREACH name IN ARRAY ARRAY['schema_version','execution','budget_policy','budget_attempts','sessions','login_attempts','temporary_heads'] LOOP
    EXECUTE format('ALTER TABLE hcla.%I ENABLE ROW LEVEL SECURITY',name);
    EXECUTE format('ALTER TABLE hcla.%I FORCE ROW LEVEL SECURITY',name);
    EXECUTE format('CREATE POLICY owner_metadata ON hcla.%I TO hcla_app USING (true) WITH CHECK (true)',name);
  END LOOP;
END $body$;
REVOKE ALL ON ALL TABLES IN SCHEMA hcla FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA hcla FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE,DELETE ON accounts,objects,sources,events,idempotency,records,tombstones,execution,budget_attempts,sessions,login_attempts,temporary_heads TO hcla_app;
GRANT SELECT ON schema_version,budget_policy TO hcla_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA hcla TO hcla_app;
-- No app path can create/reset an authorization policy. Operator installs it
-- explicitly after approving a new grant; historical exhausted grants stay closed.
COMMIT;
