"""Bounded timing inside the existing 300-second serverless function."""
# Keep the reviewed thinking/high model and token cap; no retries or grant changes.
PROVIDER_WALL_SECONDS = 180
REQUEST_PROVIDER_DEADLINE_SECONDS = 240
EXECUTION_LEASE_SECONDS = 270
# The absolute provider cutoff starts before application/DB setup, leaving at
# least 60 seconds of configured platform duration for settlement and streaming.
# Claim happens later, so its lease cannot expire before that provider cutoff.
