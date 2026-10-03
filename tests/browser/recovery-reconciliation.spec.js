import {test,expect} from '@playwright/test';

// Recovery responses are entirely local route fixtures. No live Auth, email,
// real password, account or model is used by these interrupted-flow tests.
async function fixture(page,{lifetime=60}={}){
 const now=Date.UTC(2032,0,15,0,0,0);await page.clock.install({time:now});await page.clock.pauseAt(now);
 const state={now,reads:0,updates:0,statusCode:200,status:{available:true,ready:true,expires_at:now/1000+lifetime},pending:null,release:null,settled:null};
 let finish;state.settled=new Promise(resolve=>{finish=resolve});
 await page.route('**/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname;let body={};
  if(path==='/v1/development/status')body={enabled:true,authenticated:false,cloud:true,configuration:{configured:true,member_accounts:true}};
  else if(path==='/v1/account/status')body={available:true,authenticated:false,recovery_available:true};
  else if(path==='/v1/account/recovery/status'){
   state.reads++;await route.fulfill({status:state.statusCode,contentType:'application/json',body:JSON.stringify(state.statusCode===200?state.status:{error:'synthetic status outage'})});return;
  }else if(path==='/v1/account/recovery/complete'){
   state.updates++;state.pending=route;await new Promise(resolve=>{state.release=resolve});finish();return;
  }
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)}).catch(()=>{});
 });
 await page.goto('/account/recovery');await expect(page.getByLabel('新密码',{exact:true})).toBeVisible();
 const password='offline recovery password fixture';
 await page.getByLabel('新密码',{exact:true}).fill(password);await page.getByLabel('再次输入新密码',{exact:true}).fill(password);
 return state;
}
async function finish(state,{status=200,body={updated:true,message:'密码已更新，请使用新密码重新登录。'}}={}){
 await state.pending.fulfill({status,contentType:'application/json',body:JSON.stringify(body)}).catch(()=>{});state.release();await state.settled;
}
async function submit(page,state){await page.locator('form').evaluate(form=>{form.requestSubmit();form.requestSubmit()});await expect.poll(()=>state.updates).toBe(1)}

test('grant expiry while updating preserves the bounded response and accepts confirmed success',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const state=await fixture(page,{lifetime:5});await submit(page,state);
 try{
  await page.clock.fastForward(5000);await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新申请链接'})).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('请勿重复修改');expect(state.reads).toBe(1);
  await page.screenshot({path:info.outputPath('recovery-expired-in-flight-mobile.png'),fullPage:true,animations:'disabled'});
  await finish(state);await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);expect(state.updates).toBe(1);
 }finally{state.release?.()}
});

test('timed-out update reconciles once with a fresh request and preserves server lock',async({page},info)=>{
 const state=await fixture(page);await submit(page,state);state.status={available:true,ready:false,locked:true};
 try{
  await page.clock.fastForward(15000);await expect(page.getByRole('status')).toContainText('恢复暂时锁定');expect(state.reads).toBe(2);expect(state.updates).toBe(1);
  await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新申请链接'})).toHaveCount(0);
  await page.getByRole('button',{name:'检查恢复状态',exact:true}).click();await expect.poll(()=>state.reads).toBe(3);expect(state.updates).toBe(1);
  await page.screenshot({path:info.outputPath('recovery-timeout-server-lock.png'),fullPage:true,animations:'disabled'});
  await finish(state);await expect(page.getByRole('status')).toContainText('恢复暂时锁定');
 }finally{state.release?.()}
});

test('unavailable or merely ready status cannot reopen an uncertain password mutation',async({page})=>{
 const state=await fixture(page);await submit(page,state);state.statusCode=503;
 await finish(state,{status:503,body:{error:'synthetic uncertain update'}});await expect(page.getByRole('button',{name:'检查恢复状态',exact:true})).toBeEnabled();
 await expect(page.getByRole('status')).toContainText('结果尚未确认');await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'重新申请链接'})).toHaveCount(0);expect(state.reads).toBe(2);
 state.statusCode=200;await page.getByRole('button',{name:'检查恢复状态',exact:true}).click();await expect.poll(()=>state.reads).toBe(3);await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);
 state.status={available:true,ready:false,updated:true};await page.getByRole('button',{name:'检查恢复状态',exact:true}).click();await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toBeVisible();expect(state.updates).toBe(1);
});

test('leaving recovery aborts old work and a late success cannot replace ordinary login',async({page})=>{
 const state=await fixture(page);await submit(page,state);
 try{
  await page.goto('/');await expect(page.getByRole('heading',{name:'继续你的对话',exact:true})).toBeVisible();
  await finish(state);await expect(page.getByRole('heading',{name:'继续你的对话',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'密码已更新',exact:true})).toHaveCount(0);
  expect(state.updates).toBe(1);expect(state.reads).toBe(1);await expect(page.getByLabel('用户密码',{exact:true})).toHaveValue('');
 }finally{state.release?.()}
});

test('a suspended expiry timer cannot admit a new password mutation after the deadline',async({page})=>{
 const state=await fixture(page,{lifetime:5});await page.clock.setSystemTime(state.now+6000);
 await page.getByRole('button',{name:'更新密码并结束现有登录',exact:true}).click();await expect(page.getByRole('button',{name:'重新申请链接',exact:true})).toBeVisible();await expect(page.getByLabel('新密码',{exact:true})).toHaveCount(0);
 expect(state.updates).toBe(0);expect(state.reads).toBe(1);
});
