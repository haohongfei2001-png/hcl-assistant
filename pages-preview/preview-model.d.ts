export const STORAGE_KEY:string; export const LEGACY_KEY:string;
export function emptyState():any; export function loadState(storage:Storage):any;
export function saveState(state:any,storage:Storage):void;
export function createConversation(state:any,memory?:string,topic?:string):any;
export function submit(state:any,conversationId:string,input:string,meta?:any):any;
export function changeRecord(state:any,conversationId:string,id:string,action:string):void;
export function resolveBasis(c:any,run:any):any[];
export function decodeFile(name:string,bytes:Uint8Array):{content:string;fileName:string;byteLength:number};
export function exportConversation(c:any):any;
