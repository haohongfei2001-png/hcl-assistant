# Product Review Adoption — A2 / 2026-10-01

性质：Owner 已确认 Review 的正式采用记录；只有文档与计划元数据变更，没有应用修复、视觉实现、provider调用、研究实验或能力激活。本文件不是第二份设计，以 [Master Plan](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](UX_SPEC.md)、[Visual](VISUAL_SYSTEM.md) 为规范。

## 1. 读取基线与事实

产品基线：`haohongfei2001-png/hcl-assistant@972234e8fdb868a51a519ba7f7c98cdb5a80583b`，tree `bdc1d9b595203065bea6e6868616994cd69fab3c`，已合并 [PR #5](https://github.com/haohongfei2001-png/hcl-assistant/pull/5)。该main的 [planning check](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36767804473) 已成功；这不代表A2已经实现。

Review读取的研究main为 `439d9363588ed8dea96f2c795b2f4b5d6c5e1c3c`；此处仅保留公开基线身份，不读取或引入研究材料。产品runtime lock仍固定 `a8229fcf22eccb851c58502a09ae7cecb346faf5`，三文件slice、两个EXPERIMENTAL能力。普通Web请求仍MOCK。研究最新能力不自动等于产品桥接、默认使用或回答增益。

Pages是browser-only脚本界面，本地React/Python/SQLite是产品基础，L2.5是隔离开发执行；三种事实不得混合。先前文档中的review-branch/pending字样按PR合并和exact-main事实澄清，不改写历史执行回执。

采用前另有 [PR #6](https://github.com/haohongfei2001-png/hcl-assistant/pull/6) upstream runtime sync 处于open；未作为main能力采用，不接管其代码或合并。重叠控制文档后续须依据最新main协调。

## 2. 当前UI整改结论

| 元素 | A2处置 |
|---|---|
| Synthetic Preview / MOCK | 一个清晰环境标识，详情按需；不隐藏mock身份，不逐轮重复 |
| 重置预览 | 演示菜单或设置，不占顶栏主位置 |
| 范围 / Topic下拉 | 当前范围可查看；项目按需，不是聊天前置配置 |
| 已保存重复标签 | 默认不重复，只提示异常/临时 |
| Advanced常驻导航 | 高级设置或详细检查入口 |
| 标题前记忆管理 | 记忆入口；当前背景按需查看 |
| 状态版本 / route | Inspector，不把版本变化当理解进展 |
| 每轮Explain / 在Lab检查按钮 | “查看依据”低权重；Lab下沉 |
| Composer大空白与多处技术小字 | 自适应、附件状态、相关时解释限制 |
| 每条分隔线/卡片/同权重按钮 | 以留白、正文与主次操作建立层级 |

## 3. 已定位、尚未修复的问题

全部来自基线的静态代码阅读；不冒充本次实机复现。截图外的浏览器垂直标签栏不属于HCL。

| ID | 当前实现证据 | 必须兑现的行为 | 首包 |
|---|---|---|---|
| F01 | `pages-preview/app.js` 的save序列化整个conversations，TEMPORARY未排除 | 临时正文不持久化 | P0-01 |
| F02 | updateRecord(DELETED)仅改status，content/run.input等仍留存 | 删除实际清理；stop-using真实影响未来使用 | P0-01 |
| F03 | 上传路径 `text.slice(0,1800)` 后显示已上传 | 完整保留或明确拒绝/显式选片段，不静默截断 | P0-01 |
| F04 | classify将“不是”等当CORRECTION，并替代最近活跃记录 | 否定不等于更正；目标含糊不改 | P0-01 |
| F05 | synthesize(text)仅接当前输入却可能输出“当前会话已知背景”等basis | 依据必须与实际读取记录绑定；无背景不声称已用 | P0-01 |
| F06 | Pages桌面sidebar-hidden无对应桌面规则 | 折叠在实际桌面视口有效 | P1-01 |
| F07 | Pages/React Enter发送未显式处理组合输入 | 中文IME确认候选不发送 | P1-01 |
| F08 | `apps/web/src/main.tsx` 每轮直接显示Lab/原始状态，回答主要普通p呈现 | Assistant-first层级与完整阅读排版 | P1-01 |

F01–F05不自动归因于本地后端；本地已有不同的持久化/删除/完整文件处理。需在对应surface分别复现和回归。A2采用不把任何F项标为FIXED。

## 4. 采用差异

正式固定Assistant-first、功能五层、聊天单中心、九视图、视觉tokens、MVP/演进顺序。删除默认研究导航和HCL强度；项目可选；Explain是真实记录投影；允许无专门处理/无增益。Judge只作为终局目标，现有字段/检查器不获得新能力身份。

旧冲突要求按 [Document Authority](DOCUMENT_AUTHORITY.md) 逐项处置。旧包全文和A01–A29/closure使用原blob存档，不删除失败或重写历史证据。`control/plan.json.product_development` 是唯一当前队列；顶层旧字段只保留L0–L2.5阶段/生产门槛含义，自动消费者迁移是P0-01的首项工程义务。

## 5. 本次交付验收与限制

只允许Markdown和control/plan.json计划元数据差异；apps、packages、scripts、tests、.github、contracts数据/schema/runtime lock与研究仓库不改。链接、唯一队列、依赖、Judge标签、生产/隐私门槛和存档blob须核对。

没有进行本地应用、浏览器或效力实验；容器直连公开raw GitHub因DNS失败，不能声称本地测试通过。通过GitHub连接器读取/写入；exact-head和合并后exact-main的实际CI结果在采用PR记录，不在文档中伪造自身未来SHA。已有自动checker只验证旧阶段边界与既有实现；新队列本轮人工核对，P0-01须迁移自动检查。

当前唯一下一项：**P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**。这不是开始L3或Judge开发的授权。
