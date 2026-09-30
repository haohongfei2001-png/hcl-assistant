# Document Authority and Supersession — Canonical 1.2

生效条件：本次文档采用合入 `haohongfei2001-png/hcl-assistant/main`。采用来源为Owner明确确认的Product & Interaction Design Review及长期Understand → Revise → Judge → Help → Act。没有第二套可选产品方案。

## 1. 唯一权威方案的分工

| 文件/位置 | 唯一职责 |
|---|---|
| [Master Plan 1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md) | 最终产品定义、Assistant-first、功能分层、架构、MVP与终局 |
| [UX Spec](UX_SPEC.md) | 同一方案的主流程与九个视图 |
| [Visual System](VISUAL_SYSTEM.md) | 同一方案的视觉tokens与行为 |
| [Development Plan](../DEVELOPMENT_PLAN.md) | 唯一当前开发任务、依赖与停止条件 |
| `control/plan.json.product_development` | 上述唯一当前开发队列的机器投影，不是另一套计划 |
| [Status](../STATUS.md) | 当前实现与证据事实，不由计划倒推能力 |
| [Product Contracts](../contracts/PRODUCT_CONTRACTS_V1.md) | API/数据/权限/运行回执语义，包括已采用C12；不是前台导航模板 |
| [Acceptance Matrix](ACCEPTANCE_MATRIX.md) | 当前R01–R20待实现义务与历史A01–A30证据分离 |
| [Review Adoption](PRODUCT_REVIEW_ADOPTION.md) | 本次基线、缺陷及采用历史，不是修复完成报告 |
| [Upstream Sync](RUNTIME_UPSTREAM_SYNC.md) / [Sync Evidence](RUNTIME_SYNC_EVIDENCE.md) | 已采用固定runtime维护边界与证据；不是产品定义或另一feature队列 |

Remote main代码、exact-SHA CI、reviewed runtime lock与原始回执是实现事实。产品/UX/视觉冲突以本版为准，但不能覆盖来源、权限、删除、研究隔离、runtime维护安全或生产激活门槛。队列镜像不一致须停止认领并同步，不能挑有利文档执行。

### Amendment标识的并发消歧

PR #6曾将其维护条款命名“Canonical Amendment A2 — verified upstream pin maintenance”。本Review在并发分支也使用A2。为避免两个不同含义的A2竞争：本次产品方案完整身份为 **Canonical 1.2 / A2-Product**，本文件体系中的简写A2均指该Product Review；先前runtime条款称 **UPSTREAM_SYNC_MAINTENANCE / PR6**，其全部非冲突语义继续由C12、RUNTIME_UPSTREAM_SYNC和runtime_sync元数据承载并纳入当前权威体系。编号消歧不撤销既有维护授权，不是新的产品方案。

## 2. control/plan.json作用域迁移

旧checker硬编码11个L0–L2.5包和完成后L3停止码。本次只能改文档/计划元数据，不改checker/tests、不忽略失败CI。

顶层phase/packages/next_package_id/next_ready/current_executor_stop_after/future_work_allowed_through明确保留为 **LEGACY_L0_L2_5_STAGE_COMPLETION_AND_L3_GATE_ONLY**。其中STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED只表示历史包完成不得自动进入L3，不表示全部产品整改停止。旧包完成/证据/生产门槛不改，不伪造重开包迎合checker。

当前唯一产品开发队列是 **product_development**；Status和Development Plan只镜像其中的next_ready。顶层legacy字段及旧CI输出不是第二候选任务。runtime_sync是已采用的维护配置，不是新的产品队列。

A2文档采用时标注automation_support=LEGACY_STAGE_CHECKS_ONLY_CURRENT_QUEUE_MANUALLY_REVIEWED；当时旧检查不覆盖新队列。P0-01现已将checker/reporting/tests/advance迁移为CURRENT_PRODUCT_QUEUE_AND_LEGACY_SAFETY_CHECKED，验证完整当前摘要/next/状态镜像与依赖，并继续严格验证旧11包与四个L3门槛。未适配消费者仍不得基于legacy字段新调度。已采用runtime维护继续遵从其独立固定锁、writer/main冲突和CI检查，不由此扩大权限或替产品排第二个下一任务。

这是显式兼容迁移，不放宽断言或绕过CI；实际代码和验证见 [P0 evidence](P0_01_EVIDENCE.md)。

## 3. 旧冲突设计处置

