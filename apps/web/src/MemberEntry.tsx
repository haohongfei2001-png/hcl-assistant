import React,{useEffect,useRef,useState} from 'react';
import {api,configureCloud,setMemberReady} from './api';
import {clearTemporary} from './cloud-temporary';

type Status={available:boolean;authenticated:boolean;renewable?:boolean;expires_at?:number;account_scope?:string;model_enabled?:boolean;entitlements?:{enabled:boolean;reason?:string|null}};
export function MemberEntry({children,onOwner,extra}:{children:(logout:()=>void,scope:string,notice:string,renewing:boolean,logoutPending:boolean)=>React.ReactNode;onOwner:()=>void;extra?:React.ReactNode}){
 const [status,setStatus]=useState<Status|null>(null),[email,setEmail]=useState(''),[password,setPassword]=useState(''),[register,setRegister]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const scope=useRef(''),channel=useRef<BroadcastChannel|null>(null),live=useRef(true),revision=useRef(0);
 const [renewing,setRenewing]=useState(false);
 const flight=useRef<{epoch:number;promise:Promise<void>;controller:AbortController}|null>(null);
 function suspend(){setMemberReady(false);setRenewing(true)}
 function clear(){clearTemporary();configureCloud(true);scope.current='';setRenewing(false);setStatus(value=>value?{...value,authenticated:false}:value)}
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
   if(next.authenticated)setError('');
   configureCloud(true,false,next.authenticated);setRenewing(false);scope.current=next.account_scope||'';setStatus(next);
  }catch(error){if(live.current&&epoch===revision.current){if(/Error: (401|403):/.test(String(error))||!scope.current)clear();else suspend();setError(scope.current?'连接暂不可用，正在恢复登录；当前内容暂时只读':'登录已结束，请重新登录')}}finally{clearTimeout(timeout)}})();
  flight.current={epoch,promise:task,controller};try{await task}finally{if(flight.current?.promise===task)flight.current=null}
 }
 useEffect(()=>{live.current=true;void refresh();const poll=setInterval(()=>void refresh(),10000);
  if(typeof BroadcastChannel!=='undefined'){channel.current=new BroadcastChannel('hcla-member-session');channel.current.onmessage=()=>{revision.current++;flight.current?.controller.abort();clear();void refresh()}}
  return()=>{live.current=false;revision.current++;flight.current?.controller.abort();clearInterval(poll);channel.current?.close();clearTemporary()};
 },[]);
 useEffect(()=>{if(!status?.authenticated||!status.expires_at)return;const timer=setTimeout(()=>{suspend();void refresh()},Math.max(0,status.expires_at*1000-Date.now()));return()=>clearTimeout(timer)},[status?.authenticated,status?.expires_at]);
 async function logout(){
  if(busy)return;setBusy(true);const epoch=++revision.current;flight.current?.controller.abort();
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  const complete=()=>{if(!live.current||epoch!==revision.current)return;clear();channel.current?.postMessage({type:'signed-out'});setMessage('已退出账号')};
  try{await api('/v1/account/logout',{},controller.signal);complete()}
  catch(error){if(!live.current||epoch!==revision.current)return;if(/^Error: 401:/.test(String(error)))complete();else setError('退出未完成，请重试')}
  finally{clearTimeout(timeout);if(live.current)setBusy(false)}
 }
 if(status?.authenticated&&status.account_scope)return children(()=>void logout(),status.account_scope,busy?'正在退出账号…':error||(renewing?'正在恢复账号登录，当前内容暂时只读':!status.entitlements?.enabled?(status.entitlements?.reason||'账号使用权限尚未开通'):!status.model_enabled?'模型服务尚未启用，已有记录仍可查看':''),renewing||busy,busy);
 return <main className="development-entry member-entry"><h1>HCL Assistant</h1>{extra}
  <h2>{register?'创建账号':'登录账号'}</h2><p>使用邮箱保存和找回自己的合成内容对话。请勿输入真实私密资料。</p>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  {!status?<p role="status">正在检查账号服务</p>:!status.available?<p>普通账号服务尚未启用</p>:<form onSubmit={async event=>{event.preventDefault();if(busy)return;setBusy(true);setError('');setMessage('');revision.current++;flight.current?.controller.abort();try{
   const result=await api<{message?:string}>(register?'/v1/account/register':'/v1/account/login',{email,password});setPassword('');
   if(register){setMessage(result.message||'请检查邮箱完成确认后登录');setRegister(false)}else{channel.current?.postMessage({type:'signed-in'});await refresh()}
  }catch{setPassword('');setError(register?'暂时无法创建账号，请检查输入或稍后重试':'登录未完成，请确认邮箱已验证、账号密码正确，或稍后重试')}finally{setBusy(false)}}}>
   <label>用户邮箱<input type="email" autoComplete="username" value={email} onChange={event=>setEmail(event.target.value)} maxLength={254} required/></label>
   <label>用户密码<input type="password" autoComplete={register?'new-password':'current-password'} minLength={12} maxLength={1024} value={password} onChange={event=>setPassword(event.target.value)} required/></label>
   <p>{register?'密码至少 12 个字符。完成邮箱确认后才能登录。':'使用中会自动续期，单次登录最长 12 小时；退出后临时内容会清空。'}</p>
   <button disabled={busy||!email||password.length<12}>{busy?'处理中…':register?'注册账号':'登录账号'}</button>
  </form>}
  <button type="button" disabled={busy} onClick={()=>{setRegister(!register);setPassword('');setError('');setMessage('')}}>{register?'已有账号，返回登录':'没有账号，注册'}</button>
  <details><summary>管理员入口</summary><button onClick={()=>{clear();onOwner()}}>打开管理员登录</button></details>
 </main>
}
