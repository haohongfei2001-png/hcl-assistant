# Product acceptance matrix

以下是待实现义务，不是已跑PASS。L0只检查规划、枚举、链接与边界。实施closure必须给command、SHA、fixture lineage、实际结果和限制。

| ID | 正向义务 | 负向义务 | 首包 |
|---|---|---|---|
| A01 | raw/source版本重启往返 | 错hash或截断仍标完整 | L1-01 |
| A02 | 幂等event/run | 同key异payload与半提交 | L1-01 |
| A03 | 有序state version | 旧标签页覆盖新更正 | L1-01 |
| A04 | 人物归属局部更正 | 全局同名合并 | L1-02 |
| A05 | 独立支持保留 | 撤回即否定/重复算独立 | L1-02 |
| A06 | absence依赖被新证据失效 | 只追正向引用 | L1-02 |
| A07 | event/record/receipt分开 | 迟到信息倒灌过去 | L1-02 |
| A08 | 假设分支 | 污染实际背景 | L1-02 |
| A09 | 临时正文不持久 | 日志/摘要/备份留副本 | L1-03 |
| A10 | stop/delete传播 | cache/Explain恢复删除内容 | L1-03 |
| A11 | 三套权限 | 文件扩权/cross-topic偷带 | L1-03 |
| A12 | 检索更正/挑战/反证 | 只支持旧结论 | L1-03 |
| A13 | 更正+2+2先更正 | Direct忽略前半条输入 | L1-04 |
| A14 | 每回答有controller receipt | 隐藏Base bypass | L1-04 |
| A15 | stream恢复/cancel/retry | 重复调用/过期覆盖 | L1-04 |
| A16 | clean chat/file/keyboard | 常驻Inspector/上传即理解 | L2-01 |
| A17 | 多轮自然修订 | 猜测固化为人格事实 | L2-02 |
| A18 | 未支持中文/指代unresolved | fixture冒泛化 | L2-02 |
| A19 | Explain当次依据可纠正 | 事后造理由/CoT泄漏 | L2-03 |
| A20 | Lab只读且Compare禁用 | 实验写生产/mock升级 | L2-04 |
| A21 | failure/unknown/cost记录 | 删除失败/未知成本填0 | L2-04 |
| A22 | 产品独立导出/运行 | research/确认/secrets导入 | L0-01及全部 |

## 原创轨迹规范

只用原创synthetic；记录source family、用途、预先固定的变化/不变义务。不得把研究失败题改名，不找外部题源。typed mock事件可在测试expected端存在，不能给未来真实模型充hidden gold。

轨迹一：合作不顺→主动联系→更正对方何时知情→撤回猜测。检查局部变化、旧视角、重复证据和无关目标。
轨迹二：临时安排变化→角色压力→较晚自述价值→撤回自述。检查context不变人格、expiry和目标。
轨迹三：同词不同reading→假设换判据→回实际讨论。检查fact/concept/value分离、假设不污染。

L4另用新的非确认材料测真实中文、多轮、合成/Explain忠实性、必要推断、反向伤害、普通任务非干扰与完整费用；不以偏好/长度/节点数/多拒答单独认定增益。

## L2 closure — actual synthetic results

Commands: both root checkers; `python3 -m unittest discover -s tests -v` (90 checks PASS); `npm run build` (typecheck/build PASS); `npm run test:browser` (10 headless Chromium journeys PASS). No tests skipped or removed. Package checkpoint counts and repaired failures are recorded in [execution](EXECUTION.md). Exact tested HEAD and adopted main SHAs are published by hosted CI's materialization/check summaries; branch-local completion is conditional on those checks and merge. No self-SHA is fabricated in this document.

All rows below are PASS **within authored/synthetic/mock coverage**. These are implementation obligations, not arbitrary-language or efficacy results. Test paths name the actual positive, negative and persistence/history evidence.

| ID | Actual evidence | Limit |
|---|---|---|
| A01 | `test_ledger`: restart raw/hash/parse and corrupt/truncated source refusal | UTF-8 TXT/Markdown; 64 KiB |
| A02 | `test_ledger`, `test_controller`, `test_integrated`; browser lost acknowledgement | Scoped keys; retry is a new attempt, not repeated input |
| A03 | `test_ledger`, `test_controller`, `test_integrated` | Conservative account-wide state version |
| A04 | `test_revision` and browser person/time correction | Explicit scoped identities; no general identity resolution |
| A05 | `test_revision`, `test_scenarios`, `test_privacy` | OR-of-AND, deduplicated guess roots and independent-source survival |
| A06 | `test_revision`, `test_integrated` | Conservative absence invalidation within allowed scope |
| A07 | `test_revision`, `test_scenarios`, `test_integrated` | Authored learned/event time; unknown stays unknown |
| A08 | `test_revision`, `test_scenarios`, `test_integrated` | Authored hypothetical snapshot; actual background unchanged |
| A09 | `test_privacy` volatile store/restart and persistent byte inspection | Process-local temporary state; no provider logging path exists |
| A10 | `test_privacy`, `test_explain`, `test_lab`, browser stop/delete/file purge | Simulated local restore deletion replay; no production backup certification |
| A11 | `test_privacy`, `test_integrated`, `test_transport` | Synthetic account identity, explicit perspective access, separate memory scope |
| A12 | `test_privacy`, `test_revision`, `test_integrated` | Whole eligible small-corpus closure, bounded refusal above 100 records |
| A13 | `test_controller`, `test_scenarios` | Scripted correction first; unsupported changes remain unresolved even with arithmetic |
| A14 | `test_controller`, `test_transport` | One governed mock entry; server permit; no provider transport |
| A15 | `test_controller`, `test_transport`, `test_recovery`, browser cancel/retry/lost ack | SSE replay only; interrupted restart UNKNOWN; no blind regeneration |
| A16 | Browser desktop/upload/keyboard/focus/refresh/error/narrow flows | Desktop/headless Chromium; mobile and other browsers untested |
| A17 | Three original trajectories in `test_scenarios` | Source-bound natural mock synthesis, not persistent real cognition |
| A18 | `test_scenarios`, `test_integrated` | Prefix grammar only; arbitrary Chinese/anaphora unresolved |
| A19 | `test_explain` and browser Explain/correction | Recorded binding fidelity; no semantic judge or hidden reasoning |
| A20 | `test_lab` and browser Lab | Read-only MOCK; Compare disabled with L3 gate |
| A21 | `test_controller`, `test_lab`, `test_recovery`, `test_integrated` | Failure/UNKNOWN retained; mock provider cost 0 with explicit source, unknown tokens null |
| A22 | Root repository/planning checks, `test_repository_split`, exact-SHA hosted product-only export | Bounded source/import/credential scan; not universal or cryptographic isolation proof |

