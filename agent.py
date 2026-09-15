"""Robot-owned auctions, task ledger and peer resource coordination.

The baseline acquires route nodes in a global order. Enhanced policies request
an atomic route set and release each zone after its final planned use. Robots
only replan with new permissions after returning to a private dock.
"""
import math
from warehouse import DT, edge_key, shortest, path_length

INF = 1e9

class Agent:
    def __init__(self, rid, config, model=None):
        self.id = rid
        self.config = config
        self.layout = config['map']
        self.count = config['robots']
        self.home = self.layout['homes'][rid]
        self.node = self.home
        self.pos = self.layout['nodes'][self.home]
        self.speed = config['speeds'][rid]
        self.mode = config['mode']
        self.model = model
        self.clock = 0
        self.t = 0.
        self.out = []
        self.events = []
        self.jobs = {}
        self.auctions = {}
        self.proposals = {}
        self.commits = {}
        self.peer = {}
        self.maps = {}
        self.available = True
        self.active = None
        self.stage = 'idle'
        self.route = []
        self.route_index = 0
        self.need = []
        self.held = set()
        self.request = None
        self.deferred = {}
        self.deferred_areas = {}
        self.last_emit = -1.
        self.distance = 0.
        self.wait_seconds = 0.
        self.transfers = 0
        self.reroutes = 0
        self.model_calls = 0
        self.samples = []
        self.reason = 'Waiting for jobs'
        self.pick_index = 0
        self.drop_index = 0
        self.mission = []
        for job in config['jobs']:
            self.add_job(job)

    def add_job(self, job):
        if job['id'] not in self.jobs:
            self.jobs[job['id']] = dict(job, owner=job['steward'], version=0, state='queued', ready=False)

    def send(self, kind, data, to=None):
        self.clock += 1
        self.out.append({'sender': self.id, 'to': to, 'epoch': self.config['epoch'],
                         'clock': self.clock, 'kind': kind, 'data': data})

    def event(self, kind, detail):
        self.events.append({'time': round(self.t, 2), 'robot': self.id, 'kind': kind, 'detail': detail})

    def update_job(self, jid, **changes):
        current = self.jobs[jid]
        assert current['owner'] == self.id
        current.update(changes)
        current['version'] += 1
        self.send('JOB', dict(current))

    def cost(self, job):
        if not self.available:
            return INF
        blocked = self.blocked()
        route, length = shortest(self.layout, self.home, job['pickup'], blocked)
        if not route:
            return INF
        pending = sum(j['owner'] == self.id and j['state'] != 'done' and j['id'] != job['id'] for j in self.jobs.values())
        return length / self.speed + 12 * pending + (self.remaining_seconds() if self.active else 0)

    def receive(self, msg):
        sender = msg.get('sender')
        if msg.get('epoch') != self.config['epoch'] or sender not in range(self.count) or sender == self.id:
            return
        if msg.get('to') not in (None, self.id):
            return
        self.clock = max(self.clock, msg.get('clock', 0)) + 1
        data = msg.get('data', {})
        kind = msg.get('kind')
        if kind == 'INFO':
            if data['time'] >= self.peer.get(sender, {}).get('time', -1):
                self.peer[sender] = data
        elif kind == 'MAP':
            for key, value in data.items():
                if value['version'] > self.maps.get(key, {}).get('version', -1):
                    self.maps[key] = value
        elif kind == 'JOB':
            current = self.jobs.get(data['id'])
            if current and current['owner'] == sender == data['owner'] and data['version'] > current['version']:
                self.jobs[data['id']] = dict(data)
        elif kind == 'AUCTION':
            current = self.jobs.get(data['job'])
            if current and current['owner'] == sender and current['state'] == 'queued' and current['version'] == data['version']:
                self.send('BID', {'job': current['id'], 'token': data['token'], 'cost': self.cost(current)}, sender)
        elif kind == 'BID':
            auction = self.auctions.get(data['job'])
            if auction and auction['token'] == data['token']:
                auction['bids'][sender] = data['cost']
        elif kind == 'PREPARE':
            current = self.jobs.get(data['job'])
            if (current and current['owner'] == sender and current['state'] == 'queued'
                and current['version'] == data['version'] and data['new_owner'] in range(self.count)):
                self.proposals[data['token']] = dict(data, old_owner=sender)
                self.send('ACK', {'job': data['job'], 'token': data['token']}, sender)
        elif kind == 'ACK':
            auction = self.auctions.get(data['job'])
            if auction and auction['token'] == data['token'] and auction.get('candidate') is not None:
                auction['acks'].add(sender)
        elif kind == 'COMMIT':
            proposal = self.proposals.get(data['token'])
            current = self.jobs.get(data['job'])
            if (proposal and proposal['old_owner'] == sender and current and current['owner'] == sender
                and current['version'] == data['version'] and current['state'] == 'queued'):
                self.jobs[data['job']].update(owner=data['new_owner'], version=data['version']+1, ready=True)
                self.event('transfer', f"{data['job']} ownership committed to R{data['new_owner']+1}")
        elif kind == 'REQUEST':
            zone, key = data['zone'], tuple(data['key'])
            zones = set(data.get('zones', [zone]))
            if not zones or not zones.issubset(self.layout['stations']):
                return
            own = self.request if self.request and zones.intersection(self.request['zones']) else None
            if zones.intersection(self.held) or (own and own['key'] < key):
                old = self.deferred.setdefault(zone, {}).get(sender)
                if old is None or key > old:
                    self.deferred[zone][sender] = key
                    self.deferred_areas[(zone, sender)] = zones
            else:
                self.send('GRANT', {'zone': zone, 'key': list(key)}, sender)
        elif kind == 'GRANT':
            if self.request and data['zone'] == self.request['zone'] and tuple(data['key']) == self.request['key']:
                self.request['grants'].add(sender)

    def blocked(self):
        return {k for k, v in self.maps.items() if v['blocked']}

    def queue_features(self, zone):
        busy, waiting = 0., 0.
        for peer in self.peer.values():
            if self.t - peer['time'] > 2:
                continue
            if zone in peer['held']:
                busy += max(0., peer['remaining'] - (self.t - peer['time']))
            elif zone in peer.get('pending_zones', []):
                waiting += 1
        return [1., busy, waiting]

    def penalty(self, zone):
        features = self.queue_features(zone)
        if self.mode in ('baseline', 'atomic'):
            return 0.
        if self.mode == 'predictive' and self.model:
            self.model_calls += 1
            seconds = max(0., sum(a*b for a, b in zip(features, self.model['weights'])))
        else:
            seconds = features[1] + 3 * features[2]
        return min(120., seconds) * self.speed

    def plan_mission(self, job):
        penalties = {n: self.penalty(n) for n in self.layout['stations']}
        legs = []
        pickup = self.home if job.get('carrying') else job['pickup']
        for start, end in [(self.home, pickup), (pickup, job['drop']), (job['drop'], self.home)]:
            path, _ = shortest(self.layout, start, end, self.blocked(), penalties)
            if not path:
                return None
            legs.append(path)
        return legs

    def start_auction(self, job):
        self.clock += 1
        self.auctions[job['id']] = {'token': f'{self.id}-{self.clock}-{job["id"]}',
            'version': job['version'], 'bids': {self.id: self.cost(job)}, 'acks': set(), 'last': -1.}

    def auctions_step(self):
        for job in list(self.jobs.values()):
            if job['owner'] != self.id or job['state'] != 'queued' or job['id'] == self.active:
                continue
            jid = job['id']
            if (not job['ready'] or not self.available) and jid not in self.auctions:
                self.start_auction(job)
            auction = self.auctions.get(jid)
            if not auction:
                continue
            # The owner freezes pickup while offering a transfer.
            if len(auction['bids']) == self.count and 'candidate' not in auction:
                candidate = min(auction['bids'], key=lambda rid: (auction['bids'][rid], rid))
                if auction['bids'][candidate] >= INF:
                    self.reason = 'No available bidder'
                    auction['bids'] = {self.id: self.cost(job)}
                    auction['last'] = -1.
                    continue
                if candidate == self.id:
                    self.update_job(jid, ready=True)
                    del self.auctions[jid]
                    continue
                auction['candidate'] = candidate
            if len(auction['acks']) == self.count - 1 and 'candidate' in auction:
                commit = {'job': jid, 'token': auction['token'], 'version': auction['version'], 'new_owner': auction['candidate']}
                self.commits[auction['token']] = commit
                self.send('COMMIT', commit)
                self.jobs[jid].update(owner=auction['candidate'], version=auction['version']+1, ready=True)
                self.transfers += 1
                self.event('transfer', f"{jid} handed to R{auction['candidate']+1} before pickup")
                del self.auctions[jid]
                continue
            if self.t - auction['last'] >= .4:
                if 'candidate' in auction:
                    data = {'job': jid, 'token': auction['token'], 'version': auction['version'], 'new_owner': auction['candidate']}
                    self.send('PREPARE', data)
                else:
                    self.send('AUCTION', {'job': jid, 'version': job['version'], 'token': auction['token']})
                auction['last'] = self.t

    def release(self):
        self.request = None
        for zone in sorted(self.deferred):
            for rid, key in self.deferred.pop(zone, {}).items():
                self.send('GRANT', {'zone': zone, 'key': list(key)}, rid)
        self.held.clear()
        self.deferred_areas.clear()

    def release_passed_zones(self):
        if self.mode == 'baseline':
            return
        remaining = set(self.route[self.route_index:])
        self.held.intersection_update(remaining)
        for zone, peers in list(self.deferred.items()):
            for rid, key in list(peers.items()):
                if not self.held.intersection(self.deferred_areas.get((zone, rid), {zone})):
                    self.send('GRANT', {'zone': zone, 'key': list(key)}, rid)
                    del peers[rid]
                    self.deferred_areas.pop((zone, rid), None)
            if not peers:
                del self.deferred[zone]

    def acquire(self):
        missing = [zone for zone in self.need if zone not in self.held]
        if not missing:
            return True
        zone = missing[0] if self.mode == 'baseline' else 'ROUTE'
        zones = [missing[0]] if self.mode == 'baseline' else list(self.need)
        if self.request is None:
            self.clock += 1
            self.request = {'zone': zone, 'zones': zones, 'key': (self.clock, self.id), 'grants': set(),
                            'since': self.t, 'last': -1., 'features': self.queue_features(missing[0])}
        if self.t - self.request['last'] >= .3:
            self.send('REQUEST', {'zone': zone, 'zones': zones, 'key': list(self.request['key'])})
            self.request['last'] = self.t
        if len(self.request['grants']) == self.count - 1:
            self.samples.append({'features': self.request['features'], 'wait': self.t - self.request['since']})
            self.held.update(zones)
            self.request = None
        self.wait_seconds += DT
        self.reason = 'Waiting for peer permission at ' + zone
        return False

    def remaining_seconds(self):
        if not self.active or not self.route:
            return 0.
        remaining = self.route[self.route_index:]
        length = path_length(self.layout, remaining)
        if len(remaining) > 1:
            length -= math.dist(self.layout['nodes'][remaining[0]], self.pos)
        return max(0., length / self.speed)

    def state(self):
        return {'id': self.id, 'position': self.pos, 'node': self.node, 'home': self.home,
                'active': self.active, 'stage': self.stage, 'available': self.available,
                'held': sorted(self.held), 'request': self.request['zone'] if self.request else None,
                'grants': len(self.request['grants']) if self.request else 0,
                'route': self.route[self.route_index:], 'reason': self.reason,
                'wait_seconds': round(self.wait_seconds, 2), 'distance': round(self.distance, 2),
                'battery': round(max(0., 100-self.distance*.025), 1), 'model_calls': self.model_calls,
                'transfers': self.transfers, 'reroutes': self.reroutes, 'alive': True,
                'peer_observations': [{'id': rid, 'position': info.get('position'), 'intent': info.get('intent', []),
                                       'age_seconds': round(max(0., self.t-info['time']), 2),
                                       'stale': self.t-info['time'] > 2} for rid, info in sorted(self.peer.items())]}

    def step(self, obs):
        self.t = obs['time']; self.pos = tuple(obs['position']); self.out = []
        self.available = obs.get('available', True)
        for job in obs.get('new_jobs', []):
            self.add_job(job)
        for msg in obs.get('messages', []):
            self.receive(msg)
        changed = False
        for key, value in obs.get('map_changes', {}).items():
            if value['version'] > self.maps.get(key, {}).get('version', -1):
                self.maps[key] = value; changed = True
                self.event('map', f"{key} {'closed' if value['blocked'] else 'reopened'}")
        if changed:
            self.send('MAP', self.maps)
        self.auctions_step()
        if self.active is None and self.available:
            options = [j for j in self.jobs.values() if j['owner'] == self.id and j['state'] in ('queued', 'queued_loaded') and j['ready'] and j['id'] not in self.auctions]
            options.sort(key=lambda j: (-j['priority'], j['created'], j['id']))
            for job in options:
                legs = self.plan_mission(job)
                if legs is None:
                    self.reason = 'Pickup or destination unreachable'
                    continue
                self.active = job['id']; self.stage = 'reserving'
                self.mission = legs
                self.route = legs[0] + legs[1][1:] + legs[2][1:]
                self.pick_index = len(legs[0])-1
                self.drop_index = self.pick_index+len(legs[1])-1
                self.route_index = 0
                self.need = sorted({n for n in self.route if n.startswith('N')})
                self.update_job(self.active, state='reserved')
                self.event('mission', f"{self.active}: reserving {len(self.need)} road zones")
                break
        velocity = (0., 0.)
        if self.active and self.stage == 'reserving':
            if any(edge_key(a, b) in self.blocked() for a, b in zip(self.route, self.route[1:])):
                jid = self.active
                self.release(); self.active = None; self.stage = 'idle'; self.route = []
                self.update_job(jid, state='queued_loaded' if self.jobs[jid].get('carrying') else 'queued')
                self.event('reroute', jid+' cancelled departure to replan around closure'); self.reroutes += 1
            elif self.acquire():
                self.stage = 'pickup'
                self.event('depart', f'{self.active}: all route permissions received')
        if self.active and self.stage in ('pickup', 'delivery', 'return', 'retreat'):
            # Advance node arrivals only on actual world observations.
            if self.route_index+1 < len(self.route) and math.dist(self.pos, self.layout['nodes'][self.route[self.route_index+1]]) < 1e-7:
                self.route_index += 1; self.node = self.route[self.route_index]
                self.release_passed_zones()
            if self.route_index == self.pick_index and self.stage == 'pickup':
                self.stage = 'delivery'; self.update_job(self.active, state='picked', carrying=True)
                self.event('pickup', self.active+' package picked up')
            if self.route_index == self.drop_index and self.stage == 'delivery':
                self.stage = 'return'; self.update_job(self.active, state='delivered', carrying=False, delivered_at=round(self.t, 2))
                self.event('delivery', self.active+' delivered; returning to dock')
            if self.route_index == len(self.route)-1:
                if self.stage == 'retreat' and self.jobs[self.active]['state'] != 'delivered':
                    self.update_job(self.active, state='queued_loaded' if self.jobs[self.active].get('carrying') else 'queued')
                    self.event('reroute', self.active+' safely docked to replan')
                else:
                    self.update_job(self.active, state='done', completed_at=round(self.t, 2))
                    self.event('complete', self.active+' complete and docked')
                self.release(); self.active = None; self.stage = 'idle'; self.route = []; self.reason = 'Docked'
            elif self.active:
                nxt = self.route[self.route_index+1]
                key = edge_key(self.node, nxt)
                if key in self.blocked():
                    self.reason = 'Aisle closed; holding reserved route'
                    self.wait_seconds += DT
                    retreat, _ = shortest(self.layout, self.node, self.home, self.blocked(), permitted=self.held)
                    if self.stage != 'retreat' and retreat and len(retreat) > 1 and math.dist(self.pos, self.layout['nodes'][self.node]) < 1e-7:
                        self.route = retreat; self.route_index = 0; self.stage = 'retreat'
                        self.reroutes += 1; self.event('reroute', self.active+' returning within owned zones to replan')
                else:
                    target = self.layout['nodes'][nxt]; length = math.dist(self.pos, target)
                    amount = min(length, self.speed*DT)
                    velocity = ((target[0]-self.pos[0])*amount/(length*DT), (target[1]-self.pos[1])*amount/(length*DT)) if length else (0., 0.)
                    self.reason = {'pickup': 'Going to pickup', 'delivery': 'Carrying package', 'return': 'Returning to private dock', 'retreat': 'Returning safely to replan'}[self.stage]
                    if any(math.dist(self.pos, p) < .85 for p in obs.get('nearby', [])):
                        velocity = (0., 0.); self.reason = 'Local proximity stop'; self.wait_seconds += DT
        if not self.available and self.active is None:
            self.reason = 'Maintenance: communicating and handing off queued work'
        self.distance += math.hypot(*velocity)*DT
        if self.t - self.last_emit >= .4:
            self.send('INFO', {'time': self.t, 'held': sorted(self.held), 'request': self.request['zone'] if self.request else None,
                               'remaining': self.remaining_seconds(), 'available': self.available, 'pending_zones': self.request['zones'] if self.request else [],
                               'position': list(self.pos), 'intent': self.route[self.route_index:self.route_index+4],
                               'stage': self.stage, 'job': self.active})
            for job in self.jobs.values():
                if job['owner'] == self.id:
                    self.send('JOB', dict(job))
            for commit in self.commits.values():
                self.send('COMMIT', commit)
            if self.maps:
                self.send('MAP', self.maps)
            self.last_emit = self.t
        return {'velocity': velocity, 'messages': self.out, 'state': self.state(), 'jobs': list(self.jobs.values())}
