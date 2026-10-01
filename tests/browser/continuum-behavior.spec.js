import {test,expect} from '@playwright/test';
const pages='http://127.0.0.1:4174/';
test.use({trace:'on',video:'on'});
for(const surface of ['local','pages']){
 test(`${surface} attachment selection is local pending state until explicit commit`,async({page})=>{
  await page.goto(surface==='local'?'/':pages);let events=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/events'))events++});
  const composer=page.getByLabel('消息',{exact:true});await composer.fill('INDEPENDENT_ATTACHMENT_DRAFT');
  await page.getByLabel('上传文本文件').setInputFiles({name:'pending-original.txt',mimeType:'text/plain',buffer:Buffer.from('PENDING_ORIGINAL_ONLY')});
  await expect(page.locator('.staged-attachment')).toContainText('尚未提交');await expect(page.locator('article')).toHaveCount(0);expect(events).toBe(0);await expect(composer).toHaveValue('INDEPENDENT_ATTACHMENT_DRAFT');
  await page.getByRole('button',{name:'移除待提交附件'}).click();await expect(page.locator('.staged-attachment')).toHaveCount(0);await expect(page.locator('article')).toHaveCount(0);
  await page.getByLabel('上传文本文件').setInputFiles({name:'accepted-original.txt',mimeType:'text/plain',buffer:Buffer.from('ACCEPTED_ORIGINAL_ONLY')});await page.getByRole('button',{name:'提交附件',exact:true}).click();await expect(page.locator('article')).toHaveCount(1);await expect(page.locator('.staged-attachment')).toHaveCount(0);await expect(composer).toHaveValue('INDEPENDENT_ATTACHMENT_DRAFT');
 });
 test(`${surface} context panel restores semantic trigger and permits deliberate reading`,async({page})=>{
  await page.setViewportSize({width:1448,height:1086});await page.goto(surface==='local'?'/':pages);
  for(let i=0;i<4;i++){await page.getByLabel('消息',{exact:true}).fill((surface==='local'?'报告[岚]：':'记录：')+`原创合成记录${i}。`+'这是一条用于校验阅读位置的原创合成说明，不能解释成真实人物经历。'.repeat(12));await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('article')).toHaveCount(i+1)}
  const trigger=page.locator('article').nth(1).getByRole('button',{name:'查看依据',exact:true});await trigger.scrollIntoViewIfNeeded();await trigger.focus();const offset=()=>trigger.evaluate(el=>el.getBoundingClientRect().top-document.querySelector('.messages').getBoundingClientRect().top);const before=await offset();await trigger.click();
  const panel=page.getByRole('dialog',{name:'查看依据',exact:true});await expect(panel).toHaveAttribute('aria-modal','false');await expect(page.locator('article').nth(1)).toHaveClass(/is-context-target/);
  await panel.getByRole('button',{name:'返回回答位置',exact:true}).click();await expect(panel).toHaveCount(0);await expect(trigger).toBeFocused();await expect.poll(async()=>Math.abs(await offset()-before)).toBeLessThanOrEqual(2);
  await trigger.click();await page.setViewportSize({width:1024,height:768});await page.getByRole('button',{name:'返回回答位置',exact:true}).click();await expect(trigger).toBeInViewport();
  await page.setViewportSize({width:1448,height:1086});await trigger.scrollIntoViewIfNeeded();await trigger.click();await page.locator('.messages').dispatchEvent('wheel',{deltaY:-2000});await page.locator('.messages').evaluate(el=>el.scrollTop=0);await page.getByRole('button',{name:'关闭查看依据',exact:true}).click();await expect.poll(()=>page.locator('.messages').evaluate(el=>el.scrollTop)).toBeLessThan(80);
  // A user wheel after close must cancel restoration instead of being pulled back.
  await page.setViewportSize({width:1448,height:1086});await trigger.scrollIntoViewIfNeeded();await trigger.click();await page.getByRole('button',{name:'返回回答位置',exact:true}).click();await page.locator('.messages').dispatchEvent('wheel',{deltaY:400});await page.locator('.messages').evaluate(el=>el.scrollTop+=400);const at=await page.locator('.messages').evaluate(el=>el.scrollTop);await page.waitForTimeout(450);expect(Math.abs(await page.locator('.messages').evaluate(el=>el.scrollTop)-at)).toBeLessThanOrEqual(2);
 });
}
test('Pages reset cancellation preserves pending file and confirmed reset clears it',async({page})=>{
 await page.goto(pages);await page.getByLabel('上传文本文件').setInputFiles({name:'RESET_PENDING_CANARY.txt',mimeType:'text/plain',buffer:Buffer.from('original pending reset')});await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByText('高级与演示',{exact:true}).click();page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'重置合成预览'}).click();await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.locator('.staged-attachment')).toContainText('RESET_PENDING_CANARY');await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByText('高级与演示',{exact:true}).click();page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'重置合成预览'}).click();await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.locator('body')).not.toContainText('RESET_PENDING_CANARY');
});
test('long history stays in navigation while header and composer remain in viewport',async({page})=>{
 await page.goto(pages);await page.evaluate(()=>{const conversations=Array.from({length:90},(_,i)=>({id:'history-'+i,title:'原创历史 '+i,memory:'CONVERSATION',version:0,records:[],runs:[]}));localStorage.setItem('hcl-assistant-pages-preview-v2',JSON.stringify({schemaVersion:2,storageRevision:'long-history-original',currentId:'history-0',conversations}))});await page.reload();await expect(page.locator('.brand')).toBeInViewport();await expect(page.locator('.chat-workspace>header')).toBeInViewport();await expect(page.getByRole('button',{name:'发送',exact:true})).toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1)).toBe(true);expect(await page.locator('#sidebar nav').evaluate(el=>el.scrollHeight>el.clientHeight)).toBe(true);
});
