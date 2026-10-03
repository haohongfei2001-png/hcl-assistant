/** Synthetic recovery lifecycle probes. No Auth, email or password is changed. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import ts from 'typescript';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../../apps/web/src/RecoveryEntry.tsx',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const ready=()=>({available:true,ready:true,expires_at:Math.floor(Date.now()/1000)+60});

function harness(t,{callback=false}={}){
 const state=[],effects=[],scheduled=[],requests=[],timers=new Map();let index=0,tree,serial=0;
 const hooks={useState(initial){const slot=index++;if(!(slot in state))state[slot]=initial;return[state[slot],next=>state[slot]=typeof next==='function'?next(state[slot]):next]},useRef(initial){const slot=index++;if(!(slot in state))state[slot]={current:initial};return state[slot]},useEffect(fn,deps){const slot=index++,old=effects[slot];if(!old||deps.some((value,i)=>value!==old.deps[i]))scheduled.push(()=>{old?.cleanup?.();effects[slot]={deps,cleanup:fn()}})}};
 const api={api:(path,body,signal)=>new Promise((resolve,reject)=>{
  requests.push({path,body,signal,resolve,reject});
  if(signal?.aborted)reject(new Error('AbortError'));
  else signal?.addEventListener('abort',()=>reject(new Error('AbortError')),{once:true});
 })};
 const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,module={exports:{}};
 const window=callback?{__hclaRecovery:{code:'10000000-0000-4000-8000-000000000001',invalid:false}}:{};
 new Function('require','module','exports','window','setTimeout','clearTimeout',output)(id=>id==='react'?hooks:id==='./api'?api:id.endsWith('.css')?{}:require(id),module,module.exports,window,(fn,ms)=>{timers.set(++serial,{fn,ms});return serial},id=>timers.delete(id));
 function render(){index=0;tree=module.exports.RecoveryEntry({onBack(){},callback});while(scheduled.length)scheduled.shift()();return tree}
 function nodes(node){if(!node||typeof node!=='object')return[];return[node,...[node.props?.children].flat(Infinity).flatMap(nodes)]}
 function text(node){if(Array.isArray(node))return node.map(text).join('');if(typeof node==='string')return node;if(!node||typeof node!=='object')return'';return text(node.props?.children)}
 function unmount(){for(const effect of effects)effect?.cleanup?.()}
 t.after(unmount);
 return {requests,render,unmount,get text(){return text(tree)},get passwordInputs(){return nodes(tree).filter(n=>n.type==='input'&&n.props.type==='password')},get forms(){return nodes(tree).filter(n=>n.type==='form')},get buttons(){return nodes(tree).filter(n=>n.type==='button')},button(label){return this.buttons.find(n=>text(n)===label)},submit(){this.forms[0].props.onSubmit({preventDefault(){}})},password(){for(const input of this.passwordInputs)input.props.onChange({target:{value:'SYNTHETIC_PASSWORD_FIXTURE'}});render()},expire(){[...timers.values()].find(t=>t.ms>15000).fn()},timeout(){[...timers.values()].find(t=>t.ms===15000).fn()}};
}
async function enter(h,value=ready()){h.render();h.requests[0].resolve(value);await tick();h.render()}

test('expiry cannot abort a submitted password update or replace a confirmed success with restart',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.render();h.expire();await tick();h.render();
 assert.equal(h.requests[1].signal.aborted,false);assert.equal(h.passwordInputs.length,0);assert.equal(h.button('重新申请链接'),undefined);assert.match(h.text,/请勿重复修改/);
 h.requests[1].resolve({updated:true,message:'密码已更新'});await tick();h.render();assert.match(h.text,/密码已更新/);assert.doesNotMatch(h.text,/恢复验证已过期/);assert.equal(h.requests.length,2);
});
test('mutation timeout uses a fresh bounded status read and never repeats the password update',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.render();h.timeout();await tick();h.render();
 assert.equal(h.requests.length,3);assert.equal(h.requests[2].path,'/v1/account/recovery/status');assert.equal(h.requests[2].signal.aborted,false);
 h.requests[2].resolve({available:true,ready:false,updated:true});await tick();h.render();assert.match(h.text,/密码已更新/);assert.equal(h.passwordInputs.length,0);assert.equal(h.requests.filter(r=>r.path.endsWith('/complete')).length,1);
});
test('unknown mutation plus unavailable status keeps mutation and restart closed until explicit verification',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.requests[1].reject(new Error('Error: 503: unknown'));await tick();h.render();
 h.requests[2].reject(new Error('Error: 503: unavailable'));await tick();h.render();assert.equal(h.passwordInputs.length,0);assert.equal(h.button('重新申请链接'),undefined);assert.match(h.text,/未确认/);
 h.button('检查恢复状态').props.onClick();h.requests[3].resolve({available:true,ready:false,locked:true});await tick();h.render();assert.match(h.text,/恢复暂时锁定/);assert.equal(h.forms.length,0);assert.equal(h.requests.filter(r=>r.path.endsWith('/complete')).length,1);
});
test('a ready or missing status cannot prove a timed-out remote mutation has stopped',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.requests[1].reject(new Error('Error: 503: unknown'));await tick();
 h.requests[2].resolve(ready());await tick();h.render();assert.equal(h.passwordInputs.length,0);assert.equal(h.button('重新申请链接'),undefined);
 h.button('检查恢复状态').props.onClick();h.requests[3].resolve({available:true,ready:false,requested:false});await tick();h.render();assert.equal(h.forms.length,0);assert.equal(h.button('重新申请链接'),undefined);assert.match(h.text,/未确认/);
});
test('known password rejection permits only a new explicit attempt after authoritative state is read',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.requests[1].reject(new Error('400: policy rejection'));await tick();
 h.requests[2].resolve(ready());await tick();h.render();assert.match(h.text,/密码未更新/);assert.equal(h.passwordInputs.length,2);assert(h.passwordInputs.every(n=>n.props.value===''));
 h.password();h.submit();assert.equal(h.requests.filter(r=>r.path.endsWith('/complete')).length,2);
 h.requests[3].resolve({updated:true,message:'密码已更新'});await tick();h.render();assert.match(h.text,/密码已更新/);
});
test('same-turn duplicate submits never abort or repeat the admitted mutation',async t=>{
 const h=harness(t);await enter(h);h.password();const submit=h.forms[0].props.onSubmit;submit({preventDefault(){}});submit({preventDefault(){}});
 assert.equal(h.requests.length,2);assert.equal(h.requests[1].signal.aborted,false);
 h.requests[1].resolve({updated:true,message:'密码已更新'});await tick();h.render();assert.match(h.text,/密码已更新/);
});
test('expiry before submission closes the unused grant and offers a restart without mutation',async t=>{
 const h=harness(t);await enter(h);h.password();h.expire();await tick();h.render();assert.equal(h.forms.length,0);assert(h.button('重新申请链接'));assert.equal(h.requests.length,1);
});
test('unmount aborts reconciliation and late replies cannot start another read or restore the form',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.requests[1].reject(new Error('Error: 503: unknown'));await tick();
 h.unmount();assert.equal(h.requests[2].signal.aborted,true);h.requests[2].resolve(ready());await tick();h.render();assert.equal(h.passwordInputs.length,0);assert.equal(h.requests.length,3);
});
test('earlier uncertain exchange cannot manufacture a terminal restart after an unknown update',async t=>{
 const h=harness(t,{callback:true});h.render();h.requests[0].resolve({available:true,ready:false});await tick();
 h.requests[1].reject(new Error('503: unknown exchange'));await tick();h.requests[2].resolve(ready());await tick();h.render();h.password();h.submit();
 h.requests[3].reject(new Error('503: unknown update'));await tick();h.requests[4].resolve({available:true,ready:false,requested:false});await tick();h.render();
 assert.equal(h.forms.length,0);assert.equal(h.button('重新申请链接'),undefined);assert.match(h.text,/未确认/);assert.equal(h.requests.filter(r=>r.path.endsWith('/exchange')).length,1);
});
test('unmount during callback status never exchanges a late code in another recovery context',async t=>{
 const h=harness(t,{callback:true});h.render();h.unmount();h.requests[0].resolve({available:true,ready:false});await tick();assert.equal(h.requests.length,1);
});
test('a known terminal restart releases uncertainty but does not send another email automatically',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.requests[1].reject(new Error('503: unknown update'));await tick();
 h.requests[2].resolve({available:true,ready:false,restart_required:true});await tick();h.render();assert(h.button('重新申请链接'));assert.equal(h.passwordInputs.length,0);
 h.button('重新申请链接').props.onClick();h.render();assert.equal(h.forms.length,1);assert.equal(h.requests.length,3);
});
test('a timeout of the one reconciliation read leaves an explicit check and no new automatic request',async t=>{
 const h=harness(t);await enter(h);h.password();h.submit();h.timeout();await tick();h.render();h.timeout();await tick();h.render();
 assert.equal(h.requests.length,3);assert.equal(h.requests[2].signal.aborted,true);assert.equal(h.forms.length,0);assert(h.button('检查恢复状态'));assert.equal(h.button('检查恢复状态').props.disabled,false);
});
