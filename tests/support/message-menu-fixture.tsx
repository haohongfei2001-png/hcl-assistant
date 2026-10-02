/** Browser-only synthetic stream controls for the actual shared shell. */
import React,{useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AssistantShell} from '../../apps/web/src/AssistantShell';
import {ProductDialog} from '../../apps/web/src/ProductDialog';
import {focusComposerAfterRun} from '../../apps/web/src/MessageMenuAnchor';
import type {TurnView} from '../../apps/web/src/product-view';
type Controls={update:(kind:'same-line'|'wrap'|'complete')=>void;clicks:()=>number;showOutside:()=>void;outsideClicks:()=>number;navigate:()=>void};
declare global {interface Window {__menuFixture?:Controls}}
function Fixture(){
 const [current,setCurrent]=useState('menu'),[output,setOutput]=useState('Original controlled streaming answer.'),[pending,setPending]=useState(true),[draft,setDraft]=useState(''),[receipt,setReceipt]=useState(false),[clicks,setClicks]=useState(0),[outside,setOutside]=useState(false),[outsideClicks,setOutsideClicks]=useState(0);
 useEffect(()=>{const controls:Controls={update:kind=>{if(kind==='same-line')setOutput(text=>text+' [1]');else if(kind==='wrap')setOutput(text=>text+'\n'+('Original synthetic growing line. '.repeat(16)));else setPending(false)},clicks:()=>clicks,showOutside:()=>setOutside(true),outsideClicks:()=>outsideClicks,navigate:()=>setCurrent('menu-next')};window.__menuFixture=controls;return()=>{if(window.__menuFixture===controls)delete window.__menuFixture}},[clicks,outsideClicks]);
 useEffect(()=>{if(!pending)focusComposerAfterRun(document.querySelector<HTMLTextAreaElement>('#composer'))},[pending]);
 const turn:TurnView={id:'menu-original',input:'ORIGINAL_MENU_STREAM_FIXTURE',output,pending,evidence:outside?{id:'evidence',label:'外部合成操作',onActivate:()=>setOutsideClicks(value=>value+1)}:undefined,actions:[{id:'provider',label:'查看合成测试回执',onActivate:()=>{setClicks(value=>value+1);setReceipt(true)}},{id:'source',label:'查看合成输入',onActivate:()=>{}},{id:'inspect',label:'检查合成记录',onActivate:()=>{}}]};
 return <AssistantShell environment="受控合成界面，不连接服务" environmentDetails={<p>Original component fixture only</p>} conversations={[{id:'menu',title:'Original streaming menu',memory:'CONVERSATION'}]} currentId={current} title="Original streaming menu" scope="本会话背景" turns={[turn]} draft={draft} setDraft={setDraft} busy={pending} error="" onNew={()=>{}} onOpen={()=>{}} onSend={()=>{}} onStop={()=>{}} onUpload={()=>{}} onMemory={()=>{}} settings={<p>Original fixture settings</p>} panels={receipt&&<ProductDialog label="合成测试回执" onClose={()=>setReceipt(false)}><p>Original action reached exactly once.</p></ProductDialog>}/>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
