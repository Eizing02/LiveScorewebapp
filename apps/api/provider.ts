import {z} from 'zod';
import type {Env} from './types';
import {validRoundDate} from '../../packages/football/window';
const fixtureSchema=z.object({fixture:z.object({id:z.number().int().positive(),date:z.string().datetime({offset:true}),status:z.object({short:z.string()})}),league:z.object({id:z.number().int(),season:z.number().int()}),teams:z.object({home:z.object({id:z.number().int(),name:z.string().min(1)}),away:z.object({id:z.number().int(),name:z.string().min(1)})}),goals:z.object({home:z.number().int().nonnegative().nullable(),away:z.number().int().nonnegative().nullable()})});
export const responseSchema=z.object({errors:z.union([z.array(z.unknown()),z.record(z.string(),z.unknown())]),paging:z.object({current:z.number().int().positive(),total:z.number().int().positive()}),response:z.array(fixtureSchema)});
export type ProviderFixture=z.infer<typeof fixtureSchema>;
export const mockResponse={errors:[],paging:{current:1,total:1},response:[{fixture:{id:1001,date:'2026-10-26T19:00:00+00:00',status:{short:'NS'}},league:{id:39,season:2026},teams:{home:{id:40,name:'Liverpool'},away:{id:42,name:'Arsenal'}},goals:{home:null,away:null}}]};

export class QuotaManager {
  constructor(private db:D1Database,private resetHour:number) {if(!Number.isInteger(resetHour)||resetHour<0||resetHour>23)throw new Error('unverified_reset');}
  window(now:number){return new Date(now-this.resetHour*3600000).toISOString().slice(0,10);}
  async reserve(now:number,priority:'normal'|'result'='normal',route='/fixtures'){
    if(!['/status','/leagues','/fixtures','/fixtures/statistics','/fixtures/players','/fixtures/lineups','/injuries','/predictions','/fixtures/headtohead'].includes(route))throw new Error('unsupported_provider_route');
    const window=this.window(now),cost=route==='/status'?0:1;
    await this.db.prepare('INSERT OR IGNORE INTO quota_windows(id) VALUES(?)').bind(window).run();
    const result=await this.db.prepare(`UPDATE quota_windows SET used=used+?,remaining=remaining-?,last_request_at=? WHERE id=? AND (?=0 OR (used<? AND remaining>15)) AND blocked_until<=? AND NOT EXISTS(SELECT 1 FROM quota_windows WHERE last_request_at>?-MAX(12100,60000/MAX(1,per_minute)+100)) RETURNING used,remaining`).bind(cost,cost,now,window,cost,priority==='result'?85:65,now,now).first<{used:number;remaining:number}>();
    if(!result)throw new Error('quota_or_rate_exhausted');
    const id=crypto.randomUUID();
    await this.db.prepare('INSERT INTO api_usage(id,window_id,attempted_at,route) VALUES(?,?,?,?)').bind(id,window,now,route).run();
    return {id,window,remaining:result.remaining};
  }
  async settle(ticket:{id:string;window:string},response:Response,now:number,rateError=false){
    const integer=(name:string)=>{const raw=response.headers.get(name);return raw!==null&&/^\d+$/.test(raw)?Number(raw):null;};
    const remaining=integer('x-ratelimit-requests-remaining'),minute=integer('x-ratelimit-limit'),minuteRemaining=integer('x-ratelimit-remaining'),retry=integer('retry-after');
    const token=crypto.randomUUID(),blocked=response.status===429||rateError||minuteRemaining===0?now+Math.min(3600,Math.max(60,retry??60))*1000:0;
    await this.db.batch([
      this.db.prepare('UPDATE api_usage SET status=?,remaining=?,settled_at=?,settlement_token=? WHERE id=? AND window_id=? AND settled_at IS NULL').bind(response.status,remaining,now,token,ticket.id,ticket.window),
      this.db.prepare('UPDATE quota_windows SET remaining=MIN(remaining,?),used=MAX(used,100-?),blocked_until=MAX(blocked_until,?),per_minute=MIN(per_minute,?) WHERE id=? AND EXISTS(SELECT 1 FROM api_usage WHERE id=? AND settlement_token=?)').bind(remaining??100,remaining??100,blocked,minute&&minute>0?minute:5,ticket.window,ticket.id,token),
    ]);
  }
}

export class ApiFootballClient {
  constructor(private env:Env,private fetcher:typeof fetch=fetch,private clock:()=>number=Date.now){}
  async fixtures(query:{league:number;season:number}|{date:string;timezone?:'Asia/Bangkok'|'UTC'},priority:'normal'|'result'='normal'){
    if(this.env.LIVE_API_ENABLED!=='true')return {data:responseSchema.parse(mockResponse),mode:'mock' as const,cached:false,stale:false};
    if(this.env.INTEGRATION_APPROVED!=='true'||this.env.PROVIDER_WINDOW_VERIFIED!=='true'||!this.env.API_FOOTBALL_KEY)throw new Error('live_integration_not_approved_or_verified');
    if(this.env.ZERO_COST_MODE==='true'&&'season' in query)throw new Error('known_unsupported_free_season_query');
    // /fixtures returns a filtered set. page belongs to endpoints such as /players and /odds.
    let params:URLSearchParams;
    if('date' in query){if(!validRoundDate(query.date)||query.timezone&&!['Asia/Bangkok','UTC'].includes(query.timezone))throw new Error('invalid_provider_query');params=new URLSearchParams({date:query.date,timezone:query.timezone??'Asia/Bangkok'});}
    else{if(!Number.isInteger(query.league)||query.league<=0||!Number.isInteger(query.season)||query.season<2000)throw new Error('invalid_provider_query');params=new URLSearchParams({league:String(query.league),season:String(query.season)});}
    const key='/fixtures?'+params.toString(),now=this.clock();
    const cache=await this.env.DB.prepare('SELECT * FROM response_cache WHERE key=?').bind(key).first<{payload:string;expires_at:number}>();
    if(cache&&cache.expires_at>now)return {data:responseSchema.parse(JSON.parse(cache.payload)),mode:'live' as const,cached:true,stale:false};
    try{
      const quota=new QuotaManager(this.env.DB,Number(this.env.PROVIDER_RESET_UTC_HOUR));
      const ticket=await quota.reserve(now,priority);
      const response=await this.fetcher('https://v3.football.api-sports.io'+key,{headers:{'x-apisports-key':this.env.API_FOOTBALL_KEY},signal:AbortSignal.timeout(10000)});
      await quota.settle(ticket,response,this.clock());
      if(!response.ok)throw new Error('provider_http_'+response.status);
      const text=await response.text();if(text.length>2_000_000)throw new Error('provider_payload_too_large');
      const data=responseSchema.parse(JSON.parse(text));
      if(Object.keys(data.errors).length)throw new Error('provider_reported_error');
      await this.env.DB.prepare('INSERT INTO response_cache(key,payload,expires_at,fetched_at) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,expires_at=excluded.expires_at,fetched_at=excluded.fetched_at').bind(key,JSON.stringify(data),now+3600000,new Date(now).toISOString()).run();
      return {data,mode:'live' as const,cached:false,stale:false};
    }catch(error){if(cache)return {data:responseSchema.parse(JSON.parse(cache.payload)),mode:'live' as const,cached:true,stale:true};throw error;}
  }
}
