import {afterAll,beforeAll,describe,expect,it,vi} from 'vitest';
import {database} from './helpers';
import {handle} from '../apps/api';

describe('bounded official branding cache',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database();store.env.LIVE_RESEARCH_ENABLED='true';await store.db.prepare('INSERT INTO program_observations VALUES(?,?,?,?,?,?,?,?,?,?,?)').bind('unit','api-football-1',143,'2026-10-27T10:00:00Z','2026-10-27','2026-10-27T08:00:00Z','scheduled','2026-10-27','unit',JSON.stringify({home_provider_id:4,away_provider_id:5}),'unit').run();});
  afterAll(async()=>{vi.unstubAllGlobals();await store.mf.dispose();});
  it('fetches only fixed media URLs without account credentials and validates PNG bytes',async()=>{
    const fetcher=vi.fn<typeof fetch>().mockResolvedValue(new Response(new Uint8Array([137,80,78,71,13,10,26,10,0]),{headers:{'content-type':'image/png'}}));vi.stubGlobal('fetch',fetcher);
    const r=await handle(new Request('http://local/api/media/teams/4.png'),store.env);expect(r.status).toBe(200);expect(r.headers.get('cache-control')).toContain('86400');
    expect(fetcher.mock.calls[0]?.[0]).toBe('https://media.api-sports.io/football/teams/4.png');
    expect(fetcher.mock.calls[0]?.[1]?.redirect).toBe('manual');
    expect(JSON.stringify(fetcher.mock.calls)).not.toMatch(/x-apisports-key|authorization|API_FOOTBALL_KEY/);
    fetcher.mockImplementationOnce(async()=>new Response('not PNG',{headers:{'content-type':'image/png'}}));expect((await handle(new Request('http://local/api/media/teams/5.png'),store.env)).status).toBe(404);
    vi.unstubAllGlobals();
  });
  it('does not proxy arbitrary hosts, unknown identities or disabled projects',async()=>{
    const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
    for(const path of ['teams/999.png','teams/0.png','unknown/4.png','teams/4.svg'])expect((await handle(new Request('http://local/api/media/'+path),store.env)).status).toBe(404);
    expect((await handle(new Request('http://local/api/media/teams/4.png'),{...store.env,LIVE_RESEARCH_ENABLED:'false'})).status).toBe(404);expect(fetcher).not.toHaveBeenCalled();vi.unstubAllGlobals();
  });
});
