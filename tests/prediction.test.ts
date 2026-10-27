import {describe,it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {poisson,eloProbabilities} from '../packages/prediction';
describe('probability math and training/inference parity',()=>{
  it('matches independent reference',()=>{const p=poisson(1.5,1.2);expect(p.probabilities[1]).toBeCloseTo(.2548167775864511,12);expect(p.probabilities.reduce((a,b)=>a+b)).toBeCloseTo(1,12);expect(eloProbabilities(200)[0]).toBeGreaterThan(eloProbabilities(-200)[0]);});
  it('agrees with Python exported fixture snapshots',()=>{const data=JSON.parse(readFileSync('data/mock-feature-export.json','utf8'));for(const row of data.items){const r=poisson(row.payload.home_rate,row.payload.away_rate);for(let i=0;i<3;i++)expect(r.probabilities[i]).toBeCloseTo(row.payload.poisson.probabilities[i],12);expect(eloProbabilities(row.payload.features[0])).toEqual(row.payload.elo);}});
});
