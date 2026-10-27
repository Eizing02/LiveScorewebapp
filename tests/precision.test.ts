import {afterAll,beforeAll,describe,expect,it,vi} from 'vitest';
import {database} from './helpers';
import {handle} from '../apps/api';
import {researchPick} from '../packages/football/selection';
import type {CentreFixture} from '../packages/football/types';

describe('precision research integration and eligibility',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database(true,true,true);vi.useFakeTimers({toFake:['Date']});vi.setSystemTime(new Date('2026-10-26T00:00:00Z'));},60000);
  afterAll(async()=>{vi.useRealTimers();await store?.mf.dispose();});
  it('serves real counts together with failed confirmation and uncertainty',async()=>{
    const response=await handle(new Request('http://local/api/research/precision'),store.env);
    expect(response.status).toBe(200);
    const r=await response.json() as {evaluations:Record<string,{n:number;selective:{n:number;correct:number;coverage:number;wilson95:number[]};confirmation:{passed:boolean;prospective_certified:boolean;reasons:string[]}}>};
    const t=r.evaluations.retrospective_test;
    expect(t.n).toBe(3220);expect(t.selective.n).toBe(121);expect(t.selective.correct).toBe(103);
    expect(t.selective.coverage).toBeLessThan(.04);expect(t.selective.wilson95[0]).toBeLessThan(.8);
    expect(t.confirmation.passed).toBe(false);expect(t.confirmation.reasons).toContain('each_supported_league');expect(t.confirmation.prospective_certified).toBe(false);
  });
  it('uses the matching feature schema and rejects lower confidence or unsupported cases',async()=>{
    const centre=await (await handle(new Request('http://local/api/match-centre?date=2026-10-26'),store.env)).json() as {items:CentreFixture[]};
    const f=centre.items.find(x=>x.analysis?.feature_schema==='features-v3')!;
    expect(f.analysis?.feature_schema).toBe('features-v3');expect(f.analysis?.selection_policy?.threshold).toBe(.75);
    const eligible=structuredClone(f);eligible.status='scheduled';eligible.quality='unverified';
    Object.assign(eligible.analysis!,{research_eligible:true,history_matches:100,venue_matches:[20,20],cold_start:false,last_result_dates:['2026-10-20','2026-10-21'],probabilities:[.74,.16,.1]});
    expect(researchPick(eligible,'1x2',Date.now()).reasons).toContain('below_research_threshold_or_invalid');
    eligible.analysis!.probabilities=[.8,.1,.1];expect(researchPick(eligible,'1x2',Date.now()).passed).toBe(true);
    eligible.analysis!.research_eligible=false;expect(researchPick(eligible,'1x2',Date.now()).reasons).toContain('precision_policy_not_eligible');
    eligible.analysis!.research_eligible=true;delete eligible.analysis!.selection_policy;expect(researchPick(eligible,'1x2',Date.now()).passed).toBe(false);
  });
  it('leaves production registry inactive and consumes no API-Football requests',async()=>{
    expect((await store.db.prepare('SELECT active_version FROM registry WHERE id=1').first<{active_version:null}>())?.active_version).toBeNull();
    expect((await store.db.prepare('SELECT COUNT(*) n FROM api_usage').first<{n:number}>())?.n).toBe(0);
    const evidence=await handle(new Request('http://local/api/research/precision'),{...store.env,MOCK_MODE:'false'});
    expect(evidence.status).toBe(200);expect((await evidence.json() as {live_approved:boolean}).live_approved).toBe(false);
  });
});
