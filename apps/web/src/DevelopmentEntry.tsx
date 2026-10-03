import React,{useEffect,useRef,useState} from 'react';
import {api,configureCloud} from './api';
import {clearTemporary} from './cloud-temporary';
import {MemberEntry} from './MemberEntry';
import {RecoveryEntry} from './RecoveryEntry';
import type {MemberGeneration} from './MemberMembership';
export type DevelopmentStatus={enabled:boolean;authenticated:boolean;cloud?:boolean;request_bound?:boolean;configuration:{configured?:boolean;provider_enabled?:boolean;provider?:'deepseek'|'qwen';owner_smoke_only?:boolean;temporary_trial?:boolean;member_accounts?:boolean;missing?:string[];invalid?:string[]}};
type TrialStatus={available:boolean;authenticated:boolean;expires_at?:number};
export type AccountSession={scope:string;notice:string;renewing:boolean;logoutPending:boolean;generation?:MemberGeneration};
export function DevelopmentEntry({children}:{children:(live:boolean,cloud:boolean,onLogout?:()=>void,trial?:boolean,account?:AccountSession,provider?:'deepseek'|'qwen')=>React.ReactNode}){
 const [status,setStatus]=useState<DevelopmentStatus|null>(null),[secret,setSecret]=useState(''),[login,setLogin]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [trial,setTrial]=useState<TrialStatus|null>(null),[guest,setGuest]=useState(false);
 // Owner authentication never selects the ordinary-user entry implicitly.
 // A real route keeps refresh and browser Back/Forward consistent.
 const ownerMode=location.pathname==='/admin';
 const [connecting,setConnecting]=useState(false);
 const live=useRef(true),revision=useRef(0);
 const connection=useRef<{controller:AbortController;promise:Promise<void>}|null>(null);
 async function logoutOwner(){
  if(busy)return;setBusy(true);setError('');const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  const complete=()=>{clearTemporary();setStatus(value=>value?{...value,authenticated:false}:value)};
  try{await api('/v1/development/logout',{},controller.signal);complete()}
  catch(error){if(/^Error: 401:/.test(String(error)))complete();else setError('退出未完成，请重试')}
  finally{clearTimeout(timeout);setBusy(false)}
 }
 function leaveTrial(message=''){clearTemporary();configureCloud(true,false);setGuest(false);if(message)setTrial(value=>value?{...value,available:false,authenticated:false}:value);setError(message)}
 async function refresh():Promise<void>{
  if(connection.current)return connection.current.promise;
  const epoch=++revision.current,controller=new AbortController();
  const current={controller,promise:Promise.resolve()};connection.current=current;setConnecting(true);setError('');
  const active=()=>live.current&&epoch===revision.current&&connection.current===current;
  const timeout=setTimeout(()=>controller.abort(),15000);
  current.promise=(async()=>{try{
   const next=await api<DevelopmentStatus>('/v1/development/status',undefined,controller.signal);
   const nextTrial=!ownerMode&&next.configuration.temporary_trial&&!next.authenticated?await api<TrialStatus>('/v1/trial/status',undefined,controller.signal):null;
   if(!active())return;
   const nextGuest=Boolean(nextTrial?.available&&nextTrial.authenticated);
   configureCloud(Boolean(next.request_bound),nextGuest);setStatus(next);setTrial(nextTrial);setGuest(nextGuest);
  }catch{if(active())setError(controller.signal.aborted?'连接等待过久，请检查连接后重试；不会自动重复请求':'暂时无法连接服务，请检查连接后重试')}
  finally{clearTimeout(timeout);if(active()){connection.current=null;setConnecting(false)}}})();
  return current.promise;
 }
 useEffect(()=>{live.current=true;void refresh();return()=>{live.current=false;revision.current++;connection.current?.controller.abort();connection.current=null}},[]);
 useEffect(()=>{
  if(!guest||!trial?.expires_at)return;
  let active=true;
  const timer=setTimeout(()=>leaveTrial('本次试用已结束，当前页面的临时内容已清空'),Math.max(0,trial.expires_at*1000-Date.now()));
  const poll=setInterval(()=>{void api<TrialStatus>('/v1/trial/status').then(value=>{if(active&&(!value.available||!value.authenticated))leaveTrial('本次试用已结束，临时内容已清空')}).catch(()=>{if(active)leaveTrial('无法确认试用权限，临时内容已清空，请重新检查')})},10000);
  return()=>{active=false;clearTimeout(timer);clearInterval(poll)};
 },[guest,trial?.expires_at]);
 if(location.pathname==='/account/recovery')return <RecoveryEntry callback onBack={()=>location.assign('/')}/>;
 if(status&&!status.enabled)return children(false,false);
 if(guest&&!ownerMode)return children(true,true,()=>leaveTrial(),true,undefined,status?.configuration.provider);
 const trialEntry=trial?.available&&<details className="account-trial"><summary>可选：临时合成内容试用</summary><section><h2>临时试用</h2><p>无需账号，只在当前标签页保留对话；刷新或关闭后丢失。仅使用原创合成内容，请勿输入真实私密资料。</p><p>{trial.expires_at?`本轮试用截止：${new Date(trial.expires_at*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})+'（北京时间）'}`:''}</p><button disabled={busy||!trial.available} onClick={async()=>{setBusy(true);setError('');try{await api('/v1/trial/start',{});const value=await api<TrialStatus>('/v1/trial/status');if(!value.available||!value.authenticated)throw new Error();clearTemporary();configureCloud(true,true);setTrial(value);setGuest(true)}catch{setError('试用尚未开始或已结束，请重新检查')}finally{setBusy(false)}}}>{trial.available?'开始临时试用（仅合成内容）':'试用尚未开始或已结束'}</button></section></details>;
 if((status?.cloud||status?.configuration.member_accounts)&&!ownerMode)return <MemberEntry provider={status.configuration.provider} extra={trialEntry} notice={error} onOwner={()=>location.assign('/admin')}>{(logout,scope,notice,renewing,logoutPending,generation)=>children(true,true,logout,false,{scope,notice,renewing,logoutPending,generation},status.configuration.provider)}</MemberEntry>;
 if(status?.authenticated)return children(true,Boolean(status.cloud),status.cloud?()=>void logoutOwner():undefined,false,status.cloud?{scope:'owner',notice:busy?'正在退出账号…':error,renewing:busy,logoutPending:busy,...(status.configuration.provider==='qwen'?{generation:{model:status.configuration.provider_enabled===true,temporary:true,persistent:!status.configuration.owner_smoke_only}}:{})}:undefined,status.configuration.provider);
 const cloud=Boolean(status?.cloud);
 return <main className="account-screen"><section className="development-entry member-entry" aria-labelledby="connection-heading"><div className="account-brand">HCL <span>Assistant</span></div><h1 id="connection-heading">{!status?'连接到你的对话':cloud?'管理员登录':'开发态聊天'}</h1>
  {error&&<p className="account-feedback" role="alert">{error}</p>}
  {connecting&&<p role="status">正在检查连接…</p>}
  {trialEntry}{cloud&&ownerMode&&<button className="account-switch" disabled={busy||connecting} onClick={()=>location.assign('/')}>返回用户登录</button>}
  {!status?<button className="account-secondary" disabled={connecting} onClick={()=>void refresh()}>检查连接</button>:!status.configuration.configured?<><h2>{cloud?'服务尚未启用':'需要服务器配置'}</h2><p>{cloud?'管理员完成一次性配置后，即可在这里使用。请勿在聊天中提供密码或 API key。':'尚未接通真实聊天。请在服务器安全配置界面填写，不要把 API key 放到聊天或前端。'}</p>{!cloud&&<ul>{[...(status.configuration.missing||[]),...(status.configuration.invalid||[])].map(name=><li key={name}>{name}</li>)}</ul>}<button className="account-secondary" disabled={connecting} onClick={()=>void refresh()}>重新检查</button></>:<form onSubmit={async event=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await api('/v1/development/login',cloud?{login,password:secret}:{access_token:secret});setSecret('');await refresh()}catch{setSecret('');setError(cloud?'登录失败或尝试过多，请检查账号和密码后重试':'登录失败或尝试过多，请检查本地访问口令后重试')}finally{setBusy(false)}}}>
   <p className="account-intro">{cloud?'供服务维护人员使用。普通用户请返回用户登录。':'登录后继续你的原创合成内容对话'}</p>{cloud&&<label>账号<input autoComplete="username" value={login} onChange={event=>setLogin(event.target.value)}/></label>}<label>{cloud?'密码':'本地开发访问口令'}<input type="password" autoComplete={cloud?'current-password':'off'} value={secret} onChange={event=>setSecret(event.target.value)}/></label>{!cloud&&<p className="account-hint">这是本地访问口令，不是 DeepSeek API key；不会写入浏览器存储。</p>}<button className="account-primary" disabled={busy||connecting||!secret||(cloud&&!login)}>{busy?'验证中…':cloud?'登录':'打开聊天'}</button>
  </form>}
 </section></main>
}
