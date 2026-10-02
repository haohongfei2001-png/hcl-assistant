import {test,expect} from '@playwright/test';
import {pbkdf2Sync} from 'node:crypto';
import {mkdirSync,writeFileSync} from 'node:fs';
async function receiptEvidence(info,name,value){mkdirSync(info.outputDir,{recursive:true});const path=info.outputPath(name+'.json');writeFileSync(path,JSON.stringify(value));await info.attach(name,{path,contentType:'application/json'})}
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
test('owner logout shows pending and failed state inside Settings and can retry',async({page})=>{
 await enter(page);const dialog=page.getByRole('dialog',{name:'设置'});let release;const held=new Promise(resolve=>release=resolve);let started;const requested=new Promise(resolve=>started=resolve);let calls=0;
 await page.route('**/v1/development/logout',async route=>{calls++;started();await held;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected logout failure'})})});
 try{await dialog.getByRole('button',{name:'退出登录',exact:true}).click();await requested;
  await expect(dialog.getByRole('button',{name:'正在退出…',exact:true})).toBeDisabled();await expect(dialog).toContainText('正在退出账号');expect(calls).toBe(1);
 }finally{release()}
 await expect(dialog).toContainText('退出未完成，请重试');await expect(dialog.getByRole('button',{name:'退出登录',exact:true})).toBeEnabled();
 await page.unroute('**/v1/development/logout');await dialog.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('密码',{exact:true})).toBeVisible();await expect(page.locator('.messages')).toHaveCount(0);
});
test('owner logout converges to signed out when its server cookie is already absent',async({page,context})=>{
 await enter(page);await context.clearCookies();await page.getByRole('button',{name:'退出登录',exact:true}).click();
 await expect(page.getByLabel('密码',{exact:true})).toBeVisible();await expect(page.locator('.messages')).toHaveCount(0);await expect(page.getByRole('alert')).toHaveCount(0);
});
test('cloud temporary HCL uses reviewed Bridge and disappears on refresh',async({page},info)=>{
 await page.addInitScript(()=>{const probe=window.__receiptProbe={clicks:[],dialogs:[],errors:[]};let previous='';document.addEventListener('click',event=>{const button=event.target?.closest?.('button');if(button?.textContent?.includes('查看本次模型与 HCL 回执'))probe.clicks.push({at:performance.now(),busy:[...document.querySelectorAll('button')].some(b=>b.textContent==='停止')})},true);new MutationObserver(()=>{const current=JSON.stringify([...document.querySelectorAll('dialog')].map(d=>({label:d.getAttribute('aria-label'),open:d.open})));if(current!==previous&&probe.dialogs.length<80){probe.dialogs.push({at:performance.now(),state:JSON.parse(current)});previous=current}}).observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['open']});window.addEventListener('error',event=>probe.errors.push({name:event.error?.name||'Error',message:String(event.message).slice(0,240)}))});
 try{
 await enter(page);await page.getByLabel('记忆范围').selectOption('TEMPORARY');await page.getByRole('button',{name:'发送原创 HCL 合成样例（计一次调用）'}).click();await close(page);await expect(page.locator('.assistant-message').last()).toContainText('Ada');
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看本次模型与 HCL 回执'}).last().click();await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('EXECUTED');await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('显式用于回答 true');
 await page.screenshot({path:info.outputPath('cloud-temporary-hcl-receipt.png'),fullPage:true});expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage}))).not.toContain('workshop');expect(await page.locator('body').textContent()).not.toContain('HIDDEN_REASONING_CANARY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await receiptEvidence(info,'receipt-ui-before-reload',await page.evaluate(()=>window.__receiptProbe));await page.reload();await expect(page.locator(`[data-conversation="${id}"]`)).toHaveCount(0);
 }finally{await receiptEvidence(info,'receipt-ui-events',await page.evaluate(()=>window.__receiptProbe).catch(()=>null));await page.screenshot({path:info.outputPath('receipt-ui-settled.png'),fullPage:true,animations:'disabled'}).catch(()=>{})}
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
test('owner setup uses local crypto and synthetic placeholders without network or storage',async({page})=>{
 // Deliberately fixed test-only bytes: this is not a usable generated credential.
 await page.addInitScript(()=>{
  Object.defineProperty(Crypto.prototype,'getRandomValues',{value:array=>array.fill(7)});
  Object.defineProperty(navigator.clipboard,'writeText',{value:async()=>{window.__syntheticCopied=true}});
  Storage.prototype.setItem=()=>{throw new Error('Setup must not persist')};
 });
 await page.goto('/owner-setup.html');const requests=[];page.on('request',request=>requests.push(request.url()));
 await page.getByLabel('密码（至少 12 个字符）',{exact:true}).fill('😀'.repeat(6));await page.getByLabel('再次输入密码',{exact:true}).fill('😀'.repeat(6));await page.getByRole('button',{name:'生成私人设置',exact:true}).click();await expect(page.getByRole('status')).toContainText('至少 12 个字符');await expect(page.locator('#bundle')).toHaveValue('');
 await page.getByLabel('密码（至少 12 个字符）',{exact:true}).fill('synthetic owner password only');await page.getByLabel('再次输入密码',{exact:true}).fill('synthetic owner password only');await page.getByRole('button',{name:'生成私人设置',exact:true}).click();await expect(page.getByRole('status')).toHaveText('已在当前浏览器生成，未发送或保存');
 const shape=await page.locator('#bundle').evaluate(el=>{const value=JSON.parse(el.value);return {version:value.schema_version,login:value.login,algorithm:value.verifier.split('$')[0],iterations:value.verifier.split('$')[1],syntheticKey:value.temporary_state_key==='07'.repeat(32),masked:el.type==='password'}});
 expect(shape).toEqual({version:1,login:'owner',algorithm:'pbkdf2-sha256',iterations:'600000',syntheticKey:true,masked:true});expect(requests).toEqual([]);
 const expectedVerifier='pbkdf2-sha256$600000$'+'07'.repeat(16)+'$'+pbkdf2Sync('synthetic owner password only',Buffer.alloc(16,7),600000,32,'sha256').toString('hex');expect(await page.locator('#bundle').evaluate((el,expected)=>JSON.parse(el.value).verifier===expected,expectedVerifier)).toBe(true);
 await expect(page.getByLabel('密码（至少 12 个字符）',{exact:true})).toHaveValue('');await page.getByRole('button',{name:'复制到剪贴板'}).click();expect(await page.evaluate(()=>window.__syntheticCopied)).toBe(true);
 await page.getByRole('button',{name:'清空本页'}).click();await expect(page.locator('#bundle')).toHaveValue('');expect(await page.evaluate(()=>location.search+location.hash)).toBe('');
});
