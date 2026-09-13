"""Physics, local sensors and deterministic virtual peer-network experiments."""
import heapq
import math
import random
from agent import Agent
from warehouse import DT, RADIUS, edge_key


def swept_separation(a, b, c, d):
    relative = (a[0]-c[0], a[1]-c[1])
    velocity = (b[0]-a[0]-d[0]+c[0], b[1]-a[1]-d[1]+c[1])
    norm = sum(v*v for v in velocity)
    t = max(0., min(1., -sum(r*v for r, v in zip(relative, velocity))/norm)) if norm else 0.
    return math.hypot(relative[0]+t*velocity[0], relative[1]+t*velocity[1])


class World:
    def __init__(self, config):
        self.config = config
        self.layout = config['map']
        self.count = config['robots']
        self.positions = [self.layout['nodes'][home] for home in self.layout['homes']]
        self.states = [{'id': i, 'position': p, 'alive': True, 'held': [], 'stage': 'idle', 'distance': 0, 'wait_seconds': 0, 'active': None, 'available': True, 'reason': 'Starting agent', 'route': [], 'grants': 0, 'request': None, 'battery': 100, 'transfers': 0, 'reroutes': 0, 'model_calls': 0} for i, p in enumerate(self.positions)]
        self.job_views = [[] for _ in range(self.count)]
        self.catalog = list(config['jobs'])
        self.available = [True]*self.count
        self.map_changes = {}
        self.pending_closures = set()
        self.partitioned = False
        self.time = 0.
        self.collisions = 0
        self.contacts = set()
        self.min_separation = math.inf
        self.events = []
        self.dead = set()
        self.trace = []
        if config['scenario'] == 'blocked':
            self.set_edge(edge_key('N10', 'N11'), True)

    def event(self, kind, detail, robot=None):
        self.events.append({'time': round(self.time, 2), 'robot': robot, 'kind': kind, 'detail': detail})

    def edge_occupied(self, key):
        a, b = key.split(':')
        pa, pb = self.layout['nodes'][a], self.layout['nodes'][b]
        for pos in self.positions:
            # A physical barrier is introduced only after the whole segment is clear.
            if math.dist(pa, pos)+math.dist(pos, pb) <= math.dist(pa, pb)+.02:
                return True
        return False

    def set_edge(self, key, blocked):
        valid = {edge_key(a, b) for a, b in self.layout['edges'] if a.startswith('N') and b.startswith('N')}
        if key not in valid:
            raise ValueError('Choose a road aisle from the map')
        if blocked and self.edge_occupied(key):
            self.pending_closures.add(key)
            self.event('obstacle', key+' closure queued until the segment clears')
            return
        self.pending_closures.discard(key)
        old = self.map_changes.get(key, {'version': 0})
        self.map_changes[key] = {'version': old['version']+1, 'blocked': blocked}
        self.event('obstacle', key+(' closed' if blocked else ' reopened'))

    def add_job(self, pickup, drop, priority=1):
        if pickup not in self.layout['stations'] or drop not in self.layout['stations'] or pickup == drop:
            raise ValueError('Pickup and delivery must be different road stations')
        job = {'id': f'J{len(self.catalog)+1:03}', 'pickup': pickup, 'drop': drop, 'priority': priority,
               'steward': len(self.catalog) % self.count, 'created': round(self.time, 2)}
        self.catalog.append(job)
        self.event('job', job['id']+' submitted to peer auction')
        return job

    def observations(self, rid):
        nearby_changes = {}
        for key, value in self.map_changes.items():
            a, b = key.split(':')
            if min(math.dist(self.positions[rid], self.layout['nodes'][n]) for n in (a, b)) < 4.5:
                nearby_changes[key] = value
        return {'time': self.time, 'position': self.positions[rid], 'available': self.available[rid],
                'map_changes': nearby_changes, 'new_jobs': self.catalog,
                'nearby': [p for i, p in enumerate(self.positions) if i != rid and math.dist(p, self.positions[rid]) < 1.5]}

    def apply(self, commands):
        before = list(self.positions)
        self.positions = [(p[0]+v[0]*DT, p[1]+v[1]*DT) for p, v in zip(before, commands)]
        for i in range(self.count):
            for j in range(i+1, self.count):
                separation = swept_separation(before[i], self.positions[i], before[j], self.positions[j])
                self.min_separation = min(self.min_separation, separation)
                if separation < 2*RADIUS - 1e-8:
                    if (i, j) not in self.contacts:
                        self.collisions += 1
                        self.event('collision', f'R{i+1} and R{j+1} swept bodies overlap')
                    self.contacts.add((i, j))
                else:
                    self.contacts.discard((i, j))
        self.time = round(self.time+DT, 8)
        for key in list(self.pending_closures):
            if not self.edge_occupied(key):
                self.set_edge(key, True)

    def jobs(self):
        merged = {j['id']: dict(j, owner=j['steward'], version=0, state='queued', ready=False) for j in self.catalog}
        for view in self.job_views:
            for job in view:
                if job['id'] not in merged or job['version'] > merged[job['id']]['version']:
                    merged[job['id']] = dict(job)
        return sorted(merged.values(), key=lambda j: j['id'])

    def done(self):
        return bool(self.catalog) and all(j['state'] == 'done' for j in self.jobs())

    def snapshot(self, detailed=True):
        jobs = self.jobs()
        robots = [dict(s, position=self.positions[i], alive=i not in self.dead) for i, s in enumerate(self.states)]
        result = {'time': round(self.time, 2), 'robots': robots, 'jobs': jobs, 'collisions': self.collisions,
                  'minimum_separation': round(self.min_separation, 3) if math.isfinite(self.min_separation) else None,
                  'complete': sum(j['state'] == 'done' for j in jobs), 'total_jobs': len(jobs),
                  'delivered': sum(j['state'] in ('delivered', 'done') for j in jobs),
                  'wait_seconds': round(sum(r['wait_seconds'] for r in robots), 2),
                  'distance': round(sum(r['distance'] for r in robots), 2),
                  'transfers': sum(r['transfers'] for r in robots), 'reroutes': sum(r['reroutes'] for r in robots),
                  'map_changes': self.map_changes, 'pending_closures': sorted(self.pending_closures),
                  'partitioned': self.partitioned}
        if detailed:
            result['events'] = self.events[-80:]
            result['map'] = self.layout
        return result


