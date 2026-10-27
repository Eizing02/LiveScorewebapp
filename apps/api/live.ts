import type {Env} from './types';
import type {AnalysisSnapshot,CentreFixture,HistoryMatch,ResearchReport} from '../../packages/football/types';
import {checksum,summarize} from './analysis';
import {buildDailyReport} from '../../packages/football/selection';
import {currentRound,roundWindow,type Period} from '../../packages/football/window';
import {evaluateReport,type ResultState} from '../../packages/football/settlement';
interface Observation{fixture_id:string;occurrence_id:string;observation_id:string;league_id:string;league_name:string;home_id:string;away_id:string;home:string;away:string;kickoff_utc:string;date:string;status:string;score_90:number[]|null;current_score?:number[]|null;home_provider_id?:number;away_provider_id?:number;provider_league_id?:number;first_seen_at:string;mapping_status:string;quarantine_reasons:string[]}
interface Detail{fixture:Observation;analysis:AnalysisSnapshot|null;history:Record<string,HistoryMatch[]|string>;context:unknown;recorded_enrichments:unknown[];generated_at:string;state:string;dataset_version:string}
const send=(value:unknown,status=200)=>Response.json(value,{status,headers:{'cache-control':'no-store','x-content-type-options':'nosniff'}});
async function parseChecked<T>(row:{payload:string;checksum:string}|null):Promise<T|null>{if(!row)return null;if(await checksum(row.payload)!==row.checksum)throw new Error('live_payload_checksum_mismatch');return JSON.parse(row.payload) as T;}
async function observations(env:Env,now:number,window?:{start:string;end_exclusive:string},ids?:string[]){
  const active=await env.DB.prepare("SELECT value FROM settings WHERE key='LIVE_IDENTITY_VERSION'").first<{value:string}>();
  const bounds=window?' AND h.kickoff_utc>=? AND h.kickoff_utc<?':'';
  const selected=ids?.length?' AND h.fixture_id IN('+ids.map(()=>'?').join(',')+')':'';
  if(ids&&ids.length===0)return [];
  const values:unknown[]=[new Date(now).toISOString(),active?.value??null,active?.value??null,...(window?[window.start,window.end_exclusive]:[]),...(ids??[])];
  const rows=await env.DB.prepare(`SELECT o.payload,o.checksum FROM provider_fixture_heads h JOIN provider_fixture_observations o ON o.id=h.observation_id WHERE h.observed_at<=? AND (? IS NULL OR h.mapping_version=?)${bounds}${selected} ORDER BY h.kickoff_utc,h.fixture_id LIMIT 1001`).bind(...values).all<{payload:string;checksum:string}>();
  if(rows.results.length>1000)throw new Error('live_fixture_limit');
  return Promise.all(rows.results.map(r=>parseChecked<Observation>(r))) as Promise<Observation[]>;
}
async function centre(env:Env,date:string,period:Period,now:number){
  const window=roundWindow(date,period),source=await observations(env,now,window),fixtures:CentreFixture[]=[],snapshots=new Map<string,AnalysisSnapshot>();
  for(let start=0;start<source.length;start+=80){
    const ids=source.slice(start,start+80).map(f=>f.fixture_id);
    const rows=await env.DB.prepare(`SELECT fixture_id,occurrence_id,payload,checksum FROM (SELECT fixture_id,occurrence_id,payload,checksum,ROW_NUMBER() OVER(PARTITION BY fixture_id,occurrence_id ORDER BY generated_at DESC,id DESC) choice FROM live_prediction_snapshots WHERE fixture_id IN (${ids.map(()=>'?').join(',')}) AND generated_at<=?) WHERE choice=1`).bind(...ids,new Date(now).toISOString()).all<{fixture_id:string;occurrence_id:string;payload:string;checksum:string}>();
    for(const row of rows.results){const prediction=await parseChecked<AnalysisSnapshot>(row);if(prediction)snapshots.set(row.fixture_id+':'+row.occurrence_id,prediction);}
  }
  for(const f of source)fixtures.push({id:f.fixture_id,league_id:f.league_id,league_name:f.league_name,home:f.home,away:f.away,home_id:f.home_id??'',away_id:f.away_id??'',kickoff_utc:f.kickoff_utc,match_date:f.date,status:f.status,source:'api_football_private_research',quality:f.quarantine_reasons.length?'quarantined':'provider_recorded',analysis:snapshots.get(f.fixture_id+':'+f.occurrence_id)??null,home_provider_id:f.home_provider_id,away_provider_id:f.away_provider_id,provider_league_id:f.provider_league_id,score_90:f.score_90,current_score:f.current_score??null,observed_at:f.first_seen_at,mapping_status:f.mapping_status});
  const dates=await env.DB.prepare("SELECT value FROM settings WHERE key='LIVE_SOURCE_DATES'").first<{value:string}>(),known=dates?JSON.parse(dates.value) as string[]:[];
  const capture=await env.DB.prepare("SELECT value FROM settings WHERE key='LIVE_SOURCE_CAPTURED_AT'").first<{value:string}>();
  const next=new Date(Date.parse(date+'T00:00:00Z')+86400000).toISOString().slice(0,10);
  return {fixtures,source,window,known,captured_at:capture?.value??source.reduce((s,f)=>f.first_seen_at>s?f.first_seen_at:s,''),data_completeness:known.includes(date)&&known.includes(next)?'two_source_dates_recorded':'partial_source_dates'};
}
export async function liveDaily(env:Env,date:string,period:Period,now=Date.now()):Promise<ResearchReport>{
  const data=await centre(env,date,period,now),report=buildDailyReport(data.fixtures,date,period,now,'private_research');
  report.policy_version='live-private-v1:'+report.policy_version;report.id=report.policy_version+':'+date+':'+period+':'+new Date(now).toISOString();
  report.limitations.push('ข้อมูลครอบคลุมวันที่: '+data.known.join(', ')+' · '+data.data_completeness,'การจับคู่ชื่อผ่านการทบทวนภายใน ยังไม่ใช่การรับรอง provider identity จากแหล่งทางการอิสระ');
  return report;
}
export async function liveInternal(path:string,body:string,env:Env,now=Date.now()){
  if(env.LIVE_RESEARCH_ENABLED!=='true')return send({error:'live_research_disabled'},409);
  const p=JSON.parse(body) as {date?:string;period?:Period;report_id?:string};
  if(path.endsWith('/lock')){
    const report=await liveDaily(env,p.date??currentRound(now),p.period??'day',now);
    if(report.picks.some(v=>v.passed&&Date.parse(v.kickoff_utc)<=now))throw new Error('live_report_started_selection');
    report.locked=true;report.id+=':'+(await checksum(JSON.stringify(report))).slice(0,12);const payload=JSON.stringify(report);
    await env.DB.prepare('INSERT OR IGNORE INTO live_daily_reports VALUES(?,?,?,?,?,?)').bind(report.id,report.round.date,report.generated_at,report.policy_version,payload,await checksum(payload)).run();
    return send(report);
  }
  if(!p.report_id||p.report_id.length>500)throw new Error('invalid_live_report_id');
  const report=await parseChecked<ResearchReport>(await env.DB.prepare('SELECT payload,checksum FROM live_daily_reports WHERE id=?').bind(p.report_id).first<{payload:string;checksum:string}>());if(!report)return send({error:'not_found'},404);
  const latest:Observation[]=[],results:Record<string,ResultState>={};const selectedIds=Array.from(new Set(report.picks.map(p=>p.fixture_id)));for(let i=0;i<selectedIds.length;i+=80)latest.push(...await observations(env,now,undefined,selectedIds.slice(i,i+80)));
  for(const f of latest){const score=f.score_90;results[f.fixture_id]={status:f.status==='walkover'?'awarded':['finished','finished_extra_time','finished_penalties'].includes(f.status)&&score&&f.quarantine_reasons.length===0?'finished':f.status.startsWith('finished')?'unverified':f.status,home_goals:score?.[0]??null,away_goals:score?.[1]??null,kickoff_utc:f.kickoff_utc};}
  for(const pick of report.picks){const current=latest.find(f=>f.fixture_id===pick.fixture_id);if(current&&Date.parse(current.kickoff_utc)!==Date.parse(pick.kickoff_utc))results[pick.fixture_id]={...results[pick.fixture_id],status:'postponed'};}
  const result={...evaluateReport(report,results,now),mode:'private_research'},payload=JSON.stringify(result),hash=await checksum(payload);
  await env.DB.prepare('INSERT OR IGNORE INTO live_evaluation_revisions VALUES(?,?,?,?,?,?)').bind(hash,report.id,await checksum(JSON.stringify(results)),result.evaluated_at,payload,hash).run();return send(result);
}
export async function liveResponse(url:URL,env:Env,now=Date.now()):Promise<Response>{
  if(env.LIVE_RESEARCH_ENABLED!=='true')return send({error:'live_research_disabled'},409);
  const date=url.searchParams.get('date')??currentRound(now),period=url.searchParams.get('period')??'day';if(period!=='day'&&period!=='night')return send({error:'invalid_period'},400);roundWindow(date,period);
  if(url.pathname==='/api/live/fixtures'){
    const data=await centre(env,date,period,now);return send({mode:'private_research',date,round:data.window,items:data.fixtures,total:data.fixtures.length,captured_at:data.captured_at,known_source_dates:data.known,data_completeness:data.data_completeness,automatic_refresh:false,production_approved:false});
  }
  if(url.pathname==='/api/live/daily-report')return send(await liveDaily(env,date,period,now));
  if(url.pathname==='/api/live/results'){
    const offset=Number(url.searchParams.get('offset')??0);
    if(!Number.isInteger(offset)||offset<0||offset>10000)return send({error:'invalid_offset'},400);
    const window=url.searchParams.has('date')?roundWindow(date,period):null;
    const rows=await env.DB.prepare(`SELECT id,fixture_id,kickoff_utc,payload,checksum FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY fixture_id,occurrence_id ORDER BY generated_at,id) choice FROM live_prediction_snapshots WHERE generated_at<=? AND COALESCE(json_extract(payload,'$.stage'),'initial')='initial') WHERE choice=1${window?' AND kickoff_utc>=? AND kickoff_utc<?':''} ORDER BY kickoff_utc DESC,id LIMIT 51 OFFSET ?`).bind(new Date(now).toISOString(),...(window?[window.start,window.end_exclusive]:[]),offset).all<{id:string;fixture_id:string;kickoff_utc:string;payload:string;checksum:string}>();
    const page=rows.results.slice(0,50),ids=page.map(r=>r.id),grades=new Map<string,unknown>();
    if(ids.length){
      const evaluations=await env.DB.prepare(`SELECT subject_id,payload,checksum FROM (SELECT subject_id,payload,checksum,ROW_NUMBER() OVER(PARTITION BY subject_id ORDER BY evaluated_at DESC,id DESC) choice FROM live_evaluation_revisions WHERE evaluated_at<=? AND subject_id IN (${ids.map(()=>'?').join(',')})) WHERE choice=1`).bind(new Date(now).toISOString(),...ids).all<{subject_id:string;payload:string;checksum:string}>();
      for(const row of evaluations.results)grades.set(row.subject_id,await parseChecked(row));
    }
    const fixtures=await observations(env,now,undefined,page.map(r=>r.fixture_id));
    const items=await Promise.all(page.map(async row=>({snapshot:await parseChecked<AnalysisSnapshot>(row),fixture:fixtures.find(f=>f.fixture_id===row.fixture_id)??null,kickoff_utc:row.kickoff_utc,evaluation:grades.get(row.id)??null})));
    return send({mode:'private_research',items,next_offset:rows.results.length>50?offset+50:null,definition:'first initial snapshot per fixture occurrence; pending and void excluded from accuracy'});
  }
  if(url.pathname==='/api/live/evidence'){
    const row=await env.DB.prepare("SELECT payload FROM performance WHERE id='live-implementation'").first<{payload:string}>();return send(row?JSON.parse(row.payload):{state:'not_prepared'});
  }
  if(url.pathname.startsWith('/api/live/analysis/')){
    const id=decodeURIComponent(url.pathname.split('/').at(-1)??'');if(!/^api-football-\d+$/.test(id))return send({error:'invalid_id'},400);
    const detail=await parseChecked<Detail>(await env.DB.prepare('SELECT payload,checksum FROM live_match_details WHERE fixture_id=? AND created_at<=? ORDER BY created_at DESC,id DESC LIMIT 1').bind(id,new Date(now).toISOString()).first<{payload:string;checksum:string}>());if(!detail)return send({error:'not_found'},404);
    const n=Number(url.searchParams.get('last')??10),scope=url.searchParams.get('scope')??'league';if(![5,10,20].includes(n)||!['league','all'].includes(scope))return send({error:'invalid_history_filter'},400);
    const h=detail.history,get=(key:string)=>Array.isArray(h[key])?(h[key] as HistoryMatch[]).slice(0,n):[],f=detail.fixture;
    return send({...detail,history:{last:n,cutoff_date_exclusive:h.cutoff_date_exclusive,home:summarize(get('home'),f.home_id),away:summarize(get('away'),f.away_id),home_venue:summarize(get('home_venue'),f.home_id),away_venue:summarize(get('away_venue'),f.away_id),h2h:{...summarize(get(scope==='all'?'h2h_all':'h2h_league'),f.home_id),scope}}});
  }
  return send({error:'not_found'},404);
}
