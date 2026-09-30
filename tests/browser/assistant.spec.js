import {test,expect} from '@playwright/test';

async function conversation(page){await page.goto('/');if(await page.getByRole('button',{name:'＋ 新对话',exact:true}).count()===0)await page.getByRole('button',{name:'切换侧栏'}).click();const created=page.waitForResponse(r=>r.url().endsWith('/v1/conversations')&&r.request().method()==='POST');await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toBeFocused();return (await (await created).json()).id;}

test('desktop keyboard chat, raw source and refresh recovery',async({page})=>{
 await conversation(page);await expect(page.getByText('交互演示，不连接模型')).toBeVisible();
 await page.getByLabel('消息',{exact:true}).fill('2+2');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.getByText('2 + 2 = 4。',{exact:true})).toBeVisible();
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看输入原文 v1'}).last().click();await expect(page.getByRole('dialog',{name:'原文'})).toContainText('2+2');await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'查看输入原文 v1'}).last()).toBeFocused();
 await page.reload();await page.getByRole('navigation',{name:'对话历史'}).getByRole('button').last().click();await expect(page.getByText('2 + 2 = 4。',{exact:true})).toBeVisible();
 await expect(page.locator('body')).not.toContainText('Compare');expect(await page.evaluate(()=>JSON.stringify(localStorage))).toBe('{}');
});

test('text upload reports limits and registered coverage, not understanding',async({page})=>{
 await conversation(page);await page.getByLabel('上传文本文件').setInputFiles({name:'synthetic.md',mimeType:'text/markdown',buffer:Buffer.from('原创合成文件：尚未解析。')});
 await expect(page.getByText('这段输入尚未解析。可以说明具体事件、人物和时间；当前模拟不具备任意语言理解能力。',{exact:true})).toBeVisible();
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看输入原文 v1'}).last().click();await expect(page.getByRole('dialog')).toContainText('原创合成文件：尚未解析。');await expect(page.getByRole('dialog')).toContainText('未声明完整理解');await page.getByRole('button',{name:'关闭原文'}).click();
 await page.getByLabel('上传文本文件').setInputFiles({name:'bad.pdf',mimeType:'application/pdf',buffer:Buffer.from('synthetic unsupported')});await expect(page.getByRole('alert')).toContainText('仅支持 TXT');
});

test('cancel stream and explicit retry preserve one input',async({page})=>{
 await conversation(page);let release;const gate=new Promise(resolve=>release=resolve);let entered;const waiting=new Promise(resolve=>entered=resolve);await page.route('**/v1/conversations/*/events',async route=>{entered();await gate;await route.continue();});await page.getByLabel('消息',{exact:true}).fill('未覆盖的原创输入');await page.getByRole('button',{name:'发送',exact:true}).click();await waiting;await page.getByRole('button',{name:'停止',exact:true}).click();release();await expect(page.getByText('CANCELLED',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'重试',exact:true}).last().click();await expect(page.getByText('这段输入尚未解析。可以说明具体事件、人物和时间；当前模拟不具备任意语言理解能力。',{exact:true})).toBeVisible();
 await expect(page.getByLabel('消息',{exact:true})).toBeFocused();
});

test('narrow desktop sidebar and failed drafts remain recoverable',async({page})=>{
 await page.setViewportSize({width:760,height:800});await conversation(page);await expect(page.getByRole('navigation')).toHaveCount(0);await page.getByRole('button',{name:'切换侧栏'}).click();await expect(page.getByRole('navigation')).toBeVisible();await page.getByRole('button',{name:'关闭侧栏'}).click();await expect(page.getByRole('navigation')).toHaveCount(0);
 await page.route('**/v1/conversations/*/events',route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'Synthetic version conflict'})}));
 await page.getByLabel('消息',{exact:true}).fill('保留失败输入');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.getByRole('alert')).toContainText('409');await expect(page.getByLabel('消息',{exact:true})).toHaveValue('保留失败输入');
});

test('Explain binds recorded basis and light correction produces a new run',async({page})=>{
 await conversation(page);await page.getByLabel('消息',{exact:true}).fill('报告[青]：周一收到通知');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');
 await page.getByRole('button',{name:'查看依据',exact:true}).last().click();const explain=page.getByRole('dialog',{name:'查看依据'});await expect(explain).toContainText('周一收到通知');await expect(explain).toContainText('零模型调用');
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'查看依据',exact:true}).last()).toBeFocused();
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();let memory=page.getByRole('dialog',{name:'记忆管理'});await memory.locator('.memory-card').filter({hasText:'周一收到通知'}).getByRole('button',{name:'内容不对',exact:true}).click();await memory.getByLabel('修订值').fill('周二收到通知');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(page.locator('article').last()).toContainText('周二收到通知');
 await memory.getByRole('button',{name:'关闭记忆管理'}).click();await page.getByRole('button',{name:'查看依据',exact:true}).first().click();await expect(page.getByRole('dialog',{name:'查看依据'})).toContainText('周一收到通知');await expect(page.getByRole('dialog',{name:'查看依据'})).toContainText('旧版本回答');
});

