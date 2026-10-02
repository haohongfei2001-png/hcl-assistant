import {test,expect} from '@playwright/test';

const memberEntry={enabled:true,authenticated:false,cloud:true,request_bound:true,configuration:{configured:true,provider_enabled:false,member_accounts:true}};
const disabledEntry={...memberEntry,configuration:{configured:false,provider_enabled:false}};

async function accountStatus(page){
 await page.route('**/v1/account/status',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:true,authenticated:false})}));
}

test('initial connection timeout cancels its read and explicit retry reaches member entry',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await accountStatus(page);
 await page.addInitScript(()=>{window.__startupSettled=0;const original=window.fetch.bind(window);window.fetch=(input,options)=>{const result=original(input,options);if(String(input).endsWith('/v1/development/status'))result.then(()=>window.__startupSettled++,()=>window.__startupSettled++);return result}});
 let release;const held=new Promise(resolve=>release=resolve);let reads=0,mutations=0;const errors=[];
 page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(request.method()==='POST')mutations++});
 await page.route('**/v1/development/status',async route=>{reads++;if(reads===1){await held;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(disabledEntry)}).catch(()=>{})}else await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(memberEntry)})});
 try{
  await page.goto('/');
  try{await expect(page.getByRole('alert')).toContainText('连接等待过久',{timeout:17000})}
  catch(error){await page.screenshot({path:info.outputPath('startup-timeout-before.png'),fullPage:true,animations:'disabled'});throw error}
  expect(reads).toBe(1);await expect.poll(()=>page.evaluate(()=>window.__startupSettled)).toBe(1);
  await expect(page.getByRole('button',{name:'检查连接',exact:true})).toBeEnabled();
  await page.screenshot({path:info.outputPath('startup-timeout-phone.png'),fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'检查连接',exact:true}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible();
  release();await expect(page.getByLabel('用户邮箱')).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);
  expect(reads).toBe(2);expect(mutations).toBe(0);expect(errors).toEqual([]);
 }finally{release();await page.unroute('**/v1/development/status')}
});

test('initial connection is visibly pending and cannot stack duplicate reads',async({page},info)=>{
 let release;const held=new Promise(resolve=>release=resolve);let reads=0;
 await page.route('**/v1/development/status',async route=>{reads++;await held;await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(disabledEntry)}).catch(()=>{})});
 try{
  await page.goto('/');await expect(page.getByRole('button',{name:'检查连接',exact:true})).toBeVisible();
  try{await expect(page.getByRole('button',{name:'检查连接',exact:true})).toBeDisabled();await expect(page.getByRole('status')).toContainText('正在检查连接')}
  catch(error){await page.screenshot({path:info.outputPath('startup-pending-before.png'),fullPage:true,animations:'disabled'});throw error}
  expect(reads).toBe(1);await page.screenshot({path:info.outputPath('startup-pending-desktop.png'),fullPage:true,animations:'disabled'});
 }finally{release();await page.unroute('**/v1/development/status')}
});

test('optional trial status shares the connection deadline without partially opening member entry',async({page},info)=>{
 await accountStatus(page);
 await page.addInitScript(()=>{window.__trialStatusSettled=0;const original=window.fetch.bind(window);window.fetch=(input,options)=>{const result=original(input,options);if(String(input).endsWith('/v1/trial/status'))result.then(()=>window.__trialStatusSettled++,()=>window.__trialStatusSettled++);return result}});
 let release,started;const held=new Promise(resolve=>release=resolve),trialStarted=new Promise(resolve=>started=resolve);let trialReads=0,mutations=0;
 page.on('request',request=>{if(request.method()==='POST')mutations++});
 await page.route('**/v1/development/status',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...memberEntry,configuration:{...memberEntry.configuration,temporary_trial:true}})}));
 await page.route('**/v1/trial/status',async route=>{trialReads++;if(trialReads===1){started();await held}await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({available:false,authenticated:false})}).catch(()=>{})});
 try{
  await page.goto('/');await trialStarted;await expect(page.getByLabel('用户邮箱')).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('正在检查连接');
  await expect(page.getByRole('alert')).toContainText('连接等待过久',{timeout:17000});
  expect(trialReads).toBe(1);await expect.poll(()=>page.evaluate(()=>window.__trialStatusSettled)).toBe(1);
  await page.screenshot({path:info.outputPath('startup-trial-status-timeout.png'),fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'检查连接',exact:true}).click();await expect(page.getByLabel('用户邮箱')).toBeVisible();
  expect(trialReads).toBe(2);expect(mutations).toBe(0);
 }finally{release();await page.unroute('**/v1/trial/status')}
});

test('inactive owner entry shares the account surface on a narrow phone without enabling member or trial actions',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/v1/development/status',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...memberEntry,configuration:{configured:true,provider_enabled:false}})}));
 await page.goto('/');await expect(page.getByRole('heading',{name:'管理员登录',exact:true})).toBeVisible();
 await expect(page.getByLabel('账号',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'登录',exact:true})).toBeDisabled();
 await expect(page.getByRole('button',{name:'没有账号，注册'})).toHaveCount(0);await expect(page.getByRole('button',{name:'开始临时试用（仅合成内容）'})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:info.outputPath('startup-owner-entry-phone.png'),fullPage:true,animations:'disabled'});
});
