import React,{useEffect,useRef,useState} from 'react';
import {api,configureCloud,setMemberReady} from './api';
import {clearTemporary} from './cloud-temporary';
import './account-entry.css';
import {RecoveryEntry} from './RecoveryEntry';

type Status={recovery_available?:boolean;available:boolean;authenticated:boolean;renewable?:boolean;expires_at?:number;account_scope?:string;model_enabled?:boolean;entitlements?:{enabled:boolean;temporary?:boolean;persistent?:boolean;reason?:string|null}};
export function MemberEntry({children,onOwner,extra}:{children:(logout:()=>void,scope:string,notice:string,renewing:boolean,logoutPending:boolean,generation:{model:boolean;temporary:boolean;persistent:boolean})=>React.ReactNode;onOwner:()=>void;extra?:React.ReactNode}){
 const [status,setStatus]=useState<Status|null>(null),[email,setEmail]=useState(''),[password,setPassword]=useState(''),[register,setRegister]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const scope=useRef(''),channel=useRef<BroadcastChannel|null>(null),live=useRef(true),revision=useRef(0);
 const [recover,setRecover]=useState(false);
 const [renewing,setRenewing]=useState(false),[serviceError,setServiceError]=useState(false),[showPassword,setShowPassword]=useState(false);
 const [logoutError,setLogoutError]=useState('');
 const authFlight=useRef<AbortController|null>(null);
 const flight=useRef<{epoch:number;promise:Promise<void>;controller:AbortController}|null>(null);
 function suspend(){setMemberReady(false);setRenewing(true)}
 function clear(){clearTemporary();configureCloud(true);scope.current='';setRenewing(false);setLogoutError('');setStatus(value=>value?{...value,authenticated:false}:value)}
 async function refresh():Promise<void>{const epoch=revision.current;
  if(flight.current){if(flight.current.epoch===epoch)return flight.current.promise;await flight.current.promise;if(live.current&&epoch===revision.current)return refresh();return}
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  const task=(async()=>{try{
   let next=await api<Status>('/v1/account/status',undefined,controller.signal);if(!live.current||epoch!==revision.current)return;
   if(next.renewable&&(!next.authenticated||(next.expires_at||0)*1000-Date.now()<60000)){
    suspend();try{next=await api<Status>('/v1/account/refresh',{},controller.signal)}catch(error){if(String(error).startsWith('Error: 409:'))return;throw error}
   }
   if(!live.current||epoch!==revision.current)return;
   if(!next.authenticated||next.account_scope!==scope.current)clearTemporary();
   if(next.authenticated)setError('');else setError(value=>value==='暂时连接不上账号服务，请重新检查连接'?'':value);
   configureCloud(true,false,next.authenticated);setRenewing(false);setServiceError(false);scope.current=next.account_scope||'';setStatus(next);
  }catch(error){if(live.current&&epoch===revision.current){
   if(/Error: (401|403):/.test(String(error))){clear();setStatus({available:true,authenticated:false});setServiceError(false);setError('登录已结束，请重新登录')}
   else if(scope.current){suspend();setError('连接暂不可用，正在恢复登录；当前内容暂时只读')}
   else{clear();setStatus({available:false,authenticated:false});setServiceError(true);setError('暂时连接不上账号服务，请重新检查连接')}
  }}finally{clearTimeout(timeout)}})();
  flight.current={epoch,promise:task,controller};try{await task}finally{if(flight.current?.promise===task)flight.current=null}
 }
 useEffect(()=>{live.current=true;void refresh();const poll=setInterval(()=>void refresh(),10000);
  if(typeof BroadcastChannel!=='undefined'){channel.current=new BroadcastChannel('hcla-member-session');channel.current.onmessage=()=>{revision.current++;flight.current?.controller.abort();authFlight.current?.abort();setBusy(false);clear();void refresh()}}
  return()=>{live.current=false;revision.current++;flight.current?.controller.abort();authFlight.current?.abort();clearInterval(poll);channel.current?.close();clearTemporary()};
 },[]);
 useEffect(()=>{if(!status?.authenticated||!status.expires_at)return;const timer=setTimeout(()=>{suspend();void refresh()},Math.max(0,status.expires_at*1000-Date.now()));return()=>clearTimeout(timer)},[status?.authenticated,status?.expires_at]);
 async function logout(){
  if(busy)return;setBusy(true);setLogoutError('');const epoch=++revision.current;flight.current?.controller.abort();
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  const complete=()=>{if(!live.current||epoch!==revision.current)return;revision.current++;flight.current?.controller.abort();clear();setError('');setBusy(false);channel.current?.postMessage({type:'signed-out'});setMessage('已退出账号')};
  try{await api('/v1/account/logout',{},controller.signal);complete()}
  catch(error){if(!live.current||epoch!==revision.current)return;if(/^Error: 401:/.test(String(error)))complete();else setLogoutError('退出未完成，请重试')}
  finally{clearTimeout(timeout);if(live.current&&epoch===revision.current)setBusy(false)}
 }
 if(recover)return <RecoveryEntry initialEmail={email} onBack={()=>setRecover(false)}/>;
 if(status?.authenticated&&status.account_scope)return children(()=>void logout(),status.account_scope,busy?'正在退出账号…':error||logoutError||(renewing?'正在恢复账号登录，当前内容暂时只读':!status.entitlements?.enabled?(status.entitlements?.reason||'账号使用权限尚未开通'):!status.model_enabled?'模型服务尚未启用，已有记录仍可查看':''),renewing||busy,busy,{model:Boolean(status.model_enabled),temporary:Boolean(status.entitlements?.enabled&&status.entitlements.temporary),persistent:Boolean(status.entitlements?.enabled&&status.entitlements.persistent)});
 async function submit(event:React.FormEvent){
  event.preventDefault();if(busy||!status?.available)return;setBusy(true);setError('');setMessage('');
  const epoch=++revision.current;flight.current?.controller.abort();authFlight.current?.abort();
  const controller=new AbortController();authFlight.current=controller;const timeout=setTimeout(()=>controller.abort(),15000);
  try{
   const result=await api<{message?:string}>(register?'/v1/account/register':'/v1/account/login',{email,password},controller.signal);
   if(!live.current||epoch!==revision.current)return;
   if(register){setMessage(result.message||'请检查邮箱完成确认后登录');setRegister(false)}
   else{channel.current?.postMessage({type:'signed-in'});await refresh()}
  }catch{if(live.current&&epoch===revision.current)setError(controller.signal.aborted?'连接等待过久，请重新检查连接后再试；不会自动重复提交':register?'暂时无法创建账号，请检查输入或稍后重试':'登录未完成，请确认邮箱已验证、账号密码正确，或稍后重试')}
  finally{clearTimeout(timeout);if(authFlight.current===controller){authFlight.current=null;if(live.current){setPassword('');setShowPassword(false);setBusy(false)}}}
 }
 return <main className="account-screen"><section className="development-entry member-entry" aria-labelledby="account-heading"><div className="account-brand">HCL <span>Assistant</span></div>{extra}
  <h1 id="account-heading">{register?'创建你的账号':'继续你的对话'}</h1><p className="account-intro">登录后，在你的设备上继续自己的对话。当前仅开放合成内容体验，请勿输入真实私密资料。</p>
  {error&&<p className="account-feedback" role="alert">{error}</p>}{message&&<p className="account-feedback" role="status">{message}</p>}
  {!status?<p role="status">正在检查账号服务…</p>:!status.available?<div className="account-unavailable">{!serviceError&&<p>普通账号服务暂未开放，请稍后再来</p>}<button className="account-secondary" disabled={busy} onClick={()=>void refresh()}>重新检查连接</button></div>:<form onSubmit={event=>void submit(event)}>
   <label>用户邮箱<input type="email" autoComplete="username" value={email} onChange={event=>setEmail(event.target.value)} maxLength={254} disabled={busy} required/></label>
   <div className="account-password-field"><label htmlFor="member-password">用户密码</label><span className="account-password"><input id="member-password" type={showPassword?'text':'password'} autoComplete={register?'new-password':'current-password'} minLength={12} maxLength={1024} value={password} onChange={event=>setPassword(event.target.value)} disabled={busy} required/><button type="button" className="password-visibility" aria-label={showPassword?'隐藏密码':'显示密码'} aria-pressed={showPassword} disabled={busy} onClick={()=>setShowPassword(!showPassword)}>{showPassword?'隐藏':'显示'}</button></span></div>
   <p className="account-hint">{register?'至少 12 个字符。完成邮箱确认后即可登录。':'使用期间会自动保持登录，最长 12 小时。退出会清空临时对话。'}</p>
   <button className="account-primary" disabled={busy||!email||password.length<12}>{busy?'正在处理…':register?'注册账号':'登录账号'}</button>
  </form>}
  {status?.available&&<button className="account-switch" type="button" disabled={busy} onClick={()=>{setRegister(!register);setPassword('');setShowPassword(false);setError('');setMessage('')}}>{register?'已有账号，返回登录':'没有账号，注册'}</button>}
  {status?.recovery_available&&!register&&<button className="account-switch" disabled={busy} onClick={()=>{setPassword('');setRecover(true)}}>忘记密码</button>}
  <details className="account-admin"><summary>管理员入口</summary><button disabled={busy} onClick={()=>{clear();onOwner()}}>打开管理员登录</button></details>
 </section></main>
}
