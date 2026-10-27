import {z} from 'zod';
import type {Env} from './types';
import {checksum} from './analysis';
const tables={provider_goal_components:4,provider_team_mappings:6,provider_fixture_observations:12,provider_enrichment_observations:7,provider_dataset_versions:4,live_feature_snapshots:8,live_prediction_snapshots:12,live_match_details:6,live_evaluation_revisions:6,settings:2,performance:2} as const;
const input=z.object({records:z.array(z.object({table:z.enum(Object.keys(tables) as [keyof typeof tables,...(keyof typeof tables)[]]),values:z.array(z.union([z.string().max(90000),z.number().finite(),z.null()])).max(12)}).strict()).min(1).max(20)}).strict();
export async function importLive(body:string,env:Env){
  if(env.LIVE_RESEARCH_ENABLED!=='true')return Response.json({error:'live_research_disabled'},{status:409});
  const data=input.parse(JSON.parse(body)),statements:D1PreparedStatement[]=[];
  for(const row of data.records){
    if(row.values.length!==tables[row.table])throw new Error('invalid_live_record_width');
    if(row.table==='settings'&&!['LIVE_IDENTITY_VERSION','LIVE_SOURCE_DATES','LIVE_SOURCE_CAPTURED_AT'].includes(String(row.values[0])))throw new Error('forbidden_live_setting');
    if(row.table==='performance'&&row.values[0]!=='live-implementation')throw new Error('forbidden_live_performance_id');
    if(['provider_goal_components','provider_fixture_observations','provider_enrichment_observations','live_feature_snapshots','live_prediction_snapshots','live_match_details','live_evaluation_revisions'].includes(row.table)){
      const payload=row.values.at(-2),hash=row.values.at(-1);if(typeof payload!=='string'||await checksum(payload)!==hash)throw new Error('invalid_live_record_checksum');
    }
    const verb=row.table==='settings'||row.table==='performance'?'INSERT OR REPLACE':'INSERT OR IGNORE';
    statements.push(env.DB.prepare(`${verb} INTO ${row.table} VALUES(${row.values.map(()=>'?').join(',')})`).bind(...row.values));
  }
  const results=await env.DB.batch(statements);return Response.json({mode:'private_research',records:data.records.length,changes:results.reduce((n,r)=>n+r.meta.changes,0),model_promoted:false});
}
