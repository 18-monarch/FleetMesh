"""Decision evidence must follow real grants, geometry and persisted processes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import Agent
from warehouse import make_config, RADIUS
from simulation import World, Simulation
from server import Session


class ConflictTests(unittest.TestCase):
    def agent(self):
        agent = Agent(0, make_config(200, 'compact', 3, 6, 'congestion', 'heuristic'))
        agent.t = 10
        agent.request = dict(zone='ROUTE', zones=['N00','N10'], key=(20,0), grants={2}, since=8, last=10)
        return agent

    def test_missing_grants_use_local_reports_not_inferred_ownership(self):
        a = self.agent()
        a.peer[1] = dict(time=10, held=['N10'], pending_zones=[])
        d = a.decision()
        self.assertEqual(d['missing_peers'], [1])
        self.assertEqual(d['peers'][0]['cause'], 'held_zones')
        self.assertEqual(d['peers'][0]['zones'], ['N10'])
        self.assertEqual(d['wait_seconds'], 2)
        a.t = 13
        self.assertEqual(a.decision()['peers'][0]['cause'], 'unconfirmed')
        self.assertTrue(a.decision()['peers'][0]['stale'])
        self.assertEqual(a.request['grants'], {2})

    def test_priority_requires_evidence_and_duplicate_grants_do_not_help(self):
        a = self.agent()
        a.peer[1] = dict(time=10, held=[], pending_zones=['N10'], request_key=[19,1])
        self.assertEqual(a.decision()['peers'][0]['cause'], 'earlier_request')
        a.peer[1]['request_key'] = [21,1]
        self.assertEqual(a.decision()['peers'][0]['cause'], 'awaiting_grant')
        a.request['grants'].add(2)
        self.assertEqual(a.decision()['missing_peers'], [1])
        a.request['grants'].add(1)
        self.assertEqual(a.decision()['missing_peers'], [])

    def test_occupancy_and_reservation_are_distinct_and_dead_bodies_remain(self):
        w = World(make_config(200, 'compact', 3, 6))
        w.states[0]['held'] = ['N00','N10']
        road = lambda: next(r for r in w.traffic()['roads'] if r['edge']=='N00:N10')
        self.assertEqual(road()['occupied_by'], [])
        self.assertEqual(next(z for z in w.traffic()['zones'] if z['node']=='N00')['reserved_by'], [0])
        w.positions[0] = (2.,0.); w.dead.add(0)
        self.assertEqual(road()['occupied_by'], [0])
        w.set_edge('N00:N10', True)
        self.assertIn('N00:N10', w.pending_closures)

    def test_body_clearance_not_only_centreline_controls_closure(self):
        w = World(make_config())
        w.positions[0] = (-RADIUS/2, 0.)
        w.set_edge('N00:N10', True)
        self.assertIn('N00:N10', w.pending_closures)
        w.positions[0] = (-RADIUS-.01, 0.)
        w.apply([(0.,0.)]*3)
        self.assertTrue(w.map_changes['N00:N10']['blocked'])
        self.assertNotIn('N00:N10', w.pending_closures)

    def test_conflict_is_observed_then_progress_resumes(self):
        sim = Simulation(make_config(200,'compact',3,6,'congestion','heuristic'))
        saw_conflict = saw_motion = False
        while sim.world.time < 400:
            done = sim.step()
            for robot in sim.world.states:
                saw_conflict |= any(p['cause']=='held_zones' for p in robot['decision']['peers'])
                saw_motion |= robot['distance'] > 1
            if done: break
        self.assertTrue(saw_conflict)
        self.assertTrue(saw_motion)
        self.assertTrue(sim.world.done())
        self.assertEqual(sim.world.collisions, 0)
        self.assertTrue(any(e['kind']=='decision' for e in sim.world.events))

    def test_process_decisions_survive_saved_replay_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Session(directory)
            try:
                session.command('conflict', {})
                session.playing = False
                procs = list(session.runtime.processes)
                for _ in range(100): session.runtime.step()
                snap = session.snapshot()
                self.assertEqual(len({r['pid'] for r in snap['robots']}), 3)
                self.assertTrue(all('decision' in r for r in snap['robots']))
                self.assertTrue(any(r['distance']>0 for r in snap['robots']))
                session.persist()
                record = session.store.get(session.run_id, True)
                self.assertTrue(record['frames'])
                self.assertEqual(record['snapshot']['traffic'], snap['traffic'])
                self.assertTrue(all('decision' in r for r in record['frames'][-1]['robots']))
                json.dumps(record)
            finally: session.close()
            self.assertTrue(all(not p.is_alive() for p in procs))

if __name__ == '__main__': unittest.main()
