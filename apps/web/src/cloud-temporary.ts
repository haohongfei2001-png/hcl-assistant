// Temporary bodies/snapshots live only in this tab's RAM. No browser persistence.
import type {Conversation,Run} from './api';
type Packet={view:{conversation:Conversation;state_version:number;runs:Run[];events:unknown[]};context:Record<string,unknown>;sources:{id:string;version:number;sha256:string;deleted?:boolean}[];explains:Record<string,unknown>;inspections:Record<string,unknown>;snapshot:unknown};
type Entry={conversation:Conversation;packet:Packet;requestId?:string;done?:Promise<void>;error?:Error;listeners:Set<()=>void>;unavailable?:boolean};
const entries=new Map<string,Entry>();
const runOwners=new Map<string,Entry>();
let enabled=false;
export function setCloudTemporary(value:boolean){enabled=value}
function entryForRun(id:string){return runOwners.get(id)}
export function clearTemporary(){entries.clear();runOwners.clear()}
function notify(entry:Entry){for(const listener of entry.listeners)listener()}
async function execute(entry:Entry,request:unknown){
 if(entry.unavailable)throw new Error('409: 临时连接已中断，请新建对话');
 if(entry.requestId)throw new Error('409: 请先停止当前回答，再提交临时对话修订');
 const requestId=crypto.randomUUID();entry.requestId=requestId;entry.error=undefined;
 let accepted:(run:Run)=>void=()=>{},rejected:(e:Error)=>void=()=>{};
 const acceptedPromise=new Promise<Run>((resolve,reject)=>{accepted=resolve;rejected=reject});
 entry.done=(async()=>{
  let wasAccepted=false;
  try{
   const response=await fetch('/v1/temporary/execute',{method:'POST',headers:{'Content-Type':'application/json','X-HCLA-Request':'1'},body:JSON.stringify({conversation_id:entry.conversation.id,request_id:requestId,request,snapshot:entry.packet.snapshot})});
   if(!response.ok){const value=await response.json();throw new Error(`${response.status}: ${value.error}`)}
   const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer='';let complete=false;
   while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let boundary;
    while((boundary=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,boundary);buffer=buffer.slice(boundary+2);const line=block.split('\n').find(l=>l.startsWith('data: '));if(!line)continue;const event=JSON.parse(line.slice(6));
     if(event.type==='cloud.accepted'||event.type==='cloud.run'){
      const run=event.payload as Run;runOwners.set(run.run_id,entry);
      const privacy=(request as {event?:{revisions?:{action:string}[]}}).event?.revisions?.some(r=>['DELETE','STOP_USING'].includes(r.action));
      if(privacy&&!wasAccepted){entry.packet={view:{conversation:entry.conversation,state_version:run.state_version_after,runs:[],events:[]},context:{records:[],managed_records:[],managed_sources:[]},sources:[],explains:{},inspections:{},snapshot:null}}
      entry.packet.view.state_version=run.state_version_after;entry.packet.view.runs=entry.packet.view.runs.some(r=>r.run_id===run.run_id)?entry.packet.view.runs.map(r=>r.run_id===run.run_id?run:r):[...entry.packet.view.runs,run];
      if(!wasAccepted){wasAccepted=true;accepted(run)}notify(entry);
     }else if(event.type==='cloud.completed'){entry.packet=event.payload as Packet;complete=true;notify(entry)}
     else if(event.type==='cloud.error')throw new Error(event.payload.error);
    }
   }
   if(!complete)throw new Error('临时连接中断，内容无法从服务器恢复；请新建对话，不会自动重复模型请求');
  }catch(error){entry.error=error instanceof Error?error:new Error('临时请求未完成');
   // Any ambiguous accepted request may have revoked data. Never serve the old snapshot or provisional answer.
   if(wasAccepted||!/^(?:400|401|403|409|413|422|429):/.test(entry.error.message)){entry.unavailable=true;entry.packet={view:{conversation:entry.conversation,state_version:0,runs:[],events:[]},context:{records:[],managed_records:[],managed_sources:[]},sources:[],explains:{},inspections:{},snapshot:null}}
   if(!wasAccepted)rejected(entry.error);notify(entry)}
  finally{entry.requestId=undefined}
 })();
 return acceptedPromise;
}
export async function temporaryStream(id:string,onEvent:()=>void,signal:AbortSignal):Promise<boolean>{
 const entry=entryForRun(id);if(!enabled||!entry)return false;
 const listener=()=>{if(!signal.aborted)onEvent()};entry.listeners.add(listener);listener();
 try{await entry.done;if(entry.error&&!signal.aborted)throw entry.error;listener()}finally{entry.listeners.delete(listener)}
 return true;
}
export async function temporaryApi(path:string,body:unknown,raw:(path:string,body?:unknown)=>Promise<unknown>):Promise<{handled:boolean;value?:unknown}>{
 if(!enabled)return {handled:false};
 const url=new URL(path,window.location.origin),parts=url.pathname.split('/').filter(Boolean);
 if(path==='/v1/conversations'){
  if(body===undefined)return {handled:true,value:[...await raw(path) as Conversation[],...[...entries.values()].map(e=>e.conversation)]};
  const data=body as {memory?:string;topic_id?:string;title?:string};
  if(data.memory==='TEMPORARY'){
   if(data.topic_id)throw new Error('403: 临时对话不能加入项目');
   const conversation={id:'temp-'+crypto.randomUUID(),title:data.title||'临时对话',memory:'TEMPORARY',topic_id:null};
   const packet={view:{conversation,state_version:0,runs:[],events:[]},context:{state_version:0,policy_revision:0,records:[],managed_records:[],managed_sources:[]},sources:[],explains:{},inspections:{},snapshot:null};
   entries.set(conversation.id,{conversation,packet,listeners:new Set()});return {handled:true,value:conversation};
  }
 }
 const conversationId=parts[1]==='conversations'?parts[2]:url.searchParams.get('conversation_id')||(body as {scope?:{conversation_id?:string}}|undefined)?.scope?.conversation_id;
 const entry=conversationId?entries.get(conversationId):undefined;
 if(entry){
  if(parts[1]==='conversations'&&parts[3]==='events'||parts[1]==='sources'&&body!==undefined)return {handled:true,value:await execute(entry,body)};
  if(parts[1]==='conversations')return {handled:true,value:structuredClone(entry.packet.view)};
  if(parts[1]==='context')return {handled:true,value:structuredClone(entry.packet.context)};
  if(parts[1]==='sources'){
   const source=entry.packet.sources.find(s=>s.id===parts[2]&&s.version===Number(url.searchParams.get('version'))&&s.sha256===url.searchParams.get('sha256')&&!s.deleted);
   if(!source)throw new Error('403: 原文已不可用');return {handled:true,value:structuredClone(source)};
  }
 }
 if(parts[1]==='runs'){
  const owner=entryForRun(parts[2]);if(owner){
   if(parts[3]==='cancel'){
    if(owner.requestId)await raw('/v1/temporary/cancel',{request_id:owner.requestId});
    const run=owner.packet.view.runs.find(r=>r.run_id===parts[2])!;return {handled:true,value:structuredClone(run)};
   }
   if(parts.length===3){if(owner.unavailable)throw new Error('409: 临时对话已中断，内容已清理');return {handled:true,value:structuredClone(owner.packet.view.runs.find(r=>r.run_id===parts[2]))}};
  }
 }
 if(parts[1]==='answers'&&parts[3]==='explain')for(const item of entries.values())if(parts[2] in item.packet.explains)return {handled:true,value:structuredClone(item.packet.explains[parts[2]])};
 if(parts[1]==='lab')for(const item of entries.values())if(parts[3] in item.packet.inspections)return {handled:true,value:structuredClone(item.packet.inspections[parts[3]])};
 if(parts[1]==='history'&&parts[2]==='search'){
  const query=(url.searchParams.get('q')||'').toLocaleLowerCase();const results=await raw(path) as unknown[];
  for(const item of entries.values())for(const run of item.packet.view.runs)if(!run.redacted){const text=(run.input_text||'')+'\n'+(run.answer?.text||'');if(text.toLocaleLowerCase().includes(query))results.push({conversation_id:item.conversation.id,title:item.conversation.title,run_id:run.run_id,snippet:text.slice(0,180),historical:run.outdated,related_changes:run.changes||[],scope:'TEMPORARY',source:'CURRENT_TAB_MEMORY'})}
  return {handled:true,value:results};
 }
 return {handled:false};
}
