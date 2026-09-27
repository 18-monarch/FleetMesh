'use strict';
// Read-only inspection, replay and review remain separate from robot commands.
let presenting = false;
let inspectorKey = '';
let reviewSource = null;
let reviewGeneration = 0;

function setPresentation(enabled) {
  presenting = enabled;
  document.body.classList.toggle('presenting', enabled);
  $('present-mode').setAttribute('aria-pressed', String(enabled));
  put('present-mode', enabled ? 'Exit presentation' : 'Present');
  if (enabled && view !== 'overview') setView('overview');
  if (shown()) draw(shown());
}
$('present-mode').onclick = () => setPresentation(!presenting);
window.addEventListener('keydown', event => {
  const editing = /INPUT|SELECT|TEXTAREA/.test(event.target?.tagName) || event.target?.isContentEditable;
  if (event.key === 'Escape' && presenting) setPresentation(false);
  if (!editing && !event.ctrlKey && !event.metaKey && !event.altKey &&
      event.key?.toLowerCase() === 'p' && !document.querySelector('dialog[open]')) {
    event.preventDefault();
    setPresentation(!presenting);
  }
});
$('inspect-robot').onchange = event => {
  selectedRobot = Number(event.target.value);
  if (shown()) render(shown(), !!replay);
};
$('floor').onclick = event => {
  const rect = $('floor').getBoundingClientRect();
  const hit = mapHits.find(point => Math.hypot(point.x - (event.clientX - rect.left), point.y - (event.clientY - rect.top)) < 22);
  if (hit) {
    selectedRobot = hit.id;
    if (shown()) render(shown(), !!replay);
  }
};

function renderWorkspace(state, isReplay) {
  const robots = state.robots || [];
  if (!robots.some(robot => robot.id === selectedRobot)) selectedRobot = robots[0]?.id ?? 0;
  const key = robots.map(robot => robot.id).join(',');
  if (key !== inspectorKey) {
    inspectorKey = key;
    $('inspect-robot').innerHTML = robots.map(robot => `<option value="${robot.id}">Robot ${robot.id + 1}</option>`).join('');
  }
  $('inspect-robot').disabled = !robots.length;
  $('inspect-robot').value = String(selectedRobot);
  const robot = robots.find(item => item.id === selectedRobot);
  renderDecision(state, robot, isReplay);
  put('inspect-status', robot ? !robot.alive ? 'Offline' : title(robot.stage) : 'No active run');
  put('inspect-reason', robot?.reason || 'Launch a live run or watch the recorded demo to explore local decisions.');
  const mission = state.jobs?.find(job => job.id === robot?.active);
  $('inspect-facts').innerHTML = robot ? [
    ['Mission', robot.active || 'No active mission'],
    ['Pickup / delivery', mission ? mission.pickup + ' / ' + mission.drop : 'At private dock'],
    ['Zones held', String(robot.held.length)],
    ['Waiting', number(robot.wait_seconds) + ' s']
  ].map(([label, value]) => `<div><span>${label}</span><strong>${escapeHTML(value)}</strong></div>`).join('') : '';
  put('inspect-route', robot?.route?.length ? 'Planned route: ' + robot.route.join(' → ') : 'No route requested.');
  put('inspect-grants', robot ? `Peer grants: ${robot.grants || 0}/${robots.length - 1}. Held zones: ${robot.held.join(', ') || 'none'}.` : 'No peer permissions to inspect.');
  const ended = ['completed', 'timeout', 'failed', 'interrupted', 'stopped', 'replaced'].includes(state.status);
  $('run-result').hidden = !ended && !isReplay;
  put('result-title', isReplay ? replay.source === 'sample' ? 'Recorded demonstration' : 'Recorded experiment' :
    state.status === 'completed' ? 'Every mission returned to dock.' : 'This experiment ended incomplete.');
  put('result-caption', isReplay ? 'Recorded frames are read-only. Review opens the final recorded outcome.' :
    `${state.complete}/${state.total_jobs} missions · ${number(state.time)} simulated seconds · Review the observed checks and mission lead times.`);
  $('review-current').disabled = !connected || pending || (!isReplay && !state.run_id);
  if (isReplay) {
    put('connection', replay.source === 'sample' ? 'Recorded sample / v' + (state.version || '1.1.0') : 'Recorded replay');
    put('replay-play', replay.playing ? 'Pause replay' : 'Play replay');
    $('replay-slider').value = replay.index;
    $('replay-slider').setAttribute('aria-valuetext', number(state.time) + ' simulated seconds');
    put('replay-time', number(state.time) + ' / ' + number(replay.frames.at(-1).time) + ' s');
  }
  if (!isReplay && state.rate) $('speed').value = String(state.rate);
}

