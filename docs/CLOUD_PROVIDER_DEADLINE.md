# Bounded cloud provider deadline repair

## Observed live failure, not a successful chat

The one newly approved minimal synthetic guest verification on 2026-10-02 09:39 UTC returned UNKNOWN/wall_timeout, send_state=sent, HTTP200, requested/actual model deepseek-v4-pro, no complete answer, and 67,876ms total Controller elapsed time. The matching model identity proves a provider SSE data chunk was parsed, beyond headers alone. The earlier receipt has no numeric reasoning/answer chunk counters, so it does not prove which content phase stalled. No hidden reasoning was inspected or retained. This evidence does not retrospectively prove the previous request's error code.

Read-only budget metadata after the call: two UNKNOWN attempts, zero active requests, full total USD2.83312128 admission reservation retained. Invoice costs remain unknown. The immutable trial is 2026-10-02 08:30–12:30 UTC, shared maximum USD10. No extra provider call accompanies this code repair.

## Coupled limits

The cloud application previously cut every provider request off after60s while its durable lease lasted120s and the existing Vercel Python function allowed300s. Increasing just the adapter beyond120s would race lease recovery and publishing.

The corrected timing envelope is:

- Provider wall maximum180s; connection timeout remains10s
- Absolute provider deadline240s from application entry, before configuration/database initialization, so slow setup subtracts from available time
- Execution ownership lease270s from claim, which occurs later than application entry; it cannot expire before the absolute provider cutoff
- Existing function maxDuration remains300s, leaving60s of configured duration after the provider cutoff for bounded stop, accounting, final publication and streaming
- Expired absolute deadline refuses before constructing transport. Trial expiry, cancellation, access loss and existing publication fences may end work earlier

This is not an unlimited wait, replay, extended trial or provider-budget increase. Budget reservations, conservative UNKNOWN settlement and unconfirmed-transport concurrency blocks are unchanged. A longer bounded opportunity does not establish that the provider will finish within it. Model deepseek-v4-pro, thinking enabled, high reasoning effort and8192 completion-token ceiling remain unchanged. No new service or hosting duration is enabled.

The provider receipt adds only numeric counts of parsed JSON chunks, nonempty reasoning chunks and nonempty answer chunks. Hidden content is still immediately discarded; neither its text nor length is persisted. The display accepts fixed keys with bounded integer values only.

## Current documentation checked

- https://api-docs.deepseek.com/guides/thinking_mode/ documents thinking enabled/high and separate reasoning_content/final content. There is no tools request and no reasoning replay.
- https://api-docs.deepseek.com/quick_start/rate_limit/ documents streaming keep-alives while waiting; headers alone do not prove completion.
- https://vercel.com/docs/functions/configuring-functions/duration documents configured total function duration.
- https://vercel.com/docs/functions/streaming-functions confirms Python streaming remains bounded by function duration.

## Provider-free evidence

Virtual-clock delayed SSE tests reproduce a complete synthetic answer arriving70s after dispatch: the historical60s cutoff returns UNKNOWN;180s completes with the identical wire model/thinking/effort/token policy. Tests cover the earlier absolute deadline, setup time consumption, zero transport construction after expiry, cancellation before a delayed answer, numeric-only counters and unchanged300s platform envelope. A disposable-Postgres regression moves a claim150s forward and confirms the updated lease still owns the unfinished run; historical recovery/no-replay, trial expiry and conservative budget tests remain.

Exact-head/main CI and hosted browser tests are required. No claim of successful real chat follows from these synthetic tests.
