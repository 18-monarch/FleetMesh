"""Repeatable warehouse disturbances. This module never issues peer grants."""
from copy import deepcopy
from html import escape
import json
from warehouse import edge_key


class Demonstration:
    name = 'Warehouse disruption'
    schedule = [(5, 'urgent'), (12, 'close'), (20, 'interrupt'),
                (28, 'restore'), (45, 'reopen')]

    def __init__(self):
        self.cursor = 0
        self.actions = []
        self.closed_edge = None
        self.urgent_job = None

    def advance(self, world):
        while self.cursor < len(self.schedule) and world.time >= self.schedule[self.cursor][0]:
            _, action = self.schedule[self.cursor]
            self.cursor += 1
            if action == 'urgent':
                job = world.add_job('N00', 'N32', 3)
                self.urgent_job = job['id']
                detail = f"Urgent mission {job['id']} submitted to the peer auction"
            elif action == 'close':
                candidates = []
                for state in world.states:
                    route = state.get('route', [])
                    candidates.extend(edge_key(a, b) for a, b in zip(route, route[1:])
                                      if a.startswith('N') and b.startswith('N'))
                candidates.extend(edge_key(a, b) for a, b in world.layout['edges']
                                  if a.startswith('N') and b.startswith('N'))
                self.closed_edge = next((k for k in candidates if not world.edge_occupied(k)), None)
                if self.closed_edge:
                    world.set_edge(self.closed_edge, True)
                    detail = self.closed_edge + ' closed after confirming the segment is clear'
                else:
                    detail = 'No clear road segment was available; closure skipped'
            elif action in ('interrupt', 'restore'):
                world.partitioned = action == 'interrupt'
                detail = 'Peer messages ' + ('interrupted' if world.partitioned else 'restored')
            else:
                if self.closed_edge:
                    world.set_edge(self.closed_edge, False)
                    detail = self.closed_edge + ' reopened'
                else:
                    detail = 'No demonstration closure to reopen'
            self.actions.append({'time': round(world.time, 2), 'action': action, 'detail': detail})
            world.event('demonstration', detail)

    def snapshot(self, world):
        urgent = next((j for j in world.jobs() if j['id'] == self.urgent_job), None)
        return {'name': self.name, 'actions': deepcopy(self.actions),
                'scheduled_actions': len(self.schedule), 'urgent_job': self.urgent_job,
                'urgent_state': urgent['state'] if urgent else 'not submitted',
                'closed_edge': self.closed_edge,
                'schedule_complete': self.cursor == len(self.schedule),
                'scope': 'Scripted disturbances in a local simulation. Outcomes are observed, not pre-recorded.'}


def run_report(record):
    """Portable HTML report for the last persisted snapshot, including older runs."""
    snap = record.get('snapshot', {})
    demo = snap.get('demonstration') or {}
    e = lambda x: escape(str(x))
    rows = ''.join('<tr>' + ''.join('<td>' + e(j.get(k, '')) + '</td>' for k in
                   ('id', 'owner', 'state', 'pickup', 'drop', 'priority', 'delivered_at', 'completed_at')) + '</tr>'
                   for j in snap.get('jobs', []))
    actions = ''.join(f"<li>{e(a['time'])} s: {e(a['detail'])}</li>" for a in demo.get('actions', []))
    done = bool(snap.get('total_jobs')) and snap.get('complete') == snap.get('total_jobs')
    outcome = 'All missions returned to dock' if done else 'Run incomplete at this snapshot'
    metadata = {k: record.get(k) for k in ('id', 'started', 'status', 'map', 'mode', 'seed', 'robots', 'scenario')}
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FleetMesh run report</title><style>body{{font:16px/1.6 system-ui,sans-serif;color:#17352b;max-width:1050px;margin:45px auto;padding:0 24px}}h1{{font-size:34px}}h2{{margin-top:32px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border-bottom:1px solid #ccd5ce;padding:9px;text-align:left}}pre{{white-space:pre-wrap;background:#f3f6f1;padding:16px}}.scroll{{overflow:auto}}@media print{{body{{margin:0}}h2{{break-after:avoid}}tr{{break-inside:avoid}}}}</style></head><body>
<h1>FleetMesh run report</h1><p><strong>{outcome}.</strong> {e(snap.get('complete', 0))}/{e(snap.get('total_jobs', 0))} missions completed in {e(snap.get('time', 0))} simulated seconds, including return to dock.</p>
<p>Detected inter-robot collisions: <strong>{e(snap.get('collisions', 0))}</strong>. Minimum observed separation: {e(snap.get('minimum_separation'))} m. Route recoveries: {e(snap.get('reroutes', 0))}. Ownership transfers: {e(snap.get('transfers', 0))}.</p>
<h2>Run configuration</h2><pre>{e(json.dumps(metadata, indent=2))}</pre>
<h2>Demonstration actions</h2><p>{e(demo.get('scope', 'No scripted demonstration was attached to this run.'))}</p><ol>{actions}</ol>
<p>Scheduled disturbances complete: {e(demo.get('schedule_complete', 'not applicable'))}. Urgent mission: {e(demo.get('urgent_job', 'not applicable'))}, state: {e(demo.get('urgent_state', 'not applicable'))}.</p>
<h2>Mission ledger</h2><p>Owner uses zero-based robot IDs (0 means Robot 1).</p><div class="scroll"><table><thead><tr><th>Job</th><th>Owner</th><th>State</th><th>Pickup</th><th>Delivery</th><th>Priority</th><th>Delivered at</th><th>Docked at</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Interpretation</h2><p>This report describes one persisted simulation snapshot. It does not establish a speed improvement against a baseline, physical robot safety, or reliable operation on real Wi-Fi. A zero collision count is a finite observation. Waiting during interruption and progress after restoration must be checked in the replay. A stopped peer can halt new grants indefinitely.</p>
<p>The supervisor supplies simulated physics and injects disturbances. Independent robot processes decide routes and exchange permissions over local UDP. Physical edge hardware, noisy localization and braking remain unvalidated. Battery estimates are illustrative.</p></body></html>'''
