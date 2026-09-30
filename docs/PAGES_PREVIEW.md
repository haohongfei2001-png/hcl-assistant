# GitHub Pages synthetic preview — existing surface, not canonical UX

Public preview: `https://haohongfei2001-png.github.io/hcl-assistant/`.

The existing surface is browser-only static HTML/CSS/JavaScript: no Python API, SQLite service, SSE backend, provider transport, real HCL runtime, server-side authentication/persistence, research/confirmation/LongMemEval/protected data or credentials. Scripted output is not general semantic understanding. **Do not enter real private data.**

## Known implementation limits, not fixed by A2 documentation

At baseline `972234e8`, `save()` persists the entire conversation collection in localStorage, including the currently labelled TEMPORARY path. DELETE changes a record status without clearing all body/run copies. File upload uses only the first 1800 characters. Correction detection may treat a negation as a correction and replace the latest active record. `synthesize(text)` can claim background basis without actually reading persistent context.

These findings are static-code observations, not new browser-test claims. They are tracked in [Review Adoption](PRODUCT_REVIEW_ADOPTION.md) and assigned to P0-01. Do not infer that the local Controller/SQLite tests certify these independent Pages behaviors; do not promise temporary/deletion/complete-reading semantics until they are implemented or the misleading control is explicitly removed.

## Target and development boundary

Target interaction is solely [Master 1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [UX A2](UX_SPEC.md) and [Visual System](VISUAL_SYSTEM.md). This current page and screenshot are not authority for navigation or information architecture. Keep one honest environment notice, but move technical metadata and Lab out of ordinary conversation focus.

Next task is `P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR`; only then proceed to the shared Assistant-first shell. Sharing UI/contracts must not add backend/provider/real HCL to this browser-only surface or create a second inconsistent memory implementation.

Legacy `STOP_WITH_HANDOFF_L3_GATED` and `STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED` references describe production gates, not the current product refinement queue. L3/I06 gates remain unsatisfied; no real data, provider calls, efficacy claims, Judge or agent activation is authorized.