test('guess correction stop and delete propagate through history after refresh',async({page})=>{
 await conversation(page);await page.getByLabel('消息',{exact:true}).fill('报告[澄]：原创可删除背景');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const card=memory.locator('.memory-card').filter({hasText:'原创可删除背景'});await card.getByRole('button',{name:'这只是猜测',exact:true}).click();await expect(memory.locator('.memory-card').filter({hasText:'用户猜测'})).toContainText('原创可删除背景');
 const guess=memory.locator('.memory-card').filter({hasText:'用户猜测'});await guess.getByRole('button',{name:'停止使用',exact:true}).click();await expect(guess).toContainText('STOPPED');await guess.getByRole('button',{name:'删除',exact:true}).click();await expect(guess).toHaveCount(0);
 // Also remove the original version through account-authorized memory history.
 await memory.locator('.memory-card').filter({hasText:'原创可删除背景'}).getByRole('button',{name:'删除',exact:true}).click();await expect(memory).not.toContainText('原创可删除背景');await memory.getByRole('button',{name:'关闭记忆管理'}).click();
 await page.reload();await page.getByRole('navigation',{name:'对话历史'}).getByRole('button').last().click();await expect(page.locator('.messages')).not.toContainText('原创可删除背景');expect(await page.evaluate(()=>JSON.stringify(localStorage))).toBe('{}');
});

test('person and event-time correction use simple fields and stay scoped',async({page})=>{
 const id=await conversation(page);await page.getByLabel('消息',{exact:true}).fill('报告[宁]：合成角色安排');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const active=()=>memory.locator('.memory-card').filter({hasText:'合成角色安排'}).filter({hasText:'ACTIVE'});
 await active().getByRole('button',{name:'人物不对',exact:true}).click();await memory.getByLabel('修订值').fill('柏');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(memory.getByLabel('修订值')).toHaveCount(0);
 await active().getByRole('button',{name:'时间不对',exact:true}).click();await memory.getByLabel('修订值').fill('2026-09-20T09:30');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(memory.getByLabel('修订值')).toHaveCount(0);
 const context=await (await page.request.get(`/v1/context?conversation_id=${id}`)).json();const record=context.records.find(r=>r.kind==='USER_REPORTED_EVENT');expect(record.subject_refs[0]).toBe(id+':柏');expect(record.valid_time.start).not.toBeNull();expect(record.person_access_events).toEqual([]);
});

test('read-only Lab shares the recorded run and Compare stays disabled',async({page})=>{
 const id=await conversation(page);await page.getByLabel('消息',{exact:true}).fill('2+2');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.getByText('2 + 2 = 4。',{exact:true})).toBeVisible();await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'在 Lab 检查',exact:true}).last().click();const lab=page.getByRole('dialog',{name:'HCL Lab'});await expect(lab).toContainText('DIRECT');await expect(lab).toContainText('MOCK');await expect(lab.getByRole('button',{name:/Base Compare/})).toBeDisabled();
 const before=await (await page.request.get(`/v1/conversations/${id}`)).json();const download=page.waitForEvent('download');await lab.getByRole('button',{name:'导出当前权限下的 mock 记录'}).click();await download;
 const after=await (await page.request.get(`/v1/conversations/${id}`)).json();expect(after.state_version).toBe(before.state_version);expect(after.runs[0].run_id).toBe(before.runs[0].run_id);await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'在 Lab 检查',exact:true}).last()).toBeFocused();
});

test('unparsed file can be stopped and deleted without leaving raw history',async({page})=>{
 await conversation(page);await page.getByLabel('上传文本文件').setInputFiles({name:'deletable-synthetic.md',mimeType:'text/markdown',buffer:Buffer.from('UNPARSED_BROWSER_DELETE_SYNTHETIC')});await expect(page.locator('article').last()).toContainText('当前模拟不具备');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const file=memory.locator('.memory-card').filter({hasText:'deletable-synthetic.md'});await file.getByRole('button',{name:'停止使用文件'}).click();await expect(file).toContainText('STOPPED');await file.getByRole('button',{name:'删除文件'}).click();await expect(file).toHaveCount(0);await memory.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('.messages')).not.toContainText('UNPARSED_BROWSER_DELETE_SYNTHETIC');
 await page.getByLabel('上传文本文件').setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from([255,254,0])});await expect(page.getByRole('alert')).toContainText('有效 UTF-8');
});

test('lost acknowledgement reuses the same event key instead of duplicating input',async({page})=>{
 const id=await conversation(page);let lost=true;
 await page.route('**/v1/conversations/*/events',async route=>{if(lost){lost=false;await route.fetch();await route.abort('failed');}else await route.continue();});
 await page.getByLabel('消息',{exact:true}).fill('2+2');await page.getByLabel('消息',{exact:true}).press('Enter');await expect(page.getByRole('alert')).toBeVisible();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('2+2');await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');
 const state=await (await page.request.get(`/v1/conversations/${id}`)).json();expect(state.events).toHaveLength(1);expect(state.runs).toHaveLength(1);await expect(page.locator('article')).toHaveCount(1);
});
