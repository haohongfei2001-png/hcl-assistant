# HCL Assistant Product Status

**L2_5_COMPLETE / L2_5_EXPERIMENTAL_RUNTIME_INTEGRATION_VERIFIED_WITH_LIMITS**

**NEXT_READY: STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED**

- physical split = COMPLETE
- repository isolation = COMPLETE at repository boundary
- Canonical source: `haohongfei2001-png/hcl-assistant/main`. Branch checkpoints are review evidence; adoption requires exact-head CI, merge and exact-main verification.
- L0-L2 mock product is complete. L2.5 may use only pinned development runtime on synthetic/non-confirmation inputs; production activation remains NOT_ACTIVE; efficacy remains NOT_TESTED.
- Both L2.5 packages are complete on `product/l2-5-runtime-bridge`; this writer is stopped before L3. PR review/adoption remains pending. See [execution](docs/EXECUTION.md), [queue](DEVELOPMENT_PLAN.md), [acceptance](docs/ACCEPTANCE_MATRIX.md).

L2.5 bridge execution is development-only and not efficacy evidence. L3 gates remain I06 disposition, production-permitted artifact/interface, adapter scope validation and explicit execution/data authorization.

Pin: `haohongfei2001-png/human-cognition-layer@a8229fcf22eccb851c58502a09ae7cecb346faf5`; interface `hcl-epistemic-callables-v1`, bridge `1.0`. Only `belief_interpretation` and `information_access` are EXPERIMENTAL. Synthetic real-runtime E2E PASS; 126 Python checks, both root checkers, build and 12 headless browser journeys PASS locally. Mandatory exact-head hosted CI is separate adoption evidence. Provider calls = 0.
