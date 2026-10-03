import {test,expect} from '@playwright/test';

const development={enabled:true,authenticated:false,cloud:true,request_bound:true,configuration:{configured:true,provider_enabled:false,provider:'qwen'}};
async function fixture(page,{owner=false,available=false,member=false,rights,model=false}={}){
 const state={owner,available,member,rights,model,posts:[],reads:[],holdStatus:null};
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;
  if(request.method()==='POST')state.posts.push(path);else state.reads.push(path);
  let body=[];
  if(path==='/v1/development/status')body={...development,authenticated:state.owner};
  else if(path==='/v1/account/status'){
   if(state.holdStatus)await state.holdStatus;
   body={available:state.available,authenticated:state.member,account_scope:state.member?'member-route-synthetic':undefined,expires_at:Math.floor(Date.now()/1000)+3600,model_enabled:state.model,entitlements:state.rights};
  }else if(path==='/v1/account/register')body={confirmation_required:true,message:'请检查邮箱完成确认后登录'};
  else if(path==='/v1/account/login'){state.member=true;body={};}
  else if(path==='/v1/member/budget')body={currency:'CNY',period:'2026-10',timezone:'Asia/Shanghai',scope:'AUTHENTICATED_SHARED',charged_cost_cny:'0',actor_charged_cost_cny:'0',max_cost_cny:'500',remaining_cny:'500'};
  else if(path==='/v1/member/billing/catalog')body={available:false,plans:[],reason:'会员购买尚未开放；注册不会自动开通会员'};
  else if(path==='/v1/member/billing/orders')body={available:false,orders:[]};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)}).catch(()=>{});
 });
 return state;
}

test('closed cloud root remains an ordinary entry with an explicit maintenance route',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const state=await fixture(page);
 await page.goto('/');await expect(page.getByRole('heading',{name:'继续你的对话'})).toBeVisible();
 await expect(page.locator('body')).toContainText('普通账号服务暂未开放');
 await expect(page.locator('body')).toContainText('在线购买会员暂未开放');
 await expect(page.getByLabel('账号',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'没有账号，注册'})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath('closed-member-entry-phone.png'),fullPage:true,animations:'disabled'});
 await page.getByText('管理员入口',{exact:true}).click();await page.getByRole('button',{name:'打开管理员登录'}).click();
 await expect(page).toHaveURL(/\/admin$/);await expect(page.getByRole('heading',{name:'管理员登录'})).toBeVisible();
 await page.reload();await expect(page.getByRole('heading',{name:'管理员登录'})).toBeVisible();
 await page.getByRole('button',{name:'返回用户登录'}).click();await expect(page).toHaveURL(/\/$/);
 await expect(page.getByRole('heading',{name:'继续你的对话'})).toBeVisible();
 await page.goBack();await expect(page.getByRole('heading',{name:'管理员登录'})).toBeVisible();
 await page.goForward();await expect(page.getByRole('heading',{name:'继续你的对话'})).toBeVisible();
 expect(state.posts).toEqual([]);
});

test('an existing owner cookie never selects owner chat on the ordinary route',async({page})=>{
 const state=await fixture(page,{owner:true});await page.goto('/');
 await expect(page.getByRole('heading',{name:'继续你的对话'})).toBeVisible();
 await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0);
 expect(state.reads).not.toContain('/v1/conversations');expect(state.posts).toEqual([]);
 await page.goto('/admin');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.goto('/');await expect(page.getByRole('heading',{name:'继续你的对话'})).toBeVisible();
});

test('registration confirms email but never signs in, starts a trial or grants paid access',async({page},info)=>{
 const state=await fixture(page,{available:true});await page.goto('/');
 await page.getByRole('button',{name:'没有账号，注册'}).click();
 await expect(page.getByRole('heading',{name:'创建你的账号'})).toBeVisible();
 await expect(page.locator('body')).toContainText('注册不会自动开通会员');
 await page.getByLabel('用户邮箱').fill('registered@example.test');await page.getByLabel('用户密码',{exact:true}).fill('synthetic registration password');
 await page.getByRole('button',{name:'注册账号',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('请检查邮箱');
 await expect(page.getByLabel('用户密码',{exact:true})).toHaveValue('');
 await expect(page.getByLabel('用户邮箱')).toHaveValue('registered@example.test');
 await expect(page.getByLabel('消息',{exact:true})).toHaveCount(0);
 expect(state.posts).toEqual(['/v1/account/register']);
 await page.screenshot({path:info.outputPath('registration-awaiting-confirmation.png'),fullPage:true,animations:'disabled'});
});

test('membership expiry blocks sends immediately while preserving the account and draft',async({page},info)=>{
 const initial=Math.floor(Date.now()/1000),expiry=initial+600;
 await page.clock.install({time:initial*1000});
 const state=await fixture(page,{available:true,member:true,model:true,rights:{enabled:true,membership_required:true,temporary:true,persistent:true,expires_at:expiry}});
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.clock.pauseAt((initial+60)*1000);
 await page.getByLabel('消息',{exact:true}).fill('MEMBERSHIP_EXPIRY_DRAFT');
 await page.getByLabel('本次仅使用原创合成内容，并使用账号可用额度').check();
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'设置',exact:true}).click();
 const membership=page.getByRole('region',{name:'会员状态'});
 await expect(membership).toContainText('会员有效');await expect(membership).toContainText('北京时间');
 await expect(membership.locator('time')).toHaveAttribute('datetime',new Date(expiry*1000).toISOString());
 let release;state.holdStatus=new Promise(resolve=>release=resolve);
 try{
  await page.clock.fastForward(expiry*1000-(await page.evaluate(()=>Date.now()))+1);
  await expect(membership).toContainText('会员未开通、已到期或已停用');
  await page.getByRole('button',{name:'关闭设置'}).click();
  await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
  await expect(page.getByRole('alert')).toContainText('已到期');
  await page.getByLabel('消息',{exact:true}).press('Enter');
  await expect(page.getByLabel('消息',{exact:true})).toHaveValue('MEMBERSHIP_EXPIRY_DRAFT');
  expect(state.posts).toEqual([]);
  await page.screenshot({path:info.outputPath('membership-expiry-keeps-draft.png'),fullPage:true,animations:'disabled'});
 }finally{release();state.holdStatus=null;}
 // A stale pre-expiry server snapshot also cannot reopen Send after the date.
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
});

test('unpaid member reads closed purchase information without any financial action',async({page})=>{
 const state=await fixture(page,{available:true,member:true,rights:{enabled:false,membership_required:true,temporary:false,persistent:false,reason:'会员未开通、已到期或已停用'}});
 await page.goto('/');await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'发送',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'设置',exact:true}).click();
 await expect(page.getByRole('region',{name:'会员状态'})).toContainText('注册账号不包含模型使用权限');
 await expect(page.getByRole('region',{name:'人民币月额度'})).toContainText('所有获准用户与测试共用同一个总额度');
 await page.getByRole('button',{name:'查看购买与订单',exact:true}).click();
 await expect(page.getByRole('region',{name:'会员购买与订单'})).toContainText('会员购买尚未开放');
 expect(state.reads).toContain('/v1/member/billing/catalog');expect(state.reads).toContain('/v1/member/billing/orders');
 expect(state.posts).toEqual([]);await expect(page.getByRole('button',{name:/创建订单|打开.*支付|核验.*付款|充值/})).toHaveCount(0);
 await expect(page.getByRole('link',{name:/支付/})).toHaveCount(0);
});
