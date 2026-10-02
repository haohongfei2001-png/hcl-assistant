import {test,expect} from '@playwright/test';
import {fileURLToPath} from 'node:url';
test.use({trace:'retain-on-failure',screenshot:'only-on-failure'});
const fixture='/@fs'+fileURLToPath(new URL('../support/search-focus-fixture.tsx',import.meta.url));
async function openFixture(page){
 const calls=[];page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/v1/'))calls.push(request.url())});
 await page.route('**/__test__/search-focus',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Original search focus fixture</title></head><body><div id="root"></div><script type="module">import '+JSON.stringify(fixture)+';</script></body></html>'}));
 await page.goto('/__test__/search-focus');await expect(page.getByRole('button',{name:'搜索对话',exact:true})).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>Boolean(window.__focusFixture))).toBe(true);return calls;
}
async function search(page){await page.getByRole('button',{name:'搜索对话',exact:true}).click();await page.getByLabel('搜索历史').fill('Original');await expect(page.locator('.search-hit')).toHaveCount(2)}
const hit=(page,id)=>page.locator('.search-hit').getByRole('button',{name:new RegExp('Original target '+id)});
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));

test('search result focuses its exact run after the target is committed later than navigation resolution',async({page},info)=>{
 const calls=await openFixture(page);await search(page);await hit(page,'A').click();
 await page.evaluate(()=>window.__focusFixture.resolve('A'));await expect(page.getByRole('dialog',{name:'搜索对话'})).toHaveCount(0);await frames(page);
 await expect(page.locator('[data-run="run-A"]')).toHaveCount(0);
 await page.evaluate(()=>window.__focusFixture.mount('A'));
 try{await expect(page.locator('[data-run="run-A"]')).toBeFocused()}
 finally{await page.screenshot({path:info.outputPath('search-delayed-commit.png'),fullPage:true,animations:'disabled'})}
 expect(calls).toEqual([]);
});

test('an older unresolved search selection cannot steal focus from a newer result',async({page},info)=>{
 const calls=await openFixture(page);await search(page);await hit(page,'A').click();await hit(page,'B').click();
 await page.evaluate(()=>{window.__focusFixture.mount('B');window.__focusFixture.resolve('B')});await expect(page.getByRole('dialog',{name:'搜索对话'})).toHaveCount(0);await expect(page.locator('[data-run="run-B"]')).toBeFocused();
 await page.evaluate(()=>window.__focusFixture.resolve('A'));await frames(page);
 try{await expect(page.locator('[data-run="run-B"]')).toBeFocused()}
 finally{await page.screenshot({path:info.outputPath('search-newer-result.png'),fullPage:true,animations:'disabled'})}
 expect(await page.evaluate(()=>window.__focusFixture.requested())).toEqual(['A','B']);expect(calls).toEqual([]);
});

test('ordinary search dismissal restores its trigger and a newer input cancels pending result focus',async({page})=>{
 const calls=await openFixture(page);const trigger=page.getByRole('button',{name:'搜索对话',exact:true});await search(page);await page.getByRole('button',{name:'关闭搜索对话'}).click();await expect(trigger).toBeFocused();
 await search(page);await hit(page,'A').click();await page.evaluate(()=>window.__focusFixture.resolve('A'));await expect(page.getByRole('dialog',{name:'搜索对话'})).toHaveCount(0);await frames(page);
 const composer=page.getByLabel('消息',{exact:true});await composer.click();await composer.fill('NEWER_USER_INPUT');await page.evaluate(()=>window.__focusFixture.mount('A'));await frames(page);
 await expect(composer).toBeFocused();await expect(composer).toHaveValue('NEWER_USER_INPUT');expect(calls).toEqual([]);
});
