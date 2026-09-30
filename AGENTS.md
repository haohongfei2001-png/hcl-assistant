# Product Work Contract

适用范围：`haohongfei2001-png/hcl-assistant` 仓库根。此main是唯一产品事实源。实现已adopted的HCL Assistant产品，不重开定位讨论，不接管研究I02–I06。

## Start and writer ownership

读取根目录README、STATUS、DEVELOPMENT_PLAN、Master Plan、contracts和工作包。检查本仓库remote main与open PR。一次仅一个主writer；已有认领不得平行实现。使用`product/<package>`分支与明确PR认领/交接。研究Work只写研究仓库。

本轮迁移执行者在分仓/main验证及旧目录处置后停止，不实现L1。后续专门Work从L1-01连续推进依赖安全的L1/L2；普通schema/UI/测试/bug/CI/merge conflict自行处理，不逐包问Owner。

## Hard boundaries

- 允许写本产品仓库根控制文档、contracts、docs、apps、packages、scripts、tests与产品workflows。不修改human-cognition-layer的runtime、evaluation、控制面、脚本、测试、workflow或历史receipt。
- 不读取confirmation sources/gold、protected artifacts、eval credentials、provider secrets、真实私密数据或sealed LongMemEval。不clone/archive/mount研究仓库，不通过submodule或相对路径导入。
- CI/build仅使用本产品仓库根，无symlink escape或向上扫描研究文件。仓库分离已完成；不声称public研究内容被密码学屏蔽，也不声称生产隐私已实现。
- L1/L2：synthetic/mock only，provider transport budget=0，无外部deployment credentials、real user data、paid comparison或外部onboarding。允许GitHub内建Pages发布browser-only static synthetic preview；它不得包含后端、真实HCL、研究/evaluation材料、服务器持久化或真实私密数据，也不满足任何L3 gate。L3 gates满足前无真实HCL semantic integration。
- 所有生产模拟路径也必经Controller。Base-only仅Lab实验，不回写生产context。mock不得改标签冒充live。
- 不删失败测试、不降断言、不改标签或隐藏failed/refused/unresolved；修复缺陷或报告真实阻塞。
- 禁止私有chain-of-thought收集/展示/存储。记录显式结果、provenance和usage，不持久化provider hidden reasoning正文。

## Working without owner desktop

不依赖Owner Terminal、Desktop Commander、本地浏览器登录态或Owner checkout。云端Work/GitHub可以获取本独立public产品仓库。L1/L2无需读取研究正文；历史baseline中的提交/路径/hash只是引用，不授权访问测试材料。

## Verification and merge

在根目录运行`python3 scripts/check_planning.py`、`python3 scripts/check_repository.py`和`python3 -m unittest discover -s tests -v`。实现后增加对应behavioral/browser tests，不以planning checks代替。每包需要正向、负向、持久化/修订及历史回归证据和具体delta。

PR记录范围、actual tests、证据限制及NEXT_READY。exact-head通过后合并，再核验exact-main。复核最新main与冲突，记录实际测试SHA。不force-push、不绕过失败CI、不重置并发提交、不伪造receipt。基础设施失败保持unverified。

迁移清单保存源文件hash；L0期间检查未修改迁入文件。进入L1后它是历史provenance，不禁止合理产品修改。STATUS、DEVELOPMENT_PLAN与control/plan.json中的phase/evidence/state同步推进，保持既定九包。

## Continuation and stopping

依赖安全的NEXT_READY存在即继续。真实外部权限/费用/许可门槛defer并推进独立任务；不造filler、不以PR数量衡量进展。L2完成且L3的I06/获准artifact/interface/执行和数据授权未具备时STOP_WITH_HANDOFF。物理分仓已经完成，不得再次作为未完成blocker。

旧研究产品目录已退役。禁止在旧目录开发、同步双队列或采用旧副本指令；只有本仓库main是canonical。
