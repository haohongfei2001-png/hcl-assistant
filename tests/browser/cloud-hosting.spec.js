import {test,expect} from '@playwright/test';
test.skip(!process.env.HCLA_TEST_POSTGRES_DSN,'Cloud browser fixture requires isolated Postgres');
async function enter(page){
 await page.request.post('/v1/fixture/reset-throttle');
 await page.goto('/');await page.getByLabel('账号',{exact:true}).fill('owner');await page.getByLabel('密码',{exact:true}).fill('offline password fixture');const signedIn=page.waitForResponse(r=>r.url().endsWith('/v1/development/login'));await page.getByRole('button',{name:'登录',exact:true}).click();expect((await signedIn).status()).toBe(200);
 await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByLabel('本次仅使用原创合成输入，并使用服务器已批准额度').check();
}
async function close(page){await page.getByRole('button',{name:'关闭设置'}).click()}
async function send(page,text){await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0)}
test('cloud owner login, durable multi-request chat, reload and logout',async({page},info)=>{
 await enter(page);await page.screenshot({path:info.outputPath('cloud-owner-shared-ui.png'),fullPage:true});await expect(page.getByLabel('记忆范围')).toHaveValue('CONVERSATION');await close(page);await send(page,'原创合成设定：云端纸灯是蓝色');await expect(page.locator('.assistant-message').last()).toContainText('原创离线自然语言');
 const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await page.reload();await page.locator(`[data-conversation="${id}"]`).click();await expect(page.locator('.messages')).toContainText('云端纸灯');
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('密码',{exact:true})).toBeVisible();await expect(page.locator('.messages')).toHaveCount(0);
});
test('cloud temporary HCL uses reviewed Bridge and disappears on refresh',async({page},info)=>{
 await enter(page);await page.getByLabel('记忆范围').selectOption('TEMPORARY');await page.getByRole('button',{name:'发送原创 HCL 合成样例（计一次调用）'}).click();await close(page);await expect(page.locator('.assistant-message').last()).toContainText('Ada');
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看本次模型与 HCL 回执'}).last().click();await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('EXECUTED');await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('显式用于回答 true');
 await page.screenshot({path:info.outputPath('cloud-temporary-hcl-receipt.png'),fullPage:true});expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage}))).not.toContain('workshop');expect(await page.locator('body').textContent()).not.toContain('HIDDEN_REASONING_CANARY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await page.reload();await expect(page.locator(`[data-conversation="${id}"]`)).toHaveCount(0);
});
test('cloud temporary multi-turn uses tab state and privacy deletion clears sources',async({page})=>{
 await enter(page);await page.getByLabel('记忆范围').selectOption('TEMPORARY');await close(page);await send(page,'报告[云端合成]：TEMP_CLOUD_DELETE_CANARY');await send(page,'另一个原创合成问题');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'TEMP_CLOUD_DELETE_CANARY'}).getByRole('button',{name:'删除',exact:true}).click();await expect(page.locator('.memory-card').filter({hasText:'TEMP_CLOUD_DELETE_CANARY'})).toHaveCount(0);await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('.messages')).not.toContainText('TEMP_CLOUD_DELETE_CANARY');
});
for(const mode of ['delay','interrupt'])test(`cloud temporary privacy acceptance clears React bodies before ${mode} completion`,async({page})=>{
 await enter(page);await page.getByLabel('记忆范围').selectOption('TEMPORARY');await close(page);await send(page,'报告[隐私合成]：STREAM_DELETE_PRIVATE_CANARY');
 await page.route('**/v1/temporary/execute',route=>route.continue({headers:{...route.request().headers(),'X-HCLA-Fixture-Completion':mode}}));
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'STREAM_DELETE_PRIVATE_CANARY'}).getByRole('button',{name:'删除',exact:true}).click();
 await expect(page.locator('body')).not.toContainText('STREAM_DELETE_PRIVATE_CANARY',{timeout:1000});
 if(mode==='interrupt'){await expect(page.getByRole('alert')).toContainText('中断');await expect(page.locator('body')).not.toContainText('STREAM_DELETE_PRIVATE_CANARY')}
 else await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0);
});
test('logout during a delayed temporary stream cannot resurrect tab bodies',async({page})=>{
 await enter(page);await page.getByLabel('记忆范围').selectOption('TEMPORARY');await close(page);
 await page.route('**/v1/temporary/execute',route=>route.continue({headers:{...route.request().headers(),'X-HCLA-Fixture-Completion':'delay'}}));
 await page.getByLabel('消息',{exact:true}).fill('LOGOUT_TEMP_PRIVATE_CANARY');await page.getByRole('button',{name:'发送',exact:true}).click();
 await expect(page.locator('.messages')).toContainText('LOGOUT_TEMP_PRIVATE_CANARY');
 const conversation=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 const run=await page.evaluate(async id=>(await(await import('/src/api.ts')).api(`/v1/conversations/${id}`)).runs[0].run_id,conversation);
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('密码',{exact:true})).toBeVisible();
 await page.waitForTimeout(1800);
 const result=await page.evaluate(async id=>{try{return JSON.stringify(await(await import('/src/api.ts')).api(`/v1/runs/${id}`))}catch(error){return String(error)}},run);
 expect(result).toContain('401');expect(result).not.toContain('LOGOUT_TEMP_PRIVATE_CANARY');await expect(page.locator('body')).not.toContainText('LOGOUT_TEMP_PRIVATE_CANARY');
});
