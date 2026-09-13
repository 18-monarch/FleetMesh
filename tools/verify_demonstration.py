"""Run the real process-based demo and save an independent evidence record."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Session
from demonstration import run_report


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        session = Session(directory)
        checks = {'exclusive_held_zones': True, 'unique_active_jobs': True}
        try:
            session.command('demo', {})
            states = []
            finished = False
            for tick in range(9000):
                session.demonstration.advance(session.runtime.world)
                finished = session.runtime.step()
                snap = session.snapshot()
                held = [z for r in snap['robots'] for z in r['held']]
                jobs = [r['active'] for r in snap['robots'] if r['active']]
                checks['exclusive_held_zones'] &= len(held) == len(set(held))
                checks['unique_active_jobs'] &= len(jobs) == len(set(jobs))
                if tick % 10 == 0 or finished:
                    session.persist()
                    states.append(snap)
                if finished:
                    break
            session.status = 'completed' if finished else 'timeout'
            session.playing = False
            session.persist()
            record = session.store.get(session.run_id, frames=True)
            final = record['snapshot']
            checks.update(completed=finished, seven_jobs=final['complete'] == final['total_jobs'] == 7,
                          zero_detected_collisions=final['collisions'] == 0,
                          distinct_processes=len({r['pid'] for r in final['robots']}) == 3,
                          disturbances_complete=final['demonstration']['schedule_complete'],
                          urgent_completed=final['demonstration']['urgent_state'] == 'done',
                          network_restored=not final['partitioned'],
                          closure_reopened=not any(v['blocked'] for v in final['map_changes'].values()))
            evidence = {'scope':'One real UDP/process demonstration, separate from the 160-run benchmark.',
                        'checks':checks, 'record':record,
                        'limits':['One known scenario on one Linux host.',
                                  'This does not measure real Wi-Fi, physical safety, or a 20% baseline improvement.',
                                  'Scheduling and PIDs can differ across runs.']}
            (root/'evidence/demonstration.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
            (root/'evidence/demonstration_report.html').write_text(run_report(record), encoding='utf-8')
            print(json.dumps({'checks':checks, 'seconds':final['time'], 'reroutes':final['reroutes'],
                              'transfers':final['transfers'], 'frames':len(record['frames'])}, indent=2))
            if not all(checks.values()):
                raise SystemExit(1)
        finally:
            session.close()


if __name__ == '__main__':
    main()
