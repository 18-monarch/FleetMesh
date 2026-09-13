"""Read-only run review derived from saved observations, never a safety claim."""


def summarize_run(record):
    snapshot = record.get('snapshot', {})
    jobs = snapshot.get('jobs', [])
    robots = snapshot.get('robots', [])
    frames = record.get('frames', [])
    completed = sum(job.get('state') == 'done' for job in jobs)
    delivered = sum(job.get('delivered_at') is not None for job in jobs)
    elapsed = float(snapshot.get('time', 0))
    has_data = bool(robots) and elapsed > 0
    collisions = snapshot.get('collisions') if has_data else None
    conflicts = []
    duplicate_work = []
    for frame in frames:
        zones, active = {}, {}
        for robot in frame.get('robots', []):
            for zone in set(robot.get('held', [])):
                if zone in zones and zones[zone] != robot['id']:
                    conflicts.append({'time': frame.get('time'), 'zone': zone})
                zones[zone] = robot['id']
            job = robot.get('active')
            if job:
                if job in active and active[job] != robot['id']:
                    duplicate_work.append({'time': frame.get('time'), 'job': job})
                active[job] = robot['id']

    def observed_status(value):
        return 'not_checked' if not frames else 'review' if value else 'observed'

    def duration(job, field):
        value = job.get(field)
        return round(value - job.get('created', 0), 2) if value is not None else None

    ledger = [dict(id=job['id'], owner=job.get('owner'), state=job.get('state'),
                   priority=job.get('priority', 1), pickup=job.get('pickup'), drop=job.get('drop'),
                   delivery_seconds=duration(job, 'delivered_at'),
                   dock_seconds=duration(job, 'completed_at')) for job in jobs]
    pids = [robot.get('pid') for robot in robots]
    distinct_processes = len(pids) >= 3 and all(pids) and len(set(pids)) == len(pids)
    urgent = [job for job in ledger if job['priority'] == 3]
    return {
        'run_id': record['id'], 'status': record.get('status', 'unknown'),
        'version': snapshot.get('version', 'not recorded'),
        'outcome': 'All missions returned to dock' if jobs and completed == len(jobs) else 'Run incomplete',
        'map': record.get('map'), 'policy': record.get('mode'), 'seed': record.get('seed'),
        'seconds': elapsed, 'jobs': len(jobs), 'completed': completed, 'delivered': delivered,
        'collisions': collisions, 'minimum_separation': snapshot.get('minimum_separation'),
        'transfers': snapshot.get('transfers', 0), 'reroutes': snapshot.get('reroutes', 0),
        'urgent_completed': sum(job['state'] == 'done' for job in urgent), 'urgent_jobs': len(urgent),
        'saved_frames': len(frames), 'checks': [
            {'name': 'Swept-body collision counter',
             'status': 'not_checked' if collisions is None else 'observed' if collisions == 0 else 'review',
             'detail': 'No motion observations yet.' if collisions is None else f'{collisions} detected in this simulation.'},
            {'name': 'Exclusive road-zone ownership', 'status': observed_status(conflicts),
             'detail': f'{len(conflicts)} conflicts in {len(frames)} saved frames. Between-frame ownership is not checked here.'},
            {'name': 'One active robot per mission', 'status': observed_status(duplicate_work),
             'detail': f'{len(duplicate_work)} duplicate active assignments in {len(frames)} saved frames.'},
            {'name': 'Independent robot processes',
             'status': 'observed' if distinct_processes else 'not_checked',
             'detail': f'{len(set(pids) - {None})} distinct recorded process IDs. IDs describe the capture, not current OS processes.'}
        ],
        'robots': [{'id': robot['id'], 'wait_seconds': robot.get('wait_seconds', 0),
                    'distance': robot.get('distance', 0), 'online_at_snapshot': robot.get('alive', False),
                    'completed_jobs': sum(job.get('owner') == robot['id'] and job.get('state') == 'done' for job in jobs)}
                   for robot in robots],
        'missions': ledger,
        'actions': (snapshot.get('demonstration') or {}).get('actions', []),
        'limits': [
            'A single run does not establish a speed improvement. Use the paired benchmark for comparisons.',
            'These are finite simulated observations with ideal localization and motion. They do not prove physical safety.',
            'Saved frames sample state. The collision counter comes from the simulator; the ownership review checks saved frames only.',
            'A failed peer can retain road zones and halt progress. Recovery requires a new experiment.'
        ]
    }
