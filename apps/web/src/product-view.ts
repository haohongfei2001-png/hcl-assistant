import type React from 'react';
/** Presentation only. Opaque handles/actions remain owned by the surface adapter. */
export type ConversationView = {id:string; title:string; memory:string; project?:string};
export type TurnAction = {id:string; label:string; onActivate:(event:React.MouseEvent<HTMLButtonElement>)=>void; disabled?:boolean};
export type TurnView = {id:string; input?:string; file?:TurnAction; output:string; notice?:string; pending?:boolean; evidence?:TurnAction;change?:TurnAction; sources?:TurnAction[]; actions:TurnAction[]; retry?:TurnAction};
export type AttachmentView = {name:string; status:'reading'|'registered'|'failed'; detail?:string};
