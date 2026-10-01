/** Display-only projection. Neither this model nor its test fixtures are execution receipts. */
export type InspectionFlag = boolean | null;
export type InspectionFact = {label:string; value:string | null};
export type InspectionOperation = {
 id:string; label:string; status:string | null;
 selected:InspectionFlag; executed:InspectionFlag; resultProduced:InspectionFlag;
 usedInAnswer:InspectionFlag; cacheReused:InspectionFlag;
 details:InspectionFact[];
};
export type InspectionInformation = {id:string; label:string; text:string; status:string | null};
export type InspectionViewModel = {
 runId:string;
 mode:'MOCK' | 'EXPERIMENTAL' | 'STATIC_PREVIEW' | 'DEVELOPMENT_CHAT' | 'UNKNOWN';
 outcome:string | null; treatment:string | null; pending:InspectionFlag;
 outdated:InspectionFlag; redacted:boolean; input:string | null; answer:string | null;
 coverage:string | null; selectedCapabilities:string[] | null;
 operations:InspectionOperation[];
 operationRecords:'recorded' | 'unrecorded' | 'unavailable';
 information:InspectionInformation[]; uncertainties:string[]; errors:string[];
 technicalFacts:InspectionFact[]; provenance:InspectionFact[]; usage:InspectionFact[];
 usageScope:string | null; efficacy:string | null; compareGate:string[];
};

export function inspectionFlag(value:unknown):InspectionFlag {
 return typeof value==='boolean' ? value : null;
}
export function flagText(value:InspectionFlag):string {
 return value===true ? '是' : value===false ? '否' : '未知（未记录）';
}
const outcomes:Record<string,string>={
 COMPLETED:'运行完成',PARTIAL:'部分完成',UNRESOLVED:'尚未解决',FAILED:'执行失败',
 REFUSED:'请求被拒绝',CANCELLED:'已取消',UNKNOWN:'结果未知',UNSUPPORTED:'不支持此输入或范围',
 NO_TREATMENT:'未产生专门处理结果',EXECUTED:'已记录实际处理',PENDING:'等待执行',RUNNING:'执行中',
 MOCK_AUTHORED_OUTPUT:'已记录模拟输出',NOT_SELECTED:'未选择专门处理',NOT_EXECUTED:'未执行',NO_OUTPUT:'执行后无输出',
};
export function outcomeText(value:string | null):string {
 return value===null ? '未知（未记录）' : outcomes[value] || value;
}
export function operationSummary(operation:InspectionOperation):string {
 if(operation.status && ['FAILED','REFUSED','CANCELLED','UNKNOWN','UNRESOLVED','UNSUPPORTED','NO_TREATMENT'].includes(operation.status))return outcomeText(operation.status);
 if(operation.executed===null)return '执行情况未知；不能从已选择推定已执行';
 if(operation.selected===false && operation.executed===false)return '未选择、未执行专门处理';
 if(operation.selected===true && operation.executed===false)return '已选择，尚未执行';
 if(operation.executed===true && operation.resultProduced===false)return '已执行，未产生结果';
 if(operation.resultProduced===true && operation.usedInAnswer===false)return '已产生结果，未用于本次回答';
 if(operation.resultProduced===true && operation.usedInAnswer===true)return '结果已记录为用于本次回答；不证明因果增益';
 return '仅展示已记录的状态；缺失信息保持未知';
}

type ObjectValue = Record<string,unknown>;
function object(value:unknown):ObjectValue {
 return value!==null && typeof value==='object' && !Array.isArray(value) ? value as ObjectValue : {};
}
function text(value:unknown):string | null {return typeof value==='string' ? value : null;}
function scalar(value:unknown):string | null {
 return typeof value==='string' || typeof value==='boolean' || (typeof value==='number' && Number.isFinite(value)) ? String(value) : null;
}
function strings(value:unknown):string[] | null {
 return Array.isArray(value) && value.every(row=>typeof row==='string') ? value : null;
}
function items(value:unknown):unknown[] {return Array.isArray(value) ? value : [];}
function facts(source:ObjectValue,fields:[string,string][]):InspectionFact[] {
 return fields.map(([key,label])=>({label,value:scalar(source[key])}));
}
const kinds:Record<string,string>={USER_REPORTED_EVENT:'用户报告',USER_GUESS:'用户猜测',CHARACTER_SELF_REPORT:'人物自述',THIRD_PARTY_REPORT:'转述',SYSTEM_INTERPRETATION:'系统解释',CONDITIONAL_RULE:'条件判据',CORRECTION:'更正',RETRACTION:'撤回',HYPOTHETICAL:'假设'};

