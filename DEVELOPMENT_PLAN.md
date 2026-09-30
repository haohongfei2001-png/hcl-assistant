# HCL Assistant Live Development Plan

Canonical product policy: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md). Live facts: [STATUS](STATUS.md). Package detail: [L0–L2](docs/L0_L2_WORK_PACKAGES.md). Machine mirror: `control/plan.json`.

**NEXT_READY: L1-01_EVENT_SOURCE_STATE_LEDGER**（L0已完成；迁移exact-main检查后交给专门产品Work，本轮不实现）。

## Live queue

| ID | 交付 | 依赖 | 当前状态 |
|---|---|---|---|
| L0-01 | canonical product contracts + execution setup | owner adopted direction | COMPLETE |
| L1-01 | event/source/state ledger | L0-01 | NEXT_READY |
| L1-02 | revision, dependency invalidation, historical state | L1-01 | WAITING_DEPENDENCY |
| L1-03 | privacy, expiry, scoped retrieval and counterevidence | L1-02 | WAITING_DEPENDENCY |
| L1-04 | always-on Controller, run/stream lifecycle, mock adapter | L1-03 | WAITING_DEPENDENCY |
| L2-01 | desktop chat, Topic, files, streaming controls | L1-04 | WAITING_DEPENDENCY |
| L2-02 | multi-session synthetic cognition + natural synthesis | L2-01 | WAITING_DEPENDENCY |
| L2-03 | Explain, correction and memory/privacy UX | L2-02 | WAITING_DEPENDENCY |
| L2-04 | Lab shell + integrated L2 acceptance/handoff | L2-03 | WAITING_DEPENDENCY |

九包是行为闭环，不是九个PR指标；可以合并相邻稳定切片，不按字段碎分PR。本轮只迁移，不重新制定工作包。

## Later gates

物理独立仓库已完成，列为satisfied gate，不再是未完成依赖。

L3 REAL_RUNTIME_INTEGRATION：I06 disposition + pinned permitted artifact/interface + explicit execution budget/access + product adapter scope validation。未具备不得接真实HCL。

L4 PRODUCT_MULTI_TURN_VALIDATION：独立于I02–I06 confirmation的新材料；覆盖中文、迟到信息、修订、Explain忠实性、普通任务非干扰、memory污染和完整费用。

L5 EVIDENCE_DRIVEN_OPTIMIZATION：保留实用路径，删除/简化无收益复杂度；不为排行榜修改产品机制。

## 执行规则

L0已完成。本轮迁移执行者完成exact-main核验和旧目录处置决定后停止，不开始L1。后续产品Work在L1/L2依赖满足时自主推进实现、测试、修复、PR与合并。修改live queue同时更新STATUS与control/plan.json，不把每日状态写进Master Plan。每次以实际main、head CI、receipt为准；只更新本产品仓库控制面，不写研究仓库或retired产品目录。
