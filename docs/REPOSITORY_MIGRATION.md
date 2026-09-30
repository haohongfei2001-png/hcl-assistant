# Physical repository migration record

## Immutable origin and authority

Source repository：`haohongfei2001-png/human-cognition-layer`。
Source commit：`2e54a12cad4441f4a363f852b1c2864b9254c243`。
Source subtree：`products/hcl-assistant/`，Git tree `c9e43ef2071100c5a51ecc56001bd7f74830fd12`。
Additional allowed source：`.github/workflows/hcl-assistant-planning.yml`，blob `65d8f0673f8923578f077ecc349ecae3364f274a`。
Destination：`haohongfei2001-png/hcl-assistant/main`，仓库根。
Destination initial parent：`27de9b376b5efbc95428d2ae61e0b3fa387106bb`。

完整21个canonical产品文件与专用workflow均保留。迁移清单逐项记录源Git hash、目标路径与迁移处置。未修改文件由离线Git blob hash检查，正文末尾换行差异另标记；已调整文件的最终hash由exact-SHA CI内容receipt记录。产品迁移提交只继承产品Initial commit，不含研究Git历史。

## Relocation-only changes

更新canonical repository/root、COMPLETE split/L0状态、已满足split gate、Work写入范围、规划边界断言及对应负面测试、CI根目录读取。保留九个工作包、产品原则、capability candidates、semantic contracts与I02–I06次序。没有L1实现，没有provider调用。

原生GitHub文件/tree/commit操作迁移，不使用研究全仓checkout/archive。一次性云端bootstrap方案未执行，未进入新仓库；常规产品CI只读新仓库，不回源研究仓库。

## Canonical cutover and source retirement

迁移PR合并且exact-main全部通过后，本仓库main是唯一canonical产品事实源。旧子树为retired provenance，不能继续承载产品队列。专门产品Work从此处接管，禁止在旧目录开始L1。

只在新仓库验收成功后，才允许单独极小研究PR将旧目录替换为指针README、停用旧产品专用workflow。若研究writer活跃，物理清理DEFERRED_CLEANUP；这不推迟唯一事实源切换。最终清理处置及exact-main证据记录在迁移PR评论/交接，不把未清理解释为双canonical。

## Limits and stopping

source inventory限定产品文档、checks与metadata；没有confirmation source/gold、protected evaluation artifacts、evaluation/provider credentials、LongMemEval、真实用户私密数据或研究runtime。路径、import与凭据模式检查不是万能秘密检测或生产隐私认证。两个仓库均public，隔离只声明repository/build/control boundary。

physical split在验收后的main为COMPLETE；L0保持COMPLETE；NEXT_READY保持`L1-01_EVENT_SOURCE_STATE_LEDGER`；L1/L2仍NOT_STARTED。I06/runtime/授权/安全门槛仍然有效。本轮执行者在分仓完成后停止。
