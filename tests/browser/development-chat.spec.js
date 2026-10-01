import {test,expect} from '@playwright/test';
import {mkdirSync} from 'node:fs';
const token='original-offline-browser-token-123456';
async function enter(page){
 await page.route('**/v1/**',async route=>{const request=route.request();const response=await route.fetch({url:request.url().replace('127.0.0.1:5173','127.0.0.1:8770')});await route.fulfill({response})});
 await page.goto('/');
 await expect(page.getByLabel('本地开发访问口令')).toBeVisible();await page.getByLabel('本地开发访问口令').fill(token);await page.getByRole('button',{name:'打开聊天',exact:true}).click();
 await expect(page.getByLabel('消息',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByLabel('本次仅使用原创合成输入，并使用服务器已批准额度').check();
}
async function closeSettings(page){await page.getByRole('button',{name:'关闭设置'}).click()}
async function send(page,text){await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'停止',exact:true})).toHaveCount(0)}
test('development same UI authenticates, follows Chinese context and shows truthful same-run receipt',async({page})=>{
 await enter(page);await closeSettings(page);await send(page,'原创合成设定：纸灯是蓝色');await expect(page.locator('.assistant-message').last()).toContainText('原创离线自然语言');await send(page,'刚才的纸灯是什么颜色？');await expect(page.locator('.assistant-message').last()).toContainText('蓝色');
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看本次模型与 HCL 回执'}).last().click();await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('NO_TREATMENT');await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('offline-explicit-model');await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('未知');expect(await page.locator('body').textContent()).not.toContain('HIDDEN_REASONING_CANARY');expect(await page.evaluate(()=>JSON.stringify(localStorage))).not.toContain(token);mkdirSync('.tmp/screenshots',{recursive:true});await page.screenshot({path:'.tmp/screenshots/development-chat-offline-receipt.png',fullPage:true});await page.getByRole('button',{name:'关闭本次调用回执'}).click();await page.getByRole('button',{name:'在 Lab 检查',exact:true}).last().click();await expect(page.getByRole('dialog',{name:'HCL Lab'})).toContainText('只读开发聊天记录');await expect(page.getByRole('dialog',{name:'HCL Lab'})).not.toContainText('provider-free preparation');
});
test('development original HCL input reaches pinned preparation and explicit used receipt',async({page})=>{
 await enter(page);await page.getByRole('button',{name:'发送原创 HCL 合成样例（计一次调用）'}).click();await closeSettings(page);await expect(page.locator('.assistant-message').last()).toContainText('Ada');await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'查看本次模型与 HCL 回执'}).last().click();await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('EXECUTED');await expect(page.getByRole('dialog',{name:'本次调用回执'})).toContainText('显式用于回答 true');
});
test('development provider failure is not a mock answer or automatic paid retry',async({page})=>{
 await enter(page);await closeSettings(page);await send(page,'OFFLINE_ERROR');await expect(page.locator('.messages')).toContainText('FAILED');await expect(page.getByRole('button',{name:'重试',exact:true})).toHaveCount(0);await expect(page.locator('.assistant-message').last()).not.toContainText('原创离线自然语言');
});
