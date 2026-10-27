import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const binary=fileURLToPath(new URL('../node_modules/wrangler/bin/wrangler.js',import.meta.url));
const child=spawn(process.execPath,[binary,...process.argv.slice(2)],{stdio:'inherit',env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
child.on('error',error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
child.on('exit',code=>{process.exitCode=code??1;});
