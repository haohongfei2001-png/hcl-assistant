import React from 'react';
import {flagText,operationSummary,outcomeText,type InspectionFact,type InspectionViewModel} from './inspection-model';
export type {InspectionViewModel,InspectionOperation,InspectionInformation,InspectionFact,InspectionFlag} from './inspection-model';

function Facts({items}:{items:InspectionFact[]}){
 return <dl>{items.map((fact,index)=><React.Fragment key={`${fact.label}-${index}`}><dt>{fact.label}</dt><dd style={{overflowWrap:'anywhere'}}>{fact.value??'未知（未记录）'}</dd></React.Fragment>)}</dl>;
}
const gates:Record<string,string>={I06_DISPOSITION:'I06 处置结论',PINNED_PERMITTED_RUNTIME_ARTIFACT:'固定且获准的生产运行时与接口',PRODUCT_ADAPTER_SCOPE_VALIDATION:'产品适配范围验证',EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION:'明确执行与数据授权'};

/** Pure presentation only: no fetching, writes, model calls, or inferred execution receipts. */
export function InspectionView({value}:{value:InspectionViewModel}){
 const mode=value.mode==='DEVELOPMENT_CHAT'?'只读开发聊天记录':value.mode==='EXPERIMENTAL'?'只读实验记录':value.mode==='MOCK'?'只读模拟记录':value.mode==='STATIC_PREVIEW'?'只读静态演示记录':'只读记录（模式未知）';
 return <div data-inspection-run={value.runId}>
  <h2>{mode}</h2>
  <p>{value.mode==='DEVELOPMENT_CHAT'?'通过 Controller 的开发态模型调用；专门 HCL 参与范围以本次记录为准，生产禁用。':value.mode==='EXPERIMENTAL'?'固定开发运行时，生产禁用。':value.mode==='STATIC_PREVIEW'?'Browser-only 脚本演示，未接入 backend、真实 HCL 或 provider。':value.mode==='MOCK'?'MOCK 记录，未接入真实 HCL。':'记录模式未提供，不能推定为模拟或实际执行。'} 仅展示本次显式记录，不是隐藏思维。查看记录不会重新分析。</p>
  <p>运行结果：{outcomeText(value.outcome)}{value.pending===true?' · 本次运行尚未结束':''}</p>
  {value.treatment!==null&&<p>专门处理：{outcomeText(value.treatment)}</p>}
  {value.outdated===true&&<p>这是当时的运行记录；当前记录版本不同，不据此推定发生了重要背景变化。重新分析应创建新运行，不会为旧回答补写依据。</p>}
  {value.redacted&&<p role="status">原文、依据和操作内容已按当前权限隐去；不能从缓存恢复。</p>}
  <section aria-label="当次输入与覆盖"><h3>当次输入与覆盖</h3><p style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{value.input??(value.redacted?'当时的输入不可用':'未记录可展示的输入')}</p><p>覆盖：{value.coverage==='FULL_WITHIN_DECLARED_SCOPE'?'仅在声明范围内覆盖，不代表完整语义理解':value.coverage==='PARTIAL'?'部分覆盖':value.coverage==='UNAVAILABLE'?'不可用':value.coverage??'未知（未记录）'}</p></section>
  <section aria-label="信息与解释"><h3>信息与解释</h3>{value.information.length?<ul>{value.information.map((item,index)=><li key={`${item.id}-${index}`}><p>{item.label}{item.status?' · '+item.status:''}</p><p style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{item.text}</p></li>)}</ul>:<p>{value.redacted?'相关内容不可用':'没有可展示的已记录背景或专门输出；不事后补写结构。'}</p>}{value.uncertainties.length>0&&<><h4>缺口与未解决项</h4><ul>{value.uncertainties.map((item,index)=><li key={index}>{item}</li>)}</ul></>}</section>
  <section aria-label="执行记录"><h3>执行记录</h3>
   {value.operationRecords==='unavailable'?<p>操作内容按当前权限不可用；不能推定未执行。</p>:value.operations.length===0?<p>{value.operationRecords==='unrecorded'?'未记录操作回执；执行、输出与使用情况未知。':value.selectedCapabilities?.length===0?'本次未选择专门操作；这不等于失败或不支持普通回答。':'没有可展示的操作回执；不能推定执行成功。'}</p>:<ul>{value.operations.map((operation,index)=><li key={`${operation.id}-${index}`}><h4>{operation.label}</h4><p>{operationSummary(operation)}</p><dl><dt>已选择</dt><dd>{flagText(operation.selected)}</dd><dt>已执行</dt><dd>{flagText(operation.executed)}</dd><dt>已产生结果</dt><dd>{flagText(operation.resultProduced)}</dd><dt>已用于本次回答</dt><dd>{flagText(operation.usedInAnswer)}</dd><dt>缓存复用</dt><dd>{flagText(operation.cacheReused)}</dd></dl><details><summary>此操作的记录详情</summary><Facts items={[{label:'记录状态',value:operation.status},...operation.details]}/></details></li>)}</ul>}
   {value.errors.length>0&&<><h4>错误记录</h4><ul>{value.errors.map((item,index)=><li key={index}>{item}</li>)}</ul></>}
  </section>
  <p>运行完成、产出结构或记录为已使用，都不能证明理解正确或 HCL 的独立增益。效力状态：{value.efficacy??'未知（未记录）'}。</p>
  <details><summary>当次回答记录</summary><p style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{value.answer??(value.redacted?'回答按当前权限不可用':'没有可展示的已发布回答')}</p></details>
  <details><summary>运行身份、路由与版本</summary><Facts items={value.technicalFacts}/></details>
  <details><summary>运行时来源与接口</summary><Facts items={value.provenance}/></details>
  <details><summary>Usage 与费用记录</summary><p>{value.usageScope??'统计范围未知（未记录）'}</p><Facts items={value.usage}/><p>0 仅代表记录明确给出的数值；未知 tokens 或费用不按 0 计算。这里的耗时与费用不证明真实模型性能或效果。</p></details>
  <details><summary>Research Compare 的能力门槛</summary><p>当前仅提供规格和门槛说明，未开放 Compare 执行。没有合格双侧运行时不生成对比结果；无处理差异不能检验专门增益，一侧失败也不代表另一侧获胜。</p>{value.compareGate.length?<ul>{value.compareGate.map(gate=><li key={gate}>{gates[gate]||gate}</li>)}</ul>:<p>未记录可核对的授权门槛。</p>}</details>
 </div>;
}
