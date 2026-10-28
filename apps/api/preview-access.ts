import type {Env} from './types';

/** Private preview only. Service routes retain their existing HMAC checks. */
export async function previewAccess(request:Request,env:Env):Promise<Response|null>{
  const headers={'cache-control':'private, no-store','vary':'Authorization','x-content-type-options':'nosniff','referrer-policy':'no-referrer'};
  const deny=(error:string,status:number)=>Response.json({error},{status,headers});
  if(env.APP_ENV==='preview'&&env.PREVIEW_AUTH_ENABLED!=='true')return deny('preview_auth_required',503);
  const path=new URL(request.url).pathname;
  if(path.startsWith('/internal/'))return env.PREVIEW_READ_ONLY==='true'?deny('preview_read_only',403):null;
  if(env.PREVIEW_AUTH_ENABLED!=='true')return null;
  if(!env.PREVIEW_PASSWORD||env.PREVIEW_PASSWORD.length<32||!env.PREVIEW_USERNAME||!/^[a-zA-Z0-9_-]{1,40}$/.test(env.PREVIEW_USERNAME))return deny('preview_credentials_not_configured',503);
  const url=new URL(request.url);
  if(url.protocol!=='https:'&&!['localhost','127.0.0.1','[::1]'].includes(url.hostname))return deny('https_required',426);
  const unauthorized=()=>Response.json({error:'preview_login_required'},{status:401,headers:{...headers,'www-authenticate':'Basic realm="Football AI private preview", charset="UTF-8"'}});
  const authorization=request.headers.get('authorization')??'';
  if(authorization.length>1024||!/^Basic [A-Za-z0-9+/]+={0,2}$/i.test(authorization))return unauthorized();
  let supplied:Uint8Array<ArrayBuffer>;
  try{supplied=Uint8Array.from(atob(authorization.slice(6)),c=>c.charCodeAt(0));}catch{return unauthorized();}
  const encoder=new TextEncoder(),key=await crypto.subtle.importKey('raw',encoder.encode(env.PREVIEW_PASSWORD),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
  const expected=encoder.encode(env.PREVIEW_USERNAME+':'+env.PREVIEW_PASSWORD);
  const signature=await crypto.subtle.sign('HMAC',key,expected);
  // WebCrypto performs signature verification; no secret string equality test.
  if(!await crypto.subtle.verify('HMAC',key,signature,supplied))return unauthorized();
  return null;
}
