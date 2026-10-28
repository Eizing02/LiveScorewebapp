import {z} from 'zod';
import type {Env} from './types';
import {validRoundDate} from '../../packages/football/window';

const date=z.string().refine(validRoundDate);
const schema=z.object({id:z.string().uuid(),started_at:z.string().datetime(),status:z.enum(['running','complete','failed']),business_date:date,source_dates:z.array(date).min(2).max(3),fixtures_count:z.number().int().nonnegative().default(0),quarantined_count:z.number().int().nonnegative().default(0),error_code:z.enum(['provider_or_import_failed','account_or_quota_blocked']).nullable().default(null)}).strict();
export async function recordProgramSync(body:string,env:Env){
  if(env.PROGRAM_SYNC_ENABLED!=='true')return Response.json({error:'program_sync_disabled'},{status:409});
  const p=schema.parse(JSON.parse(body)),now=new Date().toISOString();
  if(p.started_at>now||p.source_dates.some((d,i)=>d!==new Date(Date.parse(p.business_date+'T00:00:00Z')+i*86400000).toISOString().slice(0,10)))return Response.json({error:'invalid_sync_window'},{status:400});
  if(p.status==='running')await env.DB.prepare('INSERT OR IGNORE INTO program_sync_runs(id,started_at,status,business_date,source_dates) VALUES(?,?,?,?,?)').bind(p.id,p.started_at,p.status,p.business_date,JSON.stringify(p.source_dates)).run();
  else{
    const result=await env.DB.prepare("UPDATE program_sync_runs SET completed_at=?,status=?,fixtures_count=?,quarantined_count=?,error_code=? WHERE id=? AND started_at=? AND status='running'").bind(now,p.status,p.fixtures_count,p.quarantined_count,p.error_code,p.id,p.started_at).run();
    if(!result.meta.changes)return Response.json({error:'sync_run_not_running'},{status:409});
  }
  return Response.json({recorded:true});
}
export async function programSyncState(env:Env){
  const latest=await env.DB.prepare('SELECT started_at,completed_at,status,error_code FROM program_sync_runs ORDER BY started_at DESC,id DESC LIMIT 1').first();
  const success=await env.DB.prepare("SELECT completed_at FROM program_sync_runs WHERE status='complete' ORDER BY completed_at DESC LIMIT 1").first<{completed_at:string}>();
  return {enabled:env.PROGRAM_SYNC_ENABLED==='true',interval_minutes:120,last_success_at:success?.completed_at??null,latest};
}
