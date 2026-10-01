# HCL Assistant Live Development Plan — Canonical 1.2

唯一产品方案：[Master Plan 1.2](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX](docs/UX_SPEC.md)、[Visual](docs/VISUAL_SYSTEM.md)。权威分工见 [Document Authority](docs/DOCUMENT_AUTHORITY.md)。本文件是唯一live产品开发队列，机器投影为 `control/plan.json.product_development`。

<!-- CURRENT_PRODUCT_QUEUE_START -->
**NEXT_READY: M1-01_MEMBER_ACCOUNTS_AND_ISOLATION**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING。唯一当前任务：M1-01。

普通账号注册登录、请求身份与数据隔离、服务端权限和额度、自动续期；线上认证另行启用。验收：M01、M02、M03、M04、M05、M06

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
| P1-02 | revision/change/Explain/source/history/memory闭环 | P1-01 | COMPLETE |
| D1-01 | development-only DeepSeek chat | P1-02 | COMPLETE |
| P1-03 | bounded Inspect/Settings与整体synthetic验收 | D1-01 | COMPLETE |
| C1-01 | isolated stateless hosting and offline acceptance | P1-03 | COMPLETE |
| U1-01 | six-point Continuum chat interface refinement | C1-01 | COMPLETE |
| M1-01 | 普通账号、隔离与自动续期 | M01–M06 | NEXT_READY |

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

## Development-only chat amendment (2026-09-30 23:48 UTC)

Historical authorization/dependency record: D1-01 is now completed within its bounded evidence scope; the initial six-call grant is closed. Current task state is the live queue above.

User-authorized D1-01 takes priority after adopted P1-02 and before P1-03. The provider-free restriction remains binding for historical mock/refinement tests and the existing HCL Bridge lock; it is not a permanent prohibition on this new gated product-owned DeepSeek transport. See [development chat contract](docs/DEVELOPMENT_CHAT.md). No live budget, configured server or public deployment is implied by code authorization. Production, research efficacy and private-data gates remain unchanged.

## Continuum V1 设计采用历史与实施范围（不另建队列）

下段关于D1-01 NEXT_READY和采用基线是PR11时的历史快照，当前状态以文件顶部唯一队列及[P1-03/Continuum证据](docs/CONTINUUM_V1_EVIDENCE.md)为准。所列V1-A/B/C义务仍保留，现有实施/验收已逐项记录，不恢复旧队列。

最新批准的三张界面稿和两张形象稿见 [设计采用目录](docs/design/continuum-v1/README.md)。五张批准 PNG 的原始 payload 已按 manifest 无损嵌入 UTF-8 SVG 文本包装并完成反解校验；本采用变更通过 exact-head/main 后成为正式视觉基准。视觉采用不等于实现完成。

本采用重新基于最新 main **333b39f71cede6b741bfdd3486a66d6958901ce0**。保持当前 **D1-01_DEVELOPMENT_DEEPSEEK_CHAT** 为唯一 NEXT_READY 和现有 writer；不把 P1-03 提前、不恢复旧任务。D1-01 完成并按现有规则采用后，P1-03 才按 live queue 进入实现。

Continuum 工作只扩充既有 P1-03 的实施/验收范围，按三个串行切片执行：V1-A 共享外观/Home/长对话/Composer → V1-B 依据/来源/修订/锚点返回 → V1-C 双形象/响应式/motion/Inspector/Settings/整体验收。切片不拥有独立 NEXT_READY、state 或 writer，不构成第二队列。

P1-03 原 R17–R20 义务不减少；V01–V10 从属于其视觉/交互完成条件。实际页面必须与 UI-01/UI-02/UI-03 对照，并提供可播放的来源往返、修订状态和阅读位置恢复证据；无法忠实实现的部分进入偏差登记，不能静默替换为默认组件。M-01/M-02 均保留，未选唯一形象不阻塞共同界面。

## Cloud hosting amendment (2026-10-01 08:36 UTC)

Owner approved C1-01 engineering adaptation after P1-03 for isolated Vercel/Postgres hosting. This adds a bounded package to the sole current queue; it does not reopen completed packages, change the reviewed HCL lock, authorize account provisioning, create credentials, reuse another app database, authorize real private data or renew the exhausted provider grant. Offline CI remains zero provider calls. Runtime hosting is not production HCL activation or efficacy evidence. Details: [cloud hosting contract](docs/CLOUD_HOSTING.md).

## Six-point chat refinement amendment (2026-10-01)

Owner approved U1-01 following the screenshot review: compact growing composer, tighter Home, correct cleared-history state, one search and on-demand background/attachment details, three supported contextual actions, and neutral readable surfaces within Continuum V1. This is the sole implementation writer; accepted digital-being assets, provider/Bridge/security and production gates stay unchanged. Verification and bounded scope: [U1-01 evidence](docs/U1_01_EVIDENCE.md).

## Ordinary account amendment (2026-10-01 19:40 UTC)

Owner explicitly requested ordinary-user registration/login development while the optional guest trial remains inactive. M1-01 is the sole current engineering package: verified account identity, tenant and operational isolation, server-owned entitlement and global-budget checks, and bounded automatic session continuity in the existing UI. This code work does not enable Supabase Auth, create live accounts/credentials, install membership grants, open public database rights, start the guest clock or authorize real private data. See [account contract](docs/MEMBER_ACCOUNTS.md).
