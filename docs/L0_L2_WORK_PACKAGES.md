# L0–L2.5 Historical Package Index

**HISTORICAL SPECIFICATION — NOT THE CURRENT DEVELOPMENT QUEUE.** 十一包已在采用基线完成。原始全文按原Git blob保存在 [baseline specification](L0_L2_WORK_PACKAGES_BASELINE_20261001.md)；其中NOT_IMPLEMENTED/旧NEXT_READY/当前执行者等文字只按原始时间阅读，不覆盖 [STATUS](../STATUS.md)。

当前唯一队列见 [Development Plan](../DEVELOPMENT_PLAN.md) 和control/plan.json.product_development；新实施包见 [Product Refinement Packages](PRODUCT_REFINEMENT_WORK_PACKAGES.md)。界面以 [Master1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)/[UX A2](UX_SPEC.md)为准；例如旧disabled Compare占位要求不再决定主界面。来源/权限/修订/删除/研究与生产边界继续保留。

以下保留原包身份及依赖，便于历史checker/receipt定位，不重开包或改写证据。

## L0-01 — Canonical contracts and execution setup

历史：COMPLETE；产品契约与控制面采用。完整原规格见baseline。

## L1-01 — Event/source/state ledger

历史：COMPLETE；依赖L0-01；PROVIDER_FREE_IMPLEMENTED。

## L1-02 — Revision and historical dependencies

历史：COMPLETE；依赖L1-01；PROVIDER_FREE_REVISION_IMPLEMENTED。

## L1-03 — Privacy, expiry and correction-aware retrieval

历史：COMPLETE；依赖L1-02；PROVIDER_FREE_PRIVACY_RETRIEVAL_IMPLEMENTED。

## L1-04 — Always-on Controller and run lifecycle

历史：COMPLETE；依赖L1-03；MOCK_CONTROLLER_FUNCTIONAL。

## L2-01 — Desktop Assistant shell and text/file flow

历史：COMPLETE；依赖L1-04；MOCK_UI_FUNCTIONAL，不等于A2界面完成。

## L2-02 — Multi-session synthetic cognition and natural synthesis

历史：COMPLETE；依赖L2-01；SYNTHETIC_REPLAY_ONLY。

## L2-03 — Explain, correction and memory controls

历史：COMPLETE；依赖L2-02；MOCK_EXPLAIN_MEMORY_FUNCTIONAL。

## L2-04 — Lab shell and integrated L2 handoff

历史：COMPLETE；依赖L2-03；L2_MOCK_PRODUCT_VERIFIED_WITH_LIMITS。旧Compare占位是历史，不是A2目标要求。

## L2.5-01 — Pinned runtime bridge contract, handshake and capability discovery

历史：COMPLETE；依赖L2-04；EXPERIMENTAL_TRANSPORT_VERIFIED。

## L2.5-02 — Experimental mechanism execution and synthetic end-to-end bridge

历史：COMPLETE；依赖L2.5-01；L2_5_EXPERIMENTAL_RUNTIME_INTEGRATION_VERIFIED_WITH_LIMITS，不是production或efficacy。

完整历史验收见 [baseline acceptance](ACCEPTANCE_MATRIX_BASELINE_20261001.md)。研究/生产门槛没有因文档清理改变。
