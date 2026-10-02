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


test('guest Lab reads and exports only its current-tab run without an owner inspection request',async({page},info)=>{
 const inspectionRequests=[];page.on('request',r=>{if(new URL(r.url()).pathname.includes('/lab/'))inspectionRequests.push(r.url())});await enter(page);await send(page,'原创合成：GUEST_INSPECTION_RAM_ONLY');await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'在 Lab 检查',exact:true}).last().click();const lab=page.getByRole('dialog',{name:'HCL Lab'});await expect(lab).toContainText('GUEST_INSPECTION_RAM_ONLY');await expect(lab.getByRole('alert')).toHaveCount(0);expect(inspectionRequests).toEqual([]);
 const downloadPromise=page.waitForEvent('download');await lab.getByRole('button',{name:'导出当前权限下的 development 记录',exact:true}).click();const download=await downloadPromise;expect(download.suggestedFilename()).toMatch(/^development_chat-run-/);expect(inspectionRequests).toEqual([]);await page.screenshot({path:info.outputPath('guest-owned-inspection.png'),fullPage:true});await page.getByRole('button',{name:'关闭HCL Lab',exact:true}).click();await page.reload();await expect(page.locator('body')).not.toContainText('GUEST_INSPECTION_RAM_ONLY');
});

test('thinking-only stream timeout exposes safe diagnostics without a retry, answer, or hidden text',async({page},info)=>{
 let calls=0;page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/v1/trial/execute')calls++});await enter(page);await page.getByLabel('消息',{exact:true}).fill('ORIGINAL_THINKING_TIMEOUT_FIXTURE');await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('.messages')).toContainText('UNKNOWN',{timeout:20000});await expect(page.locator('.messages')).toContainText('不会自动重复请求');await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看本次模型与 HCL 回执'}).last().click();const receipt=page.getByRole('dialog',{name:'本次调用回执'});await expect(receipt).toContainText('wall_timeout');await expect(receipt).toContainText('请求发送状态：已发送');await expect(receipt).toContainText('HTTP 状态：200');await expect(receipt).toContainText('已接收数据片段：1');await expect(receipt).toContainText('思考片段数（不含内容）：1');await expect(receipt).toContainText('回答片段数：0');await expect(receipt).toContainText('NO_TREATMENT');await expect(receipt).toContainText('费用：未知');await expect(receipt).toContainText('不会自动重复模型请求');await expect(page.locator('body')).not.toContainText('OFFLINE_HIDDEN_REASONING_MUST_NOT_RENDER');expect(calls).toBe(1);await page.screenshot({path:info.outputPath('guest-thinking-timeout-receipt.png'),fullPage:true});await page.getByRole('button',{name:'关闭本次调用回执'}).click();await page.getByRole('button',{name:'在 Lab 检查',exact:true}).last().click();await expect(page.getByRole('dialog',{name:'HCL Lab'})).toContainText('wall_timeout');await expect(page.getByRole('dialog',{name:'HCL Lab'})).not.toContainText('OFFLINE_HIDDEN_REASONING_MUST_NOT_RENDER');expect(calls).toBe(1);
});
