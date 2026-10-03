import {test,expect} from '@playwright/test';

async function fixture(page,{unknown=false,closed=false,now=Date.now(),quoteSeconds=3600}={}){
 let paid=false,serverNow=now;const created=[],checkout=[],queries=[],expiry=Math.floor(now/1000)+3600;let orders=[];
 const offer={plan_id:'offline-fixture',version:1,title:'离线会员套餐',amount_minor:990,currency:'CNY',duration_days:30,max_requests:20,max_cost_cny:'25',temporary:true,persistent:true,terms_digest:'a'.repeat(64),shared_capacity_limited:true,renewal_mode:'USER_INITIATED_FIXED_DURATION',usage_period:'ASIA_SHANGHAI_CALENDAR_MONTH'};
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;let body=[];
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,configuration:{configured:true,provider:'qwen',member_accounts:true}};
  else if(path==='/v1/account/status')body={available:true,authenticated:true,account_scope:'member-commerce-fixture',expires_at:expiry,model_enabled:paid,entitlements:{enabled:paid,membership_required:true,temporary:paid,persistent:paid,expires_at:expiry,access_kind:paid?'PAID_MEMBERSHIP':undefined}};
  else if(path==='/v1/member/billing/catalog')body={available:!closed,plans:closed?[]:[offer],reason:closed?'会员购买尚未开放；注册不会自动开通会员':undefined};
  else if(path==='/v1/member/billing/orders'&&request.method()==='POST'){
   created.push(request.postDataJSON());const order={order_id:'offline-order-'+created.length,plan_id:offer.plan_id,plan_version:1,amount_minor:990,currency:'CNY',duration_days:30,state:'PENDING',verification_state:'NOT_QUERIED',created_at:Math.floor(serverNow/1000),expires_at:Math.floor(serverNow/1000)+quoteSeconds};orders=[order,...orders];body=order;
  }else if(path==='/v1/member/billing/orders')body={available:!closed,orders};
  else if(/^\/v1\/member\/billing\/orders\/offline-order-\d+\/checkout$/.test(path)){
   const id=path.split('/').at(-2);checkout.push(request.postDataJSON());orders=orders.map(order=>order.order_id===id?{...order,state:unknown?'UNCERTAIN':'CHECKOUT_READY'}:order);
   if(unknown){await route.abort('failed');return;}body={checkout_url:'https://checkout.example.test/'+id};
  }else if(/^\/v1\/member\/billing\/orders\/offline-order-\d+\/reconcile$/.test(path)){
   const id=path.split('/').at(-2);queries.push(request.postDataJSON());paid=!unknown;orders=orders.map(order=>order.order_id===id?{...order,state:paid?'FULFILLED':'UNCERTAIN',verification_state:paid?'VERIFIED':'VERIFIED_PENDING',...(paid?{access_starts_at:expiry-100,access_expires_at:expiry+86400*30,access_enabled:true}:{})}:order);body=orders.find(order=>order.order_id===id);
  }else if(/^\/v1\/member\/billing\/orders\/offline-order-\d+$/.test(path))body=orders.find(order=>order.order_id===path.split('/').at(-1));
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500',actor_charged_cost_cny:'0'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await page.getByLabel('消息',{exact:true}).fill('SYNTHETIC_DRAFT_RETAINS_AFTER_BILLING');
 await page.getByRole('button',{name:'会员与订单',exact:true}).click();await page.getByRole('button',{name:'查看购买与订单',exact:true}).click();
 return {created,checkout,queries,offer,advanceServer:milliseconds=>{serverNow+=milliseconds}};
}

