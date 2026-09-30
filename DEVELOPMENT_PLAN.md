# HCL Assistant Live Development Plan — Canonical 1.2

唯一产品方案：[Master Plan 1.2](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](docs/UX_SPEC.md)、[Visual](docs/VISUAL_SYSTEM.md)。权威分工见 [Document Authority](docs/DOCUMENT_AUTHORITY.md)。本文件是唯一live产品开发队列，机器投影为 `control/plan.json.product_development`。

<!-- CURRENT_PRODUCT_QUEUE_START -->
**NEXT_READY: P1-02_REVISION_EVIDENCE_MEMORY_LOOP**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING。唯一当前任务：P1-02。

revision/change/evidence/source/history/memory control loop。验收：R13、R14、R15、R16

任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。
<!-- CURRENT_PRODUCT_QUEUE_END -->

## 1. 唯一当前任务

以上机器投影是当前唯一任务，具体scope、正负测试和完成判据见 [当前工作包](docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md)。依赖按顺序推进；不能把旧L3停止码当成产品全局停止，不能越过P0直接换皮。

当前checker/reporting/advance消费product_development，严格保留历史11包与L3/研究边界。包完成须实际验收；没有一般语义能力时明确不支持，不堆关键词冒充理解。每包在独立PR中接受exact-head审查/CI与exact-main核验后才采用。

## 2. 依赖顺序

| ID | Delta | Dependencies | State |
|---|---|---|---|
| P0-01 | truthful preview contracts + current-queue checker migration | Canonical1.2合入main | COMPLETE |
| P1-01 | shared Assistant-first home/chat shell、视觉与输入/阅读体系 | P0-01 | COMPLETE |
| P1-02 | revision/change/Explain/source/history/memory闭环 | P1-01 | NEXT_READY |
| P1-03 | bounded Inspect/Settings、Continuum V1视觉还原与整体synthetic验收 | P1-02 | WAITING_DEPENDENCY |

工作包定义见 [Product Refinement Packages](docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md)，验收R01–R20见 [Acceptance Matrix](docs/ACCEPTANCE_MATRIX.md)。表中状态按当前机器队列投影；设计采用本身不填PASS。不按PR数量衡量进展，不重新选择并列产品方案。

当前全部整改仅synthetic/provider-free、max_provider_calls=0、real_private_data_allowed=false、production_activation_allowed=false。Judge与Act不在当前开发包中。

## 3. 历史阶段与已采用维护

L0–L2.5十一包继续COMPLETE，原delta与证据不变；[historical index](docs/L0_L2_WORK_PACKAGES.md) 和byte-identical baseline保留原规格，不能从其中NOT_IMPLEMENTED/旧next恢复待办。

历史L2.5阶段交接码为 `STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED`。control/plan.json顶层phase=L2_5_COMPLETE、旧packages/next字段仍只记该阶段和L3边界，以保持旧checker/test不被本次文档变更重写；它不再是全产品调度指令。唯一当前next在product_development。旧自动报告覆盖不足已记录，P0-01须补齐，不宣称旧checker已验证新队列。

PR #6在本次采用期间已由另一执行者合入 `e2a72050e184e61f45b17de3f867419e86c658de`。既有hourly/manual exact upstream candidate testing与reviewed lock-only repin维护按 [sync contract](docs/RUNTIME_UPSTREAM_SYNC.md) 和 [evidence](docs/RUNTIME_SYNC_EVIDENCE.md) 保留。该维护不是第二套产品方案或待开发feature，不改变P0优先级、当前writer、stable-lock/来源/CI/生产门槛。同步实现与C12原样继承；本次不执行repin、不新增其授权。

## 4. L3与长期路线

完成P1-03后，L3门槛未满足则停止交接，不造填充功能。门槛仍为I06 disposition、固定获准production runtime/interface、产品adapter scope验证、明确执行/数据授权；L2.5成功不自动满足。

后续门槛满足时，先真实普通聊天与本会话持续理解/自然更正，再明确授权的项目内跨对话；更后才扩展获准工具和Act。Understand → Revise → Judge → Help → Act是长期价值链，不是当前五个模块。Judge仅长期目标，不因main_judgment字段、条件检查或mock文本而视作实现。

## 5. Writer与合并

执行者先读最新main/open PR/AGENTS，只有一个implementation writer。重叠控制文档须协调到Canonical1.2后再合并，不能恢复第二套队列或覆盖已采用维护。

每个实施包提供实际delta、正负/修订/持久化/browser证据、exact-head CI；合并后检查exact-main，再同步Status、此文件与product_development。代码、权限或实测未支持的内容保留未实现，不用描述代替验证。本次文档执行者在合并核验后停止。

## 6. Continuum V1 增量，不另建队列

最新批准的三张界面稿和两张形象稿见 [设计采用目录](docs/design/continuum-v1/README.md)。正式采用须完整原图入库核验及原有审查/合并门槛，缺图的草稿不授权启动新视觉实施。

本次读取基线 fa2cd0bf 已完成 P0-01/P1-01，P1-02 由 PR #10 的现有 implementation writer 推进。保留其代码、回执和依赖；本次不认领任何 implementation 包，不覆盖 writer 元数据。若 main 在采用前前进，重读并保留新完成状态，不把本文件的读取基线投影覆盖回去。

新视觉工作归入尚未完成的 **P1-03**，按 V1-A 共享外观/首页/长对话 → V1-B 依据/来源/修订/锚点返回 → V1-C 双形象/响应式/Inspector与Settings/整体截图及交互验收推进。三切片范围、参考图和验收条件在 [P1-03包定义](docs/PRODUCT_REFINEMENT_WORK_PACKAGES.md#continuum-v1p1-03-内的三个依赖交付切片) 中；切片不是另外的 NEXT_READY、独立队列或并行 writer。

P1-03 原 R17–R20 义务不减少，新增 V01–V10 从属于 R19/R20。原四包任务ID、依赖、验收数组、机器 product_plan_version 和 L3 停止条件保持不变，避免本次文档变更要求修改 checker/tests/workflow。checker 的通过不证明视觉还原：实际页面与五张原稿对照、关键操作录像、偏差登记仍须逐项审阅。

两形象 M-01/M-02 均保留，未定唯一品牌不阻塞共同界面。图稿中的示例事实、引用、文件/搜索/模型/agent按钮不能增加当前能力。所有阶段维持 synthetic/provider-free/no-private-data 边界；完成视觉不自动进入 L3。
