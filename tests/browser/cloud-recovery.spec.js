import {test,expect} from '@playwright/test';
test.skip(!process.env.HCLA_TEST_POSTGRES_DSN,'Disposable Postgres and injected Auth only');
test.beforeEach(async({request})=>{await request.post('/v1/fixture/recovery-mode')});
async function requestLink(page,email='a@example.test'){
 await page.goto('/');await page.getByRole('button',{name:'忘记密码',exact:true}).click();const emailInput=page.getByLabel('账号邮箱'),restart=page.getByRole('button',{name:'重新申请链接'});await expect(emailInput.or(restart)).toBeVisible();if(await restart.isVisible())await restart.click();await emailInput.fill(email);await page.getByRole('button',{name:'发送恢复链接',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('如果该邮箱可以找回账号');
 const response=await page.request.post('/v1/fixture/recovery-link',{data:{email}});expect(response.status()).toBe(200);return (await response.json()).path;
}
async function enterLink(page,path){await page.goto(path);await expect(page.getByLabel('新密码',{exact:true})).toBeVisible();expect(new URL(page.url()).search).toBe('')}
async function change(page,password){await page.getByLabel('新密码',{exact:true}).fill(password);await page.getByLabel('再次输入新密码',{exact:true}).fill(password);await page.getByRole('button',{name:'更新密码并结束现有登录'}).click()}
async function login(page,password='offline member password'){
 await page.goto('/');await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码',{exact:true}).fill(password);await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
}

test('phone recovery scrubs the code and completes without storing upstream secrets',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const path=await requestLink(page),code=new URL('http://fixture'+path).searchParams.get('code');const seen=[];
 page.on('request',r=>seen.push({url:r.url(),kind:r.resourceType(),referer:r.headers().referer||''}));await enterLink(page,path);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('recovery-phone-password-form.png'),fullPage:true,animations:'disabled'});
 const leaks=seen.filter(r=>r.kind!=='document'&&(r.url.includes(code)||r.referer.includes(code))).map(r=>({path:new URL(r.url).pathname,kind:r.kind,urlContainsCode:r.url.includes(code),referrerContainsCode:r.referer.includes(code)}));
 await info.attach('recovery-request-check',{body:JSON.stringify({nonDocumentRequests:seen.filter(r=>r.kind!=='document').length,leaks}),contentType:'application/json'});expect(leaks).toEqual([]);
 await change(page,'offline changed browser password');await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();await page.screenshot({path:info.outputPath('recovery-phone-complete.png'),fullPage:true,animations:'disabled'});
 const storage=await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage,cookie:document.cookie}));for(const secret of [code,'offline changed browser password','offline-recovery-access','code_verifier'])expect(storage).not.toContain(secret);
 await page.getByRole('button',{name:'返回登录'}).click();await login(page,'offline changed browser password');
});

test('unknown email gets the same generic request confirmation',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'忘记密码',exact:true}).click();await page.getByLabel('账号邮箱').fill('unknown@example.test');const sent=page.waitForResponse(r=>r.url().endsWith('/v1/account/recovery/start'));
 await page.getByRole('button',{name:'发送恢复链接',exact:true}).click();expect((await sent).status()).toBe(202);await expect(page.getByRole('status')).toContainText('如果该邮箱可以找回账号');await expect(page.locator('body')).not.toContainText('账号不存在');await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);
});

test('a link cannot be consumed by another browser and cannot be reused',async({page,browser})=>{
 const path=await requestLink(page);const context=await browser.newContext();const other=await context.newPage();
 try{await other.goto('http://127.0.0.1:5173'+path);await expect(other.getByRole('alert')).toContainText('恢复验证暂未完成');await expect(other.getByLabel('新密码',{exact:true})).toHaveCount(0);expect(new URL(other.url()).search).toBe('');await other.getByRole('button',{name:'检查恢复状态'}).click();await expect(other.getByRole('button',{name:'重新申请链接'})).toBeVisible();
  await enterLink(page,path);await change(page,'offline replay-safe password');await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();await page.goto(path);await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新申请链接'})).toBeVisible();
 }finally{await context.close()}
});

test('expired recovery stays closed and offers a clear restart',async({page})=>{
 const path=await requestLink(page);await page.request.post('/v1/fixture/recovery-expire');await page.goto(path);await expect(page.getByRole('button',{name:'重新申请链接'})).toBeVisible();await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await page.getByRole('button',{name:'重新申请链接'}).click();await expect(page.getByLabel('账号邮箱')).toBeVisible();
});

test('a rejected password clears the fields and needs an explicit new attempt',async({page})=>{
 await enterLink(page,await requestLink(page));let updates=0;page.on('request',r=>{if(r.url().endsWith('/v1/account/recovery/complete'))updates++});
 await change(page,'weak-fixture browser password');await expect(page.getByRole('alert')).toContainText('密码未更新');await expect(page.getByLabel('新密码',{exact:true})).toHaveValue('');await expect(page.getByLabel('再次输入新密码',{exact:true})).toHaveValue('');expect(updates).toBe(1);
 await change(page,'offline stronger browser password');await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();expect(updates).toBe(2);
});

test('an uncertain password mutation never repeats or unlocks through a fresh link',async({page},info)=>{
 await enterLink(page,await requestLink(page));let updates=0;page.on('request',r=>{if(r.url().endsWith('/v1/account/recovery/complete'))updates++});
 await change(page,'uncertain-fixture browser password');await expect(page.getByRole('status')).toContainText('恢复暂时锁定');await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新申请链接'})).toHaveCount(0);expect(updates).toBe(1);
 await page.getByRole('button',{name:'检查恢复状态'}).click();await expect(page.getByRole('status')).toContainText('恢复暂时锁定');expect(updates).toBe(1);await expect(page.getByRole('button',{name:'检查恢复状态'})).toBeEnabled();await page.screenshot({path:info.outputPath('recovery-uncertain-locked.png'),fullPage:true,animations:'disabled'});
 // A second cookie can prove mailbox control; it still cannot bypass uncertainty.
 await page.context().clearCookies();const path=await requestLink(page);await page.goto(path);await expect(page.getByRole('status')).toContainText('恢复暂时锁定');await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);expect(updates).toBe(1);
});

test('password recovery revokes an already open account in another browser',async({page,browser})=>{
 const context=await browser.newContext();const other=await context.newPage();
 try{await other.goto('http://127.0.0.1:5173/');await other.getByLabel('用户邮箱').fill('a@example.test');await other.getByLabel('用户密码',{exact:true}).fill('offline member password');await other.getByRole('button',{name:'登录账号',exact:true}).click();await expect(other.getByLabel('消息',{exact:true})).toBeVisible();await other.getByLabel('消息',{exact:true}).fill('REVOKED_SESSION_DRAFT');
  await enterLink(page,await requestLink(page));await change(page,'offline revoke browser password');await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();await expect(other.getByLabel('用户邮箱')).toBeVisible({timeout:15000});await expect(other.getByLabel('消息',{exact:true})).toHaveCount(0);await expect(other.locator('body')).not.toContainText('REVOKED_SESSION_DRAFT');
 }finally{await context.close()}
});

for(const suffix of ['?code=invalid','?code=10000000-0000-4000-8000-000000000001&code=10000000-0000-4000-8000-000000000002','#error=synthetic'])test('malformed callback keeps its explanation '+suffix,async({page})=>{
 await page.goto('/account/recovery'+suffix);await expect(page.getByRole('alert')).toContainText('恢复链接无效，请重新申请');expect(new URL(page.url()).search+new URL(page.url()).hash).toBe('');await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);
});
