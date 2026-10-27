import {test,expect} from '@playwright/test';
test('research filtering explains selections, abstentions and insufficient evidence on desktop/mobile',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?view=research&panel=matches');await page.getByRole('button',{name:'การคัดกรองเดิม',exact:true}).click();
  await expect(page.getByText('67 / 1,066',{exact:true})).toBeVisible();await expect(page.getByText('57 / 67',{exact:true})).toBeVisible();
  await expect(page.getByText('งานวิจัย · ยังไม่ผ่านการยืนยัน',{exact:true})).toBeVisible();
  await page.locator('.filter-panel').evaluate(element=>element.scrollIntoView({block:'start'}));
  await page.screenshot({path:'reports/selection-v1/filtering-overview.png'});
  await page.getByLabel('ลีกของผลคัดกรอง').selectOption('en.1');await expect(page.getByText('หน้า 1/1 · 10 รายการ')).toBeVisible();
  await page.getByRole('button',{name:/^เหตุผล /}).first().click();await expect(page.getByRole('dialog',{name:'เหตุผลการคัดกรองรายคู่'})).toBeVisible();await expect(page.getByText('ประวัติที่รู้ก่อนเกม',{exact:true})).toBeVisible();
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByLabel('สถานะการคัด').selectOption('rejected');await expect(page.getByText('โอกาสหลัง calibration').first()).toBeVisible();await page.getByRole('button',{name:/^เหตุผล /}).first().click();await expect(page.getByText('โอกาสหลัง calibration ต่ำกว่าเกณฑ์',{exact:true})).toBeVisible();await page.getByLabel('ปิดเหตุผลการคัดกรอง').click();
  await page.getByText('ดูการทดลองทั้ง 12 กติกาบน validation',{exact:true}).click();await expect(page.getByText('กติกาที่เลือกไว้ก่อน test',{exact:true})).toBeVisible();
  await page.screenshot({path:'reports/selection-v1/filtering-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:'reports/selection-v1/filtering-mobile.png',fullPage:true});expect(errors).toEqual([]);
});
