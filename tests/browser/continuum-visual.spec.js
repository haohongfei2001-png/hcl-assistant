import {test,expect} from '@playwright/test';
import {createHash} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';

/** Original synthetic acceptance fixtures. No live/provider execution, receipt
 * substitution, response-text injection, or bitmap-backed UI is used here.
 * Local long answers are the existing bounded mock projection; Pages answers
 * are explicitly labelled source excerpts. Screenshots remain unedited.
 * Passing assertions is not a region-level visual acceptance of V01–V10.
 */
const PAGES='http://127.0.0.1:4174/';
const STORAGE='hcl-assistant-pages-preview-v2';
const FIXTURE_ID='continuum-original-paper-lantern-20261001';
const OLD='日期标记：原创灯会周五布展';
const NEW='日期标记：原创灯会改为周六布展，其他事项尚未重新评估';
const paragraphs=[
 '这是为界面验收新写的纸灯展览合成材料。策划人澄负责核对纸卡编号，协作者岚负责登记展台位置。所有人名、活动和安排都是虚构的，文字只用于检查阅读与来源定位。表格中的日期是这份材料的内容，不是外部事实，也不是模型理解能力的证明。旧记录应当保留当时版本，后来的更正必须单独呈现，不能悄悄覆盖之前的回答。',
 '场地包含入口说明区、作品展示区和安静阅读区。入口说明区需要一张清楚的时间卡，展示区需要可辨认的作品编号，阅读区需要完整的材料目录。当前资料没有记录参与者何时获知新的安排，因此检查界面必须保留未知，不用系统保存时间替代人物获知时间。资料登记、被选入背景以及被用于回答，是三个需要分别核对的事实。',
 '整理工作从确认来源开始。每张纸卡都有自己的版本，修改某一张纸卡不代表其他独立来源已经改变。若两个登记者提供的说法不同，应当将差异保留下来，而不是选择更顺眼的一个。这个受限演示能够展示来源、历史和更正记录，却不能凭结构漂亮就断言已经理解全部材料，更不能推断任何人的私人想法。',
 '阅读长回答时，使用者可能停留在中间一段核对出处。打开依据以后，原来的回答仍应当可辨认；进入原文后，返回按钮应当回到同一层依据。普通关闭和明确返回回答位置有不同含义。前者尊重使用者后来主动阅读的位置，后者回到最初的触发点。这些行为需要真实浏览器轨迹来验证，不能由示意截图代替。',
 '这次演示中的文件是新建的纯文本附件。测试将先选择文件，再明确点击提交附件，最后核对登记后的原始字节。选择不代表已经提交，完整读取不代表理解，显示了引用也不自动证明语义支持。遇到来源删除或者权限变化时，应当停止显示不再可用的原文，而不是从之前的缓存中把文字恢复出来。',
 '更正流程先确定要修改哪一条背景，再显示旧信息、新信息和受到影响的回答。背景已经提交成功以后，某个旧回答仍可能没有重新评估。界面应该直接说明这个区别，而不把新版本号或者动画结束当成理解完成。若更正失败，编辑框保留可恢复的内容，原记录不能提前显示为已经更新。',
 '深色文字需要在浅冰蓝背景和白色阅读表面上保持清楚。控件不应为了让截图显得整齐而缩成细小的字。窄窗口下，导航和来源详情需要转换成可操作的单层界面；表格和代码可以在自己的区域滚动，但整张页面不应被推到屏幕外。键盘焦点、中文输入法和放大阅读需要分别留下证据。',
 '装饰形态只是一种可选的界面元素。悬浮核心和接收容器都没有麦克风权限，也没有监听含义。安静阅读期间不应出现连续漂浮的装饰循环；正在执行的实际工作与装饰本身必须分开。关闭装饰以后，状态信息、文本和输入框仍然完整，不能把必要的反馈藏在一个不可见的图案里。',
];
const STRUCTURES='\n\n## 原创纸灯展览核对清单\n\n|事项|当前原始记录|限制|\n|---|---|---|\n|布展|周五|后续更正单独登记|\n|入口|东侧待核对|不推断已经确认|\n\n> 原创合成引用：登记表示保存了这句话，不表示这句话已被独立验证。\n\n```text\n原创流程：核对来源 → 登记版本 → 按当前权限查看\nTHIS_IS_SYNTHETIC_RENDERING_CONTENT\n```\n\n';
const FILE_TEXT='# 原创合成材料，不是实时模型分析\n\n'+STRUCTURES+paragraphs.map((p,i)=>`### 原创阅读段落 ${i+1}\n\n${p}\n\n${paragraphs[(i+3)%paragraphs.length]}`).join('\n\n')+'\n\n原始附件结束标记：CONTINUUM_ORIGINAL_END';
const FILE_NAME='continuum-original-paper-lantern.txt';
const sha=value=>createHash('sha256').update(value).digest('hex');
const chinese=value=>(value.match(/\p{Script=Han}/gu)||[]).length;
const url=surface=>surface==='pages'?PAGES:'/';

