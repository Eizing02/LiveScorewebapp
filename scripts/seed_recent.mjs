import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const file=process.argv[2]??'db/seed-centre.sql';
if(!['db/seed-centre.sql','db/seed-precision.sql','db/seed-provider-preview.sql','db/seed-live-research.sql','db/seed-provider-quota.sql'].includes(file))throw new Error('unsupported_local_seed');
const result=spawnSync(process.execPath,['scripts/wrangler.mjs','d1','execute','football-ai','--local','--file='+file],{cwd:fileURLToPath(new URL('../',import.meta.url)),encoding:'utf8',maxBuffer:32*1024*1024,windowsHide:true});
if(result.status!==0){process.stderr.write((result.stderr||result.stdout||String(result.error)).slice(-4000));process.exit(result.status??1);}
const summary=result.stdout.match(/\d+ commands executed successfully/);
console.log('Local D1 only: '+(summary?.[0]??'seed completed')+'. No provider requests or remote database writes.');
