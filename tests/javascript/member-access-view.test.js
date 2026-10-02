import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {renderToStaticMarkup} from 'react-dom/server';
import ts from 'typescript';
const require=createRequire(import.meta.url),source=readFileSync(new URL('../../apps/web/src/MemberMembership.tsx',import.meta.url),'utf8');
const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText,module={exports:{}};
new Function('require','module','exports',output)(require,module,module.exports);
const render=value=>renderToStaticMarkup(module.exports.MemberMembership({value}));
test('TEST_ONLY is explicitly non-paid and displays finite lifetime caps',()=>{
 const text=render({enabled:true,access_kind:'TEST_ONLY',expires_at:2000000000,test_max_requests:8,test_max_cost_cny:'100',test_chat_enabled:true});
 assert.match(text,/测试使用资格/);assert.match(text,/这不是付费会员/);assert.match(text,/不会每月自动重置/);assert.match(text,/100/);assert.doesNotMatch(text,/会员有效/);
});
test('readiness-only testing does not promise normal chat',()=>{
 assert.match(render({enabled:true,access_kind:'TEST_ONLY',test_max_requests:1,test_max_cost_cny:'13',test_chat_enabled:false}),/未获准日常聊天/);
});
test('paid membership remains separate and malformed dates cannot crash its view',()=>{
 assert.match(render({enabled:true,access_kind:'PAID_MEMBERSHIP',expires_at:Number.MAX_SAFE_INTEGER}),/会员有效/);
 assert.doesNotMatch(render({enabled:true,access_kind:'PAID_MEMBERSHIP',expires_at:NaN}),/datetime/);
});
