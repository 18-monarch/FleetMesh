import {cp, mkdir, readFile, readdir, rm, writeFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'public');
await rm(out,{recursive:true,force:true});
await mkdir(out,{recursive:true});
await cp(path.join(root,'web'),out,{recursive:true,filter:src=>!src.endsWith('package.json')});
const version=(await readFile(path.join(root,'version.py'),'utf8')).match(/['"]([^'"]+)['"]/)[1];
const landing=(await readFile(path.join(root,'web/experience.html'),'utf8')).replaceAll('__VERSION__',version);
let app=(await readFile(path.join(root,'web/index.html'),'utf8')).replaceAll('__VERSION__',version).replaceAll('__TOKEN__','');
app=app.replace('Local workspace','Private visitor workspace').replace('Runs on your laptop.<br>Simulation data stays here.','Independent simulated robots.<br>History belongs to this browser.').replace('Each run saves snapshots to local SQLite storage.','Each run saves sampled snapshots to Neon PostgreSQL. History is retained for up to 7 days, subject to the public demo’s latest-80-run limit. Keep this browser’s cookies to retain access.').replace('The local server must remain running.','The simulation backend must be available.');
await writeFile(path.join(out,'index.html'),landing);
await writeFile(path.join(out,'app.html'),app);
await rm(path.join(out,'experience.html'));
await cp(path.join(root,'docs/guide.html'),path.join(out,'guide.html'));
await cp(path.join(root,'evidence/summary.json'),path.join(out,'evidence.json'));
for(const file of ['experience.js','app.js']){
 const p=path.join(out,file);await writeFile(p,(await readFile(p,'utf8')).replaceAll('/api/evidence','/evidence.json'));
}
await writeFile(path.join(out,'404.html'),'<!doctype html><title>FleetMesh — Page not found</title><h1>Page not found</h1><p><a href="/">Return to FleetMesh</a></p>');
console.log('Built FleetMesh '+version+' static frontend. Backend requests use /api/* rewrites.');
