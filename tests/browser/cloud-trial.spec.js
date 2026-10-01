import {test,expect} from '@playwright/test';
test.skip(!process.env.HCLA_TEST_POSTGRES_DSN,'Disposable Postgres only');
test.beforeEach(async({request})=>{await request.post('/v1/fixture/trial-mode')});
async function enter(page){await page.goto('/');await page.getByRole('button',{name:'开始临时试用（仅合成内容）'}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible()}
async function send(page,text){await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('.assistant-message').last()).toContainText('原创离线自然语言');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0)}
test('guest opens temporary chat without account and never fetches owner history',async({page})=>{
 const requests=[];page.on('request',r=>requests.push(new URL(r.url()).pathname));await enter(page);await send(page,'原创合成：GUEST_RAM_ONLY_CANARY');
 await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByLabel('记忆范围')).toHaveCount(0);await page.getByRole('button',{name:'关闭设置'}).click();
 expect(requests.filter(p=>p==='/v1/conversations'||p==='/v1/topics'||p==='/v1/history/search')).toEqual([]);
 expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage,cookie:document.cookie}))).not.toContain('GUEST_RAM_ONLY_CANARY');
 expect((await page.request.get('/v1/conversations')).status()).toBe(401);
 await page.reload();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await expect(page.locator('body')).not.toContainText('GUEST_RAM_ONLY_CANARY');
});
test('two browsers cannot see each other temporary bodies or owner routes',async({browser,page})=>{
 await enter(page);await send(page,'原创合成：BROWSER_A_PRIVATE_CANARY');
 const other=await browser.newContext();const b=await other.newPage();await b.goto('http://127.0.0.1:5173/');await b.getByRole('button',{name:'开始临时试用（仅合成内容）'}).click();await expect(b.getByLabel('消息',{exact:true})).toBeVisible();await expect(b.locator('body')).not.toContainText('BROWSER_A_PRIVATE_CANARY');
 expect((await b.request.get('http://127.0.0.1:5173/v1/history/search?q=PRIVATE')).status()).toBe(401);await other.close();
});
test('expiry stops access and clears guest tab bodies',async({page})=>{
 await enter(page);await send(page,'原创合成：EXPIRED_GUEST_CANARY');await page.request.post('/v1/fixture/trial-expire');
 await expect(page.getByRole('alert')).toContainText('试用已结束',{timeout:15000});await expect(page.locator('body')).not.toContainText('EXPIRED_GUEST_CANARY');
 expect((await page.request.post('/v1/trial/start',{data:{},headers:{Origin:'http://127.0.0.1:5173','X-HCLA-Request':'1'}})).status()).toBe(403);
});
