/** Original display-only fixtures; not runtime execution or browser evidence. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

// Compile the small pure view files for Node without changing the repository or starting a browser.
const require=createRequire(import.meta.url);
const compiled=new Map();
function load(name){
 if(compiled.has(name))return compiled.get(name);
 const source=readFileSync(new URL(`../../apps/web/src/${name}`,import.meta.url),'utf8');
 const result=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}});
 const module={exports:{}};
 new Function('require','module','exports',result.outputText)(id=>id==='./inspection-model'?load('inspection-model.ts'):require(id),module,module.exports);
 compiled.set(name,module.exports);return module.exports;
}
const {projectLocalInspection,inspectionFlag,flagText,operationSummary}=load('inspection-model.ts');
const {InspectionView}=load('InspectionView.tsx');

function envelope(overrides={}){
 return {mode:'MOCK',read_only:true,compare_enabled:false,compare_gate:['I06_DISPOSITION','PINNED_PERMITTED_RUNTIME_ARTIFACT','PRODUCT_ADAPTER_SCOPE_VALIDATION','EXPLICIT_EXECUTION_AND_DATA_AUTHORIZATION'],usage_scope:'THIS_ATTEMPT; provider-free original fixture',efficacy:'NOT_TESTED',run:{run_id:'original-inspection-a',input_text:'原创合成记录：展览周五开幕。',pending:false,outdated:false,state_version_before:2,state_version_after:3,route:'DIRECT',selected_capability_ids:[],operation_receipts:[],selected_context:{coverage:'PARTIAL',records:[]},run_receipt:{run_id:'original-inspection-a',outcome:'COMPLETED',usage:{provider_calls:0,input_tokens:null,output_tokens:null,cost:{amount:0,currency:'USD',source:'PROVIDER_FREE_MOCK'}}},...overrides}};
}
function project(data){return projectLocalInspection(data,'original-inspection-a')}
function operation(fields){return {id:'display-only-operation',label:'display-only-original-fixture',status:null,selected:null,executed:null,resultProduced:null,usedInAnswer:null,cacheReused:null,details:[],...fields}}
const fixtures=[
 {id:'not-selected',selected:false,executed:false,resultProduced:false,usedInAnswer:false,status:'NOT_SELECTED',summary:'未选择、未执行专门处理'},
 {id:'selected-not-executed',selected:true,executed:false,resultProduced:false,usedInAnswer:false,status:'NOT_EXECUTED',summary:'已选择，尚未执行'},
 {id:'executed-no-output',selected:true,executed:true,resultProduced:false,usedInAnswer:false,status:'NO_OUTPUT',summary:'已执行，未产生结果'},
 {id:'output-not-used',selected:true,executed:true,resultProduced:true,usedInAnswer:false,status:'COMPLETED',summary:'已产生结果，未用于本次回答'},
 {id:'output-used',selected:true,executed:true,resultProduced:true,usedInAnswer:true,status:'COMPLETED',summary:'结果已记录为用于本次回答；不证明因果增益'},
 {id:'execution-failed',selected:true,executed:true,resultProduced:false,usedInAnswer:false,status:'FAILED',summary:'执行失败'},
 {id:'execution-unknown',selected:true,executed:null,resultProduced:null,usedInAnswer:null,status:'UNKNOWN',summary:'结果未知'},
 {id:'unsupported-input',selected:false,executed:false,resultProduced:false,usedInAnswer:false,status:'UNSUPPORTED',summary:'不支持此输入或范围'},
 {id:'no-treatment',selected:true,executed:true,resultProduced:false,usedInAnswer:false,status:'NO_TREATMENT',summary:'未产生专门处理结果'},
];
for(const fixture of fixtures)test(`original display-only ${fixture.id} remains distinct`,()=>{
 const row=operation(fixture);assert.equal(operationSummary(row),fixture.summary);
 const html=renderToStaticMarkup(React.createElement(InspectionView,{value:{...project(envelope()),operations:[row]}}));
 assert(html.includes(fixture.summary));for(const label of ['已选择','已执行','已产生结果','已用于本次回答','缓存复用'])assert(html.includes(label));
});
test('missing, null, invalid and explicitly false flags stay different',()=>{
 for(const value of [undefined,null,0,1,'true','false',{},[]])assert.equal(inspectionFlag(value),null);
 assert.equal(inspectionFlag(false),false);assert.equal(inspectionFlag(true),true);
 assert.equal(flagText(null),'未知（未记录）');assert.equal(flagText(false),'否');
 const view=project(envelope({selected_capability_ids:['selected-only'],operation_receipts:undefined}));
 assert.equal(view.operationRecords,'unrecorded');assert.equal(view.operations[0].selected,true);
 for(const key of ['executed','resultProduced','usedInAnswer','cacheReused'])assert.equal(view.operations[0][key],null);
});
test('local operation flags remain actual independent values, never inferred from status',()=>{
 const view=project(envelope({selected_capability_ids:['original-capability'],operation_receipts:[{operation_id:'op',capability_id:'original-capability',status:'COMPLETED',selected:true,executed:null,result_produced:true,used_in_answer:false,cache_reused:false}]}));
 const row=view.operations[0];assert.equal(view.operations.length,1);assert.equal(row.executed,null);assert.equal(row.resultProduced,true);assert.equal(row.usedInAnswer,false);
 assert.match(operationSummary(row),/未知/);
});
test('missing selection and operation arrays never become successful empty processing',()=>{
 const view=project(envelope({selected_capability_ids:undefined,operation_receipts:undefined}));
 assert.equal(view.selectedCapabilities,null);assert.equal(view.operationRecords,'unrecorded');
 const html=renderToStaticMarkup(React.createElement(InspectionView,{value:view}));assert(html.includes('执行、输出与使用情况未知'));assert(!html.includes('本次未选择专门操作'));
});
test('rejects mismatched run or receipt, mutable envelope and unrelated Pages shape',()=>{
 for(const value of [envelope({run_id:'newer-run'}),envelope({run_receipt:{run_id:'newer-run'}}),{...envelope(),read_only:false},{...envelope(),compare_enabled:true},{id:'original-inspection-a',route:'DIRECT',caps:[]}])assert.throws(()=>project(value),/身份或只读边界/);
});
test('projection keeps requested old run and explicit current-policy redactions',()=>{
 const first=envelope({answer:{text:'OLD_ANSWER'},selected_context:{coverage:'PARTIAL',records:[{record_id:'r',kind:'USER_GUESS',content:'OLD_BASIS'}]}});
 const before=JSON.stringify(first),old=project(first);const other=envelope({run_id:'new-run',run_receipt:{run_id:'new-run',outcome:'FAILED'}});projectLocalInspection(other,'new-run');
 assert.equal(old.runId,'original-inspection-a');assert.equal(old.answer,'OLD_ANSWER');assert.equal(JSON.stringify(first),before);
 const redacted=project(envelope({redacted:true,input_text:'MUST_NOT_DISPLAY',answer:{text:'MUST_NOT_DISPLAY'},selected_context:{records:[{content:'MUST_NOT_DISPLAY'}]},runtime_outputs:[{quote:'MUST_NOT_DISPLAY'}],operation_receipts:[{capability_id:'MUST_NOT_DISPLAY'}],unresolved_updates:[{reason:'MUST_NOT_DISPLAY'}]}));
 const html=renderToStaticMarkup(React.createElement(InspectionView,{value:redacted}));assert(!html.includes('MUST_NOT_DISPLAY'));assert.equal(redacted.operationRecords,'unavailable');assert(html.includes('不能推定未执行'));
});
test('preserves exact runtime identity, interface and zero-provider cost source without assigning unknown zeros',()=>{
 const sha='0123456789abcdef0123456789abcdef01234567',data=envelope();data.mode='EXPERIMENTAL';data.run.run_receipt.bridge_provenance={source_commit_sha:sha,interface_version:'original-test-interface-v1',artifact_digest:'sha256:original',production_enabled:false,evidence_class:'DEVELOPMENT_INTEGRATION_ONLY'};
 const view=project(data),html=renderToStaticMarkup(React.createElement(InspectionView,{value:view}));
 assert.equal(view.provenance.find(row=>row.label==='精确运行时 SHA').value,sha);assert(html.includes(sha));assert(html.includes('original-test-interface-v1'));
 assert.equal(view.usage.find(row=>row.label==='Provider calls').value,'0');assert.equal(view.usage.find(row=>row.label==='费用来源').value,'PROVIDER_FREE_MOCK');assert.equal(view.usage.find(row=>row.label==='输入 tokens').value,null);
 assert.equal(view.usage.find(row=>row.label==='Adapter invocations').value,null);assert(html.includes('不证明真实模型性能或效果'));
 const unknown=project(envelope({run_receipt:{}}));assert(unknown.usage.every(row=>row.value===null));
});
test('normal renderer has details-only technical facts, no fake Compare controls, and excludes unknown hidden fields',()=>{
 const data=envelope();data.run.hidden_reasoning='NEVER_RENDER_REASONING';data.run.run_receipt.hidden_reasoning='NEVER_RENDER_REASONING';
 const html=renderToStaticMarkup(React.createElement(InspectionView,{value:project(data)}));
 assert(!html.includes('NEVER_RENDER_REASONING'));assert(!html.includes('<button'));assert(!html.includes('<pre'));assert(!html.includes('<details open'));
 for(const label of ['运行身份、路由与版本','运行时来源与接口','Usage 与费用记录','Research Compare 的能力门槛'])assert(html.includes(`<summary>${label}</summary>`));
 assert(html.includes('未开放 Compare 执行'));assert(html.includes('都不能证明理解正确或 HCL 的独立增益'));
});
test('development chat keeps real model fields separate from HCL treatment and unknown invoice',()=>{
 const data=envelope();data.mode='DEVELOPMENT_CHAT';data.usage_scope='THIS_ATTEMPT; real development provider receipt';data.run.live_chat=true;data.run.run_receipt.mode='REAL_DEVELOPMENT';data.run.run_receipt.actual_treatment='NO_TREATMENT';data.run.run_receipt.provider={requested_model:'original-model',actual_model:'original-model',thinking:'enabled',reasoning_effort:'high',finish_reason:'stop'};data.run.run_receipt.usage.cost={amount:null,currency:'USD',source:'UNKNOWN'};
 const view=project(data);assert.equal(view.mode,'DEVELOPMENT_CHAT');assert.equal(view.operations.length,0);assert.equal(view.treatment,'NO_TREATMENT');assert(view.technicalFacts.some(f=>f.label==='实际模型'&&f.value==='original-model'));assert(view.usage.some(f=>f.label==='费用金额'&&f.value===null));const html=renderToStaticMarkup(React.createElement(InspectionView,{value:view}));assert(html.includes('只读开发聊天记录'));assert(!html.includes('provider-free preparation'));
});
test('static Pages projection never upgrades template capability labels into execution receipts',async()=>{
 const preview=await import('../../pages-preview/preview-model.js');const source=readFileSync(new URL('../../pages-preview/inspection.ts',import.meta.url),'utf8');const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;const module={exports:{}};new Function('require','module','exports',compiled)(id=>id==='./preview-model.js'?preview:require(id),module,module.exports);
 const state=preview.emptyState(),conversation=preview.createConversation(state,'CONVERSATION');preview.submit(state,conversation.id,'记录：原创静态纸灯');const run=conversation.runs.at(-1);run.caps=['imaginary-template-label'];const view=module.exports.previewInspection(conversation,run);assert.equal(view.mode,'STATIC_PREVIEW');assert.deepEqual(view.operations,[]);assert.equal(view.operationRecords,'unrecorded');assert.equal(view.selectedCapabilities,null);assert(view.usage.some(f=>f.label==='Provider calls'&&f.value==='0'));
});
