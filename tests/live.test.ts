import {afterAll,beforeAll,describe,expect,it,vi} from 'vitest';
import {database,signed} from './helpers';
import {handle} from '../apps/api';
import {checksum} from '../apps/api/analysis';
import type {ResearchReport} from '../packages/football/types';

describe('real-source private research with ephemeral test fixtures',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  const fixtureId='api-football-900001',kickoff='2026-10-26T12:00:00.000Z';
  const fixture={fixture_id:fixtureId,occurrence_id:'unit-occurrence',observation_id:'unit-observation',league_id:'eng-premier',league_name:'Premier League',provider_league_id:39,home_provider_id:40,away_provider_id:51,home_id:'unit-home',away_id:'unit-away',home:'Unit Home',away:'Unit Away',kickoff_utc:kickoff,date:'2026-10-26',business_date:'2026-10-26',first_seen_at:'2026-10-25T17:00:00.000Z',mapping_version:'unit-mapping',mapping_status:'reviewed',quarantine_reasons:[],status:'scheduled',score_90:null,current_score:null};
  async function observation(value:typeof fixture){const payload=JSON.stringify(value);await store.db.prepare('INSERT INTO provider_fixture_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').bind(value.observation_id,fixtureId,value.occurrence_id,'eng-premier','unit-home','unit-away',value.kickoff_utc,value.business_date,value.first_seen_at,value.status,payload,await checksum(payload)).run();}
  beforeAll(async()=>{
    store=await database();store.env.LIVE_RESEARCH_ENABLED='true';vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-10-26T00:00:00Z'));
    await observation(fixture);
    const values=['unit-feature',fixtureId,'2026-10-25','2026-10-25T18:00:00.000Z','features-v3','unit-dataset',JSON.stringify({values:Array(58).fill(0)})];
    await store.db.prepare('INSERT INTO live_feature_snapshots VALUES(?,?,?,?,?,?,?,?)').bind(...values,await checksum(values[6])).run();
    const p={fixture_id:fixtureId,snapshot_id:'unit-prediction',model_version:'unit-weights',generated_at:'2026-10-25T18:00:00.000Z',cutoff_date:'2026-10-24',training_cutoff:'2026-10-25',dataset_version:'unit',goal_model:'unit',probabilities:[.8,.1,.1],poisson_probabilities:[.8,.1,.1],home_rate:1.8,away_rate:.8,markets:{'over_2.5':.6,'under_2.5':.4,btts_yes:.5},scorelines:[],history_matches:100,venue_matches:[20,20],last_result_dates:['2026-10-20','2026-10-21'],cold_start:false,mode:'private_research',locked:true,feature_schema:'features-v3',research_eligible:true,selection_policy:{id:'unit-p75',threshold:.75}};
    const payload=JSON.stringify(p);
    await store.db.prepare('INSERT INTO live_prediction_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').bind('unit-prediction',fixtureId,fixture.occurrence_id,fixture.observation_id,p.generated_at,kickoff,'unit-feature','unit-weights','unit-runtime','private_research',payload,await checksum(payload)).run();
    await store.db.prepare('INSERT INTO settings VALUES(?,?)').bind('LIVE_SOURCE_DATES',JSON.stringify(['2026-10-26','2026-10-27'])).run();
  });
  afterAll(async()=>{vi.useRealTimers();await store?.mf.dispose();});
  it('requires the private-read flag and reports the correct half-open round',async()=>{
    expect((await handle(new Request('http://local/api/live/fixtures'),{...store.env,LIVE_RESEARCH_ENABLED:'false'})).status).toBe(409);
    const r=await handle(new Request('http://local/api/live/fixtures?date=2026-10-26'),store.env);expect(r.status).toBe(200);
    const value=await r.json() as {items:{analysis:{mode:string}}[];round:{start:string};mode:string};
    expect(value.items).toHaveLength(1);expect(value.mode).toBe('private_research');expect(value.items[0].analysis.mode).toBe('private_research');expect(value.round.start).toBe('2026-10-25T23:00:00.000Z');
    expect((await handle(new Request('http://local/api/live/fixtures?date=2026-02-30'),store.env)).status).toBe(400);
  });
  it('exposes provider branding IDs and missing scores without changing source evidence',async()=>{
    const response=await handle(new Request('http://local/api/live/fixtures?date=2026-10-26'),store.env);
    const value=await response.json() as {items:{home_provider_id:number;away_provider_id:number;provider_league_id:number;score_90:null;current_score:null;observed_at:string}[]};
    expect(value.items[0].home_provider_id).toBe(40);expect(value.items[0].away_provider_id).toBe(51);expect(value.items[0].provider_league_id).toBe(39);
    expect(value.items[0].score_90).toBeNull();expect(value.items[0].current_score).toBeNull();expect(value.items[0].observed_at).toBe(fixture.first_seen_at);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM provider_fixture_observations').first<{n:number}>())?.n).toBe(1);
  });
  it('lists the first prematch snapshot with an ungraded state and bounded pagination',async()=>{
    const response=await handle(new Request('http://local/api/live/results'),store.env);
    const value=await response.json() as {items:{snapshot:{snapshot_id:string};evaluation:null}[];next_offset:null};
    expect(value.items).toHaveLength(1);expect(value.items[0].snapshot.snapshot_id).toBe('unit-prediction');
    expect(value.items[0].evaluation).toBeNull();expect(value.next_offset).toBeNull();
    const otherRound=await (await handle(new Request('http://local/api/live/results?date=2026-10-27'),store.env)).json() as {items:unknown[]};expect(otherRound.items).toHaveLength(0);
    const original=JSON.parse((await store.db.prepare('SELECT payload FROM live_prediction_snapshots WHERE id=?').bind('unit-prediction').first<{payload:string}>())!.payload);
    const later=JSON.stringify({...original,snapshot_id:'later-prediction',generated_at:'2026-10-25T18:30:00.000Z'});
    await store.db.prepare('INSERT INTO live_prediction_snapshots SELECT ?,fixture_id,occurrence_id,observation_id,?,kickoff_utc,feature_id,weights_version,runtime_version,mode,?,? FROM live_prediction_snapshots WHERE id=?').bind('later-prediction','2026-10-25T18:30:00.000Z',later,await checksum(later),'unit-prediction').run();
    for(const [n,grade] of ['loss','win'].entries()){
      const payload=JSON.stringify({prediction_id:'unit-prediction',grade,outcome:n});
      await store.db.prepare('INSERT INTO live_evaluation_revisions VALUES(?,?,?,?,?,?)').bind('grade-'+n,'unit-prediction','result-'+n,`2026-10-25T2${n}:00:00.000Z`,payload,await checksum(payload)).run();
    }
    const revised=await (await handle(new Request('http://local/api/live/results'),store.env)).json() as {items:{snapshot:{snapshot_id:string};evaluation:{grade:string}}[]};
    expect(revised.items).toHaveLength(1);expect(revised.items[0].snapshot.snapshot_id).toBe('unit-prediction');expect(revised.items[0].evaluation.grade).toBe('win');
    expect((await handle(new Request('http://local/api/live/results?offset=-1'),store.env)).status).toBe(400);
  });
  it('rejects modified/deleted snapshots and invalid probability or timing imports',async()=>{
    await expect(store.db.prepare('DELETE FROM live_prediction_snapshots').run()).rejects.toThrow('immutable');
    await expect(store.db.prepare('UPDATE live_feature_snapshots SET payload=?').bind('{}').run()).rejects.toThrow('immutable');
    await expect(store.db.prepare('INSERT INTO live_prediction_snapshots SELECT ?,fixture_id,occurrence_id,observation_id,?,kickoff_utc,feature_id,weights_version,runtime_version,mode,payload,checksum FROM live_prediction_snapshots').bind('late',kickoff).run()).rejects.toThrow();
    await expect(store.db.prepare('INSERT INTO live_prediction_snapshots SELECT ?,fixture_id,occurrence_id,observation_id,generated_at,kickoff_utc,feature_id,weights_version,runtime_version,mode,?,checksum FROM live_prediction_snapshots').bind('invalid','{"probabilities":[0.9,0.9,0.9]}').run()).rejects.toThrow('probabilities');
  });
  it('locks real-source research before kickoff without forcing bundles',async()=>{
    const unsigned=new Request('http://local/internal/live-reports/lock',{method:'POST',body:'{}'});expect((await handle(unsigned,store.env)).status).toBe(401);
    const request=await signed('http://local/internal/live-reports/lock',store.env,JSON.stringify({date:'2026-10-26',period:'day'}));
    const report=await (await handle(request,store.env)).json() as ResearchReport;
    expect(report.mode).toBe('private_research');expect(report.picks.filter(p=>p.passed)).toHaveLength(1);expect(report.bundles.every(b=>b.legs.length===0)).toBe(true);
    await expect(store.db.prepare('DELETE FROM live_daily_reports').run()).rejects.toThrow('immutable');
    expect((await store.db.prepare('SELECT active_version FROM registry WHERE id=1').first<{active_version:null}>())?.active_version).toBeNull();
  });
  it('keeps correction evaluations as revisions and uses 90-minute scores',async()=>{
    const saved=await store.db.prepare('SELECT id FROM live_daily_reports LIMIT 1').first<{id:string}>();expect(saved).not.toBeNull();
    vi.setSystemTime(new Date('2026-10-26T16:00:00Z'));
    const finished={...fixture,observation_id:'result-one',status:'finished_penalties',score_90:[1,1],first_seen_at:'2026-10-26T15:00:00.000Z'};
    await observation(finished as unknown as typeof fixture);
    async function evaluate(){const request=await signed('http://local/internal/live-reports/evaluate',store.env,JSON.stringify({report_id:saved!.id}));return (await handle(request,store.env)).json() as Promise<{mode:string;counts:{win:number;loss:number}}> ;}
    const first=await evaluate();expect(first.mode).toBe('private_research');expect(first.counts.loss).toBe(1);
    await observation({...finished,observation_id:'result-two',status:'finished',score_90:[2,0],first_seen_at:'2026-10-26T15:30:00.000Z'} as unknown as typeof fixture);
    expect((await evaluate()).counts.win).toBe(1);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM live_evaluation_revisions WHERE subject_id=?').bind(saved!.id).first<{n:number}>())?.n).toBe(2);
  });
  it('signed import cannot change the active registry or general settings',async()=>{
    const payload=JSON.stringify({records:[{table:'settings',values:['MODEL_AUTO_PROMOTE','true']}]});const request=await signed('http://local/internal/live/import',store.env,payload);expect((await handle(request,store.env)).status).toBe(400);
    expect((await store.db.prepare('SELECT active_version FROM registry WHERE id=1').first<{active_version:null}>())?.active_version).toBeNull();
  });
  it('exports checksummed archive pages and rejects unsupported kinds',async()=>{
    async function archive(body:unknown){return handle(await signed('http://local/internal/live/export',store.env,JSON.stringify(body)),store.env);}
    expect((await archive({kind:'settings'})).status).toBe(400);
    const first=await (await archive({kind:'observations'})).json() as {records:{observation_id:string}[];source_coverage:Record<string,string>;next_cursor:string|null};
    expect(first.records.length).toBeGreaterThan(0);expect(first.source_coverage.LIVE_SOURCE_DATES).toBeDefined();expect(first.next_cursor).toBeNull();
    expect(first.records.some(r=>r.observation_id==='unit-observation')).toBe(true);
    const component={league:'en.1',model:'unit',weights:{},created_at:'2026-10-26T00:00:00Z'},payload=JSON.stringify(component);
    const request=await signed('http://local/internal/live/import',store.env,JSON.stringify({records:[{table:'provider_goal_components',values:['unit-goal-component',component.created_at,payload,await checksum(payload)]}]}));
    expect((await handle(request,store.env)).status).toBe(200);
    const restored=await (await archive({kind:'goal-components'})).json() as {records:unknown[]};expect(restored.records).toEqual([component]);
    await expect(store.db.prepare('DELETE FROM provider_goal_components').run()).rejects.toThrow('immutable');
  });
});
