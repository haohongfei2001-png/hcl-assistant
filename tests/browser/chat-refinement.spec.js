import {test,expect} from '@playwright/test';
const pages='http://127.0.0.1:4174/';
const storageKey='hcl-assistant-pages-preview-v2';
async function send(page,text){await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0)}
for(const surface of ['local','pages']){
 test(`${surface} refined Home has one search, three supported actions and compact growing composer`,async({page},info)=>{
  await page.setViewportSize({width:1448,height:1086});await page.goto(surface==='local'?'/':pages);
  const composer=page.getByLabel('消息',{exact:true}),suggestions=page.getByRole('list',{name:'可以从这里开始'});
  await expect(suggestions.getByRole('button')).toHaveCount(3);await expect(page.getByRole('button',{name:'搜索对话',exact:true})).toHaveCount(1);
  await expect(page.getByText('TXT / Markdown',{exact:false})).toHaveCount(0);
  const measure=()=>composer.evaluate(el=>({height:el.clientHeight,padding:parseFloat(getComputedStyle(el).paddingTop)+parseFloat(getComputedStyle(el).paddingBottom),line:parseFloat(getComputedStyle(el).lineHeight),scroll:el.scrollHeight}));
  let m=await measure();expect((m.height-m.padding)/m.line).toBeGreaterThanOrEqual(1);expect((m.height-m.padding)/m.line).toBeLessThan(1.1);
  await page.screenshot({path:info.outputPath('refined-home-1448.png'),fullPage:true});
  let requests=0;page.on('request',request=>{if(/\/events$|\/sources$|\/execute$/.test(request.url())&&request.method()==='POST')requests++});
  await suggestions.getByRole('button',{name:'试试一个简单问题'}).click();await expect(composer).toHaveValue('2+2');await expect(composer).toBeFocused();expect(await page.locator('.composer-surface').evaluate(el=>getComputedStyle(el).borderColor)).toBe('rgb(119, 112, 178)');await page.screenshot({path:info.outputPath('refined-composer-focus.png'),fullPage:true});expect(requests).toBe(0);
  await suggestions.getByRole('button',{name:'添加一份合成资料'}).click();await expect(page.getByRole('dialog',{name:'附加资料'})).toContainText('64 KiB');await expect(page.getByRole('dialog')).toContainText('UTF-8');await page.keyboard.press('Escape');expect(requests).toBe(0);
  const attach=page.getByRole('button',{name:'附加文本资料',exact:true});await attach.focus();await attach.press('Enter');const chooserPromise=page.waitForEvent('filechooser');await page.getByRole('dialog',{name:'附加资料'}).getByRole('button',{name:'选择文件',exact:true}).click();const chooser=await chooserPromise;await chooser.setFiles({name:'keyboard-original.md',mimeType:'text/markdown',buffer:Buffer.from('ORIGINAL_KEYBOARD_ATTACHMENT')});await expect(page.getByRole('dialog',{name:'附加资料'})).toHaveCount(0);await expect(attach).toBeFocused();await expect(page.locator('.staged-attachment')).toContainText('keyboard-original.md');expect(requests).toBe(0);await page.getByRole('button',{name:'移除待提交附件'}).click();

  await page.getByRole('button',{name:'搜索对话',exact:true}).click();await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'搜索对话',exact:true})).toBeFocused();await composer.focus();await page.keyboard.press('Control+k');await expect(page.getByLabel('搜索历史')).toBeFocused();await page.keyboard.press('Escape');await expect(composer).toBeFocused();
  await composer.fill('原创多行\n'.repeat(20));m=await measure();expect((m.height-m.padding)/m.line).toBeLessThanOrEqual(7);expect(m.scroll).toBeGreaterThan(m.height);
  await composer.fill('');m=await measure();expect((m.height-m.padding)/m.line).toBeLessThan(1.1);
  const wrap='这是一份仅用于测试自动换行的原创合成草稿。'.repeat(5);await composer.fill(wrap);const wide=await measure();await page.setViewportSize({width:390,height:844});await expect.poll(async()=>(await measure()).height).toBeGreaterThan(wide.height);await expect(composer).toHaveValue(wrap);
  if(await page.locator('.nav-scrim').isVisible())await page.getByRole('button',{name:'关闭侧栏',exact:true}).click();await composer.fill('');await page.emulateMedia({reducedMotion:'reduce'});await page.screenshot({path:info.outputPath('refined-home-390.png'),fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await send(page,'2+2');await expect(page.locator('.home-stage')).toHaveCount(0);await expect(suggestions).toHaveCount(0);await expect(page.locator('.companion--home')).toHaveCount(0);await expect(page.locator('.companion--mini')).toHaveCount(1);await expect(page.locator('.assistant-message')).toContainText('4');await page.screenshot({path:info.outputPath('refined-conversation-390.png'),fullPage:true});
 });
}
test('Pages delete feedback, cleared history, independent draft and staged file stay truthful',async({page},info)=>{
 await page.goto(pages);await send(page,'记录：U1_DELETE_CANARY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 await page.getByLabel('消息',{exact:true}).fill('INDEPENDENT_DRAFT');await page.getByLabel('上传文本文件').setInputFiles({name:'independent.md',mimeType:'text/markdown',buffer:Buffer.from('INDEPENDENT_UNSENT_FILE')});
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'U1_DELETE_CANARY'}).getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'关闭记忆管理'}).click();
 await expect(page.locator('.operation-feedback')).toContainText('已删除选中资料');await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','');await expect(page.locator('.conversation-identity strong')).toHaveText('新对话');await expect(page.getByLabel('消息',{exact:true})).toHaveValue('INDEPENDENT_DRAFT');await expect(page.locator('.staged-attachment')).toContainText('independent.md');await expect(page.locator('body')).not.toContainText('U1_DELETE_CANARY');
 expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain('U1_DELETE_CANARY');await expect(page.locator(`[data-conversation="${id}"]`)).toContainText('历史对话');
 await expect(page.locator('.operation-feedback')).toHaveCount(0,{timeout:8000});
 await page.getByRole('button',{name:'移除待提交附件'}).click();await page.locator(`[data-conversation="${id}"]`).click();await expect(page.locator('.empty-history')).toContainText('相关消息和来源正文已删除');await expect(page.locator('.home-stage')).toHaveCount(0);await page.screenshot({path:info.outputPath('refined-cleared-history.png'),fullPage:true});
 // Reuse the same cleared conversation and verify a second carry event is not lost.
 await send(page,'记录：U1_REPEAT_DELETE');await page.getByLabel('上传文本文件').setInputFiles({name:'second.md',mimeType:'text/markdown',buffer:Buffer.from('SECOND_INDEPENDENT_FILE')});await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'U1_REPEAT_DELETE'}).getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('.staged-attachment')).toContainText('second.md');await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','');

 await page.reload();await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','');await expect(page.locator('body')).not.toContainText('删除已清理');await expect(page.locator('body')).not.toContainText('U1_DELETE_CANARY');
 await send(page,'2+2');await expect(page.locator('.assistant-message')).toContainText('4');
});
test('Pages partial deletion and failed deletion retain genuine history',async({page})=>{
 await page.goto(pages);await send(page,'记录：U1_FIRST_CANARY');await send(page,'记录：U1_SURVIVING_CANARY');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.evaluate(()=>{window.originalSetItem=Storage.prototype.setItem;Storage.prototype.setItem=()=>{throw new Error('Original synthetic quota error')}});await page.locator('.memory-card').filter({hasText:'U1_FIRST_CANARY'}).getByRole('button',{name:'删除',exact:true}).click();await expect(page.getByRole('alert').first()).toContainText('未保存');await expect(page.locator('.operation-feedback')).toHaveCount(0);await expect(page.locator('.memory-card').filter({hasText:'U1_FIRST_CANARY'})).toContainText('ACTIVE');await page.evaluate(()=>Storage.prototype.setItem=window.originalSetItem);
 await page.locator('.memory-card').filter({hasText:'U1_FIRST_CANARY'}).getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation',id);await expect(page.locator('.messages')).toContainText('U1_SURVIVING_CANARY');await expect(page.locator('body')).not.toContainText('U1_FIRST_CANARY');await expect(page.locator('.conversation-identity strong')).toHaveText('历史对话');
 await page.reload();await expect(page.locator('.messages')).toContainText('U1_SURVIVING_CANARY');await expect(page.locator('body')).not.toContainText('删除已清理');
});
test('Pages legacy cleaned title retains independent source and explicit empty-history identity',async({page})=>{
 await page.goto(pages);await page.evaluate(key=>localStorage.setItem(key,JSON.stringify({schemaVersion:2,storageRevision:0,currentId:'legacy',conversations:[{id:'legacy',title:'历史对话（删除已清理）',memory:'CONVERSATION',version:1,runs:[],records:[{id:'deleted',kind:'UNRESOLVED',status:'DELETED',version:1},{id:'independent',kind:'UNRESOLVED',legacy:true,status:'ACTIVE',version:1,content:'U1_LEGACY_INDEPENDENT'}]}]})),storageKey);await page.reload();await expect(page.locator('.empty-history')).toContainText('独立来源仍保留');await expect(page.locator('.conversation-identity strong')).toHaveText('历史对话');await expect(page.locator('.home-stage')).toHaveCount(0);await page.getByRole('button',{name:'查看保留的记录'}).click();await expect(page.getByRole('dialog',{name:'记忆管理'})).toContainText('U1_LEGACY_INDEPENDENT');expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain('删除已清理');
});

