import {afterAll,beforeAll,describe,expect,it} from 'vitest';
import {database,signed} from './helpers';
import {handle} from '../apps/api';
import {QuotaManager} from '../apps/api/provider';
describe('signed global quota broker',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database();store.env.PROVIDER_BROKER_ENABLED='true';store.env.PROVIDER_WINDOW_VERIFIED='true';});afterAll(async()=>{await store?.mf.dispose();});
  it('refuses unsigned or unsupported routes before reserving quota',async()=>{
    expect((await handle(new Request('http://local/internal/provider-quota/reserve',{method:'POST',body:'{}'}),store.env)).status).toBe(401);
    const bad=await signed('http://local/internal/provider-quota/reserve',store.env,JSON.stringify({route:'/unknown'}));expect((await handle(bad,store.env)).status).toBe(400);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM api_usage').first<{n:number}>())?.n).toBe(0);
  });
  it('shares the same ledger with the Worker client and exempts status from daily usage',async()=>{
    const now=Date.parse('2026-10-22T10:00:00Z'),manager=new QuotaManager(store.db,0);
    const ticket=await manager.reserve(now,'normal','/status');
    const window=await store.db.prepare('SELECT used,remaining FROM quota_windows WHERE id=?').bind(ticket.window).first<{used:number;remaining:number}>();expect(window).toEqual({used:0,remaining:100});
    await manager.reserve(now+12100,'normal','/fixtures');
    await expect(manager.reserve(now+12101,'normal','/injuries')).rejects.toThrow();
  });
  it('reconciles provider usage, settles once and respects a lower minute limit',async()=>{
    const now=Date.parse('2026-10-23T10:00:00Z'),manager=new QuotaManager(store.db,0),ticket=await manager.reserve(now);
    await manager.settle(ticket,new Response('{}',{headers:{'x-ratelimit-requests-remaining':'70','x-ratelimit-limit':'2'}}),now);
    await manager.settle(ticket,new Response('{}',{headers:{'x-ratelimit-requests-remaining':'0'}}),now+1);
    expect((await store.db.prepare('SELECT remaining FROM quota_windows WHERE id=?').bind(ticket.window).first<{remaining:number}>())?.remaining).toBe(70);
    await expect(manager.reserve(now+13000)).rejects.toThrow();await manager.reserve(now+30100);
  });
});
