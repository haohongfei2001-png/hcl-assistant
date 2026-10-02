import {test,expect} from '@playwright/test';
test.use({trace:'retain-on-failure',screenshot:'only-on-failure'});
const composer=page=>page.getByLabel('消息',{exact:true});
async function sidebar(page){if(!await page.locator('#sidebar').count())await page.getByRole('button',{name:'切换侧栏'}).click()}
async function create(page,canary){
 await sidebar(page);const made=page.waitForResponse(r=>r.url().endsWith('/v1/conversations')&&r.request().method()==='POST');await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();const id=(await(await made).json()).id;await expect(composer(page)).toBeFocused();
 await composer(page).fill('报告[岚]：'+canary);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(composer(page)).toHaveValue('');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0);await expect(page.locator('article')).toContainText(canary);return {id,run:await page.locator('article').getAttribute('data-run')};
}
async function select(page,id){await sidebar(page);await page.locator(`[data-conversation="${id}"]`).click()}
async function enter(page){await page.goto('/');await expect(composer(page)).toBeVisible()}
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));

test('a hanging selected-history read times out without losing newer draft text or enabling writes',async({page},info)=>{
 await enter(page);const a=await create(page,'HISTORY_TIMEOUT_ORIGINAL_A');await composer(page).fill('A_SAVED_DRAFT');await create(page,'HISTORY_TIMEOUT_ORIGINAL_B');let started,release;const waiting=new Promise(resolve=>started=resolve),gate=new Promise(resolve=>release=resolve);let gets=0,posts=0,aborted=0;
 page.on('request',r=>{if(r.url().endsWith(`/v1/conversations/${a.id}`)&&r.method()==='GET')gets++;if(r.method()==='POST')posts++});page.on('requestfailed',r=>{if(r.url().endsWith(`/v1/conversations/${a.id}`))aborted++});
 await page.route(`**/v1/conversations/${a.id}`,async route=>{const response=await route.fetch();started();await gate;await route.fulfill({response}).catch(()=>{})});
 try{await select(page,a.id);await waiting;await expect(composer(page)).toHaveValue('A_SAVED_DRAFT');await composer(page).fill('NEWER_DRAFT_DURING_HISTORY_READ');await expect(page.getByRole('button',{name:'重新读取这段对话',exact:true})).toBeVisible({timeout:17000});await expect(page.locator('#send')).toBeDisabled();await expect(composer(page)).toHaveValue('NEWER_DRAFT_DURING_HISTORY_READ');expect(gets).toBe(1);expect(posts).toBe(0);expect(aborted).toBe(1)}finally{await page.screenshot({path:info.outputPath('history-read-timeout.png'),fullPage:true});release()}
 await page.unroute(`**/v1/conversations/${a.id}`);await page.getByRole('button',{name:'重新读取这段对话',exact:true}).click();await expect(page.locator('article')).toContainText('HISTORY_TIMEOUT_ORIGINAL_A');await expect(page.locator('#send')).toBeEnabled();await expect(composer(page)).toHaveValue('NEWER_DRAFT_DURING_HISTORY_READ');expect(gets).toBe(2);expect(posts).toBe(0);
});

test('a failed search-result history read stays in search and retries explicitly before exact-run focus',async({page},info)=>{
 await enter(page);const a=await create(page,'HISTORY_SEARCH_FAILED_TARGET');await composer(page).fill('SEARCH_TARGET_DRAFT');await create(page,'HISTORY_SEARCH_OTHER');let gets=0,posts=0;page.on('request',r=>{if(r.url().endsWith(`/v1/conversations/${a.id}`)&&r.method()==='GET')gets++;if(r.method()==='POST')posts++});
 await page.route(`**/v1/conversations/${a.id}`,route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Original selected-history failure'})}));
 await page.getByRole('button',{name:'搜索对话',exact:true}).click();await page.getByLabel('搜索历史').fill('HISTORY_SEARCH_FAILED_TARGET');const hit=page.locator('.search-hit').filter({hasText:'HISTORY_SEARCH_FAILED_TARGET'}).getByRole('button').first();await hit.click();const dialog=page.getByRole('dialog',{name:'搜索对话'});
 try{await expect(dialog).toBeVisible();await expect(dialog.getByRole('alert')).toContainText('暂时无法打开这条结果');expect(gets).toBe(1);expect(posts).toBe(0)}finally{await page.screenshot({path:info.outputPath('history-search-failure.png'),fullPage:true})}
 await page.unroute(`**/v1/conversations/${a.id}`);await hit.click();await expect(dialog).toHaveCount(0);await expect(page.locator(`[data-run="${a.run}"]`)).toBeFocused();await expect(composer(page)).toHaveValue('SEARCH_TARGET_DRAFT');expect(gets).toBe(2);expect(posts).toBe(0);
});

test('a stale failed history read cannot replace a newer A to B to A visit or its draft',async({page})=>{
 await enter(page);const a=await create(page,'HISTORY_STALE_ORIGINAL_A');await composer(page).fill('STALE_A_SAVED_DRAFT');const b=await create(page,'HISTORY_STALE_ORIGINAL_B');let first=true,started,release;const waiting=new Promise(resolve=>started=resolve),gate=new Promise(resolve=>release=resolve);
 await page.route(`**/v1/conversations/${a.id}`,async route=>{if(!first){await route.continue();return}first=false;started();await gate;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Original stale history failure'})}).catch(()=>{})});
 try{await select(page,a.id);await waiting;await select(page,b.id);await expect(page.locator('article')).toContainText('HISTORY_STALE_ORIGINAL_B');await select(page,a.id);await expect(page.locator('article')).toContainText('HISTORY_STALE_ORIGINAL_A');await expect(composer(page)).toHaveValue('STALE_A_SAVED_DRAFT');release();await frames(page);await expect(page.getByRole('alert')).toHaveCount(0);await expect(composer(page)).toHaveValue('STALE_A_SAVED_DRAFT');await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation',a.id)}finally{release()}
});

test('phone selected-history failure is recoverable and never masquerades as an empty new conversation',async({page},info)=>{
 await page.setViewportSize({width:390,height:844});await enter(page);const a=await create(page,'HISTORY_PHONE_RETRY_TARGET');await composer(page).fill('PHONE_HISTORY_DRAFT');await create(page,'HISTORY_PHONE_OTHER');
 await page.route(`**/v1/conversations/${a.id}`,route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Original phone history failure'})}));await select(page,a.id);
 try{await expect(page.getByRole('button',{name:'重新读取这段对话',exact:true})).toBeInViewport();await expect(page.locator('.home-stage')).toHaveCount(0);await expect(page.locator('#send')).toBeDisabled();await expect(composer(page)).toHaveValue('PHONE_HISTORY_DRAFT')}finally{await page.screenshot({path:info.outputPath('history-read-phone-error.png'),fullPage:true})}
 await page.unroute(`**/v1/conversations/${a.id}`);await page.getByRole('button',{name:'重新读取这段对话',exact:true}).click();await expect(page.locator('article')).toContainText('HISTORY_PHONE_RETRY_TARGET');await expect(page.locator('#send')).toBeEnabled();await expect(composer(page)).toHaveValue('PHONE_HISTORY_DRAFT');
});
