import type {Env} from './types';

/** Fixed CDN image cache. No API account headers, arbitrary URLs or provider queries. */
export async function mediaResponse(url:URL,env:Env){
  if(env.LIVE_RESEARCH_ENABLED!=='true')return new Response(null,{status:404});
  const match=/^\/api\/media\/(teams|leagues)\/([1-9]\d{0,8})\.png$/.exec(url.pathname);
  if(!match)return new Response(null,{status:404});
  const [,kind,raw]=match,id=Number(raw),request=new Request(url.origin+url.pathname);
  const cache=(globalThis.caches as CacheStorage&{default?:Cache}|undefined)?.default;
  const hit=await cache?.match(request);if(hit)return hit;
  const query=kind==='leagues'?'SELECT 1 n FROM program_observations WHERE competition_id=? LIMIT 1':"SELECT 1 n FROM program_observations WHERE json_extract(payload,'$.home_provider_id')=? OR json_extract(payload,'$.away_provider_id')=? LIMIT 1";
  const known=await env.DB.prepare(query).bind(...(kind==='leagues'?[id]:[id,id])).first();
  if(!known)return new Response(null,{status:404});
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);
  try{
    const response=await fetch(`https://media.api-sports.io/football/${kind}/${id}.png`,{redirect:'manual',signal:controller.signal,headers:{accept:'image/png','user-agent':'FootballPredictionAI-local-media/1.0'}});
    if(!response.ok||!response.headers.get('content-type')?.startsWith('image/png')||Number(response.headers.get('content-length')??0)>512000)return new Response(null,{status:404,headers:{'x-media-state':'upstream_rejected'}});
    const bytes=new Uint8Array(await response.arrayBuffer());
    if(bytes.length>512000||[137,80,78,71,13,10,26,10].some((v,i)=>bytes[i]!==v))return new Response(null,{status:404});
    const image=new Response(bytes,{headers:{'content-type':'image/png','cache-control':'public,max-age=86400','x-content-type-options':'nosniff','referrer-policy':'no-referrer'}});
    try{await cache?.put(request,image.clone());}catch{/* A cache outage must not discard a validated image. */}return image;
  }catch{return new Response(null,{status:404,headers:{'x-media-state':'upstream_unavailable'}});}finally{clearTimeout(timer);}
}
