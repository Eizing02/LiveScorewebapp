import {z} from 'zod';
import type {Env} from './types';
import {checksum} from './analysis';
const kinds={observations:'provider_fixture_observations',enrichments:'provider_enrichment_observations',features:'live_feature_snapshots',predictions:'live_prediction_snapshots',evaluations:'live_evaluation_revisions','goal-components':'provider_goal_components'} as const;
const input=z.object({kind:z.enum(Object.keys(kinds) as [keyof typeof kinds,...(keyof typeof kinds)[]]),cursor:z.string().max(200).default('')}).strict();
export async function exportLive(body:string,env:Env){
  if(env.LIVE_RESEARCH_ENABLED!=='true')return Response.json({error:'live_research_disabled'},{status:409});
  const p=input.parse(JSON.parse(body)),rows=await env.DB.prepare(`SELECT id,payload,checksum FROM ${kinds[p.kind]} WHERE id>? ORDER BY id LIMIT 20`).bind(p.cursor).all<{id:string;payload:string;checksum:string}>();
  const result:unknown[]=[];let size=0,last=p.cursor;
  for(const row of rows.results){if(await checksum(row.payload)!==row.checksum)throw new Error('archive_checksum_mismatch');if(size+new TextEncoder().encode(row.payload).length>80000&&result.length)break;result.push(JSON.parse(row.payload));size+=new TextEncoder().encode(row.payload).length;last=row.id;}
  const settings=await env.DB.prepare("SELECT key,value FROM settings WHERE key IN('LIVE_SOURCE_DATES','LIVE_SOURCE_CAPTURED_AT')").all<{key:string;value:string}>();
  return Response.json({kind:p.kind,records:result,next_cursor:result.length<rows.results.length||rows.results.length===20?last:null,source_coverage:Object.fromEntries(settings.results.map(r=>[r.key,r.value]))});
}
