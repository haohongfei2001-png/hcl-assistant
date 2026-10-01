# HCL Assistant

**Assistant-first：一个能够持续交流、允许更正、在新信息出现后修订理解并帮助用户完成任务的AI助手。** 这是产品目标，不是当前已验证能力。长期终局：`Understand → Revise → Judge → Help → Act`；**Judge仅是长期目标，未实现为通用能力、未验证、未生产启用。**

## Canonical product entry

唯一产品事实源是 `haohongfei2001-png/hcl-assistant/main`。正式采用的唯一产品方案为 [Product Master Plan 1.2 / A2-Product](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)；[UX Spec](docs/UX_SPEC.md) 与 [Visual System](docs/VISUAL_SYSTEM.md) 是同一方案的具体规范，不是替代方案。

开发先读 [STATUS](STATUS.md)、[DEVELOPMENT_PLAN](DEVELOPMENT_PLAN.md)、[AGENTS](AGENTS.md)、[Document Authority](docs/DOCUMENT_AUTHORITY.md)。数据/运行契约见 [contracts](contracts/PRODUCT_CONTRACTS_V1.md)。当前队列如下：

<!-- CURRENT_PRODUCT_QUEUE_START -->
**NEXT_READY: STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED**

当前产品阶段：ASSISTANT_FIRST_REFINEMENT_COMPLETE。唯一当前任务：无，等待L3门槛。

当前7包已完成；L3四门槛未满足，停止交接，不自动新增provider调用、Judge或Act。

任务认领与writer见control/plan.json；exact-head及exact-main验收是采用条件。
<!-- CURRENT_PRODUCT_QUEUE_END -->

验收未完成前不推进下一包。

当前队列机器投影为 `control/plan.json.product_development`。顶层旧phase/next_ready仅是L0–L2.5完成与L3生产门槛记录，不是第二套live队列；自动消费者迁移列入P0-01，未迁移者不得据旧字段新调度产品任务。

## Current implementation and entry

L0–L2 mock产品与L2.5受限development bridge已合入main；基线PR #5与并发合入的维护PR #6见 [adoption record](docs/PRODUCT_REVIEW_ADOPTION.md)。普通Web消息仍MOCK，没有通用模型回答；L2.5只在明确配置的隔离synthetic路径执行固定runtime slice。production remains disabled，efficacy remains NOT_TESTED。P0/P1整改及Continuum V1共享界面已实现，受限验收见[P1-03证据](docs/P1_03_EVIDENCE.md)。

Python >=3.11标准库/SQLite；React/TypeScript/Vite版本由npm lock固定。没有托管provider服务或生产认证；默认mock/Pages/CI保持零provider调用；另行授权的D1开发态DeepSeek链路已完成原始合成输入验证，不改production runtime lock或生产权限。历史证据见 [acceptance](docs/ACCEPTANCE_MATRIX.md) 与 [execution](docs/EXECUTION.md)。

既有 [upstream runtime synchronization](docs/RUNTIME_UPSTREAM_SYNC.md) 的hourly/manual候选验证与lock-only审阅维护继续保留，正常实验执行仍只读reviewed exact lock。它不是第二套产品开发队列；当前writer与新main仍受维护publisher的冲突检查。同步代码、workflow、C12契约和 [sync evidence](docs/RUNTIME_SYNC_EVIDENCE.md) 从已合入PR #6原样继承，不由本次文档工作实现或扩权。

## GitHub Pages synthetic preview

`https://haohongfei2001-png.github.io/hcl-assistant/`

这是browser-only静态脚本演示：无Python/SQLite backend、真实HCL、provider调用、服务器持久化或研究数据。**只使用合成信息，不输入真实私密数据。** P0-01已实现并验证受限的临时、删除、文件读取及显式更正/依据契约，实际验收与限制见 [Pages boundary and limitations](docs/PAGES_PREVIEW.md)。不能从“模拟”字样推定数据控制行为已正确。

## One-command development chat

在配置好的本地电脑中运行 `npm run chat`，同一命令启动API与共享网页、等待就绪并打开浏览器；Ctrl-C同时停止二者。首次普通依赖安装为 `npm ci --ignore-scripts`。需要操作员直接安全输入配置时运行 `npm run chat -- --configure`；密钥和本地访问密码是隐藏终端输入，不进入网页、仓库或浏览器存储。

