import React,{useEffect,useState} from 'react';
import {api} from './api';
export type DevelopmentStatus={enabled:boolean;authenticated:boolean;configuration:{configured?:boolean;missing?:string[];invalid?:string[]}};
export function DevelopmentEntry({children}:{children:(live:boolean)=>React.ReactNode}){
 const [status,setStatus]=useState<DevelopmentStatus|null>(null),[secret,setSecret]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){try{setStatus(await api<DevelopmentStatus>('/v1/development/status'));setError('')}catch{setError('无法连接本地服务，请检查一键启动终端')}}
 useEffect(()=>{void refresh()},[]);
 if(status&&!status.enabled)return children(false);
 if(status?.authenticated)return children(true);
 return <main className="development-entry"><h1>HCL Assistant 开发态聊天</h1><p>仅用于原创合成输入。服务器配置完整并获准预算后才会调用真实模型。</p>{error&&<p role="alert">{error}</p>}{!status?<button onClick={()=>void refresh()}>检查连接</button>:!status.configuration.configured?<><h2>需要服务器配置</h2><p>尚未接通真实聊天。请按开发配置指南在服务器安全配置界面填写，不要把 API key 放到聊天或前端。</p><ul>{[...(status.configuration.missing||[]),...(status.configuration.invalid||[])].map(name=><li key={name}>{name}</li>)}</ul><button onClick={()=>void refresh()}>重新检查</button></>:<form onSubmit={async event=>{event.preventDefault();if(busy)return;setBusy(true);setError('');try{await api('/v1/development/login',{access_token:secret});setSecret('');await refresh()}catch{setSecret('');setError('登录失败或尝试过多，请检查本地访问口令后重试')}finally{setBusy(false)}}}><label>本地开发访问口令<input type="password" autoComplete="off" value={secret} onChange={event=>setSecret(event.target.value)}/></label><p>这是本地访问口令，不是 DeepSeek API key；不会写入浏览器存储。</p><button disabled={busy||!secret}>{busy?'验证中…':'打开聊天'}</button></form>}</main>
}
