import type {CentreFixture,Market,ResearchPick,ResearchReport} from './types';
import {roundWindow,validRoundDate,type Period} from './window';
export const DAILY_POLICY='daily-research-v2-p70-history8-not-live-qualified';
export function researchPick(f:CentreFixture,market:Market,now:number):ResearchPick{
  const s=f.analysis,reasons:string[]=[];let outcome='unavailable',p=0;
  if(s){if(market==='1x2'){const index=s.probabilities.indexOf(Math.max(...s.probabilities));outcome=['เหย้าชนะ','เสมอ','เยือนชนะ'][index];p=s.probabilities[index];}else{outcome=market==='over_2.5'?'สูง 2.5':market==='under_2.5'?'ต่ำ 2.5':'ทั้งสองทีมยิง';p=s.markets[market];}}
  if(!s)reasons.push('missing_snapshot');
  if(f.quality==='clock_boundary_example')reasons.push('clock_example_not_a_pick');
  if(f.status!=='scheduled')reasons.push('not_scheduled');
  if(!Number.isFinite(Date.parse(f.kickoff_utc))||Date.parse(f.kickoff_utc)<=now)reasons.push('already_started_or_invalid_kickoff');
  if(s&&(!Number.isFinite(Date.parse(s.generated_at))||Date.parse(s.generated_at)>now||Date.parse(s.generated_at)>=Date.parse(f.kickoff_utc)||!validRoundDate(s.cutoff_date)||!validRoundDate(s.training_cutoff)||s.cutoff_date>=f.match_date||s.training_cutoff>s.generated_at.slice(0,10)))reasons.push('invalid_temporal_cutoff');
  if(s&&(!s.last_result_dates||s.last_result_dates.length!==2||s.last_result_dates.some(d=>!validRoundDate(d)||d>=f.match_date||(Date.parse(f.match_date)-Date.parse(d))/86400000>45)))reasons.push('old_or_missing_team_history');
  if(s&&(s.history_matches<40||s.venue_matches.length!==2||Math.min(...s.venue_matches)<8||s.cold_start))reasons.push('insufficient_history');
  const threshold=market==='1x2'&&s?.selection_policy?s.selection_policy.threshold:.7;
  if(!Number.isFinite(p)||!Number.isFinite(threshold)||threshold<0||threshold>1||p<threshold||p>1)reasons.push('below_research_threshold_or_invalid');
  if(market==='1x2'&&s?.feature_schema==='features-v3'&&(!s.selection_policy||s.research_eligible!==true))reasons.push('precision_policy_not_eligible');
  if(s&&(s.probabilities.length!==3||s.probabilities.some(v=>!Number.isFinite(v)||v<0||v>1)||Math.abs(s.probabilities.reduce((a,b)=>a+b,0)-1)>1e-6))reasons.push('invalid_probabilities');
  return {fixture_id:f.id,snapshot_id:s?.snapshot_id??'',home_id:f.home_id,away_id:f.away_id,home:f.home,away:f.away,league_name:f.league_name,kickoff_utc:f.kickoff_utc,model_version:s?.model_version??'none',market,outcome,probability:p,passed:reasons.length===0,reasons,live_blockers:[...(f.source.startsWith('mock')?['mock_fixture']:['provider_identity_not_independently_verified']),'source_time_and_mapping_unverified','model_not_approved','new_market_or_league_policy_not_confirmed']};
}
export function buildDailyReport(fixtures:CentreFixture[],date:string,period:Period,now:number,mode:'mock_research'|'private_research'='mock_research'):ResearchReport{
  const precision=fixtures.find(f=>f.analysis?.feature_schema==='features-v3')?.analysis;const policyVersion=precision?DAILY_POLICY+':'+precision.model_version.split(':')[0]+':'+(precision.selection_policy?.id??'unqualified'):DAILY_POLICY;
  const round=roundWindow(date,period),inWindow=fixtures.filter(f=>f.kickoff_utc>=round.start&&f.kickoff_utc<round.end_exclusive);
  const picks=inWindow.flatMap(f=>(['1x2','over_2.5','under_2.5','btts_yes'] as Market[]).map(m=>researchPick(f,m,now))).sort((a,b)=>Number(b.passed)-Number(a.passed)||b.probability-a.probability||a.fixture_id.localeCompare(b.fixture_id)||a.market.localeCompare(b.market));
  const candidates=picks.filter(p=>p.market==='1x2'&&p.passed),seenTeams=new Set<string>(),seenFixtures=new Set<string>(),unique:ResearchPick[]=[];
  for(const p of candidates){if(seenFixtures.has(p.fixture_id)||seenTeams.has(p.home_id)||seenTeams.has(p.away_id))continue;unique.push(p);seenFixtures.add(p.fixture_id);seenTeams.add(p.home_id);seenTeams.add(p.away_id);}
  const bundles=[3,5].map(size=>({size,legs:unique.length>=size?unique.slice(0,size):[],independent_estimate:unique.length>=size?unique.slice(0,size).reduce((p,l)=>p*l.probability,1):null,status:unique.length>=size?'research_independence_assumption_unconfirmed':'insufficient_qualified_fixtures'}));
  const goalFixtures=inWindow.filter(f=>{const a=f.analysis;return a&&[a.home_rate,a.away_rate].every(v=>Number.isFinite(v)&&v>0&&v<=5)&&Number.isFinite(a.markets['over_2.5'])&&researchPick(f,'over_2.5',now).reasons.every(r=>r==='below_research_threshold_or_invalid');});
  return {id:`${policyVersion}:${date}:${period}:${new Date(now).toISOString()}`,round,generated_at:new Date(now).toISOString(),mode,policy_version:policyVersion,locked:false,fixture_count:inWindow.length,picks,bundles,goal_ranking:goalFixtures.map(f=>({fixture_id:f.id,home:f.home,away:f.away,expected_total:f.analysis!.home_rate+f.analysis!.away_rate,over25:f.analysis!.markets['over_2.5']})).sort((a,b)=>b.expected_total-a.expected_total||a.fixture_id.localeCompare(b.fixture_id)),limitations:[mode==='private_research'?'โปรแกรมจริง คำทำนายวิจัย ยังไม่อนุมัติโมเดลใช้งานจริง':'ข้อมูลโปรแกรมจำลอง ใช้ดูการทำงานของระบบ',precision?'1X2 ใช้กติกา validation '+(precision.selection_policy?.threshold??0)*100+'% เฉพาะกลุ่มที่รองรับ ยังไม่รับรองอนาคต':'เกณฑ์ 70% เป็นการทดลอง ยังไม่ยืนยันกับลีกและตลาดใหม่','โมเดล/การสอบเทียบของแต่ละตลาดมีที่มาต่างกัน ตรวจผลแยกกัน','ชุดแสดงผลคูณภายใต้สมมติฐานอิสระ ยังไม่มีผลทดสอบว่าถูกครบชุดจริง','ไม่เติมคู่ให้ครบจำนวนเมื่อไม่มีคู่ผ่านเกณฑ์']};
}