| 旧要求/位置 | 处置 |
|---|---|
| Master1.0/1.1与UX v1冲突的默认呈现 | 当前Master/UX/Visual替代，旧版本仅历史 |
| 左栏常驻Topic/范围、Advanced、标题前记忆管理 | 按需项目、当前范围、记忆入口替代 |
| 每轮route/version/MOCK/Lab主按钮 | 下沉；真实环境标识仍保留 |
| Lab主导、Case-first、常驻图谱、Base/HCL或强度滑块 | 排除，不可自行恢复为并列变体 |
| L2-04 disabled Compare按钮 | 历史事实保留，新主体验去掉占位；Lab说明真实门槛 |
| 人际/概念/责任首页分类 | 内部验证场景，对外通用助手 |
| 人格分/心理诊断/永久第三方画像列入Later | 排除，不与移动/语音/获准工具混列 |
| stale review-branch/下一步L2.5文字 | 由PR5/PR6已合入事实及当前Status替代 |
| [L0–L2.5 Packages](L0_L2_WORK_PACKAGES.md) | 历史索引，全文存档，不是当前待办 |
| [Baseline Acceptance](ACCEPTANCE_MATRIX_BASELINE_20261001.md) | 原A01–A29保留，只证当时synthetic范围；A30另由sync evidence保留 |
| Execution、迁移/研究基线 | 历史provenance；旧NEXT_READY/NOT_IMPLEMENTED不覆盖live文件 |
| Pages文档/截图/当前代码 | 现存受限实现与反例，不决定目标IA |
| 研究仓库旧products/hcl-assistant副本 | 退役，不在那里开发或维护双队列；本次不修改研究仓库 |
| 尚未合并分支文档 | 不覆盖main，合并前协调到唯一产品方案 |

## 4. 历史保留与并发合并

L0_L2_WORK_PACKAGES_BASELINE_20261001.md、ACCEPTANCE_MATRIX_BASELINE_20261001.md使用产品972234e8对应原blob字节不变。历史“当前/next/NOT_IMPLEMENTED/PASS”按原时间范围阅读。不删失败、不改分、不升级mock。

执行期间另一写入者将PR #6合入main e2a72050。此次在最新main树上仅重新应用文档/计划差异，并把该main作为合并父提交，保留其所有应用、脚本、测试、workflow、C12、runtime维护文档/证据和runtime_sync字段。Stable lock不改。Git compare以e2a72050为新的直接基线；不得将继承的代码归为本次实现。

原始head2cbfc524的通过只属于该head；协调后的新head及最终main必须分别验证。当前唯一下一项仍P0-01，不因为继承维护实现转向repin、L3或Judge。

## 5. Continuum V1 视觉增量的权威与采用门槛

以上第4节的“当前/下一项”只记录 A2 原采用时点；全局下一项始终来自最新 product_development，不恢复 P0-01。此次视觉采用读取基线为 main `fa2cd0bfac7cc392fb886544acfdc95038d9d678`：P0-01/P1-01 已完成，P1-02 有独立 writer 的 PR #10；本次不覆盖该 writer、不接管其代码、不将未合入实现写成完成。

| V1 位置 | 权威范围 |
|---|---|
| [Design Adoption](design/continuum-v1/README.md) / [manifest](design/continuum-v1/asset-manifest.json) | Owner 最新批准的五张原图、原始身份/校验值、采用条件和示例语义例外 |
| UI-01 / UI-02 / UI-03 原稿 | 首页、对话与依据/修订的目标布局、配色、光感和材质；不是能力或事实证据 |
| M-01 / M-02 原稿 | 两个并存数字形象候选；未选唯一方案，不阻塞共同界面 |
| [Implementation Spec](design/continuum-v1/IMPLEMENTATION_SPEC.md) | UX/Visual 的组成部分，补齐静态图的组件、响应式、键盘、异常、动效和锚点返回 |
| [Visual Acceptance](design/continuum-v1/ACCEPTANCE.md) | R19/R20 下 V01–V10 的实际截图/交互演示/偏差记录要求；不伪称已自动验收 |

五张原图未完整入库核验时，PR 保持草稿且不可合并；仅有 manifest、文字规范或本地副本不构成仓库资产完成。正式采用需所有原图与 manifest 匹配、最新 main/并行 PR 协调、exact-head 审阅/CI、合入和 exact-main 核验。采用后它们替代冲突的旧暖白灰绿编辑器视觉，旧 visual 原字节保留为历史 baseline，不作为可选方案。

优先级按作用域：产品架构/权限/来源/研究与生产门槛始终高于图内示例；目标外观以五张批准稿和 Visual 为准；静态图未表达的行为以 UX/V1 Implementation 为准；事实只来自 exact-SHA 代码/回执；队列只来自 product_development。图片里的企业、引用、PDF按钮或智能体不是新授权，语义替换须显式记录但不能变成任意换皮。

机器 `product_plan_version` 保持 `1.2/A2-Product`；不为视觉采用修改 checker/tests/workflows 的硬编码四包结构。三个 V1 交付切片从属既有 P1-03，不持有独立 NEXT_READY 或执行者，不构成第二队列。其原 R17–R20 义务和全部既有回归仍适用，新增 V 验收必须有实际证据。

任何并发 main 前进都需重新基线协调，只在最新树上重放本次资产/规格/计划差异并保留新 main 父历史。不得 force-push、重置已完成状态、覆盖历史证据/固定锁/维护配置或以过期 CI 合并新 head。
