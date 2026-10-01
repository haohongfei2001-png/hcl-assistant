import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
const expectedScope=user=>'member-'+createHash('sha256').update('https://abcdefghijklmnopqrst.supabase.co/auth/v1\n10000000-0000-4000-8000-00000000000'+(user==='a'?'1':'2')).digest('hex');
test.skip(!process.env.HCLA_TEST_POSTGRES_DSN,'Disposable Postgres + injected auth only');
test.beforeEach(async({request})=>{await request.post('/v1/fixture/member-mode')});
async function enter(page,user='a'){
 await page.goto('/');await page.getByLabel('用户邮箱').fill(user+'@example.test');await page.getByLabel('用户密码').fill('offline member password');
 const accepted=page.waitForResponse(r=>r.url().endsWith('/v1/account/login'));await page.getByRole('button',{name:'登录账号',exact:true}).click();expect((await accepted).status()).toBe(200);
 await expect(page.getByLabel('消息',{exact:true})).toBeVisible();const identity=await browserRead(page,'/v1/account/status');expect(identity.status).toBe(200);expect(identity.body.authenticated).toBe(true);expect(identity.body.account_scope).toBe(expectedScope(user));
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByLabel('本次仅使用原创合成输入，并使用服务器已批准额度').check();await page.getByRole('button',{name:'关闭设置'}).click();
}
async function send(page,text){await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('.assistant-message').last()).toContainText('原创离线自然语言');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0)}
async function logout(page){await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible()}
// Chromium accepts Secure cookies on this trustworthy loopback fixture; the
// separate APIRequestContext follows HTTP cookie policy. Check signed-in access
// with the same browser transport the product uses, retaining Secure cookies.
async function browserRead(page,path){return page.evaluate(async value=>{const response=await fetch(value);return {status:response.status,body:await response.json()}},path)}

test('registration requires confirmation and exposes no server credential',async({page},info)=>{
 await page.goto('/');await page.getByRole('button',{name:'没有账号，注册'}).click();await page.getByLabel('用户邮箱').fill('new@example.test');await page.getByLabel('用户密码').fill('offline member password');await page.getByRole('button',{name:'注册账号',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('邮箱');await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0);await expect(page.getByLabel('用户密码')).toHaveValue('');
 expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage,cookie:document.cookie}))).not.toContain('offline member password');
 await page.screenshot({path:info.outputPath('member-confirmation-entry.png'),fullPage:true});
});

test('ordinary account entry remains usable on a narrow phone screen',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByLabel('用户邮箱')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath('member-mobile-entry.png'),fullPage:true});
 await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码').fill('offline member password');await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 expect((await browserRead(page,'/v1/account/status')).body.account_scope).toBe(expectedScope('a'));
});

test('two member browsers have separate history and cannot use owner routes',async({page,browser},info)=>{
 const paths=[];page.on('request',r=>paths.push(new URL(r.url()).pathname));await enter(page);await send(page,'原创合成：MEMBER_A_PRIVATE_CANARY');
 const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 expect((await page.request.get('/v1/conversations')).status()).toBe(401);expect(paths.filter(p=>p==='/v1/conversations'||p==='/v1/topics'||p==='/v1/history/search')).toEqual([]);
 const other=await browser.newContext();const b=await other.newPage();await b.goto('http://127.0.0.1:5173/');await b.getByLabel('用户邮箱').fill('b@example.test');await b.getByLabel('用户密码').fill('offline member password');await b.getByRole('button',{name:'登录账号',exact:true}).click();await expect(b.getByLabel('消息',{exact:true})).toBeVisible();
 await expect(b.locator('body')).not.toContainText('MEMBER_A_PRIVATE_CANARY');const identity=await browserRead(b,'/v1/account/status');expect(identity.status).toBe(200);expect(identity.body.authenticated).toBe(true);expect(identity.body.account_scope).toBe(expectedScope('b'));expect((await browserRead(b,'/v1/member/conversations/'+id)).status).toBe(403);
 await page.screenshot({path:info.outputPath('member-shared-chat.png'),fullPage:true});await other.close();
});

