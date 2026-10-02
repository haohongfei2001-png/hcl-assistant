import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import ts from 'typescript';
const source=readFileSync(new URL('../../apps/web/src/provider-diagnostics.ts',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,module={exports:{}};
new Function('module','exports',compiled)(module,module.exports);
const {providerDiagnostics}=module.exports;
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