test('consumer explicitly prepares one bound order and server-confirmed membership preserves chat draft',async({page},info)=>{
 const state=await fixture(page);const button=page.getByRole('button',{name:'创建订单并准备支付',exact:true});await expect(button).toBeDisabled();
 await page.getByLabel(/我已核对 离线会员套餐/).check();await button.evaluate(node=>{node.click();node.click()});
 const link=page.getByRole('link',{name:'在支付服务打开订单',exact:true});await expect(link).toHaveAttribute('href','https://checkout.example.test/offline-order-1');
 expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(0);
 expect(Object.keys(state.created[0]).sort()).toEqual(['idempotency_key','plan_id','terms_digest','version']);expect(state.created[0].terms_digest).toBe(state.offer.terms_digest);
 await expect(page.getByRole('region',{name:'会员状态',exact:true})).toContainText('会员未开通');
 await page.screenshot({path:info.outputPath('membership-order-ready-desktop.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'核验此订单付款',exact:true}).click();await expect(page.getByRole('region',{name:'会员状态',exact:true})).toContainText('会员有效');
 expect(state.queries).toEqual([{}]);await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('本订单权益：');
 await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('SYNTHETIC_DRAFT_RETAINS_AFTER_BILLING');
});

test('uncertain checkout remains query-only and cannot unlock a member from a browser claim',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const state=await fixture(page,{unknown:true});await page.getByLabel(/我已核对 离线会员套餐/).check();await page.getByRole('button',{name:'创建订单并准备支付',exact:true}).click();
 await expect(page.getByRole('region',{name:'会员购买与订单',exact:true}).getByRole('alert')).toContainText('勿重复付款');
 await page.getByRole('button',{name:'重新读取套餐与订单',exact:true}).click();await expect(page.getByRole('button',{name:'核验此订单付款',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'准备或打开此订单支付页',exact:true})).toHaveCount(0);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(0);
 await page.getByRole('button',{name:'核验此订单付款',exact:true}).click();await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('付款尚未完成');
 await expect(page.getByRole('region',{name:'会员状态',exact:true})).toContainText('会员未开通');expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(1);
 await page.screenshot({path:info.outputPath('membership-order-uncertain-mobile.png'),fullPage:true,animations:'disabled'});
});

test('unconfigured billing displays no offers and never dispatches a payment operation',async({page})=>{
 const state=await fixture(page,{closed:true});await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('会员购买尚未开放');
 await expect(page.getByRole('button',{name:'创建订单并准备支付'})).toHaveCount(0);expect(state.created).toHaveLength(0);expect(state.checkout).toHaveLength(0);expect(state.queries).toHaveLength(0);
});

test('expired guest offer does not obscure ordinary registration or revive trial authority',async({page},info)=>{
 let starts=0;
 await page.route('**/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname;let body={};
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,configuration:{configured:true,temporary_trial:true,member_accounts:true}};
  if(path==='/v1/trial/status')body={available:false,authenticated:false,expires_at:1};
  if(path==='/v1/account/status')body={available:true,authenticated:false};
  if(path==='/v1/trial/start')starts++;
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.getByRole('heading',{name:'继续你的对话',exact:true})).toBeVisible();
 await expect(page.getByLabel('用户邮箱',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'临时试用',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'试用尚未开始或已结束',exact:true})).toHaveCount(0);expect(starts).toBe(0);
 await page.screenshot({path:info.outputPath('ordinary-entry-with-expired-trial-mobile.png'),fullPage:true,animations:'disabled'});
});


test('an unreadable order history refuses new purchase even when an offer loads',async({page})=>{
 const state=await fixture(page);
 // This later route supersedes the generic fixture for an interrupted reload.
 await page.route('**/v1/member/billing/orders',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'offline read failure'})}));
 await page.getByRole('button',{name:'重新读取套餐与订单',exact:true}).click();
 await expect(page.getByRole('region',{name:'会员购买与订单',exact:true}).getByRole('alert')).toContainText('暂时无法读取订单');
 await page.getByLabel(/我已核对 离线会员套餐/).check();await expect(page.getByRole('button',{name:'创建订单并准备支付',exact:true})).toBeDisabled();expect(state.created).toHaveLength(0);
});

test('session restoration aborts late checkout UI and only rereads server-owned orders after recovery',async({page})=>{
 let checkoutRoute,refreshRoute,finishCheckout,finishRefresh;const state=await fixture(page);
 await page.route('**/v1/member/billing/orders/offline-order-1/checkout',route=>{checkoutRoute=route;return new Promise(resolve=>{finishCheckout=resolve})});
 await page.getByLabel(/我已核对 离线会员套餐/).check();await page.getByRole('button',{name:'创建订单并准备支付',exact:true}).click();await expect.poll(()=>Boolean(checkoutRoute)).toBe(true);
 let suspended=true;const expires=Math.floor(Date.now()/1000)+3600;
 await page.route('**/v1/account/status',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(suspended?{available:true,authenticated:false,renewable:true}:{available:true,authenticated:true,account_scope:'member-commerce-fixture',expires_at:expires,model_enabled:false,entitlements:{enabled:false,membership_required:true}})}));
 await page.route('**/v1/account/refresh',route=>{refreshRoute=route;return new Promise(resolve=>{finishRefresh=resolve})});
 await page.evaluate(()=>window.dispatchEvent(new Event('hcla-member-status-refresh')));
 await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('订单操作暂时不可用');await expect.poll(()=>Boolean(refreshRoute)).toBe(true);
 await checkoutRoute.fulfill({status:200,contentType:'application/json',body:JSON.stringify({checkout_url:'https://checkout.example.test/stale'})}).catch(()=>{});finishCheckout();
 await expect(page.getByRole('link',{name:'在支付服务打开订单',exact:true})).toHaveCount(0);
 suspended=false;await refreshRoute.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:true,authenticated:true,account_scope:'member-commerce-fixture',expires_at:expires,model_enabled:false,entitlements:{enabled:false,membership_required:true}})});finishRefresh();
 await expect(page.getByRole('button',{name:'重新读取套餐与订单',exact:true})).toBeEnabled();await expect(page.getByRole('link',{name:'在支付服务打开订单',exact:true})).toHaveCount(0);expect(state.created).toHaveLength(1);expect(state.queries).toHaveLength(0);
});

