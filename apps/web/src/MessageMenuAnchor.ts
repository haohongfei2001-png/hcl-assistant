import {useEffect,useLayoutEffect,useRef,type RefObject} from 'react';

type OwnedMenu={details:HTMLDetailsElement;anchor:HTMLElement;answer:HTMLElement;offset:number;conversation:string|null};
type StagedMenu=OwnedMenu&{height:number};
/** Keep the action under an existing gesture; retain geometry, never answer text. */
export function useMessageMenuAnchor(scroll:RefObject<HTMLDivElement|null>,conversation:string|null,turns:unknown,bottom:RefObject<boolean>){
 const owned=useRef<OwnedMenu|null>(null),staged=useRef<StagedMenu|null>(null),pins=useRef(new Map<HTMLElement,string>()),pointer=useRef(false),cleanupFrame=useRef(0),stageTimer=useRef(0),pointerTimer=useRef(0),pointerVersion=useRef(0);
 function clean(){cleanupFrame.current=0;if(pointer.current)return;for(const [answer,original] of pins.current){if(owned.current?.answer===answer)continue;answer.style.minHeight=original;pins.current.delete(answer)}}
 function later(){if(!cleanupFrame.current)cleanupFrame.current=requestAnimationFrame(clean)}
 function clearStage(){staged.current=null;window.clearTimeout(stageTimer.current)}
 function release(){owned.current=null;clearStage();later()}
 function restore(value:OwnedMenu){const container=scroll.current;if(!container)return;const delta=value.anchor.getBoundingClientRect().top-container.getBoundingClientRect().top-value.offset;if(Math.abs(delta)>.5)container.scrollTop+=delta}
 function capture(target:HTMLElement){
  const details=target.closest<HTMLDetailsElement>('details'),container=scroll.current;
  if(!details||!container?.contains(details)||!details.querySelector('.message-menu'))return;
  const summary=details.querySelector<HTMLElement>('summary'),anchor=target.closest<HTMLElement>('button,summary')||summary,answer=details.closest('article')?.querySelector<HTMLElement>('.assistant-message');
  if(!anchor||!answer||(!details.open&&anchor!==summary))return;
  const value:OwnedMenu={details,anchor,answer,offset:anchor.getBoundingClientRect().top-container.getBoundingClientRect().top,conversation};
  if(!details.open){clearStage();staged.current={...value,height:answer.getBoundingClientRect().height};stageTimer.current=window.setTimeout(clearStage,250);return}
  const pending=staged.current?.details===details&&staged.current.conversation===conversation?staged.current:null;clearStage();
  if(owned.current?.details!==details){owned.current=null;later()}
  if(!pins.current.has(answer)){pins.current.set(answer,answer.style.minHeight);answer.style.minHeight=Math.ceil(pending?.height??answer.getBoundingClientRect().height)+'px'}
  owned.current=pending&&anchor===summary?pending:value;bottom.current=false;restore(owned.current);
 }
 function toggle(details:HTMLDetailsElement){if(details.open)capture(details.querySelector<HTMLElement>('summary')||details);else if(owned.current?.details===details||staged.current?.details===details)release()}
 useLayoutEffect(()=>{
  const value=owned.current;if(staged.current&&staged.current.conversation!==conversation)clearStage();if(!value){const waiting=staged.current;if(waiting?.details.open)capture(waiting.anchor);return}
  if(value.conversation!==conversation||!value.anchor.isConnected||!value.answer.isConnected||!value.details.open){release();return}
  restore(value);
 },[turns,conversation]);
 useEffect(()=>{
  const outside=(event:Event)=>{if(owned.current&&!owned.current.details.contains(event.target as Node))release();else if(staged.current&&!staged.current.details.contains(event.target as Node))clearStage()};
  const down=(event:Event)=>{pointer.current=true;const version=++pointerVersion.current;window.clearTimeout(pointerTimer.current);pointerTimer.current=window.setTimeout(()=>{if(version!==pointerVersion.current)return;pointer.current=false;release()},15000);outside(event)};
  const up=()=>{pointerVersion.current++;pointer.current=false;window.clearTimeout(pointerTimer.current);later()};
  const cancel=()=>{clearStage();release();up()};
  const intent=(event:Event)=>{if(event instanceof KeyboardEvent&&!['ArrowUp','ArrowDown','PageUp','PageDown','Home','End'].includes(event.key))return;release()};
  window.addEventListener('pointerdown',down,true);window.addEventListener('pointerup',up,true);window.addEventListener('pointercancel',cancel,true);window.addEventListener('blur',up);window.addEventListener('focusin',outside,true);window.addEventListener('wheel',intent,{capture:true,passive:true});window.addEventListener('touchmove',intent,{capture:true,passive:true});window.addEventListener('keydown',intent,true);window.addEventListener('resize',release);
  return()=>{owned.current=null;clearStage();pointer.current=false;window.clearTimeout(pointerTimer.current);cancelAnimationFrame(cleanupFrame.current);clean();window.removeEventListener('pointerdown',down,true);window.removeEventListener('pointerup',up,true);window.removeEventListener('pointercancel',cancel,true);window.removeEventListener('blur',up);window.removeEventListener('focusin',outside,true);window.removeEventListener('wheel',intent,true);window.removeEventListener('touchmove',intent,true);window.removeEventListener('keydown',intent,true);window.removeEventListener('resize',release)};
 },[]);
 return {capture,toggle,release};
}

export function focusComposerAfterRun(input:HTMLTextAreaElement|null){
 if(!document.activeElement?.closest('.messages details[open],dialog[open]'))input?.focus();
}