async function openReplay(source) {
  try {
    const record = await fetchJSON(source === 'sample' ? '/api/sample' : '/api/runs/' + source + '?frames=1', {}, 12000);
    if (!record.frames?.length) throw Error('This run has no saved frames.');
    replay = {
      source,
      frames: record.frames.map(frame => ({...frame, map: record.config.map, policy: record.mode})),
      index: 0, playing: false, clock: Number(record.frames[0].time), lastWall: null
    };
    $('replay-slider').max = replay.frames.length - 1;
    $('replay-slider').value = 0;
    mapKey = ''; lastJobs = ''; lastEvents = '';
    setView('overview');
    render(replay.frames[0], true);
  } catch (error) { toast(error.message); }
}
$('open-sample').onclick = () => openReplay('sample');
$('replay-play').onclick = () => {
  if (!replay) return;
  if (replay.index === replay.frames.length - 1) {
    replay.index = 0;
    replay.clock = Number(replay.frames[0].time);
  }
  replay.playing = !replay.playing;
  replay.lastWall = null;
  render(replay.frames[replay.index], true);
};
function advanceReplay(now) {
  if (!replay?.playing) return;
  if (replay.lastWall === null) { replay.lastWall = now; return; }
  const elapsed = Math.max(0, Math.min((now - replay.lastWall) / 1000, 1));
  replay.lastWall = now;
  replay.clock += elapsed * Number($('replay-rate').value || 4);
  while (replay.index < replay.frames.length - 1 && Number(replay.frames[replay.index + 1].time) <= replay.clock) replay.index++;
  if (replay.index === replay.frames.length - 1) replay.playing = false;
  render(replay.frames[replay.index], true);
}
setInterval(() => advanceReplay(Date.now()), 100);

$('review-current').onclick = () => loadReview(replay?.source || live?.run_id);
$('review-sample').onclick = () => loadReview('sample');
$('review-replay').onclick = () => openReplay(reviewSource);
async function loadReview(source) {
  if (!source) return toast('Choose a saved run or open the recorded demo.');
  const generation = ++reviewGeneration;
  setView('review');
  $('review-loading').hidden = false;
  $('review-content').hidden = true;
  $('review-empty').hidden = true;
  put('review-loading', 'Loading the run review…');
  try {
    const data = await fetchJSON(source === 'sample' ? '/api/sample/insights' : '/api/runs/' + source + '/insights', {}, 12000);
    if (generation !== reviewGeneration) return;
    reviewSource = source;
    renderReview(data, source);
    $('review-loading').hidden = true;
    $('review-content').hidden = false;
  } catch (error) {
    if (generation !== reviewGeneration) return;
    put('review-loading', 'Could not load this review: ' + error.message);
    $('review-empty').hidden = false;
  }
}
function renderReview(data, source) {
  put('review-source', source === 'sample' ? 'INCLUDED RECORDING / v' + data.version : 'SAVED RUN / ' + data.run_id.slice(0, 8));
  put('review-outcome', data.outcome);
  put('review-meta', `${title(data.map)} · ${title(data.policy)} policy · Seed ${data.seed} · ${title(data.status)} · ${data.saved_frames} saved frames`);
  $('review-report').href = source === 'sample' ? '/api/sample/report' : '/api/runs/' + source + '/report';
  $('review-metrics').innerHTML = [
    ['Missions complete', `${data.completed} / ${data.jobs}`, 'Delivery and return to dock'],
    ['Mission time', number(data.seconds) + ' s', 'From simulation start'],
    ['Detected collisions', data.collisions ?? '—', 'Finite simulated observations'],
    ['Urgent missions', `${data.urgent_completed} / ${data.urgent_jobs}`, 'Returned to dock']
  ].map(([label, value, caption]) => `<article><span>${label}</span><strong>${escapeHTML(value)}</strong><p>${caption}</p></article>`).join('');
  $('review-checks').innerHTML = data.checks.map(check => `<article class="review-check"><div><strong>${escapeHTML(check.name)}</strong><span class="status ${check.status === 'review' ? 'error' : ''}">${check.status === 'observed' ? 'Observed' : check.status === 'review' ? 'Needs review' : 'Not checked'}</span></div><p>${escapeHTML(check.detail)}</p></article>`).join('');
  const maxWait = Math.max(1, ...data.robots.map(robot => robot.wait_seconds));
  $('review-waits').innerHTML = data.robots.map(robot => `<div class="wait-row"><div><strong>Robot ${robot.id + 1}</strong><span>${number(robot.wait_seconds)} s</span></div><div class="wait-track"><i style="width:${robot.wait_seconds / maxWait * 100}%;background:${colors[robot.id]}"></i></div><p>${robot.completed_jobs} missions completed · ${number(robot.distance)} m travelled</p></div>`).join('');
  put('review-actions-count', `${data.transfers} ownership transfers · ${data.reroutes} route recoveries · ${data.actions.length} scripted disturbances`);
  $('review-ledger').innerHTML = data.missions.map(job => `<tr><td><strong>${escapeHTML(job.id)}</strong>${job.priority === 3 ? ' <span class="urgent-label">Urgent</span>' : ''}</td><td>Robot ${job.owner + 1}</td><td>${escapeHTML(title(job.state))}</td><td>${job.delivery_seconds === null ? '—' : number(job.delivery_seconds) + ' s'}</td><td>${job.dock_seconds === null ? '—' : number(job.dock_seconds) + ' s'}</td></tr>`).join('');
  $('review-limits').innerHTML = data.limits.map(limit => `<li>${escapeHTML(limit)}</li>`).join('');
}


