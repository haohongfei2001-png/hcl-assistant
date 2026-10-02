/** Controlled component orchestration tests, not a browser or runtime-execution claim. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import ts from 'typescript';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../../apps/web/src/lab.tsx',import.meta.url),'utf8');
const modelSource=readFileSync(new URL('../../apps/web/src/inspection-model.ts',import.meta.url),'utf8');
function compile(source,resolve){
 const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,module={exports:{}};
 new Function('require','module','exports',output)(resolve,module,module.exports);return module.exports;
}
const model=compile(modelSource,require);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function payload(id,overrides={}){return {mode:'MOCK',read_only:true,compare_enabled:false,run:{run_id:id,run_receipt:{run_id:id,outcome:'COMPLETED'},selected_context:{},operation_receipts:[],selected_capability_ids:[],input_text:`original-${id}`,...overrides}}}
function harness(t,options={}){
 const state=[],effects=[],scheduled=[],requests=[],downloads=[];let index=0,props,tree,closed=0,unmounted=false,lateWrites=0;
 const hooks={useState(initial){const slot=index++;if(!(slot in state))state[slot]=initial;return [state[slot],next=>{if(unmounted)lateWrites++;state[slot]=typeof next==='function'?next(state[slot]):next}]},useRef(initial){const slot=index++;if(!(slot in state))state[slot]={current:initial};return state[slot]},useEffect(fn,deps){const slot=index++,old=effects[slot];if(!old||deps.some((value,i)=>value!==old.deps[i]))scheduled.push(()=>{old?.cleanup?.();effects[slot]={deps,cleanup:fn()}})}};
 const View=()=>null,Dialog=()=>null;
 const {Lab}=compile(source,id=>id==='react'?hooks:id==='./panels'?{Dialog}:id==='./InspectionView'?{InspectionView:View}:id==='./inspection-model'?model:id==='./api'?{accountPath:options.accountPath||((path)=>path),requireMemberReady:options.requireMemberReady||(()=>{})}:id==='./cloud-temporary'?{temporaryApi:options.temporaryApi||(async()=>({handled:false}))}:require(id));
 t.mock.method(globalThis,'fetch',(path,options)=>new Promise((resolve,reject)=>requests.push({path,options,resolve:value=>resolve({ok:true,status:200,json:async()=>value}),refuse:status=>resolve({ok:false,status,json:async()=>({error:'not available'})}),reject})));
 t.mock.method(URL,'createObjectURL',blob=>{downloads.push(blob);return 'blob:original-test'});t.mock.method(URL,'revokeObjectURL',()=>{});
 const priorDocument=Object.getOwnPropertyDescriptor(globalThis,'document'),priorWindow=Object.getOwnPropertyDescriptor(globalThis,'window');
 Object.defineProperty(globalThis,'document',{configurable:true,value:{body:{appendChild(){}},createElement(){return {click(){},remove(){}}}}});
 Object.defineProperty(globalThis,'window',{configurable:true,value:{setTimeout:fn=>fn()}});
 t.after(()=>{if(priorDocument)Object.defineProperty(globalThis,'document',priorDocument);else delete globalThis.document;if(priorWindow)Object.defineProperty(globalThis,'window',priorWindow);else delete globalThis.window});
 function render(id=props?.runId){index=0;props={runId:id,onClose:()=>{closed++}};tree=Lab(props);while(scheduled.length)scheduled.shift()();return tree}
 function nodes(node){if(!node||typeof node!=='object')return [];return [node,...[node.props?.children].flat(Infinity).flatMap(nodes)]}
 function button(text){return nodes(tree).find(node=>node.type==='button'&&[node.props.children].flat(Infinity).join('').includes(text))}
 return {requests,downloads,render,button,get view(){return nodes(tree).find(node=>node.type===View)?.props.value},get closed(){return closed},get lateWrites(){return lateWrites},text(){return JSON.stringify(tree.props.children)},close(){tree.props.onClose()},unmount(){unmounted=true;for(const effect of effects)effect?.cleanup?.()}};
}

test('late old-run load cannot replace the newly selected run',async t=>{
 const h=harness(t);h.render('a');await tick();h.render('b');await tick();assert.equal(h.requests[0].options.signal.aborted,true);
 h.requests[1].resolve(payload('b'));await tick();h.render('b');await tick();assert.equal(h.view.runId,'b');
 h.requests[0].resolve(payload('a'));await tick();h.render('b');await tick();assert.equal(h.view.runId,'b');
});
test('unmount and close abort reads and ignore late success or failure',async t=>{
 const h=harness(t);h.render('a');await tick();h.unmount();h.requests[0].resolve(payload('a'));await tick();assert.equal(h.requests[0].options.signal.aborted,true);assert.equal(h.lateWrites,0);
});
test('export refetches current permissions, serializes the exact new envelope, and deduplicates clicks',async t=>{
 const h=harness(t);h.render('a');await tick();h.requests[0].resolve(payload('a'));await tick();h.render('a');await tick();const click=h.button('导出当前权限').props.onClick;click();click();await tick();
 assert.equal(h.requests.length,2);assert.equal(h.requests[1].path,'/v1/lab/export/a');assert.equal(h.requests[1].options.cache,'no-store');h.render('a');await tick();assert.equal(h.view,undefined);
 const latest=payload('a',{redacted:true,input_text:undefined,exact_retained_field:{runtime_sha:'ORIGINAL_PROVENANCE'}});delete latest.run.input_text;h.requests[1].resolve(latest);await tick();h.render('a');await tick();
 assert.equal(h.downloads.length,1);assert.deepEqual(JSON.parse(await h.downloads[0].text()),latest);assert.equal(h.view.redacted,true);
});
test('cancelled export cannot create a file or restore the cached record',async t=>{
 const h=harness(t);h.render('a');await tick();h.requests[0].resolve(payload('a'));await tick();h.render('a');await tick();h.button('导出当前权限').props.onClick();await tick();h.render('a');await tick();h.button('取消导出').props.onClick();h.requests[1].resolve(payload('a'));await tick();h.render('a');await tick();
 assert.equal(h.downloads.length,0);assert.equal(h.view,undefined);assert(h.text().includes('导出已取消'));assert.equal(h.requests[1].options.signal.aborted,true);
});
test('navigation or closing during export cannot download the old run',async t=>{
 const h=harness(t);h.render('a');await tick();h.requests[0].resolve(payload('a'));await tick();h.render('a');await tick();h.button('导出当前权限').props.onClick();await tick();h.render('b');await tick();h.requests[1].resolve(payload('a'));await tick();assert.equal(h.downloads.length,0);
 h.requests[2].resolve(payload('b'));await tick();h.render('b');await tick();h.button('导出当前权限').props.onClick();await tick();h.close();h.requests[3].resolve(payload('b'));await tick();assert.equal(h.closed,1);assert.equal(h.downloads.length,0);
});
test('permission denial or mismatched export removes prior content and never falls back to cache',async t=>{
 const h=harness(t);h.render('a');await tick();h.requests[0].resolve(payload('a'));await tick();h.render('a');await tick();h.button('导出当前权限').props.onClick();await tick();h.requests[1].refuse(403);await tick();h.render('a');await tick();assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('HTTP 403'));
 h.render('b');await tick();h.requests[2].resolve(payload('b'));await tick();h.render('b');await tick();h.button('导出当前权限').props.onClick();await tick();h.requests[3].resolve(payload('a'));await tick();h.render('b');await tick();assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('身份或只读边界'));
});


test('guest inspection and fresh export use only the owned RAM projection',async t=>{
 let reads=0;const h=harness(t,{temporaryApi:async(path,body)=>{assert.equal(body,undefined);reads++;return {handled:true,value:payload('guest',{input_text:reads===1?'ORIGINAL_GUEST_BODY':'FRESH_GUEST_EXPORT'})}}});h.render('guest');await tick();h.render('guest');assert.equal(h.requests.length,0);assert.equal(h.view.runId,'guest');h.button('导出当前权限').props.onClick();await tick();await tick();h.render('guest');assert.equal(reads,2);assert.equal(h.downloads.length,1);assert.equal(JSON.parse(await h.downloads[0].text()).run.input_text,'FRESH_GUEST_EXPORT');assert.equal(h.requests.length,0);
});
test('missing or expired guest projection refuses locally without an owner request',async t=>{
 const h=harness(t,{temporaryApi:async()=>{throw new Error('403: 临时试用不能访问持久会话或其他用户内容')}});h.render('expired');await tick();h.render('expired');assert.equal(h.requests.length,0);assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('临时试用不能访问'));
});
test('member inspection and export use the current member route with no-store and abort signals',async t=>{
 const h=harness(t,{accountPath:path=>'/v1/member/'+path.slice(4)});h.render('member');await tick();assert.equal(h.requests[0].path,'/v1/member/lab/runs/member');assert.equal(h.requests[0].options.cache,'no-store');h.requests[0].resolve(payload('member'));await tick();h.render('member');h.button('导出当前权限').props.onClick();await tick();await tick();assert.equal(h.requests[1].path,'/v1/member/lab/export/member');h.close();assert.equal(h.requests[1].options.signal.aborted,true);h.requests[1].resolve(payload('member'));await tick();assert.equal(h.downloads.length,0);
});


test('suspended member inspection and export stop before RAM or network reads',async t=>{
 let ready=false,localReads=0;const h=harness(t,{requireMemberReady:()=>{if(!ready)throw new Error('503: 正在恢复账号登录，请稍候')},temporaryApi:async()=>{localReads++;return {handled:true,value:payload('member')}}});h.render('member');await tick();h.render('member');assert.equal(localReads,0);assert.equal(h.requests.length,0);assert.equal(h.view,undefined);assert(h.text().includes('正在恢复账号登录'));
 ready=true;h.render('other');await tick();h.render('member');await tick();h.render('member');assert.equal(h.view.runId,'member');const reads=localReads;ready=false;h.button('导出当前权限').props.onClick();await tick();h.render('member');assert.equal(localReads,reads);assert.equal(h.requests.length,0);assert.equal(h.downloads.length,0);assert.equal(h.view,undefined);
});
test('member readiness lost during a local projection prevents its display or export',async t=>{
 let ready=true,release;const h=harness(t,{requireMemberReady:()=>{if(!ready)throw new Error('503: 正在恢复账号登录，请稍候')},temporaryApi:()=>new Promise(resolve=>release=resolve)});h.render('member');ready=false;release({handled:true,value:payload('member')});await tick();h.render('member');assert.equal(h.view,undefined);assert.equal(h.requests.length,0);assert.equal(h.downloads.length,0);assert(h.text().includes('正在恢复账号登录'));
});


test('readiness lost while a member inspection network read is held discards the result',async t=>{
 let ready=true;const h=harness(t,{requireMemberReady:()=>{if(!ready)throw new Error('503: 正在恢复账号登录，请稍候')}});h.render('member');await tick();ready=false;h.requests[0].resolve(payload('member'));await tick();h.render('member');assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('正在恢复账号登录'));
});
test('readiness lost while a member export network read is held cannot download or restore the record',async t=>{
 let ready=true;const h=harness(t,{requireMemberReady:()=>{if(!ready)throw new Error('503: 正在恢复账号登录，请稍候')}});h.render('member');await tick();h.requests[0].resolve(payload('member'));await tick();h.render('member');h.button('导出当前权限').props.onClick();await tick();ready=false;h.requests[1].resolve(payload('member'));await tick();h.render('member');assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('正在恢复账号登录'));
});
