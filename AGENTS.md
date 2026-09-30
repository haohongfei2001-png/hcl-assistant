# Product Work Contract

适用范围：`haohongfei2001-png/hcl-assistant` 仓库根。此main是唯一产品事实源。实现已adopted的HCL Assistant产品，不重开定位讨论，不接管研究I02–I06。

## Start and writer ownership

读取根目录README、STATUS、DEVELOPMENT_PLAN、Master Plan、contracts和工作包。检查本仓库remote main与open PR。一次仅一个主writer；已有认领不得平行实现。使用`product/<package>`分支与明确PR认领/交接。研究Work只写研究仓库。

当前 L0–L2 已完成。本次 canonical plan amendment 执行者在 merge/exact-main 验证后停止，不实现 Bridge。下一位专门 Work 从 L2.5-01 开始，依赖安全时继续 L2.5-02；普通 schema/transport/tests/bug/CI/merge conflict 自行处理，不逐包问 Owner。

## Hard boundaries

- 允许写本产品仓库根控制文档、contracts、docs、apps、packages、scripts、tests与产品workflows。不修改human-cognition-layer的runtime、evaluation、控制面、脚本、测试、workflow或历史receipt。
- 不读取confirmation sources/gold、protected artifacts、eval credentials、provider secrets、真实私密数据或sealed LongMemEval。不clone/archive/mount研究仓库，不通过submodule或相对路径导入。
- CI/build仅使用本产品仓库根，无symlink escape或向上扫描研究文件。仓库分离已完成；不声称public研究内容被密码学屏蔽，也不声称生产隐私已实现。
- L1/L2：synthetic/mock only，provider transport budget=0。L2.5：允许 exact-SHA、allowlisted、development-only HCL runtime bridge 与 permitted synthetic/non-confirmation mechanism execution；production_enabled 必须 false。禁止 confirmation/gold/protected evaluation artifacts、LongMemEval、真实私密数据、formal-eval case-specific tuning 和 efficacy promotion。provider-backed execution 默认未授权，若需要须另有明确 development authorization。GitHub Pages preview 仍不得包含真实 HCL。
- 所有生产模拟路径也必经Controller。Base-only仅Lab实验，不回写生产context。mock不得改标签冒充live。
- 不删失败测试、不降断言、不改标签或隐藏failed/refused/unresolved；修复缺陷或报告真实阻塞。
- 禁止私有chain-of-thought收集/展示/存储。记录显式结果、provenance和usage，不持久化provider hidden reasoning正文。

## Working without owner desktop

不依赖 Owner Terminal、Desktop Commander、本地浏览器登录态或 Owner checkout。云端 Work/GitHub 可以获取本独立 public 产品仓库。L2.5 如需研究 runtime，只能通过 GitHub 对 `human-cognition-layer` exact commit SHA 的 allowlisted runtime/interface material 读取；禁止全仓遍历、confirmation/eval/sealed material 与浮动 ref。

## Verification and merge

在根目录运行`python3 scripts/check_planning.py`、`python3 scripts/check_repository.py`和`python3 -m unittest discover -s tests -v`。实现后增加对应behavioral/browser tests，不以planning checks代替。每包需要正向、负向、持久化/修订及历史回归证据和具体delta。

PR记录范围、actual tests、证据限制及NEXT_READY。exact-head通过后合并，再核验exact-main。复核最新main与冲突，记录实际测试SHA。不force-push、不绕过失败CI、不重置并发提交、不伪造receipt。基础设施失败保持unverified。

迁移清单保存源文件 hash，现为历史 provenance。STATUS、DEVELOPMENT_PLAN 与 control/plan.json 中的 phase/evidence/state 同步推进。L0–L2 九包保持既定边界；L2.5 只新增两包 runtime integration engineering，不重写既有完成证据。

## Continuation and stopping

依赖安全的 NEXT_READY 存在即继续。真实外部权限/费用/许可门槛 defer 并推进独立任务；不造 filler、不以 PR 数量衡量进展。L2.5 完成后，若 L3 的 I06/production-permitted artifact/interface/执行与数据授权未具备，则 STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED。物理分仓已经完成，不得再次作为未完成 blocker。

旧研究产品目录已退役。禁止在旧目录开发、同步双队列或采用旧副本指令；只有本仓库main是canonical。