// Observations only: this panel never grants permission or changes a robot route.
function renderDecision(state, robot, isReplay) {
  const decision = robot?.decision;
  const offline = robot && !robot.alive;
  put('decision-kind', offline ? 'Offline' : decision ? title(decision.kind) : 'Not recorded');
  put('decision-summary', offline ? `R${robot.id+1} process is offline. Its reservations remain held.` :
    decision?.summary || robot?.reason || 'Start a run to inspect controller decisions.');
  const causes = {
    held_zones: 'last reported holding conflicting zones',
    earlier_request: 'last reported an earlier conflicting request',
    awaiting_grant: 'grant has not arrived; no confirmed blocking cause',
    unconfirmed: 'peer information is missing or stale; permission remains required'
  };
  $('decision-peers').innerHTML = offline ? '' : (decision?.peers || []).map(peer =>
    `<li><strong>R${peer.id+1}</strong> ${escapeHTML(causes[peer.cause] || 'awaiting permission')}${peer.zones.length ? ': '+escapeHTML(peer.zones.join(', ')) : ''}. <span class="fine">${peer.age_seconds === null ? 'No peer observation.' : 'Observation age '+number(peer.age_seconds)+' simulated s.'}</span></li>`).join('');
  put('decision-next', offline ? 'Start a new experiment for recovery. Silence does not release occupied space.' : decision?.next || 'Detailed decision evidence was not stored in this older frame.');
  put('decision-source', `${isReplay ? 'Recorded' : 'Latest'} controller observation${decision ? ' · grants must match the request ID.' : ''} Simulator occupancy below is separate from what each robot knows.`);
  put('traffic-time', state.traffic ? `${number(state.time)} simulated s${isReplay ? ' / recorded' : ''}` : 'Not recorded');
  const roads = state.traffic?.roads || [];
  const occupied = roads.filter(road => road.occupied_by.length);
  $('traffic-summary').textContent = state.traffic ? occupied.length ?
    occupied.map(road => `${road.edge.replace(':', ' – ')}: ${road.occupied_by.map(id=>'R'+(id+1)).join(', ')}`).join(' · ') :
    'No robot currently intersects a road section; robots may be in private docks.' :
    'Section occupancy was not recorded in this frame. Existing routes and robot positions remain available.';
  $('traffic-zones').innerHTML = (state.traffic?.zones || []).map(zone =>
    `<tr><td>${escapeHTML(zone.node)}</td><td>${zone.reserved_by.map(id=>'R'+(id+1)).join(', ') || 'None'}</td><td>${zone.requested_by.map(id=>'R'+(id+1)).join(', ') || 'None'}</td></tr>`).join('') || '<tr><td colspan="3">No recorded reservation detail.</td></tr>';
}

function drawTraffic(ctx, state, xy) {
  const nodes = state.map.nodes;
  for (const road of state.traffic?.roads || []) {
    if (!road.occupied_by.length || road.closed) continue;
    const [a,b] = road.edge.split(':');
    ctx.beginPath();ctx.moveTo(...xy(nodes[a]));ctx.lineTo(...xy(nodes[b]));
    ctx.strokeStyle='#f7c16b66';ctx.lineWidth=17;ctx.stroke();
  }
  const robot = state.robots?.find(item=>item.id===selectedRobot);
  for (const node of robot?.decision?.requested_zones || []) {
    if (!nodes[node]) continue;
    const [x,y] = xy(nodes[node]);
    ctx.beginPath();ctx.arc(x,y,14,0,Math.PI*2);ctx.setLineDash([3,3]);
    ctx.strokeStyle='#f7c16b';ctx.lineWidth=2;ctx.stroke();ctx.setLineDash([]);
  }
}
