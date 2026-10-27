import {z} from 'zod';
import type {Env} from './types';
import {QuotaManager} from './provider';
const routes=['/status','/leagues','/fixtures','/fixtures/statistics','/fixtures/players','/fixtures/lineups','/injuries','/predictions','/fixtures/headtohead'] as const;
const reserveSchema=z.object({route:z.enum(routes),priority:z.enum(['normal','result']).default('normal')}).strict();
const settleSchema=z.object({ticket:z.object({id:z.string().uuid(),window:z.string().regex(/^\d{4}-\d{2}-\d{2}$/)}),status:z.number().int().min(0).max(599),headers:z.record(z.string(),z.number().int().nonnegative()),rate_error:z.boolean().default(false)}).strict();
export async function providerBroker(path:string,body:string,env:Env){
  if(env.PROVIDER_BROKER_ENABLED!=='true'||env.PROVIDER_WINDOW_VERIFIED!=='true')return Response.json({error:'provider_broker_disabled'}, {status:409});
  const manager=new QuotaManager(env.DB,Number(env.PROVIDER_RESET_UTC_HOUR));
  if(path.endsWith('/reserve')){
    const p=reserveSchema.parse(JSON.parse(body));
    try{return Response.json(await manager.reserve(Date.now(),p.priority,p.route));}
    catch{return Response.json({error:'quota_or_rate_exhausted_no_upstream_request'}, {status:429});}
  }
  const p=settleSchema.parse(JSON.parse(body)),headers=new Headers();
  for(const [name,value] of Object.entries(p.headers))if(['x-ratelimit-requests-remaining','x-ratelimit-limit','x-ratelimit-remaining','retry-after'].includes(name.toLowerCase()))headers.set(name,String(value));
  const response=new Response(null,{status:p.status>=200&&p.status<=599?p.status:503,headers});
  await manager.settle(p.ticket,response,Date.now(),p.rate_error);
  return Response.json({settled:true});
}
