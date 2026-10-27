export function goalMarkets(home:number,away:number){
  if(![home,away].every(v=>Number.isFinite(v)&&v>0&&v<=5))throw new Error('invalid_goal_rate');
  const rate=home+away,markets:Record<string,number>={};
  for(const line of [1.5,2.5,3.5]){let under=Math.exp(-rate),term=under;for(let k=1;k<=Math.floor(line);k++){term*=rate/k;under+=term;}markets['over_'+line]=Math.min(1,Math.max(0,1-under));markets['under_'+line]=1-markets['over_'+line];}
  markets.btts_yes=(1-Math.exp(-home))*(1-Math.exp(-away));markets.btts_no=1-markets.btts_yes;
  return markets;
}
