export interface Prediction { probabilities: [number,number,number]; expected_home_goals:number; expected_away_goals:number; top_scorelines:{home:number;away:number;probability:number}[]; tail_mass:number }
export function poisson(home:number,away:number):Prediction {
  if (![home,away].every(x=>Number.isFinite(x)&&x>0&&x<=5)) throw new Error('invalid_goal_rate');
  const distributions=[home,away].map(rate=>{const p=[Math.exp(-rate)];for(let k=1;k<=20;k++)p.push(p[k-1]*rate/k);return p;});
  const probabilities:[number,number,number]=[0,0,0]; const scores:Prediction['top_scorelines']=[];let mass=0;
  for(let h=0;h<=20;h++)for(let a=0;a<=20;a++){const p=distributions[0][h]*distributions[1][a];mass+=p;probabilities[h>a?0:h===a?1:2]+=p;scores.push({home:h,away:a,probability:p});}
  return {probabilities:probabilities.map(p=>p/mass) as [number,number,number],expected_home_goals:home,expected_away_goals:away,top_scorelines:scores.sort((a,b)=>b.probability-a.probability).slice(0,5),tail_mass:Math.max(0,1-mass)};
}
export function eloProbabilities(difference:number):[number,number,number] {const q=10**((difference+60)/400),tie=.65*Math.sqrt(q),sum=q+tie+1;return [q/sum,tie/sum,1/sum];}
