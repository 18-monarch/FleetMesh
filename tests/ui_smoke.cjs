/* Application JavaScript + real HTTP/process backend.
 * A minimal DOM/canvas harness, not a browser rendering or layout test.
 * Optional: node tests/ui_smoke.cjs (Python must be installed).
 */
const fs=require('fs'),path=require('path'),os=require('os'),vm=require('vm'),assert=require('assert'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..');const temp=fs.mkdtempSync(path.join(os.tmpdir(),'fleetmesh-ui-'));
const python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON||process.env.PYTHON||'python3';
const proc=spawn(python,[path.join(root,'server.py'),'--port','0','--data-dir',temp]);
let output='',errors='';proc.stdout.on('data',d=>output+=d);proc.stderr.on('data',d=>errors+=d);
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(condition,timeout=25000){const started=Date.now();while(!condition()){if(Date.now()-started>timeout)throw Error('Timed out: '+output+' '+errors);await delay(50)}}
(async()=>{try{
await until(()=>/http:\/\/127.0.0.1:\d+/.test(output));const base=output.match(/http:\/\/127.0.0.1:\d+/)[0];const html=await(await fetch(base+'/app')).text();const token=html.match(/name="fleetmesh-token" content="([^"]+)"/)[1];
class Element{set innerHTML(value){this._html=value;for(const id of this.childIds||[])elements.delete(id);this.childIds=[];for(const match of value.matchAll(/id="([^"]+)"/g)){this.childIds.push(match[1]);elements.set(match[1],new Element(match[1]))}}get innerHTML(){return this._html||''}constructor(id=''){this.id=id;this.innerHTML='';this.textContent='';this.hidden=false;this.value='';this.dataset={};this.style={};this.classes=new Set();this.classList={toggle:(key,value)=>{if(value)this.classes.add(key);else this.classes.delete(key)}};this.listeners={};this.content='';this.disabled=false;this.values={}}addEventListener(kind,fn){this.listeners[kind]=fn}setAttribute(key,value){this[key]=value}removeAttribute(key){delete this[key]}showModal(){this.open=true}close(){this.open=false}querySelector(){return this.submit||(this.submit=new Element())}getBoundingClientRect(){return {width:900,height:380}}getContext(){return new Proxy({},{get:(object,key)=>object[key]||(()=>{})})}}
const elements=new Map([...html.matchAll(/id="([^"]+)"/g)].map(match=>[match[1],new Element(match[1])]));
const nav=['overview','missions','evidence','history','review'].map(name=>{const element=new Element();element.dataset.view=name;return element});
const doc={getElementById:id=>{assert(elements.has(id),'Missing DOM element '+id);return elements.get(id)},querySelector:selector=>selector==='dialog[open]'?null:({content:token}),querySelectorAll:selector=>selector==='.view'?[...elements.values()].filter(e=>e.id.startsWith('view-')):selector.includes('data-view')?nav:[],body:new Element('body')};
const context=vm.createContext({console,document:doc,window:{devicePixelRatio:1,addEventListener(){}},fetch:(url,options)=>fetch(new URL(url,base),options),setInterval(){},setTimeout,clearTimeout,AbortController,FormData:function(form){return new Map(Object.entries(form.values))}});
vm.runInContext(fs.readFileSync(path.join(root,'web/app.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(root,'web/workspace.js'),'utf8'),context);
await until(()=>vm.runInContext('live !== null',context));
assert.equal((await fetch(base+'/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).status,403);
assert.equal((await fetch(base+'/api/start',{method:'POST',headers:{'Content-Type':'application/json','X-FleetMesh-Token':token},body:'{"robots":99}'})).status,400);
// Bundled replay is usable on a clean install and never launches or replaces a live fleet.
assert(!html.includes('__VERSION__'));
await elements.get('open-sample').onclick();
assert(vm.runInContext('replay.source === "sample" && live.run_id === null',context));
assert(elements.get('connection').textContent.includes('Recorded sample'));
assert(elements.get('new-run').disabled);
elements.get('replay-play').onclick();
vm.runInContext('advanceReplay(1000); advanceReplay(2000)',context);
assert(vm.runInContext('replay.index > 0',context));
elements.get('replay-slider').oninput({target:{value:'10'}});
assert(vm.runInContext('replay.index===10 && !replay.playing',context));
vm.runInContext('replay.clock = Number(replay.frames.at(-1).time); replay.playing=true; replay.lastWall=2000; advanceReplay(2100)',context);
assert(vm.runInContext('replay.index===replay.frames.length-1 && !replay.playing',context));
elements.get('inspect-robot').onchange({target:{value:'2'}});
assert(vm.runInContext('selectedRobot===2',context));
assert(elements.get('inspect-grants').textContent.includes('Held zones'));
elements.get('present-mode').onclick();assert(doc.body.classes.has('presenting'));
assert.equal(elements.get('present-mode')['aria-pressed'],'true');
await elements.get('review-current').onclick();
assert(!doc.body.classes.has('presenting'));
assert(elements.get('review-outcome').textContent.includes('All missions'));
assert(elements.get('review-source').textContent.includes('INCLUDED RECORDING'));
assert(elements.get('review-ledger').innerHTML.includes('J007'));
elements.get('exit-replay').onclick();
const form=elements.get('experiment-form');form.values={map:'warehouse',scenario:'normal',mode:'predictive',seed:'203',robots:'3',jobs:'3'};
await form.onsubmit({preventDefault(){},currentTarget:form});
assert(vm.runInContext('live.robots.length===3',context));
await vm.runInContext('command("speed",{rate:32})',context);
await elements.get('network').onclick();assert(vm.runInContext('live.partitioned',context));await elements.get('network').onclick();
const maintainedButton=elements.get('robot-maintain-0');await elements.get('pause').onclick();assert(vm.runInContext('!live.playing',context));assert.equal(elements.get('robot-maintain-0'),maintainedButton,'Polling must preserve the action button DOM node');await elements.get('pause').onclick();
await vm.runInContext('command("maintenance",{robot:0,available:false})',context);await vm.runInContext('command("maintenance",{robot:0,available:true})',context);
const jobForm=elements.get('job-form');jobForm.values={pickup:'N00',drop:'N12',priority:'3'};await jobForm.onsubmit({preventDefault(){},currentTarget:jobForm});
assert(vm.runInContext('live.total_jobs===4',context));
await vm.runInContext('command("aisle",{edge:"N20:N30",blocked:true})',context);await vm.runInContext('command("aisle",{edge:"N20:N30",blocked:false})',context);
const started=Date.now();while(Date.now()-started<30000){await vm.runInContext('poll()',context);if(vm.runInContext('live.complete===4',context))break;await delay(100)}
assert(vm.runInContext('live.complete===4 && live.collisions===0',context));
await vm.runInContext('loadHistory()',context);assert(elements.get('history-table').innerHTML.includes('Replay'));
const rid=vm.runInContext('live.run_id',context);const csv=await(await fetch(base+'/api/runs/'+rid+'/csv')).text();assert(csv.includes('J004'));assert.equal((await fetch(base+'/api/runs/'+rid+'/unknown')).status,404);
const record=await(await fetch(base+'/api/runs/'+rid+'?frames=1')).json();assert(record.frames.length>1);
await vm.runInContext('loadReview(live.run_id)',context);assert(elements.get('review-metrics').innerHTML.includes('4 / 4'));
const reviewed=await(await fetch(base+'/api/runs/'+rid+'/insights')).json();assert.equal(reviewed.completed,4);assert.equal(reviewed.collisions,0);
await elements.get('open-sample').onclick();assert.equal(vm.runInContext('live.run_id',context),rid);elements.get('exit-replay').onclick();
await elements.get('history-table').onclick({target:{closest(){return {dataset:{replay:rid}}}}});assert(vm.runInContext('replay !== null',context));elements.get('exit-replay').onclick();assert(vm.runInContext('replay===null',context));
elements.get('mission-query').value='J004';elements.get('mission-query').oninput();assert(elements.get('jobs-table').innerHTML.includes('J004'));assert(!elements.get('jobs-table').innerHTML.includes('J001'));
elements.get('mission-query').value='no-such-job';elements.get('mission-query').oninput();assert(elements.get('jobs-table').innerHTML.includes('No missions match'));
elements.get('mission-query').value='';elements.get('mission-query').oninput();
const originalFetch=context.fetch;const retryIds=[];let responseLost=false;
context.fetch=async(url,options)=>{const response=await originalFetch(url,options);if(url==='/api/job'){retryIds.push(options.headers['X-FleetMesh-Request-ID']);if(!responseLost){responseLost=true;throw Error('Simulated response loss after server commit')}}return response};
await vm.runInContext('command("job",{pickup:"N10",drop:"N32",priority:3})',context);context.fetch=originalFetch;
assert.equal(retryIds.length,2);assert.equal(retryIds[0],retryIds[1]);assert(vm.runInContext('live.total_jobs===5',context),'Retry created duplicate mission');
context.fetch=async()=>{throw Error('Simulated disconnected local server')};await vm.runInContext('poll()',context);assert(elements.get('new-run').disabled);context.fetch=originalFetch;await vm.runInContext('poll()',context);assert(!elements.get('new-run').disabled);
await elements.get('launch-demo').onclick();
assert(vm.runInContext('live.policy === "heuristic" && live.demonstration !== null',context));
await vm.runInContext('command("speed",{rate:32})',context);
const demoStarted=Date.now();while(Date.now()-demoStarted<30000){await vm.runInContext('poll()',context);if(vm.runInContext('live.complete===7',context))break;await delay(100)}
assert(vm.runInContext('live.complete===7 && live.collisions===0 && live.demonstration.schedule_complete',context));
const demoId=vm.runInContext('live.run_id',context);
const reportResponse=await fetch(base+'/api/runs/'+demoId+'/report');assert.equal(reportResponse.status,200);
const report=await reportResponse.text();assert(report.includes('All missions returned to dock'));assert(report.includes('J007'));
assert(elements.get('demo-outcome').textContent.includes('All missions returned to dock'));
const savedDemo=await(await fetch(base+'/api/runs/'+demoId+'?frames=1')).json();assert.equal(savedDemo.snapshot.demonstration.actions.length,5);
assert(elements.get('network').disabled,'Completed runs must disable fault controls');
assert(!elements.get('add-job').disabled,'Completed runs should accept a new mission');
await vm.runInContext('command("start",{jobs:1})',context);
await elements.get('robots').onclick({target:{closest(){return {dataset:{robot:'0',action:'kill'}}}}});
assert(elements.get('stop-dialog').open);assert(vm.runInContext('live.robots[0].alive',context),'Opening confirmation must not kill the process');
await elements.get('confirm-stop').onclick();assert(vm.runInContext('!live.robots[0].alive',context));assert(!elements.get('stop-dialog').open);
const result={passed:true,harness:'Application JS with minimal DOM/canvas stubs and a real HTTP/UDP backend; not browser visual QA',checks:['startup','hosted JS rendering functions','invalid token rejection','invalid options rejection','new experiment','network interrupt/restore','pause/resume','maintenance controls','live job submission','aisle close/reopen','four jobs completed','history','CSV export','recorded replay','scripted demo button','seven demo missions completed','persisted disturbance log','HTML run report','stable robot action nodes','mission filtering','unknown route rejection','lost-response retry without duplicate mission','disconnect control state','completed-run controls','explicit process-stop confirmation','recorded demo on clean install without processes','replay playback and scrubbing','replay ends and pauses','robot decision inspector','presentation view and accessible state','sample run review and mission lead times','live run insights API','recorded sample preserves live run','version identity in hosted UI'],collisions:vm.runInContext('live.collisions',context),completed:7};fs.writeFileSync(path.join(root,'evidence/ui_http_checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{proc.kill('SIGINT');await delay(500);if(proc.exitCode===null)proc.kill('SIGKILL');fs.rmSync(temp,{recursive:true,force:true})}})().catch(e=>{console.error(e);process.exitCode=1});
