import {test,expect} from '@playwright/test';

async function mockedQwen(page,enabled=true){
 const seen=[];
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  let body=[];
  if(path==='/v1/development/status')body={enabled:true,authenticated:true,cloud:true,request_bound:false,configuration:{configured:true,provider:'qwen',provider_enabled:enabled,owner_smoke_only:enabled}};
  else if(path==='/v1/budget')body={currency:'CNY',period:'2026-10',timezone:'Asia/Shanghai',charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500'};
  else if(path==='/v1/conversations'&&request.method()==='POST'){
   expect(request.postDataJSON().memory).toBe('TEMPORARY');
   body={id:'qwen-fixture',title:'新对话',memory:request.postDataJSON().memory,topic_id:null};
  }
  else if(path==='/v1/conversations/qwen-fixture')body={runs:[],state_version:0};
  else if(path.endsWith('/events')&&request.method()==='POST'){
   seen.push(request.postDataJSON());
   await route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Offline browser interception: no provider call'})});return;
  }
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/admin');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 return seen;
}

test('Qwen owner smoke names the actual provider and sends its explicit policy and original belief case',async({page})=>{
 const seen=await mockedQwen(page);
 await expect(page.locator('body')).toContainText('千问3.8-Max');
 await page.getByRole('button',{name:'设置',exact:true}).click();
 await expect(page.getByRole('region',{name:'人民币月额度'})).toContainText('500');
 await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('TEMPORARY');
 await expect(page.getByLabel('记忆范围',{exact:true}).locator('option[value="CONVERSATION"]')).toHaveAttribute('disabled','');
 await page.getByLabel('记忆范围',{exact:true}).press('Home');
 await expect(page.getByLabel('记忆范围',{exact:true})).toHaveValue('TEMPORARY');
 await page.getByLabel('本次仅使用原创合成输入，并使用服务器已批准额度').check();
 await page.getByRole('button',{name:'发送原创 HCL 合成样例（计一次调用）'}).click();
 await expect.poll(()=>seen.length).toBe(1);
 expect(seen[0].model_resource_policy.adapter).toBe('QWEN');
 expect(seen[0].event.text).toBe('Mira said, "I believe that the team meeting was moved to Thursday."');
 expect(seen[0].development_execution.query).toBe('What does Mira believe, and does this establish the actual meeting date?');
 expect(seen[0].allowed_memory_scope).toBe('TEMPORARY');
});

test('Qwen key-only disabled configuration never claims a live provider or sends a chat',async({page})=>{
 const seen=await mockedQwen(page,false);
 await expect(page.locator('body')).toContainText('模型服务暂未开放');
 await expect(page.locator('body')).not.toContainText('千问3.8-Max 真实调用');
 await page.getByLabel('消息',{exact:true}).fill('This offline draft must remain unsent');
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
 expect(seen).toHaveLength(0);
});

test('registered unpaid Qwen account cannot send and sees the shared membership boundary',async({page})=>{
 const modelPosts=[];
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;let body=[];
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,request_bound:true,configuration:{configured:true,provider:'qwen',provider_enabled:true,member_accounts:true,owner_smoke_only:false,shared_monthly:true}};
  else if(path==='/v1/account/status')body={available:true,authenticated:true,account_scope:'member-offline-fixture',expires_at:Math.floor(Date.now()/1000)+3600,model_enabled:false,entitlements:{enabled:false,temporary:false,persistent:false,membership_required:true,reason:'会员未开通；注册账号不包含模型使用权限'}};
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',scope:'AUTHENTICATED_SHARED',timezone:'Asia/Shanghai',charged_cost_cny:'20',actor_charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'480'};
  if(request.method()==='POST'&&/events|execute/.test(path))modelPosts.push(path);
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await expect(page.locator('body')).toContainText('会员未开通');
 await page.getByLabel('消息',{exact:true}).fill('Offline unpaid account draft');
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'设置',exact:true}).click();
 await expect(page.getByRole('region',{name:'人民币月额度'})).toContainText('所有获准用户与测试共用同一个总额度');
 expect(modelPosts).toHaveLength(0);
});
