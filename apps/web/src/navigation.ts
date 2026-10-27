import {useEffect,useState} from 'react';
export function navigate(values:Record<string,string|null>,replace=false,state:unknown=null){
  const url=new URL(location.href);
  for(const [key,value] of Object.entries(values)){if(value===null)url.searchParams.delete(key);else url.searchParams.set(key,value);}
  if(replace)history.replaceState(state,'',url);else history.pushState(state,'',url);
  window.dispatchEvent(new PopStateEvent('popstate'));
}
export function useSearch(){
  const [search,setSearch]=useState(location.search);
  useEffect(()=>{const update=()=>setSearch(location.search);window.addEventListener('popstate',update);return()=>window.removeEventListener('popstate',update);},[]);
  return new URLSearchParams(search);
}
