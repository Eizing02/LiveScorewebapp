import type {CentreFixture} from './types';
export interface ProgramFixture extends CentreFixture {
  provider_league_id:number;home_provider_id:number;away_provider_id:number;
  country:string;competition_type:string;season:string;model_supported:boolean;
  observed_at:string;business_date:string;
}
export interface Competition {id:string;provider_id:number;name:string;country:string;n:number}
export interface ProgramPage {
  date:string;period:'day'|'night';items:ProgramFixture[];total:number;round_total:number;
  page:number;page_size:number;pages:number;competitions:Competition[];countries:string[];
  captured_at:string;data_completeness:string;known_source_dates:string[];
  sync?:{enabled:boolean;interval_minutes:number;last_success_at:string|null;latest:{status:string;completed_at:string|null;error_code:string|null}|null};
  source_dates:{date:string;state:string;captured_at:string|null;rows:number|null}[];
}
