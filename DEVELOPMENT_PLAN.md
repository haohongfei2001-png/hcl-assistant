# HCL Assistant Live Development Plan — A2

唯一产品方案：[Master Plan 1.2](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](docs/UX_SPEC.md)、[Visual](docs/VISUAL_SYSTEM.md)。权威分工见 [Document Authority](docs/DOCUMENT_AUTHORITY.md)。本文件是唯一live队列，机器投影为 `control/plan.json.product_development`。

**NEXT_READY: P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**

## 1. 唯一当前任务

先兑现预览中的临时、删除、不再使用、完整读取、更正与依据承诺，不先换皮、不进入L3、不实现Judge。具体scope、正负测试和完成判据见 [P0-01](docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md#p0-01--truthful-preview-contract-repair)。

P0-01先迁移当前队列的checker/reporting/tests与消费者，再修对应surface的真实行为。自动调度不能继续读取legacy next字段；历史11包、生产/隐私/研究边界仍须严格验证。没有一般语义能力时明确不支持，不继续堆关键词脚本冒充理解。

本次A2文档执行者仅采用文档与计划元数据；implementation_started=false。下一位implementation Work明确认领后才写代码，不将本次“写入方案”解释成启动实施。

## 2. 依赖顺序

| ID | Delta | Dependencies | State |
|---|---|---|---|
| P0-01 | truthful preview contracts + current-queue checker migration | A2合入main | NEXT_READY |
| P1-01 | shared Assistant-first home/chat shell、视觉与输入/阅读体系 | P0-01 | WAITING_DEPENDENCY |
| P1-02 | revision/change/Explain/source/history/memory闭环 | P1-01 | WAITING_DEPENDENCY |
| P1-03 | bounded Inspect/Settings与整体synthetic验收 | P1-02 | WAITING_DEPENDENCY |

工作包定义见 [Product Refinement Packages](docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md)，验收R01–R20见 [Acceptance Matrix](docs/ACCEPTANCE_MATRIX.md)。所有新增包NOT_IMPLEMENTED；设计采用不填PASS。不按PR数量衡量进展，不重新选择五套产品方案。

当前全部整改仅synthetic/provider-free、max_provider_calls=0、real_private_data_allowed=false、production_activation_allowed=false。Judge与Act不在当前开发包中。

## 3. 历史阶段不是另一套live队列

L0–L2.5十一包继续COMPLETE，原delta与证据不变；[historical index](docs/L0_L2_WORK_PACKAGES.md) 和byte-identical baseline保留原规格，不能从其中NOT_IMPLEMENTED/旧next恢复待办。

历史L2.5阶段交接码为 `STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED`。control/plan.json顶层phase=L2_5_COMPLETE、旧packages/next字段仍只记该阶段和L3边界，以保持旧checker/test不被本次文档变更重写；它不再是全产品调度指令。唯一当前next在product_development中。旧自动报告覆盖不足已明确记录，P0-01须补齐，不宣称旧checker已验证新队列。

## 4. L3与长期路线

完成P1-03后，L3门槛未满足则停止并交接，不造填充功能。门槛仍为I06 disposition、固定获准production runtime/interface、产品adapter scope验证、明确执行/数据授权；L2.5成功不自动满足。

后续门槛满足时，先真实普通聊天与本会话持续理解/自然更正，再明确授权的项目内跨对话；更后才扩展获准工具和Act。Understand → Revise → Judge → Help → Act是长期价值链，不是当前五个模块。Judge仅长期目标，不因main_judgment字段、条件检查或mock文本而视作实现。

## 5. Writer与合并

执行者先读最新main/open PR/AGENTS，只有一个implementation writer。当前open runtime-sync PR不因文档采用被接管或合并；重叠控制文档须协调到A2后再合并，不能恢复第二套队列。

每个实施包提供实际delta、正负/修订/持久化/browser证据、exact-head CI；合并后检查exact-main，再同步Status、此文件与product_development。代码、权限或实测未支持的内容保留未实现，不用描述代替验证。本次文档执行者在A2合并核验后停止。
