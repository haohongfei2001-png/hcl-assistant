import React,{useEffect,useRef,useState} from 'react';
import {Dialog} from './panels';
import {accountPath,requireMemberReady} from './api';
import {temporaryApi} from './cloud-temporary';
import {InspectionView} from './InspectionView';
import {projectLocalInspection,type InspectionViewModel} from './inspection-model';

type LoadedInspection={raw:unknown;view:InspectionViewModel};
async function readInspection(path:string,runId:string,signal:AbortSignal):Promise<LoadedInspection>{
 if(signal.aborted)throw new DOMException('Inspection aborted','AbortError');
 requireMemberReady(path);
 // Current-tab temporary projections are authoritative for their own runs. A
 // missing guest projection throws locally; it must not fall through to owner data.
 const local=await temporaryApi(path,undefined,async()=>{throw new Error('Inspection cannot use an unscoped fallback')});
 if(signal.aborted)throw new DOMException('Inspection aborted','AbortError');
 requireMemberReady(path);
 if(local.handled)return {raw:local.value,view:projectLocalInspection(local.value,runId)};
 const response=await fetch(accountPath(path),{method:'GET',cache:'no-store',headers:{'Content-Type':'application/json'},signal});
 const raw:unknown=await response.json();
 if(signal.aborted)throw new DOMException('Inspection aborted','AbortError');
 requireMemberReady(path);
 if(!response.ok)throw new Error(`检查记录读取失败（HTTP ${response.status}）；未使用缓存导出`);
 return {raw,view:projectLocalInspection(raw,runId)};
}
export function Lab({runId,onClose}:{runId:string;onClose:()=>void}){
 const [loaded,setLoaded]=useState<LoadedInspection|null>(null),[error,setError]=useState(''),[exporting,setExporting]=useState(false);
 const current=useRef(runId),generation=useRef(0),loadRequest=useRef<AbortController|null>(null),exportRequest=useRef<AbortController|null>(null);
 current.current=runId;
 useEffect(()=>{
  const token=++generation.current,request=new AbortController();loadRequest.current=request;exportRequest.current?.abort();exportRequest.current=null;
  setLoaded(null);setError('');setExporting(false);
  void readInspection(`/v1/lab/runs/${encodeURIComponent(runId)}`,runId,request.signal).then(value=>{if(!request.signal.aborted&&token===generation.current&&current.current===runId)setLoaded(value)}).catch(e=>{if(!request.signal.aborted&&token===generation.current&&current.current===runId)setError(String(e))});
  return()=>{generation.current++;request.abort();exportRequest.current?.abort();exportRequest.current=null};
 },[runId]);
 function close(){generation.current++;loadRequest.current?.abort();exportRequest.current?.abort();exportRequest.current=null;onClose()}
 function cancelExport(){exportRequest.current?.abort();exportRequest.current=null;setExporting(false);setError('导出已取消，未生成文件。关闭后可重新检查当前权限下的记录。')}
 async function download(){
  if(exportRequest.current)return;
  const target=runId,token=generation.current,request=new AbortController();exportRequest.current=request;setExporting(true);setError('');
  // Invalidate the displayed copy while permissions are being rechecked; never export the earlier response.
  setLoaded(null);loadRequest.current?.abort();
  try{
   const latest=await readInspection(`/v1/lab/export/${encodeURIComponent(target)}`,target,request.signal);
   if(request.signal.aborted||token!==generation.current||current.current!==target)return;
   setLoaded(latest);
   const url=URL.createObjectURL(new Blob([JSON.stringify(latest.raw,null,2)],{type:'application/json'}));
   const link=document.createElement('a');link.href=url;link.download=`${latest.view.mode.toLowerCase()}-run-${target}.json`;
   document.body.appendChild(link);
   try{link.click()}finally{link.remove();window.setTimeout(()=>URL.revokeObjectURL(url),0)}
  }catch(e){if(!request.signal.aborted&&token===generation.current&&current.current===target){setLoaded(null);setError(String(e))}}
  finally{if(exportRequest.current===request){exportRequest.current=null;if(token===generation.current&&current.current===target)setExporting(false)}}
 }
 const value=loaded?.view.runId===runId?loaded.view:null;
 return <Dialog label="HCL Lab" onClose={close}>
  {error&&<p role="alert">{error}</p>}
  {value?<InspectionView value={value}/>:<p role="status">{exporting?'正在按当前权限读取可导出的记录…':error?'记录当前不可用。关闭后可重新检查；不会显示先前缓存。':'正在读取所选运行的记录…'}</p>}
  <button disabled={!value||exporting} onClick={()=>void download()}>导出当前权限下的 {value?.mode==='DEVELOPMENT_CHAT'?'development':value?.mode==='EXPERIMENTAL'?'experimental':value?.mode==='MOCK'?'mock':'只读'} 记录</button>
  {exporting&&<button onClick={cancelExport}>取消导出</button>}
  {!value&&!exporting&&!error&&<p>关闭检查即可取消读取；不会取消或重新执行原运行。</p>}
 </Dialog>;
}
