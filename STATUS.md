# HCL Assistant Product Status

## 当前产品阶段

**L0 = COMPLETE / L1_L2_DEVELOPMENT_READY — PLANNING/SETUP ONLY**

**NEXT_READY: L1-01_EVENT_SOURCE_STATE_LEDGER**

- physical split = COMPLETE
- repository isolation = COMPLETE at repository boundary
- 唯一 canonical product source of truth：`haohongfei2001-png/hcl-assistant/main`。
- 产品根目录：本仓库根（`.`），不再嵌套于研究仓库。
- Assistant UI / persistent Controller / Context store：NOT_IMPLEMENTED。
- L1/L2：NOT_STARTED。Real HCL runtime：NOT_INTEGRATED / GATED_AFTER_I06。
- 本轮及 L0–L2 授权 provider calls/spend：0 / 0。Efficacy：UNTESTED。

## 迁移与 evidence

L0 于研究 PR #279、`2e54a12cad4441f4a363f852b1c2864b9254c243` 完成，原 exact-head / exact-main 28 项 planning/setup 检查通过（main run 36716075308）。这是历史产品 setup 证据，不是研究效力。

本次将该提交的完整21文件产品子树及1个专用workflow迁移到本仓库根。源Git hash及迁移处置见 [清单](control/repository-migration.json)，迁移/退役规则见 [记录](docs/REPOSITORY_MIGRATION.md)。

分仓完成声明仅在本仓库迁移PR合入且exact-main HCL Assistant Planning通过后生效；工作分支上的声明不是完成证据。实际main SHA、文件digest及检查结果由GitHub/CI给出，不把自身SHA伪造为静态字段。

## Remaining gates

物理分仓不再是未完成blocker。Repository separation不等于生产tenant隔离、网络sandbox或对所有账号权限的认证；两个仓库均为public。

L1/L2仍只允许synthetic/provider-free。真实数据及部署仍需明确授权和产品安全/隐私验收；L3另需I06 disposition、固定获准runtime/interface artifact、产品adapter scope验证。未授权任何研究数据或源代码导入。

## Work与停止点

本轮迁移执行者在exact-main验证和旧目录安全退役/延后清理决定后停止，不开始L1-01。下一位专门产品Work按本仓库README、AGENTS、DEVELOPMENT_PLAN及契约认领唯一writer，从L1-01开始。

旧研究产品目录只保留retired migration provenance身份；即使物理清理deferred，也绝不是第二产品队列或事实源。研究I02 → I03 → I04 → I05 → I06不变。
