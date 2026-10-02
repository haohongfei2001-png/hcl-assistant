import React,{useEffect,useState} from 'react';
import {api,configureCloud} from './api';
import {clearTemporary} from './cloud-temporary';
import {MemberEntry} from './MemberEntry';
import {RecoveryEntry} from './RecoveryEntry';
export type DevelopmentStatus={enabled:boolean;authenticated:boolean;cloud?:boolean;request_bound?:boolean;configuration:{configured?:boolean;provider_enabled?:boolean;temporary_trial?:boolean;member_accounts?:boolean;missing?:string[];invalid?:string[]}};
type TrialStatus={available:boolean;authenticated:boolean;expires_at?:number};
export function DevelopmentEntry({children}:{children:(live:boolean,cloud:boolean,onLogout?:()=>void,trial?:boolean,account?:{scope:string;notice:string;renewing:boolean;logoutPending:boolean;generation?:{model:boolean;temporary:boolean;persistent:boolean}})=>React.ReactNode}){
 const [status,setStatus]=useState<DevelopmentStatus|null>(null),[secret,setSecret]=useState(''),[login,setLogin]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [trial,setTrial]=useState<TrialStatus|null>(null),[guest,setGuest]=useState(false);
 const [ownerMode,setOwnerMode]=useState(false);
 async function logoutOwner(){
  if(busy)return;setBusy(true);setError('');const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  const complete=()=>{clearTemporary();setStatus(value=>value?{...value,authenticated:false}:value)};
  try{await api('/v1/development/logout',{},controller.signal);complete()}
  catch(error){if(/^Error: 401:/.test(String(error)))complete();else setError('退出未完成，请重试')}
  finally{clearTimeout(timeout);setBusy(false)}
 }
 function leaveTrial(message=''){clearTemporary();configureCloud(true,false);setGuest(false);if(message)setTrial(value=>value?{...value,available:false,authenticated:false}:value);setError(message)}
 async function refresh(){try{
  const next=await api<DevelopmentStatus>('/v1/development/status');configureCloud(Boolean(next.request_bound));setStatus(next);setError('');
  if(next.configuration.temporary_trial&&!next.authenticated){const value=await api<TrialStatus>('/v1/trial/status');setTrial(value);if(value.available&&value.authenticated){configureCloud(true,true);setGuest(true)}}
 }catch{setError('暂时无法连接服务，请稍后重试')}}
 useEffect(()=>{void refresh()},[]);
 useEffect(()=>{
  if(!guest||!trial?.expires_at)return;
  let active=true;
  const timer=setTimeout(()=>leaveTrial('本次试用已结束，当前页面的临时内容已清空'),Math.max(0,trial.expires_at*1000-Date.now()));
  const poll=setInterval(()=>{void api<TrialStatus>('/v1/trial/status').then(value=>{if(active&&(!value.available||!value.authenticated))leaveTrial('本次试用已结束，临时内容已清空')}).catch(()=>{if(active)leaveTrial('无法确认试用权限，临时内容已清空，请重新检查')})},10000);
  return()=>{active=false;clearTimeout(timer);clearInterval(poll)};
 },[guest,trial?.expires_at]);
 if(location.pathname==='/account/recovery')return <RecoveryEntry callback onBack={()=>location.assign('/')}/>;
 if(status&&!status.enabled)return children(false,false);
 if(guest)return children(true,true,()=>leaveTrial(),true);
 const trialEntry=trial&&<section><h2>临时试用</h2><p>无需账号，只在当前标签页保留对话；刷新或关闭后丢失。仅使用原创合成内容，请勿输入真实私密资料。</p><p>{trial.expires_at?`本轮试用截止：${new Date(trial.expires_at*1000).toLocaleString()}`:''}</p><button disabled={busy||!trial.available} onClick={async()=>{setBusy(true);setError('');try{await api('/v1/trial/start',{});const value=await api<TrialStatus>('/v1/trial/status');if(!value.available||!value.authenticated)throw new Error();clearTemporary();configureCloud(true,true);setTrial(value);setGuest(true)}catch{setError('试用尚未开始或已结束，请重新检查')}finally{setBusy(false)}}}>{trial.available?'开始临时试用（仅合成内容）':'试用尚未开始或已结束'}</button></section>;
 if(status?.configuration.member_accounts&&!ownerMode)return <MemberEntry extra={trialEntry} onOwner={()=>setOwnerMode(true)}>{(logout,scope,notice,renewing,logoutPending,generation)=>children(true,true,logout,false,{scope,notice,renewing,logoutPending,generation})}</MemberEntry>;
 if(status?.authenticated)return children(true,Boolean(status.cloud),status.cloud?()=>void logoutOwner():undefined,false,status.cloud?{scope:'owner',notice:busy?'正在退出账号…':error,renewing:busy,logoutPending:busy}:undefined);
 const cloud=Boolean(status?.cloud);
 return <main className="development-entry"><h1>{cloud?'HCL Assistant':'HCL Assistant 开发态聊天'}</h1>
  {error&&<p role="alert">{error}</p>}
  {trialEntry}{status?.configuration.member_accounts&&ownerMode&&<button onClick={()=>{setOwnerMode(false);setSecret('')}}>返回用户登录</button>}
  {!status?<button onClick={()=>void refresh()}>检查连接</button>:!status.configuration.configured?<><h2>{cloud?'服务尚未启用':'需要服务器配置'}</h2><p>{cloud?'管理员完成一次性配置后，即可在这里使用。请勿在聊天中提供密码或 API key。':'尚未接通真实聊天。请在服务器安全配置界面填写，不要把 API key 放到聊天或前端。'}</p>{!cloud&&<ul>{[...(status.configuration.missing||[]),...(status.configuration.invalid||[])].map(name=><li key={name}>{name}</li>)}</ul>}<button onClick={()=>void refresh()}>重新检查</button></>:<form onSubmit={async event=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await api('/v1/development/login',cloud?{login,password:secret}:{access_token:secret});setSecret('');await refresh()}catch{setSecret('');setError(cloud?'登录失败或尝试过多，请检查账号和密码后重试':'登录失败或尝试过多，请检查本地访问口令后重试')}finally{setBusy(false)}}}>
   <p>{trial?'管理员入口':'登录后继续你的原创合成内容对话'}</p>{cloud&&<label>账号<input autoComplete="username" value={login} onChange={event=>setLogin(event.target.value)}/></label>}<label>{cloud?'密码':'本地开发访问口令'}<input type="password" autoComplete={cloud?'current-password':'off'} value={secret} onChange={event=>setSecret(event.target.value)}/></label>{!cloud&&<p>这是本地访问口令，不是 DeepSeek API key；不会写入浏览器存储。</p>}<button disabled={busy||!secret||(cloud&&!login)}>{busy?'验证中…':cloud?'登录':'打开聊天'}</button>
  </form>}
 </main>
}
