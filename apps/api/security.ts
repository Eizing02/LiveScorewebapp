import type {Env} from './types';
export async function readLimited(request:Request,max=100_000){
  if(Number(request.headers.get('content-length')??0)>max)throw new Error('payload_too_large');
  if(!request.body)return '';
  const reader=request.body.getReader();const chunks:Uint8Array[]=[];let size=0;
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();throw new Error('payload_too_large');}chunks.push(value);}
  const data=new Uint8Array(size);let offset=0;for(const c of chunks){data.set(c,offset);offset+=c.length;}
  return new TextDecoder().decode(data);
}
export async function authorize(request:Request,body:string,env:Env,now=Date.now()){
  const path=new URL(request.url).pathname;
  const secret=path.startsWith('/internal/predictions/')?env.ML_IMPORT_SECRET:env.INTERNAL_SYNC_SECRET;
  if(!secret||secret.length<32)throw new Error('unauthorized');
  const timestamp=request.headers.get('x-timestamp')??'',nonce=request.headers.get('x-nonce')??'',signature=request.headers.get('x-signature')??'';
  if(!/^\d{13}$/.test(timestamp)||Math.abs(now-Number(timestamp))>300000||!/^[a-zA-Z0-9-]{16,80}$/.test(nonce)||!/^[a-f0-9]{64}$/.test(signature))throw new Error('unauthorized');
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
  const bytes=Uint8Array.from(signature.match(/../g)!.map(x=>parseInt(x,16)));
  const message=[request.method,new URL(request.url).pathname+new URL(request.url).search,timestamp,nonce,body].join('\n');
  if(!await crypto.subtle.verify('HMAC',key,bytes,new TextEncoder().encode(message)))throw new Error('unauthorized');
  const result=await env.DB.prepare('INSERT OR IGNORE INTO nonces(nonce,expires_at) VALUES(?,?)').bind(nonce,now+600000).run();
  if(!result.meta.changes)throw new Error('replay_rejected');
}
