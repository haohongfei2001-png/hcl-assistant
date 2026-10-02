# Product Work Contract — Canonical A2

适用范围：`haohongfei2001-png/hcl-assistant`根。main是唯一产品事实源。实现已采用的Assistant-first方案，不重新设计定位，不接管研究I02–I06。

## Start and authority

先读README、STATUS、DEVELOPMENT_PLAN、Master Plan1.2、docs/DOCUMENT_AUTHORITY.md、UX_SPEC、VISUAL_SYSTEM、contracts、PRODUCT_REFINEMENT_WORK_PACKAGES和ACCEPTANCE_MATRIX；再核对remote main、open PR和writer。普通用户先聊天；Explain/Inspector按需，Lab是高级研究环境。

当前唯一产品队列为 `control/plan.json.product_development`，与Development Plan/Status一致。<!-- CURRENT_PRODUCT_QUEUE_START -->
**NEXT_READY: STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_COMPLETE。唯一当前任务：无，等待L3门槛。

当前10包已完成；L3四门槛未满足，停止交接，不自动新增provider调用、Judge或Act。

任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。
<!-- CURRENT_PRODUCT_QUEUE_END -->。顶层旧phase/packages/next字段只记L0–L2.5完成与L3门槛，不是第二队列，不据旧STOP跳过已采用产品整改。当前checker/报告/advance消费者已迁移到product_development，同时严格保留旧阶段断言。禁止恢复legacy字段调度。

A2文档采用已合并。当前implementation Work获准按唯一队列实现P0/P1；一次一个writer，逐包exact-head审查/CI、合并和exact-main核验。认领以control/plan.json.writer与open PR为准；不得并行接管。

长期终局为Understand → Revise → Judge → Help → Act。Judge = LONG_TERM_GOAL_ONLY，未实现为通用能力、未验证、未生产启用；不得凭终局新增已启用能力或agent执行权限，不推断私人研究概念。

## Writer ownership

一次一个implementation writer；已有认领不得并行实现。使用product/<package>分支和明确PR认领/交接。文档采用与已有runtime-sync审阅工作范围分开，不接管或合并无关代码。未来合并重叠文件须保留A2与唯一队列，不从旧分支恢复旧产品方案。禁止force-push覆盖并发提交。

## Hard boundaries

- 产品Work只写此仓库，不修改human-cognition-layer的runtime、evaluation、控制面、脚本、测试、workflow或历史receipt。
- 不读取confirmation sources/gold、protected artifacts、eval credentials、provider secrets、真实私密数据或sealed LongMemEval；不clone/archive/mount研究仓库，不做研究全仓依赖。
- 仓库分离已完成；不声称public研究内容被密码学屏蔽，也不声称生产隐私已完成。
- L1/L2与P0/P1当前整改只用synthetic/mock、provider budget=0。L2.5仅exact-SHA allowlisted development runtime与permitted synthetic inputs，production_enabled=false；不能把当前UI请求改成真实provider或正式激活。
- runtime acquisition仅允许固定SHA/allowlist，不读确认/eval/sealed资产；不改formal-eval case-specific prompt；不为视觉演示重写原始source去迎合机制。
- 所有生产模拟输入/变更/回答仍经Controller。Pages无backend/provider/真实HCL；共享UI不得变成权限旁路。Base-only仅隔离Lab实验，不回写真实背景。
- 不收集/展示/持久化私有chain-of-thought；只记录显式结果、来源、版本与usage。
- 不删失败测试、不降低断言、不隐藏failed/refused/unresolved/no treatment，不把mock/experimental改标live或把schema正确升级效力。

## Development and verification

不依赖Owner桌面、登录态或checkout。现有root checks、Python、build、browser与固定development smoke按README执行；只运行获准provider-free路径。说明实际测试环境、命令、SHA、覆盖和限制；基础设施失败保留unverified。

普通代码决策遵从已采用方案。先P0真实承诺，再P1主体验；不是简单美化，不制造新本体/图谱平台。新包必须有正向帮助、负面边界、修订/持久化和实际browser证据；截图不代替行为测试。

PR记录范围、actual tests、限制与唯一NEXT_READY。exact-head通过后合并，再核验exact-main。current queue迁移不放宽L3或历史11包要求；旧checker输出不能被当作A2队列已获自动验证。

