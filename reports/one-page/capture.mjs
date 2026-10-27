import {chromium} from 'playwright';
import {mkdir,writeFile,copyFile} from 'node:fs/promises';

await mkdir('.impeccable/review',{recursive:true});
const browser=await chromium.launch(),evidence=[];
async function settle(page){
  await page.evaluate(()=>document.fonts.ready);
  await page.waitForFunction(()=>[...document.images].filter(i=>{const r=i.getBoundingClientRect();return r.width&&r.top<innerHeight&&r.bottom>0&&r.left<innerWidth&&r.right>0;}).every(i=>i.complete),{timeout:20000});
}
async function capture(page,name){
  await settle(page);await page.screenshot({path:'.impeccable/review/'+name+'.png',fullPage:true});
  await copyFile('.impeccable/review/'+name+'.png','reports/one-page/'+name+'.png');
  evidence.push({name,...await page.evaluate(()=>({width:innerWidth,height:innerHeight,document_width:document.documentElement.scrollWidth,document_height:document.documentElement.scrollHeight,visible_rows:[...document.querySelectorAll('.fixture-row')].filter(e=>{const r=e.getBoundingClientRect();const pane=document.querySelector('.fixture-list-scroll').getBoundingClientRect();return r.width>0&&r.height>0&&r.top>=Math.max(0,pane.top)&&r.bottom<=Math.min(innerHeight,pane.bottom);}).length,body_scroll:scrollY,fixture_scroll:document.querySelector('.fixture-list-scroll')?.scrollTop??null}))});
}
for(const [width,height,name] of [[1440,900,'desktop'],[1366,768,'user-1366'],[1024,900,'tablet'],[768,900,'user-768'],[390,844,'mobile'],[320,900,'user-320']]){
  const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:5173/?live_date=2026-10-27&league=provider-143');await page.locator('.fixture-row').first().waitFor();
  if(width>=768){await page.locator('.fixture-row').first().click();await page.getByRole('tab',{name:'สรุป',exact:true}).waitFor();}
  await capture(page,name);
  if(width===390){await page.locator('.fixture-row').first().click();await page.getByRole('tab',{name:'สรุป',exact:true}).waitFor();await capture(page,'mobile-analysis');await page.getByRole('tab',{name:'ข้อมูลทีม'}).click();await capture(page,'mobile-team-unknown');await page.getByRole('button',{name:'กลับไปหน้ารายการ'}).click();await page.getByRole('button',{name:'ตัวกรอง',exact:true}).click();await capture(page,'mobile-filters');}
  evidence.at(-1).page_errors=errors;await page.close();
}
const page=await browser.newPage({viewport:{width:1440,height:900}});
await page.goto('http://127.0.0.1:5173/?live_date=2026-10-27');await page.locator('.fixture-row').first().waitFor();await capture(page,'all-competitions');
await page.goto('http://127.0.0.1:5173/?live_date=2026-10-25&league=esp-laliga&live_match=api-football-1570426&analysis_tab=history&last=20&h2h=all');await page.getByRole('heading',{name:'H2H คู่จริง · 19 นัด',exact:true}).waitFor();await capture(page,'legacy-history');
await page.goto('http://127.0.0.1:5173/?view=daily&live_date=2026-10-27');await page.getByRole('heading',{name:'คู่ผ่านเกณฑ์ทดลอง 0 คู่'}).waitFor();await capture(page,'daily-empty');
await page.goto('http://127.0.0.1:5173/?view=results&live_date=2026-10-27');await page.getByRole('heading',{name:'ยังไม่มีคำทำนายล่วงหน้าในระบบ'}).waitFor();await capture(page,'results-empty');
await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:5173/?live_date=2026-10-27&league=provider-143');await page.locator('.fixture-row').first().waitFor();await page.evaluate(()=>document.documentElement.style.fontSize='200%');await capture(page,'mobile-text-200');
await page.locator('.fixture-row').last().scrollIntoViewIfNeeded();await settle(page);
const zoom=await page.locator('.fixture-row').last().evaluate(e=>{const r=e.getBoundingClientRect(),pane=document.querySelector('.fixture-list-scroll');return {body_height:document.documentElement.scrollHeight,viewport_height:innerHeight,scroll_y:scrollY,pane_height:pane.clientHeight,last_row_top:r.top,last_row_bottom:r.bottom,last_row_visible:r.top>=0&&r.bottom<=innerHeight};});
await page.screenshot({path:'.impeccable/review/mobile-text-200-reading.png'});await copyFile('.impeccable/review/mobile-text-200-reading.png','reports/one-page/mobile-text-200-reading.png');await writeFile('reports/one-page/zoom-reading.json',JSON.stringify(zoom,null,2));
await browser.close();await writeFile('reports/one-page/layout-verification.json',JSON.stringify(evidence,null,2));
console.log(JSON.stringify(evidence));
