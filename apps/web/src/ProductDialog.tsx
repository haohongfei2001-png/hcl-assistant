import React,{useEffect,useRef} from 'react';
export function ProductDialog({label,onClose,children}:{label:string;onClose:()=>void;children:React.ReactNode}){
 const ref=useRef<HTMLDialogElement>(null),focus=useRef<HTMLElement|null>(null);
 useEffect(()=>{focus.current=document.activeElement as HTMLElement;ref.current?.showModal();return()=>{ref.current?.close();focus.current?.isConnected&&focus.current.focus()};},[]);
 return <dialog id="panel" ref={ref} className="overlay" aria-label={label} onCancel={e=>{e.preventDefault();onClose()}}><div className="panel-header"><strong>{label}</strong><button aria-label={'关闭'+label} onClick={onClose}>关闭</button></div><div id="panelContent">{children}</div></dialog>;
}
