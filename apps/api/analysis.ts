import {z} from 'zod';
import type {Env} from './types';
import type {AnalysisSnapshot,CentreFixture,HistoryMatch,TeamSummary,ResearchReport} from '../../packages/football/types';
import {buildDailyReport} from '../../packages/football/selection';
import {currentRound,roundWindow,type Period} from '../../packages/football/window';
import {evaluateReport,type ResultState} from '../../packages/football/settlement';

const send=(v:unknown,status=200)=>Response.json(v,{status,headers:{'cache-control':'no-store','x-content-type-options':'nosniff'}});
const querySchema=z.object({date:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),period:z.enum(['day','night']).default('day'),league:z.string().regex(/^[a-z-]{1,40}$/).optional(),page:z.coerce.number().int().min(1).max(100).default(1)});
function query(url:URL){const params=querySchema.parse({date:url.searchParams.get('date')??currentRound(),period:url.searchParams.get('period')??'day',league:url.searchParams.get('league')??undefined,page:url.searchParams.get('page')??1});return {...params,window:roundWindow(params.date,params.period)};}
export async function checksum(value:string){const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));return Array.from(new Uint8Array(bytes)).map(v=>v.toString(16).padStart(2,'0')).join('');}
const fixtureSelect=`SELECT f.id,f.league_id,l.name AS league_name,h.name AS home,a.name AS away,f.home_id,f.away_id,f.kickoff_utc,f.match_date,f.status,f.source,f.quality FROM fixtures f JOIN leagues l ON l.id=f.league_id JOIN teams h ON h.id=f.home_id JOIN teams a ON a.id=f.away_id`;
async function attach(env:Env,fixtures:Omit<CentreFixture,'analysis'>[],now:number,snapshotId?:string){
  const pointer=snapshotId?null:await env.DB.prepare("SELECT value FROM settings WHERE key='RECENT_RESEARCH_CANDIDATE'").first<{value:string}>(),snapshots=new Map<string,AnalysisSnapshot>();
  if(!snapshotId&&!pointer)return fixtures.map(f=>({...f,analysis:null}));
  // At most 82 bound parameters and 13 chunk queries for a capped 1,000-fixture round.
  for(let start=0;start<fixtures.length;start+=80){const ids=fixtures.slice(start,start+80).map(f=>f.id);const rows=await env.DB.prepare(`SELECT fixture_id,payload,checksum FROM (SELECT fixture_id,payload,checksum,ROW_NUMBER() OVER(PARTITION BY fixture_id ORDER BY generated_at DESC,id DESC) AS choice FROM analysis_snapshots WHERE fixture_id IN (${ids.map(()=>'?').join(',')}) AND generated_at<=? AND ${snapshotId?'id=?':'model_version=?'}) WHERE choice=1`).bind(...ids,new Date(now).toISOString(),snapshotId??pointer!.value).all<{fixture_id:string;payload:string;checksum:string}>();for(const row of rows.results){if(await checksum(row.payload)!==row.checksum)throw new Error('analysis_checksum_mismatch');snapshots.set(row.fixture_id,JSON.parse(row.payload) as AnalysisSnapshot);}}
  return fixtures.map(f=>({...f,analysis:snapshots.get(f.id)??null}));
}
async function windowFixtures(env:Env,date:string,period:Period,now:number){const w=roundWindow(date,period);const rows=await env.DB.prepare(fixtureSelect+" WHERE f.source='mock_centre' AND f.kickoff_utc>=? AND f.kickoff_utc<? ORDER BY f.kickoff_utc,f.id LIMIT 1001").bind(w.start,w.end_exclusive).all<Omit<CentreFixture,'analysis'>>();if(rows.results.length>1000)throw new Error('fixture_window_too_large');return attach(env,rows.results,now);}
const historySelect=`SELECT r.id,r.league_id,l.name AS league_name,r.season,r.match_date,r.home_id,r.away_id,h.name AS home,a.name AS away,r.home_goals,r.away_goals,r.quality FROM recent_results r JOIN leagues l ON l.id=r.league_id JOIN teams h ON h.id=r.home_id JOIN teams a ON a.id=r.away_id`;
export function summarize(rows:HistoryMatch[],team:string):TeamSummary{
  let wins=0,draws=0,losses=0,gf=0,ga=0,over=0,btts=0,clean=0;const form:string[]=[];
  for(const row of rows){const h=row.home_id===team,scored=h?row.home_goals:row.away_goals,conceded=h?row.away_goals:row.home_goals;gf+=scored;ga+=conceded;if(scored>conceded){wins++;form.push('W');}else if(scored===conceded){draws++;form.push('D');}else{losses++;form.push('L');}if(scored+conceded>2.5)over++;if(scored>0&&conceded>0)btts++;if(conceded===0)clean++;}
  return {n:rows.length,wins,draws,losses,goals_for:gf,goals_against:ga,average_for:rows.length?gf/rows.length:null,average_against:rows.length?ga/rows.length:null,over25:rows.length?over/rows.length:null,btts:rows.length?btts/rows.length:null,clean_sheets:clean,form,matches:rows};
}
export async function createReport(env:Env,date:string,period:Period,now=Date.now()){if(env.MOCK_MODE!=='true')throw new Error('live_daily_report_not_approved');return buildDailyReport(await windowFixtures(env,date,period,now),date,period,now);}
export async function lockDailyReport(env:Env,date:string,period:Period,now=Date.now()){
  const report=await createReport(env,date,period,now);if(report.picks.some(p=>Date.parse(p.kickoff_utc)<=now))throw new Error('cannot_lock_round_after_first_kickoff');report.locked=true;report.id+=':'+(await checksum(JSON.stringify(report))).slice(0,16);const payload=JSON.stringify(report),hash=await checksum(payload);
  await env.DB.prepare('INSERT OR IGNORE INTO daily_report_snapshots VALUES(?,?,?,?,?,?,?,?)').bind(report.id,date,period,report.generated_at,report.policy_version,payload,hash,'mock_research').run();
  return report;
}
export async function evaluateDailyReport(env:Env,id:string,now=Date.now()){
  if(env.MOCK_MODE!=='true')throw new Error('live_evaluation_not_approved');
  const row=await env.DB.prepare('SELECT payload,checksum FROM daily_report_snapshots WHERE id=?').bind(id).first<{payload:string;checksum:string}>();if(!row||await checksum(row.payload)!==row.checksum)throw new Error('missing_or_invalid_report');
  const report=JSON.parse(row.payload) as ResearchReport,results:Record<string,ResultState>={};
  for(const fixture of new Set(report.picks.map(p=>p.fixture_id))){const result=await env.DB.prepare('SELECT status,home_goals,away_goals,kickoff_utc FROM fixtures WHERE id=?').bind(fixture).first<ResultState>();if(result)results[fixture]=result;}
  const evaluation=evaluateReport(report,results,now),payload=JSON.stringify(evaluation),hash=await checksum(payload);
  await env.DB.prepare('INSERT OR IGNORE INTO daily_report_evaluations VALUES(?,?,?,?,?)').bind(hash,id,evaluation.evaluated_at,payload,hash).run();return evaluation;
}
export async function analysisResponse(url:URL,env:Env,now=Date.now()):Promise<Response>{
  if(url.pathname==='/api/provider-preview'||url.pathname==='/api/history/quality'||url.pathname==='/api/research/expanded'||url.pathname==='/api/research/precision'){
    const id=url.pathname==='/api/provider-preview'?'api-football-preview':url.pathname.endsWith('quality')?'recent-quality':url.pathname.endsWith('precision')?'precision-v3':'recent-backtest';const row=await env.DB.prepare('SELECT payload FROM performance WHERE id=?').bind(id).first<{payload:string}>();if(!row)return send({state:'not_prepared'},404);const value=JSON.parse(row.payload) as {chunked?:boolean;key?:string;parts?:number;checksum?:string};if(value.chunked){const chunks=await env.DB.prepare('SELECT part,payload FROM research_report_chunks WHERE report_key=? ORDER BY part').bind(value.key).all<{part:number;payload:string}>();if(chunks.results.length!==value.parts||chunks.results.some((c,i)=>c.part!==i))throw new Error('report_incomplete');const payload=chunks.results.map(c=>c.payload).join('');if(await checksum(payload)!==value.checksum)throw new Error('report_checksum_mismatch');return send(JSON.parse(payload));}return send(value);
  }
  if(env.MOCK_MODE!=='true')return send({error:'live_match_centre_not_approved'},409);
  if(url.pathname==='/api/match-centre/config')return send({mode:'mock_research',demo_round:'2026-10-26',current_round:currentRound(now),day_start_hour:6,timezone:'Asia/Bangkok'});
  if(url.pathname==='/api/match-centre'){
    const q=query(url),all=await windowFixtures(env,q.date,q.period,now),filtered=all.filter(f=>!q.league||f.league_id===q.league),size=24;
    return send({round:q.window,mode:'mock_research',items:filtered.slice((q.page-1)*size,q.page*size),total:filtered.length,page:q.page,page_size:size,pages:Math.ceil(filtered.length/size),data_completeness:'mock fixtures only; not an actual complete schedule'});
  }
  if(url.pathname==='/api/daily-report'){
    const q=query(url),reportId=url.searchParams.get('id');if(reportId&&reportId.length>240)return send({error:'invalid_report_id'},400);const statement=reportId?env.DB.prepare('SELECT payload,checksum FROM daily_report_snapshots WHERE id=? AND generated_at<=?').bind(reportId,new Date(now).toISOString()):env.DB.prepare('SELECT payload,checksum FROM daily_report_snapshots WHERE round_date=? AND period=? AND generated_at<=? ORDER BY generated_at DESC,rowid DESC LIMIT 1').bind(q.date,q.period,new Date(now).toISOString());const row=await statement.first<{payload:string;checksum:string}>();if(reportId&&!row)return send({error:'report_not_found'},404);
    if(row){if(await checksum(row.payload)!==row.checksum)throw new Error('daily_report_checksum_mismatch');const report=JSON.parse(row.payload) as ResearchReport;const result=await env.DB.prepare('SELECT payload,checksum FROM daily_report_evaluations WHERE report_id=? AND evaluated_at<=? ORDER BY evaluated_at DESC,id DESC LIMIT 1').bind(report.id,new Date(now).toISOString()).first<{payload:string;checksum:string}>();if(result&&await checksum(result.payload)!==result.checksum)throw new Error('evaluation_checksum_mismatch');return send({...report,evaluation:result?JSON.parse(result.payload):null});}
    return send(await createReport(env,q.date,q.period,now));
  }
  if(url.pathname.startsWith('/api/analysis/')){
    const id=decodeURIComponent(url.pathname.split('/').at(-1)??'');if(!/^[a-zA-Z0-9:-]{1,100}$/.test(id))return send({error:'invalid_id'},400);
    const fixture=await env.DB.prepare(fixtureSelect+' WHERE f.id=?').bind(id).first<Omit<CentreFixture,'analysis'>>();if(!fixture)return send({error:'not_found'},404);
    const snapshotId=url.searchParams.get('snapshot')??undefined;if(snapshotId&&!/^[a-zA-Z0-9:-]{1,180}$/.test(snapshotId))return send({error:'invalid_snapshot'},400);
    const [f]=await attach(env,[fixture],now,snapshotId),cutoff=f.analysis?.cutoff_date;if(!cutoff)return send({fixture:f,state:'insufficient_data',history:null});
    const n=Number(url.searchParams.get('last')??10);if(![5,10,20].includes(n))return send({error:'invalid_history_window'},400);
    const teamRows=async(team:string,venue?:'home'|'away')=>(await env.DB.prepare(historySelect+` WHERE r.dataset_version=? AND r.match_date<=? AND r.league_id=? AND ${venue==='home'?'r.home_id=?':venue==='away'?'r.away_id=?':'(r.home_id=? OR r.away_id=?)'} ORDER BY r.match_date DESC,r.id DESC LIMIT ?`).bind(...[f.analysis!.dataset_version,cutoff,f.league_id,team,...(venue?[]:[team]),n]).all<HistoryMatch>()).results;
    const home=await teamRows(f.home_id),away=await teamRows(f.away_id),hv=await teamRows(f.home_id,'home'),av=await teamRows(f.away_id,'away');
    const allLeagues=url.searchParams.get('h2h')==='all';const h2h=(await env.DB.prepare(historySelect+` WHERE r.dataset_version=? AND r.match_date<=? AND ((r.home_id=? AND r.away_id=?) OR (r.home_id=? AND r.away_id=?)) ${allLeagues?'':'AND r.league_id=?'} ORDER BY r.match_date DESC,r.id DESC LIMIT ?`).bind(...[f.analysis!.dataset_version,cutoff,f.home_id,f.away_id,f.away_id,f.home_id,...(allLeagues?[]:[f.league_id]),n]).all<HistoryMatch>()).results;
    return send({fixture:f,history:{last:n,cutoff_date:cutoff,home:summarize(home,f.home_id),away:summarize(away,f.away_id),home_venue:summarize(hv,f.home_id),away_venue:summarize(av,f.away_id),h2h:{...summarize(h2h,f.home_id),scope:allLeagues?'all_imported_leagues':'same_league'}},provider:{state:'not_connected',blocks:['standings','injuries','lineups','provider_predictions','odds']},publication:{status:'research_only',live_blockers:['mock_fixture','unverified_source_dates_and_mapping','model_not_approved']}});
  }
  return send({error:'not_found'},404);
}
