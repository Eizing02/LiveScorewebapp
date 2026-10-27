import {afterAll,beforeAll,describe,expect,it} from 'vitest';
import {database} from './helpers';
import {handle} from '../apps/api';
import {checksum} from '../apps/api/analysis';
describe('recorded provider preview never triggers upstream requests',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database();});afterAll(async()=>{await store?.mf.dispose();});
  it('reports absence of a prepared cache explicitly',async()=>{expect((await handle(new Request('http://local/api/provider-preview'),store.env)).status).toBe(404);});
  it('reads a checksummed cache with mapping pending while live integration stays disabled',async()=>{
    const value={mode:'provider_recorded_preview',total:1,predictions_approved:false,automatic_refresh:false,leagues:[{id:39,name:'Premier League',fixtures:[{provider_fixture_id:101,home:'Home',away:'Away',goals:[null,null],prediction:null,historical_team_mapping:'unverified'}]}]};
    const payload=JSON.stringify(value),key=await checksum(payload);
    await store.db.prepare('INSERT INTO research_report_chunks VALUES(?,?,?)').bind(key,0,payload).run();
    await store.db.prepare('INSERT INTO performance VALUES(?,?)').bind('api-football-preview',JSON.stringify({chunked:true,key,parts:1,checksum:key})).run();
    const response=await handle(new Request('http://local/api/provider-preview'),store.env);
    expect(response.status).toBe(200);expect(await response.json()).toEqual(value);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM api_usage').first<{n:number}>())?.n).toBe(0);
    expect(store.env.LIVE_API_ENABLED).toBe('false');
  });
});
