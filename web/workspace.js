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
