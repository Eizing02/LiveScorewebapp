import {afterAll,beforeAll,describe,it,expect,vi} from 'vitest';
import {database} from './helpers';
import {ApiFootballClient,QuotaManager,mockResponse} from '../apps/api/provider';
describe('provider quota and cache against local D1',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database();});afterAll(async()=>{await store?.mf.dispose();});
  it('default mock never calls transport',async()=>{const fetcher=vi.fn(()=>{throw new Error('network_forbidden');});const response=await new ApiFootballClient(store.env,fetcher).fixtures({league:39,season:2026});expect(response.mode).toBe('mock');expect(fetcher).not.toHaveBeenCalled();});
  it('requires verified account and approval for live mode',async()=>{await expect(new ApiFootballClient({...store.env,LIVE_API_ENABLED:'true'}).fixtures({league:39,season:2026})).rejects.toThrow('not_approved');});
  it('atomic reservation permits one concurrent caller and enforces soft/reserve caps',async()=>{
    const manager=new QuotaManager(store.db,0),now=Date.parse('2026-10-20T10:00:00Z');
    const settled=await Promise.allSettled(Array.from({length:8},()=>manager.reserve(now)));
    expect(settled.filter(r=>r.status==='fulfilled')).toHaveLength(1);
    await expect(manager.reserve(now+12000)).rejects.toThrow();
    await manager.reserve(now+12100);
    await store.db.prepare('UPDATE quota_windows SET used=65,last_request_at=0 WHERE id=?').bind('2026-10-20').run();
    await expect(manager.reserve(now+30000)).rejects.toThrow();
    await manager.reserve(now+30000,'result');
    await store.db.prepare('UPDATE quota_windows SET used=85,last_request_at=0 WHERE id=?').bind('2026-10-20').run();
    await expect(manager.reserve(now+50000,'result')).rejects.toThrow();
    await manager.reserve(Date.parse('2026-10-21T00:01:00Z'));
  });
  it('uses provider remaining, backs off on 429, retains stale cache',async()=>{
    const now=Date.parse('2026-10-22T10:00:00Z'),manager=new QuotaManager(store.db,0),ticket=await manager.reserve(now);
    await manager.settle(ticket,new Response('{}',{status:429,headers:{'x-ratelimit-requests-remaining':'0','retry-after':'120'}}),now);
    await expect(manager.reserve(now+130000,'result')).rejects.toThrow();
    await store.db.prepare('INSERT INTO response_cache VALUES(?,?,?,?)').bind('/fixtures?date=2026-10-22&timezone=Asia%2FBangkok',JSON.stringify(mockResponse),now-1,new Date(now).toISOString()).run();
    const fetcher=vi.fn(()=>Promise.resolve(new Response('{}',{status:500})));
    const env={...store.env,LIVE_API_ENABLED:'true',INTEGRATION_APPROVED:'true',PROVIDER_WINDOW_VERIFIED:'true',API_FOOTBALL_KEY:'not-a-real-key-test-only'};
    const stale=await new ApiFootballClient(env,fetcher,()=>now+300000).fixtures({date:'2026-10-22'});
    expect(stale.stale).toBe(true);expect(fetcher).not.toHaveBeenCalled();
  });
  it('validates successful mock transport, caches and handles empty/errors',async()=>{
    let now=Date.parse('2026-10-23T10:00:00Z');const env={...store.env,LIVE_API_ENABLED:'true',INTEGRATION_APPROVED:'true',PROVIDER_WINDOW_VERIFIED:'true',API_FOOTBALL_KEY:'not-a-real-key-test-only'};
    const fetcher=vi.fn(()=>Promise.resolve(Response.json({...mockResponse,response:[]},{headers:{'x-ratelimit-requests-remaining':'90'}})));
    const client=new ApiFootballClient(env,fetcher,()=>now);
    expect((await client.fixtures({date:'2026-10-23'})).data.response).toEqual([]);
    expect((await client.fixtures({date:'2026-10-23'})).cached).toBe(true);expect(fetcher).toHaveBeenCalledTimes(1);expect(fetcher).toHaveBeenCalledWith('https://v3.football.api-sports.io/fixtures?date=2026-10-23&timezone=Asia%2FBangkok',expect.anything());
    now+=15000;
    const invalid=vi.fn(()=>Promise.resolve(Response.json({...mockResponse,errors:{plan:'not covered'}})));
    await expect(new ApiFootballClient(env,invalid,()=>now).fixtures({date:'2026-10-24'})).rejects.toThrow('provider_reported_error');
  });
  it('supports the verified date query without adding a restricted season filter',async()=>{
    const now=Date.parse('2026-10-24T10:00:00Z');const env={...store.env,LIVE_API_ENABLED:'true',INTEGRATION_APPROVED:'true',PROVIDER_WINDOW_VERIFIED:'true',API_FOOTBALL_KEY:'unit-test-key'};
    const fetcher=vi.fn(()=>Promise.resolve(Response.json(mockResponse)));
    const client=new ApiFootballClient(env,fetcher,()=>now);
    await client.fixtures({date:'2026-10-25'});
    expect(fetcher).toHaveBeenCalledWith('https://v3.football.api-sports.io/fixtures?date=2026-10-25&timezone=Asia%2FBangkok',expect.anything());
    expect((await client.fixtures({date:'2026-10-25'})).cached).toBe(true);
    await expect(client.fixtures({date:'2026-02-30'})).rejects.toThrow('invalid_provider_query');
  });
});
