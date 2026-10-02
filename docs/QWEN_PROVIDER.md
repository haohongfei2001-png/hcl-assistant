# Beijing Qwen provider preparation

Current activation target: [the approved monthly owner budget](QWEN_MONTHLY_BUDGET.md).
The separate one-call funding examples below are historical preparation only;
first smoke and ordinary owner use now share CNY500 per Shanghai calendar month.

## Authority and activation state

Owner requested HCLA-only integration on 2026-10-02: Alibaba Cloud Model Studio,
China North 2 (Beijing), pay-as-you-go, exact API model `qwen3.8-max`.
HCL research/tests are explicitly out of scope. This package implements offline
code and a separately reviewable additive schema. It installs no live grant,
credential, account, resource or schema; it does not call or activate a provider.
The existing expired DeepSeek guest trial cannot authorize Qwen.
This slice targets the hosted HCLA cloud entry; the legacy local USD launcher
explicitly refuses Qwen selection rather than silently calling DeepSeek.

Missing `HCLA_PROVIDER` preserves the existing DeepSeek configuration behavior.
Selecting `qwen` without an explicit Qwen grant is disabled, even with a key.
Legacy DeepSeek grants, default cloud activation and trial-window variables are
refused with Qwen selection. There is no automatic fallback or retry.

## Official contract checked 2026-10-02

- Exact model: `qwen3.8-max`, not a guessed alias or automatically chosen snapshot.
- Beijing pay-as-you-go uncached input CNY12 / million tokens; output CNY36 /
  million tokens. No cache, batch or promotion discount is assumed. These are
  dated floor rates; recheck the account's official prices before activation.
- Wire: OpenAI-compatible Chat Completions SSE, text messages only, one choice,
  `stream=true`, `stream_options.include_usage=true`, `enable_thinking=true`,
  `reasoning_effort=xhigh`. This model's documented native effort choices are
  low/medium/xhigh. Do not copy a DeepSeek `thinking` object or simultaneously
  send `thinking_budget` with effort.
- Use `max_completion_tokens` for the combined thinking + answer output cap.
  The documented possible ten-token deviation is included in admission
  reservation and usage verification. Supported wire cap is 1–131072.
- The full documented 1,000,000-token context is reserved conservatively.
  Product prompts remain capped at 8192 UTF-8 serialized bytes including context
  and framing. The adapter separately verifies the final serialized HTTP JSON
  body is at most8192 bytes before transport. Oversized Qwen history is refused,
  never pruned to fit. This does not claim that byte count is an official tokenizer.