// Artifacts are retained under test-results, already collected by the canonical workflow.
test.use({viewport:{width:1448,height:1086},deviceScaleFactor:1,trace:'on',video:{mode:'on',size:{width:1448,height:1086}},screenshot:'only-on-failure'});

async function settle(page){await page.evaluate(async()=>{await document.fonts.ready;await Promise.all(document.getAnimations().filter(animation=>animation.effect?.getTiming().iterations!==Infinity).map(animation=>animation.finished.catch(()=>{})));await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))})}
async function measuredA11y(page){return page.evaluate(()=>{
 const rgba=value=>{const n=value.match(/[\d.]+/g)?.map(Number)||[0,0,0,0];return [n[0],n[1],n[2],n.length>3?n[3]:1]};
 const blend=(front,back)=>front.slice(0,3).map((v,i)=>v*front[3]+back[i]*(1-front[3]));
 const lum=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
 const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
 function background(el){const chain=[];for(let node=el;node;node=node.parentElement)chain.push(node);let value=[220,232,252];for(const node of chain.reverse()){const style=getComputedStyle(node);if(node.matches('.continuum-shell'))continue;value=blend(rgba(style.backgroundColor),value)}return value}
 const effectiveOpacity=el=>{let opacity=1;for(let node=el;node;node=node.parentElement)opacity*=Number(getComputedStyle(node).opacity);return opacity};
 const samples=[];for(const selector of ['.home-copy>p','.home-copy>small','.composer-note','.composer-controls>small','.markdown p','.context-panel p','.environment','.error','.send']){for(const node of [...document.querySelectorAll(selector)].slice(0,8)){const box=node.getBoundingClientRect();if(!box.width||!box.height)continue;const style=getComputedStyle(node),bg=background(node),fg=blend(rgba(style.color),bg);samples.push({selector,effectiveOpacity:effectiveOpacity(node),foreground:fg,compositedBackground:bg,contrast:ratio(fg,bg),disabled:node.matches(':disabled'),fontSize:parseFloat(style.fontSize)})}}
 const targets=[];for(const selector of ['#send','.composer-controls>button','.chat-workspace>header>button:first-child','.return-to-answer','.panel-header button'])for(const node of document.querySelectorAll(selector)){const box=node.getBoundingClientRect();if(box.width&&box.height)targets.push({selector,width:box.width,height:box.height})}
 const selectionNode=document.querySelector('.markdown p,.home-copy p,#composer'),selection=getComputedStyle(selectionNode,'::selection'),selectionBg=blend(rgba(selection.backgroundColor),background(selectionNode)),selectionFg=blend(rgba(selection.color),selectionBg);
 const active=document.activeElement,focusStyle=getComputedStyle(active),focusColor=rgba(focusStyle.outlineColor),focus={visible:active.matches(':focus-visible'),width:parseFloat(focusStyle.outlineWidth),contrast:ratio(focusColor,background(active))};
 return {focus,method:'Observed computed foreground and RGBA ancestor surfaces, alpha-composited over the conservative darkest channel bound of the actual fixed gradient palette (220,232,252); not nominal token contrast or a masked screenshot',samples,targets,selectionContrast:ratio(selectionFg,selectionBg)};
})}

