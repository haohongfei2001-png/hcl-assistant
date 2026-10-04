/** Actual App lifecycle with synthetic account permissions and controlled API reads. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import ts from 'typescript';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../../apps/web/src/main.tsx',import.meta.url),'utf8').replace('function App(','export function App(').replace(/createRoot\(document[\s\S]*$/,'');
const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const account=(scope='member-synthetic',generation={model:true,temporary:true,persistent:false})=>({scope,notice:'',renewing:false,logoutPending:false,generation});
const nodes=node=>node&&typeof node==='object'?[node,...[node.props?.children].flat(Infinity).flatMap(nodes)]:[];
function harness(t,initial=account()){
 const state=[],effects=[],scheduled=[],requests=[];let index=0,tree,session=initial;
 const hooks={useState(initial){const slot=index++;if(!(slot in state))state[slot]=typeof initial==='function'?initial():initial;return [state[slot],next=>state[slot]=typeof next==='function'?next(state[slot]):next]},useRef(initial){const slot=index++;if(!(slot in state))state[slot]={current:initial};return state[slot]},useEffect(fn,deps){const slot=index++,old=effects[slot];if(!old||deps.some((v,i)=>v!==old.deps[i]))scheduled.push(()=>{old?.cleanup?.();effects[slot]={deps,cleanup:fn()}})}};
 const api={api:(path,body,signal)=>new Promise((resolve,reject)=>requests.push({path,body,signal,resolve,reject})),stream:async()=>{}};
 const module={exports:{}};new Function('require','module','exports','BroadcastChannel',output)(id=>id==='react'?hooks:id==='./api'?api:id.startsWith('.')?new Proxy({},{get:(_,key)=>key==='labels'?{}:function fixture(){}}):require(id),module,module.exports,undefined);
 function render(next=session){session=next;index=0;tree=module.exports.App({live:true,cloud:true,provider:'qwen',account:session});while(scheduled.length)scheduled.shift()();return tree}
 function unmount(){for(const effect of effects)effect?.cleanup?.()}
 t.after(unmount);
 return {requests,render,unmount,get props(){return tree.props},get memory(){return nodes(tree.props.settings).find(n=>n.type==='select'&&n.props['aria-label']==='记忆范围')},consent(){nodes(tree.props.currentSettings||tree.props.composerConsent).find(n=>n.type==='input').props.onChange({target:{checked:true}})},async history(conversations=[]){requests.filter(r=>!r.body).forEach(r=>r.resolve(r.path==='/v1/conversations'?conversations:[]));await tick();render()}};
}
for(const scope of ['owner','member-synthetic'])test(`${scope} with only temporary rights starts in the permitted scope`,async t=>{
 const h=harness(t,account(scope));h.render();await h.history();h.consent();h.render();
 assert.equal(h.memory.props.value,'TEMPORARY');assert.equal(h.props.sendDisabled,false);assert.match(h.props.scope,/临时/);
 if(scope==='owner')assert.equal(nodes(h.props.currentSettings).find(n=>n.type==='button').props.disabled,false);
});
test('valid explicit project scope survives a permission refresh',async t=>{
 const both=account('member-synthetic',{model:true,temporary:true,persistent:true}),h=harness(t,both);h.render();await h.history();
 h.memory.props.onChange({target:{value:'TOPIC'}});h.render({...both,generation:{...both.generation,temporary:false}});assert.equal(h.memory.props.value,'TOPIC');
});
test('a fresh account allowed persistent storage retains its ordinary conversation default',async t=>{
 const h=harness(t,account('member-synthetic',{model:true,temporary:false,persistent:true}));h.render();await h.history();assert.equal(h.memory.props.value,'CONVERSATION');
});
test('readiness completion cannot upgrade its adopted temporary scope to persistent storage',async t=>{
 const h=harness(t,account('member-synthetic',{model:false,temporary:true,persistent:false,readinessRequired:true,readinessAvailable:true}));h.render();await h.history();assert.equal(h.memory.props.value,'TEMPORARY');
 h.render(account('member-synthetic',{model:true,temporary:false,persistent:true,readinessRequired:false,readinessAvailable:false}));assert.equal(h.memory.props.value,'');assert.match(h.props.error,/设置中选择/);assert.equal(h.requests.filter(r=>r.body).length,0);
});
test('losing temporary permission never silently upgrades a temporary choice to persistent storage',async t=>{
 const h=harness(t);h.render();await h.history();h.render(account('member-synthetic',{model:true,temporary:false,persistent:true}));
 assert.equal(h.memory.props.value,'');assert.equal(h.props.sendDisabled,true);assert.match(h.props.error,/设置中选择/);
 await assert.rejects(Promise.resolve().then(()=>h.props.onNew()),/设置中选择/);assert.equal(h.requests.filter(r=>r.body).length,0);
 h.memory.props.onChange({target:{value:'CONVERSATION'}});h.render();assert.equal(h.memory.props.value,'CONVERSATION');
});
test('revoked persistent rights change only the next new scope, retaining existing history',async t=>{
 const both=account('member-synthetic',{model:true,temporary:true,persistent:true}),h=harness(t,both),c={id:'original-history',title:'Original history',memory:'CONVERSATION',topic_id:null};h.render();await h.history([c]);
 const open=h.props.onOpen(c.id);h.requests.at(-1).resolve({runs:[],state_version:0});await open;h.render(account());
 assert.equal(h.memory.props.value,'TEMPORARY');assert.equal(h.props.currentId,c.id);assert.equal(h.props.scope,'本会话背景');assert.equal(h.props.sendDisabled,true);
 assert.match(h.props.error,/不能使用这种对话范围/);assert.equal(h.requests.filter(r=>r.body).length,0);
});
test('no permitted scope refuses new conversation without a mutation',async t=>{
 const h=harness(t,account('member-synthetic',{model:false,temporary:false,persistent:false}));h.render();await h.history();
 assert.equal(h.memory.props.value,'');const result=Promise.resolve().then(()=>h.props.onNew());await assert.rejects(result,/可用.*范围/);h.render();
 assert.equal(h.requests.filter(r=>r.body).length,0);assert.equal(h.props.sendDisabled,true);assert.match(h.props.error,/可用.*范围/);assert.equal(h.memory.props.value,'');
});
for(const reason of ['会员未开通','会员已到期'])test(`scope refusal preserves the authoritative account reason: ${reason}`,async t=>{
 const h=harness(t,account('member-synthetic',{model:false,temporary:false,persistent:false,reason}));h.render();await h.history();assert(h.props.error.includes(reason));assert.match(h.props.error,/没有可用/);assert.equal(h.props.sendDisabled,true);
 await assert.rejects(Promise.resolve().then(()=>h.props.onNew()),new RegExp(reason));assert.equal(h.requests.filter(r=>r.body).length,0);
});
test('permissions revoked during conversation creation prevent the later event',async t=>{
 const h=harness(t);h.render();await h.history();h.consent();h.render();h.props.setDraft('Original synthetic draft');h.render();
 const sending=h.props.onSend();await tick();const creation=h.requests.find(r=>r.path==='/v1/conversations'&&r.body);assert(creation);
 h.render(account('member-synthetic',{model:false,temporary:false,persistent:false}));creation.resolve({id:'created-before-revocation',memory:'TEMPORARY',title:'Original',topic_id:null});await tick();
 for(const r of h.requests.filter(r=>!r.body))r.resolve([]);await tick();h.requests.at(-1).resolve({runs:[],state_version:0});await sending;h.render();
 assert.equal(h.requests.filter(r=>r.path.endsWith('/events')).length,0);assert.equal(h.props.draft,'Original synthetic draft');
});
test('account replacement cannot inherit an old selection or resume its pending creation',async t=>{
 const first=harness(t,account('member-a',{model:true,temporary:true,persistent:true}));first.render();await first.history();first.memory.props.onChange({target:{value:'TOPIC'}});first.render();
 const creating=first.props.onNew();const old=first.requests.find(r=>r.body);first.unmount();
 const second=harness(t,account('member-b'));second.render();await second.history();assert.equal(second.memory.props.value,'TEMPORARY');
 old.resolve({id:'old-account-created',memory:'TOPIC',title:'Old',topic_id:null});await tick();for(const r of first.requests.filter(r=>!r.body))r.resolve([]);await assert.rejects(creating,/切换/);
 assert.equal(second.props.currentId,null);assert.equal(second.requests.filter(r=>r.body).length,0);
});
