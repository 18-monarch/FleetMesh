"""Six predeclared process-runtime checks, separate from the 160-run benchmark.

These are functional audit cases on known map families, not a performance
comparison, independent validation campaign or physical safety proof.
"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transport import ProcessRuntime
from warehouse import make_config
from version import VERSION

CASES = [
    (9410, 'compact', 3, 9, 'normal'),
    (9411, 'warehouse', 4, 9, 'network'),
    (9412, 'extended', 6, 12, 'network'),
    (9413, 'warehouse', 3, 9, 'blocked'),
    (9414, 'extended', 6, 12, 'congestion'),
    (9415, 'warehouse', 3, 30, 'normal'),
]

def main():
    root=Path(__file__).resolve().parents[1]
    rows=[]
    for seed,map_name,robots,jobs,scenario in CASES:
        config=make_config(seed,map_name,robots,jobs,scenario,'heuristic')
        runtime=ProcessRuntime(config)
        checks={'exclusive_held_zones':True,'unique_active_jobs':True}
        started=time.monotonic()
        try:
            done=False
            while runtime.world.time < config['max_seconds']:
                done=runtime.step()
                states=runtime.world.states
                zones=[z for r in states for z in r['held']]
                active=[r['active'] for r in states if r['active']]
                checks['exclusive_held_zones'] &= len(zones)==len(set(zones))
                checks['unique_active_jobs'] &= len(active)==len(set(active))
                if done:break
            snap=runtime.world.snapshot()
            deliveries=[e['detail'].split()[0] for e in runtime.world.events if e['kind']=='delivery']
            checks.update(completed=done,zero_detected_collisions=snap['collisions']==0,
                          distinct_processes=len({r.get('pid') for r in snap['robots']})==robots,
                          each_job_delivered_once=len(deliveries)==jobs and len(set(deliveries))==jobs,
                          no_dead_peers=not runtime.world.dead)
            row={'seed':seed,'map':map_name,'robots':robots,'jobs':jobs,'scenario':scenario,
                 'policy':'heuristic','seconds':snap['time'],'complete':snap['complete'],
                 'collisions':snap['collisions'],'minimum_separation':snap['minimum_separation'],
                 'wall_seconds':round(time.monotonic()-started,3),'checks':checks}
            rows.append(row)
            print(json.dumps(row),flush=True)
        finally:runtime.close()
    report={'version':VERSION,'scope':'Six predeclared functional process checks on one Linux host; not a speed benchmark or physical validation.',
            'passed':all(all(r['checks'].values()) for r in rows),'cases':rows}
    (root/'evidence/runtime_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':main()
