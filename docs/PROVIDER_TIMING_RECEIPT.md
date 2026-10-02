# Bounded provider timing and visible failures

The ordinary task failure reported on 2026-10-02 remains undiagnosed pending its same-tab receipt. The earlier minimal synthetic success is not normal-task acceptance. This change adds observability, not a claimed repair of that unknown failure.

The existing adapter receipt now carries only fixed numeric millisecond milestones relative to transport setup start: HTTP headers, first bytes (including keepalives), first parsed JSON object event, first nonempty reasoning occurrence, first nonempty answer occurrence, last parsed object event, and time since that last event at termination. They are observations, not token counts or measurements of provider compute/queue time. Partial SSE frames become events only once parsed. Event times are captured before queue backpressure; multiple events in one read share its observation time.

Absent milestones remain absent, never zero. Observed zero is valid. Cancellation before send has no transport milestones. A HTTP rejection can have only a headers milestone. Keepalives can show bytes without data events. Malformed protocol, deadlines and cancellation retain only already observed metrics. Last-event age is captured before bounded worker shutdown, so shutdown delay is not labeled a streaming stall. Hidden reasoning is still discarded; neither raw headers, exception strings nor private content enters metrics.

The failed chat card shows the same allowlisted reason, send state and total duration as its receipt, with an explicit no-automatic-repeat and unknown-cost notice. An unknown cause remains unknown. More retains the complete receipt with counts and timing. Existing model, high thinking, token ceiling, absolute deadlines, cancellation fences, reservations and tenant boundaries are unchanged. No model calls were made for this batch.

Provider-free checks cover distinct virtual-clock header/keepalive/reasoning/answer times, cancellation before send, HTTP rejection, keepalive-only early EOF, numeric allowlist validation and visible safe failure summaries. Existing cloud browser timeout journey now requires the reason directly on the failed card, reasoning timing in the receipt and no invented first-answer time. Exact-head and exact-main hosted acceptance are required before adoption.

Local validation: 395 Python tests passed (60 database-only cases skipped locally), 42 view tests passed, TypeScript/build/preview guard and repository/planning checks passed. Hosted database and browser checks remain required.
