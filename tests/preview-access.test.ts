import {describe,it,expect,vi} from 'vitest';
import worker,{handle} from '../apps/api';
import type {Env} from '../apps/api/types';
const password='test-only-preview-password-32-characters';
const env={APP_ENV:'preview',PREVIEW_AUTH_ENABLED:'true',PREVIEW_READ_ONLY:'true',PREVIEW_USERNAME:'owner',PREVIEW_PASSWORD:password,MOCK_MODE:'false',LIVE_API_ENABLED:'false'} as Env;
const request=(path='/',credential='owner:'+password)=>new Request('https://preview.example'+path,{headers:{authorization:'Basic '+btoa(credential)}});
describe('private read-only cloud preview',()=>{
  it('blocks anonymous requests before assets or database access',async()=>{
    const fetch=vi.fn(),prepare=vi.fn();
    for(const path of ['/','/assets/app.js','/api/program/fixtures','/api/health']){
      const r=await handle(new Request('https://preview.example'+path),{...env,ASSETS:{fetch} as unknown as Fetcher,DB:{prepare} as unknown as D1Database});
      expect(r.status).toBe(401);expect(r.headers.get('www-authenticate')).toContain('Basic');expect(r.headers.get('cache-control')).toContain('no-store');
    }
    expect(fetch).not.toHaveBeenCalled();expect(prepare).not.toHaveBeenCalled();
  });
  it('fails closed for disabled authentication, missing credentials and insecure remote HTTP',async()=>{
    expect((await handle(request(),{...env,PREVIEW_AUTH_ENABLED:'false'})).status).toBe(503);
    expect((await handle(request(),{...env,PREVIEW_PASSWORD:undefined})).status).toBe(503);
    expect((await handle(request(),{...env,PREVIEW_PASSWORD:'short'})).status).toBe(503);
    expect((await handle(new Request('http://preview.example',{headers:request().headers}),env)).status).toBe(426);
  });
  it('rejects wrong identities, passwords and malformed authorization without exposing values',async()=>{
    for(const credential of ['wrong:'+password,'owner:wrong'])expect((await handle(request('/api/health',credential),env)).status).toBe(401);
    for(const authorization of ['Basic %%%%','Bearer anything','Basic '+('a'.repeat(1100))])expect((await handle(new Request('https://preview.example',{headers:{authorization}}),env)).status).toBe(401);
    const text=await (await handle(request('/api/health','owner:wrong'),env)).text();expect(text).not.toContain(password);
  });
  it('serves authenticated assets and API responses with private cache headers',async()=>{
    const fetch=vi.fn().mockResolvedValue(new Response('private app',{headers:{'cache-control':'public,max-age=86400'}}));
    const response=await worker.fetch(request(),{...env,ASSETS:{fetch} as unknown as Fetcher});
    expect(response.status).toBe(200);expect(await response.text()).toBe('private app');expect(response.headers.get('cache-control')).toBe('private, no-store');expect(response.headers.get('vary')).toBe('Authorization');
    expect((await worker.fetch(request('/api/health'),env)).status).toBe(200);
    fetch.mockResolvedValueOnce(Response.redirect('https://preview.example/index.html'));
    expect((await worker.fetch(request(),{...env,ASSETS:{fetch} as unknown as Fetcher})).headers.get('cache-control')).toBe('private, no-store');
    const unicode=password+'ไทย',encoded=btoa(String.fromCharCode(...new TextEncoder().encode('owner:'+unicode)));
    expect((await handle(new Request('https://preview.example/api/health',{headers:{authorization:'Basic '+encoded}}),{...env,PREVIEW_PASSWORD:unicode})).status).toBe(200);
  });
  it('blocks signed service writes and scheduled work in the read-only preview',async()=>{
    const prepare=vi.fn();
    expect((await handle(request('/internal/provider-quota/reserve'),{...env,DB:{prepare} as unknown as D1Database})).status).toBe(403);
    expect(prepare).not.toHaveBeenCalled();
    const waitUntil=vi.fn();await worker.scheduled({scheduledTime:Date.now()} as ScheduledController,{...env,SCHEDULER_ENABLED:'true'},{waitUntil} as unknown as ExecutionContext);expect(waitUntil).not.toHaveBeenCalled();
  });
  it('preserves the existing local default and HMAC boundary outside read-only mode',async()=>{
    expect((await handle(new Request('http://localhost/api/health'),{MOCK_MODE:'true'} as Env)).status).toBe(200);
    expect((await handle(new Request('https://preview.example/internal/sync/dry-run',{method:'POST',body:'{}'}),{...env,PREVIEW_READ_ONLY:'false'})).status).toBe(401);
  });
});