test('logout and account switch clear drafts and previous account UI',async({page})=>{
 await enter(page);await send(page,'原创合成：OLD_MEMBER_BODY');await page.getByLabel('消息',{exact:true}).fill('OLD_MEMBER_DRAFT');await logout(page);await enter(page,'b');
 await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await expect(page.locator('body')).not.toContainText('OLD_MEMBER_BODY');
 expect((await browserRead(page,'/v1/account/status')).body.account_scope).toBe(expectedScope('b'));const histories=await browserRead(page,'/v1/member/conversations');expect(histories.status).toBe(200);expect(histories.body).toEqual([]);
});

test('automatic renewal keeps the current temporary packet without asking for login',async({page})=>{
 await enter(page);await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByLabel('记忆范围').selectOption('TEMPORARY');await page.getByRole('button',{name:'关闭设置'}).click();await send(page,'原创合成：RENEWAL_TEMP_CANARY');
 await page.getByLabel('消息',{exact:true}).fill('RENEWAL_DRAFT');await page.request.post('/v1/fixture/member-renew');
 const renewed=await page.waitForResponse(r=>r.url().endsWith('/v1/account/refresh'),{timeout:15000});expect(renewed.status()).toBe(200);
 await expect(page.getByLabel('消息',{exact:true})).toHaveValue('RENEWAL_DRAFT');await expect(page.locator('.messages')).toContainText('RENEWAL_TEMP_CANARY');
 expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage,cookie:document.cookie}))).not.toContain('offline-refresh');
});

test('absolute expiry clears temporary content and failed logout is visible',async({page})=>{
 await enter(page);await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByLabel('记忆范围').selectOption('TEMPORARY');await page.getByRole('button',{name:'关闭设置'}).click();await send(page,'原创合成：EXPIRY_MEMBER_CANARY');
 await page.route('**/v1/account/logout',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected temporary failure'})}));
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.getByRole('alert')).toContainText('退出未完成');
 await page.request.post('/v1/fixture/member-expire');await expect(page.getByLabel('用户邮箱')).toBeVisible({timeout:15000});await expect(page.locator('body')).not.toContainText('EXPIRY_MEMBER_CANARY');
});

test('an export response accepted before logout cannot download after account teardown',async({page})=>{
 await enter(page);await send(page,'原创合成：DELAYED_EXPORT_MEMBER_CANARY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 const downloads=[];page.on('download',value=>downloads.push(value));let release;const held=new Promise(resolve=>release=resolve);let intercepted;const started=new Promise(resolve=>intercepted=resolve);
 await page.route('**/v1/member/conversations/'+id,async route=>{const response=await route.fetch();intercepted();await held;await route.fulfill({response})});
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'导出当前会话'}).click();await started;await logout(page);
 const completed=page.waitForResponse(r=>r.url().endsWith('/v1/member/conversations/'+id));release();await (await completed).finished();
 await page.waitForTimeout(500);expect(downloads).toHaveLength(0);await expect(page.locator('body')).not.toContainText('DELAYED_EXPORT_MEMBER_CANARY');
});

test('status polling is serialized so old authentication cannot overwrite a newer result',async({page})=>{
 await enter(page);let release;const held=new Promise(resolve=>release=resolve);let count=0;let started;const intercepted=new Promise(resolve=>started=resolve);
 await page.route('**/v1/account/status',async route=>{count++;started();await held;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:true,authenticated:false,renewable:false})})});
 await page.evaluate(()=>{const channel=new BroadcastChannel('hcla-member-session');channel.postMessage({type:'status-change'});channel.close()});await intercepted;
 // A real interval fires while this read is blocked; it must share the one read.
 await page.waitForTimeout(10500);expect(count).toBe(1);release();await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0);
});
