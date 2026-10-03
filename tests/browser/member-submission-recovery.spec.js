import {test,expect} from '@playwright/test';

// Synthetic route fixtures only: no real Auth, email, account or model requests.
async function fixture(page){
 const state={member:false,reads:0,posts:[]};
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;let body=[];
  if(request.method()==='POST')state.posts.push(path);
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,configuration:{configured:true,provider:'qwen',member_accounts:true}};
  else if(path==='/v1/account/status'){
   state.reads++;body={available:true,authenticated:state.member,account_scope:state.member?'member-submission-fixture':undefined,expires_at:Math.floor(Date.now()/1000)+3600,model_enabled:false,entitlements:{enabled:false,membership_required:true}};
  }else if(path==='/v1/account/login'){state.member=true;body={};}
  else if(path==='/v1/account/register')body={confirmation_required:true,message:'请检查邮箱完成确认后登录'};
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500',actor_charged_cost_cny:'0'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)}).catch(()=>{});
 });
 await page.goto('/');await expect(page.getByLabel('用户邮箱')).toBeVisible();
 await page.getByLabel('用户邮箱').fill('synthetic@example.test');await page.getByLabel('用户密码',{exact:true}).fill('synthetic offline password');
 return state;
}

for(const register of [false,true])test(`${register?'registration':'login'} repeated submission sends one request and resumes only after explicit retry`,async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const state=await fixture(page);
 if(register){await page.getByRole('button',{name:'没有账号，注册',exact:true}).click();await page.getByLabel('用户密码',{exact:true}).fill('synthetic offline password')}
 const path=register?'/v1/account/register':'/v1/account/login';let calls=0,pending,release;
 await page.route('**'+path,route=>{calls++;pending=route;return new Promise(resolve=>{release=resolve})});
 await page.locator('form').evaluate(form=>{form.requestSubmit();form.requestSubmit()});await expect.poll(()=>calls).toBe(1);
 await page.evaluate(()=>window.dispatchEvent(new Event('hcla-member-status-refresh')));
 await expect(page.getByLabel('用户密码',{exact:true})).toBeDisabled();expect(state.reads).toBe(1);
 await pending.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'offline temporary failure'})});release();
 await expect(page.getByRole('alert')).toContainText(register?'暂时无法创建账号':'登录未完成');
 await expect(page.getByLabel('用户邮箱')).toHaveValue('synthetic@example.test');await expect(page.getByLabel('用户密码',{exact:true})).toHaveValue('');
 await page.evaluate(()=>window.dispatchEvent(new Event('hcla-member-status-refresh')));await expect.poll(()=>state.reads).toBe(2);expect(calls).toBe(1);
 await page.screenshot({path:info.outputPath(register?'registration-explicit-retry-mobile.png':'login-explicit-retry-mobile.png'),fullPage:true,animations:'disabled'});
 await page.unroute('**'+path);await page.getByLabel('用户密码',{exact:true}).fill('new synthetic offline password');
 await page.getByRole('button',{name:register?'注册账号':'登录账号',exact:true}).click();
 if(register){await expect(page.getByRole('status')).toContainText('请检查邮箱');await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0)}
 else{await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled()}
 expect(state.posts).toEqual([path]);
});

test('slow pre-login status cannot delay a successful login or replace its account',async({page})=>{
 const state=await fixture(page);let pending,release;
 const stale=async route=>{pending=route;await new Promise(resolve=>{release=resolve});await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:true,authenticated:false})}).catch(()=>{})};
 await page.route('**/v1/account/status',stale);
 await page.evaluate(()=>window.dispatchEvent(new Event('hcla-member-status-refresh')));await expect.poll(()=>Boolean(pending)).toBe(true);
 await page.unroute('**/v1/account/status',stale);
 try{
  await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
  await page.getByLabel('消息',{exact:true}).fill('SYNTHETIC_POST_LOGIN_DRAFT');release();
  await expect(page.getByLabel('消息',{exact:true})).toHaveValue('SYNTHETIC_POST_LOGIN_DRAFT');expect(state.posts).toEqual(['/v1/account/login']);
 }finally{release()}
});

test('another tab supersedes a pending login and clears its credentials before a new attempt',async({page})=>{
 const state=await fixture(page);let pending,release;
 const held=async route=>{pending=route;await new Promise(resolve=>{release=resolve});await route.fulfill({status:200,contentType:'application/json',body:'{}'}).catch(()=>{})};
 await page.route('**/v1/account/login',held);await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect.poll(()=>Boolean(pending)).toBe(true);
 await page.evaluate(()=>{const channel=new BroadcastChannel('hcla-member-session');channel.postMessage({type:'signed-out'});channel.close()});
 await expect(page.getByLabel('用户密码',{exact:true})).toHaveValue('');await expect(page.getByLabel('用户密码',{exact:true})).toBeEnabled();
 await page.unroute('**/v1/account/login',held);await page.getByLabel('用户密码',{exact:true}).fill('new synthetic offline password');
 await page.getByRole('button',{name:'登录账号',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 release();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();expect(state.posts).toEqual(['/v1/account/login']);
});
