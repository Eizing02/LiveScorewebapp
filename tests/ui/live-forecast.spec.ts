import {expect,test} from '@playwright/test';

test('isolated synthetic UI responses expose forecast markets, scorelines and daily rankings',async({page})=>{
  const empty={n:0,wins:0,draws:0,losses:0,average_for:null,average_against:null,form:[],matches:[]};
  const analysis={probabilities:[.8,.1,.1],home_rate:1.8,away_rate:.7,markets:{'over_2.5':.45,'under_2.5':.55,btts_yes:.5},scorelines:[{home:2,away:1,probability:.13}],generated_at:'2026-10-27T12:00:00Z',model_version:'synthetic-ui-test-only',cutoff_date:'2026-10-26'};
  await page.route(/\/api\/(?:live|program)\//,async route=>{
    const path=new URL(route.request().url()).pathname;
    const body=path.includes('/analysis/')?{fixture:{home:'Unit Home',away:'Unit Away',league_name:'Unit League',mapping_status:'synthetic'},analysis,state:'snapshot_available',history:{cutoff_date_exclusive:'2026-10-27',home:empty,away:empty,home_venue:empty,away_venue:empty,h2h:empty},context:{availability:{known:false},lineups:{confirmed:false},provider_forecast:{probabilities:null},past_xg:{home:{n:0,xg_for_mean:null},away:{n:0,xg_for_mean:null}}},recorded_enrichments:[]}:path.endsWith('/daily')?{picks:[{fixture_id:'api-football-900000001',home:'Unit Home',away:'Unit Away',league_name:'Unit League',market:'1x2',outcome:'home',probability:.8,passed:true}],bundles:[],goal_ranking:[{fixture_id:'api-football-900000001',home:'Unit Home',away:'Unit Away',expected_total:2.5,over25:.45}],limitations:[]}:{date:'2026-10-28',total:0,round_total:0,page:1,pages:1,competitions:[],countries:[],source_dates:[],items:[],captured_at:'2026-10-27T12:00:00Z',known_source_dates:['2026-10-28'],data_completeness:'partial_source_dates'};
    await route.fulfill({json:body});
  });
  await page.goto('/?view=provider&live_date=2026-10-28&live_match=api-football-900000001');
  const dialog=page.getByRole('article',{name:'วิเคราะห์คู่จริง'});await expect(dialog.getByText('2–1',{exact:true})).toBeVisible();
  await page.getByRole('tab',{name:'ประตู',exact:true}).click();
  await expect(dialog.getByRole('cell',{name:'55.0%',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'กลับไปหน้ารายการ'}).click();
  await page.getByRole('button',{name:'คู่เด่น',exact:true}).click();
  await expect(page.getByRole('cell',{name:'80.0%',exact:true})).toBeVisible();
  await expect(page.getByRole('cell',{name:'2.50',exact:true})).toBeVisible();
  await expect(page.getByRole('cell',{name:'45.0%',exact:true})).toBeVisible();
});
