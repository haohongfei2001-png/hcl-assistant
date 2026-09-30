# HCL Assistant Product Status

## Current product direction and next task

**Product design: Canonical 1.2 / A2-Product — Assistant-first**（本版合入main后生效）。正式采用既有Product & Interaction Design Review，不重新设计；本次只有文档和计划元数据。

<!-- CURRENT_PRODUCT_QUEUE_START -->
**NEXT_READY: P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING。唯一当前任务：P0-01。

truthful temporary/delete/stop-use/file/correction/basis contracts and current-queue checker migration。验收：R01、R02、R03、R04、R05、R06、R07

任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。
<!-- CURRENT_PRODUCT_QUEUE_END -->

当前实施状态由以上队列与各包证据共同界定。当前机器队列是 `control/plan.json.product_development`；细节见 [Development Plan](DEVELOPMENT_PLAN.md) 与 [Authority](docs/DOCUMENT_AUTHORITY.md)。

长期终局：Understand → Revise → Judge → Help → Act。**Judge = LONG_TERM_GOAL_ONLY / NOT_IMPLEMENTED_AS_GENERAL_CAPABILITY / NOT_VALIDATED / NOT_PRODUCTION_ENABLED**。未新增Judge运行时能力、已启用manifest项或agent权限。

## Implemented baseline and evidence

- physical split = COMPLETE
- repository isolation = COMPLETE at repository boundary
- Canonical source: `haohongfei2001-png/hcl-assistant/main`.
- Review原基线 `972234e8fdb868a51a519ba7f7c98cdb5a80583b` 已合并PR #5；对应exact-main planning检查成功。
- 本次合并前main由另一执行者推进到 `e2a72050e184e61f45b17de3f867419e86c658de`（PR #6）。文档采用已合并该main历史，保留全部已采用upstream-sync代码、工作流、C12契约、runtime_sync元数据与证据；不归功于本次工作。
- **L2_5_COMPLETE / L2_5_EXPERIMENTAL_RUNTIME_INTEGRATION_VERIFIED_WITH_LIMITS**：这是既有受限实现阶段，不是A2界面完成。
- L0–L2 mock基础已完成；普通UI消息仍MOCK，没有通用模型回答。Pages是独立browser-only scripted preview，无真实HCL/provider/backend。
- 采用时stable pin仍为 `human-cognition-layer@a8229fcf22eccb851c58502a09ae7cecb346faf5`；interface `hcl-epistemic-callables-v1`，bridge1.0，三文件slice。当前执行身份始终以reviewed lock为准；本次不repin。只有belief_interpretation与information_access为EXPERIMENTAL，不代表一般中文、持久HCL认知或通用判断。
- 历史L2.5的126 Python检查、build、12 headless journeys与synthetic smoke范围见 [baseline acceptance](docs/ACCEPTANCE_MATRIX_BASELINE_20261001.md)；后续upstream维护验收A30及结果见 [sync evidence](docs/RUNTIME_SYNC_EVIDENCE.md)。本次不重写原回执，不把它们当成Pages全部行为或A2设计验收。
- Production = NOT_ACTIVE；efficacy = NOT_TESTED；real language generalization = NOT_TESTED。

## Known unresolved product findings

Pages历史缺陷已在原始基线复现；P0-01修复和真实浏览器验收见 [包证据](docs/P0_01_EVIDENCE.md)。详见 [Review Adoption](docs/PRODUCT_REVIEW_ADOPTION.md)。P0-01先兑现这些承诺，再做主界面重构。

## Production gate and compatibility record

L3四门槛仍未满足：I06_DISPOSITION、PINNED_PERMITTED_RUNTIME_ARTIFACT、PRODUCT_ADAPTER_SCOPE_VALIDATION、EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION。没有新增provider调用、真实数据或production activation授权。

历史L2.5阶段交接码：`STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED`。它仅禁止历史包完成后自动进入L3，不是当前全产品NEXT_READY。control/plan.json顶层legacy字段保留这一作用域；当前checker已分别验证唯一product_development队列和旧11包/L3边界；报告明确区分两种next_ready，不放宽历史断言。

既有upstream候选测试/lock-only审阅维护继续按 [原契约](docs/RUNTIME_UPSTREAM_SYNC.md) 执行；它不是另一个feature-development NEXT_READY，不覆盖当前writer或A2方案。此文档不改变其workflow设置或生产门槛。
