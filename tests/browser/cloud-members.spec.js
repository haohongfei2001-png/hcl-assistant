import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
const expectedScope=user=>'member-'+createHash('sha256').update('https://abcdefghijklmnopqrst.supabase.co/auth/v1\n10000000-0000-4000-8000-00000000000'+(user==='a'?'1':'2')).digest('hex');
test.skip(!process.env.HCLA_TEST_POSTGRES_DSN,'Disposable Postgres + injected auth only');
test.beforeEach(async({request})=>{await request.post('/v1/fixture/member-mode')});
async function enter(page,user='a'){
 await page.goto('/');await page.getByLabel('用户邮箱').fill(user+'@example.test');await page.getByLabel('用户密码').fill('offline member password');
 const accepted=page.waitForResponse(r=>r.url().endsWith('/v1/account/login'));await page.getByRole('button',{name:'登录账号',exact:true}).click();expect((await accepted).status()).toBe(200);
 await expect(page.getByLabel('消息',{exact:true})).toBeVisible();const identity=await browserRead(page,'/v1/account/status');expect(identity.status).toBe(200);expect(identity.body.authenticated).toBe(true);expect(identity.body.account_scope).toBe(expectedScope(user));
 await page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度').check();
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
 await page.screenshot({path:info.outputPath('member-confirmation-entry.png'),fullPage:true,animations:'disabled'});
});

test('ordinary account entry remains usable on a narrow phone screen',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByLabel('用户邮箱')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath('member-mobile-entry.png'),fullPage:true,animations:'disabled'});
 await expect(page.getByLabel('用户密码',{exact:true})).toHaveAttribute('type','password');await page.getByRole('button',{name:'显示密码',exact:true}).click();await expect(page.getByLabel('用户密码',{exact:true})).toHaveAttribute('type','text');await page.getByRole('button',{name:'隐藏密码',exact:true}).click();
 await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码').fill('offline member password');await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 expect((await browserRead(page,'/v1/account/status')).body.account_scope).toBe(expectedScope('a'));
});

test('account connection failure has an explicit retry and preserves entered email',async({page},info)=>{
 await page.route('**/v1/account/status',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected account outage'})}));
 await page.goto('/');await expect(page.getByRole('button',{name:'重新检查连接'})).toBeVisible();await expect(page.getByRole('alert')).toContainText('连接不上账号服务');
 await expect(page.getByRole('button',{name:'没有账号，注册'})).toHaveCount(0);await page.screenshot({path:info.outputPath('member-connection-retry.png'),fullPage:true,animations:'disabled'});
 await page.unroute('**/v1/account/status');await page.getByRole('button',{name:'重新检查连接'}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);
 await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码').fill('incorrect password fixture');await page.getByRole('button',{name:'登录账号',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('登录未完成');await expect(page.getByLabel('用户邮箱')).toHaveValue('a@example.test');await expect(page.getByLabel('用户密码')).toHaveValue('');
});

test('a stalled sign-in is bounded and is never automatically repeated',async({page})=>{
 await page.goto('/');await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码').fill('offline member password');
 let release;const held=new Promise(resolve=>release=resolve);let calls=0;
 await page.route('**/v1/account/login',async route=>{calls++;await held;await route.abort().catch(()=>{})});
 try{await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByRole('button',{name:'正在处理…',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('连接等待过久',{timeout:17000});expect(calls).toBe(1);await expect(page.getByLabel('用户邮箱')).toHaveValue('a@example.test');await expect(page.getByLabel('用户密码')).toHaveValue('');
 }finally{release();await page.unroute('**/v1/account/login')}
 await page.getByLabel('用户密码').fill('offline member password');await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
});

test('first member message needs no Settings visit and cannot bypass inline consent',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByLabel('用户邮箱').fill('a@example.test');await page.getByLabel('用户密码').fill('offline member password');await page.getByRole('button',{name:'登录账号',exact:true}).click();
 await page.getByLabel('消息',{exact:true}).fill('原创合成：FIRST_MESSAGE_PHONE');let events=0;page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.endsWith('/events'))events++});
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();await page.getByLabel('消息',{exact:true}).press('Enter');expect(events).toBe(0);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('原创合成：FIRST_MESSAGE_PHONE');
 const consent=page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度');await expect(consent).toBeVisible();await consent.check();await expect(page.getByRole('button',{name:'发送',exact:true})).toBeEnabled();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('member-mobile-first-message.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('.assistant-message').last()).toContainText('原创离线自然语言');expect(events).toBe(1);
});

