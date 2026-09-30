# Product Acceptance Matrix — Canonical 1.2

归属：[Master](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](UX_SPEC.md)、[Work Packages](PRODUCT_REFINEMENT_WORK_PACKAGES.md)。P0-01的R01–R07已有受限synthetic实现与exact-head验收，见 [P0 evidence](P0_01_EVIDENCE.md)；采用仍须最终head/main核验。**R08–R20仍NOT_IMPLEMENTED / NOT_TESTED_IN_A2**，不因既有CI通过改填PASS。

## Historical evidence, unchanged

原A01–A29、L2的90检查/10browser与L2.5的126检查/12browser等closure按原blob保存在 [baseline](ACCEPTANCE_MATRIX_BASELINE_20261001.md)。[Execution](EXECUTION.md)为历史证据，不是当前队列。本地SQLite/Controller验收不自动认证Pages；旧A20的disabled Compare占位不再是新主体验要求。原安全义务继续保留。

### A30 — inherited upstream synchronization maintenance acceptance

PR6已合入main e2a72050，维护验收保留：unchanged main退出UP_TO_DATE；exact candidate只用既有allowlist；provenance/interface/manifest不兼容或smoke/regression/build/browser失败保留stable pin；仅full-pass候选产生lock-only PR；writer/main冲突defer；auto-merge须已有strict required CI。证据为 [sync report](RUNTIME_SYNC_EVIDENCE.md)、tests/test_upstream_runtime_sync.py与既有actual runtime/Python/build/browser记录。L3/I06门槛不变，本次不修改该代码/测试/证据或自行重跑候选验证。

## Current product obligations

| ID | Positive obligation | Negative / boundary | First package |
|---|---|---|---|
| R01 | 当前product_development唯一队列被checker/报告/消费者读取 | 多ready/依赖/镜像漂移拒绝；旧11包与L3门槛不削弱 | P0-01 |
| R02 | TEMPORARY无持久正文，刷新/重开行为如实 | localStorage/run/摘要副本不泄漏 | P0-01 |
| R03 | DELETE清理副本，STOP_USING阻止未来使用 | 仅改标签不算成功，独立来源范围明确，不复活 | P0-01 |
| R04 | 文件支持范围内完整读取/保存/定位 | 不silent slice1800，注册不等理解 | P0-01 |
| R05 | 明确更正只作用于正确目标 | 否定不等更正，含糊/未支持不改最近记录 | P0-01 |
| R06 | 回答/Explain依据绑定实际读取记录 | 无历史不声称已用，开放输入不假装理解 | P0-01 |
| R07 | Pages与local分别实测并回归 | 不把后端PASS套Pages，保留历史失败/实验边界 | P0-01 |
| R08 | Home/Conversation直接聊天 | 无Case wizard/强制Topic/心理分类/常驻Inspector | P1-01 |
| R09 | Sidebar/标题/当前范围与按需项目清楚 | 不混新建默认与当前范围，无每轮route/version/Lab主CTA | P1-01 |
| R10 | Composer草稿/停止/附件/IME正确 | 中文候选Enter不发送，失败不丢草稿 | P1-01 |
| R11 | Markdown/代码/引用/表格与流式阅读可用 | 向上阅读不拉底，键盘/焦点/缩放/窄窗通过 | P1-01 |
| R12 | UI/产品视图复用且mock身份清晰 | Pages无backend/provider/真实HCL，不复制不同记忆语义 | P1-01 |
| R13 | 回答→依据→原文→更正可返回 | 不叠modal/丢焦点，来源与当次版本对应 | P1-02 |
| R14 | 重要变化说明旧依据/新信息/影响 | 无影响不造insight，未重算不标不变，弱化不证替代动机 | P1-02 |
| R15 | 更正/现在变化/猜测/假设分开，历史依据保留 | 不倒填获知时间/假设回写/事后理由 | P1-02 |
| R16 | 历史搜索/记忆范围/停止/删除/导出一致 | 检索带更正/撤回/反证，缓存/导出不复活 | P1-02 |
| R17 | Inspector/Lab按需可读，同run真实状态 | selected/executed/output/used与无处理/失败/未知分开 | P1-03 |
| R18 | Settings只显示真实行为和边界 | 无强度/未接入模型能力，无Judge或agent激活 | P1-03 |
| R19 | 普通/更正/迟到信息/假设/冲突/恢复原创闭环 | 普通任务不强制认知展示，重要不确定性保留正文 | P1-03 |
| R20 | 可用性、正确性、增益分开报告 | 节点数/偏好/结构美观不证效力，无provider不报真实模型性能 | P1-03 |

每行完成需命令、exact SHA、fixture lineage、实际结果、surface/浏览器/存储范围与限制；只用新原创非确认材料，不改名复用研究失败题或读取confirmation/gold/私人数据。截图只证视觉，失败/未知/未处理/权限/删除/不支持均需验收。

P0/P1完成不开放L3或把Judge升级实现。真实日常MVP、中文多轮效力、真实provider延迟/成本、跨模型增益与生产隐私须后续单独授权验证。
