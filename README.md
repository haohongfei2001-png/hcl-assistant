# HCL Assistant — synthetic/mock product

Assistant → 按需 Explain → 高级只读 HCL Lab。所有模拟输入、修订和回答都经过 Interaction Controller。

**L1/L2 = provider-free implemented and locally verified; real HCL NOT_INTEGRATED.** 唯一 canonical 产品事实源仍是 `haohongfei2001-png/hcl-assistant/main`；采用以 exact-head CI、合并和 exact-main CI 为准。见 [STATUS](STATUS.md)、[DEVELOPMENT_PLAN](DEVELOPMENT_PLAN.md)、[AGENTS](AGENTS.md)、[Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)、[contracts](contracts/PRODUCT_CONTRACTS_V1.md)、[工作包](docs/L0_L2_WORK_PACKAGES.md)、[验收矩阵](docs/ACCEPTANCE_MATRIX.md) 和 [执行证据](docs/EXECUTION.md)。

Python >=3.11 标准库 / SQLite；React/TypeScript/Vite 与 headless Playwright 精确版本在 npm lock。无托管服务、provider transport、研究代码或部署依赖。SQLite 与临时测试输出不入 Git。

## Run the synthetic desktop locally

仅使用合成数据。HTTP 服务固定 loopback，身份为隔离测试身份，不是生产认证。临时会话正文只留进程内存，重启丢失。持久会话可重启恢复；中断 run 标 UNKNOWN，不自动重调 adapter。

```sh
npm ci --ignore-scripts
mkdir -p .local
python3 -m apps.api.server --database .local/mock.sqlite
# In a second shell, from this repository root:
npm run dev
```

Open `http://127.0.0.1:5173`. Text/Markdown/UTF-8 only, 64 KiB; registration does not certify understanding. Optional [authored mock grammar and original trajectories](docs/SYNTHETIC_SCENARIOS.md) demonstrate scoped background/revision. Arbitrary text remains unresolved; no general semantic/Chinese efficacy claim.

## Verify

```sh
python3 scripts/check_planning.py
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
npm run build
npx playwright install chromium --only-shell
npm run test:browser
```

Hosted `HCL Assistant Planning` materializes only this public product repository at exact SHA, runs root checks and synthetic behavior/browser acceptance, and publishes SHA/content digest/results in its job summary. Checks certify the tested mock contracts, not production privacy, real HCL semantics or efficacy.

L2 closes with **STOP_WITH_HANDOFF_L3_GATED**. L3 requires I06 disposition, a pinned permitted runtime artifact/interface, product adapter scope validation, and explicit execution/data authorization. No real integration, paid API, real/private data, public deployment or external onboarding is authorized by L1/L2 completion. Physical repository split is complete; it is not an outstanding blocker or cryptographic isolation claim.
