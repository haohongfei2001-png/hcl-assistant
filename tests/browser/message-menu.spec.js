import {test,expect} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import {mkdirSync,writeFileSync} from 'node:fs';
test.use({trace:'retain-on-failure',screenshot:'only-on-failure'});
const fixture='/@fs'+fileURLToPath(new URL('../support/message-menu-fixture.tsx',import.meta.url));
async function openFixture(page){
 const calls=[];page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/v1/'))calls.push(request.url())});
 await page.route('**/__test__/message-menu',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>Original message menu fixture</title></head><body><div id="root"></div><script type="module">import '+JSON.stringify(fixture)+';</script></body></html>'}));
 await page.goto('/__test__/message-menu');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await expect.poll(()=>page.evaluate(()=>Boolean(window.__menuFixture))).toBe(true);
 await page.evaluate(()=>{window.__menuEvents=[];for(const kind of ['pointerdown','pointerup','click'])document.addEventListener(kind,event=>window.__menuEvents.push({kind,target:event.target?.textContent?.slice(0,80),scroll:document.querySelector('.messages')?.scrollTop}),true)});return calls;
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
async function evidence(page,info,before,after){mkdirSync(info.outputDir,{recursive:true});writeFileSync(info.outputPath('menu-gesture.json'),JSON.stringify({before,after,events:await page.evaluate(()=>window.__menuEvents),clicks:await page.evaluate(()=>window.__menuFixture.clicks())}));await page.screenshot({path:info.outputPath('menu-after-stream-update.png'),fullPage:true,animations:'disabled'})}
for(const kind of ['same-line','wrap','complete'])test(`an open message action keeps its pointer gesture through a ${kind} stream update`,async({page},info)=>{
 const calls=await openFixture(page);await page.getByLabel('更多消息操作').click();const action=page.getByRole('button',{name:'查看合成测试回执',exact:true});await expect(action).toBeVisible();
 const before=await action.boundingBox();expect(before).not.toBeNull();const point={x:before.x+before.width/2,y:before.y+before.height/2};
 await page.mouse.move(point.x,point.y);await page.mouse.down();await page.evaluate(kind=>window.__menuFixture.update(kind),kind);await frames(page);const after=await action.boundingBox();await page.mouse.up();
 try{expect(Math.abs(after.y-before.y)).toBeLessThanOrEqual(2);await expect(page.getByRole('dialog',{name:'合成测试回执'})).toBeVisible();expect(await page.evaluate(()=>window.__menuFixture.clicks())).toBe(1);expect(calls).toEqual([])}
 finally{await evidence(page,info,before,after)}
});

test('keyboard message action keeps focus when completion settles and normal dismissal returns it',async({page})=>{
 const calls=await openFixture(page);const summary=page.getByLabel('更多消息操作');await summary.focus();await summary.press('Enter');const action=page.getByRole('button',{name:'查看合成测试回执',exact:true});await action.focus();
 await page.evaluate(()=>window.__menuFixture.update('complete'));await frames(page);await expect(action).toBeFocused();await action.press('Enter');await expect(page.getByRole('dialog',{name:'合成测试回执'})).toBeVisible();await page.getByRole('button',{name:'关闭合成测试回执'}).click();await expect(action).toBeFocused();expect(await page.evaluate(()=>window.__menuFixture.clicks())).toBe(1);expect(calls).toEqual([]);
});

test('manual scrolling releases menu geometry but its open state still prevents automatic bottom following',async({page})=>{
 await openFixture(page);await page.getByLabel('更多消息操作').click();const action=page.getByRole('button',{name:'查看合成测试回执',exact:true});await action.focus();const answer=page.locator('.assistant-message');await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).not.toBe('');
 await page.locator('.messages').hover();await page.mouse.wheel(0,70);await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');await frames(page);const before=await page.locator('.messages').evaluate(el=>el.scrollTop);
 await page.evaluate(()=>window.__menuFixture.update('wrap'));await frames(page);expect(Math.abs(await page.locator('.messages').evaluate(el=>el.scrollTop)-before)).toBeLessThanOrEqual(2);await expect(page.locator('.messages details')).toHaveAttribute('open','');
});

test('closing a menu and resizing the viewport release temporary geometry',async({page})=>{
 await openFixture(page);const summary=page.getByLabel('更多消息操作'),answer=page.locator('.assistant-message');await summary.click();await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).not.toBe('');await summary.click();await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');
 await summary.click();await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).not.toBe('');await page.setViewportSize({width:1100,height:720});await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');
});

test('releasing a completed menu cannot collapse geometry during an outside action gesture',async({page})=>{
 await openFixture(page);await page.evaluate(()=>window.__menuFixture.showOutside());await page.getByLabel('更多消息操作').click();await page.getByRole('button',{name:'查看合成测试回执',exact:true}).focus();await page.evaluate(()=>window.__menuFixture.update('complete'));await frames(page);
 const answer=page.locator('.assistant-message'),outside=page.getByRole('button',{name:'外部合成操作',exact:true});await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).not.toBe('');const before=await outside.boundingBox();
 await page.mouse.move(before.x+before.width/2,before.y+before.height/2);await page.mouse.down();await frames(page);const held=await outside.boundingBox();expect(Math.abs(held.y-before.y)).toBeLessThanOrEqual(2);await page.mouse.up();
 expect(await page.evaluate(()=>window.__menuFixture.outsideClicks())).toBe(1);await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');
});

test('focusing a closed summary and cancelling its gesture leave no pinned answer geometry',async({page})=>{
 await openFixture(page);const summary=page.getByLabel('更多消息操作'),answer=page.locator('.assistant-message');await summary.focus();await page.waitForTimeout(300);await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');
 await summary.dispatchEvent('pointerdown');await summary.dispatchEvent('pointercancel');await frames(page);await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');await expect(page.locator('.messages details')).not.toHaveAttribute('open','');
});

test('conversation navigation releases a menu pin even if the parent reuses the same turn element',async({page})=>{
 await openFixture(page);await page.getByLabel('更多消息操作').click();const answer=page.locator('.assistant-message');await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).not.toBe('');await page.evaluate(()=>window.__menuFixture.navigate());await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','menu-next');await expect.poll(()=>answer.evaluate(el=>el.style.minHeight)).toBe('');
});
