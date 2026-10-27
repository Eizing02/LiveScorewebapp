import {useEffect,useRef,useState} from 'react';
import mediaIndex from './media-index.json';
const localMedia=new Set(mediaIndex);
export function PitchIcon(){return <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect x="3" y="5" width="26" height="22" rx="3" stroke="currentColor" strokeWidth="1.7"/><path d="M16 5v22M3 11h5v10H3m26-10h-5v10h5" stroke="currentColor" strokeWidth="1.7"/><circle cx="16" cy="16" r="4" stroke="currentColor" strokeWidth="1.7"/></svg>;}
export function Arrow({back=false}:{back?:boolean}){return <svg className={back?'arrow back':'arrow'} width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m9 5 7 7-7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg>;}
export function CloseIcon(){return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>;}
export function StarIcon({filled=false}:{filled?:boolean}){return <svg width="18" height="18" viewBox="0 0 24 24" fill={filled?'currentColor':'none'} aria-hidden="true"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"/></svg>;}
export function FilterIcon(){return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 6h16M7 12h10m-7 6h4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>;}
export default function BrandLogo({id,kind='teams',name,large=false}:{id?:number;kind?:'teams'|'leagues';name:string;large?:boolean}){
  const [failed,setFailed]=useState<string|null>(null),src=id&&Number.isInteger(id)&&id>0?`${localMedia.has(kind+'/'+id)?'/media':'/api/media'}/${kind}/${id}.png`:null;
  const holder=useRef<HTMLSpanElement>(null),[visible,setVisible]=useState(false);
  useEffect(()=>{if(!src?.startsWith('/api/'))return;if(!('IntersectionObserver'in window)){setVisible(true);return;}const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setVisible(true);observer.disconnect();}},{rootMargin:'80px'});if(holder.current)observer.observe(holder.current);return()=>observer.disconnect();},[src]);
  return <span ref={holder} className={`brand-logo${large?' large':''}`} aria-hidden="true">{src&&failed!==src&&(visible||src.startsWith('/media/'))?<img src={src} alt="" width={large?48:28} height={large?48:28} loading="lazy" decoding="async" onError={()=>setFailed(src)}/>:<span className="logo-fallback">{name.trim().slice(0,2).toLocaleUpperCase()}</span>}</span>;
}
