import {beforeAll,afterAll,describe,it,expect,vi} from 'vitest';
import {database,signed} from './helpers';
import {handle} from '../apps/api';
import {runSync,lockAndEvaluate,upsertFixtures} from '../apps/api/jobs';
import {mockResponse} from '../apps/api/provider';
describe('mock Worker + D1 integration',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database(true);vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-10-25T12:00:00Z'));});afterAll(async()=>{vi.useRealTimers();await store?.mf.dispose();});
  it('serves local fixtures, predictions and real backtest',async()=>{
    const fixtures=await (await handle(new Request('http://local/api/fixtures'),store.env)).json() as {items:unknown[]};expect(fixtures.items).toHaveLength(3);
    expect((await handle(new Request('http://local/api/fixtures?page=-1'),store.env)).status).toBe(400);
    const detail=await (await handle(new Request('http://local/api/matches/mock-1001'),store.env)).json() as {prediction:{probabilities:number[]}};expect(detail.prediction.probabilities.reduce((a,b)=>a+b)).toBeCloseTo(1);
    const report=await (await handle(new Request('http://local/api/model-performance'),store.env)).json() as {final_holdout:{metrics:{logistic:{all:{n:number}}}}};expect(report.final_holdout.metrics.logistic.all.n).toBeGreaterThan(1000);
    expect((await handle(new Request('http://local/api/leagues',{method:'POST'}),store.env)).status).toBe(405);
  });
  it('private routes deny anonymous, stale signatures, replay and invalid probabilities',async()=>{
    expect((await handle(new Request('http://local/internal/sync/dry-run',{method:'POST'}),store.env)).status).toBe(401);
    const req=await signed('http://local/internal/sync/dry-run',store.env,'{}');
    expect((await handle(req.clone() as Request,store.env)).status).toBe(200);expect((await handle(req.clone() as Request,store.env)).status).toBe(409);
    const expired=await signed('http://local/internal/sync/dry-run',store.env,'{}','POST',crypto.randomUUID(),Date.now()-600000);expect((await handle(expired,store.env)).status).toBe(401);
    const bad=await signed('http://local/internal/predictions/import',store.env,JSON.stringify({predictions:[{id:'bad',fixture_id:'mock-1001',model_version:'v1',generated_at:new Date().toISOString(),information_cutoff_date:'2026-05-24',stage:'initial',probabilities:[.5,.5,.5],feature_snapshot_hash:'a'.repeat(64)}]}));expect((await handle(bad,store.env)).status).toBe(400);
    const tooLarge=new Request('http://local/internal/sync/execute',{method:'POST',body:'x'.repeat(100001)});expect((await handle(tooLarge,store.env)).status).toBe(413);
  });
  it('sync is idempotent under concurrent execution, missing live scores stay null',async()=>{
    const now=Date.parse('2026-10-25T00:00:00Z');const results=await Promise.all([runSync(store.env,'same-job',now),runSync(store.env,'same-job',now)]);expect(results.some(r=>r.status==='complete')).toBe(true);
    expect((await runSync(store.env,'same-job',now+60001)).status).toBe('duplicate_job');
    const fixture=await store.db.prepare('SELECT home_goals FROM fixtures WHERE id=?').bind('mock-1001').first<{home_goals:null}>();expect(fixture?.home_goals).toBeNull();
    const calls=await store.db.prepare('SELECT COUNT(*) n FROM api_usage').first<{n:number}>();expect(calls?.n).toBe(0);
  });
  it('imports only approved pre-kickoff snapshots, rejects future-trained models and preserves candidates',async()=>{
    const feature=await store.db.prepare('SELECT snapshot_hash,information_cutoff_date FROM features WHERE fixture_id=?').bind('mock-1002').first<{snapshot_hash:string;information_cutoff_date:string}>();
    await store.db.prepare('INSERT INTO model_versions VALUES(?,?,?,?,?,?,?,?)').bind('test-approved','logistic','2026-07-01','test-sha','test-dataset','test-digest','{}','approved').run();
    const prediction={id:'valid-batch-test',fixture_id:'mock-1002',model_version:'test-approved',generated_at:new Date().toISOString(),information_cutoff_date:feature!.information_cutoff_date,stage:'initial',probabilities:[.5,.25,.25],feature_snapshot_hash:feature!.snapshot_hash};
    const call=async(payload:unknown)=>handle(await signed('http://local/internal/predictions/import',store.env,JSON.stringify({predictions:[payload]})),store.env);
    expect((await call(prediction)).status).toBe(200);expect((await call(prediction)).status).toBe(200);
    expect((await store.db.prepare('SELECT COUNT(*) n FROM predictions WHERE id=?').bind(prediction.id).first<{n:number}>())?.n).toBe(1);
    expect((await call({...prediction,id:'wrong-hash',feature_snapshot_hash:'f'.repeat(64)})).status).toBe(409);
    await store.db.prepare('UPDATE model_versions SET training_cutoff=? WHERE version=?').bind('2027-07-01','test-approved').run();
    expect((await call({...prediction,id:'future-trained'})).status).toBe(409);
    const promote=await signed('http://local/internal/models/promote',store.env,JSON.stringify({version:'unknown-candidate',approved:true}));expect((await handle(promote,store.env)).status).toBe(409);
    expect((await store.db.prepare('SELECT active_version FROM registry WHERE id=1').first<{active_version:null}>())?.active_version).toBeNull();
  });
  it('prediction locks cannot be overwritten and cancelled fixtures do not settle',async()=>{
    await lockAndEvaluate(store.env,'2026-10-27T00:00:00.000Z');
    await expect(store.db.prepare('UPDATE predictions SET probabilities=? WHERE fixture_id=?').bind('[1,0,0]','mock-1001').run()).rejects.toThrow('immutable');
    await store.db.prepare('UPDATE fixtures SET status=?,home_goals=3,away_goals=0 WHERE id=?').bind('awarded','mock-1001').run();
    await lockAndEvaluate(store.env,'2026-10-27T01:00:00.000Z');
    expect((await store.db.prepare('SELECT COUNT(*) n FROM evaluations').first<{n:number}>())?.n).toBe(0);
    const finished=structuredClone(mockResponse.response);finished[0].fixture.status.short='FT';finished[0].goals={home:2,away:1} as never;
    await upsertFixtures(store.env,finished,'mock');await lockAndEvaluate(store.env,'2026-10-27T02:00:00.000Z');
    expect((await store.db.prepare('SELECT COUNT(*) n FROM evaluations').first<{n:number}>())?.n).toBe(1);
  });
  it('retains immutable feature history after the current feature row changes',async()=>{
    const old=await store.db.prepare('SELECT * FROM features WHERE fixture_id=?').bind('mock-1003').first<{snapshot_hash:string;payload:string}>();
    const payload=JSON.stringify({...JSON.parse(old!.payload),history_matches:9999});
    await store.db.prepare('UPDATE features SET snapshot_hash=?,payload=? WHERE fixture_id=?').bind('e'.repeat(64),payload,'mock-1003').run();
    const archived=await store.db.prepare('SELECT payload FROM feature_snapshots WHERE hash=?').bind(old!.snapshot_hash).first<{payload:string}>();
    expect(archived?.payload).toBe(old!.payload);
    await expect(store.db.prepare('DELETE FROM feature_snapshots WHERE hash=?').bind(old!.snapshot_hash).run()).rejects.toThrow('immutable');
    await expect(store.db.prepare('UPDATE features SET snapshot_hash=? WHERE fixture_id=?').bind(old!.snapshot_hash,'mock-1003').run()).rejects.toThrow('collision');
  });
});
