import { chromium } from '@playwright/test';
import { writeFileSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
const out = { recorded_at:new Date().toISOString(), source_hashes:Object.fromEntries(['App.tsx','ProviderPreview.tsx','style.css','centre.css'].map(f=>[f,createHash('sha256').update(readFileSync('apps/web/src/'+f)).digest('hex')])), viewports:[] };
const browser=await chromium.launch({headless:true});
for(const width of [1440,390,320]) {
 const context=await browser.newContext({viewport:{width,height:900},locale:'th-TH'});
 const page=await context.newPage(); const requests=[], consoleErrors=[], blocked=[];
 await page.route('**/*', route=>{const u=new URL(route.request().url()); if(['127.0.0.1','localhost'].includes(u.hostname))return route.continue();blocked.push(u.origin);return route.abort();});
 page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 page.on('pageerror',e=>consoleErrors.push(e.message));
 await page.goto('http://127.0.0.1:5173/?view=provider&live_date=2026-10-25',{waitUntil:'networkidle'});
 await page.locator('.provider-preview').waitFor();
 const metrics=await page.evaluate(()=>{
 const info=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return {tag:e.tagName,text:e.textContent.trim().slice(0,110),x:r.x,y:r.y,width:r.width,height:r.height,fontSize:s.fontSize,lineHeight:s.lineHeight,color:s.color,background:s.backgroundColor,outline:s.outline,ariaLabel:e.getAttribute('aria-label'),ariaCurrent:e.getAttribute('aria-current'),ariaPressed:e.getAttribute('aria-pressed'),tabindex:e.getAttribute('tabindex')};};
 return {url:location.href,title:document.title,viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,headings:[...document.querySelectorAll('h1,h2,h3')].map(info),nav:[...document.querySelectorAll('nav button')].map(info),controls:[...document.querySelectorAll('input,select,.filter-toolbar button')].map(info),firstLink:info(document.querySelector('.provider-league .text-button')),firstAnalysis:info(document.querySelector('.provider-league td:last-child .text-button')),tables:[...document.querySelectorAll('.table-wrap')].map(e=>({box:info(e),clientWidth:e.clientWidth,scrollWidth:e.scrollWidth,tabindex:e.getAttribute('tabindex'),role:e.getAttribute('role')})),typography:[...document.querySelectorAll('.intro p,.stats small,.stats span,.notice,label,th,td,footer')].slice(0,32).map(info),fonts:[...document.fonts].map(f=>({family:f.family,status:f.status})),fontCheck:document.fonts.check('16px "IBM Plex Sans Thai"'),images:[...document.images].map(i=>({src:i.getAttribute('src'),loading:i.loading,alt:i.alt})),resource:performance.getEntriesByType('resource').map(e=>({name:e.name,initiator:e.initiatorType,duration:e.duration,transferSize:e.transferSize,decodedBodySize:e.decodedBodySize})),navTiming:performance.getEntriesByType('navigation').map(e=>({domContentLoaded:e.domContentLoadedEventEnd,load:e.loadEventEnd})),paint:performance.getEntriesByType('paint').map(e=>({name:e.name,start:e.startTime})),status:document.querySelector('[role="status"]')?.textContent??null};
 });
 const focus=[];
 for(let i=0;i<18;i++){await page.keyboard.press('Tab');focus.push(await page.evaluate(()=>{const e=document.activeElement,s=getComputedStyle(e),r=e.getBoundingClientRect();return {tag:e.tagName,text:e.textContent.trim().slice(0,80),ariaLabel:e.getAttribute('aria-label'),outline:s.outline,outlineOffset:s.outlineOffset,x:r.x,y:r.y,width:r.width,height:r.height,scrollX:scrollX,scrollY:scrollY};}));}
 out.viewports.push({width,metrics,focus,requests,consoleErrors,blocked}); await context.close();
}
await browser.close();
writeFileSync('reports/impeccable/assessment-b-evidence.json',JSON.stringify(out,null,2));
console.log(JSON.stringify(out,null,2));