Open limits: synthetic identity only; no production authentication, remote retention/deletion guarantees, real user data, real HCL runtime, general language extraction, calibrated cognition or efficacy. Future L4 needs new authorized non-confirmation material. L3 gate is unchanged and unsatisfied.


## L2.5 amendment — experimental runtime bridge obligations

以下均为待实现的 development integration 义务，不是本次 plan amendment 的 PASS：
- A23：exact HCL SHA + artifact/interface digest handshake；floating main/tag、digest/interface mismatch 必须 fail closed。
- A24：capability manifest discovery 保留 PENDING_I06 / EXPERIMENTAL / production_enabled=false；不得把发现即视为 RETAIN。
- A25：request/response serialization 有版本且拒绝未知/越界 payload；confirmation/eval/sealed material 不可进入。
- A26：timeout/error/cancel/unknown transport 保留真实 outcome，不盲重试、不改写旧 receipt。
- A27：selected / executed / output-produced / used-in-answer 分离；支持 UNSUPPORTED / NO_TREATMENT / FAILED / UNRESOLVED。
- A28：至少一条原创 synthetic real-runtime end-to-end smoke；不得使用真实用户私密数据或正式评估 case。
- A29：L2.5 execution 永远不能设置 production activation 或生成 efficacy evidence；L3 仍必须等待 I06 disposition。

L2.5-01 branch acceptance: A23/A24 PASS within the pinned three-file provider-free slice (`test_runtime_handshake`, `test_runtime_acquisition`); actual subprocess handshake READY. A29 policy projection PASS, production_enabled=false / PENDING_I06. Other mechanism execution and A25–A28 remain pending L2.5-02. 104 Python checks, build and all 10 historical browser journeys PASS; external exact-head CI governs adoption.

## L2.5 closure — actual development integration results

126 Python tests, root checkers, typecheck/build, 12 headless browser journeys and the four-path original synthetic real-runtime Controller smoke PASS locally. GitHub exact-head CI repeats these checks; source checkpoints do not self-certify main adoption. Inputs originate in the authored `original_workshop_20261001` family in runtime tests/smoke and its browser sibling; no reused research/evaluation cases. The external artifact is exactly the three allowlisted files at `a8229fcf22eccb851c58502a09ae7cecb346faf5`, with file/Git/tree/artifact/interface/manifest digests in the lock. These are DEVELOPMENT_INTEGRATION_ONLY / NOT_EFFICACY_EVIDENCE.

| ID | Actual evidence | Limit |
|---|---|---|
| A23 | `test_runtime_handshake`, `test_runtime_acquisition`, `test_runtime_execution`: actual process READY, wrong SHA/interface/digest/path and manifest drift refused | Product-owned callable interface; explicit reviewed repin required |
| A24 | Separate discovered manifest snapshot, EXPERIMENTAL/PENDING_I06, production_enabled=false; retention/unknown-capability negatives | Two projected capabilities only; other eight unbridged |
| A25 | Strict versioned request/response tests, source hash/span/quote validation, unknown/duplicate/nonfinite/bound refusal | Original synthetic sources only; metadata is not a private-data detector |
| A26 | Real process timeout, active cancellation/reaping, exit/garbage/oversize response; Controller cancel/retry/concurrent revision | Execution uncertainty remains null + UNKNOWN, no automatic retry |
| A27 | Operation flags/output refs, same-run Explain/Lab and deletion tests | Public expression syntax only; no private truth or broad semantics |
| A28 | Mandatory actual-runtime Python E2E, four-path CLI smoke, two new headless browser journeys | Original named English modal source; Chinese/prose no-treatment preserved |
| A29 | Controller refuses persistent/Topic/non-synthetic/unconfigured/typed-command paths; temporary body byte/restart tests; unchanged Pages tests | No production activation, efficacy or provider authorization |

Open limits: no integration of the entire research runtime, no provider-backed extraction/generation, no general Chinese/pronoun understanding, no persistent HCL cognitive state, no production privacy or efficacy certification. The four L3/I06 gates remain unmet. Existing L0–L2 package evidence and historical failures remain unchanged.
