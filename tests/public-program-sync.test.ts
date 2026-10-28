import {beforeAll,afterAll,describe,it,expect} from 'vitest';
import worker,{handle} from '../apps/api';
import {database,signed} from './helpers';

describe('public programme, signed collector only',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database();Object.assign(store.env,{APP_ENV:'public',PREVIEW_AUTH_ENABLED:'false',PREVIEW_READ_ONLY:'true',PROGRAM_SYNC_ENABLED:'true',LIVE_RESEARCH_ENABLED:'true'});});
  afterAll(async()=>{await store?.mf.dispose();});
  it('serves the public website and API without Basic authentication',async()=>{
    const env={...store.env,ASSETS:{fetch:async()=>new Response('public app')} as unknown as Fetcher};
    expect((await worker.fetch(new Request('https://public.example/'),env)).status).toBe(200);
    expect((await handle(new Request('https://public.example/api/health'),env)).status).toBe(200);
    const response=await handle(new Request('https://public.example/api/program/fixtures?date=2026-10-28'),env);
    expect(response.status).toBe(200);expect((await response.json() as {automatic_refresh:boolean}).automatic_refresh).toBe(true);
  });
  it('keeps unsigned imports unauthorized and blocks model, legacy sync and research writes',async()=>{
    for(const path of ['/internal/program/import','/internal/program/sync-status','/internal/provider-quota/reserve'])expect((await handle(new Request('https://public.example'+path,{method:'POST',body:'{}'}),store.env)).status).toBe(401);
    for(const path of ['/internal/models/promote','/internal/sync/execute','/internal/live/import'])expect((await handle(await signed('https://public.example'+path,store.env,'{}'),store.env)).status).toBe(403);
  });
  it('records completed sync, rejects replay/final edits and exposes only safe freshness metadata',async()=>{
    const run={id:crypto.randomUUID(),started_at:new Date(Date.now()-1000).toISOString(),business_date:'2026-10-28',source_dates:['2026-10-28','2026-10-29','2026-10-30']};
    const send=async(status:string)=>handle(await signed('https://public.example/internal/program/sync-status',store.env,JSON.stringify({...run,status,fixtures_count:123})),store.env);
    expect((await send('running')).status).toBe(200);expect((await send('complete')).status).toBe(200);expect((await send('failed')).status).toBe(409);
    const response=await handle(new Request('https://public.example/api/program/fixtures?date=2026-10-28'),store.env);
    const text=await response.text(),data=JSON.parse(text);expect(data.sync.latest.status).toBe('complete');expect(data.sync.last_success_at).toBeTruthy();expect(text).not.toContain(store.env.INTERNAL_SYNC_SECRET);
    const nonce=crypto.randomUUID(),time=Date.now();
    const replay=()=>signed('https://public.example/internal/program/import',store.env,'{}','POST',nonce,time);
    expect((await handle(await replay(),store.env)).status).toBe(400);expect((await handle(await replay(),store.env)).status).toBe(409);
  });
  it('rejects malformed calendar windows and refuses collector writes when disabled',async()=>{
    const body=JSON.stringify({id:crypto.randomUUID(),started_at:new Date(Date.now()-1000).toISOString(),business_date:'2026-10-28',source_dates:['2026-10-28','2026-10-30','2026-10-31'],status:'running'});
    expect((await handle(await signed('https://public.example/internal/program/sync-status',store.env,body),store.env)).status).toBe(400);
    expect((await handle(await signed('https://public.example/internal/program/import',store.env,'{}'),{...store.env,PROGRAM_SYNC_ENABLED:'false'})).status).toBe(403);
  });
});