test('Pages closing memory before delete acknowledgement returns Home',async({page})=>{
 await page.goto(pages);await send(page,'记录：U1_DELAYED_DELETE');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.evaluate(()=>{const original=navigator.locks.request.bind(navigator.locks);const gate=new Promise(resolve=>window.releaseDelete=resolve);navigator.locks.request=(name,action)=>original(name,async()=>{window.deleteEntered=true;await gate;return action()})});
 await page.locator('.memory-card').filter({hasText:'U1_DELAYED_DELETE'}).getByRole('button',{name:'删除',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.deleteEntered)).toBe(true);await page.getByRole('button',{name:'关闭记忆管理'}).click();await page.evaluate(()=>window.releaseDelete());await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation','');await expect(page.locator('.home-stage')).toBeVisible();await expect(page.locator('body')).not.toContainText('U1_DELAYED_DELETE');
});
test('Pages attachment carry collision is explicit and retains both files with their owners',async({page})=>{
 await page.goto(pages);await page.getByLabel('上传文本文件').setInputFiles({name:'home.md',mimeType:'text/markdown',buffer:Buffer.from('HOME_ATTACHMENT')});await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await send(page,'记录：U1_COLLISION_DELETE');const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await page.getByLabel('上传文本文件').setInputFiles({name:'conversation.md',mimeType:'text/markdown',buffer:Buffer.from('CONVERSATION_ATTACHMENT')});
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'U1_COLLISION_DELETE'}).getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.getByRole('alert')).toContainText('home.md');await expect(page.getByRole('alert')).toContainText('conversation.md');await expect(page.locator('.staged-attachment')).toContainText('home.md');await page.locator(`[data-conversation="${id}"]`).click();await expect(page.locator('.staged-attachment')).toContainText('conversation.md');
});

