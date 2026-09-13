"""Planar warehouse graphs and deterministic experiment configurations."""
import heapq
import math
import random
from version import VERSION

DT = 0.1
RADIUS = 0.28
MAPS = {'compact': (3, 3), 'warehouse': (4, 3), 'extended': (4, 4)}

def edge_key(a, b):
    return ':'.join(sorted((a, b)))

def build_map(name='warehouse', robot_count=3):
    cols, rows = MAPS[name]
    nodes = {f'N{x}{y}': (x * 4., y * 4.) for x in range(cols) for y in range(rows)}
    edges = []
    for x in range(cols):
        for y in range(rows):
            if x + 1 < cols:
                edges.append((f'N{x}{y}', f'N{x+1}{y}'))
            if y + 1 < rows:
                edges.append((f'N{x}{y}', f'N{x}{y+1}'))
    entries = [('N00', (-2., 0.)), (f'N0{rows-1}', (-2., (rows-1)*4.)),
               (f'N{cols-1}0', ((cols-1)*4.+2., 0.)),
               (f'N{cols-1}{rows-1}', ((cols-1)*4.+2., (rows-1)*4.)),
               ('N10', (4., -2.)), (f'N1{rows-1}', (4., (rows-1)*4.+2.))]
    for i, (node, pos) in enumerate(entries[:robot_count]):
        nodes[f'H{i}'] = pos
        edges.append((f'H{i}', node))
    return {'name': name, 'nodes': nodes, 'edges': edges, 'homes': [f'H{i}' for i in range(robot_count)],
            'stations': [f'N{x}{y}' for x in range(cols) for y in range(rows)],
            'width': cols, 'height': rows}

def shortest(layout, start, goal, blocked=(), penalties=None, permitted=None):
    blocked = set(blocked)
    penalties = penalties or {}
    graph = {n: [] for n in layout['nodes']}
    for a, b in layout['edges']:
        if edge_key(a, b) in blocked:
            continue
        if permitted is not None and any(n.startswith('N') and n not in permitted for n in (a, b)):
            continue
        length = math.dist(layout['nodes'][a], layout['nodes'][b])
        graph[a].append((b, length)); graph[b].append((a, length))
    queue = [(0., start, [])]
    seen = set()
    while queue:
        cost, node, route = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node); route = route + [node]
        if node == goal:
            return route, cost
        for other, length in graph[node]:
            # Private parking is never a shortcut.
            if other.startswith('H') and other not in (start, goal):
                continue
            heapq.heappush(queue, (cost + length + penalties.get(other, 0), other, route))
    return [], math.inf

def path_length(layout, route):
    return sum(math.dist(layout['nodes'][a], layout['nodes'][b]) for a, b in zip(route, route[1:]))

def make_config(seed=200, map_name='warehouse', robot_count=3, job_count=9, scenario='normal', mode='predictive'):
    rng = random.Random(seed)
    layout = build_map(map_name, robot_count)
    jobs = []
    stations = layout['stations']
    center = f'N{layout["width"]//2}{layout["height"]//2}'
    for i in range(job_count):
        pickup = center if scenario == 'congestion' and i % 2 == 0 else rng.choice(stations)
        drop = rng.choice([n for n in stations if n != pickup])
        jobs.append({'id': f'J{i+1:03}', 'pickup': pickup, 'drop': drop, 'priority': 1,
                     'steward': i % robot_count, 'created': 0.})
    return {'seed': seed, 'map': layout, 'robots': robot_count, 'jobs': jobs, 'scenario': scenario,
            'mode': mode, 'speeds': [rng.uniform(1.0, 1.3) for _ in range(robot_count)],
            'drop': .1 if scenario == 'network' else 0., 'delay': .3 if scenario == 'network' else 0.,
            'max_seconds': 900, 'epoch': f'test-{seed}', 'version': VERSION}