- Only `https://dashscope.aliyuncs.com/compatible-mode/v1` or a valid single
  workspace-label Beijing `https://<workspace>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
  may receive the key. No redirects, arbitrary path, other region, query,
  credentials-in-URL, nonstandard port or HTTP is permitted. Regional keys must
  match the endpoint. The old Beijing domain remains officially supported.

Primary sources:
- https://help.aliyun.com/zh/model-studio/qwen3-8-max
- https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions
- https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope
- https://help.aliyun.com/zh/model-studio/deep-thinking

## Completion and privacy

The existing bounded transport enforces 10s connect, 180s cloud provider wall,
240s absolute provider cutoff, 270s lease and existing 300s Vercel function limit.
Only final text is provisional-streamed; reasoning text is immediately discarded,
never stored, displayed or replayed. Numeric usage/counters are allowed.

Exact returned model, final `[DONE]`, nonempty answer and `finish_reason=stop`
remain required. Length-limited, missing-finish, cancelled, early-EOF and uncertain
transport outcomes are not relabeled completed. Qwen additionally requires
consistent usage and prompt/completion counts within the reserved bounds. Missing
usage or cap violations withhold the provisional answer as UNKNOWN. Failed and
unknown attempts retain the full reservation. There is no inferred zero invoice.

No tools, search, native DashScope/Responses API, audio or image inputs are enabled
by the model's broader advertised capabilities. HCL runtime locks, temporary tab
memory, persistent history/tenant isolation and synthetic-only consent are unchanged.

## Separate CNY authorization and data

The additive migration creates only `hcla.qwen_budget_policy`,
`hcla.qwen_budget_attempts`, `hcla.qwen_member_entitlements` and
`hcla.qwen_member_budget_attempts`. It creates no policy rows, entitlements,
secrets, new roles or public access. App-role policy/entitlement writes are denied.
Member rows are tenant-isolated with forced RLS. The global CNY ceiling and the
member CNY ceiling are checked in the same serialized transaction.

All legacy USD policy/attempt/history and expired trial rows remain untouched.
The migration adds admission triggers to the old attempt tables, without rewriting data.
No USD authorization is transferred or converted. Active/unconfirmed dispatches
on either provider block the other provider in this reviewed code. Successful lower usage does not
refund reservation capacity. Raw output/usage receipts do not replace an invoice.

Qwen supports authenticated owner and separately entitled member routes. This
package does not create a new anonymous guest-trial entitlement or extend the old
trial clock. An explicit later trial request requires its own bounded design.

## Operator handoff after review

Use the existing authorized HCLA Vercel project, not a new project:

1. The owner enters the existing Beijing API key directly in Vercel's secure
   Environment Variables interface as `HCLA_QWEN_API_KEY`, scoped only to the
   approved deployment environment. Never send the key in chat, git, logs,
   screenshots, frontend variables or the browser's storage. Key entry alone
   does not activate this implementation.
2. After explicit approval of a CNY ceiling, request count and total-output cap,
   the operator prepares `HCLA_QWEN_MODEL_GRANT` with exactly these non-secret
   fields: provider (`qwen`), model (`qwen3.8-max`), region (`cn-beijing`), currency
   (`CNY`), base_url, budget_id (new `hcla-qwen-cny-...` identity), max_requests
   (integer), max_cost_cny (decimal string), input_cny_per_million (decimal string),
   output_cny_per_million (decimal string), max_completion_tokens (integer).
3. The offline `scripts/print_qwen_budget_policy.py --approved-grant '<JSON>'`
   helper validates this contract and prints metadata only. It never installs it.
   Apply the additive migration and matching immutable Qwen policy only after
   separate approval. Never overwrite or reset the old USD policy/attempts.
4. Only then select `HCLA_PROVIDER=qwen` on the approved deployment. Do not leave
   legacy `HCLA_MODEL_GRANT`, `HCLA_CLOUD_PROVIDER_ENABLED=true`, or
   `HCLA_TRIAL_WINDOW` alongside it. Member spending additionally needs a newly
   approved CNY member entitlement; existing USD entitlements do not grant it.
   Verify old active-attempt metadata before cutover. The migration adds a
   SECURITY INVOKER trigger under the existing transaction advisory lock. Once
   an explicitly approved Qwen policy row exists, new legacy HCLA USD/trial
   reservations are rejected by the database, including from pre-Qwen binaries.
   Existing legacy requests may settle; Qwen remains blocked while any old
   reservation is active. With no Qwen policy row, migration alone does not
   disable legacy admission. Do not revoke the shared DeepSeek API key or change
   HCL core. Do not clear an active/unknown reservation just to pass this gate.
5. Redeploy only when authorized, verify non-secret configuration, then use only
   the explicitly approved synthetic smoke input/call count. A deploy/readiness
   check must not implicitly call the model. No auto retry follows failure.

This document contains no live grant. Finite illustrative reservation: a 4096
total-output cap reserves 4106 output tokens plus 1,000,000 input tokens, or
CNY12.147816 at the listed floors. A rounded CNY13/one-call approval would cover
that worst-case reservation. This is deliberately a whole-context worst case,
not expected cost, an invoice or purchase approval. No unverified tokenizer
heuristic replaces the bound.

Suggested original synthetic HCLA smoke, only after separate approval: input
`Mira said, "I believe that the team meeting was moved to Thursday."`; query
`What does Mira believe, and does this establish the actual meeting date?`.
Run through the pinned `belief_interpretation` preparation with its existing
SYNTHETIC_NON_CONFIRMATION/ORIGINAL_PRODUCT_SYNTHETIC contract, temporary scope,
one Qwen dispatch,4096 combined output tokens and no automatic retry. The offline
test verifies actual provider-free HCL preparation plus fake Qwen completion,
source binding and no reasoning retention. It does not establish live efficacy.

## Verification

`tests/test_qwen_provider.py` covers the wire contract, exact endpoint, secret and
reasoning non-retention, missing/malformed/over-limit usage, cancellation, no
fallback, default-disabled selection, immutable native-CNY policy, no-refund
budget and Controller publication. `tests/test_qwen_postgres.py` uses only the
existing disposable localhost test database to verify concurrent admission,
cross-provider fences, policy immutability and member RLS/accounting. A skipped
Postgres test is unverified, not a pass. All provider tests use synthetic transports.

## Optional one-call owner smoke restriction

For the first smoke, the non-secret grant additionally contains `smoke` with
exactly `scope: OWNER_ONLY_SYNTHETIC_SMOKE`, `input_sha256`, and `query_sha256`.
The fingerprints identify the exact UTF-8 source and query above. This requires
max_requests=1 and a fresh TEMPORARY request at state version0 through the existing
belief_interpretation contract. Uploads, other text/query, older conversation state
and persistent conversations are rejected before admission. Member execution and
member model-availability status remain disabled even if member entitlement rows
exist. No anonymous guest route is opened. The normal authenticated owner route
is required; no secret-bearing test endpoint or auth bypass is added.

The server resolves and checks `model_resource_policy.adapter=QWEN` for Qwen;
explicit DEEPSEEK-only requests cannot silently change provider. Status and UI
carry the selected provider, and the advanced Qwen sample uses the exact original
Mira source/query. Key-only/default-disabled Qwen does not claim a live model.

## Local validation checkpoint

Original synthetic transports only, no live keys or provider calls. Full Python
suite and focused Qwen/controller/DeepSeek regressions pass in the cloud checkout;
PostgreSQL tests are explicitly skipped locally because no disposable server is
configured. Build, TypeScript,42 JS view tests and both repository checks pass.
The local Playwright run is infrastructure-blocked: bundled browser absent; the
installed Chromium aborts on sandbox socket permission/read-only-profile errors.
This is not a browser-test pass. Exact-head CI includes the complete browser suite
(including two Qwen UI tests) and four new real-Postgres Qwen tests; those remain
adoption gates. Additive live migration and activation remain unapproved/unrun.
