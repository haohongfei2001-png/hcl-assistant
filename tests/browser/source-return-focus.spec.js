import {test,expect} from '@playwright/test';

test('local source return restores committed focus without waiting for an animation frame',async({page})=>{
 await page.goto('/');
 const composer=page.getByLabel('消息',{exact:true});
 await composer.fill('报告[澄]：原创焦点回归合成材料');
 await page.getByRole('button',{name:'发送',exact:true}).click();
 await page.getByRole('button',{name:'查看依据',exact:true}).click();
 const evidence=page.getByRole('dialog',{name:'查看依据',exact:true});
 const sourceButton=evidence.getByRole('button',{name:/查看来源 v/}).first();
 await sourceButton.click();
 const source=page.getByRole('dialog',{name:'原文',exact:true});
 await expect(source).toContainText('原创焦点回归合成材料');
 const back=source.getByRole('button',{name:'返回依据',exact:true});
 await back.focus();
 // Model an animation-frame callback deferred beyond React's commit. The
 // source button must receive focus from its committed component lifecycle.
 await page.evaluate(()=>{
  window.originalFocusRAF=window.requestAnimationFrame;
  window.requestAnimationFrame=()=>0;
 });
 try{
  await page.keyboard.press('Enter');
  await expect(evidence).toBeVisible();
  await expect(sourceButton).toHaveAttribute('aria-current','true');
  await expect(sourceButton).toBeFocused();
 }finally{
  await page.evaluate(()=>{window.requestAnimationFrame=window.originalFocusRAF;delete window.originalFocusRAF});
 }
 // A later unrelated render must not repeatedly steal the user's focus.
 await composer.fill('独立的新草稿');
 await expect(composer).toBeFocused();
 await expect(composer).toHaveValue('独立的新草稿');
});
