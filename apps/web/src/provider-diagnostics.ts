// Only fixed protocol metadata is eligible for the consumer receipt. Never
// render arbitrary upstream error text, headers, bodies, or hidden reasoning.
const reasons:Record<string,string>={
 wall_timeout:'请求等待超过时限',connect_timeout:'建立连接超时',timeout:'连接等待超时',transport_error:'模型连接中断',early_eof:'响应在完成前结束',http_error:'模型服务返回错误状态',cancelled:'请求已取消',model_mismatch:'返回模型与请求不符',missing_model:'响应缺少模型身份',missing_finish_reason:'响应缺少完成标记',empty_answer:'未收到可发布的回答',length:'达到输出长度限制',output_limit:'达到输出大小限制',credential_echo:'响应触发安全拦截',transport_setup_failed:'无法建立模型连接',invalid_request:'请求格式无效',unsupported_message:'不支持的消息格式',invalid_stream:'响应流格式无效',invalid_json:'响应数据格式无效',invalid_chunk:'响应片段格式无效',invalid_choices:'响应选项格式无效',invalid_choice:'响应选项格式无效',invalid_delta:'响应增量格式无效',invalid_finish_reason:'响应完成标记无效',invalid_content:'回答格式无效',content_after_finish:'完成后仍有响应内容',event_too_large:'响应片段超过大小限制',unexpected_tool_call:'收到未授权工具调用',callback_error:'处理响应时中断',finish_content_filter:'响应被内容安全规则停止',finish_tool_calls:'响应要求未启用的工具',finish_insufficient_system_resource:'模型服务资源不足'
};
const object=(value:unknown):Record<string,unknown>=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
export function providerDiagnostics(value:unknown):{label:string;value:string}[]{
 const receipt=object(value),provider=object(receipt.provider),usage=object(receipt.usage),facts:{label:string;value:string}[]=[];
 const code=provider.error_code;if(typeof code==='string'&&Object.hasOwn(reasons,code))facts.push({label:'诊断原因',value:reasons[code]+'（'+code+'）'});
 const state=provider.send_state;facts.push({label:'请求发送状态',value:state==='sent'?'已发送':state==='not_sent'?'未发送':'未知'});
 const status=provider.http_status;if(typeof status==='number'&&Number.isInteger(status)&&status>=100&&status<=599)facts.push({label:'HTTP 状态',value:String(status)});
 const counts=object(provider.stream_counts);for(const [key,label] of [['chunks','已接收数据片段'],['reasoning_chunks','思考片段数（不含内容）'],['answer_chunks','回答片段数']] as const){const count=counts[key];if(typeof count==='number'&&Number.isSafeInteger(count)&&count>=0&&count<=10000000)facts.push({label,value:String(count)})}
 const timing=object(provider.stream_timing_ms);for(const [key,label] of [['headers_ms','收到响应头'],['first_byte_ms','收到首批数据'],['first_event_ms','首个数据事件'],['first_reasoning_ms','首个思考片段（不含内容）'],['first_answer_ms','首个回答片段'],['last_event_ms','最后数据事件'],['last_event_age_ms','结束前无新数据事件时长']] as const){const ms=timing[key];if(typeof ms==='number'&&Number.isSafeInteger(ms)&&ms>=0&&ms<=3600000)facts.push({label:label+'（毫秒）',value:String(ms)})}
 const finish=provider.finish_reason;if(typeof finish==='string'&&['stop','length','content_filter','tool_calls','insufficient_system_resource'].includes(finish))facts.push({label:'结束原因',value:finish});
 const latency=usage.latency_ms;if(typeof latency==='number'&&Number.isSafeInteger(latency)&&latency>=0&&latency<=3600000)facts.push({label:'本次耗时（毫秒）',value:String(latency)});
 if(Array.isArray(receipt.errors)&&receipt.errors.includes('TRANSPORT_TERMINATION_UNCONFIRMED'))facts.push({label:'连接状态',value:'尚未确认停止，保留原请求的预算占用'});
 return facts;
}

// Same fixed allowlist as the full receipt; absent metadata stays unknown.
export function providerFailureSummary(value:unknown):string{
 const facts=providerDiagnostics(value),labels=['诊断原因','请求发送状态','本次耗时（毫秒）'];
 const summary=facts.filter(f=>labels.includes(f.label)).map(f=>`${f.label}：${f.value}`).join('；');
 return summary+'。不会自动重复请求；费用未知不代表免费。';
}
