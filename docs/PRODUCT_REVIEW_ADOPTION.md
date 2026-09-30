# Product Review Adoption — Canonical 1.2 / A2-Product

2026-10-01。Owner已确认Review的正式采用，只有文档与计划元数据，没有应用修复、视觉实现、provider调用、研究实验或能力激活。本文件不是第二份设计；以 [Master](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](UX_SPEC.md)、[Visual](VISUAL_SYSTEM.md)为规范。

## 1. 读取基线与并发事实

原Review产品基线：`972234e8fdb868a51a519ba7f7c98cdb5a80583b`，tree `bdc1d9b595203065bea6e6868616994cd69fab3c`，已合并 [PR5](https://github.com/haohongfei2001-png/hcl-assistant/pull/5)，exact-main [planning](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36767804473)成功。

原文档head `2cbfc5240eb4d709f01250f24b8d2d8277b85c43` 的 [CI36774752304](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36774752304) 实际通过旧root checks、126 Python检查、build、12 browser journeys和固定dev smoke。这个结果只属于原head，不冒充协调后head/main验证。

合并前复核发现另一写入者已将 [PR6](https://github.com/haohongfei2001-png/hcl-assistant/pull/6) 合入main `e2a72050e184e61f45b17de3f867419e86c658de`。本次以该树为直接基线，保留其所有代码、workflow、C12契约、runtime维护文档/证据和runtime_sync元数据，再应用本次文档方案。继承维护不是本次实现，不新增repin或生产授权。A2编号消歧见 [Authority](DOCUMENT_AUTHORITY.md)。

Review研究main为 `439d9363588ed8dea96f2c795b2f4b5d6c5e1c3c`；此处仅保留公开身份，不引入研究材料。产品stable runtime仍是reviewed lock，本次不改初始a8229fc pin、三文件slice或两个EXPERIMENTAL能力。普通UI仍MOCK。

Pages是browser-only脚本界面，本地React/Python/SQLite是产品基础，L2.5是隔离dev执行；三者不混合。研究新能力不自动等于产品已桥接、默认使用或回答增益。

## 2. UI整改结论

| 元素 | 处置 |
|---|---|
| Synthetic Preview / MOCK | 一个清晰环境标识，详情按需；不隐藏、不逐轮重复 |
| 重置预览 | 演示菜单/设置，不占顶栏主位置 |
| 范围 / Topic下拉 | 当前范围可查看，项目按需，不是聊天前置配置 |
| 已保存标签 | 默认不重复，只提示异常/临时 |
| Advanced | 高级设置或详细检查 |
| 标题前记忆管理 | 记忆入口，当前背景按需 |
| version / route | Inspector，不当理解进展 |
| 每轮Explain / Lab主按钮 | 查看依据低权重，Lab下沉 |
| Composer空白/技术小字 | 自适应输入与相关动作提示 |
| 每条卡片/分隔线/同权重按钮 | 留白、正文、主次操作层级 |

## 3. 已定位、未修复的问题

这些是基线静态代码观察，不冒充本次实机复现；浏览器垂直标签栏不属于HCL。

| ID | 实现证据 | 目标 | 首包 |
|---|---|---|---|
| F01 | Pages save序列化全部conversations，TEMPORARY未排除 | 临时正文不持久 | P0-01 |
| F02 | updateRecord(DELETED)只改status，content/run.input仍留 | 删除实际清理；stop真实影响未来使用 | P0-01 |
| F03 | 上传text.slice(0,1800)后显示已上传 | 完整保留或明确拒绝/显式选片段 | P0-01 |
| F04 | “不是”等当CORRECTION并替代最近活跃记录 | 否定不等更正，目标含糊不改 | P0-01 |
| F05 | synthesize(text)只接当前输入却可能称已知会话背景 | 依据绑定实际使用记录 | P0-01 |
| F06 | Pages sidebar-hidden仅移动断点有对应规则 | 桌面折叠实测 | P1-01 |
| F07 | Pages/React Enter未显式处理组合输入 | 中文IME不误发送 | P1-01 |
| F08 | main.tsx每轮Lab/原始状态，普通p回答 | Assistant-first层级与阅读体系 | P1-01 |

F01–F05不自动归因于本地后端；不同surface分别复现/回归。本次不把任何F项标FIXED。

## 4. 采用差异和历史边界

固定Assistant-first、功能五层、聊天单中心、九视图、视觉、MVP和演进。删除默认研究导航/HCL强度，项目可选；Explain为记录投影；无专门处理/无增益合法。Judge仅长期目标，不因字段/条件检查获得新能力身份。

旧冲突要求由Authority处置；旧十一包及A01–A29原blob存档，PR6维护A30在当前Acceptance和sync evidence继续保留。旧失败/结果/安全边界不改。product_development是唯一当前产品队列；顶层legacy只表示历史阶段/L3门槛。新队列自动校验迁移是P0-01首项义务，不声称已实现。

## 5. 验收与限制

相对最新main e2a72050，只允许Markdown和control/plan.json计划元数据差异。应用、packages、scripts、tests、.github、contracts/schema/lock与研究仓库不改。核对链接、唯一队列、依赖、Judge边界、原blob和维护继承。

本地容器raw GitHub读取DNS失败，不声明本地测试/browser通过；通过GitHub连接器读写并核查hosted CI。协调后的exact-head与最终main结果在 [PR7](https://github.com/haohongfei2001-png/hcl-assistant/pull/7) 留证，不伪造自身未来SHA。旧checker只自动验证既有阶段/边界与实现，新队列本轮人工核对。所有新R01–R20仍NOT_IMPLEMENTED/NOT_TESTED_IN_A2。

唯一下一项：**P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**。此次文档执行者合并核验后停止，不开始代码或Judge/Act。
