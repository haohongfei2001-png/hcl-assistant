# HCL Assistant Live Development Plan

Canonical: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [packages](docs/L0_L2_WORK_PACKAGES.md), [contracts](contracts/PRODUCT_CONTRACTS_V1.md).

**NEXT_READY: L2.5-01_PINNED_RUNTIME_BRIDGE_CONTRACT_AND_HANDSHAKE**

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
| L2.5-01 | pinned development runtime bridge contract, handshake and capability discovery | L2-04 | NEXT_READY |
| L2.5-02 | real-runtime serialization/lifecycle/receipts and synthetic end-to-end execution | L2.5-01 | WAITING_DEPENDENCY |

L2.5 is development-only. Use a fixed HCL commit SHA and allowlisted runtime/interface; no floating main, confirmation/evaluation material, LongMemEval, real private data, production activation or efficacy promotion. Provider-backed execution is not implied and requires separate explicit development authorization if needed.

After L2.5 completion, stop at **L3 Production Capability Activation** unless its gates are satisfied. L3 retains I06 disposition, pinned production-permitted runtime artifact/interface, product adapter scope validation and explicit execution/data authorization; it reuses transport rather than rebuilding it.
