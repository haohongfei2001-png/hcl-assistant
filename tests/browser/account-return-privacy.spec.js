import {test,expect} from '@playwright/test';
async function closedAccount(page){
 const posts=[];
 await page.addInitScript(()=>{
  const original=window.fetch;window.__authFragmentAtFetch=[];
  window.fetch=(...args)=>{window.__authFragmentAtFetch.push(/access_token|refresh_token|SYNTHETIC_/i.test(location.hash));return original(...args)};
 });
 await page.route('**/v1/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname;if(request.method()==='POST')posts.push(path);
  const body=path==='/v1/development/status'?{enabled:true,authenticated:false,cloud:true,configuration:{configured:true,member_accounts:true}}:{available:true,authenticated:false};
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });return posts;
}
test('confirmation-return credentials are gone before account UI fetches and never create a login',async({page})=>{
 const posts=await closedAccount(page);
 await page.goto('/?view=welcome#access_token=SYNTHETIC_ACCESS_CANARY&refresh_token=SYNTHETIC_REFRESH_CANARY&type=signup&expires_in=3600');
 await expect(page.getByRole('button',{name:'登录账号',exact:true})).toBeVisible();
 expect(new URL(page.url()).hash).toBe('');expect(new URL(page.url()).search).toBe('?view=welcome');
 expect(await page.evaluate(()=>window.__authFragmentAtFetch.every(value=>value===false))).toBe(true);
 expect(await page.evaluate(()=>JSON.stringify({local:localStorage,session:sessionStorage,cookie:document.cookie}))).not.toContain('SYNTHETIC_');
 expect(posts).toEqual([]);await expect(page.locator('body')).not.toContainText('SYNTHETIC_');
});
test('safe hash routing survives while mixed auth fields are discarded',async({page})=>{
 const posts=await closedAccount(page);await page.goto('/#view=notes&access_token=SYNTHETIC_CANARY&token_type=bearer');
 await expect(page.getByRole('button',{name:'登录账号',exact:true})).toBeVisible();expect(new URL(page.url()).hash).toBe('#view=notes');
 await page.goto('/#/settings?view=notes');await expect(page.getByRole('button',{name:'登录账号',exact:true})).toBeVisible();expect(new URL(page.url()).hash).toBe('#/settings?view=notes');expect(posts).toEqual([]);
});
test('history replacement failure reloads a clean same-origin URL before account initialization',async({page})=>{
 const posts=await closedAccount(page);await page.addInitScript(()=>{history.replaceState=()=>{throw new Error('synthetic history failure')}});
 await page.goto('/#provider_token=SYNTHETIC_PROVIDER_CANARY&refresh_token=SYNTHETIC_REFRESH_CANARY');
 await expect(page.getByRole('button',{name:'登录账号',exact:true})).toBeVisible();expect(new URL(page.url()).hash).toBe('');
 expect(await page.evaluate(()=>window.__authFragmentAtFetch.every(value=>value===false))).toBe(true);expect(posts).toEqual([]);
});
