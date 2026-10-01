# Product Refinement Work Packages — A2

归属：[Master Plan](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[UX Spec](UX_SPEC.md)、[Visual System](VISUAL_SYSTEM.md)。这是已确认Review的实施分解，不是重新设计。唯一live队列在 [Development Plan](../DEVELOPMENT_PLAN.md) 与 `control/plan.json.product_development`；本文件只定义包。文档采用与后续implementation Work分开；实现必须明确认领。

当前状态和依赖仅以 Development Plan 与 product_development 为准；最新 live queue 在 P1-02 与 P1-03 之间包含获准的 D1-01 development-only chat，本文件不另建并行队列。L0–L2.5历史完成不重开；L3生产激活门槛不变。全部当前整改只用synthetic/provider-free数据，不获得真实用户数据、provider、Judge或agent执行授权。工作包不是PR数量承诺，不扩成通用平台。

## P0-01 — Truthful preview contract repair

唯一任务标识：**P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR**。

目标：先让预览里“临时、删除、不再使用、完整读取、更正、依据”与真实行为一致，再进入视觉与主界面重构。起点是当前Pages静态代码中的可定位问题，不是声称本地后端也有同样缺陷。

依赖：A2文档在main正式采用；L2.5历史基线保留。下一位明确的implementation Work认领后执行；本次采用不启动代码。

范围：
- 当前队列消费者/checker/reporting/tests支持 `control/plan.json.product_development`；历史11包与L3安全门槛保持严格校验。输出不能再把legacy阶段停止码称作全局NEXT_READY；拒绝当前多ready/未知依赖/镜像漂移。先完成此适配，才允许自动认领或调度新包。
- TEMPORARY正文不得进入localStorage或其他持久副本；刷新/重开行为准确。
- DELETE实际移除受影响正文及run/input/派生副本；STOP_USING实际阻止后续使用。不能只改状态标签；其他独立来源仍有相同信息时明确范围。
- 文件在支持限额内完整保留并核对；不能silent slice到1800字符后称完整上传/读取。不能支持完整内容就明确拒绝或要求用户显式选片段。
- 普通否定句不当作更正；更正对象不按最近记录猜测。只支持明确synthetic场景/目标时如实限制，含糊目标不修改并澄清。
- 回答/Explain只有实际读取并记录的依据；无相应背景时不得模板声称已参考历史。开放输入保持未覆盖，不扩大关键词脚本冒充一般理解。

验收：R01–R07；真实浏览器与存储字节/刷新检查，文件首尾及完整内容检查，更正不误伤/不支持分支、依据来源绑定、local L2与L2.5历史回归。原始问题先复现；失败记录保留，不删除或弱化旧安全断言。

完成判据：以上承诺可兑现或误导动作被明确移除/标为不支持；无虚假成功；原有生产与研究边界不变；当前队列得到真实自动校验。完整原始范围的正向、负向、修订/持久化证据随exact SHA发布。

不做：新视觉主题、完整页面重写、通用语义提取器、真实模型、runtime repin、Judge、Research Compare或agent。下一项只能是P1-01，不能以修复完成跳过依赖。

## P1-01 — Shared Assistant-first shell and interaction system

任务标识：P1-01_ASSISTANT_FIRST_SHARED_SHELL；依赖P0-01；状态见唯一live队列。

目标：把已有方案落实成一个一致主聊天界面，不在旧页面上只换配色。

范围：按UX/Visual重构Home与Conversation、Sidebar、当前范围、可选项目、标题、消息排版与composer；隐藏路由/版本/每轮Lab；保留一个真实环境标识；Markdown/代码/引用/表格、草稿、停止/恢复、中文IME、焦点、流式滚动和窄窗口。Pages与本地尽量共享UI/产品视图契约，通过明确mock adapter区分；保持Pages无后端/provider/真实HCL边界，不复制第二套不同语义的记忆系统。

验收：R08–R12；截图用于视觉核对，实际browser行为与存储验收分别记录。对话直接开始，无Case wizard/Topic必填/常驻Inspector/HCL强度。P0不回归。

不做：新定位、新心理分类、全图、模型市场或生产provider。

## P1-02 — Revision, evidence and memory interaction loop

任务标识：P1-02_REVISION_EVIDENCE_MEMORY_LOOP；依赖P1-01；状态见唯一live队列。

目标：将真实更正、依据、重要理解变化、历史/搜索和记忆控制连成普通用户可用闭环。

范围：按UX提供回答级“查看依据”、可返回的原文定位、重要变化摘要、旧依据/新信息/影响说明、当前范围背景管理、基本历史搜索和权限内导出。自然更正优先，受限synthetic语义如实标明；精确表单只是补充。纠错、从现在变化、猜测、假设分开；重要不确定性保留正文；旧回答不被新证据洗白。实现当前可支持的版本/记录投影，不伪造自由语言理解。

验收：R13–R16；同一记录链从回答到依据/来源/更正，历史和新run分开；假设不回写；未知/失败/删除/无依据有正确空状态。停止使用与删除受P0约束，反证与更正不被搜索漏掉。

不做：全局人物档案、一般Judge、跨项目自动记忆、完整图谱编辑或provider调用。

## P1-03 — Integrated product acceptance and bounded inspection

任务标识：P1-03_INTEGRATED_SYNTHETIC_ACCEPTANCE；当前 live queue 依赖 D1-01（P1-02 已完成）；状态见唯一 live 队列。

目标：完成A2产品体验的受限synthetic验收，保留可检查性，不扩大Lab为主产品。

范围：按需只读详细检查与既有Lab整理；selected/executed/output/used、未处理/不支持/失败/未知分别显示；按当前权限导出。基础Settings覆盖真实可用设置、数据范围与限制。完整跑普通任务、更正、迟到信息、假设、来源冲突、恢复、临时/删除等原创轨迹。Research Compare只保留规格与能力门槛说明，不执行真实比较或生成假双栏结果。

验收：R17–R20及全部R01–R16回归；报告正向可用行为、错误/未覆盖、keyboard/IME、视觉/窄屏、延迟与成本可测范围。不得用节点数/Explain展开率代替任务成功或认知效力。没有provider时费用为明确来源的0，不声称真实模型延迟/成本达标。

完成后：若L3四项门槛未满足，STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED。不造新功能填充等待；保留未来真实日常MVP所需门槛清单。Judge仍LONG_TERM_GOAL_ONLY，Act仍未授权。

### Continuum V1：P1-03 内的三个依赖交付切片

本增量落实已正式采用的 [Continuum V1 五张设计稿](design/continuum-v1/README.md)。不重开已完成的 P1-01/P1-02，沿用其真实修订、来源和数据控制逻辑。父包仍是 P1-03，原 R17–R20 范围和全部既有回归均保留。

| 切片 | 依赖 | 范围及对应设计 | 完成/验收条件 |
|---|---|---|---|
| V1-A：共享外观与阅读/输入 | D1-01 完成且 V1 原图/规范已采用（P1-02 已完成） | UI-01、UI-02；共享 frame、轻量导航/顶栏、Home、对话阅读面、文件条、表格/代码、composer；按原图还原配色/光感/材质；保留 A/B/off 插槽契约但不等待形象选择 | V01、V02、相关 V08/V10；实际首页与长回答对照截图，至少3轮长内容，IME/草稿/流式不抢滚动；P0/P1-01 功能不回归 |
| V1-B：依据/来源/修订的连续展开 | V1-A | UI-02、UI-03；回答级依据层、来源列表/片段/原文、变化比较、未重评/失败/未知、正常关闭与返回原位置；复用 P1-02 记录而非重做语义 | V03–V07、相关 V10；可播放来源往返和修订轨迹，同视口锚点误差目标≤2 CSS px、重排后同段落可见，当前权限下原文不泄露 |
| V1-C：双形象、全状态与整体验收 | V1-B | M-01、M-02、UI-01/02/03；两套候选和 off，responsive/keyboard/减少动态/低性能fallback；原P1-03的Inspector/Settings/Lab边界；全部原轨迹回归 | V01–V10 和 R01–R20 所需证据齐全；实际页面/原稿对照和操作录像，重大偏差已审阅；两形象并存即可，不要求选唯一品牌 |

三个切片是同一父包的工作分解与交付顺序，不是独立机器队列，不各设 NEXT_READY/state/writer，不按三条并行支线启动。`product_development` 的既有 package identities、D1-01→P1-03 顺序和各自验收数组不因视觉采用改变；P1-03 直到原义务与 V01–V10 均满足才可 COMPLETE。现有 checker 尚不自动验证新 V 项，必须显式审阅实际证据；不得因此削弱既有检查。

每个切片可形成必要审阅检查点，但不能用 PR 数量替代结果。无法忠实实现的布局/材质/动作须在偏差表写清，不静默换成默认组件，不把旧 P1-01 截图当 V1 已实现。完整交付和差异登记格式见 [Visual Acceptance](design/continuum-v1/ACCEPTANCE.md)。

## 共同交付规则

每包在最新main基线认领；保持一个implementation writer。PR写明实际变化、命令、exact SHA、结果与限制；exact-head通过后合并，复核exact-main。不得force-push覆盖并发工作，不绕过失败CI，不把mock/experimental改标live。内部常规代码决策遵从已采用规格，只有实质产品方向或权限变化才需要重新采用。

当前产品整改不是研究I02–I06的新支线，不读取确认材料，不修改研究结果。若新原型显示某结构没有帮助，先减少展示与实现复杂度，不重新发明五套产品方案。
