import {test,expect} from '@playwright/test';
test('provider schedule opens by default and keeps nullable scores and dated evidence',async({page})=>{
  const response=await page.request.get('/api/program/fixtures?date=2026-10-25');
  await page.goto('/?live_date=2026-10-25');
  await expect(page.getByRole('heading',{name:'โปรแกรมแข่งขัน',exact:true})).toBeVisible();
  await expect(page.locator('.match-card')).toHaveCount(0);
  if(response.ok()){
    const data=await response.json() as {items:{league_id:string}[]};
    await expect(page.locator('.fixture-row')).toHaveCount(data.items.length);
    await expect(page.locator('.fixture-league')).toHaveCount(new Set(data.items.map(f=>f.league_id)).size);
    await expect(page.getByText('สกอร์และสถานะ ณ เวลาบันทึก',{exact:false})).toBeVisible();
    await page.screenshot({path:'reports/one-page/program-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:'reports/one-page/program-mobile.png',fullPage:true});
  }else await expect(page.getByRole('alert')).toContainText('เครื่องนี้ยังไม่เปิดอ่านข้อมูลโปรแกรมจริง');
});
