import {z} from 'zod';
import type {Env} from './types';
import type {ProgramFixture,Competition} from '../../packages/football/program';
import type {AnalysisSnapshot,TeamSummary} from '../../packages/football/types';
import {checksum} from './analysis';
import {liveDaily,liveResponse} from './live';
import {currentRound,roundWindow} from '../../packages/football/window';
import {PROGRAM_COMPETITION_ORDER} from '../../packages/football/competition-order';
import {programSyncState} from './program-sync';

const send=(body:unknown,status=200)=>Response.json(body,{status,headers:{'cache-control':'no-store','x-content-type-options':'nosniff'}});
const date=z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const hash=z.string().regex(/^[a-f0-9]{64}$/);
const input=z.object({records:z.array(z.object({kind:z.enum(['fixture','source']),values:z.array(z.union([z.string().max(15000),z.number().finite()])).max(11)}).strict()).min(1).max(20)}).strict();

export async function importProgram(body:string,env:Env){
  if(env.LIVE_RESEARCH_ENABLED!=='true')return send({error:'live_research_disabled'},409);
  const data=input.parse(JSON.parse(body)),statements:D1PreparedStatement[]=[];
  for(const record of data.records){
    const v=record.values;
    if(record.kind==='fixture'){
      if(v.length!==11)throw new Error('invalid_program_record_width');
      hash.parse(v[0]);hash.parse(v[10]);date.parse(v[4]);date.parse(v[7]);
      const p=JSON.parse(String(v[9])) as ProgramFixture&{observation_id:string;source_date:string;search_text:string};
      if(!Number.isFinite(Date.parse(p.kickoff_utc))||new Date(p.kickoff_utc).toISOString()!==p.kickoff_utc||!Number.isFinite(Date.parse(p.observed_at))||new Date(p.observed_at).toISOString()!==p.observed_at)throw new Error('canonical_utc_required');
      if(await checksum(String(v[9]))!==v[10]||p.observation_id!==v[0]||p.id!==v[1]||p.provider_league_id!==v[2]||p.kickoff_utc!==v[3]||p.business_date!==v[4]||p.observed_at!==v[5]||p.status!==v[6]||p.source_date!==v[7]||p.search_text!==v[8]||!/^api-football-\d+$/.test(p.id)||!Number.isSafeInteger(p.provider_league_id)||p.provider_league_id<=0||!Number.isFinite(Date.parse(p.observed_at))||Date.parse(p.observed_at)>Date.now()+60000)throw new Error('invalid_program_record');
      const round=roundWindow(p.business_date,'day');if(p.kickoff_utc<round.start||p.kickoff_utc>=round.end_exclusive)throw new Error('invalid_program_business_date');
      const semantic=Object.fromEntries(Object.entries(p).filter(([key])=>!['observation_id','observed_at','source_sha256'].includes(key)).sort(([a],[b])=>a.localeCompare(b)));
      const fingerprint=await checksum(JSON.stringify(semantic));
      const previous=await env.DB.prepare('SELECT fingerprint,verified_at FROM program_fixture_fingerprints WHERE fixture_id=?').bind(p.id).first<{fingerprint:string;verified_at:string}>();
      if(!previous||previous.fingerprint!==fingerprint||p.observed_at<previous.verified_at)statements.push(env.DB.prepare('INSERT OR IGNORE INTO program_observations VALUES(?,?,?,?,?,?,?,?,?,?,?)').bind(...v));
      statements.push(env.DB.prepare('INSERT INTO program_fixture_fingerprints VALUES(?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET fingerprint=excluded.fingerprint,verified_at=excluded.verified_at WHERE excluded.verified_at>=program_fixture_fingerprints.verified_at').bind(p.id,fingerprint,p.observed_at));
    }else{
      if(v.length!==6)throw new Error('invalid_program_source_width');
      hash.parse(v[0]);hash.parse(v[5]);date.parse(v[1]);
      if(!Number.isFinite(Date.parse(String(v[2])))||Date.parse(String(v[2]))>Date.now()+60000||!['recorded','partial','denied'].includes(String(v[3]))||!Number.isInteger(v[4])||Number(v[4])<0)throw new Error('invalid_program_source');
      statements.push(env.DB.prepare('INSERT OR IGNORE INTO program_sources VALUES(?,?,?,?,?,?)').bind(...v));
    }
  }
  await env.DB.batch(statements);return send({accepted:data.records.length,training_labels_added:0,model_promoted:false});
}
async function checked<T>(row:{payload:string;checksum:string}){if(await checksum(row.payload)!==row.checksum)throw new Error('program_checksum_mismatch');return JSON.parse(row.payload) as T;}
const from=' FROM program_heads h JOIN program_observations f ON f.id=h.observation_id ';
// Only trusted, static numeric IDs enter this SQL; request values stay bound.
const competitionRank='CASE f.competition_id '+PROGRAM_COMPETITION_ORDER.map((id,rank)=>`WHEN ${id} THEN ${rank}`).join(' ')+` ELSE ${PROGRAM_COMPETITION_ORDER.length} END`;
const competitionCountry="COALESCE(json_extract(f.payload,'$.country'),'')",competitionName="COALESCE(json_extract(f.payload,'$.league_name'),'')";
// A stable group label keeps renamed competitions contiguous across pages too.
const fixtureOrder=`${competitionRank},MIN(${competitionCountry}) OVER(PARTITION BY f.competition_id),MIN(${competitionName}) OVER(PARTITION BY f.competition_id),f.competition_id,f.kickoff_utc,f.fixture_id`;
async function enrich(items:ProgramFixture[],env:Env,now:string){
  if(!items.length)return items;
  const rows=await env.DB.prepare(`SELECT fixture_id,kickoff_utc,payload,checksum FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY fixture_id ORDER BY generated_at DESC,id DESC) choice FROM live_prediction_snapshots WHERE fixture_id IN (${items.map(()=>'?').join(',')}) AND generated_at<=?) WHERE choice=1`).bind(...items.map(f=>f.id),now).all<{fixture_id:string;kickoff_utc:string;payload:string;checksum:string}>();
  for(const row of rows.results){const fixture=items.find(f=>f.id===row.fixture_id);if(fixture&&fixture.kickoff_utc===row.kickoff_utc)fixture.analysis=await checked<AnalysisSnapshot>(row);}
  return items;
}
const empty=():TeamSummary=>({n:0,wins:0,draws:0,losses:0,goals_for:0,goals_against:0,average_for:null,average_against:null,over25:null,btts:null,clean_sheets:0,form:[],matches:[]});
async function detail(url:URL,env:Env,now:number){
  const id=decodeURIComponent(url.pathname.split('/').at(-1)??'');if(!/^api-football-\d+$/.test(id))return send({error:'invalid_id'},400);
  const row=await env.DB.prepare('SELECT f.payload,f.checksum'+from+'WHERE f.fixture_id=? AND f.observed_at<=?').bind(id,new Date(now).toISOString()).first<{payload:string;checksum:string}>();
  if(!row)return send({error:'not_found'},404);
  const f=await checked<ProgramFixture>(row),legacyURL=new URL(url);legacyURL.pathname='/api/live/analysis/'+id;
  const response=await liveResponse(legacyURL,env,now);
  if(response.ok){
    const body=await response.json() as {fixture:Record<string,unknown>&{kickoff_utc:string};analysis:unknown};
    if(body.fixture.kickoff_utc===f.kickoff_utc)return send({...body,fixture:{...body.fixture,...f,home_id:body.fixture.home_id??'',away_id:body.fixture.away_id??'',mapping_status:body.fixture.mapping_status??f.mapping_status}});
  }else if(response.status!==404)return response;
  const last=Number(url.searchParams.get('last')??10),scope=url.searchParams.get('scope')??'league';
  if(![5,10,20].includes(last)||!['league','all'].includes(scope))return send({error:'invalid_history_filter'},400);
  return send({fixture:f,analysis:null,state:f.model_supported?'insufficient_verified_data':'model_not_supported',mode:'private_research',history:{last,cutoff_date_exclusive:f.match_date,home:empty(),away:empty(),home_venue:empty(),away_venue:empty(),h2h:{...empty(),scope}},context:{availability:{known:false,records:null,missing:null,questionable:null},lineups:{confirmed:false},provider_forecast:{probabilities:null,available_at:null},past_xg:{home:{n:0,xg_for_mean:null},away:{n:0,xg_for_mean:null}}},recorded_enrichments:[],generated_at:new Date(now).toISOString()});
}
export async function programResponse(url:URL,env:Env,now=Date.now()):Promise<Response>{
  if(env.LIVE_RESEARCH_ENABLED!=='true')return send({error:'live_research_disabled'},409);
  if(url.pathname.startsWith('/api/program/analysis/'))return detail(url,env,now);
  if(!['/api/program/fixtures','/api/program/daily'].includes(url.pathname))return send({error:'not_found'},404);
  const dateValue=url.searchParams.get('date')??currentRound(now),period=url.searchParams.get('period')??'day';
  if(period!=='day'&&period!=='night')return send({error:'invalid_period'},400);
  const window=roundWindow(dateValue,period),iso=new Date(now).toISOString();
  const schema=z.object({q:z.string().max(100),league:z.string().regex(/^[a-z0-9-]{1,80}$/),country:z.string().max(100),status:z.enum(['all','upcoming','live','finished','other']),page:z.coerce.number().int().min(1).max(10000),following:z.string().max(2000)});
  const p=schema.parse({q:url.searchParams.get('q')??'',league:url.searchParams.get('league')??'all',country:url.searchParams.get('country')??'all',status:url.searchParams.get('status')??'all',page:url.searchParams.get('page')??1,following:url.searchParams.get('following')??''});
  const global='f.kickoff_utc>=? AND f.kickoff_utc<? AND f.observed_at<=?',baseValues:unknown[]=[window.start,window.end_exclusive,iso],where=[global],values=[...baseValues];
  if(p.q){where.push("f.search_text LIKE ? ESCAPE '\\'");values.push('%'+p.q.normalize('NFKC').toLowerCase().replace(/[\\%_]/g,s=>'\\'+s)+'%');}
  if(p.country!=='all'){where.push("json_extract(f.payload,'$.country')=?");values.push(p.country);}
  if(p.status==='upcoming')where.push("f.status IN ('scheduled','unverified')");
  if(p.status==='live')where.push("f.status IN ('live','suspended','interrupted')");
  if(p.status==='finished')where.push("f.status LIKE 'finished%'");
  if(p.status==='other')where.push("f.status IN ('postponed','cancelled','abandoned','awarded','walkover')");
  if(p.following){const ids=p.following.split(',');if(ids.length>50||ids.some(v=>!/^([a-z0-9-]{1,80})$/.test(v)))return send({error:'invalid_following'},400);where.push(`json_extract(f.payload,'$.league_id') IN (${ids.map(()=>'?').join(',')})`);values.push(...ids);}
  if(url.searchParams.get('ready')==='1'){where.push('EXISTS(SELECT 1 FROM live_prediction_snapshots p WHERE p.fixture_id=f.fixture_id AND p.kickoff_utc=f.kickoff_utc AND p.generated_at<=?)');values.push(iso);}
  const grouped=await env.DB.prepare(`SELECT MIN(json_extract(f.payload,'$.league_id')) id,f.competition_id provider_id,MIN(${competitionName}) name,MIN(${competitionCountry}) country,COUNT(*) n`+from+'WHERE '+where.join(' AND ')+` GROUP BY f.competition_id ORDER BY ${competitionRank},country,name,provider_id`).bind(...values).all<Competition>();
  if(p.league!=='all'){where.push("json_extract(f.payload,'$.league_id')=?");values.push(p.league);}
  const filtered=where.join(' AND '),total=(await env.DB.prepare('SELECT COUNT(*) n'+from+'WHERE '+filtered).bind(...values).first<{n:number}>())?.n??0;
  if(url.pathname==='/api/program/daily'){
    const report=await liveDaily(env,dateValue,period,now),ids=Array.from(new Set([...report.picks.map(p=>p.fixture_id),...report.goal_ranking.map(p=>p.fixture_id)])),matched=new Set<string>();
    for(let i=0;i<ids.length;i+=30){const chunk=ids.slice(i,i+30);const rows=await env.DB.prepare('SELECT f.fixture_id'+from+'WHERE '+filtered+` AND f.fixture_id IN (${chunk.map(()=>'?').join(',')})`).bind(...values,...chunk).all<{fixture_id:string}>();for(const row of rows.results)matched.add(row.fixture_id);}
    return send({...report,fixture_count:total,picks:report.picks.filter(p=>matched.has(p.fixture_id)),goal_ranking:report.goal_ranking.filter(p=>matched.has(p.fixture_id))});
  }
  const pages=Math.max(1,Math.ceil(total/25)),page=Math.min(p.page,pages);
  const rows=await env.DB.prepare('SELECT f.payload,f.checksum'+from+'WHERE '+filtered+` ORDER BY ${fixtureOrder} LIMIT 25 OFFSET ?`).bind(...values,(page-1)*25).all<{payload:string;checksum:string}>();
  const items=await enrich(await Promise.all(rows.results.map(r=>checked<ProgramFixture>(r))),env,iso);
  const overview=await env.DB.prepare("SELECT json_extract(f.payload,'$.country') country,COUNT(*) n"+from+'WHERE '+global+' GROUP BY country ORDER BY country').bind(...baseValues).all<{country:string;n:number}>();
  const next=new Date(Date.parse(dateValue+'T00:00:00Z')+86400000).toISOString().slice(0,10);
  const sources=await env.DB.prepare('SELECT source_date,observed_at,state,row_count FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY source_date ORDER BY observed_at DESC,id DESC) choice FROM program_sources WHERE source_date IN (?,?) AND observed_at<=?) WHERE choice=1').bind(dateValue,next,iso).all<{source_date:string;observed_at:string;state:string;row_count:number}>();
  const coverage=[dateValue,next].map(date=>{const value=sources.results.find(s=>s.source_date===date);return {date,state:value?.state??'not_fetched',captured_at:value?.observed_at??null,rows:value?.row_count??null};});
  const captured=coverage.filter(s=>s.state==='recorded').map(s=>s.captured_at!).sort()[0]??items.map(f=>f.observed_at).sort()[0]??'';
  return send({date:dateValue,period,round:window,items,total,round_total:overview.results.reduce((n,g)=>n+g.n,0),page,page_size:25,pages,competitions:grouped.results,countries:overview.results.map(g=>g.country),source_dates:coverage,captured_at:captured,known_source_dates:coverage.filter(s=>s.state==='recorded').map(s=>s.date),data_completeness:coverage.every(s=>s.state==='recorded')?'two_source_dates_recorded':'partial_source_dates',automatic_refresh:env.PROGRAM_SYNC_ENABLED==='true',sync:await programSyncState(env),model_promoted:false});
}
