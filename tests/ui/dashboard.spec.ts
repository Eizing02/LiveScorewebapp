import {test,expect} from '@playwright/test';
test('Thai mock dashboard, details, real holdout and data quality',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/?view=research&panel=matches');await expect(page.getByText('17,027',{exact:true})).toBeVisible();
  await page.screenshot({path:'reports/dashboard-desktop.png',fullPage:true});
  await page.getByLabel('เลือกลีก').selectOption('eng-premier');
  await expect(page.locator('.match-card')).toHaveCount(1);await page.locator('.match-card').click();
  await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByText('ประตูคาดหมายของแบบจำลอง')).toBeVisible();await page.getByLabel('ปิดรายละเอียด').click();
  await page.getByRole('button',{name:'ผล Backtest เดิม'}).click();await expect(page.getByRole('cell',{name:'0.9973',exact:true})).toBeVisible();
  await page.screenshot({path:'reports/performance-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'คุณภาพข้อมูล',exact:true}).click();await expect(page.getByText('หลักฐานเดิมยังคงกัก 66 นัด EPL 2019/20 และพักทั้งฤดูกาล', {exact:false})).toBeVisible();
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'คู่แข่งขันจำลอง',exact:true}).click();await expect(page.locator('.match-card').first()).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);expect(errors).toEqual([]);
  await page.screenshot({path:'reports/dashboard-mobile.png',fullPage:true});
});