async function capture(page,info,name){await settle(page);const a11y=await measuredA11y(page);await writeFile(info.outputPath(name+'-accessibility.json'),JSON.stringify(a11y,null,2));await info.attach(name+'-accessibility-measurements',{body:JSON.stringify(a11y),contentType:'application/json'});for(const sample of a11y.samples){expect(sample.effectiveOpacity,`${name} ${sample.selector} settled text opacity`).toBe(1);expect(sample.contrast,`${name} ${sample.selector} composited contrast`).toBeGreaterThanOrEqual(sample.disabled?3:4.5);}for(const target of a11y.targets){expect(target.width,`${name} ${target.selector} width`).toBeGreaterThanOrEqual(43.5);expect(target.height,`${name} ${target.selector} height`).toBeGreaterThanOrEqual(43.5)}expect(a11y.selectionContrast).toBeGreaterThanOrEqual(4.5);if(name==='keyboard-focus-visible'){expect(a11y.focus.visible).toBe(true);expect(a11y.focus.width).toBeGreaterThanOrEqual(2);expect(a11y.focus.contrast).toBeGreaterThanOrEqual(3)}const path=info.outputPath(name+'.png');await page.screenshot({path,fullPage:true});await info.attach(name,{path,contentType:'image/png'});const state=await page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,font:getComputedStyle(document.querySelector('.continuum-shell')).fontFamily,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,motion:document.querySelector('.continuum-shell').dataset.motion,transparency:document.querySelector('.continuum-shell').dataset.transparency,companion:document.querySelector('.companion')?.dataset.derivativeOf||'off'}));const captureMetadata={fixtureId:FIXTURE_ID,fixtureSha256:sha(FILE_TEXT),implementationSha:process.env.PRODUCT_SHA||process.env.GITHUB_SHA||'UNVERIFIED_WORKTREE',...state};await writeFile(info.outputPath(name+'-capture-metadata.json'),JSON.stringify(captureMetadata,null,2));await info.attach(name+'-capture-metadata',{body:JSON.stringify(captureMetadata),contentType:'application/json'});return path}
async function metadata(page,browser,info,surface,extra={}){
 const observed=await page.evaluate(()=>({viewport:{width:innerWidth,height:innerHeight},dpr:devicePixelRatio,font:getComputedStyle(document.querySelector('.continuum-shell')).fontFamily,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,motion:document.querySelector('.continuum-shell').dataset.motion,transparency:document.querySelector('.continuum-shell').dataset.transparency}));
 const data={fixtureId:FIXTURE_ID,fixtureSha256:sha(FILE_TEXT),fixtureChineseCharacters:chinese(FILE_TEXT),sourceClass:'ORIGINAL_SYNTHETIC_NOT_LIVE_MODEL_OUTPUT',surface,implementationSha:process.env.PRODUCT_SHA||process.env.GITHUB_SHA||'UNVERIFIED_WORKTREE',browserVersion:browser.version(),...observed,...extra,limitations:['Screenshots are actual unedited browser captures; region-by-region comparison remains a separate review','CSS text enlargement is labelled separately from native browser zoom','No claim of model latency, production readiness, semantic generalization or HCL efficacy']};
 await writeFile(info.outputPath('continuum-evidence.json'),JSON.stringify(data,null,2));await info.attach('continuum-evidence',{body:JSON.stringify(data,null,2),contentType:'application/json'});
}
async function originals(info,ids){
 const root=resolve('docs/design/continuum-v1'),manifest=JSON.parse(await readFile(resolve(root,'asset-manifest.json'),'utf8'));
 for(const id of ids){const asset=manifest.assets.find(a=>a.id===id),wrapper=await readFile(resolve(root,asset.path),'utf8'),encoded=/data:image\/png;base64,([^"\s]+)/.exec(wrapper);expect(encoded,`${id} original payload`).not.toBeNull();const bytes=Buffer.from(encoded[1],'base64');expect(sha(bytes)).toBe(asset.sha256);await info.attach(id+'-unchanged-approved-reference',{body:bytes,contentType:'image/png'})}
}
async function open(page,surface){await page.goto(url(surface));await expect(page.getByLabel('消息',{exact:true})).toBeVisible();await expect(page.getByLabel('上传文本文件')).toBeEnabled();await expect(page.locator('.environment')).toContainText('交互演示，不连接模型')}
async function send(page,text){const n=await page.locator('article').count();await page.getByLabel('消息',{exact:true}).fill(text);await page.getByRole('button',{name:'发送',exact:true}).click();await expect(page.locator('article')).toHaveCount(n+1);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'发送',exact:true})).toBeVisible({timeout:15000});await expect(page.locator('article').last().locator('.markdown')).not.toHaveText('')}
async function sidebar(page){if(!await page.getByRole('button',{name:'设置',exact:true}).isVisible())await page.getByRole('button',{name:'切换侧栏',exact:true}).click()}
async function settings(page,values){await sidebar(page);await page.getByRole('button',{name:'设置',exact:true}).click();for(const [label,value] of Object.entries(values))await page.getByLabel(label,{exact:true}).selectOption(value);await page.getByRole('button',{name:'关闭设置',exact:true}).click();if(await page.locator('.nav-scrim').isVisible())await page.getByRole('button',{name:'关闭侧栏',exact:true}).click()}
async function assertWidth(page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No document-wide horizontal overflow').toBe(true);for(const selector of ['.header-search','#composer','#send']){const box=await page.locator(selector).boundingBox();expect(box,selector).not.toBeNull();expect(box.x,selector+' left').toBeGreaterThanOrEqual(-1);expect(box.x+box.width,selector+' right').toBeLessThanOrEqual((await page.viewportSize()).width+1)}}
async function requestAudit(page,info,surface){
 const requests=[];page.on('request',request=>requests.push(request.url()));
 return async()=>{
  const origins=new Set(surface==='pages'?['http://127.0.0.1:4174']:['http://127.0.0.1:5173']);
  expect(requests.filter(value=>!origins.has(new URL(value).origin))).toEqual([]);
  if(surface==='pages')expect(requests.filter(value=>new URL(value).pathname.startsWith('/v1/'))).toEqual([]);
  await info.attach('observed-browser-request-urls',{body:JSON.stringify(requests,null,2),contentType:'application/json'});
 };
}
async function zeroProvider(page,surface){
 if(surface==='pages')return {providerCalls:0,evidence:'Observed static same-origin browser requests and the Pages no-backend transport boundary; no invented runtime receipt'};
 const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
 if(!id)return {providerCalls:0,evidence:'No conversation execution requested'};
 const response=await page.request.get(`/v1/conversations/${id}`);expect(response.ok()).toBe(true);const value=await response.json();
 expect(value.runs.length).toBeGreaterThan(0);for(const run of value.runs){expect(run.run_receipt.usage.provider_calls).toBe(0);expect(run.run_receipt.mode).toBe('MOCK')}
 return {providerCalls:0,evidence:'Every actual local run receipt reports MOCK/provider_calls=0',runIds:value.runs.map(r=>r.run_id)};
}
async function attachment(page,surface){
 const before=await page.locator('article').count();await page.getByLabel('上传文本文件').setInputFiles({name:FILE_NAME,mimeType:'text/plain',buffer:Buffer.from(FILE_TEXT)});
 await expect(page.locator('.staged-attachment')).toContainText('已选择，尚未提交');await expect(page.locator('article')).toHaveCount(before);
 await page.getByRole('button',{name:'提交附件',exact:true}).click();await expect(page.locator('.staged-attachment')).toHaveCount(0);await expect(page.locator('article')).toHaveCount(before+1);await expect(page.locator('.attachment').filter({hasText:FILE_NAME})).toContainText('已完整登记');await expect(page.getByRole('button',{name:'发送',exact:true})).toBeVisible({timeout:15000});await expect(page.locator('article').last().getByRole('status')).toHaveCount(0);
 if(surface==='pages'){
  const record=await page.evaluate(({key,name})=>JSON.parse(localStorage.getItem(key)).conversations.flatMap(c=>c.records).find(r=>r.fileName===name),{key:STORAGE,name:FILE_NAME});expect(record.content).toBe(FILE_TEXT);expect(record.byteLength).toBe(Buffer.byteLength(FILE_TEXT));
 }else{
  const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');const value=await(await page.request.get(`/v1/conversations/${id}`)).json();const run=value.runs.find(r=>r.input_text===FILE_TEXT);expect(run).toBeTruthy();const ref=run.input_source_ref;const source=await page.request.get(`/v1/sources/${ref.source_id}?conversation_id=${id}&version=${ref.version}&sha256=${ref.sha256}`);expect(source.ok()).toBe(true);expect((await source.json()).text).toBe(FILE_TEXT);
 }
}
async function longConversation(page,surface){
 if(surface==='pages'){
  await send(page,'记录：'+OLD+'。这只是原创合成安排，尚待核对。');await attachment(page,surface);await send(page,'演示：查看当前背景');await send(page,'演示：查看当前背景');
 }else{
  // Explicit typed original records exercise the actual mock Controller, whose
  // answers are bounded 180-character excerpts. Nothing patches an answer/receipt.
  const starts=['\n\n## 原创合成计划\n\n'+OLD+'。','\n\n|事项|记录|\n|---|---|\n|布展|周五待核对|\n\n','\n\n```text\n原创步骤：核对纸卡版本\n```\n\n','\n\n> 原创引文：保存不证明真实，引用不证明理解。\n\n'];
  const records=starts.map((start,i)=>({kind:'USER_REPORTED_EVENT',content:start+paragraphs[i]+paragraphs[i+4]}));
  const created=await page.request.post('/v1/conversations',{data:{title:'原创合成 Continuum 长阅读验收',memory:'CONVERSATION'}});expect(created.ok()).toBe(true);const c=await created.json();const state=await(await page.request.get(`/v1/conversations/${c.id}`)).json();
  const accepted=await page.request.post(`/v1/conversations/${c.id}/events`,{data:{scope:{conversation_id:c.id},expected_state_version:state.state_version,idempotency_key:'continuum-'+Date.now(),model_resource_policy:{adapter:'MOCK',max_provider_calls:0},event:{text:'原创结构化合成输入；以下为受限 Controller 明确记录，不是模型生成。\n'+records.map(r=>r.content).join('\n\n'),records}}});expect(accepted.ok()).toBe(true);const run=await accepted.json();
  await expect.poll(async()=> (await(await page.request.get(`/v1/runs/${run.run_id}`)).json()).pending,{timeout:15000}).toBe(false);
  await page.reload();await page.locator(`[data-conversation="${c.id}"]`).click();await expect(page.locator('article')).toHaveCount(1);
  for(const question of ['原创合成阅读检查：保留当前来源摘录。','原创合成阅读检查：再次核对未验证的安排。','原创合成阅读检查：继续查看原始条件。'])await send(page,question);
  await attachment(page,surface);
 }
 const responses=await page.locator('.assistant-message .markdown').allTextContents();expect(responses.length).toBeGreaterThanOrEqual(3);expect(chinese(responses.join('\n'))).toBeGreaterThanOrEqual(2000);
 expect(await page.locator('.user-message').count()).toBeGreaterThanOrEqual(3);await expect(page.locator('.markdown table').last()).toBeVisible();expect(await page.locator('.markdown blockquote').count()).toBeGreaterThan(0);expect(await page.locator('.markdown pre code').count()).toBeGreaterThan(0);
 return {assistantChineseCharacters:chinese(responses.join('\n')),userTurns:await page.locator('.user-message').count(),assistantTurns:responses.length,projection:surface==='pages'?'Actual Pages source excerpts':'Actual bounded MOCK excerpts, repeated across independent original synthetic requests'};
}
async function fullAnswerTiles(page,info){
 // Unedited viewport tiles cover each answer without resizing or restyling DOM.
 const index=[];const answers=page.locator('.assistant-message');
 for(let answer=0;answer<await answers.count();answer++){
  const el=answers.nth(answer);const geometry=await el.evaluate(node=>{const root=node.closest('.messages');return {start:root.scrollTop+node.getBoundingClientRect().top-root.getBoundingClientRect().top,height:node.getBoundingClientRect().height,viewport:root.clientHeight,max:root.scrollHeight-root.clientHeight}});
  const step=Math.max(120,geometry.viewport-70);expect(Math.ceil(geometry.height/step)).toBeLessThan(40);
  for(let offset=0,tile=0;offset<geometry.height;offset+=step,tile++){
   const target=Math.min(geometry.max,Math.max(0,geometry.start+offset-16));await page.locator('.messages').evaluate((node,value)=>node.scrollTop=value,target);const file=await capture(page,info,`long-answer-${answer+1}-tile-${tile+1}`);index.push({answer:answer+1,tile:tile+1,file,scrollTop:await page.locator('.messages').evaluate(node=>node.scrollTop),...geometry});
  }
 }
 await info.attach('full-answer-viewport-tile-index',{body:JSON.stringify(index,null,2),contentType:'application/json'});
}

for(const surface of ['local','pages']){
 test(`${surface} Continuum Home and working companion A B off with static opaque evidence`,async({page,browser},info)=>{
  test.setTimeout(90000);const audit=await requestAudit(page,info,surface);await open(page,surface);await originals(info,['UI-01','M-01','M-02']);
  await expect(page.locator('.home-stage')).toBeVisible();await capture(page,info,'home-1448-A');
  await settings(page,{'伙伴形态':'receiver'});await expect(page.locator('.home-companion .companion')).toHaveAttribute('data-derivative-of','M-02');await capture(page,info,'home-1448-B');
  await settings(page,{'伙伴形态':'off'});await expect(page.locator('.companion')).toHaveCount(0);await expect(page.locator('.composer')).toBeVisible();await capture(page,info,'home-1448-off');
  await send(page,'2+2');await capture(page,info,'working-1448-off');
  for(const [variant,label] of [['orb','A'],['receiver','B']]){await settings(page,{'伙伴形态':variant});await expect(page.locator('.answer-identity .companion')).toHaveCount(1);await expect(page.locator('.companion')).toHaveAttribute('aria-hidden','true');await capture(page,info,'working-1448-'+label)}
  await page.emulateMedia({reducedMotion:'reduce'});await settings(page,{'动态效果':'static','表面效果':'opaque'});expect(await page.locator('.companion-body').evaluate(node=>getComputedStyle(node).animationName)).toBe('none');expect(await page.locator('.continuum-shell').evaluate(node=>getComputedStyle(node).backgroundImage)).toBe('none');await capture(page,info,'working-B-reduced-motion-opaque');
  await assertWidth(page);await audit();await metadata(page,browser,info,surface,{coverage:['V01','V09','V08 static/opaque subset'],zeroProvider:await zeroProvider(page,surface)});
 });

 test(`${surface} Continuum original long reading source return and committed revision replay`,async({page,browser},info)=>{
  test.setTimeout(150000);const audit=await requestAudit(page,info,surface);await open(page,surface);await originals(info,['UI-02','UI-03']);await info.attach(FIXTURE_ID,{body:FILE_TEXT,contentType:'text/plain'});
  let metrics;await test.step('Create original synthetic 3+3 long reading and deliberately submit exact TXT bytes',async()=>{metrics=await longConversation(page,surface)});
  await fullAnswerTiles(page,info);const selected=page.locator('article').last(),runId=await selected.getAttribute('data-run'),before=await selected.locator('.markdown').textContent();
  await test.step('Chosen answer to recorded evidence to original source and return',async()=>{
   const trigger=selected.getByRole('button',{name:'查看依据',exact:true});await trigger.scrollIntoViewIfNeeded();await capture(page,info,'chosen-answer-before-evidence');await trigger.click();const evidence=page.getByRole('dialog',{name:'查看依据',exact:true});await expect(evidence).toHaveAttribute('aria-modal','false');await expect(page.locator('article.is-context-target')).toHaveAttribute('data-run',runId);await capture(page,info,'evidence-1448');
   const sourceButton=evidence.getByRole('button',{name:/查看来源 v/});await expect(sourceButton.first()).toBeVisible();const selectedSource=surface==='pages'?sourceButton.last():sourceButton.first();await selectedSource.scrollIntoViewIfNeeded();const evidenceScroll=await evidence.evaluate(node=>node.scrollTop);await selectedSource.click();const source=page.getByRole('dialog',{name:'原文',exact:true});await expect(source).toContainText('原创');await source.evaluate(node=>node.scrollTop=Math.min(260,node.scrollHeight-node.clientHeight));await capture(page,info,'source-1448-scrolled');await source.getByRole('button',{name:'返回依据',exact:true}).click();await expect(evidence).toBeVisible();await expect(selectedSource).toHaveAttribute('aria-current','true');await expect(selectedSource).toBeFocused();await expect.poll(async()=>Math.abs(await evidence.evaluate(node=>node.scrollTop)-evidenceScroll)).toBeLessThanOrEqual(2);await evidence.getByRole('button',{name:'返回回答位置',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await expect(trigger).toBeFocused();await expect(selected.locator('.markdown')).toHaveText(before);await capture(page,info,'returned-same-answer-1448');
  });
  await test.step('Precisely correct the original record and retain pending old-analysis state',async()=>{
   await sidebar(page);await page.getByRole('button',{name:'记忆管理',exact:true}).click();const memory=page.getByRole('dialog',{name:'记忆管理',exact:true});const row=memory.locator('.memory-card').filter({hasText:OLD}).filter({hasText:'ACTIVE'}).first();await row.getByRole('button',{name:'内容不对',exact:true}).click();await page.getByLabel('修订值',{exact:true}).fill(NEW);await capture(page,info,'correction-exact-target-before-submit');
   const conversation=await page.locator('.chat-workspace').getAttribute('data-current-conversation');
   const accepted=surface==='local'?page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname===`/v1/conversations/${conversation}/events`&&response.request().postDataJSON()?.event?.type==='revision'):null;
   await page.getByRole('button',{name:'提交更正并更新回答',exact:true}).click();
   if(accepted){const response=await accepted;expect(response.ok()).toBe(true);const run=await response.json();await expect.poll(async()=>{const result=await page.request.get(new URL(`/v1/runs/${run.run_id}`,page.url()).href);expect(result.ok()).toBe(true);return (await result.json()).pending},{timeout:15000}).toBe(false)}
   await expect(page.getByLabel('修订值',{exact:true})).toHaveCount(0);await memory.getByRole('button',{name:'关闭记忆管理',exact:true}).click();await page.getByRole('button',{name:'查看变化',exact:true}).last().click();const change=page.getByRole('dialog',{name:'理解变化',exact:true});await expect(change).toContainText(OLD);await expect(change).toContainText(NEW);await expect(change).toContainText('未重新评估');await capture(page,info,'revision-committed-pending-analysis');await change.getByRole('button',{name:'返回回答位置',exact:true}).click();await expect(page.locator(`[data-run="${runId}"] .markdown`)).toHaveText(before);
   await send(page,surface==='pages'?'演示：查看当前背景':'原创合成检查：按当前已更正背景继续，不改写旧回答。');await expect(page.locator('article').last().locator('.markdown')).toContainText('周六');await capture(page,info,'new-explicit-attempt-old-history-retained');
  });
  await audit();await metadata(page,browser,info,surface,{coverage:['V02','V03','V04','V05','V07 replay/focus subset','V10 replay subset'],...metrics,attachmentSha256:sha(FILE_TEXT),zeroProvider:await zeroProvider(page,surface),readingAnchorPrecision:'Exact ≤2px drift assertions are owned by the separate anchor-specific suite; this replay checks same-run identity and restored focus'});
 });

 test(`${surface} Continuum narrow reading 1280 1024 390 320 and doubled text capture`,async({page,browser},info)=>{
  test.setTimeout(90000);const audit=await requestAudit(page,info,surface);await open(page,surface);
  for(const viewport of [{width:1280,height:800},{width:1024,height:768},{width:390,height:844},{width:320,height:844}]){
   await page.setViewportSize(viewport);if(viewport.width<960&&await page.locator('.nav-scrim').isVisible())await page.getByRole('button',{name:'关闭侧栏',exact:true}).click();await assertWidth(page);await capture(page,info,`home-${viewport.width}`);
  }
  await send(page,surface==='pages'?'记录：原创窄屏材料，旧安排是周五，仍待核对。':'报告[原创澄]：原创窄屏材料，旧安排是周五，仍待核对。');if(surface==='pages')await send(page,'演示：查看当前背景');
  await page.getByRole('button',{name:'查看依据',exact:true}).last().click();await expect(page.getByRole('dialog',{name:'查看依据'})).toHaveAttribute('aria-modal','true');await capture(page,info,'evidence-320-full-route');await page.getByRole('button',{name:/查看来源 v/}).first().click();await expect(page.getByRole('dialog',{name:'原文'})).toContainText('原创窄屏材料');await capture(page,info,'source-320-full-route');await page.getByRole('button',{name:'返回依据',exact:true}).click();await page.getByRole('button',{name:'返回回答位置',exact:true}).click();await expect(page.getByRole('dialog')).toHaveCount(0);await assertWidth(page);
  await page.setViewportSize({width:1280,height:800});await page.getByRole('button',{name:'查看依据',exact:true}).last().click();await expect(page.getByRole('dialog',{name:'查看依据'})).toHaveAttribute('aria-modal','false');await capture(page,info,'evidence-1280-context');await page.getByRole('button',{name:'返回回答位置',exact:true}).click();
  await page.setViewportSize({width:1024,height:768});await page.getByRole('button',{name:'查看依据',exact:true}).last().click();await expect(page.getByRole('dialog',{name:'查看依据'})).toHaveAttribute('aria-modal','false');await capture(page,info,'evidence-1024-context');await page.getByRole('button',{name:'返回回答位置',exact:true}).click();
  await page.setViewportSize({width:1280,height:800});await page.emulateMedia({reducedMotion:'reduce'});await settings(page,{'动态效果':'static','表面效果':'opaque'});
  // Explicit text-only enlargement harness: record all original computed sizes
  // before applying doubles, avoiding cascading 400% nested text. Not native zoom.
  const scaled=await page.evaluate(()=>{const nodes=[...document.querySelectorAll('.continuum-shell *')].filter(node=>!node.closest('svg,.companion')&&(['INPUT','TEXTAREA','SELECT'].includes(node.tagName)||[...node.childNodes].some(child=>child.nodeType===Node.TEXT_NODE&&child.textContent.trim())));const styles=nodes.map(node=>{const s=getComputedStyle(node);return {node,font:parseFloat(s.fontSize),line:parseFloat(s.lineHeight)}});for(const {node,font,line} of styles){node.style.setProperty('font-size',font*2+'px','important');if(Number.isFinite(line))node.style.setProperty('line-height',line*2+'px','important')}return styles.length});
  expect(scaled).toBeGreaterThan(10);await assertWidth(page);await capture(page,info,'text-200-percent-opaque-reduced-motion');await audit();await metadata(page,browser,info,surface,{coverage:['V08 selected responsive/text-scale captures'],textScale:'200% computed text and line heights, explicitly applied by test harness; native browser zoom not claimed',viewports:['1280x800','1024x768','390x844','320x844'],zeroProvider:await zeroProvider(page,surface)});
 });
}

test('local Continuum committed correction with failed and unknown answer stays truthful',async({page,browser},info)=>{
 test.setTimeout(90000);await open(page,'local');
 for(const outcome of ['failed','unknown']){
  await sidebar(page);await page.getByRole('button',{name:'＋ 新对话',exact:true}).click();await expect(page.locator('article')).toHaveCount(0);await expect(page.getByLabel('上传文本文件')).toBeEnabled();await send(page,`报告[澄]：原创${outcome}旧安排周五`);await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:`原创${outcome}旧安排周五`}).getByRole('button',{name:'内容不对',exact:true}).click();await page.getByLabel('修订值').fill(`原创${outcome}新安排周六`);
  let attempts=0;await page.route('**/v1/conversations/*/events',async route=>{const body=route.request().postDataJSON();if(body.event.type==='revision'){attempts++;body.event.simulation=outcome;await route.continue({postData:JSON.stringify(body)})}else await route.continue()});await page.getByRole('button',{name:'提交更正并更新回答',exact:true}).click();await expect(page.getByLabel('修订值')).toHaveCount(0);await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('article').last()).toContainText('背景变更已提交');await expect(page.locator('article').last()).toContainText(outcome.toUpperCase());await expect(page.locator('article').last()).toContainText('本次回答未完成');expect(attempts).toBe(1);await capture(page,info,`revision-committed-answer-${outcome}`);await page.unroute('**/v1/conversations/*/events');
  await page.getByRole('button',{name:'查看变化',exact:true}).last().click();await expect(page.getByRole('dialog')).toContainText('未重新评估');await capture(page,info,`revision-${outcome}-pending-affected`);await page.getByRole('button',{name:'返回回答位置'}).click();await page.getByRole('button',{name:'记忆管理',exact:true}).click();await expect(page.locator('.memory-card').filter({hasText:`原创${outcome}新安排周六`})).toContainText('ACTIVE');await page.getByRole('button',{name:'关闭记忆管理'}).click();
 }
 await metadata(page,browser,info,'local',{coverage:['V06 committed+failed/unknown actual synthetic simulation'],zeroProvider:await zeroProvider(page,'local')});
});

