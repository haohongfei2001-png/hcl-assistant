/** Controlled UI lifecycle regression probes; no browser, account or network calls. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import ts from 'typescript';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../../apps/web/src/MemberEntry.tsx',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const authenticated={available:true,authenticated:true,account_scope:'synthetic-member-a',expires_at:Math.floor(Date.now()/1000)+900,model_enabled:true,entitlements:{enabled:true,temporary:true,persistent:true}};
function harness(t){
 const state=[],effects=[],scheduled=[],requests=[],channels=[],intervals=new Map();let index=0,tree,serial=0;
 const hooks={useState(initial){const slot=index++;if(!(slot in state))state[slot]=initial;return [state[slot],next=>state[slot]=typeof next==='function'?next(state[slot]):next]},useRef(initial){const slot=index++;if(!(slot in state))state[slot]={current:initial};return state[slot]},useEffect(fn,deps){const slot=index++,old=effects[slot];if(!old||deps.some((value,i)=>value!==old.deps[i]))scheduled.push(()=>{old?.cleanup?.();effects[slot]={deps,cleanup:fn()}})}};
 t.mock.method(globalThis,'setInterval',fn=>{const id=++serial;intervals.set(id,fn);return id});t.mock.method(globalThis,'clearInterval',id=>intervals.delete(id));t.mock.method(globalThis,'setTimeout',()=>++serial);t.mock.method(globalThis,'clearTimeout',()=>{});
 const broadcast=Object.getOwnPropertyDescriptor(globalThis,'BroadcastChannel');Object.defineProperty(globalThis,'BroadcastChannel',{configurable:true,writable:true,value:class{constructor(){channels.push(this)}postMessage(){}close(){}}});t.after(()=>Object.defineProperty(globalThis,'BroadcastChannel',broadcast));
 const api={api:(path,body,signal)=>new Promise((resolve,reject)=>requests.push({path,body,signal,resolve,reject})),configureCloud(){},setMemberReady(){}};
 const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,module={exports:{}};
 new Function('require','module','exports',output)(id=>id==='react'?hooks:id==='./api'?api:id==='./cloud-temporary'?{clearTemporary(){}}:id==='./RecoveryEntry'?{RecoveryEntry(){}}:id.endsWith('.css')?{}:require(id),module,module.exports);
 function render(){index=0;tree=module.exports.MemberEntry({onOwner(){},children:(logout,scope,notice,renewing,logoutPending,generation)=>({type:'signed-in',props:{logout,scope,notice,renewing,logoutPending,generation}})});while(scheduled.length)scheduled.shift()();return tree}
 function nodes(node){if(!node||typeof node!=='object')return [];return [node,...[node.props?.children].flat(Infinity).flatMap(nodes)]}
 t.after(()=>{for(const effect of effects)effect?.cleanup?.()});
 return {requests,render,poll(){for(const fn of [...intervals.values()])fn()},broadcast(){channels[0].onmessage({data:{type:'signed-in'}})},get signedIn(){return tree.type==='signed-in'},get notice(){return tree.props.notice},get generation(){return tree.props.generation},get alerts(){return nodes(tree).filter(n=>n.props?.role==='alert').map(n=>n.props.children)},logout(){tree.props.logout()},form(){return nodes(tree).find(n=>n.type==='form')},inputs(){return nodes(tree).filter(n=>n.type==='input')},buttons(){return nodes(tree).filter(n=>n.type==='button')}};
}
async function enter(h){h.render();h.requests[0].resolve(authenticated);await tick();h.render();assert.equal(h.signedIn,true)}
test('successful logout aborts and fences a status read begun while logout was pending',async t=>{
 const h=harness(t);await enter(h);h.logout();h.render();h.poll();assert.equal(h.requests[2].path,'/v1/account/status');
 h.requests[1].resolve({});await tick();h.render();assert.equal(h.signedIn,false);assert.equal(h.requests[2].signal.aborted,true);
 h.requests[2].resolve(authenticated);await tick();h.render();assert.equal(h.signedIn,false);
});
test('failed logout stays visible through a healthy status read until explicit retry',async t=>{
 const h=harness(t);await enter(h);h.logout();h.requests[1].reject(new Error('503: synthetic logout failure'));await tick();h.render();assert.match(h.notice,/退出未完成/);
 h.poll();h.requests[2].resolve(authenticated);await tick();h.render();assert.match(h.notice,/退出未完成/);
 h.logout();h.requests[3].resolve({});await tick();h.render();assert.equal(h.signedIn,false);
});
test('a superseded logout completion cannot unlock a newer account submission',async t=>{
 const h=harness(t);await enter(h);h.logout();h.broadcast();h.requests[2].resolve({available:true,authenticated:false});await tick();h.render();
 h.inputs().find(n=>n.props.type==='email').props.onChange({target:{value:'synthetic@example.test'}});h.inputs().find(n=>n.props.id==='member-password').props.onChange({target:{value:'synthetic offline password'}});h.render();
 h.form().props.onSubmit({preventDefault(){}});h.render();assert.equal(h.requests[3].path,'/v1/account/login');assert(h.inputs().every(n=>n.props.disabled));
 h.requests[1].resolve({});await tick();h.render();assert(h.inputs().every(n=>n.props.disabled));
 h.requests[3].reject(new Error('401: synthetic rejection'));await tick();h.render();
});

test('connection uncertainty takes priority without erasing an unresolved logout failure',async t=>{
 const h=harness(t);await enter(h);h.logout();h.requests[1].reject(new Error('503: synthetic logout failure'));await tick();h.render();
 h.poll();h.requests[2].reject(new Error('503: synthetic connection outage'));await tick();h.render();assert.match(h.notice,/只读/);
 h.poll();h.requests[3].resolve(authenticated);await tick();h.render();assert.match(h.notice,/退出未完成/);
});

test('confirmed logout clears a prior connection warning from the signed-out entry',async t=>{
 const h=harness(t);await enter(h);h.poll();h.requests[1].reject(new Error('503: synthetic connection outage'));await tick();h.render();assert.match(h.notice,/只读/);
 h.logout();h.requests[2].resolve({});await tick();h.render();assert.equal(h.signedIn,false);assert.deepEqual(h.alerts,[]);
});

// These are display/admission affordances only; server guards remain authoritative.
test('paid membership expiry disables every send path without signing out or changing scope',async t=>{
 const h=harness(t);h.render();const expiry=Math.floor(Date.now()/1000)-1;
 h.requests[0].resolve({...authenticated,entitlements:{...authenticated.entitlements,membership_required:true,expires_at:expiry}});await tick();h.render();
 assert.equal(h.signedIn,true);assert.equal(h.generation.model,false);assert.equal(h.generation.temporary,false);assert.equal(h.generation.persistent,false);
 assert.match(h.generation.reason,/已到期/);assert.deepEqual(h.generation.membership,{enabled:false,expires_at:expiry});
});
test('active paid membership exposes its own expiry while unavailable model remains blocked',async t=>{
 const h=harness(t);h.render();const expiry=Math.floor(Date.now()/1000)+3600;
 h.requests[0].resolve({...authenticated,model_enabled:false,entitlements:{...authenticated.entitlements,membership_required:true,expires_at:expiry}});await tick();h.render();
 assert.equal(h.generation.model,false);assert.deepEqual(h.generation.membership,{enabled:true,expires_at:expiry});assert.match(h.notice,/模型服务尚未启用/);
});
