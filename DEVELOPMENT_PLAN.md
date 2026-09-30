# HCL Assistant Live Development Plan

Canonical: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [packages](docs/L0_L2_WORK_PACKAGES.md), [contracts](contracts/PRODUCT_CONTRACTS_V1.md).

**NEXT_READY: STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED**

| ID | Delta | Dependencies | State |
|---|---|---|---|
| L0-01 | canonical contracts and setup |  | COMPLETE |
| L1-01 | event source state ledger | L0-01 | COMPLETE |
| L1-02 | revision and historical dependencies | L1-01 | COMPLETE |
| L1-03 | privacy expiry and correction-aware retrieval | L1-02 | COMPLETE |
| L1-04 | always-on controller and run lifecycle | L1-03 | COMPLETE |
| L2-01 | desktop chat and text file flow | L1-04 | COMPLETE |
| L2-02 | multi-session synthetic cognition and natural synthesis | L2-01 | COMPLETE |
| L2-03 | Explain correction and memory controls | L2-02 | COMPLETE |
| L2-04 | Lab shell and integrated mock acceptance | L2-03 | COMPLETE |
| L2.5-01 | pinned development runtime bridge contract handshake and capability discovery | L2-04 | COMPLETE |
| L2.5-02 | real-runtime serialization lifecycle receipts and synthetic end-to-end execution | L2.5-01 | COMPLETE |

Both L2.5 packages are adopted through PR #5; the sole upstream-sync maintenance writer stops before L3. Latest package evidence: L2_5_EXPERIMENTAL_RUNTIME_INTEGRATION_VERIFIED_WITH_LIMITS. Actual SHA validation is recorded by CI, not fabricated in live state.

L2.5 is development-only. After it completes, L3 remains I06-gated Production Capability Activation and reuses the bridge transport.

Authorized maintenance: hourly/manual exact upstream candidate testing and reviewed runtime repins, using the existing L2.5 bridge. This does not add or change a package boundary. See [sync contract](docs/RUNTIME_UPSTREAM_SYNC.md) and [evidence](docs/RUNTIME_SYNC_EVIDENCE.md).
