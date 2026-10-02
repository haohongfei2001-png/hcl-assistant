import {test,expect} from '@playwright/test';

test('ordinary TEST_ONLY account offers explicit readiness without sending its draft or claiming paid membership',async({page},info)=>{
 let ready=false;const modelPosts=[];const expiry=Math.floor(Date.now()/1000)+3600;
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;let body=[];
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,request_bound:false,configuration:{configured:true,provider:'qwen',provider_enabled:true,member_accounts:true}};
  else if(path==='/v1/account/status')body={available:true,authenticated:true,account_scope:'member-test-only-fixture',expires_at:expiry,model_enabled:ready,readiness_required:!ready,readiness_available:!ready,entitlements:{enabled:true,membership_required:true,temporary:true,persistent:ready,expires_at:expiry,access_kind:'TEST_ONLY',test_max_requests:8,test_max_cost_cny:'100',test_chat_enabled:true}};
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',timezone:'Asia/Shanghai',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',actor_charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500'};
  else if(path==='/v1/member/conversations'&&request.method()==='POST'){
   expect(request.postDataJSON().memory).toBe('TEMPORARY');body={id:'synthetic-readiness',title:'临时对话',memory:'TEMPORARY',topic_id:null};
  }else if(path==='/v1/member/conversations/synthetic-readiness')body={runs:[],state_version:0};
  else if((path.endsWith('/events')||path.endsWith('/temporary/execute'))&&request.method()==='POST'){
   modelPosts.push(request.postDataJSON().request??request.postDataJSON());await route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:'Offline interception; no provider call'})});return;
  }
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.getByLabel('消息',{exact:true}).fill('PRIVATE_DRAFT_NOT_PART_OF_READINESS');
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
 const check=page.getByRole('button',{name:'验证模型连接（一次合成调用）'});
 await expect(check).toBeDisabled();await page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度').check();await expect(check).toBeEnabled();
 await page.getByRole('button',{name:'设置',exact:true}).click();
 const grant=page.getByRole('region',{name:'测试使用资格'});await expect(grant).toContainText('这不是付费会员');await expect(grant).toContainText('100');await expect(page.getByRole('region',{name:'会员状态'})).toHaveCount(0);
 await page.screenshot({path:info.outputPath('ordinary-test-only-rights.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('button',{name:'关闭设置'}).click();await check.click();
 await expect.poll(()=>modelPosts.length).toBe(1);
 expect(modelPosts[0].event.text).toBe('Mira said, "I believe that the team meeting was moved to Thursday."');
 expect(modelPosts[0].development_execution.query).toBe('What does Mira believe, and does this establish the actual meeting date?');
 expect(modelPosts[0].allowed_memory_scope).toBe('TEMPORARY');expect(modelPosts[0].member_readiness_check).toBe(true);
 await expect(page.getByLabel('消息',{exact:true})).toHaveValue('PRIVATE_DRAFT_NOT_PART_OF_READINESS');
 ready=true;
 await page.waitForResponse(response=>response.url().endsWith('/v1/account/status'),{timeout:15000});
 await expect(check).toHaveCount(0);await expect(page.getByRole('button',{name:'发送',exact:true})).toBeEnabled();
 expect(modelPosts).toHaveLength(1);
});
