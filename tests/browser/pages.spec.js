import {test,expect} from '@playwright/test';
const key='hcl-assistant-pages-preview-v2';
async function open(page){await page.goto('http://127.0.0.1:4174/');}
async function send(page,text){await page.locator('#composer').fill(text);await page.locator('#send').click();}
async function stored(page){return page.evaluate(key=>JSON.parse(localStorage.getItem(key)),key);}
test('Pages temporary canary is absent from all persistent bytes and reload',async({page})=>{
 await open(page);await page.locator('#memoryScope').selectOption('TEMPORARY');await page.locator('#newConversation').click();await send(page,'记录：ORIGINAL_BROWSER_TEMP_CANARY');await send(page,'演示：查看当前背景');
 expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain('ORIGINAL_BROWSER_TEMP_CANARY');expect(await page.evaluate(()=>JSON.stringify(sessionStorage))).not.toContain('ORIGINAL_BROWSER_TEMP_CANARY');
 await page.reload();await expect(page.locator('body')).not.toContainText('ORIGINAL_BROWSER_TEMP_CANARY');
});
test('Pages persistent delete clears source title input output after refresh; stop blocks next use',async({page})=>{
 await open(page);await send(page,'记录：ORIGINAL_BROWSER_DELETE_CANARY');await send(page,'演示：查看当前背景');
 await page.locator('#openMemory').click();const row=page.locator('.memory-row').filter({hasText:'ORIGINAL_BROWSER_DELETE_CANARY'}).first();await row.getByRole('button',{name:'停止使用',exact:true}).click();await page.locator('#closePanel').click();
 await send(page,'演示：查看当前背景');await expect(page.locator('article').last()).not.toContainText('ORIGINAL_BROWSER_DELETE_CANARY');
 await page.locator('#openMemory').click();await page.locator('.memory-row').filter({hasText:'ORIGINAL_BROWSER_DELETE_CANARY'}).first().getByRole('button',{name:'删除',exact:true}).click();await page.locator('#closePanel').click();
 expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain('ORIGINAL_BROWSER_DELETE_CANARY');await expect(page.locator('body')).not.toContainText('ORIGINAL_BROWSER_DELETE_CANARY');await page.reload();await expect(page.locator('body')).not.toContainText('ORIGINAL_BROWSER_DELETE_CANARY');
});
test('Pages complete file first tail and bytes preserved; malformed/oversize refused',async({page})=>{
 await open(page);const text='ORIGINAL_HEAD\n'+'全文'.repeat(3000)+'\nORIGINAL_TAIL',bytes=Buffer.from(text);
 await page.locator('#fileInput').setInputFiles({name:'original.md',mimeType:'text/markdown',buffer:bytes});await expect(page.locator('article').last()).toContainText('ORIGINAL_TAIL');
 let data=await stored(page);expect(data.conversations[0].records[0].content).toBe(text);expect(data.conversations[0].records[0].byteLength).toBe(bytes.length);await page.reload();await expect(page.locator('article').last()).toContainText('ORIGINAL_TAIL');
 await page.locator('#fileInput').setInputFiles({name:'bad.md',mimeType:'text/markdown',buffer:Buffer.from([255])});await expect(page.locator('#error')).toBeVisible();
 await page.locator('#fileInput').setInputFiles({name:'large.txt',mimeType:'text/plain',buffer:Buffer.alloc(65537,65)});await expect(page.locator('#error')).toContainText('64 KiB');expect((await stored(page)).conversations[0].records).toHaveLength(1);
});
test('Pages negation ambiguous correction leave originals; exact target and recorded evidence bind',async({page})=>{
 await open(page);await send(page,'记录：Lin Thursday');await send(page,'记录：Sora Monday');const original=(await stored(page)).conversations[0].records[0].id;
 await send(page,'这不是我想问的问题');await send(page,'更正：周六');expect((await stored(page)).conversations[0].records[0].status).toBe('ACTIVE');
 await send(page,`更正 ${original}：Lin Friday`);expect((await stored(page)).conversations[0].records[1].status).toBe('ACTIVE');await send(page,'演示：查看当前背景');
 await expect(page.locator('article').last()).toContainText('Lin Friday');await expect(page.locator('article').last()).not.toContainText('Lin Thursday');await page.locator('[data-explain]').last().click();await expect(page.locator('#panelContent')).toContainText('Lin Friday');await expect(page.locator('#panelContent')).not.toContainText('Lin Thursday');
});
test('Pages open relationship question has no fabricated historical basis',async({page})=>{
 await open(page);await send(page,'她为什么不回复，关系发生了什么？');await expect(page.locator('article').last()).toContainText('暂不支持');await page.locator('[data-explain]').last().click();await expect(page.locator('#panelContent')).toContainText('本次没有人物背景依据');await expect(page.locator('#panelContent')).not.toContainText('当前会话中与冲突相关的已知背景');
});
test('Pages IME confirmation does not send and has no backend requests',async({page})=>{
 const forbidden=[];page.on('request',req=>{if(req.url().includes('/v1/'))forbidden.push(req.url())});await open(page);await page.locator('#composer').fill('中文合成草稿');await page.locator('#composer').dispatchEvent('keydown',{key:'Enter',code:'Enter',isComposing:true});await expect(page.locator('#composer')).toHaveValue('中文合成草稿');await expect(page.locator('article')).toHaveCount(0);expect(forbidden).toEqual([]);
});