test('unavailable model keeps a member draft and never sends a paid request',async({page})=>{
 await page.route('**/v1/account/status',async route=>{const response=await route.fetch();const status=await response.json();await route.fulfill({response,json:{...status,model_enabled:false}})});
 await enter(page);await page.getByLabel('消息',{exact:true}).fill('UNAVAILABLE_MODEL_DRAFT');let mutations=0;
 page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.startsWith('/v1/member/'))mutations++});
 await expect(page.getByRole('alert')).toContainText('模型服务暂未开放');await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();await page.getByLabel('消息',{exact:true}).press('Enter');
 expect(mutations).toBe(0);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('UNAVAILABLE_MODEL_DRAFT');
});

test('history outage stays distinct from an empty account and read-only retry keeps the draft',async({page},info)=>{
 const uncaught=[];page.on('pageerror',error=>uncaught.push(error.message));
 await page.route('**/v1/member/conversations',route=>route.request().method()==='GET'?route.fulfill({status:503,contentType:'text/html',body:'Injected unavailable history'}):route.continue());
 await enter(page);await page.getByLabel('消息',{exact:true}).fill('HISTORY_RECOVERY_DRAFT');
 await expect(page.getByRole('navigation',{name:'对话历史'})).toContainText('对话列表暂不可用');await expect(page.getByText('还没有对话',{exact:true})).toHaveCount(0);await expect(page.getByRole('alert')).toContainText('暂时无法加载对话列表');
 await page.screenshot({path:info.outputPath('member-history-retry.png'),fullPage:true,animations:'disabled'});
 let mutations=0;page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.startsWith('/v1/member/'))mutations++});
 await page.unroute('**/v1/member/conversations');await page.getByRole('button',{name:'重新加载对话'}).click();await expect(page.getByText('还没有对话',{exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);
 await expect(page.getByLabel('消息',{exact:true})).toHaveValue('HISTORY_RECOVERY_DRAFT');expect(mutations).toBe(0);expect(uncaught).toEqual([]);
});

test('an accepted new conversation is retained when its list refresh fails',async({page})=>{
 await enter(page);let creates=0,events=0;
 await page.route('**/v1/member/conversations',route=>{if(route.request().method()==='POST'){creates++;return route.continue()}return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected post-create list failure'})})});
 page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname.endsWith('/events'))events++});
 await send(page,'原创合成：ACCEPTED_CONVERSATION_ONCE');await expect(page.getByRole('alert')).toContainText('暂时无法加载对话列表');expect(creates).toBe(1);expect(events).toBe(1);
 const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');expect(id).toBeTruthy();
 await page.unroute('**/v1/member/conversations');await page.getByRole('button',{name:'重新加载对话'}).click();await expect(page.locator('[data-conversation="'+id+'"]')).toBeVisible();
 await expect(page.locator('.messages')).toContainText('ACCEPTED_CONVERSATION_ONCE');expect(creates).toBe(1);expect(events).toBe(1);
});

