import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyState,createConversation,submit,changeRecord,resolveBasis,selectedBackground,persistentState,saveState,loadState,decodeFile,exportConversation,STORAGE_KEY,LEGACY_KEY} from '../../pages-preview/preview-model.js';
const setup = memory => {const state=emptyState(),c=createConversation(state,memory);return {state,c};};
const storage = () => {const data=new Map();return {getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k),bytes:()=>JSON.stringify([...data])};};
test('temporary body, title, runs and derived output never persist; other conversations survive',()=>{
 const {state,c}=setup('TEMPORARY'),s=storage();submit(state,c.id,'记录：ORIGINAL_TEMP_SECRET');submit(state,c.id,'演示：查看当前背景');
 const saved=createConversation(state);submit(state,saved.id,'记录：INDEPENDENT_PERSISTENT');saveState(state,s);
 assert(!s.bytes().includes('ORIGINAL_TEMP_SECRET'));assert(s.bytes().includes('INDEPENDENT_PERSISTENT'));
 assert.equal(loadState(s).conversations.length,1);assert.equal(persistentState(state).conversations.length,1);
});
test('delete clears raw/run/derived/title/export and reload bytes; independent source remains',()=>{
 const {state,c}=setup(),s=storage();const run=submit(state,c.id,'记录：ORIGINAL_DELETE_CANARY');submit(state,c.id,'演示：查看当前背景');
 submit(state,c.id,'记录：INDEPENDENT_SOURCE');changeRecord(state,c.id,run.recordId,'DELETED');saveState(state,s);
 assert(!JSON.stringify(exportConversation(c)).includes('ORIGINAL_DELETE_CANARY'));assert(!s.bytes().includes('ORIGINAL_DELETE_CANARY'));
 assert(!JSON.stringify(loadState(s)).includes('ORIGINAL_DELETE_CANARY'));assert(s.bytes().includes('INDEPENDENT_SOURCE'));
 assert.equal(submit(state,c.id,'演示：查看当前背景').basisRefs.length,1);
});
test('stop prevents subsequent use but historical reference remains honestly stopped',()=>{
 const {state,c}=setup();const first=submit(state,c.id,'记录：STOP_CANARY'),historical=submit(state,c.id,'演示：查看当前背景');
 changeRecord(state,c.id,first.recordId,'STOPPED');const next=submit(state,c.id,'演示：查看当前背景');
 assert.deepEqual(next.basisRefs,[]);assert(!next.text.includes('STOP_CANARY'));assert.equal(resolveBasis(c,historical)[0].status,'STOPPED');
 assert.throws(()=>changeRecord(state,c.id,first.recordId,'GUESS'));
});
test('supported UTF-8 file preserves entire content and byte count beyond 1800 chars',()=>{
 const content='ORIGINAL_HEAD\n'+'中文'.repeat(6000)+'\nORIGINAL_TAIL';const bytes=new TextEncoder().encode(content),f=decodeFile('original.md',bytes),{state,c}=setup();
 const run=submit(state,c.id,f.content,f);assert.equal(run.input,content);assert.equal(c.records[0].content,content);assert.equal(c.records[0].byteLength,bytes.length);
 assert.equal(decodeFile('limit.txt',new Uint8Array(65536).fill(65)).content.length,65536);
});
test('oversize malformed UTF-8 binary and unknown formats explicitly refused',()=>{
 for(const [name,bytes] of [['bad.pdf',new Uint8Array([65])],['too.txt',new Uint8Array(65537)],['bad.md',new Uint8Array([0xff])],['nul.txt',new Uint8Array([0])]]) assert.throws(()=>decodeFile(name,bytes));
});
test('ordinary negation ambiguous correction and unknown target never mutate background',()=>{
 const {state,c}=setup();submit(state,c.id,'记录：Lan sends draft Thursday');const original=c.records[0].id;
 for(const text of ['这不是我要的结论','更正：星期六','更正 record-missing：星期六']) submit(state,c.id,text);
 assert.equal(c.records.find(r=>r.id===original).status,'ACTIVE');assert.equal(selectedBackground(c).length,1);
});
test('explicit correction targets exact record; unrelated and historical originals preserved',()=>{
 const {state,c}=setup();const first=submit(state,c.id,'记录：Lan Thursday'),second=submit(state,c.id,'记录：Mira Sunday'),old=submit(state,c.id,'演示：查看当前背景');
 const changed=submit(state,c.id,`更正 ${first.recordId}：Lan Friday`);assert.equal(changed.status,'COMPLETED');
 assert.equal(c.records.find(r=>r.id===first.recordId).status,'SUPERSEDED');assert.equal(c.records.find(r=>r.id===second.recordId).status,'ACTIVE');
 assert(old.text.includes('Lan Thursday'));assert.equal(resolveBasis(c,old)[0].content,'Lan Thursday');
 const next=submit(state,c.id,'演示：查看当前背景');assert(!next.text.includes('Lan Thursday'));assert(next.text.includes('Lan Friday'));
});
test('open input fabricates no basis/capability and questions are unresolved not facts',()=>{
 const {state,c}=setup();const first=submit(state,c.id,'她不回信息，是什么关系？');assert.deepEqual(first.basisRefs,[]);assert.deepEqual(first.caps,[]);assert.equal(first.status,'UNSUPPORTED');assert.equal(c.records[0].kind,'UNRESOLVED');
 assert.equal(submit(state,c.id,'为什么2+2？').status,'UNSUPPORTED');assert.equal(submit(state,c.id,'2+2').text,'4。');
});
test('basis is exact read lineage, absent elsewhere and cannot cross conversation',()=>{
 const {state,c}=setup();const first=submit(state,c.id,'记录：ORIGINAL_BASIS');const run=submit(state,c.id,'演示：查看当前背景');
 assert.deepEqual(run.basisRefs,[{recordId:first.recordId,version:1}]);assert.equal(resolveBasis(c,run)[0].content,'ORIGINAL_BASIS');
 const other=createConversation(state);assert.deepEqual(submit(state,other.id,'演示：查看当前背景').basisRefs,[]);
 assert.equal(submit(state,other.id,`更正 ${first.recordId}：cross-scope`).status,'UNSUPPORTED');
});
test('v1 migration removes temporary and deleted copies without losing independent originals',()=>{
 const s=storage();s.setItem(LEGACY_KEY,JSON.stringify({conversations:[{id:'temp',memory:'TEMPORARY',title:'TEMP_OLD',records:[{content:'TEMP_OLD'}],runs:[]},{id:'saved',memory:'CONVERSATION',title:'DELETE_OLD',records:[{id:'r1',status:'DELETED',content:'DELETE_OLD'},{id:'r2',status:'ACTIVE',content:'KEEP_OLD'}],runs:[{input:'DELETE_OLD',text:'DELETE_OLD'}]}]}));
 const state=loadState(s);assert.equal(s.getItem(LEGACY_KEY),null);assert(!s.bytes().includes('TEMP_OLD'));assert(!s.bytes().includes('DELETE_OLD'));assert(s.bytes().includes('KEEP_OLD'));assert.equal(selectedBackground(state.conversations[0]).length,0);
});
test('storage failure is thrown, never silent successful persistence',()=>{
 const {state}=setup();assert.throws(()=>saveState(state,{getItem(){return null},setItem(){throw new Error('quota')}}),/quota/);
});

test('stale tab cannot resurrect deletion or stop-use persisted by another tab',()=>{
 const {state,c}=setup(),s=storage();const first=submit(state,c.id,'记录：STALE_TAB_CANARY');saveState(state,s);
 const tabA=loadState(s),tabB=loadState(s);changeRecord(tabA,c.id,first.recordId,'STOPPED');saveState(tabA,s);
 submit(tabB,c.id,'记录：unrelated');assert.throws(()=>saveState(tabB,s),/其他页面/);
 const tabC=loadState(s);changeRecord(tabC,c.id,first.recordId,'DELETED');saveState(tabC,s);
 assert.throws(()=>saveState(tabA,s),/其他页面/);assert(!s.bytes().includes('STALE_TAB_CANARY'));
});
test('v2 reload cleans simultaneous/reintroduced legacy bodies and exposes cleanup failure',()=>{
 const {state}=setup(),s=storage();saveState(state,s);s.setItem(LEGACY_KEY,'LEGACY_TEMP_CANARY');loadState(s);assert(!s.bytes().includes('LEGACY_TEMP_CANARY'));
 s.setItem(LEGACY_KEY,'legacy');assert.throws(()=>loadState({...s,removeItem(){throw new Error('cleanup denied')}}),/cleanup denied/);
});
