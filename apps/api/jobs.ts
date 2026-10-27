import {PROVIDER_LEAGUES} from '../../packages/football/provider-leagues';
import {poisson} from '../../packages/prediction';
import {ApiFootballClient,type ProviderFixture} from './provider';
import type {Env,FeaturePayload,Fixture} from './types';
export async function upsertFixtures(env:Env,fixtures:ProviderFixture[],source:string,now=new Date().toISOString()){
  const leagueMap:Record<number,string>=Object.fromEntries(PROVIDER_LEAGUES.map(l=>[l.provider_id,l.id]));
  for(const m of fixtures){
    const league=leagueMap[m.league.id];if(!league)continue;
    const id=source==='mock'?'mock-'+m.fixture.id:'api-football-'+m.fixture.id;
    const home='provider-'+m.teams.home.id,away='provider-'+m.teams.away.id;
    const state=({NS:'scheduled',FT:'finished',PST:'postponed',CANC:'cancelled',ABD:'abandoned',AWD:'awarded'} as Record<string,string>)[m.fixture.status.short]??'unverified';
    await env.DB.batch([
      ...[m.teams.home,m.teams.away].map(t=>env.DB.prepare('INSERT INTO teams(id,name,provider_id) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name').bind('provider-'+t.id,t.name,String(t.id))),
      env.DB.prepare(`INSERT INTO fixtures(id,provider_fixture_id,league_id,season,home_id,away_id,match_date,kickoff_utc,status,home_goals,away_goals,source,fetched_at,quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET kickoff_utc=excluded.kickoff_utc,match_date=excluded.match_date,status=excluded.status,home_goals=excluded.home_goals,away_goals=excluded.away_goals,fetched_at=excluded.fetched_at`).bind(id,source==='mock'?null:String(m.fixture.id),league,String(m.league.season),home,away,m.fixture.date.slice(0,10),new Date(m.fixture.date).toISOString(),state,m.goals.home,m.goals.away,source,now,source==='mock'?'mock_fixture':'provider_recorded'),
    ]);
  }
}
export async function predictPending(env:Env,now=new Date().toISOString()){
  // Bounded batch. Full historical feature rebuilding is intentionally offline.
  const rows=await env.DB.prepare(`SELECT f.*,t.payload,t.snapshot_hash FROM fixtures f JOIN features t ON t.fixture_id=f.id WHERE f.status='scheduled' AND f.kickoff_utc>? ORDER BY f.kickoff_utc LIMIT 5`).bind(now).all<Fixture&{payload:string;snapshot_hash:string}>();
  let inserted=0;
  for(const row of rows.results){
    const features=JSON.parse(row.payload) as FeaturePayload;
    if(features.information_cutoff_date>=row.match_date||features.history_matches<40)continue;
    const prediction=poisson(features.home_rate,features.away_rate);
    const id=`${row.id}:poisson-v1:initial`;
    const result=await env.DB.prepare(`INSERT OR IGNORE INTO predictions(id,fixture_id,model_version,generated_at,information_cutoff_date,stage,probabilities,expected_home_goals,expected_away_goals,scorelines,feature_snapshot_hash,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`).bind(id,row.id,'poisson-v1',now,features.information_cutoff_date,'initial',JSON.stringify(prediction.probabilities),prediction.expected_home_goals,prediction.expected_away_goals,JSON.stringify(prediction.top_scorelines),row.snapshot_hash,'baseline_fallback').run();
    inserted+=result.meta.changes;
  }
  return inserted;
}
export async function lockAndEvaluate(env:Env,now=new Date().toISOString()){
  await env.DB.prepare(`UPDATE predictions SET locked=1 WHERE locked=0 AND fixture_id IN(SELECT id FROM fixtures WHERE kickoff_utc<=?)`).bind(now).run();
  const settled=await env.DB.prepare(`SELECT p.id,p.probabilities,f.home_goals,f.away_goals FROM predictions p JOIN fixtures f ON p.fixture_id=f.id LEFT JOIN evaluations e ON e.prediction_id=p.id WHERE p.locked=1 AND f.status='finished' AND f.home_goals IS NOT NULL AND f.away_goals IS NOT NULL AND e.prediction_id IS NULL LIMIT 10`).all<{id:string;probabilities:string;home_goals:number;away_goals:number}>();
  for(const row of settled.results){const p=JSON.parse(row.probabilities) as number[],y=row.home_goals>row.away_goals?0:row.home_goals===row.away_goals?1:2;await env.DB.prepare('INSERT OR IGNORE INTO evaluations VALUES(?,?,?,?,?)').bind(row.id,y,-Math.log(Math.max(1e-15,p[y])),p.reduce((n,v,i)=>n+(v-(i===y?1:0))**2,0),now).run();}
}
export async function runSync(env:Env,jobId:string,now=Date.now()){
  if(env.LIVE_API_ENABLED==='true')return {status:'managed_collector_required',reason:'Use the signed quota broker and Python canonical live pipeline; legacy sync cannot create provider-only model identities.'};
  const lock=await env.DB.prepare(`INSERT INTO job_locks(key,owner,expires_at) VALUES('sync',?,?) ON CONFLICT(key) DO UPDATE SET owner=excluded.owner,expires_at=excluded.expires_at WHERE job_locks.expires_at<=? RETURNING owner`).bind(jobId,now+60000,now).first();
  if(!lock)return {status:'already_running'};
  try{
    const job=await env.DB.prepare('INSERT OR IGNORE INTO jobs(id,status,started_at) VALUES(?,?,?)').bind(jobId,'running',new Date(now).toISOString()).run();
    if(!job.meta.changes)return {status:'duplicate_job'};
    try{
      // First integration is intentionally one league and one page per job.
      const response=await new ApiFootballClient(env).fixtures({league:39,season:2026});
      await upsertFixtures(env,response.data.response,response.mode,new Date(now).toISOString());
      await lockAndEvaluate(env,new Date(now).toISOString());
      const predictions=await predictPending(env,new Date(now).toISOString());
      const status=response.stale?'degraded':'complete';
      await env.DB.prepare('UPDATE jobs SET status=?,completed_at=?,detail=? WHERE id=?').bind(status,new Date(now).toISOString(),JSON.stringify({mode:response.mode,predictions,remaining_pages:response.data.paging.total-response.data.paging.current,stale:response.stale}),jobId).run();
      return {status,mode:response.mode,predictions};
    }catch{
      await env.DB.prepare('UPDATE jobs SET status=?,completed_at=?,detail=? WHERE id=?').bind('failed',new Date(now).toISOString(),'sync_failed_last_snapshot_retained',jobId).run();
      throw new Error('sync_failed');
    }
  }finally{await env.DB.prepare('DELETE FROM job_locks WHERE key=? AND owner=?').bind('sync',jobId).run();}
}