async function shortQuote(page){
 const now=Date.UTC(2032,0,15,0,0,0);
 await page.clock.install({time:now});await page.clock.pauseAt(now+1000);
 const state=await fixture(page,{now,quoteSeconds:60});
 await page.getByLabel(/我已核对 离线会员套餐/).check();await page.getByRole('button',{name:'创建订单并准备支付',exact:true}).click();
 const link=page.getByRole('link',{name:'在支付服务打开订单',exact:true});await expect(link).toBeVisible();
 return {...state,now,link};
}

test('idle quote expiry removes payment actions and preserves original order reconciliation',async({page})=>{
 const state=await shortQuote(page);
 await page.clock.fastForward(59000);
 await expect(state.link).toHaveCount(0);await expect(page.getByRole('button',{name:'准备或打开此订单支付页',exact:true})).toHaveCount(0);
 await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('此订单报价已到期');
 expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(0);
 await page.getByRole('button',{name:'核验此订单付款',exact:true}).click();await expect(page.getByRole('region',{name:'会员状态',exact:true})).toContainText('会员有效');
 expect(state.queries).toHaveLength(1);expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);
 await page.getByRole('button',{name:'关闭设置'}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('SYNTHETIC_DRAFT_RETAINS_AFTER_BILLING');
});

test('background resume observes expiry and a retreating client clock cannot revive the link',async({page})=>{
 const state=await shortQuote(page);
 // Jump wall time without running timers to model a suspended background tab.
 await page.clock.setSystemTime(state.now+61000);await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
 await expect(state.link).toHaveCount(0);
 await page.clock.setSystemTime(state.now+2000);await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
 await expect(state.link).toHaveCount(0);await expect(page.getByRole('button',{name:'准备或打开此订单支付页',exact:true})).toHaveCount(0);
 expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(0);
 // A fresh quote needs another explicit user action and a new key; expiry
 // alone does not create another order or repeat checkout creation.
 state.advanceServer(61000);await page.getByRole('button',{name:'创建订单并准备支付',exact:true}).click();
 await expect(state.link).toHaveAttribute('href','https://checkout.example.test/offline-order-2');
 expect(state.created).toHaveLength(2);expect(state.created[0].idempotency_key).not.toBe(state.created[1].idempotency_key);expect(state.checkout).toHaveLength(2);expect(state.queries).toHaveLength(0);
});

test('stale payment click checks the deadline even before a suspended timer resumes',async({page})=>{
 const state=await shortQuote(page);let popups=0;page.on('popup',()=>{popups++});
 await page.context().route('https://checkout.example.test/**',route=>route.abort());
 await page.clock.setSystemTime(state.now+61000);
 await state.link.evaluate(node=>node.click());
 await expect(state.link).toHaveCount(0);expect(popups).toBe(0);
 expect(state.created).toHaveLength(1);expect(state.checkout).toHaveLength(1);expect(state.queries).toHaveLength(0);
});

test('checkout response arriving after quote expiry never publishes a payment link',async({page})=>{
 const now=Date.UTC(2032,0,15,0,0,0);await page.clock.install({time:now});await page.clock.pauseAt(now+1000);
 const state=await fixture(page,{now,quoteSeconds:5});let pending,finish;
 await page.route('**/v1/member/billing/orders/offline-order-1/checkout',route=>{pending=route;return new Promise(resolve=>{finish=resolve})});
 await page.route('**/v1/member/billing/orders/offline-order-1',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({order_id:'offline-order-1',plan_id:state.offer.plan_id,plan_version:1,amount_minor:990,currency:'CNY',duration_days:30,state:'CHECKOUT_READY',verification_state:'NOT_QUERIED',created_at:now/1000,expires_at:now/1000+5})}));
 await page.getByLabel(/我已核对 离线会员套餐/).check();await page.getByRole('button',{name:'创建订单并准备支付',exact:true}).click();await expect.poll(()=>Boolean(pending)).toBe(true);
 await page.clock.fastForward(5000);await pending.fulfill({status:200,contentType:'application/json',body:JSON.stringify({checkout_url:'https://checkout.example.test/offline-order-1'})});finish();
 await expect(page.getByRole('button',{name:'重新读取套餐与订单',exact:true})).toBeEnabled();await expect(page.getByRole('link',{name:'在支付服务打开订单',exact:true})).toHaveCount(0);
 await expect(page.getByRole('region',{name:'会员购买与订单',exact:true})).toContainText('此订单报价已到期');await expect(page.getByRole('button',{name:'核验此订单付款',exact:true})).toBeVisible();
 expect(state.created).toHaveLength(1);expect(state.queries).toHaveLength(0);
});
