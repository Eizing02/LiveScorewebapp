import {lazy,Suspense} from 'react';
import ProviderPreview from './ProviderPreview';
import {navigate,useSearch} from './navigation';
import {PitchIcon} from './BrandLogo';
const ResearchHub=lazy(()=>import('./ResearchHub'));
export default function App(){
  const params=useSearch(),view=params.get('view')??(params.has('match')?'research':'provider');
  const section=view==='research'?'research':['daily','results'].includes(view)?view:'provider';
  return <div className="app-frame"><a className="skip-link" href="#main-content">ข้ามไปเนื้อหา</a><header className="app-header"><a className="brand" href="/" aria-label="สนามข้อมูล หน้าหลัก"><PitchIcon/><span>สนามข้อมูล<small>Football Prediction AI</small></span></a><nav className="primary-nav" aria-label="หน้าข้อมูล">{[['provider','โปรแกรม'],['daily','คู่เด่น'],['results','ผลการทำนาย']].map(([id,label])=><button key={id} aria-current={section===id?'page':undefined} onClick={()=>navigate({view:id,live_match:null})}>{label}</button>)}</nav><div className="header-tools"><span className="local-status">เวลาไทย · รอบ 06:00–06:00</span><button className="research-link" aria-current={section==='research'?'page':undefined} onClick={()=>navigate({view:'research',live_match:null})}>งานวิจัย</button></div></header><main id="main-content" className={section==='research'?'research-main':'workspace-main'}>{section==='research'?<Suspense fallback={<p role="status">กำลังเปิดงานวิจัย…</p>}><ResearchHub/></Suspense>:<ProviderPreview view={section==='daily'?'daily':section==='results'?'results':'fixtures'}/>}</main></div>;
}
