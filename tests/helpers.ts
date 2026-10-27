import {Miniflare} from 'miniflare';
import {readFileSync,readdirSync} from 'node:fs';
import type {Env} from '../apps/api/types';
export async function database(seed=false,centre=false,precision=false){
  const mf=new Miniflare({modules:true,script:'export default {fetch(){return new Response("ok")}}',compatibilityDate:'2026-07-30',d1Databases:['DB']});
  const db=await mf.getD1Database('DB');
  // Each migration statement/trigger is kept on one line for D1.exec.
  for(const file of readdirSync('db/migrations').filter(f=>f.endsWith('.sql')).sort())await db.exec(readFileSync('db/migrations/'+file,'utf8').split('\n').filter(l=>l.trim()).join('\n'));
  if(seed){
    await db.exec(readFileSync('db/seed.sql','utf8'));
    const statements=readFileSync('db/seed-selection.sql','utf8').trim().split('\n');
    for(let i=0;i<statements.length;i+=50)await db.exec(statements.slice(i,i+50).join('\n'));
  }
  if(centre){const statements=readFileSync('db/seed-centre.sql','utf8').trim().split('\n');for(let i=0;i<statements.length;i+=50)await db.exec(statements.slice(i,i+50).join('\n'));}
  if(precision){const statements=readFileSync('db/seed-precision.sql','utf8').trim().split('\n');for(let i=0;i<statements.length;i+=50)await db.exec(statements.slice(i,i+50).join('\n'));}
  return {mf,db:db as unknown as D1Database,env:{DB:db,ZERO_COST_MODE:'true',LIVE_API_ENABLED:'false',INTEGRATION_APPROVED:'false',MODEL_AUTO_PROMOTE:'false',SCHEDULER_ENABLED:'false',PROVIDER_WINDOW_VERIFIED:'false',PROVIDER_RESET_UTC_HOUR:'0',MOCK_MODE:'true',ALLOWED_ORIGIN:'http://127.0.0.1:5173',INTERNAL_SYNC_SECRET:'test-only-sync-secret-32-characters-minimum',ML_IMPORT_SECRET:'test-only-ml-secret-32-characters-minimum'} as unknown as Env};
}
export async function signed(url:string,env:Env,body='',method='POST',nonce=crypto.randomUUID(),time=Date.now()){
  const u=new URL(url);const timestamp=String(time),secret=u.pathname.startsWith('/internal/predictions/')?env.ML_IMPORT_SECRET!:env.INTERNAL_SYNC_SECRET!;
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const signature=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode([method,u.pathname+u.search,timestamp,nonce,body].join('\n')));
  return new Request(url,{method,headers:{'x-timestamp':timestamp,'x-nonce':nonce,'x-signature':Array.from(new Uint8Array(signature)).map(b=>b.toString(16).padStart(2,'0')).join(''),'content-type':'application/json'},...(method==='GET'?{}:{body})});
}
