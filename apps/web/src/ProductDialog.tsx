import React,{useContext,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {ReadingAnchorContext} from './ReadingAnchor';
export function ProductDialog({label,onClose,children,contextual=['查看依据','原文','理解变化'].includes(label)}:{label:string;onClose:()=>void;children:React.ReactNode;contextual?:boolean}){
 const ref=useRef<HTMLDialogElement>(null),focus=useRef<HTMLElement|null>(null),latestClose=useRef(onClose),reading=useContext(ReadingAnchorContext),[wide,setWide]=useState(()=>innerWidth>=1024);latestClose.current=onClose;
 function close(explicit=false){if(contextual)reading.close(explicit,()=>latestClose.current());else latestClose.current()}
 const closeRef=useRef(close);closeRef.current=close;
 useEffect(()=>{const resize=()=>setWide(innerWidth>=1024);window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize)},[]);
 useEffect(()=>{const node=ref.current;if(!node)return;if(!focus.current)focus.current=document.activeElement as HTMLElement;if(node.open)node.close();if(contextual&&wide)node.show();else node.showModal();const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'&&contextual&&wide&&!document.querySelector('dialog[open][aria-modal="true"]')){event.preventDefault();closeRef.current(false)}};window.addEventListener('keydown',escape);return()=>{window.removeEventListener('keydown',escape);node.close()}},[wide,contextual]);
 useEffect(()=>()=>{if(!contextual&&focus.current?.isConnected)focus.current.focus({preventScroll:true})},[contextual]);
 useLayoutEffect(()=>{if(contextual&&ref.current)ref.current.scrollTop=reading.panelScroll(label)},[label,contextual]);
 return <dialog id="panel" ref={ref} className={'overlay'+(contextual?' context-panel':'')} onScroll={()=>{if(contextual&&ref.current)reading.panelScroll(label,ref.current.scrollTop)}} aria-label={label} aria-modal={contextual&&wide?'false':'true'} onCancel={event=>{event.preventDefault();close()}}><div className="panel-header"><strong>{label}</strong><div>{contextual&&<button className="return-to-answer" onClick={()=>close(true)}>返回回答位置</button>}<button aria-label={'关闭'+label} onClick={()=>close()}>关闭</button></div></div><div id="panelContent" key={label}>{children}</div></dialog>;
}