test('a failed history list cancels its still-pending companion read',async({page})=>{
 await page.addInitScript(()=>{window.__historyTopicAborts=0;window.__historyTopicSettled=0;const original=window.fetch.bind(window);window.fetch=(input,options)=>{const topic=String(input).endsWith('/v1/member/topics');if(topic)options?.signal?.addEventListener('abort',()=>window.__historyTopicAborts++,{once:true});const result=original(input,options);if(topic)result.then(()=>window.__historyTopicSettled++,()=>window.__historyTopicSettled++);return result}});
 let started;const topicStarted=new Promise(resolve=>started=resolve);let release;const held=new Promise(resolve=>release=resolve);
 await page.route('**/v1/member/topics',async route=>{started();await held;await route.abort().catch(()=>{})});
 await page.route('**/v1/member/conversations',async route=>{await topicStarted;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected one-sided history failure'})})});
 try{await enter(page);await expect(page.getByRole('button',{name:'重新加载对话'})).toBeEnabled();await expect.poll(()=>page.evaluate(()=>window.__historyTopicAborts)).toBe(1);await expect.poll(()=>page.evaluate(()=>window.__historyTopicSettled)).toBe(1)}
 finally{release();await page.unroute('**/v1/member/topics');await page.unroute('**/v1/member/conversations')}
});

test('two member browsers have separate history and cannot use owner routes',async({page,browser},info)=>{
 const paths=[];page.on('request',r=>paths.push(new URL(r.url()).pathname));await enter(page);await send(page,'原创合成：MEMBER_A_PRIVATE_CANARY');
 const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 expect((await page.request.get('/v1/conversations')).status()).toBe(401);expect(paths.filter(p=>p==='/v1/conversations'||p==='/v1/topics'||p==='/v1/history/search')).toEqual([]);
 const other=await browser.newContext();const b=await other.newPage();await b.goto('http://127.0.0.1:5173/');await b.getByLabel('用户邮箱').fill('b@example.test');await b.getByLabel('用户密码').fill('offline member password');await b.getByRole('button',{name:'登录账号',exact:true}).click();await expect(b.getByLabel('消息',{exact:true})).toBeVisible();
 await expect(b.locator('body')).not.toContainText('MEMBER_A_PRIVATE_CANARY');const identity=await browserRead(b,'/v1/account/status');expect(identity.status).toBe(200);expect(identity.body.authenticated).toBe(true);expect(identity.body.account_scope).toBe(expectedScope('b'));expect((await browserRead(b,'/v1/member/conversations/'+id)).status).toBe(403);
 await page.screenshot({path:info.outputPath('member-shared-chat.png'),fullPage:true,animations:'disabled'});await other.close();
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
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByRole('dialog',{name:'设置'})).toContainText('退出未完成');await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.getByRole('alert')).toContainText('退出未完成');
 await page.request.post('/v1/fixture/member-expire');await expect(page.getByLabel('用户邮箱')).toBeVisible({timeout:15000});await expect(page.locator('body')).not.toContainText('EXPIRY_MEMBER_CANARY');
});

test('accepted logout cancels an older status snapshot and never restores the previous account UI',async({page},info)=>{
 await page.addInitScript(()=>{window.__logoutStatusAborts=0;window.__logoutStatusSettled=0;window.__trackLogoutStatus=false;const original=window.fetch.bind(window);window.fetch=(input,options)=>{const track=window.__trackLogoutStatus&&String(input).endsWith('/v1/account/status');if(track)options?.signal?.addEventListener('abort',()=>window.__logoutStatusAborts++,{once:true});const result=original(input,options);if(track)result.then(()=>window.__logoutStatusSettled++,()=>window.__logoutStatusSettled++);return result}});
 await enter(page);await send(page,'原创合成：LOGOUT_OLD_ACCOUNT_CANARY');
 let releaseLogout,releaseStatus,captured,released;const logoutHold=new Promise(resolve=>releaseLogout=resolve),statusHold=new Promise(resolve=>releaseStatus=resolve),statusCaptured=new Promise(resolve=>captured=resolve),statusReleased=new Promise(resolve=>released=resolve);let writes=0;
 await page.route('**/v1/account/logout',async route=>{writes++;await logoutHold;await route.continue()});
 await page.route('**/v1/account/status',async route=>{const response=await route.fetch();captured();await statusHold;await route.fulfill({response}).catch(()=>{});released()});
 try{
  await page.evaluate(()=>window.__trackLogoutStatus=true);await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();
  await statusCaptured;releaseLogout();await expect(page.getByLabel('用户邮箱')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>window.__logoutStatusAborts)).toBe(1);await expect.poll(()=>page.evaluate(()=>window.__logoutStatusSettled)).toBe(1);
  releaseStatus();await statusReleased;await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.locator('body')).not.toContainText('LOGOUT_OLD_ACCOUNT_CANARY');expect(writes).toBe(1);
  await page.screenshot({path:info.outputPath('member-confirmed-logout.png'),fullPage:true,animations:'disabled'});
 }finally{releaseLogout();releaseStatus();await page.unroute('**/v1/account/logout');await page.unroute('**/v1/account/status')}
});

