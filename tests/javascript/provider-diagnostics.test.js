import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../../apps/web/src/provider-diagnostics.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,module={exports:{}};
new Function('module','exports',compiled)(module,module.exports);
const {providerDiagnostics,providerFailureSummary}=module.exports;
test('known protocol metadata distinguishes sent timeout from proven no-send and output limit',()=>{
 assert.deepEqual(providerDiagnostics({provider:{error_code:'wall_timeout',http_status:200,send_state:'sent'},usage:{latency_ms:60001}}),[{label:'诊断原因',value:'请求等待超过时限（wall_timeout）'},{label:'请求发送状态',value:'已发送'},{label:'HTTP 状态',value:'200'},{label:'本次耗时（毫秒）',value:'60001'}]);
 assert.equal(providerDiagnostics({provider:{send_state:'not_sent'}})[0].value,'未发送');assert.equal(providerDiagnostics({provider:{send_state:'unknown'}})[0].value,'未知');assert.match(providerDiagnostics({provider:{error_code:'length',finish_reason:'length'}})[0].value,/输出长度/);
});
test('arbitrary upstream strings and invalid numeric metadata never enter the receipt',()=>{
 const canary='PRIVATE_UPSTREAM_BODY_OR_CREDENTIAL';const values=providerDiagnostics({provider:{error_code:canary,send_state:canary,http_status:canary,finish_reason:canary,request_id:canary,body:canary},usage:{latency_ms:Infinity},errors:[canary]});assert.deepEqual(values,[{label:'请求发送状态',value:'未知'}]);assert(!JSON.stringify(values).includes(canary));assert.deepEqual(providerDiagnostics(null),[{label:'请求发送状态',value:'未知'}]);
});
test('unconfirmed transport keeps its reservation truthful without inventing a charge or retry',()=>{
 const facts=providerDiagnostics({errors:['TRANSPORT_TERMINATION_UNCONFIRMED'],provider:{send_state:'unknown'},usage:{latency_ms:-1}});assert.equal(facts.length,2);assert.match(facts[1].value,/保留原请求的预算占用/);assert(!JSON.stringify(facts).includes('免费'));
});

test('stream diagnostics show only bounded numeric counts, never reasoning content',()=>{
 const facts=providerDiagnostics({provider:{stream_counts:{chunks:3,reasoning_chunks:2,answer_chunks:0,body:'PRIVATE_HIDDEN_TEXT'}}});assert(facts.some(x=>x.label==='思考片段数（不含内容）'&&x.value==='2'));assert(!JSON.stringify(facts).includes('PRIVATE_HIDDEN_TEXT'));assert.equal(providerDiagnostics({provider:{stream_counts:{chunks:-1,reasoning_chunks:'HIDDEN',answer_chunks:Infinity}}}).length,1);
});

test('timing allowlist preserves observed zero and omits absent or malformed metrics',()=>{
 const facts=providerDiagnostics({provider:{stream_timing_ms:{headers_ms:0,first_byte_ms:1250,first_event_ms:null,first_reasoning_ms:-1,first_answer_ms:'secret',last_event_ms:Infinity,last_event_age_ms:42,arbitrary:'PRIVATE'}}});
 assert.deepEqual(facts.slice(1),[{label:'收到响应头（毫秒）',value:'0'},{label:'收到首批数据（毫秒）',value:'1250'},{label:'结束前无新数据事件时长（毫秒）',value:'42'}]);
});
test('failed card gives safe known reason and duration without inferring unknown cause',()=>{
 assert.match(providerFailureSummary({provider:{error_code:'wall_timeout',send_state:'sent'},usage:{latency_ms:180000}}),/wall_timeout.*已发送.*180000/);
 const unknown=providerFailureSummary({provider:{error_code:'PRIVATE',send_state:'unknown'}});
 assert(!unknown.includes('PRIVATE'));assert(!unknown.includes('超时'));assert.match(unknown,/未知/);assert.match(unknown,/不会自动重复/);
});