test('pages Continuum empty evidence ambiguous correction storage failure and removed source',async({page,browser},info)=>{
 await open(page,'pages');await send(page,'2+2');await page.getByRole('button',{name:'查看依据',exact:true}).click();await expect(page.getByRole('dialog')).toContainText('本次没有人物背景依据');await capture(page,info,'evidence-empty');await page.getByRole('button',{name:'返回回答位置'}).click();await send(page,'记录：原创待更正安排周五');await send(page,'更正一下之前的安排');await expect(page.locator('article').last()).toContainText('未猜测或修改');await capture(page,info,'ambiguous-target-no-mutation');
 await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'原创待更正安排周五'}).getByRole('button',{name:'内容不对',exact:true}).click();await page.getByLabel('修订值').fill('原创新安排周六');await page.evaluate(()=>{window.originalSetItem=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new Error('original synthetic storage refusal')}});await page.getByRole('button',{name:'提交更正并更新回答',exact:true}).click();await expect(page.getByLabel('修订值')).toHaveValue('原创新安排周六');await expect(page.getByRole('alert').last()).toBeVisible();await capture(page,info,'failed-write-draft-preserved');await page.evaluate(()=>Storage.prototype.setItem=window.originalSetItem);await page.getByRole('button',{name:'提交更正并更新回答',exact:true}).click();await expect(page.getByLabel('修订值')).toHaveCount(0);await page.getByRole('button',{name:'关闭记忆管理'}).click();await page.getByRole('button',{name:'记忆管理',exact:true}).click();await page.locator('.memory-card').filter({hasText:'原创新安排周六'}).getByRole('button',{name:'删除',exact:true}).click();await page.getByRole('button',{name:'关闭记忆管理'}).click();await expect(page.locator('body')).not.toContainText('原创新安排周六');await capture(page,info,'removed-source-no-resurrection');await metadata(page,browser,info,'pages',{coverage:['V03 empty','V06 ambiguous/failed mutation/removed source'],zeroProvider:await zeroProvider(page,'pages')});
});

