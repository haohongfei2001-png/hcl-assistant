# Document Authority and Supersession — A2

生效条件：本次文档采用合入 `haohongfei2001-png/hcl-assistant/main`。采用来源是 Owner 对已完成 Product & Interaction Design Review 的明确确认，并补充长期 `Understand → Revise → Judge → Help → Act`。本版没有第二套可选产品方案。

## 1. 唯一权威方案的分工

| 文件/位置 | 唯一职责 |
|---|---|
| [Master Plan 1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md) | 最终产品定义、Assistant-first、功能分层、架构原则、MVP与长期终局 |
| [UX Spec A2](UX_SPEC.md) | 同一方案的主流程与九个视图交互要求 |
| [Visual System A2](VISUAL_SYSTEM.md) | 同一方案的视觉tokens和行为要求 |
| [Development Plan](../DEVELOPMENT_PLAN.md) | 唯一当前开发任务、依赖顺序与停止条件 |
| `control/plan.json.product_development` | 上述唯一开发队列的机器可读投影，不是另一套计划 |
| [Status](../STATUS.md) | 当前已实现/未实现与证据事实，不能由计划倒推能力 |
| [Product Contracts](../contracts/PRODUCT_CONTRACTS_V1.md) | 现有API、数据、修订、权限与运行回执语义；不是前台导航模板 |
| [Acceptance Matrix](ACCEPTANCE_MATRIX.md) | 新设计待实现验收与历史证据的分离 |
| [Review Adoption](PRODUCT_REVIEW_ADOPTION.md) | 本次采用基线、现存问题与整改归属，不是已修复报告 |

Remote main代码、exact-SHA CI、固定runtime lock与原始回执是实现/证据事实。设计文件不升级这些事实。多个规范冲突时先按上表职责解决；产品/UX/视觉以A2为准，不能覆盖来源、权限、删除、研究隔离或生产激活门槛。队列镜像不一致必须停止认领并同步，不能挑对自己方便的一份继续。

## 2. control/plan.json 的明确作用域迁移

当前旧checker硬编码了11个L0–L2.5包及完成后的L3停止码。本次是文档/计划元数据采用，不能修改checker/tests或让失败CI被忽略。

因此同一plan文件保留顶层 `phase / packages / next_package_id / next_ready / current_executor_stop_after / future_work_allowed_through` 作为 **LEGACY_L0_L2_5_STAGE_COMPLETION_AND_L3_GATE_ONLY**。其中 `STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED` 仅表示完成这些历史包后不得自动进入L3，不再表示全部产品整改都停止。十一包的完成事实、production gates和证据原样保留，不伪造一个历史包重新NEXT_READY来迎合旧checker。

当前唯一产品开发队列是 **`product_development`**，当前任务从 `product_development.next_ready` 读取。根Development Plan和Status只镜像这个产品任务。顶层legacy next字段不是第二个候选任务，旧CI输出中的同名字段也只具有历史阶段含义。

本版明确记录 `automation_support=LEGACY_STAGE_CHECKS_ONLY_CURRENT_QUEUE_MANUALLY_REVIEWED`。现有自动检查的通过不被称为已验证A2队列。下一项P0-01先把checker/reporting/tests和队列消费者适配到这一唯一当前队列，并继续严格验证所有旧11包/权限/生产门槛。不得只读legacy next字段作当前调度；未适配自动消费者必须停止新调度，不能忽略新writer/任务。

这是一项显式兼容迁移，不是放宽历史断言或绕过CI。迁移属于下一项代码任务，本次没有修改代码。

## 3. 冲突设计的处置

| 旧要求或位置 | 处置 |
|---|---|
| Master Plan 1.0/1.1与UX v1中冲突的默认呈现 | 由当前Master/UX/Visual替代；旧版本只在Git历史保留 |
| 左侧常驻Topic/范围表单、默认Advanced、标题前记忆管理 | 由A2导航/当前范围/按需项目替代 |
| 每轮状态版本、route、MOCK、Lab主按钮 | 下沉；环境标识保留真实可见 |
| Lab主导、Case-first、常驻图谱、前台Base/HCL或强度滑块 | 排除，不是后续可自由恢复的变体 |
| L2-04要求显示disabled Compare按钮 | 历史验收事实保留；新主体验移除占位，Lab只说明真实门槛 |
| 人际/概念/责任作为默认首页分类 | 改为内部验证场景；对外通用助手 |
| 人格评分、心理诊断、全局永久第三方画像列入Later | 从产品路线排除；不与移动/语音/获准工具等可能后期功能混列 |
| README/STATUS/AGENTS中L2.5尚在review branch或下一步开始bridge | 已合并事实以PR #5与exact-main为准；当前队列另行明确 |
| [L0–L2.5 Packages](L0_L2_WORK_PACKAGES.md) | 历史包索引；原始全文在baseline文件保留，不是当前待开发队列 |
| [Baseline Acceptance](ACCEPTANCE_MATRIX_BASELINE_20261001.md) | 原始A01–A29及closure保留，只证明当时指定synthetic范围，不认证Pages缺陷已修复或A2合格 |
| [Execution](EXECUTION.md)、迁移/研究基线文档 | 历史provenance，不用其中旧NEXT_READY或NOT_IMPLEMENTED覆盖当前Status |
| [Pages Preview](PAGES_PREVIEW.md)与当前截图/代码 | 现存受限实现及反例，不是目标IA的权威来源 |
| 研究仓库旧products/hcl-assistant副本 | 退役，不在那里开发，不维护双队列；本次不修改研究仓库 |
| 尚未合并PR及其分支文档 | 不覆盖current main；合并前必须保留A2定义和唯一队列 |

## 4. 历史文件与保留原则

`L0_L2_WORK_PACKAGES_BASELINE_20261001.md` 与 `ACCEPTANCE_MATRIX_BASELINE_20261001.md` 是产品main `972234e8fdb868a51a519ba7f7c98cdb5a80583b` 对应文件的byte-identical Git blob存档。存档中的“当前”“NEXT_READY”“NOT_IMPLEMENTED”或阶段PASS只按原始时间/范围阅读，不是新指令。

不删除失败证据、不修改分数、不升级mock，不把设计采用写成修复完成。API契约、capability manifest、runtime lock、应用、脚本、测试与workflow在本次采用中不改。

## 5. 并发工作

采用前发现open PR #6（upstream runtime sync），其产品基线也是972234e8；它不是已合入功能，也不是本次用户授权接管的工作。此次只修改文档/计划，保留该PR代码和分支。其后续合并须基于最新main协调重叠控制文档，不得把legacy全产品STOP恢复为当前任务，或把自动repin变成生产激活。
