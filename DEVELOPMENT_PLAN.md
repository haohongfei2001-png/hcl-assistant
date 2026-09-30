# HCL Assistant Live Development Plan

Canonical: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [packages](docs/L0_L2_WORK_PACKAGES.md), [contracts](contracts/PRODUCT_CONTRACTS_V1.md).

**NEXT_READY: L1-02_REVISION_HISTORICAL_DEPENDENCIES**

| ID | Delta | Dependencies | State |
|---|---|---|---|
| L0-01 | canonical contracts and setup |  | COMPLETE |
| L1-01 | event source state ledger | L0-01 | COMPLETE |
| L1-02 | revision and historical dependencies | L1-01 | NEXT_READY |
| L1-03 | privacy expiry and correction-aware retrieval | L1-02 | WAITING_DEPENDENCY |
| L1-04 | always-on controller and run lifecycle | L1-03 | WAITING_DEPENDENCY |
| L2-01 | desktop chat and text file flow | L1-04 | WAITING_DEPENDENCY |
| L2-02 | multi-session synthetic cognition and natural synthesis | L2-01 | WAITING_DEPENDENCY |
| L2-03 | Explain correction and memory controls | L2-02 | WAITING_DEPENDENCY |
| L2-04 | Lab shell and integrated mock acceptance | L2-03 | WAITING_DEPENDENCY |

Sole writer: `product/l1-01`, sequential L1/L2 checkpoints in one coherent PR. Latest package evidence: PROVIDER_FREE_IMPLEMENTED. Actual SHA validation is recorded by CI, not fabricated in live state.

L3 remains gated: I06 disposition, pinned permitted runtime artifact/interface, product adapter scope validation, explicit execution and data authorization. Do not enter L3.
