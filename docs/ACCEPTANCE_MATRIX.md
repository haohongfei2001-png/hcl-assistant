# Product Acceptance Matrix — A2

归属：[Master Plan](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](UX_SPEC.md)、[Work Packages](PRODUCT_REFINEMENT_WORK_PACKAGES.md)。本次只采用设计与计划，**下列R01–R20全部NOT_IMPLEMENTED / NOT_TESTED_IN_A2**，不因旧CI通过改填PASS。

## Historical evidence, unchanged

原A01–A29义务、L2的90检查/10browser以及L2.5的126检查/12browser等closure完整保存在 [byte-identical baseline](ACCEPTANCE_MATRIX_BASELINE_20261001.md)，来源为main972234e8的原Git blob。原执行范围、失败与限制不改；[Execution](EXECUTION.md)仍是历史证据，不是当前队列。

原L2本地SQLite/Controller验收不自动认证独立Pages实现；原A20的disabled Compare展示不再是新主体验要求。原A09/A10等安全义务继续适用，不能为了新UI删除。A2规范通过须有新的对应行为证据。

## Current product obligations

| ID | Positive obligation | Negative / boundary | First package |
|---|---|---|---|
| R01 | 当前product_development唯一队列被checker/报告/消费者准确读取 | 多ready/依赖/镜像漂移拒绝；旧11包与L3门槛不削弱 | P0-01 |
| R02 | TEMPORARY无持久正文，刷新/重开行为如实 | localStorage/run/摘要副本不泄漏临时正文 | P0-01 |
| R03 | DELETE清理实际副本；STOP_USING阻止未来使用 | 仅改标签不算成功；独立来源范围说明；历史不复活 | P0-01 |
| R04 | 文件支持范围内完整读取/保存/定位 | 不silent slice1800；超限/不支持明确，不把注册当理解 | P0-01 |
| R05 | 明确更正只作用于正确目标 | 否定不等于更正；含糊/未支持不改最近记录 | P0-01 |
| R06 | 回答与Explain依据绑定实际读取记录 | 无历史不模板声称已用；开放输入不假装语义理解 | P0-01 |
| R07 | 对应Pages与local surface分别实测并回归 | 不把本地后端PASS套用Pages；保留原失败和实验边界 | P0-01 |
| R08 | Home/Conversation同一直接聊天入口 | 无Case wizard/强制Topic/心理分类/常驻Inspector | P1-01 |
| R09 | Sidebar/标题/当前范围与按需项目清楚 | 不混同新建默认与当前范围；无每轮route/version/Lab主CTA | P1-01 |
| R10 | Composer草稿/停止/发送/附件/IME正确 | 中文候选Enter不发送；失败不丢草稿；无假完成 | P1-01 |
| R11 | Markdown/代码/引用/表格与流式阅读可用 | 向上阅读不拉底；键盘/焦点/缩放/窄窗通过 | P1-01 |
| R12 | UI/产品视图复用且mock身份清晰 | Pages无backend/provider/真实HCL；不复制不同记忆语义 | P1-01 |
| R13 | 回答→依据→原文→更正可返回同上下文 | 不叠多重modal/丢焦点；来源与当次版本对应 | P1-02 |
| R14 | 重要变化说明旧依据/新信息/影响 | 无影响不造insight；未重算不标不变；解释弱化不证替代动机 | P1-02 |
| R15 | 更正/现在变化/猜测/假设分开，旧回答保留当时记录 | 假设不回写；今天信息不倒填人物过去；无事后理由 | P1-02 |
| R16 | 历史搜索、记忆范围、停止/删除与导出一致 | 检索带更正/撤回/反证；缓存/导出不复活删除 | P1-02 |
| R17 | Inspector/Lab按需可读，同run真实操作状态 | 选中/执行/输出/使用分开，无处理/不支持/失败/未知不混同 | P1-03 |
| R18 | Settings只显示真实可用行为与数据边界 | 无HCL强度/未接入模型能力；没有agent或Judge激活 | P1-03 |
| R19 | 普通/更正/迟到信息/假设/冲突/恢复原创synthetic闭环 | 普通任务不强制认知展示；重要不确定性不全藏Explain | P1-03 |
| R20 | 产品可用性、数据/理解正确性、增益证据分开报告 | 不以节点数/偏好/拒答/结构美观推效力；无provider不报真实模型性能 | P1-03 |

## Evidence requirements

每行完成需命令、exact SHA、fixture lineage、实际结果、surface/浏览器/存储范围及限制。仅用新原创非确认材料，不使用研究失败题改名、confirmation/gold或私人数据。公开模板结果只标synthetic，不变成外部泛化。

失败、未知、无专门处理、来源删除、权限变化与不支持输入均需验收；截图只是视觉证据。P0/P1 completion不能打开L3，也不能把Judge从长期目标改为已实现。真实日常MVP、中文多轮效力、真实provider延迟/成本、跨模型增益和生产隐私须后续单独授权与验证。
