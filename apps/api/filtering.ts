import type {Env} from './types';
const json=(value:unknown,status=200)=>Response.json(value,{status,headers:{'cache-control':'no-store','x-content-type-options':'nosniff'}});
export async function filteringResponse(url:URL,env:Env){
  const supplied=url.searchParams.get('run');
  if(supplied&&!/^[a-z0-9:-]{1,100}$/.test(supplied))return json({error:'invalid_research_run'},400);
  const run=supplied?await env.DB.prepare('SELECT id,payload FROM filter_research_runs WHERE id=?').bind(supplied).first<{id:string;payload:string}>():await env.DB.prepare('SELECT id,payload FROM filter_research_runs ORDER BY rowid DESC LIMIT 1').first<{id:string;payload:string}>();
  if(!run)return json({state:'insufficient_data',publication_state:'research_only',items:[]});
  if(url.pathname==='/api/filtering')return json(JSON.parse(run.payload));
  if(url.pathname!=='/api/filtering/matches')return json({error:'not_found'},404);
  const league=url.searchParams.get('league'),selection=url.searchParams.get('selection')??'selected',page=Number(url.searchParams.get('page')??'1');
  if(league&&!['en.1','es.1','de.1'].includes(league)||!['all','selected','rejected'].includes(selection)||!Number.isInteger(page)||page<1||page>100)return json({error:'invalid_filter'},400);
  const state=selection==='all'?null:selection==='selected'?1:0;
  const records=await env.DB.prepare('SELECT payload FROM filter_research_decisions WHERE run_id=? AND (? IS NULL OR league=?) AND (? IS NULL OR selected=?) ORDER BY match_date,fixture_id LIMIT 25 OFFSET ?').bind(run.id,league,league,state,state,(page-1)*25).all<{payload:string}>();
  const counts=await env.DB.prepare(`SELECT COUNT(*) AS total,COALESCE(SUM(selected),0) AS selected,COALESCE(SUM(CASE WHEN selected=1 AND predicted_outcome=actual_outcome THEN 1 ELSE 0 END),0) AS correct FROM filter_research_decisions WHERE run_id=? AND (? IS NULL OR league=?)`).bind(run.id,league,league).first<{total:number;selected:number;correct:number}>();
  const filteredTotal=selection==='all'?counts!.total:selection==='selected'?counts!.selected:counts!.total-counts!.selected;
  return json({run_id:run.id,publication_state:'research_only',items:records.results.map(r=>JSON.parse(r.payload)),page,page_size:25,total:filteredTotal,pages:Math.ceil(filteredTotal/25),group_counts:counts});
}
