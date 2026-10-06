import {test,expect} from '@playwright/test';

const pages='http://127.0.0.1:4174/';
async function capture(page,info,name){
 await page.evaluate(()=>document.fonts.ready);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:info.outputPath(name+'.png'),fullPage:true,animations:'disabled'});
}

test('shared consumer Home, chat, settings and memory render at desktop and phone widths',async({page},info)=>{
 let networkWrites=0;page.on('request',r=>{if(r.method()!=='GET')networkWrites++});
 await page.setViewportSize({width:1440,height:1000});await page.goto(pages);
 await expect(page.getByRole('heading',{name:'有什么需要帮忙的？',exact:true})).toBeVisible();
 await expect(page.getByRole('list',{name:'可以从这里开始'}).getByRole('button')).toHaveCount(3);
 expect(await page.locator('.continuum-shell').evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(244, 245, 248)');
 expect(await page.locator('.chat-workspace').evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(255, 255, 255)');
 await capture(page,info,'consumer-home-desktop');
 const input=page.getByLabel('消息',{exact:true});await input.fill('2+2');await capture(page,info,'consumer-composer-focus');
 await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('.assistant-message')).toContainText('4');
 await capture(page,info,'consumer-conversation-desktop');
 await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByRole('dialog',{name:'设置',exact:true})).toBeVisible();await capture(page,info,'consumer-settings-desktop');
 await page.getByRole('button',{name:'关闭设置',exact:true}).click();await page.getByRole('button',{name:'记忆管理',exact:true}).click();await expect(page.getByRole('dialog',{name:'记忆管理',exact:true})).toBeVisible();await capture(page,info,'consumer-memory-desktop');
 await page.getByRole('button',{name:'关闭记忆管理',exact:true}).click();await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.locator('.home-stage')).toBeVisible();
 await page.setViewportSize({width:390,height:844});if(await page.locator('.nav-scrim').isVisible())await page.getByRole('button',{name:'关闭侧栏',exact:true}).click();
 await capture(page,info,'consumer-home-phone');
 await page.setViewportSize({width:320,height:844});await capture(page,info,'consumer-home-small-phone');
 expect(networkWrites).toBe(0);
});

async function accountFixture(page,member=false){
 const writes=[];
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;if(request.method()!=='GET')writes.push(path);
  let body=[];
  if(path==='/v1/development/status')body={enabled:true,cloud:true,authenticated:false,configuration:{configured:true,provider:'qwen',member_accounts:true}};
  else if(path==='/v1/account/status')body={available:true,recovery_available:true,authenticated:member,account_scope:member?'consumer-visual-synthetic':undefined,expires_at:Math.floor(Date.now()/1000)+3600,model_enabled:false,entitlements:{enabled:false,membership_required:true}};
  else if(path==='/v1/account/recovery/status')body={available:true,ready:false};
  else if(path==='/v1/member/billing/catalog')body={available:false,plans:[],reason:'会员购买尚未开放；注册不会自动开通会员'};
  else if(path==='/v1/member/billing/orders')body={available:false,orders:[]};
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500',actor_charged_cost_cny:'0'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 return writes;
}

test('ordinary account, registration and recovery share the consumer surfaces without submitting credentials',async({page},info)=>{
 const writes=await accountFixture(page);await page.setViewportSize({width:1440,height:1000});await page.goto('/');
 await expect(page.getByLabel('用户邮箱',{exact:true})).toBeVisible();
 expect(await page.locator('.account-screen').evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(244, 245, 248)');
 await capture(page,info,'consumer-login-desktop');
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'没有账号，注册',exact:true}).click();await expect(page.getByRole('heading',{name:'创建你的账号'})).toBeVisible();await capture(page,info,'consumer-registration-phone');
 await page.getByRole('button',{name:'已有账号，返回登录',exact:true}).click();await page.getByRole('button',{name:'忘记密码',exact:true}).click();await expect(page.getByLabel('账号邮箱',{exact:true})).toBeVisible();await capture(page,info,'consumer-recovery-phone');
 expect(writes).toEqual([]);
});

test('closed membership and order surfaces remain truthful in the consumer presentation',async({page},info)=>{
 const writes=await accountFixture(page,true);await page.setViewportSize({width:1440,height:1000});await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'会员与订单',exact:true}).click();await page.getByRole('button',{name:'查看购买与订单',exact:true}).click();
 await expect(page.getByRole('region',{name:'会员购买与订单'})).toContainText('会员购买尚未开放');await expect(page.getByRole('region',{name:'会员状态'})).toContainText('会员未开通');await capture(page,info,'consumer-membership-desktop');
 await page.setViewportSize({width:390,height:844});await capture(page,info,'consumer-membership-phone');
 await expect(page.getByRole('button',{name:'创建订单并准备支付'})).toHaveCount(0);expect(writes).toEqual([]);
});
