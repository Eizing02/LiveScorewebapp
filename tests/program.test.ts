import {afterAll,beforeAll,describe,expect,it,vi} from 'vitest';
import {database,signed} from './helpers';
import {handle} from '../apps/api';
import {checksum} from '../apps/api/analysis';
import type {ProgramPage} from '../packages/football/program';

describe('display catalogue is independent of training eligibility',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  function fixture(n:number,league=143,kickoff='2026-10-27T18:00:00.000Z',observed='2026-10-27T08:00:00.000Z'){
    return {id:'api-football-'+n,observation_id:n.toString(16).padStart(64,'0'),provider_league_id:league,league_id:'provider-'+league,league_name:league===143?'Cup':'Other Cup',country:league===143?'Spain':'England',home:'Unit Home '+n,away:'Unit Away',home_provider_id:1,away_provider_id:2,kickoff_utc:kickoff,business_date:kickoff<'2026-10-27T23:00:00.000Z'?'2026-10-27':'2026-10-28',match_date:kickoff.slice(0,10),status:'scheduled',source_date:'2026-10-27',search_text:('Unit Home '+n+' Unit Away').toLowerCase(),observed_at:observed,current_score:null,score_90:null,model_supported:false,analysis:null};
  }
  async function importRows(records:unknown[]){return handle(await signed('http://local/internal/program/import',store.env,JSON.stringify({records})),store.env);}
  async function insert(f:ReturnType<typeof fixture>){const payload=JSON.stringify(f);return importRows([{kind:'fixture',values:[f.observation_id,f.id,f.provider_league_id,f.kickoff_utc,f.business_date,f.observed_at,f.status,f.source_date,f.search_text,payload,await checksum(payload)]}]);}
  beforeAll(async()=>{
    vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-10-27T12:00:00Z'));
    store=await database();store.env.LIVE_RESEARCH_ENABLED='true';
    for(let n=9000;n<9027;n++)expect((await insert(fixture(n,n===9026?200:143))).status).toBe(200);
    for(const date of ['2026-10-27','2026-10-28'])expect((await importRows([{kind:'source',values:[date.slice(-2).padStart(64,'0'),date,'2026-10-27T08:00:00.000Z','recorded',40,'a'.repeat(64)]}])).status).toBe(200);
  });
  afterAll(async()=>{vi.useRealTimers();await store?.mf.dispose();});
  async function query(params=''){const r=await handle(new Request('http://local/api/program/fixtures?date=2026-10-27'+params),store.env);expect(r.status).toBe(200);return r.json() as Promise<ProgramPage>;}
  it('shows non-target competitions and nullable scores with server-wide pagination and filters',async()=>{
    const first=await query();expect(first.total).toBe(27);expect(first.items).toHaveLength(25);expect(first.items[0].analysis).toBeNull();expect(first.items[0].current_score).toBeNull();
    expect((await query('&page=2')).items).toHaveLength(2);
    const searched=await query('&q=9026');expect(searched.total).toBe(1);expect(searched.items[0].country).toBe('England');
    expect((await query('&country=Spain')).total).toBe(26);
    expect((await query('&league=provider-200')).total).toBe(1);
    expect((await query('&following=provider-143')).total).toBe(26);
    expect((await query('&q=%25')).total).toBe(0);
    expect(first.data_completeness).toBe('two_source_dates_recorded');
  });
  it('serves honest empty analysis for a cup without creating predictions',async()=>{
    const r=await handle(new Request('http://local/api/program/analysis/api-football-9000?last=5&scope=all'),store.env);
    const d=await r.json() as {analysis:null;state:string;history:{h2h:{n:number}}};expect(d.analysis).toBeNull();expect(d.state).toBe('model_not_supported');expect(d.history.h2h.n).toBe(0);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM live_prediction_snapshots').first<{n:number}>())?.n).toBe(0);
    expect((await handle(new Request('http://local/api/program/fixtures'),{...store.env,LIVE_RESEARCH_ENABLED:'false'})).status).toBe(409);
  });
  it('applies the latest correction before selecting a round and keeps immutable evidence',async()=>{
    const original=fixture(9000);expect((await insert(original)).status).toBe(200);expect((await query()).total).toBe(27);
    const moved={...fixture(9000,143,'2026-10-28T18:00:00.000Z','2026-10-27T09:00:00.000Z'),observation_id:'f'.repeat(64)};
    expect((await insert(moved)).status).toBe(200);expect((await query()).total).toBe(26);
    await expect(store.db.prepare('DELETE FROM program_observations').run()).rejects.toThrow('immutable');
    expect((await store.db.prepare('SELECT COUNT(*) n FROM program_observations WHERE fixture_id=?').bind(original.id).first<{n:number}>())?.n).toBe(2);
  });
  it('avoids storing unchanged fixtures repeatedly but retains their verification time',async()=>{
    const value={...fixture(9025),observation_id:'d'.repeat(64),observed_at:'2026-10-27T11:00:00.000Z'};
    expect((await insert(value)).status).toBe(200);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM program_observations WHERE fixture_id=?').bind(value.id).first<{n:number}>())?.n).toBe(1);
    expect((await store.db.prepare('SELECT verified_at FROM program_fixture_fingerprints WHERE fixture_id=?').bind(value.id).first<{verified_at:string}>())?.verified_at).toBe(value.observed_at);
  });
  it('distinguishes denied, not-fetched and complete-empty days and rejects unsigned writes',async()=>{
    expect((await handle(new Request('http://local/internal/program/import',{method:'POST',body:'{}'}),store.env)).status).toBe(401);
    expect((await importRows([{kind:'source',values:['e'.repeat(64),'2026-10-28','2026-10-27T10:00:00.000Z','denied',0,'b'.repeat(64)]}])).status).toBe(200);
    const value=await query();expect(value.data_completeness).toBe('partial_source_dates');expect(value.source_dates[1].state).toBe('denied');
    const absent=await handle(new Request('http://local/api/program/fixtures?date=2026-10-29'),store.env);const p=await absent.json() as ProgramPage;expect(p.total).toBe(0);expect(p.source_dates.every(s=>s.state==='not_fetched')).toBe(true);
    for(const [index,day] of ['2026-10-29','2026-10-30'].entries())expect((await importRows([{kind:'source',values:[String(index+1).repeat(64),day,'2026-10-27T10:00:00.000Z','recorded',0,'a'.repeat(64)]}])).status).toBe(200);
    const emptyDay=await (await handle(new Request('http://local/api/program/fixtures?date=2026-10-29'),store.env)).json() as ProgramPage;expect(emptyDay.total).toBe(0);expect(emptyDay.data_completeness).toBe('two_source_dates_recorded');
    expect((await handle(new Request('http://local/api/program/fixtures?date=2026-02-30'),store.env)).status).toBe(400);
    expect((await handle(new Request('http://local/api/program/fixtures?page=-1'),store.env)).status).toBe(400);
  });
});
