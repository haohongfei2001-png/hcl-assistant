import {test,expect} from '@playwright/test';

async function conversation(page){await page.goto('/');await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.getByLabel('消息')).toBeFocused();}

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
