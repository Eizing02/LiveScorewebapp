import {afterAll,beforeAll,describe,expect,it,vi} from 'vitest';
import {database} from './helpers';
import {handle} from '../apps/api';
import {checksum} from '../apps/api/analysis';
import type {ProgramPage} from '../packages/football/program';

describe('programme competition order before pagination',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  let id=100000;
  const seeded:{id:string;provider_league_id:number;kickoff_utc:string}[]=[];
  beforeAll(async()=>{
    vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-10-27T12:00:00Z'));
    store=await database();store.env.LIVE_RESEARCH_ENABLED='true';
    const statements:D1PreparedStatement[]=[];
    async function add(league:number,name:string,country:string,kickoff='2026-10-27T21:00:00.000Z'){
      const f={id:'api-football-'+(++id),observation_id:id.toString(16).padStart(64,'0'),provider_league_id:league,league_id:'provider-'+league,league_name:name,country,home:'Unit Home '+id,away:'Unit Away',home_provider_id:1,away_provider_id:2,kickoff_utc:kickoff,business_date:'2026-10-27',match_date:kickoff.slice(0,10),status:'scheduled',source_date:'2026-10-27',search_text:('Unit Home '+id+' Unit Away').toLowerCase(),observed_at:'2026-10-27T08:00:00.000Z',current_score:null,score_90:null,model_supported:false,analysis:null};
      const payload=JSON.stringify(f);
      statements.push(store.db.prepare('INSERT INTO program_observations VALUES(?,?,?,?,?,?,?,?,?,?,?)').bind(f.observation_id,f.id,league,kickoff,f.business_date,f.observed_at,f.status,f.source_date,f.search_text,payload,await checksum(payload)));
      seeded.push(f);
    }
    // More than a page of early small-league fixtures must not hide late majors.
    for(let n=0;n<31;n++)await add(900010,'Regional League','Albania','2026-10-26T23:00:00.000Z');
    await add(39,'Premier League','England','2026-10-27T22:00:00.000Z');
    await add(39,'Premier League','England','2026-10-27T20:00:00.000Z');
    await add(39,'Premier League','England','2026-10-27T20:00:00.000Z');
    for(const [league,name,country] of [
      [140,'La Liga','Spain'],[135,'Serie A','Italy'],[78,'Bundesliga','Germany'],[61,'Ligue 1','France'],
      [2,'UEFA Champions League','World'],[3,'UEFA Europa League','World'],[848,'UEFA Conference League','World'],
      [40,'Championship','England'],[45,'FA Cup','England'],[143,'Copa del Rey','Spain'],
      [88,'Eredivisie','Netherlands'],[296,'Thai League 1','Thailand'],[71,'Serie A','Brazil'],[141,'Segunda División','Spain'],
      [900001,'Ligue 1','Algeria'],[900002,'Premier League','England'],[900004,'Alpha','Zambia'],[900003,'Alpha','Zambia']
    ] as const)await add(league,name,country);
    await store.db.batch(statements);
  });
  afterAll(async()=>{vi.useRealTimers();await store?.mf.dispose();});
  async function query(params=''){
    const response=await handle(new Request('http://local/api/program/fixtures?date=2026-10-27'+params),store.env);
    expect(response.status).toBe(200);return response.json() as Promise<ProgramPage>;
  }
  async function allPages(params=''){
    const first=await query(params),items=[...first.items];
    for(let page=2;page<=first.pages;page++)items.push(...(await query(params+'&page='+page)).items);
    return {first,items};
  }
  it('puts the five major leagues first, then cups and lower divisions despite earlier minor kickoffs',async()=>{
    const {first,items}=await allPages(),groups=[...new Set(items.map(f=>f.provider_league_id))];
    expect(first.items).toHaveLength(25);expect(first.items[0].provider_league_id).toBe(39);
    expect(groups.slice(0,5)).toEqual([39,140,135,78,61]);
    expect(groups).toEqual(first.competitions.map(c=>c.provider_id));
    for(const [a,b] of [[61,2],[2,3],[3,848],[848,40],[40,45],[45,143],[143,88],[88,296],[296,71],[71,141],[141,900010]])expect(groups.indexOf(a)).toBeLessThan(groups.indexOf(b));
    const premier=items.filter(f=>f.provider_league_id===39);
    expect(premier.map(f=>f.kickoff_utc)).toEqual(['2026-10-27T20:00:00.000Z','2026-10-27T20:00:00.000Z','2026-10-27T22:00:00.000Z']);
    expect(premier[0].id<premier[1].id).toBe(true);
    expect(items).toHaveLength(seeded.length);expect(new Set(items.map(f=>f.id)).size).toBe(seeded.length);
    expect(items.map(f=>f.id).sort()).toEqual(seeded.map(f=>f.id).sort());
    expect((await query()).items.map(f=>f.id)).toEqual(first.items.map(f=>f.id));
  });
  it('uses provider identity for same names and stable country/name/ID fallback across page boundaries',async()=>{
    const {first,items}=await allPages(),groups=[...new Set(items.map(f=>f.provider_league_id))];
    expect(groups.indexOf(135)).toBeLessThan(groups.indexOf(71)); // Italy/Brazil: Serie A
    expect(groups.indexOf(61)).toBeLessThan(groups.indexOf(900001)); // France/Algeria: Ligue 1
    expect(groups.indexOf(39)).toBeLessThan(groups.indexOf(900002)); // Same name and country, different ID
    expect(groups.slice(-5)).toEqual([900010,900001,900002,900003,900004]);
    for(const c of first.competitions)expect(items.filter(f=>f.provider_league_id===c.provider_id)).toHaveLength(c.n);
    expect(items.filter(f=>f.provider_league_id===900010)).toHaveLength(31);
  });
  it('keeps the same order under country, league and following filters without changing counts',async()=>{
    const spain=await query('&country=Spain');
    expect(spain.competitions.map(c=>c.provider_id)).toEqual([140,143,141]);expect(spain.total).toBe(3);
    const followed=await allPages('&following=provider-900010,provider-140,provider-39');
    expect(followed.first.competitions.map(c=>c.provider_id)).toEqual([39,140,900010]);expect(followed.first.total).toBe(35);
    expect(followed.items.slice(0,4).map(f=>f.provider_league_id)).toEqual([39,39,39,140]);
    const single=await query('&league=provider-900010&page=2');expect(single.total).toBe(31);expect(single.items).toHaveLength(6);expect(single.items.every(f=>f.provider_league_id===900010)).toBe(true);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM live_prediction_snapshots').first<{n:number}>())?.n).toBe(0);
  });
});
