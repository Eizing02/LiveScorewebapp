export type Period='day'|'night';
const HOUR=3600000;
export function validRoundDate(value:string){return /^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;}
export function currentRound(now:number=Date.now()){if(!Number.isFinite(now))throw new Error('invalid_clock');return new Date(now+HOUR).toISOString().slice(0,10);}
export function roundWindow(date:string=currentRound(),period:Period='day'){
  if(!validRoundDate(date)||!['day','night'].includes(period))throw new Error('invalid_round');
  const midnight=Date.parse(date+'T00:00:00Z'),start=midnight+(period==='day'?-1:11)*HOUR,end=midnight+23*HOUR;
  return {date,period,timezone:'Asia/Bangkok',start:new Date(start).toISOString(),end_exclusive:new Date(end).toISOString(),label:period==='day'?'06:00–06:00 วันถัดไป':'18:00–06:00 วันถัดไป'};
}
