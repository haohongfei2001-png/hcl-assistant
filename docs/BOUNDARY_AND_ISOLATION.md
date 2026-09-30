# Repository boundary and research isolation — ADR 001

## Adopted and completed repository split

Canonical产品仓库：`haohongfei2001-png/hcl-assistant`，public，仓库根。迁移main/check验收后physical split = COMPLETE；repository isolation = COMPLETE at repository boundary。只有此仓库main控制HCL Assistant。

`human-cognition-layer`负责cognition runtime、research、evaluation/evidence及I02–I06；`hcl-assistant`负责Assistant Web、persistence、Controller product layer、Explain、Lab及L0–L5。未来只通过明确获准的版本化runtime artifact/interface消费能力，不能隐式导入研究源树。

旧产品目录是retired migration provenance，不是第二canonical或writer；并发研究需要延后清理时也不改变这一点。见[迁移记录](REPOSITORY_MIGRATION.md)。

## Verified versus not implied

迁移仅保留21个产品文件及其1个专用CI，记录逐文件Git hash。没有复制研究Git历史、runtime代码、evaluation材料、confirmation sources/gold、protected artifacts、credential、provider secrets或真实私密用户数据。产品baseline中的历史引用只保留为文档指针，不是研究数据导入或读取授权。

常规planning workflow仅获取本产品仓库exact SHA；测试进程不接收API凭据。物化前拒绝unsafe paths、symlinks和submodules，离线运行planning与边界检查。public内容凭据模式扫描是有界检查，不是万能秘密检测。

分仓不使public研究内容对有网络权限的人不可见，不撤销Owner在其他工具中的跨仓权限，也不等于生产身份/存储隔离。runtime/network sandbox及tenant/privacy控制仍属产品实施和验收；不要夸大ACL隔离。

## Runtime bridge amendment

L1/L2 仍是 synthetic/mock、零 provider transport。L2.5 新增一个严格 development-only 例外：产品可从 `haohongfei2001-png/human-cognition-layer` 的 exact commit SHA 读取 allowlisted runtime/interface material，并在 synthetic/non-confirmation 输入上执行当前可用 HCL mechanism。不得使用浮动 main/tag、confirmation/evaluation/sealed material、真实私密数据或正式评估 outcome 做 case-specific tuning。

L2.5 bridge 不改变仓库职责：研究仓库仍独立推进 I02–I06，产品仓库不修改研究 runtime/evaluation。Bridge 只消费版本化接口/工件，不把研究仓库整体变成产品 source tree。若某 mechanism 需要 provider-backed execution，默认未授权，必须另有明确 development execution authorization。

正式 L3 仍需 I06 disposition、production-permitted runtime artifact/interface、adapter scope 验证以及执行/数据授权；其职责为 Production Capability Activation，而非首次 transport 建设。physical split 已满足。

禁止读取/复制confirmation source/gold、受保护artifact、evaluation credentials、provider secrets和sealed LongMemEval。禁止依I03–I06 outcome调产品prompt、把confirmation case当demo、从产品feedback改frozen evaluation。必要通用问题用新原创非确认材料复现。

## Allowed share and engineering boundaries

共享只限 runtime version、stable interface、capability disposition、limitations 与已批准的通用改进。L0–L2 不导入研究 Python。L2.5 只可按 exact SHA + allowlisted paths/material 建立 development bridge；不得 clone/archive/mount 整个研究仓库为产品依赖，不添加研究 submodule，不读取 eval/data/reports 中受保护材料，不调用研究 workflow/runner/credential store。

产品workflow permissions为contents:read，无pull_request_target、无研究secrets、无隐藏provider调用。只获取本仓库根并校验blob hash；读取token只在物化步骤提供，测试步骤没有凭据。不以研究CI替代产品CI。

account data permission、人物perspective access、persistence/reuse permission仍独立。数据和cache key包含tenant/conversation/topic/perspective/policy/version；Lab与Assistant不相互写入。上述既定契约不因迁移改变。
