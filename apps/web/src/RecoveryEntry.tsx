import React,{useEffect,useRef,useState} from 'react';
import {api} from './api';
import './account-entry.css';
type RecoveryStatus={locked?:boolean;available:boolean;ready:boolean;requested?:boolean;updated?:boolean;restart_required?:boolean;expires_at?:number};
declare global {interface Window {__hclaRecovery?:{code:string|null;invalid:boolean}}}
export function RecoveryEntry({onBack,initialEmail='',callback=false}:{onBack:()=>void;initialEmail?:string;callback?:boolean}){
 const [status,setStatus]=useState<RecoveryStatus|null>(null),[email,setEmail]=useState(initialEmail),[password,setPassword]=useState(''),[confirmation,setConfirmation]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const live=useRef(true),revision=useRef(0),flight=useRef<AbortController|null>(null),code=useRef<string|null>(null),exchangeStarted=useRef(false),exchangeFailed=useRef(false),invalidCallback=useRef(false);
 async function perform(work:(signal:AbortSignal,active:()=>boolean)=>Promise<void>){
  const epoch=++revision.current;flight.current?.abort();const controller=new AbortController();flight.current=controller;const timeout=setTimeout(()=>controller.abort(),15000);setBusy(true);
  const active=()=>live.current&&epoch===revision.current;
  try{await work(controller.signal,active)}finally{clearTimeout(timeout);if(active()){setBusy(false);flight.current=null}}
 }
 function reconcile(value:RecoveryStatus){return exchangeFailed.current&&!value.ready&&!value.locked&&!value.updated&&!value.requested?{...value,restart_required:true}:value}
 async function check(){await perform(async(signal,active)=>{try{
  let value=await api<RecoveryStatus>('/v1/account/recovery/status',undefined,signal);
  if(value.available&&code.current&&!exchangeStarted.current){exchangeStarted.current=true;const valueCode=code.current;code.current=null;value=await api<RecoveryStatus>('/v1/account/recovery/exchange',{code:valueCode},signal)}
  if(!active())return;value=reconcile(value);setStatus(value);setError(value.locked||value.updated?'':value.restart_required?'恢复链接已使用、失效或结果未确认，请重新申请链接':invalidCallback.current&&!value.ready?'恢复链接无效，请重新申请':'');
 }catch{if(active()){
  if(exchangeStarted.current)exchangeFailed.current=true;
  let value:RecoveryStatus={available:true,ready:false,restart_required:true};
  if(exchangeStarted.current&&!signal.aborted){try{value=await api<RecoveryStatus>('/v1/account/recovery/status',undefined,signal)}catch{/* Read only; never exchange a code twice. */}}
  if(active()){setStatus(reconcile(value));setError(value.locked||value.ready||value.updated?'':'恢复验证暂未完成。可以检查状态；链接失效时请重新申请，不会自动重复验证或修改密码')}
 }}})}
 useEffect(()=>{live.current=true;if(callback){const initial=window.__hclaRecovery;delete window.__hclaRecovery;code.current=initial?.code||null;if(initial?.invalid){invalidCallback.current=true;setError('恢复链接无效，请重新申请')}};void check();return()=>{live.current=false;revision.current++;flight.current?.abort();code.current=null}},[]);
 useEffect(()=>{if(!status?.ready||!status.expires_at)return;const timer=setTimeout(()=>{revision.current++;flight.current?.abort();setBusy(false);setPassword('');setConfirmation('');setStatus(value=>value?{...value,ready:false,restart_required:true}:value);setError('恢复验证已过期，请重新申请链接')},Math.max(0,status.expires_at*1000-Date.now()));return()=>clearTimeout(timer)},[status?.ready,status?.expires_at]);
 async function request(event:React.FormEvent){event.preventDefault();if(busy)return;setError('');setMessage('');code.current=null;exchangeFailed.current=false;await perform(async(signal,active)=>{try{
  const value=await api<{message:string;expires_at:number}>('/v1/account/recovery/start',{email},signal);if(active()){setStatus({available:true,ready:false,requested:true,expires_at:value.expires_at});setMessage(value.message)}
 }catch{if(active())setError('申请暂未完成，请稍后重试。不会自动重复发送；如果已收到链接，请在当前浏览器打开')}})}
 async function complete(event:React.FormEvent){event.preventDefault();if(busy)return;if(password!==confirmation){setError('两次输入的新密码不一致');return}setError('');await perform(async(signal,active)=>{try{
  const value=await api<{updated:boolean;message:string}>('/v1/account/recovery/complete',{password,confirmation},signal);if(active()){setStatus({available:true,ready:false,updated:value.updated});setMessage(value.message)}
 }catch(caught){if(active()){setError(/^Error: 400:/.test(String(caught))?'密码未更新，请换用更强的新密码再试':'密码更新未确认，请检查恢复状态。现有登录可能已结束，不会自动重复修改');try{const value=await api<RecoveryStatus>('/v1/account/recovery/status',undefined,signal);if(active()){setStatus(value);if(value.locked)setError('')}}catch{/* The visible check action reads state without replaying the mutation. */}}}
 finally{if(active()){setPassword('');setConfirmation('')}}})}
 function restart(){invalidCallback.current=false;exchangeFailed.current=false;revision.current++;flight.current?.abort();code.current=null;exchangeStarted.current=true;setBusy(false);setError('');setMessage('');setPassword('');setConfirmation('');setStatus({available:true,ready:false})}
 return <main className="account-screen"><section className="development-entry member-entry" aria-labelledby="recovery-heading"><div className="account-brand">HCL <span>Assistant</span></div><h1 id="recovery-heading">{status?.updated?'密码已更新':status?.ready?'设置新密码':'找回账号'}</h1>
  <p className="account-intro">恢复链接仅用于修改密码，不能查看对话。请使用发起申请的浏览器打开链接。</p>
  {error&&<p role="alert" className="account-feedback">{error}</p>}{message&&<p role="status" className="account-feedback">{message}</p>}
  {!status?<p role="status">正在检查恢复服务…</p>:!status.available?<p>账号找回服务尚未开放</p>:status.updated?<p>请返回登录，使用新密码继续。</p>:status.locked?<p role="status">上次密码修改结果尚未确认，恢复暂时锁定。请联系管理员核对服务端结果；重新申请链接不会解除锁定。</p>:status.ready?<form onSubmit={event=>void complete(event)}>
   <label>新密码<input type="password" autoComplete="new-password" minLength={12} maxLength={1024} value={password} onChange={event=>setPassword(event.target.value)} disabled={busy} required/></label>
   <label>再次输入新密码<input type="password" autoComplete="new-password" minLength={12} maxLength={1024} value={confirmation} onChange={event=>setConfirmation(event.target.value)} disabled={busy} required/></label>
   <p className="account-hint">至少12个字符。提交修改会结束此账号现有的应用登录；如果修改结果无法确认，系统会暂停恢复并提示下一步。</p>
   <button className="account-primary" disabled={busy||password.length<12||confirmation.length<12}>{busy?'正在更新…':'更新密码并结束现有登录'}</button>
  </form>:status.requested?<p>请查看邮箱。没有收到时，请先检查垃圾邮件，稍后再申请。</p>:status.restart_required?<p>链接无法继续使用。重新申请后，请打开最新收到的链接。</p>:<form onSubmit={event=>void request(event)}><label>账号邮箱<input type="email" autoComplete="username" value={email} onChange={event=>setEmail(event.target.value)} disabled={busy} maxLength={254} required/></label><button className="account-primary" disabled={busy||!email}>{busy?'正在申请…':'发送恢复链接'}</button></form>}
  {(error||!status?.available||status?.locked)&&<button className="account-secondary" disabled={busy} onClick={()=>void check()}>{busy?'正在检查…':'检查恢复状态'}</button>}
  {status?.available&&!status.updated&&!status.locked&&(status.requested||status.restart_required)&&<button className="account-secondary" disabled={busy} onClick={restart}>重新申请链接</button>}
  <button className="account-switch" disabled={busy} onClick={onBack}>返回登录</button>
 </section></main>
}