test('Pages delayed deletion cannot replace a newer conversation or its draft and file',async({page})=>{
 await page.goto(pages);await send(page,'记录：U1_INDEPENDENT_CONVERSATION');const other=await page.locator('.chat-workspace').getAttribute('data-current-conversation');await page.getByLabel('消息',{exact:true}).fill('OTHER_UNSENT_DRAFT');await page.getByLabel('上传文本文件').setInputFiles({name:'other.md',mimeType:'text/markdown',buffer:Buffer.from('OTHER_UNSENT_FILE')});await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await send(page,'记录：U1_NAV_DELAYED_DELETE');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.evaluate(()=>{const original=navigator.locks.request.bind(navigator.locks);const gate=new Promise(resolve=>window.releaseDelete=resolve);navigator.locks.request=(name,action)=>original(name,async()=>{window.deleteEntered=true;await gate;return action()})});await page.locator('.memory-card').filter({hasText:'U1_NAV_DELAYED_DELETE'}).getByRole('button',{name:'删除',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.deleteEntered)).toBe(true);await page.getByRole('button',{name:'关闭记忆管理'}).click();await page.locator(`[data-conversation="${other}"]`).click();await page.evaluate(()=>window.releaseDelete());await expect(page.getByLabel('上传文本文件')).toBeEnabled();await expect(page.locator('.chat-workspace')).toHaveAttribute('data-current-conversation',other);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('OTHER_UNSENT_DRAFT');await expect(page.locator('.staged-attachment')).toContainText('other.md');await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('.operation-feedback')).toHaveCount(0);await expect(page.locator('body')).not.toContainText('U1_NAV_DELAYED_DELETE');
});

