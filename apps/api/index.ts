import {exportLive} from './live-export';
import {importProgram,programResponse} from './program';
import {mediaResponse} from './media';
import {importLive} from './live-import';
import {liveResponse,liveInternal} from './live';
import {providerBroker} from './provider-broker';
import {z} from 'zod';
import type {Env,Fixture} from './types';
import {authorize,readLimited} from './security';
import {runSync} from './jobs';
import {filteringResponse} from './filtering';
import {analysisResponse,lockDailyReport,evaluateDailyReport} from './analysis';
const json=(value:unknown,status=200)=>Response.json(value,{status,headers:{'cache-control':'no-store','x-content-type-options':'nosniff','referrer-policy':'no-referrer'}});
const importSchema=z.object({predictions:z.array(z.object({id:z.string().min(1).max(160),fixture_id:z.string().min(1).max(100),model_version:z.string().min(1).max(80),generated_at:z.string().datetime(),information_cutoff_date:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),stage:z.enum(['initial','refresh','final']),probabilities:z.tuple([z.number().min(0).max(1),z.number().min(0).max(1),z.number().min(0).max(1)]).refine(p=>Math.abs(p.reduce((a,b)=>a+b,0)-1)<1e-6),feature_snapshot_hash:z.string().regex(/^[a-f0-9]{64}$/)})).max(20)});
export async function handle(request:Request,env:Env):Promise<Response>{
  try{
    const url=new URL(request.url),path=url.pathname;
    if(path.startsWith('/internal/')){
      const body=await readLimited(request);await authorize(request,body,env);
      if(path==='/internal/live/import'&&request.method==='POST')return await importLive(body,env);
      if(path==='/internal/program/import'&&request.method==='POST')return await importProgram(body,env);
      if(path==='/internal/live/export'&&request.method==='POST')return await exportLive(body,env);
      if((path==='/internal/live-reports/lock'||path==='/internal/live-reports/evaluate')&&request.method==='POST')return await liveInternal(path,body,env);
      if((path==='/internal/provider-quota/reserve'||path==='/internal/provider-quota/settle')&&request.method==='POST')return await providerBroker(path,body,env);
      if(path==='/internal/daily-reports/lock'&&request.method==='POST'){
        const p=z.object({date:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),period:z.enum(['day','night']).default('day')}).parse(JSON.parse(body));return json(await lockDailyReport(env,p.date,p.period));
      }
      if(path==='/internal/daily-reports/evaluate'&&request.method==='POST'){const p=z.object({report_id:z.string().min(1).max(240)}).parse(JSON.parse(body));return json(await evaluateDailyReport(env,p.report_id));}
      if(path==='/internal/sync/dry-run'&&request.method==='POST')return json({live_enabled:env.LIVE_API_ENABLED==='true',estimated_calls:1,scope:'EPL season query; current-season free-plan access unverified; use date preflight first',before_live:['coverage + allowed seasons','verified reset and headers','direct vs RapidAPI account','provider terms + billing controls'],automatic_retries:0});
      if(path==='/internal/sync/execute'&&request.method==='POST')return json(await runSync(env,crypto.randomUUID()));
      if(path==='/internal/features/export'&&request.method==='GET'){
        const cursor=url.searchParams.get('cursor')??'';if(cursor.length>100)return json({error:'invalid_cursor'},400);
        const rows=await env.DB.prepare('SELECT t.*,f.kickoff_utc,f.match_date FROM features t JOIN fixtures f ON f.id=t.fixture_id WHERE fixture_id>? AND f.kickoff_utc>? ORDER BY fixture_id LIMIT 20').bind(cursor,new Date().toISOString()).all();
        return json({items:rows.results,next_cursor:rows.results.length===20?rows.results.at(-1)?.fixture_id:null});
      }
      if(path==='/internal/predictions/import'&&request.method==='POST'){
        const data=importSchema.parse(JSON.parse(body));const statements:D1PreparedStatement[]=[];
        for(const p of data.predictions){
          const fixture=await env.DB.prepare('SELECT * FROM fixtures WHERE id=?').bind(p.fixture_id).first<Fixture>();
          const feature=await env.DB.prepare('SELECT snapshot_hash,information_cutoff_date FROM features WHERE fixture_id=?').bind(p.fixture_id).first<{snapshot_hash:string;information_cutoff_date:string}>();
          const model=await env.DB.prepare('SELECT version,training_cutoff FROM model_versions WHERE version=? AND status=?').bind(p.model_version,'approved').first<{version:string;training_cutoff:string}>();
          if(!fixture?.kickoff_utc||fixture.status!=='scheduled'||!model||model.training_cutoff>fixture.match_date||model.training_cutoff>p.generated_at.slice(0,10)||!feature||feature.snapshot_hash!==p.feature_snapshot_hash||feature.information_cutoff_date!==p.information_cutoff_date||p.information_cutoff_date>=fixture.match_date||Date.parse(p.generated_at)>Date.now()+60000||Date.parse(p.generated_at)>=Date.parse(fixture.kickoff_utc)||Date.now()>=Date.parse(fixture.kickoff_utc))return json({error:'prediction_cutoff_feature_or_model_rejected'},409);
          statements.push(env.DB.prepare('INSERT OR IGNORE INTO predictions(id,fixture_id,model_version,generated_at,information_cutoff_date,stage,probabilities,scorelines,feature_snapshot_hash,source) VALUES(?,?,?,?,?,?,?,?,?,?)').bind(p.id,p.fixture_id,p.model_version,p.generated_at,p.information_cutoff_date,p.stage,JSON.stringify(p.probabilities),'[]',p.feature_snapshot_hash,'batch_ml'));
        }
        if(statements.length)await env.DB.batch(statements);
        return json({accepted:data.predictions.length});
      }
      if(path==='/internal/ops/summary'&&request.method==='GET'){
        const jobs=await env.DB.prepare('SELECT id,status,started_at,completed_at FROM jobs ORDER BY started_at DESC LIMIT 10').all();
        const quota=await env.DB.prepare('SELECT id,used,remaining FROM quota_windows ORDER BY id DESC LIMIT 2').all();return json({jobs:jobs.results,quota:quota.results,MODEL_AUTO_PROMOTE:false});
      }
      if(['/internal/models/promote','/internal/models/rollback'].includes(path)&&request.method==='POST'){
        const payload=z.object({version:z.string().min(1).max(80).optional(),approved:z.literal(true)}).parse(JSON.parse(body));
        const reg=await env.DB.prepare('SELECT * FROM registry WHERE id=1').first<{active_version:string|null;previous_version:string|null}>();
        const target=path.endsWith('rollback')?reg?.previous_version:payload.version;
        if(!target||!await env.DB.prepare('SELECT version FROM model_versions WHERE version=? AND status IN(?,?)').bind(target,'eligible','approved').first())return json({error:'model_not_eligible'},409);
        await env.DB.batch([env.DB.prepare('UPDATE registry SET previous_version=active_version,active_version=? WHERE id=1').bind(target),env.DB.prepare('UPDATE model_versions SET status=? WHERE version=?').bind('approved',target),env.DB.prepare('INSERT INTO audit_log VALUES(?,?,?,?)').bind(crypto.randomUUID(),path,new Date().toISOString(),target)]);return json({active_version:target});
      }
      return json({error:'not_found'},404);
    }
    if(path.startsWith('/api/')&&request.method!=='GET')return json({error:'method_not_allowed'},405);
    if(path.startsWith('/api/live/'))return await liveResponse(url,env);
    if(path.startsWith('/api/program/'))return await programResponse(url,env);
    if(path.startsWith('/api/media/'))return await mediaResponse(url,env);
    if(path==='/api/provider-preview'||path==='/api/match-centre'||path.startsWith('/api/match-centre/')||path.startsWith('/api/analysis/')||path==='/api/daily-report'||path==='/api/history/quality'||path==='/api/research/expanded'||path==='/api/research/precision')return await analysisResponse(url,env);
    if(path==='/api/health')return json({status:'ok',mode:env.MOCK_MODE==='true'?'mock':'configured',live_api_enabled:env.LIVE_API_ENABLED==='true',auto_promote:false});
    if(path==='/api/filtering'||path.startsWith('/api/filtering/'))return filteringResponse(url,env);
    if(path==='/api/leagues')return json({items:(await env.DB.prepare('SELECT id,name,source_code FROM leagues ORDER BY name').all()).results});
    if(path==='/api/fixtures'){
      const league=url.searchParams.get('league'),date=url.searchParams.get('date'),page=Number(url.searchParams.get('page')??'1');
      if(league&&!/^[a-z-]{1,30}$/.test(league)||date&&(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(Date.parse(date)))||!Number.isInteger(page)||page<1||page>100)return json({error:'invalid_filter'},400);
      const rows=await env.DB.prepare(`SELECT f.*,h.name AS home,a.name AS away FROM fixtures f JOIN teams h ON h.id=f.home_id JOIN teams a ON a.id=f.away_id WHERE (? IS NULL OR league_id=?) AND (? IS NULL OR match_date=?) ORDER BY kickoff_utc LIMIT 50 OFFSET ?`).bind(league,league,date,date,(page-1)*50).all();return json({items:rows.results,page,mode:env.MOCK_MODE==='true'?'mock':'configured'});
    }
    if(path.startsWith('/api/matches/')||path.startsWith('/api/predictions/')){
      const id=decodeURIComponent(path.split('/').at(-1)??'');if(!/^[a-zA-Z0-9:-]{1,100}$/.test(id))return json({error:'invalid_id'},400);
      const fixture=await env.DB.prepare('SELECT f.*,h.name AS home,a.name AS away FROM fixtures f JOIN teams h ON h.id=f.home_id JOIN teams a ON a.id=f.away_id WHERE f.id=?').bind(id).first();
      if(!fixture)return json({error:'not_found'},404);
      const prediction=await env.DB.prepare('SELECT * FROM predictions WHERE fixture_id=? ORDER BY generated_at DESC LIMIT 1').bind(id).first();
      return json({fixture,prediction:prediction?{...prediction,probabilities:JSON.parse(String(prediction.probabilities)),scorelines:JSON.parse(String(prediction.scorelines))}:null,data_state:prediction?'available':'insufficient_data'});
    }
    if(path==='/api/model-performance'){
      const report=await env.DB.prepare('SELECT payload FROM performance WHERE id=?').bind('backtest').first<{payload:string}>();return json(report?JSON.parse(report.payload):{state:'insufficient_data'});
    }
    if(path.startsWith('/api/'))return json({error:'not_found'},404);
    return env.ASSETS?env.ASSETS.fetch(request):json({error:'not_found'},404);
  }catch(error){
    const code=error instanceof Error?error.message:'request_failed';
    return json({error:code==='unauthorized'?'unauthorized':code==='replay_rejected'?'replay_rejected':code==='payload_too_large'?'payload_too_large':'request_rejected'},code==='unauthorized'?401:code==='replay_rejected'?409:code==='payload_too_large'?413:400);
  }
}
export default {
  async fetch(request:Request,env:Env){const response=await handle(request,env);if(request.headers.get('origin')===env.ALLOWED_ORIGIN)response.headers.set('access-control-allow-origin',env.ALLOWED_ORIGIN);return response;},
  async scheduled(controller:ScheduledController,env:Env,ctx:ExecutionContext){if(env.SCHEDULER_ENABLED!=='true')return;ctx.waitUntil(runSync(env,'cron-'+controller.scheduledTime));},
};