已验证DeepSeek后端开发链路和固定HCL合成Bridge参与，UI链路另有零调用浏览器测试；没有声称真实provider浏览器端到端或用户Mac安装已经验收。首轮6次开发调用授权已用完并关闭，不能拿旧grant初始化新的额度。后续本地使用需要一个安全配置且明确获准的新产品运行环境/额度，见[操作说明与实际结果](docs/DEVELOPMENT_CHAT.md)。用户已于2026-10-01批准云端托管适配；代码与离线验收见 [cloud hosting](docs/CLOUD_HOSTING.md)。真实托管地址、账户配置及新模型额度尚未启用；下面的Pages仍只是静态演示。

## Run the existing local synthetic product

身份为隔离测试身份，不是生产认证。HTTP固定loopback。仅合成输入；TXT/Markdown/UTF-8，64KiB；注册不证明完整理解。当前local临时会话正文在进程内存，重启丢失；持久会话可恢复，未知中断不自动重调adapter。不要把该后端行为等同于独立Pages实现。

```sh
npm ci --ignore-scripts
mkdir -p .local
python3 -m apps.api.server --database .local/mock.sqlite
# Second shell
npm run dev
```

原始synthetic用法与限制见 [scenarios](docs/SYNTHETIC_SCENARIOS.md)。任意未支持输入保留未解析，不宣称一般中文/语义能力。

## Existing verification

```sh
python3 scripts/fetch_development_runtime.py /tmp/hcl-assistant-development-runtime
export HCL_DEVELOPMENT_ARTIFACT=/tmp/hcl-assistant-development-runtime
python3 scripts/check_planning.py
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
npm run build
npx playwright install chromium --only-shell
npm run test:browser
python3 scripts/smoke_development_bridge.py "$HCL_DEVELOPMENT_ARTIFACT"
```

P0-01已迁移root checker/报告/advance消费者到唯一product_development队列，继续独立验证旧11包及L3边界。队列通过不等于界面验收通过。Hosted exact-head/main CI记录实际SHA与结果；通过不等于生产隐私、语义泛化、Judge或效力证明。

L3仍需I06处置、固定获准production artifact/interface、产品adapter scope验证、明确执行/数据授权。受限development接口与版本见 [Experimental Runtime Bridge](docs/EXPERIMENTAL_RUNTIME_BRIDGE.md)。不得为终局目标自动开放provider、研究数据或agent。

## Development-only chat amendment (2026-09-30 23:48 UTC)

Historical authorization/dependency record: D1-01 is now completed within its bounded evidence scope; the initial six-call grant is closed. Current task state is the live queue above.

User-authorized D1-01 takes priority after adopted P1-02 and before P1-03. The provider-free restriction remains binding for historical mock/refinement tests and the existing HCL Bridge lock; it is not a permanent prohibition on this new gated product-owned DeepSeek transport. See [development chat contract](docs/DEVELOPMENT_CHAT.md). No live budget, configured server or public deployment is implied by code authorization. Production, research efficacy and private-data gates remain unchanged.

## Cloud hosting amendment (2026-10-01 08:36 UTC)

Owner approved C1-01 engineering adaptation after P1-03 for isolated Vercel/Postgres hosting. This adds a bounded package to the sole current queue; it does not reopen completed packages, change the reviewed HCL lock, authorize account provisioning, create credentials, reuse another app database, authorize real private data or renew the exhausted provider grant. Offline CI remains zero provider calls. Runtime hosting is not production HCL activation or efficacy evidence. Details: [cloud hosting contract](docs/CLOUD_HOSTING.md).

## Six-point chat refinement amendment (2026-10-01)

Owner approved U1-01 following the screenshot review: compact growing composer, tighter Home, correct cleared-history state, one search and on-demand background/attachment details, three supported contextual actions, and neutral readable surfaces within Continuum V1. This is the sole implementation writer; accepted digital-being assets, provider/Bridge/security and production gates stay unchanged. Verification and bounded scope: [U1-01 evidence](docs/U1_01_EVIDENCE.md).
