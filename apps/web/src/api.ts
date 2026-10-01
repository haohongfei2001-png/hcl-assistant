export type Conversation={id:string; title:string; topic_id:string|null; memory:string};
export type Ref={source_id:string; version:number; sha256:string; span?:number[]};
export type Change={action:string;old:{record_id:string;content:string;kind:string;source_refs:Ref[]}[];new:{record_id:string;content:string;kind:string;source_refs:Ref[]}[];impact:string;actual_changed:boolean;not_reevaluated_count:number;invalidated_count:number};
export type Run={changes?:Change[];run_id:string; input_text?:string; conversation_id:string; state_version_after:number; input_source_ref:Ref; pending:boolean; outdated:boolean; redacted?:boolean; answer:null|{answer_id:string; text:string; citation_refs:Ref[]}; stream:{seq:number; type:string; payload:{text?:string}}[]; run_receipt:{outcome:string; route:string; mode?:string; development_only?:boolean;actual_treatment?:string;provider?:{requested_model:string|null;actual_model:string|null;request_id:string|null;finish_reason:string|null;send_state:string};usage?:{provider_calls:number|null;input_tokens:number|null;output_tokens:number|null;cost:{amount:number|null;currency:string}};operations?:{selected:boolean;executed:boolean|null;result_produced:boolean|null;used_in_answer:boolean|null}[]}; errors:string[]};
export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-HCLA-Request':'1'},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await response.json(); if(!response.ok)throw new Error(`${response.status}: ${data.error}`); return data;
}
export async function stream(runId:string,onEvent:()=>void,signal:AbortSignal){
 let after=0;
 for(let attempts=0;attempts<3;attempts++){
  try{
   const response=await fetch(`/v1/runs/${runId}/events?after=${after}`,{signal}); if(!response.ok)throw new Error('Stream unavailable');
   const reader=response.body!.getReader(); const decoder=new TextDecoder(); let pending='';
   while(true){const {value,done}=await reader.read(); if(done)break; pending+=decoder.decode(value,{stream:true}); let boundary;
    while((boundary=pending.indexOf('\n\n'))>=0){const block=pending.slice(0,boundary);pending=pending.slice(boundary+2);const line=block.split('\n').find(l=>l.startsWith('data: '));if(line){const event=JSON.parse(line.slice(6));if(event.seq>after){after=event.seq;onEvent();}}}
   }
   const run=await api<Run>(`/v1/runs/${runId}`); if(!run.pending)return;
  }catch(e){if(signal.aborted)return;if(attempts===2)throw e;}
 }
 throw new Error('Stream stopped. Reload history to recover the recorded run.');
}