## Continuation and stopping

后续implementation Work只能在其明确范围内按唯一队列推进。真实权限、费用、许可、数据或生产门槛保持阻塞，不制造filler。P1-03完成但L3四门槛未具备则停止交接；物理分仓不能再次当作未完成blocker。

旧L0–L2.5规格/closure为历史证据，旧研究产品目录已退役；不维护双队列。当前状态以STATUS和exact-main为准，架构/交互以Master1.2及其UX/Visual规范为准。

## Development-only chat amendment (2026-09-30 23:48 UTC)

User-authorized D1-01 takes priority after adopted P1-02 and before P1-03. The provider-free restriction remains binding for historical mock/refinement tests and the existing HCL Bridge lock; it is not a permanent prohibition on this new gated product-owned DeepSeek transport. See [development chat contract](docs/DEVELOPMENT_CHAT.md). No live budget, configured server or public deployment is implied by code authorization. Production, research efficacy and private-data gates remain unchanged.

## Cloud hosting amendment (2026-10-01 08:36 UTC)

Owner approved C1-01 engineering adaptation after P1-03 for isolated Vercel/Postgres hosting. This adds a bounded package to the sole current queue; it does not reopen completed packages, change the reviewed HCL lock, authorize account provisioning, create credentials, reuse another app database, authorize real private data or renew the exhausted provider grant. Offline CI remains zero provider calls. Runtime hosting is not production HCL activation or efficacy evidence. Details: [cloud hosting contract](docs/CLOUD_HOSTING.md).

## Six-point chat refinement amendment (2026-10-01)

Owner approved U1-01 following the screenshot review: compact growing composer, tighter Home, correct cleared-history state, one search and on-demand background/attachment details, three supported contextual actions, and neutral readable surfaces within Continuum V1. This is the sole implementation writer; accepted digital-being assets, provider/Bridge/security and production gates stay unchanged. Verification and bounded scope: [U1-01 evidence](docs/U1_01_EVIDENCE.md).

## Bounded temporary trial amendment (2026-10-01)

Owner requested an at-most-four-hour, shared USD10, no-login temporary synthetic trial. The sole writer may implement isolated guest routes and a new explicit versioned budget policy; no full membership system, owner-route bypass, historical budget reset, production HCL activation or real-private-data permission is included. Offline CI remains zero provider calls. Live key entry and matching bounded activation are separate steps. Contract: [temporary trial](docs/TEMPORARY_TRIAL.md).

## Ordinary account amendment (2026-10-01 19:40 UTC)

Owner explicitly requested ordinary-user registration/login development while the optional guest trial remains inactive. M1-01 delivered the bounded account engineering slice: verified account identity, tenant and operational isolation, server-owned entitlement and global-budget checks, and bounded automatic session continuity in the existing UI. This code work does not enable Supabase Auth, create live accounts/credentials, install membership grants, open public database rights, start the guest clock or authorize real private data. See [account contract](docs/MEMBER_ACCOUNTS.md).

## Consumer journey amendment (2026-10-01 21:18 UTC)

Owner requested continued consumer-product improvement. U2-01 is the bounded next slice: the adopted visual language on the mobile account entry, explicit connection/sign-in recovery, first-message consent next to Send, and truthful account/model availability. It preserves one chat UI and all synthetic-only, tenant, entitlement, budget and activation gates. No live Auth, credential, paid email, billing, provider or private-data activation is included.

## Password recovery amendment (2026-10-01 22:10 UTC)

M2-01 adds one disabled, bounded ordinary-account recovery flow after U2-01. Follow [the recovery contract](docs/PASSWORD_RECOVERY.md). Code/offline tests are authorized; no live email, Auth configuration, credential changes, public rights, paid service, model or guest activation is authorized by this slice.

## Beijing Qwen preparation amendment (2026-10-02)

Owner requested HCLA-only Model Studio Beijing pay-as-you-go `qwen3.8-max` integration. The sole writer may implement this default-closed provider option, immutable native-CNY budget and offline tests. See [Qwen contract](docs/QWEN_PROVIDER.md). Existing DeepSeek USD histories, expired guest trial, HCL research/runtime, synthetic-only/private-data and production gates remain unchanged. This code slice authorizes no live key entry by an agent, grant installation, database migration, provider calls or activation.