// Real shared Home, browser-only synthetic Pages runtime. No screenshot mask,
// injected CSS, remote service, account, payment or provider is used here.
for(const width of [1440,390]) test(`glass Home material and actual controls at ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height:width===390?844:960});
 await page.emulateMedia({reducedMotion:'reduce'});
 let posts=0;page.on('request',request=>{if(request.method()==='POST')posts++});
 await page.goto(pages);await expect(page.locator('.home-stage')).toBeVisible();
 await page.evaluate(()=>document.fonts.ready);
 const composer=page.getByLabel('消息',{exact:true}),surface=page.locator('.composer-surface'),attach=page.getByRole('button',{name:'附加文本资料',exact:true}),send=page.getByRole('button',{name:'发送',exact:true});
 await expect(send).toBeDisabled();await expect(page.locator('.home-companion')).toHaveCount(0);
 const boxes=await Promise.all([surface,attach,composer,send].map(node=>node.boundingBox()));
 const [shell,left,input,right]=boxes;expect(shell.height).toBeLessThanOrEqual(width===390?66:78);
 for(const box of [left,right]){expect(box.width).toBeGreaterThanOrEqual(44);expect(box.height).toBeGreaterThanOrEqual(44);expect(Math.abs((box.y+box.height/2)-(input.y+input.height/2))).toBeLessThanOrEqual(1)}
 for(const control of [page.locator('.environment'),page.locator('.background-toggle')]){const box=await control.boundingBox();expect(box.width).toBeGreaterThanOrEqual(44);expect(box.height).toBeGreaterThanOrEqual(44)}
 expect(left.x+left.width).toBeLessThan(input.x);expect(input.x+input.width).toBeLessThan(right.x);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 const style=await surface.evaluate(el=>({background:getComputedStyle(el).backgroundImage,blur:getComputedStyle(el).backdropFilter,border:getComputedStyle(el).borderWidth}));
 expect(style.background).toContain('rgba');expect(style.blur).toContain('blur');expect(style.border).toBe('1px');
 await page.screenshot({path:info.outputPath(`glass-home-${width}.png`),fullPage:true});
 await composer.fill('一起理清今天的想法');await expect(send).toBeEnabled();await expect(composer).toBeFocused();
 await page.screenshot({path:info.outputPath(`glass-home-draft-${width}.png`),fullPage:true});
 expect(posts).toBe(0);await composer.fill('第一行\n第二行\n第三行');await expect.poll(async()=>(await surface.boundingBox()).height).toBeGreaterThan(shell.height);
 await composer.fill('');await expect.poll(async()=>(await surface.boundingBox()).height).toBe(shell.height);
 await attach.click();await expect(page.getByRole('dialog',{name:'附加资料'})).toContainText('仅使用合成资料');await page.keyboard.press('Escape');await expect(attach).toBeFocused();
 expect(posts).toBe(0);await expect(page.getByText('只使用合成资料，请勿输入真实私密信息',{exact:true})).toBeVisible();
});
