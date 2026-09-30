# HCL Assistant Product Status

## Current product direction and next task

**Product design: Canonical 1.2 / A2 — Assistant-first**（本版合入main后生效）。正式采用既有Product & Interaction Design Review，不重新设计；本次只有文档和计划元数据。

**NEXT_READY: P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_READY。P0/P1实现尚未开始；当前文档执行者止于合并和exact-main核验，不修改代码。当前机器队列是 `control/plan.json.product_development`；细节见 [Development Plan](DEVELOPMENT_PLAN.md) 与 [Authority](docs/DOCUMENT_AUTHORITY.md)。

长期终局：Understand → Revise → Judge → Help → Act。**Judge = LONG_TERM_GOAL_ONLY / NOT_IMPLEMENTED_AS_GENERAL_CAPABILITY / NOT_VALIDATED / NOT_PRODUCTION_ENABLED**。未新增Judge运行时能力、已启用manifest项或agent权限。

## Implemented baseline and evidence

- physical split = COMPLETE
- repository isolation = COMPLETE at repository boundary
- Canonical source: `haohongfei2001-png/hcl-assistant/main`.
- 基线 `972234e8fdb868a51a519ba7f7c98cdb5a80583b` 已合并PR #5；对应exact-main planning检查成功，不再称L2.5仅在待合并分支。
- **L2_5_COMPLETE / L2_5_EXPERIMENTAL_RUNTIME_INTEGRATION_VERIFIED_WITH_LIMITS**：这是既有受限实现阶段，不是A2界面完成。
- L0–L2 mock基础已完成；普通UI消息仍MOCK，没有通用模型回答。Pages是独立browser-only scripted preview，无真实HCL/provider/backend。
- L2.5 pin仍为 `human-cognition-layer@a8229fcf22eccb851c58502a09ae7cecb346faf5`；interface `hcl-epistemic-callables-v1`，bridge1.0，三文件slice。只有belief_interpretation与information_access为EXPERIMENTAL；不代表一般中文、持久HCL认知或通用判断能力。
- 历史126 Python检查、build、12 headless journeys与synthetic runtime smoke的范围见 [baseline acceptance](docs/ACCEPTANCE_MATRIX_BASELINE_20261001.md)。本次不重写原回执，不将其当作Pages全部行为或A2设计验收。
- Production = NOT_ACTIVE；efficacy = NOT_TESTED；real language generalization = NOT_TESTED。

## Known unresolved product findings

当前Pages的临时持久化、仅改删除标签、1800字符静默截断、误定更正目标、模板依据与实际背景不匹配仍是待修问题；没有在文档采用中修复。详见 [Review Adoption](docs/PRODUCT_REVIEW_ADOPTION.md)。P0-01先兑现这些承诺，再做主界面重构。

## Production gate and compatibility record

L3四门槛仍未满足：I06_DISPOSITION、PINNED_PERMITTED_RUNTIME_ARTIFACT、PRODUCT_ADAPTER_SCOPE_VALIDATION、EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION。没有新增provider调用、真实数据或production activation授权。

历史L2.5阶段交接码：`STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED`。它仅禁止历史包完成后自动进入L3，不是当前全产品NEXT_READY。control/plan.json顶层legacy字段保留这一作用域；旧checker输出只验证这个阶段。新产品队列自动检查迁移为P0-01的首项工程义务，本次不修改checker或绕过CI。

采用前open PR #6为独立runtime-sync审阅工作，不是已合入能力；本次不接管、不合并。未来合并不得覆盖A2定义或当前唯一队列。
