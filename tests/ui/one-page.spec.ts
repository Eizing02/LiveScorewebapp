import {test,expect} from '@playwright/test';
test('cached global catalogue exposes other cups, paginates and filters on the server',async({page})=>{
  const response=await page.request.get('/api/program/fixtures?date=2026-10-27');test.skip(!response.ok(),'Private programme catalogue is not enabled in this environment.');
  const data=await response.json() as {round_total:number;total:number;pages:number};
  await page.goto('/?live_date=2026-10-27');await expect(page.locator('.fixture-row')).toHaveCount(Math.min(25,data.total));await expect(page.locator('.result-count')).toContainText(String(data.round_total));
  const first=await page.locator('.fixture-row').first().getAttribute('id');if(data.pages>1){await page.getByRole('button',{name:'ถัดไป',exact:true}).click();await expect(page).toHaveURL(/page=2/);await expect.poll(()=>page.locator('.fixture-row').first().getAttribute('id')).not.toBe(first);}
  await page.getByRole('button',{name:/Copa del Rey/}).first().click();await expect(page).toHaveURL(/league=provider-143/);await expect(page.locator('.fixture-league')).toHaveCount(1);await expect(page.locator('.fixture-league h2')).toContainText('Copa del Rey');await page.locator('.fixture-row').first().click();await expect(page.getByRole('article',{name:'วิเคราะห์คู่จริง'})).toContainText('รายการนี้ยังไม่มีโมเดลที่ผ่านการตรวจสอบ');
  expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight)).toBe(true);
});
test('following competitions persists without hiding the all-competitions view',async({page})=>{
  const response=await page.request.get('/api/program/fixtures?date=2026-10-27');test.skip(!response.ok(),'Private programme catalogue not prepared.');
  const data=await response.json() as {round_total:number};
  await page.goto('/?live_date=2026-10-27');const star=page.locator('.competition-pane').getByRole('button',{name:'ติดตาม Spain Copa del Rey',exact:true});await expect(star).toBeVisible();await star.click();await expect(star).toHaveAttribute('aria-pressed','true');await page.getByRole('button',{name:'ลีกติดตาม',exact:true}).click();await expect(page.locator('.fixture-league')).toHaveCount(1);await page.reload();await expect(page.locator('.fixture-league')).toHaveCount(1);await page.getByRole('button',{name:'ทั้งหมด',exact:true}).click();await expect(page.locator('.result-count')).toContainText(String(data.round_total));
});

test('sidebar, mobile filter and fixture groups share the server league order',async({page})=>{
  const response=await page.request.get('/api/program/fixtures?date=2026-10-25');test.skip(!response.ok(),'Private programme catalogue not prepared.');
  const data=await response.json() as {total:number;competitions:{provider_id:number;name:string;country:string}[];items:{league_id:string;league_name:string;country:string}[]};
  const majors=[39,140,135,78,61].filter(id=>data.competitions.some(c=>c.provider_id===id));
  expect(data.competitions.slice(0,majors.length).map(c=>c.provider_id)).toEqual(majors);
  const groups=[...new Map(data.items.map(f=>[f.league_id,`${f.country} ${f.league_name}`])).values()];
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:900});await page.goto('/?live_date=2026-10-25');await expect(page.locator('.fixture-row')).toHaveCount(Math.min(25,data.total));
    await expect.poll(()=>page.locator('.fixture-league').evaluateAll(elements=>elements.map(e=>e.getAttribute('aria-label')))).toEqual(groups);
    if(width===1440)await expect(page.locator('.competition-choice>button:first-child>span:not(.brand-logo)')).toHaveText(data.competitions.map(c=>c.name+c.country));
    await page.getByRole('button',{name:'ตัวกรอง',exact:true}).click();await expect(page.getByLabel('ลีกคู่จริง').locator('option')).toHaveText(['ทุกรายการ',...data.competitions.map(c=>`${c.country} · ${c.name}`)]);
    await page.getByRole('button',{name:'เสร็จสิ้น'}).click();
    await page.screenshot({path:`reports/league-order/${width===1440?'desktop':'mobile'}.png`,fullPage:true});
  }
});
