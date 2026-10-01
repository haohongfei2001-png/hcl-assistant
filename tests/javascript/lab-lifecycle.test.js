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
function harness(t){
 const state=[],effects=[],scheduled=[],requests=[],downloads=[];let index=0,props,tree,closed=0,unmounted=false,lateWrites=0;
 const hooks={useState(initial){const slot=index++;if(!(slot in state))state[slot]=initial;return [state[slot],next=>{if(unmounted)lateWrites++;state[slot]=typeof next==='function'?next(state[slot]):next}]},useRef(initial){const slot=index++;if(!(slot in state))state[slot]={current:initial};return state[slot]},useEffect(fn,deps){const slot=index++,old=effects[slot];if(!old||deps.some((value,i)=>value!==old.deps[i]))scheduled.push(()=>{old?.cleanup?.();effects[slot]={deps,cleanup:fn()}})}};
 const View=()=>null,Dialog=()=>null;
 const {Lab}=compile(source,id=>id==='react'?hooks:id==='./panels'?{Dialog}:id==='./InspectionView'?{InspectionView:View}:id==='./inspection-model'?model:require(id));
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
 const h=harness(t);h.render('a');h.render('b');assert.equal(h.requests[0].options.signal.aborted,true);
 h.requests[1].resolve(payload('b'));await tick();h.render('b');assert.equal(h.view.runId,'b');
 h.requests[0].resolve(payload('a'));await tick();h.render('b');assert.equal(h.view.runId,'b');
});
test('unmount and close abort reads and ignore late success or failure',async t=>{
 const h=harness(t);h.render('a');h.unmount();h.requests[0].resolve(payload('a'));await tick();assert.equal(h.requests[0].options.signal.aborted,true);assert.equal(h.lateWrites,0);
});
test('export refetches current permissions, serializes the exact new envelope, and deduplicates clicks',async t=>{
 const h=harness(t);h.render('a');h.requests[0].resolve(payload('a'));await tick();h.render('a');const click=h.button('导出当前权限').props.onClick;click();click();
 assert.equal(h.requests.length,2);assert.equal(h.requests[1].path,'/v1/lab/export/a');assert.equal(h.requests[1].options.cache,'no-store');h.render('a');assert.equal(h.view,undefined);
 const latest=payload('a',{redacted:true,input_text:undefined,exact_retained_field:{runtime_sha:'ORIGINAL_PROVENANCE'}});delete latest.run.input_text;h.requests[1].resolve(latest);await tick();h.render('a');
 assert.equal(h.downloads.length,1);assert.deepEqual(JSON.parse(await h.downloads[0].text()),latest);assert.equal(h.view.redacted,true);
});
test('cancelled export cannot create a file or restore the cached record',async t=>{
 const h=harness(t);h.render('a');h.requests[0].resolve(payload('a'));await tick();h.render('a');h.button('导出当前权限').props.onClick();h.render('a');h.button('取消导出').props.onClick();h.requests[1].resolve(payload('a'));await tick();h.render('a');
 assert.equal(h.downloads.length,0);assert.equal(h.view,undefined);assert(h.text().includes('导出已取消'));assert.equal(h.requests[1].options.signal.aborted,true);
});
test('navigation or closing during export cannot download the old run',async t=>{
 const h=harness(t);h.render('a');h.requests[0].resolve(payload('a'));await tick();h.render('a');h.button('导出当前权限').props.onClick();h.render('b');h.requests[1].resolve(payload('a'));await tick();assert.equal(h.downloads.length,0);
 h.requests[2].resolve(payload('b'));await tick();h.render('b');h.button('导出当前权限').props.onClick();h.close();h.requests[3].resolve(payload('b'));await tick();assert.equal(h.closed,1);assert.equal(h.downloads.length,0);
});
test('permission denial or mismatched export removes prior content and never falls back to cache',async t=>{
 const h=harness(t);h.render('a');h.requests[0].resolve(payload('a'));await tick();h.render('a');h.button('导出当前权限').props.onClick();h.requests[1].refuse(403);await tick();h.render('a');assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('HTTP 403'));
 h.render('b');h.requests[2].resolve(payload('b'));await tick();h.render('b');h.button('导出当前权限').props.onClick();h.requests[3].resolve(payload('a'));await tick();h.render('b');assert.equal(h.view,undefined);assert.equal(h.downloads.length,0);assert(h.text().includes('身份或只读边界'));
});
