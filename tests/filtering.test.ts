import {afterAll,beforeAll,describe,it,expect} from 'vitest';
import {database} from './helpers';
import {handle} from '../apps/api';
describe('immutable selective research API',()=>{
  let store:Awaited<ReturnType<typeof database>>;
  beforeAll(async()=>{store=await database(true);});afterAll(async()=>{await store?.mf.dispose();});
  it('reports the frozen rule and explicitly failed confirmation',async()=>{
    const response=await handle(new Request('http://local/api/filtering'),store.env);
    const data=await response.json() as {publication_state:string;selection:{chosen_rule:{id:string}};test:{selected_result:{n:number;correct:number;confirmation_passed:boolean};n_all:number}};
    expect(data.publication_state).toBe('research_only');expect(data.selection.chosen_rule.id).toBe('probability-p70');
    expect(data.test.n_all).toBe(1066);expect(data.test.selected_result.n).toBe(67);expect(data.test.selected_result.correct).toBe(57);expect(data.test.selected_result.confirmation_passed).toBe(false);
  });
  it('paginates all selected evidence without duplicates and reconciles group counts',async()=>{
    const ids=new Set<string>();let correct=0;
    for(let page=1;page<=3;page++){
      const response=await handle(new Request('http://local/api/filtering/matches?page='+page),store.env);
      const data=await response.json() as {items:{id:string;date:string;information_cutoff_date:string;target:number;probabilities_calibrated:number[];decision:{choice:number;selected:boolean};publication_state:string}[];total:number;group_counts:{selected:number;correct:number}};
      expect(data.total).toBe(67);expect(data.group_counts.correct).toBe(57);
      for(const row of data.items){expect(ids.has(row.id)).toBe(false);ids.add(row.id);expect(row.decision.selected).toBe(true);expect(Math.max(...row.probabilities_calibrated)).toBeGreaterThanOrEqual(.7);expect(row.information_cutoff_date<row.date).toBe(true);expect(row.publication_state).toBe('research_only');if(row.target===row.decision.choice)correct++;}
    }
    expect(ids.size).toBe(67);expect(correct).toBe(57);
  });
  it('filters league/rejections without changing the policy or underlying predictions',async()=>{
    const data=await (await handle(new Request('http://local/api/filtering/matches?league=en.1&selection=selected'),store.env)).json() as {items:{league:string}[];total:number;group_counts:{total:number;selected:number;correct:number}};
    expect(data.total).toBe(10);expect(data.group_counts).toEqual({total:380,selected:10,correct:7});expect(data.items.every(r=>r.league==='en.1')).toBe(true);
    const rejected=await (await handle(new Request('http://local/api/filtering/matches?selection=rejected'),store.env)).json() as {total:number;items:{decision:{selected:boolean;reasons:string[]}}[]};
    expect(rejected.total).toBe(999);expect(rejected.items.every(r=>!r.decision.selected&&r.decision.reasons.includes('probability_below_threshold'))).toBe(true);
    for(const query of ['?page=-1','?selection=anything','?league=xx.1','?run=bad%27'])expect((await handle(new Request('http://local/api/filtering/matches'+query),store.env)).status).toBe(400);
    expect((await handle(new Request('http://local/api/filtering',{method:'POST'}),store.env)).status).toBe(405);
    expect((await store.db.prepare('SELECT active_version FROM registry WHERE id=1').first<{active_version:null}>())?.active_version).toBeNull();
    expect((await store.db.prepare('SELECT COUNT(*) n FROM api_usage').first<{n:number}>())?.n).toBe(0);
  });
  it('rejects post-test evidence changes',async()=>{
    await expect(store.db.prepare('UPDATE filter_research_decisions SET selected=1').run()).rejects.toThrow('immutable');
    await expect(store.db.prepare('DELETE FROM filter_research_runs').run()).rejects.toThrow('immutable');
  });
});