class Simulation:
    def __init__(self, config, model=None):
        self.world = World(config)
        self.agents = [Agent(i, config, model) for i in range(config['robots'])]
        self.queue = []
        self.sequence = 0
        self.rng = random.Random(config['seed']+9182)
        self.cursors = [0]*config['robots']
        self.network = {'sent': 0, 'received': 0, 'lost': 0}

    def step(self):
        w = self.world
        inbox = [[] for _ in self.agents]
        while self.queue and self.queue[0][0] <= w.time + 1e-8:
            _, _, rid, message = heapq.heappop(self.queue)
            if not w.partitioned:
                inbox[rid].append(message); self.network['received'] += 1
        commands = []
        for i, agent in enumerate(self.agents):
            if i in w.dead:
                commands.append((0., 0.)); continue
            obs = w.observations(i); obs['messages'] = inbox[i]
            result = agent.step(obs)
            w.states[i] = result['state']; w.job_views[i] = result['jobs']
            w.events.extend(agent.events[self.cursors[i]:]); self.cursors[i] = len(agent.events)
            commands.append(result['velocity'])
            for message in result['messages']:
                for rid in range(w.count):
                    if rid == i or message['to'] not in (None, rid):
                        continue
                    self.network['sent'] += 1
                    if w.partitioned or self.rng.random() < w.config['drop']:
                        self.network['lost'] += 1; continue
                    self.sequence += 1
                    heapq.heappush(self.queue, (w.time+DT+self.rng.random()*w.config['delay'], self.sequence, rid, message))
        w.apply(commands)
        return w.done()

    def run(self, limit=None):
        limit = limit or self.world.config['max_seconds']
        while self.world.time < limit:
            if self.step():
                break
        return self.result()

    def result(self):
        w = self.world; s = w.snapshot(False)
        return {'seed': w.config['seed'], 'map': w.layout['name'], 'scenario': w.config['scenario'],
                'mode': w.config['mode'], 'robots': w.count, 'jobs': len(w.catalog),
                'completed': w.done(), 'seconds': s['time'], 'collisions': s['collisions'],
                'minimum_separation': s['minimum_separation'], 'wait_seconds': s['wait_seconds'],
                'distance': s['distance'], 'transfers': s['transfers'], 'reroutes': s['reroutes']}
