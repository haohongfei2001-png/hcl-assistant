# Evidence boundary

`test_planning.py`只测L0控制面完整性、状态声明、契约区分、路径与adoption gate。它不测试真实cognition、自动语义分类、persistent store或完整browser体验。原28项planning测试全部保留；迁移另增repository-root/边界测试。L1/L2必须增加对应实际behavioral tests，不能以这些静态检查代替。

发布的capability JSON Schema可供标准Draft2020-12工具验证；当前stdlib checker是针对产品契约的定向验证，不冒充通用JSON Schema引擎。运行记录必须注明检查范围。

在本独立仓库根运行planning checker、repository checker及unittest。迁移清单检查源文件完整性、未修改内容及public文件中的常见凭据模式；它不是任意秘密不存在或生产安全已经实现的证明。

L1/L2 adds actual SQLite/restart, revision, policy, Controller, loopback HTTP/SSE, authored scenario, Explain, Lab, recovery and integrated boundary/race tests. `tests/browser/assistant.spec.js` drives the HTTP-backed React UI in headless Chromium, including correction during streaming, stop/delete after refresh, raw-file deletion, and lost-ack idempotent replay. Mock and real evidence remain separate. Synthetic fixture lineage and limits are in `docs/SYNTHETIC_SCENARIOS.md`. Build/dependency caches and test artifacts are excluded from public-content scanning; original source provenance remains pinned as migration history.
