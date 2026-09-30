import {readFileSync} from 'node:fs';
const stablePin=JSON.parse(readFileSync(new URL('../../contracts/runtime-bridge.lock.json',import.meta.url),'utf8'));
import {test,expect} from '@playwright/test';
const text='Ada said, "I believe that the workshop starts Friday."';
async function development(page,source=text,capability='belief_interpretation',memory='TEMPORARY'){
 const conversation=await (await page.request.post('/v1/conversations',{data:{title:'original-runtime-smoke',memory}})).json();
 const state=await (await page.request.get(`/v1/conversations/${conversation.id}`)).json();
 const response=await page.request.post(`/v1/conversations/${conversation.id}/events`,{data:{scope:{conversation_id:conversation.id},event:{type:'upload',filename:'original-runtime-synthetic.md',text:source},expected_state_version:state.state_version,idempotency_key:crypto.randomUUID(),development_execution:{schema_version:'1.0',capability_id:capability,query:'What does Ada believe?',input_class:'SYNTHETIC_NON_CONFIRMATION',fixture_family:'original_workshop_browser_20261001',purpose:'DEVELOPMENT_INTEGRATION_ONLY',timeout_ms:3000}}});
 return {conversation,response};
}

test('actual pinned runtime result shares Assistant Explain Lab source and deletion policy',async({page})=>{
 const ready=await (await page.request.get('/v1/development/runtime')).json();expect(ready.handshake_status).toBe('READY');expect(ready.production_enabled).toBe(false);
 expect(ready.source_commit_sha).toBe(stablePin.source_commit_sha);expect(ready.interface_version).toBe(stablePin.interface_version);expect(ready.artifact_digest).toBe(stablePin.artifact_digest);
 const {conversation,response}=await development(page);expect(response.ok()).toBeTruthy();const accepted=await response.json();
 await expect.poll(async()=> (await (await page.request.get(`/v1/runs/${accepted.run_id}`)).json()).pending).toBe(false);
 const run=await (await page.request.get(`/v1/runs/${accepted.run_id}`)).json();expect(run.run_receipt.mode).toBe('REAL');expect(run.run_receipt.actual_treatment).toBe('EXECUTED');expect(run.operation_receipts[0].used_in_answer).toBe(true);expect(run.run_receipt.usage.provider_calls).toBe(0);
 const context=await (await page.request.get(`/v1/context?conversation_id=${conversation.id}`)).json();expect(context.records).toEqual([]);
 await page.goto('/');await page.getByRole('navigation',{name:'对话历史'}).getByRole('button',{name:/original-runtime-smoke/}).last().click();await expect(page.locator('header')).toContainText('EXPERIMENTAL');await expect(page.locator('article').last()).toContainText('私人状态或世界事实');
 await page.getByRole('button',{name:'查看依据',exact:true}).last().click();const explain=page.getByRole('dialog',{name:'查看依据'});await expect(explain).toContainText('EXPERIMENTAL');await expect(explain).toContainText(text);await page.keyboard.press('Escape');
 await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'在 Lab 检查',exact:true}).last().click();const lab=page.getByRole('dialog',{name:'HCL Lab'});await expect(lab).toContainText('只读实验记录');await expect(lab).toContainText(ready.source_commit_sha);await expect(lab).toContainText('hcl-epistemic-callables-v1');await expect(lab.getByRole('button',{name:/Base Compare/})).toBeDisabled();
 const download=page.waitForEvent('download');await lab.getByRole('button',{name:'导出当前权限下的 experimental 记录'}).click();await download;await page.keyboard.press('Escape');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理'});const source=memory.locator('.memory-card').filter({hasText:'original-runtime-synthetic.md'});await source.getByRole('button',{name:'删除文件'}).click();await expect(source).toHaveCount(0);await memory.getByRole('button',{name:'关闭记忆管理'}).click();
 const exported=await (await page.request.get(`/v1/lab/export/${accepted.run_id}`)).json();expect(JSON.stringify(exported)).not.toContain('workshop starts Friday');expect(exported.run.redacted).toBe(true);
});

test('ordinary inputs stay no-treatment and persistent activation is refused',async({page})=>{
 const {response}=await development(page,'原创中文：我不知道合成同事的想法。');expect(response.ok()).toBeTruthy();const accepted=await response.json();
 await expect.poll(async()=> (await (await page.request.get(`/v1/runs/${accepted.run_id}`)).json()).pending).toBe(false);
 const run=await (await page.request.get(`/v1/runs/${accepted.run_id}`)).json();expect(run.run_receipt.actual_treatment).toBe('NO_TREATMENT');expect(run.runtime_outputs).toEqual([]);expect(run.operation_receipts[0].used_in_answer).toBe(false);expect(run.development_request.sources[0].text).toBe('原创中文：我不知道合成同事的想法。');
 const unsupported=await development(page,text,'goal_plan');expect(unsupported.response.ok()).toBeTruthy();const old=await unsupported.response.json();
 await expect.poll(async()=> (await (await page.request.get(`/v1/runs/${old.run_id}`)).json()).run_receipt.actual_treatment).toBe('UNSUPPORTED');
 const forbidden=await development(page,text,'belief_interpretation','CONVERSATION');expect(forbidden.response.status()).toBe(403);
 const noRun=await (await page.request.get(`/v1/conversations/${forbidden.conversation.id}`)).json();expect(noRun.runs).toEqual([]);expect(noRun.events).toEqual([]);
});
