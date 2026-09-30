import {test,expect} from '@playwright/test';

async function conversation(page){await page.goto('/');const created=page.waitForResponse(r=>r.url().endsWith('/v1/conversations')&&r.request().method()==='POST');await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.getByLabel('消息')).toBeFocused();return (await (await created).json()).id;}

test('desktop keyboard chat, raw source and refresh recovery',async({page})=>{
 await conversation(page);await expect(page.getByText('模拟运行：未接入真实 HCL 机制 · 仅合成数据')).toBeVisible();
 await page.getByLabel('消息').fill('2+2');await page.getByLabel('消息').press('Enter');await expect(page.getByText('2 + 2 = 4。',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'查看输入原文 v1'}).last().click();await expect(page.getByRole('dialog',{name:'原文'})).toContainText('2+2');await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'查看输入原文 v1'}).last()).toBeFocused();
 await page.reload();await page.getByRole('navigation',{name:'对话历史'}).getByRole('button').last().click();await expect(page.getByText('2 + 2 = 4。',{exact:true})).toBeVisible();
 await expect(page.locator('body')).not.toContainText('Compare');expect(await page.evaluate(()=>JSON.stringify(localStorage))).toBe('{}');
});

test('text upload reports limits and registered coverage, not understanding',async({page})=>{
 await conversation(page);await page.getByLabel('上传文本文件').setInputFiles({name:'synthetic.md',mimeType:'text/markdown',buffer:Buffer.from('原创合成文件：尚未解析。')});
 await expect(page.getByText('这段输入尚未解析。可以说明具体事件、人物和时间；当前模拟不具备任意语言理解能力。',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'查看输入原文 v1'}).last().click();await expect(page.getByRole('dialog')).toContainText('原创合成文件：尚未解析。');await expect(page.getByRole('dialog')).toContainText('未声明完整理解');await page.getByRole('button',{name:'关闭原文'}).click();
 await page.getByLabel('上传文本文件').setInputFiles({name:'bad.pdf',mimeType:'application/pdf',buffer:Buffer.from('synthetic unsupported')});await expect(page.getByRole('alert')).toContainText('仅支持 TXT');
});

test('cancel stream and explicit retry preserve one input',async({page})=>{
 await conversation(page);await page.getByLabel('消息').fill('未覆盖的原创输入');await page.getByRole('button',{name:'发送',exact:true}).click();await page.getByRole('button',{name:'停止',exact:true}).click();await expect(page.getByText('CANCELLED',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'重试',exact:true}).last().click();await expect(page.getByText('这段输入尚未解析。可以说明具体事件、人物和时间；当前模拟不具备任意语言理解能力。',{exact:true})).toBeVisible();
 await expect(page.getByLabel('消息')).toBeFocused();
});

test('narrow desktop sidebar and failed drafts remain recoverable',async({page})=>{
 await page.setViewportSize({width:760,height:800});await conversation(page);await page.getByRole('button',{name:'切换侧栏'}).click();await expect(page.getByRole('navigation')).toHaveCount(0);
 await page.route('**/v1/conversations/*/events',route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({error:'Synthetic version conflict'})}));
 await page.getByLabel('消息').fill('保留失败输入');await page.getByLabel('消息').press('Enter');await expect(page.getByRole('alert')).toContainText('409');await expect(page.getByLabel('消息')).toHaveValue('保留失败输入');
});

test('Explain binds recorded basis and light correction produces a new run',async({page})=>{
 await conversation(page);await page.getByLabel('消息').fill('报告[青]：周一收到通知');await page.getByLabel('消息').press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');
 await page.getByRole('button',{name:'Explain',exact:true}).last().click();const explain=page.getByRole('dialog',{name:'Explain'});await expect(explain).toContainText('周一收到通知');await expect(explain).toContainText('零模型调用');
 await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Explain',exact:true}).last()).toBeFocused();
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();let memory=page.getByRole('dialog',{name:'记忆管理'});await memory.locator('.memory-card').filter({hasText:'周一收到通知'}).getByRole('button',{name:'内容不对',exact:true}).click();await memory.getByLabel('修订值').fill('周二收到通知');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(page.locator('article').last()).toContainText('周二收到通知');
 await memory.getByRole('button',{name:'关闭记忆管理'}).click();await page.getByRole('button',{name:'Explain',exact:true}).first().click();await expect(page.getByRole('dialog',{name:'Explain'})).toContainText('周一收到通知');await expect(page.getByRole('dialog',{name:'Explain'})).toContainText('旧版本回答');
});

test('guess correction stop and delete propagate through history after refresh',async({page})=>{
 await conversation(page);await page.getByLabel('消息').fill('报告[澄]：原创可删除背景');await page.getByLabel('消息').press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const card=memory.locator('.memory-card').filter({hasText:'原创可删除背景'});await card.getByRole('button',{name:'这只是猜测',exact:true}).click();await expect(memory.locator('.memory-card').filter({hasText:'用户猜测'})).toContainText('原创可删除背景');
 const guess=memory.locator('.memory-card').filter({hasText:'用户猜测'});await guess.getByRole('button',{name:'停止使用',exact:true}).click();await expect(guess).toContainText('STOPPED');await guess.getByRole('button',{name:'删除',exact:true}).click();await expect(guess).toHaveCount(0);
 // Also remove the original version through account-authorized memory history.
 await memory.locator('.memory-card').filter({hasText:'原创可删除背景'}).getByRole('button',{name:'删除',exact:true}).click();await expect(memory).not.toContainText('原创可删除背景');await memory.getByRole('button',{name:'关闭记忆管理'}).click();
 await page.reload();await page.getByRole('navigation',{name:'对话历史'}).getByRole('button').last().click();await expect(page.locator('.messages')).not.toContainText('原创可删除背景');expect(await page.evaluate(()=>JSON.stringify(localStorage))).toBe('{}');
});

test('person and event-time correction use simple fields and stay scoped',async({page})=>{
 const id=await conversation(page);await page.getByLabel('消息').fill('报告[宁]：合成角色安排');await page.getByLabel('消息').press('Enter');await expect(page.locator('article').last()).toContainText('先核对关键条件');await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const active=()=>memory.locator('.memory-card').filter({hasText:'合成角色安排'}).filter({hasText:'ACTIVE'});
 await active().getByRole('button',{name:'人物不对',exact:true}).click();await memory.getByLabel('修订值').fill('柏');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(memory.getByLabel('修订值')).toHaveCount(0);
 await active().getByRole('button',{name:'时间不对',exact:true}).click();await memory.getByLabel('修订值').fill('2026-09-20T09:30');await memory.getByRole('button',{name:'提交更正并更新回答'}).click();await expect(memory.getByLabel('修订值')).toHaveCount(0);
 const context=await (await page.request.get(`/v1/context?conversation_id=${id}`)).json();const record=context.records.find(r=>r.kind==='USER_REPORTED_EVENT');expect(record.subject_refs[0]).toBe(id+':柏');expect(record.valid_time.start).not.toBeNull();expect(record.person_access_events).toEqual([]);
});