test('failed logout remains visible after a healthy poll and only an explicit retry submits again',async({page},info)=>{
 await enter(page);let writes=0;
 await page.route('**/v1/account/logout',route=>{writes++;return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Injected logout outage'})})});
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'退出登录',exact:true}).click();
 await expect(page.getByRole('dialog',{name:'设置'})).toContainText('退出未完成');
 await page.waitForResponse(response=>response.url().endsWith('/v1/account/status')&&response.status()===200,{timeout:15000});
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 await expect(page.getByRole('dialog',{name:'设置'})).toContainText('退出未完成');expect(writes).toBe(1);
 await page.screenshot({path:info.outputPath('member-logout-retry-after-poll.png'),fullPage:true,animations:'disabled'});
 await page.unroute('**/v1/account/logout');await page.route('**/v1/account/logout',route=>{writes++;return route.continue()});
 await page.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible();expect(writes).toBe(2);
});

test('a stalled member logout times out, keeps the draft and permits retry',async({page})=>{
 await enter(page);await page.getByLabel('消息',{exact:true}).fill('LOGOUT_RETRY_DRAFT');await page.getByRole('button',{name:'设置',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'设置'});let release;const held=new Promise(resolve=>release=resolve);
 await page.route('**/v1/account/logout',async route=>{await held;await route.abort().catch(()=>{})});
 try{
  await dialog.getByRole('button',{name:'退出登录',exact:true}).click();await expect(dialog.getByRole('button',{name:'正在退出…',exact:true})).toBeDisabled();
  await expect(dialog).toContainText('退出未完成，请重试',{timeout:17000});await expect(dialog.getByRole('button',{name:'退出登录',exact:true})).toBeEnabled();
  await expect(page.getByLabel('消息',{exact:true})).toHaveValue('LOGOUT_RETRY_DRAFT');
 }finally{release();await page.unroute('**/v1/account/logout')}
 await dialog.getByRole('button',{name:'退出登录',exact:true}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.locator('body')).not.toContainText('LOGOUT_RETRY_DRAFT');
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

test('logout unmount aborts a held selected-history read without returning the old account body',async({page})=>{
 await page.addInitScript(()=>{window.__selectedMemberAborts=0;const original=window.fetch.bind(window);window.fetch=(input,options)=>{if(/\/v1\/member\/conversations\/[^/?]+$/.test(String(input)))options?.signal?.addEventListener('abort',()=>window.__selectedMemberAborts++,{once:true});return original(input,options)}});
 await enter(page);await send(page,'原创合成：LOGOUT_HELD_HISTORY_BODY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeFocused();await page.evaluate(()=>window.__selectedMemberAborts=0);let entered,release;const waiting=new Promise(resolve=>entered=resolve),gate=new Promise(resolve=>release=resolve);
 await page.route(`**/v1/member/conversations/${id}`,async route=>{const response=await route.fetch();entered();await gate;await route.fulfill({response}).catch(()=>{})});
 try{await page.locator(`[data-conversation="${id}"]`).click();await waiting;await logout(page);await expect.poll(()=>page.evaluate(()=>window.__selectedMemberAborts)).toBe(1);release();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.locator('body')).not.toContainText('LOGOUT_HELD_HISTORY_BODY');await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0)}finally{release()}
});
