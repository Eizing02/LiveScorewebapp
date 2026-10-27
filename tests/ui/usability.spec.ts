import {test,expect,type Page} from '@playwright/test';
const fixtures=[
  {id:'api-football-900000001',league_id:'eng-premier',league_name:'Premier League',country:'England',provider_league_id:39,home_provider_id:40,away_provider_id:51,home:'Unit Home Football Club With A Long Name',away:'Unit Away',kickoff_utc:'2026-10-27T23:30:00Z',business_date:'2026-10-27',status:'scheduled',analysis:null,score_90:null,current_score:null},
  {id:'api-football-900000002',league_id:'ita-serie-a',league_name:'Serie A',country:'Italy',provider_league_id:135,home:'Unit Milan',away:'Unit Rome',kickoff_utc:'2026-10-27T12:00:00Z',business_date:'2026-10-27',status:'finished',analysis:null,score_90:[0,0],current_score:[0,0]}
];
const empty={n:0,wins:0,draws:0,losses:0,average_for:null,average_against:null,form:[],matches:[]};
async function mock(page:Page){
  await page.route(/\/api\/(?:program|live)\//,async route=>{
    const url=new URL(route.request().url()),params=url.searchParams;
    const items=fixtures.filter(f=>(!params.get('q')||f.home.toLowerCase().includes(params.get('q')!.toLowerCase()))&&(params.get('league')==='all'||!params.get('league')||params.get('league')===f.league_id));
    const body=url.pathname.includes('/analysis/')?{fixture:fixtures[0],analysis:null,state:'insufficient_data',history:{cutoff_date_exclusive:'2026-10-27',home:empty,away:empty,home_venue:empty,away_venue:empty,h2h:empty},context:{availability:{known:false},lineups:{confirmed:false},provider_forecast:{probabilities:null},past_xg:{home:{n:0,xg_for_mean:null},away:{n:0,xg_for_mean:null}}},recorded_enrichments:[]}:url.pathname.endsWith('/results')?{items:[],next_offset:null}:url.pathname.endsWith('/evidence')?{prospective_evaluation:{settled_primary_n:0,accuracy:null}}:{date:'2026-10-27',total:items.length,round_total:2,page:1,pages:1,items,competitions:[{id:'eng-premier',provider_id:39,name:'Premier League',country:'England',n:1},{id:'ita-serie-a',provider_id:135,name:'Serie A',country:'Italy',n:1}],countries:['England','Italy'],source_dates:[{date:'2026-10-27',state:'recorded'},{date:'2026-10-28',state:'not_fetched'}],captured_at:'2026-10-25T10:00:00Z',known_source_dates:['2026-10-27'],data_completeness:'partial_source_dates'};
    await route.fulfill({json:body});
  });
}
test('real default, URL filters and browser Back preserve the same workspace',async({page})=>{
  await mock(page);await page.goto('/?live_date=2026-10-27');
  await expect(page.getByRole('button',{name:'โปรแกรม',exact:true})).toHaveAttribute('aria-current','page');
  await expect(page.locator('.fixture-row')).toHaveCount(2);await expect(page.locator('.match-card')).toHaveCount(0);
  await page.getByRole('button',{name:'ตัวกรอง',exact:true}).click();await page.getByLabel('ลีกคู่จริง').selectOption('eng-premier');
  await page.getByRole('button',{name:'เสร็จสิ้น'}).click();await page.getByRole('searchbox',{name:'ค้นหาทีม'}).fill('Unit Home');
  await expect(page.locator('.fixture-row')).toHaveCount(1);await expect(page).toHaveURL(/league=eng-premier/);
  await page.locator('.fixture-row').click();await expect(page.getByRole('article',{name:'วิเคราะห์คู่จริง'})).toBeVisible();
  const contrast=await page.locator('.fixture-row').evaluate(e=>{const s=getComputedStyle(e),lum=(c:string)=>{const [r,g,b]=c.match(/[\d.]+/g)!.slice(0,3).map(Number).map(v=>{const x=v/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;});return .2126*r+.7152*g+.0722*b;};const a=lum(s.color),b=lum(s.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);});expect(contrast).toBeGreaterThanOrEqual(4.5);
  await expect(page.locator('.fixture-row')).toBeVisible();
  await page.getByRole('tab',{name:'ฟอร์ม–H2H'}).click();await expect(page.getByRole('heading',{name:'ฟอร์มและการพบกัน'})).toBeVisible();
  await page.goBack();await expect(page.getByRole('article',{name:'วิเคราะห์คู่จริง'})).toHaveCount(0);await expect(page.locator('.fixture-row')).toBeFocused();
  await expect(page.getByRole('searchbox')).toHaveValue('Unit Home');await page.reload();await expect(page.locator('.fixture-row')).toHaveCount(1);
});
test('nullable scores, stale status, partial coverage and image failure stay truthful',async({page})=>{
  await mock(page);await page.route('**/media/teams/40.png',r=>r.abort());await page.goto('/?live_date=2026-10-27');
  await expect(page.locator('.source-strip')).toContainText('ข้อมูลเก่า');await expect(page.locator('.coverage-note')).toContainText('รอบนี้ยังไม่ครบ');
  await expect(page.locator('.fixture-row').first().locator('.fixture-score b')).toHaveCount(0);
  await expect(page.locator('.fixture-row').nth(1).locator('.fixture-score b')).toHaveText(['0','0']);
  await expect(page.locator('.fixture-row').first().locator('.logo-fallback')).toHaveCount(1);
});
test('cache error has a retry and never substitutes mock fixtures',async({page})=>{
  let calls=0;await page.route('**/api/program/fixtures?**',r=>{calls++;return r.fulfill({status:503,json:{error:'test_unavailable'}});});
  await page.goto('/');await expect(page.getByRole('alert')).toContainText('ยังเปิดโปรแกรมไม่ได้');await expect(page.locator('.fixture-row,.match-card')).toHaveCount(0);const before=calls;
  await page.getByRole('button',{name:'ลองอีกครั้ง'}).click();await expect.poll(()=>calls).toBeGreaterThan(before);
});
test('results keep absent accuracy distinct from zero percent',async({page})=>{
  await mock(page);await page.goto('/?view=results');await expect(page.getByRole('heading',{name:'ยังไม่มีคำทำนายล่วงหน้าในระบบ'})).toBeVisible();await expect(page.locator('.evaluation-summary')).toContainText('ยังไม่มีผล');await expect(page.locator('.evaluation-summary')).not.toContainText('0.0%');
});
test('panes stay inside mobile, tablet and desktop windows with readable long names',async({page})=>{
  await mock(page);await page.emulateMedia({reducedMotion:'reduce'});
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});await page.goto('/?live_date=2026-10-27');await expect(page.locator('.fixture-row')).toHaveCount(2);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight)).toBe(true);
    expect(await page.locator('.fixture-row').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize))).toBeGreaterThanOrEqual(16);
    const action=await page.locator('.fixture-row').first().locator('.fixture-action').boundingBox();expect(action!.x+action!.width).toBeLessThanOrEqual(width);
  }
  await page.setViewportSize({width:390,height:900});await page.locator('.fixture-row').first().click();await expect(page.getByRole('article',{name:'วิเคราะห์คู่จริง'})).toBeVisible();await expect(page.locator('.fixtures-pane')).not.toBeVisible();
  await page.getByRole('tab',{name:'ฟอร์ม–H2H'}).click();await page.keyboard.press('ArrowRight');await expect(page.getByRole('tab',{name:'ประตู',exact:true})).toHaveAttribute('aria-selected','true');
  await page.getByRole('button',{name:'กลับไปหน้ารายการ'}).click();await expect(page.locator('.fixtures-pane')).toBeVisible();
  await page.evaluate(()=>{document.documentElement.style.fontSize='200%';});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(await page.locator('.fixture-list-scroll').evaluate(e=>e.clientHeight)).toBeGreaterThanOrEqual(160);
  const zoomRow=page.locator('.fixture-row').first();const time=await zoomRow.locator('.fixture-time time').boundingBox(),home=await zoomRow.locator('.fixture-home').boundingBox();expect(time!.x+time!.width).toBeLessThanOrEqual(home!.x);
  await page.locator('.fixture-row').last().scrollIntoViewIfNeeded();await expect(page.locator('.fixture-row').last()).toBeInViewport();await page.locator('.fixture-row').last().click();await page.getByRole('tab',{name:'ฟอร์ม–H2H'}).scrollIntoViewIfNeeded();await expect(page.getByRole('tab',{name:'ฟอร์ม–H2H'})).toBeInViewport();
});
test('league headings show counts and accessible collapse state that survives reload',async({page})=>{
  await mock(page);await page.setViewportSize({width:390,height:844});await page.goto('/?live_date=2026-10-27');await expect(page.locator('.league-match-count').first()).toHaveText('1 คู่');
  const fold=page.getByRole('button',{name:'พับ England Premier League',exact:true});await fold.click();await expect(page.getByRole('button',{name:'แสดง England Premier League',exact:true})).toHaveAttribute('aria-expanded','false');await expect(page.locator('.fixture-row:visible')).toHaveCount(1);
  await page.reload();await expect(page.locator('.fixture-row:visible')).toHaveCount(1);await page.getByRole('button',{name:'แสดง England Premier League',exact:true}).click();await expect(page.locator('.fixture-row:visible')).toHaveCount(2);
});
test('keyboard entry provides a skip link and visible focus',async({page})=>{
  await mock(page);await page.goto('/');await page.keyboard.press('Tab');await expect(page.getByRole('link',{name:'ข้ามไปเนื้อหา'})).toBeFocused();await page.keyboard.press('Enter');await page.keyboard.press('Tab');expect(await page.locator(':focus').evaluate(e=>getComputedStyle(e).outlineStyle)).toBe('solid');
});
