import {test,expect} from '@playwright/test';

async function fixture(page,{temporary=true,persistent=false,history=[]}={}){
 const state={temporary,persistent,history,creates:[],events:[],temporaryPackets:[]},expiry=Math.floor(Date.now()/1000)+3600;
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;let body=[];
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,request_bound:false,configuration:{configured:true,provider:'qwen',provider_enabled:true,member_accounts:true}};
  else if(path==='/v1/account/status')body={available:true,authenticated:true,account_scope:'synthetic-paid-scope',expires_at:expiry,model_enabled:state.temporary||state.persistent,entitlements:{enabled:state.temporary||state.persistent,membership_required:true,temporary:state.temporary,persistent:state.persistent,expires_at:expiry,access_kind:'PAID_MEMBERSHIP'}};
  else if(path==='/v1/member/conversations'){
   if(request.method()==='POST'){
    const input=request.postDataJSON();state.creates.push(input);
    expect(input.memory==='TEMPORARY'?state.temporary:state.persistent).toBe(true);
    body={id:'scope-created-'+state.creates.length,title:'新对话',memory:input.memory,topic_id:input.topic_id};state.history.push(body);
   }else body=state.history;
  }else if((path.endsWith('/events')||path==='/v1/member/temporary/execute')&&request.method()==='POST'){
   const input=request.postDataJSON();state.events.push(input.request??input);if(path==='/v1/member/temporary/execute')state.temporaryPackets.push(input);
   await route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Synthetic interception; zero provider calls'})});return;
  }else if(path.startsWith('/v1/member/conversations/'))body={runs:[],state_version:0};
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',timezone:'Asia/Shanghai',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',actor_charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500'};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 state.refresh=async()=>{
  const response=page.waitForResponse(r=>r.url().endsWith('/v1/account/status'));
  await page.evaluate(()=>window.dispatchEvent(new Event('hcla-member-status-refresh')));await response;
 };
 return state;
}
test('ordinary temporary-only member sends in the permitted scope without changing settings',async({page},info)=>{
 const state=await fixture(page);await page.getByLabel('消息',{exact:true}).fill('Original synthetic member conversation');
 await page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度').check();await expect(page.getByRole('button',{name:'发送',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'发送',exact:true}).click();await expect.poll(()=>state.events.length).toBe(1);
 expect(state.creates).toHaveLength(0);expect(state.temporaryPackets).toHaveLength(1);expect(state.temporaryPackets[0].snapshot).toBeNull();
 expect(state.events[0].allowed_memory_scope).toBe('TEMPORARY');expect(state.events[0].scope.topic_id).toBeNull();expect(state.events[0].event.text).toBe('Original synthetic member conversation');
 await expect(page.getByLabel('消息',{exact:true})).toHaveValue('Original synthetic member conversation');
 await page.getByRole('button',{name:'对话背景',exact:true}).click();await expect(page.getByLabel('当前对话范围')).toContainText('临时 · 关闭或刷新页面丢失');
 await page.screenshot({path:info.outputPath('ordinary-temporary-scope.png'),fullPage:true,animations:'disabled'});
 await page.reload();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','');
 await expect(page.getByRole('navigation',{name:'对话历史'}).getByRole('button')).toHaveCount(0);expect(state.creates).toHaveLength(0);expect(state.temporaryPackets).toHaveLength(1);
});
test('revocation preserves saved history and applies temporary scope only to the next conversation',async({page})=>{
 const state=await fixture(page,{persistent:true,history:[{id:'saved-original',title:'Saved original fixture',memory:'CONVERSATION',topic_id:null}]});
 await page.getByRole('navigation',{name:'对话历史'}).getByRole('button',{name:'Saved original fixture'}).click();await page.getByLabel('消息',{exact:true}).fill('Retained original draft');
 await page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度').check();state.persistent=false;await state.refresh();
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('Retained original draft');
 await page.getByRole('button',{name:'对话背景',exact:true}).click();await expect(page.getByLabel('当前对话范围')).toHaveText('本会话背景');await page.getByRole('button',{name:'关闭对话背景'}).click();
 await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('TEMPORARY');await page.getByRole('button',{name:'关闭设置'}).click();
 await page.locator('#newConversation').click();await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation',/^temp-/);expect(state.creates).toHaveLength(0);expect(state.events).toHaveLength(0);
 await page.getByRole('button',{name:'对话背景',exact:true}).click();await expect(page.getByLabel('当前对话范围')).toContainText('临时 · 关闭或刷新页面丢失');await page.getByRole('button',{name:'关闭对话背景'}).click();
 await expect(page.getByRole('navigation',{name:'对话历史'}).getByRole('button',{name:'Saved original fixture'})).toBeVisible();
});
test('explicit permitted project selection survives a refreshed entitlement',async({page})=>{
 const state=await fixture(page,{persistent:true});await page.getByRole('button',{name:'设置',exact:true}).click();
 await page.getByLabel('记忆范围',{exact:true}).selectOption('TOPIC');state.temporary=false;await state.refresh();
 await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('TOPIC');await expect(page.getByLabel('记忆范围',{exact:true}).locator('option[value="TEMPORARY"]')).toHaveAttribute('disabled','');expect(state.creates).toHaveLength(0);
 await page.getByLabel('记忆范围',{exact:true}).press('End');await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('TOPIC');
});
test('an account with no permitted scope cannot create or send',async({page})=>{
 const state=await fixture(page,{temporary:false,persistent:false});await page.locator('#newConversation').click();
 await expect(page.getByRole('alert').filter({hasText:'没有可用的对话范围'})).toBeVisible();await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('');expect(state.creates).toHaveLength(0);expect(state.events).toHaveLength(0);
});
test('losing temporary permission requires explicit selection before persistent creation',async({page})=>{
 const state=await fixture(page);state.temporary=false;state.persistent=true;await state.refresh();
 await page.locator('#newConversation').click();await expect(page.getByRole('alert').filter({hasText:'设置中选择可用范围'})).toBeVisible();expect(state.creates).toHaveLength(0);
 await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('');
 await page.getByLabel('记忆范围',{exact:true}).selectOption('CONVERSATION');await page.getByRole('button',{name:'关闭设置'}).click();
 await page.locator('#newConversation').click();await expect.poll(()=>state.creates.length).toBe(1);expect(state.creates[0].memory).toBe('CONVERSATION');expect(state.events).toHaveLength(0);
});
