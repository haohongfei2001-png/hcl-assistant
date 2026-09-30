# HCL Assistant — Product Control Plane

这是 HCL Assistant 的独立 public 产品仓库。唯一 canonical product source of truth 是 `haohongfei2001-png/hcl-assistant/main`；不是研究运行时，也不是已上线产品。

**产品：Assistant → 按需 Explain → 高级 HCL Lab。所有生产回答由 HCL Interaction Controller 管理。**

## Work 从这里开始

1. 阅读 [STATUS](STATUS.md)、[DEVELOPMENT_PLAN](DEVELOPMENT_PLAN.md)、[AGENTS](AGENTS.md)。
2. 阅读 [Product Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)。
3. 按 [稳定契约](contracts/PRODUCT_CONTRACTS_V1.md)、[工作包](docs/L0_L2_WORK_PACKAGES.md) 和 [验收矩阵](docs/ACCEPTANCE_MATRIX.md) 执行唯一 NEXT_READY。
4. 检查本仓库 remote main 和相关 PR。只在本产品仓库工作，不运行研究工作流。

当前是 **L0 COMPLETE / physical split COMPLETE / L1–L2 development-ready**；L1/L2 尚未开始。迁移声明以本仓库 main 和 exact-SHA CI 为准；工作分支不是完成证据。产品基础设施、mock 和真实认知效力是不同状态。

## 仓库边界

本仓库根目录承担唯一产品控制面。研究仓库仅负责 cognition runtime、research、evaluation/evidence 和 I02–I06；旧产品目录为 retired migration source，不能双写或继续执行旧队列。

physical split = COMPLETE；repository isolation = COMPLETE at repository boundary。公开仓库分离不是生产身份/数据隐私或网络隔离认证。L1/L2 仍仅 synthetic/provider-free；真实数据、凭据、部署与 L3 仍需原有 I06/运行时/授权/安全门槛，不因分仓自动许可。

见 [边界决策](docs/BOUNDARY_AND_ISOLATION.md)、[迁移记录](docs/REPOSITORY_MIGRATION.md) 与 [迁移清单](control/repository-migration.json)。

## 初始结构

- `contracts/`：稳定产品契约与 capability manifest。
- `control/`：机器可读 live queue；不存用户数据。
- `docs/`：工作包、UX、验收、隔离与只读研究基线。
- `apps/`：未来 Web/API；L0 仅目录说明。
- `packages/`：未来 controller/context/store/adapter；L0 不实现运行时。
- `scripts/`、`tests/`：仅 provider-free planning/setup 验证。

检查（在本仓库根目录）：

```sh
python3 scripts/check_planning.py
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -v
```

Hosted CI：`HCL Assistant Planning`。它按 exact SHA 仅物化本独立仓库根，不读取研究仓库；输出 exact SHA、产品内容 digest、迁移/凭据边界检查和测试结果。不访问 provider 或继承研究凭据。检查通过不是 persistent cognition 已实现或 HCL efficacy 证明。
