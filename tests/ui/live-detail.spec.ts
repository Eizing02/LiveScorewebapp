import {test,expect} from '@playwright/test';
test('real details filter H2H and disclose missing forecasts without a provider call',async({page})=>{
  const status=await page.request.get('/api/program/fixtures?date=2026-10-25');
  // No live cache or credentials are needed in CI; API/DB unit tests cover that case.
  if(status.status()===409){await page.goto('/?view=provider');await expect(page.getByRole('heading',{level:1})).toBeVisible();return;}
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?view=provider&live_date=2026-10-25&live_match=api-football-1570426');
  const dialog=page.getByRole('article',{name:'วิเคราะห์คู่จริง'});await expect(dialog).toBeVisible();
  await expect(dialog.getByText('เกมเริ่มไปแล้วขณะประมวลผล',{exact:false})).toBeVisible();
  await page.getByRole('tab',{name:'ฟอร์ม–H2H'}).click();
  await page.getByLabel('เกมย้อนหลังคู่จริง').selectOption('20');
  await expect(dialog.getByRole('heading',{name:'H2H คู่จริง · 9 นัด',exact:true})).toBeVisible();
  await page.getByLabel('รายการ H2H คู่จริง').selectOption('all');
  await expect(dialog.getByRole('heading',{name:'H2H คู่จริง · 19 นัด',exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'ข้อมูลทีม'}).click();
  await expect(dialog.getByText('Missing 9',{exact:false})).toBeVisible();
  await expect(dialog.getByText('เหย้า 45.0% · เสมอ 45.0% · เยือน 10.0%',{exact:true})).toBeVisible();
  await page.screenshot({path:'reports/live-research/live-detail-desktop.png'});
  const link=page.url();await page.getByRole('button',{name:'กลับไปหน้ารายการ'}).click();await expect(dialog).toHaveCount(0);
  await page.goto(link);await expect(dialog).toBeVisible();
  await page.setViewportSize({width:390,height:844});await dialog.evaluate(node=>{node.scrollTop=0;});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'reports/live-research/live-detail-mobile.png'});
  await page.getByRole('button',{name:'กลับไปหน้ารายการ'}).click();await page.getByRole('button',{name:'คู่เด่น',exact:true}).click();
  await expect(page.getByText('คู่ผ่านเกณฑ์ทดลอง 0 คู่',{exact:true})).toBeVisible();expect(errors).toEqual([]);
});
