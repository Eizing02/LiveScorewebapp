export interface Env {
  DB:D1Database; ASSETS?:Fetcher; ZERO_COST_MODE:string; LIVE_API_ENABLED:string; INTEGRATION_APPROVED:string;
  MODEL_AUTO_PROMOTE:string; SCHEDULER_ENABLED:string; PROVIDER_WINDOW_VERIFIED:string; PROVIDER_RESET_UTC_HOUR:string;
  MOCK_MODE:string; ALLOWED_ORIGIN:string; API_FOOTBALL_KEY?:string; INTERNAL_SYNC_SECRET?:string; ML_IMPORT_SECRET?:string;
  PROVIDER_BROKER_ENABLED?:string;
  LIVE_RESEARCH_ENABLED?:string;
  APP_ENV?:string; PREVIEW_AUTH_ENABLED?:string; PREVIEW_READ_ONLY?:string;
  PREVIEW_USERNAME?:string; PREVIEW_PASSWORD?:string;
}
export interface Fixture {id:string;league_id:string;season:string;home_id:string;away_id:string;match_date:string;kickoff_utc:string|null;status:string;home_goals:number|null;away_goals:number|null;source:string;quality:string}
export interface FeaturePayload {features:number[];home_rate:number;away_rate:number;history_matches:number;cold_start:boolean;information_cutoff_date:string;feature_schema_version:string}