/** Only accepts the current read-only local Lab envelope. Pages must explicitly build its own view model. */
export function projectLocalInspection(payload:unknown,requestedRunId:string):InspectionViewModel {
 const envelope=object(payload),run=object(envelope.run),receipt=object(run.run_receipt);
 if(envelope.read_only!==true || envelope.compare_enabled!==false || run.run_id!==requestedRunId || (receipt.run_id!==undefined && receipt.run_id!==requestedRunId))throw new Error('检查记录身份或只读边界不匹配，未显示或导出');
 const redacted=run.redacted===true,context=object(run.selected_context),usage=object(receipt.usage),cost=object(usage.cost);
 const selected=strings(run.selected_capability_ids),rawOperations=Array.isArray(run.operation_receipts) ? run.operation_receipts : null;
 const operations:InspectionOperation[]=redacted ? [] : (rawOperations || []).map((item,index)=>{
  const row=object(item);
  return {id:text(row.operation_id) || `unidentified-${index}`,label:text(row.capability_id) || '未标明能力的操作',status:text(row.status),
   selected:inspectionFlag(row.selected),executed:inspectionFlag(row.executed),resultProduced:inspectionFlag(row.result_produced),usedInAnswer:inspectionFlag(row.used_in_answer),cacheReused:inspectionFlag(row.cache_reused),
   details:[...facts(row,[['operation_id','操作 ID'],['publication_status','发布状态'],['cache_status','缓存状态'],['model_calls','模型调用记录'],['native_receipt_digest','原始回执摘要']]),{label:'输出 ID',value:strings(row.output_ids)?.join(', ') ?? null}]};
 });
 // A selection without an operation receipt proves selection only, never execution or output.
 if(!redacted)for(const capability of selected || [])if(!items(rawOperations).some(item=>object(item).capability_id===capability))operations.push({id:`selection-${capability}`,label:capability,status:null,selected:true,executed:null,resultProduced:null,usedInAnswer:null,cacheReused:null,details:[]});
 const information:InspectionInformation[]=redacted ? [] : items(context.records).flatMap((item,index)=>{
  const row=object(item),content=text(row.content);return content===null ? [] : [{id:text(row.record_id)||`context-${index}`,label:kinds[text(row.kind)||'']||text(row.kind)||'已记录背景',text:content,status:text(row.epistemic_status)}];
 });
 if(!redacted)for(const [index,item] of items(run.runtime_outputs).entries()){
  const row=object(item),quote=text(row.quote);if(quote!==null)information.push({id:text(row.output_id)||`output-${index}`,label:'运行时返回的来源显式表达',text:quote,status:text(row.epistemic_status)});
 }
 const preparation=object(run.answer_preparation),answer=object(run.answer),provenance=object(receipt.bridge_provenance);
 return {
  runId:requestedRunId,mode:envelope.mode==='DEVELOPMENT_CHAT'?'DEVELOPMENT_CHAT':envelope.mode==='EXPERIMENTAL'?'EXPERIMENTAL':envelope.mode==='MOCK'?'MOCK':'UNKNOWN',outcome:text(receipt.outcome),treatment:text(receipt.actual_treatment),
  pending:inspectionFlag(run.pending),outdated:inspectionFlag(run.outdated),redacted,input:redacted?null:text(run.input_text),answer:redacted?null:text(answer.text),coverage:text(context.coverage),
  selectedCapabilities:selected,operations,operationRecords:redacted?'unavailable':rawOperations===null?'unrecorded':'recorded',information,
  uncertainties:redacted?[]:[...new Set([...(strings(preparation.material_uncertainties)||[]),...(strings(answer.material_uncertainties)||[]),...items(run.unresolved_updates).flatMap(item=>{const reason=text(object(item).reason);return reason===null?[]:[reason]})])],
  errors:[...new Set([...(strings(run.errors)||[]),...(strings(receipt.errors)||[])])],
  technicalFacts:[{label:'Run ID',value:requestedRunId},...facts(run,[['route','路由'],['state_version_before','状态版本（前）'],['state_version_after','状态版本（后）'],['snapshot_id','Snapshot ID']]),...facts(object(receipt.provider),[['requested_model','请求模型'],['actual_model','实际模型'],['thinking','思考模式'],['reasoning_effort','推理资源设置'],['finish_reason','结束原因'],['send_state','请求发送状态'],['request_id','Provider request ID']]),...facts(receipt,[['attempt_id','Attempt ID'],['mode','回执模式'],['runtime_hash','运行时摘要'],['config_hash','配置摘要'],['production_enabled','生产启用'],['evidence_class','证据类型'],['gain_assessment','增益评估']])],
  provenance:facts(provenance,[['source_repository','运行时仓库'],['source_commit_sha','精确运行时 SHA'],['interface_version','接口版本'],['interface_digest','接口摘要'],['artifact_digest','Artifact 摘要'],['bridge_version','Bridge 版本'],['implementation_id','实现 ID'],['runtime_version','运行时版本'],['native_runtime_version','原生运行时版本'],['bridge_artifact_digest','Bridge artifact 摘要'],['serialization_version','序列化版本'],['receipt_version','回执版本'],['config_hash','配置摘要'],['capability_manifest_digest','能力清单摘要'],['mode','来源模式'],['production_enabled','生产启用'],['evidence_class','证据类型'],['efficacy','效力状态']]),
  usage:[...facts(usage,[['provider_calls','Provider calls'],['adapter_invocations','Adapter invocations'],['input_tokens','输入 tokens'],['output_tokens','输出 tokens'],['reasoning_tokens','推理 tokens（仅计数）'],['latency_ms','本次记录耗时（毫秒）']]),...facts(cost,[['amount','费用金额'],['currency','币种'],['source','费用来源']])],
  usageScope:text(envelope.usage_scope),efficacy:text(envelope.efficacy),compareGate:strings(envelope.compare_gate)||[],
 };
}
