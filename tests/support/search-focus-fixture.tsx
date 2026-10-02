/** Browser-only controlled props for the real shared shell; never a production entry. */
import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AssistantShell} from '../../apps/web/src/AssistantShell';
import type {TurnView} from '../../apps/web/src/product-view';

type Controls={resolve:(id:string)=>void;reject:(id:string)=>void;mount:(id:string)=>void;requested:()=>string[]};
declare global {interface Window {__focusFixture?:Controls}}
const turn=(id:string):TurnView=>({id:'run-'+id,input:'ORIGINAL_SEARCH_FIXTURE '+id,output:'Original controlled answer '+id,actions:[]});
function Fixture(){
 const [current,setCurrent]=useState('base'),[turns,setTurns]=useState<TurnView[]>([turn('base')]),[draft,setDraft]=useState('');
 const pending=useRef(new Map<string,{resolve:()=>void;reject:(error:Error)=>void}>()),requested=useRef<string[]>([]);
 useEffect(()=>{const controls:Controls={resolve:id=>{const entry=pending.current.get(id);if(!entry)throw new Error('No pending fixture navigation');pending.current.delete(id);entry.resolve()},reject:id=>{const entry=pending.current.get(id);if(!entry)throw new Error('No pending fixture navigation');pending.current.delete(id);entry.reject(new Error('Original controlled navigation failure'))},mount:id=>{setCurrent(id);setTurns([turn(id),...['tail-1','tail-2','tail-3'].map(suffix=>({...turn(id+'-'+suffix),output:'Original trailing synthetic content for navigation visibility. '.repeat(70)}))])},requested:()=>requested.current.slice()};window.__focusFixture=controls;return()=>{if(window.__focusFixture===controls)delete window.__focusFixture}},[]);
 return <AssistantShell environment="受控合成界面，不连接服务" environmentDetails={<p>Original component fixture only</p>}
  conversations={['base','A','B'].map(id=>({id,title:'Original target '+id,memory:'CONVERSATION'}))} currentId={current} title={'Original target '+current} scope="本会话背景" turns={turns} draft={draft} setDraft={setDraft} busy={false} error=""
  onNew={()=>{setCurrent('base');setTurns([turn('base')])}} onOpen={id=>{requested.current.push(id);return new Promise<void>((resolve,reject)=>pending.current.set(id,{resolve,reject}))}} onSend={()=>{}} onUpload={()=>{}} onMemory={()=>{}}
  onSearch={async()=>['A','B'].map(id=>({conversation_id:id,title:'Original target '+id,run_id:'run-'+id,snippet:'Original search result '+id,historical:false,related_changes:[],scope:'CONVERSATION',source:'CONTROLLED_FIXTURE'}))} historyRevision={0} settings={<p>Original fixture settings</p>}/>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