test('local Continuum failed source load retains evidence and reduced-motion reversal',async({page,browser},info)=>{
 await page.emulateMedia({reducedMotion:'reduce'});await open(page,'local');await send(page,'报告[澄]：原创来源加载失败演示');const trigger=page.getByRole('button',{name:'查看依据',exact:true}).last();await trigger.click();await page.route('**/v1/sources/*?*',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Original synthetic source temporarily unavailable'})}));await page.getByRole('button',{name:/查看来源 v/}).first().click();await expect(page.getByRole('dialog',{name:'查看依据'})).toBeVisible();await expect(page.getByRole('alert')).toContainText('503');await capture(page,info,'source-load-failed-evidence-retained-reduced-motion');await page.getByRole('button',{name:'返回回答位置'}).click();await expect(trigger).toBeFocused();let release,entered;const gate=new Promise(r=>release=r),waiting=new Promise(r=>entered=r);await page.route('**/v1/answers/*/explain',async route=>{entered();await gate;await route.continue()});await trigger.click();await waiting;await expect(page.getByRole('dialog',{name:'查看依据'})).toContainText('正在读取');await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);release();await expect(trigger).toBeFocused();await page.waitForTimeout(100);await expect(page.getByRole('dialog')).toHaveCount(0);await page.getByRole('button',{name:'搜索对话',exact:true}).hover();await capture(page,info,'reduced-motion-reversal-hover');await page.keyboard.press('Tab');await capture(page,info,'keyboard-focus-visible');await metadata(page,browser,info,'local',{coverage:['V10 failed source load and reduced-motion interruption','V08 hover/focus/disabled/error/selection measured surfaces'],zeroProvider:await zeroProvider(page,'local')});
});

 test('local denied source invalidates cached evidence without a browser notification',async({page,browser},info)=>{
  await open(page,'local');const canary='ORIGINAL_DENIED_SOURCE_CACHE_CANARY';await send(page,'报告[澄]：'+canary);await page.getByLabel('更多消息操作').last().click();await page.getByRole('button',{name:'编辑为新消息'}).click();await expect(page.getByLabel('消息',{exact:true})).toHaveValue('报告[澄]：'+canary);await page.getByRole('button',{name:'查看依据',exact:true}).click();await expect(page.getByRole('dialog')).toContainText(canary);
  const id=await page.locator('.chat-workspace').getAttribute('data-current-conversation');const state=await(await page.request.get(`/v1/conversations/${id}`)).json(),ref=state.runs[0].input_source_ref;
  const result=await page.request.post(`/v1/conversations/${id}/events`,{data:{scope:{conversation_id:id},expected_state_version:state.state_version,idempotency_key:'source-denial-'+Date.now(),event:{type:'revision',text:'原创合成：删除指定来源',revisions:[{action:'DELETE',target_ids:[ref.source_id]}]}}});expect(result.ok()).toBe(true);
  let entered,release;const waiting=new Promise(r=>entered=r),gate=new Promise(r=>release=r);await page.route('**/v1/conversations/'+id,async route=>{entered();await gate;await route.continue()});await page.getByRole('button',{name:/查看来源 v/}).first().click();await waiting;await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.locator('body')).not.toContainText(canary);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');release();await expect(page.getByRole('alert')).toContainText('旧依据已清理');await expect(page.locator('body')).not.toContainText(canary);await expect(page.getByLabel('消息',{exact:true})).toHaveValue('');await capture(page,info,'denied-source-current-policy-cache-cleared');await metadata(page,browser,info,'local',{coverage:['V03/V04 current-policy denial clears cached evidence','R03 out-of-band source deletion does not retain visible derived copy'],zeroProvider:await zeroProvider(page,'local')});
 });
