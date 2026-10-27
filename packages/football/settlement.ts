import type {ResearchPick,ResearchReport} from './types';
export interface ResultState{status:string;home_goals:number|null;away_goals:number|null;kickoff_utc:string}
export type Grade='win'|'loss'|'void'|'pending';
export function settlePick(pick:ResearchPick,result:ResultState|undefined,now:number):Grade{
  if(!result)return 'pending';
  if(['postponed','cancelled','abandoned','awarded'].includes(result.status))return 'void';
  if(result.status!=='finished'||Date.parse(result.kickoff_utc)>now||!Number.isInteger(result.home_goals)||!Number.isInteger(result.away_goals)||result.home_goals!<0||result.away_goals!<0)return 'pending';
  const h=result.home_goals!,a=result.away_goals!;let correct=false;
  if(pick.market==='1x2')correct=pick.outcome===(h>a?'เหย้าชนะ':h===a?'เสมอ':'เยือนชนะ');
  else if(pick.market==='over_2.5')correct=h+a>=3;
  else if(pick.market==='under_2.5')correct=h+a<=2;
  else if(pick.market==='btts_yes')correct=h>0&&a>0;
  return correct?'win':'loss';
}
export function settleBundle(grades:Grade[]):Grade|'reduced_win'{if(!grades.length||grades.every(g=>g==='void'))return 'void';if(grades.includes('loss'))return 'loss';if(grades.includes('pending'))return 'pending';if(grades.includes('void'))return 'reduced_win';return 'win';}
export function evaluateReport(report:ResearchReport,results:Record<string,ResultState>,now:number){
  const picks=report.picks.filter(p=>p.passed).map(p=>({fixture_id:p.fixture_id,snapshot_id:p.snapshot_id,market:p.market,outcome:p.outcome,grade:settlePick(p,results[p.fixture_id],now)}));
  const bundles=report.bundles.map(b=>({size:b.size,grade:b.legs.length===b.size?settleBundle(b.legs.map(l=>settlePick(l,results[l.fixture_id],now))):'not_created'}));
  return {policy:'analysis-90min-half-lines-v1',report_id:report.id,evaluated_at:new Date(now).toISOString(),mode:'mock_research',picks,bundles,counts:{win:picks.filter(p=>p.grade==='win').length,loss:picks.filter(p=>p.grade==='loss').length,void:picks.filter(p=>p.grade==='void').length,pending:picks.filter(p=>p.grade==='pending').length},note:'Grading analysis events only; reduced/void sets are not counted as full-size wins. No payout or real-world accuracy claim.'};
}
