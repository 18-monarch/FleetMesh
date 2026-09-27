/* Optional real-browser check: npm install --no-save playwright; npx playwright install chromium.
 * Run: node tests/conflict_browser.cjs
 * FLEETMESH_BROWSER_EXECUTABLE may select an already installed Chromium.
 * No cloud credentials needed. Output: test-results/conflict-*.
 */
const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'test-results');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'fleetmesh-conflict-'));
fs.mkdirSync(out, {recursive:true});
const server = spawn(process.env.PYTHON || 'python3', ['start.py','--port','0','--data-dir',temp], {cwd:root});
let output = '', browser;
server.stdout.on('data', d=>output+=d);
server.stderr.on('data', d=>output+=d);
const delay = ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 try {
  for(let n=0;n<100&&!output.includes('running at');n++) await delay(100);
  const base = output.match(/http:\/\/127.0.0.1:\d+/)?.[0];
  assert(base, 'Server failed to start: '+output);
  browser = await chromium.launch({headless:true, executablePath:process.env.FLEETMESH_BROWSER_EXECUTABLE || undefined,
    args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage']});
  const page = await browser.newPage({viewport:{width:1440,height:1050}, reducedMotion:'reduce'});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error') errors.push(m.text())});
  await page.goto(base+'/app');
  await page.locator('#launch-conflict:not([disabled])').waitFor();
  await page.click('#launch-conflict');
  await page.waitForFunction(()=>live?.traffic?.roads.some(r=>r.occupied_by.length) &&
    live.robots.some(r=>r.decision?.peers?.some(p=>p.cause==='held_zones')),null,{timeout:20000});
  await page.click('#pause');await page.waitForFunction(()=>live.status==='paused');
  const rid = await page.evaluate(()=>live.robots.find(r=>r.decision?.peers.some(p=>p.cause==='held_zones')).id);
  await page.selectOption('#inspect-robot',String(rid));
  await page.locator('#inspect-robot').focus();
  await page.keyboard.press('Tab');
  assert.match(await page.locator('#decision-peers').innerText(), /holding conflicting zones/);
  await page.waitForFunction(()=>document.getElementById('toast').hidden);
  await page.locator('.map-surface').screenshot({path:path.join(out,'conflict-desktop.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('.map-surface').screenshot({path:path.join(out,'conflict-mobile.png')});
  const mobile = await page.evaluate(()=>({viewport:innerWidth,document:document.documentElement.scrollWidth}));
  assert.equal(mobile.viewport,mobile.document);
  await page.setViewportSize({width:1440,height:1050});
  const start = await page.evaluate(()=>({id:live.run_id,time:live.time,pids:live.robots.map(r=>r.pid)}));
  assert.equal(new Set(start.pids).size,3);
  const edge = await page.evaluate(()=>live.traffic.roads.find(r=>r.occupied_by.length).edge);
  await page.selectOption('#aisle',edge);await page.click('#close-aisle');
  await page.waitForFunction(e=>live.pending_closures.includes(e),edge);
  assert.match(await page.locator('#aisle-state').innerText(), /Closure queued/);
  await page.click('#open-aisle');await page.waitForFunction(e=>!live.pending_closures.includes(e),edge);
  await page.click('#network');await page.waitForFunction(()=>live.partitioned);
  const before = await page.evaluate(()=>live.time);
  await page.click('#pause');await page.waitForFunction(t=>live.time>t+3,before);
  await page.click('#pause');await page.waitForFunction(()=>live.status==='paused');
  await page.selectOption('#inspect-robot',String(rid));
  assert.match(await page.locator('#decision-peers').innerText(), /stale/);
  await page.click('#network');await page.waitForFunction(()=>!live.partitioned);
  await page.selectOption('#speed','32');await page.click('#pause');
  await page.waitForFunction(()=>live.status==='completed',null,{timeout:60000});
  const outcome = await page.evaluate(()=>({complete:live.complete,jobs:live.total_jobs,collisions:live.collisions,time:live.time}));
  assert.equal(outcome.complete,6);assert.equal(outcome.collisions,0);
  await page.reload();await page.waitForFunction(()=>live?.status==='completed');
  const record = await page.evaluate(async()=>fetchJSON('/api/runs/'+live.run_id+'?frames=1'));
  assert(record.frames.some(f=>f.robots.some(r=>r.decision?.peers.some(p=>p.cause==='held_zones'))));
  const report = await page.evaluate(async()=> (await fetch('/api/runs/'+live.run_id+'/report')).text());
  assert(report.includes('Controller decisions at this snapshot'));
  await page.evaluate(async()=>openReplay(live.run_id));await page.waitForFunction(()=>!!replay);
  assert(await page.locator('#launch-conflict').isDisabled());
  await page.click('#exit-replay');await page.waitForFunction(()=>!replay);
  await page.click('#open-sample');await page.waitForFunction(()=>replay?.source==='sample');
  assert.match(await page.locator('#decision-next').innerText(), /older frame/);
  assert.deepEqual(errors,[]);
  const result={passed:true,source:'Local browser / HTTP / independent UDP agents / SQLite / saved replay',
    start,outcome,frames:record.frames.length,mobile,console_errors:errors,
    checks:['shared-zone wait','three distinct processes','occupied closure and cancellation','stale peer information',
      'network restoration and completion','refresh','saved conflict evidence','HTML report','read-only replay',
      'older recording compatibility','keyboard focus','reduced-motion context','mobile width']};
  fs.writeFileSync(path.join(out,'conflict-browser.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
 } finally {
  if(browser) await browser.close();
  server.kill('SIGINT');
  for(let n=0;n<30&&server.exitCode===null;n++) await delay(100);
  if(server.exitCode===null) server.kill('SIGKILL');
  fs.rmSync(temp,{recursive:true,force:true});
 }
})().catch(error=>{console.error(error);process.exitCode=1});
