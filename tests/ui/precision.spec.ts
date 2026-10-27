import {test,expect} from '@playwright/test';

test('precision evidence keeps coverage, uncertainty and failed gates visible',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?view=research&panel=matches');await page.getByRole('button',{name:'เป้าความแม่นยำ',exact:true}).click();
  await expect(page.getByRole('heading',{name:'เป้าความแม่นยำ 70–80% ของคู่ที่คัด'})).toBeVisible();
  await expect(page.getByText('103 ถูก / 121 คู่',{exact:true})).toBeVisible();
  await expect(page.getByText('85.12%',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('3.76%',{exact:true}).first()).toBeVisible();
  await expect(page.getByText('77.71–90.38%',{exact:true})).toBeVisible();
  await expect(page.getByRole('cell',{name:'0.6819',exact:true})).toBeVisible();
  await page.screenshot({path:'reports/precision-v3/precision-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'reports/precision-v3/precision-mobile.png',fullPage:true});
  await page.getByLabel('ช่วงประเมินความแม่นยำ').selectOption('current_season_audit');
  await expect(page.getByText('11 ถูก / 13 คู่',{exact:true})).toBeVisible();
  await expect(page.getByText('13 จาก 556 คู่ทั้งหมด',{exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});
