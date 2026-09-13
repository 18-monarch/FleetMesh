import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent import Agent
from simulation import Simulation,swept_separation
from warehouse import make_config,edge_key
from transport import ProcessRuntime,pack,unpack
from storage import RunStore
from server import integer, Session
from demonstration import Demonstration, run_report
ROOT=Path(__file__).resolve().parents[1]
MODEL=json.loads((ROOT/'model.json').read_text())

class ProductTests(unittest.TestCase):
    def test_paused_actions_are_present_in_saved_report(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                session.start({'jobs':1})
                session.command('pause',{})
                session.command('job',{'pickup':'N00','drop':'N32','priority':3})
                session.command('network',{'partitioned':True})
                saved=session.store.get(session.run_id)
                self.assertEqual(saved['jobs'],2)
                self.assertTrue(saved['snapshot']['partitioned'])
                self.assertIn('J002',run_report(saved))
            finally:session.close()

    def test_command_retries_do_not_duplicate_jobs_or_replace_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                first=session.execute('start',{'jobs':1},'start-request-123')
                again=session.execute('start',{'jobs':1},'start-request-123')
                self.assertEqual(first['run_id'],again['run_id'])
                self.assertTrue(again['replayed'])
                job={'pickup':'N00','drop':'N32','priority':3}
                session.execute('job',job,'mission-request-123')
                session.execute('job',job,'mission-request-123')
                self.assertEqual(len(session.runtime.world.catalog),2)
                with self.assertRaises(ValueError):session.execute('job',dict(job,priority=1),'mission-request-123')
            finally:session.close()

    def test_terminal_run_rejects_new_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                session.start({'jobs':1});session.playing=False;session.status='timeout'
                before=len(session.runtime.world.catalog)
                with self.assertRaises(ValueError):session.command('job',{'pickup':'N00','drop':'N32','priority':3})
                with self.assertRaises(ValueError):session.command('network',{'partitioned':True})
                self.assertEqual(len(session.runtime.world.catalog),before)
                self.assertFalse(session.runtime.world.partitioned)
            finally:session.close()

    def test_failed_replacement_keeps_old_evidence_and_clears_live_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                session.start({'jobs':1});old=session.run_id
                with patch('server.ProcessRuntime',side_effect=RuntimeError('test startup failure')):
                    with self.assertRaises(RuntimeError):session.start({'jobs':2})
                self.assertIsNone(session.runtime)
                self.assertIsNone(session.run_id)
                self.assertEqual(session.status,'failed')
                self.assertEqual(session.store.get(old)['jobs'],1)
                self.assertEqual(session.store.get(old)['status'],'replaced')
            finally:session.close()

    def test_invalid_predictor_is_rejected_without_losing_current_run(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                session.start({'jobs':1});old=session.run_id
                session.model={'weights':[float('nan'),2,3]}
                with self.assertRaises(ValueError):session.start({'mode':'predictive'})
                self.assertEqual(session.run_id,old)
                self.assertFalse(session.snapshot()['model_available'])
            finally:session.close()

    def test_published_snapshot_does_not_change_after_control_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            session=Session(directory)
            try:
                session.start({'jobs':1});snapshot=session.snapshot()
                session.command('aisle',{'edge':'N10:N11','blocked':True})
                self.assertEqual(snapshot['map_changes'],{})
                self.assertTrue(session.snapshot()['map_changes']['N10:N11']['blocked'])
            finally:session.close()

    def test_scripted_disturbances_complete_without_duplicate_cargo(self):
        sim=Simulation(make_config(200,'warehouse',3,6,'normal','heuristic'),MODEL)
        demo=Demonstration()
        for _ in range(9000):
            demo.advance(sim.world)
            done=sim.step()
            self.assert_exclusive(sim)
            if done:break
        self.assertTrue(done)
        self.assertEqual(sim.world.collisions,0)
        self.assertEqual(sum(j['state']=='done' for j in sim.world.jobs()),7)
        self.assertEqual(demo.snapshot(sim.world)['urgent_state'],'done')
        self.assertFalse(sim.world.partitioned)
        self.assertFalse(any(v['blocked'] for v in sim.world.map_changes.values()))

    def test_report_escapes_labels_and_marks_incomplete_run(self):
        report=run_report({'map':'<script>alert(1)</script>','snapshot':{'total_jobs':3,'complete':1,'time':4}})
        self.assertNotIn('<script>',report)
        self.assertIn('&lt;script&gt;',report)
        self.assertIn('Run incomplete at this snapshot',report)
        self.assertIn('No scripted demonstration',report)

    def assert_exclusive(self,sim):
        for i,a in enumerate(sim.agents):
            for b in sim.agents[i+1:]:
                self.assertFalse(a.held.intersection(b.held))
                if a.active and b.active:self.assertNotEqual(a.active,b.active)

    def test_repeated_jobs_across_map_and_fleet_sizes(self):
        for name,count in [('compact',3),('warehouse',4),('extended',6)]:
            with self.subTest(map=name,robots=count):
                sim=Simulation(make_config(203,name,count,6,mode='predictive'),MODEL)
                while sim.world.time<650:
                    done=sim.step();self.assert_exclusive(sim)
                    if done:break
                self.assertTrue(done);self.assertEqual(sim.world.collisions,0)
                self.assertEqual(len([e for e in sim.world.events if e['kind']=='delivery']),6)

    def test_unpicked_jobs_transfer_in_maintenance(self):
        config=make_config(205,job_count=9)
        sim=Simulation(config,MODEL);sim.world.available[0]=False
        self.assertTrue(sim.run(650)['completed']);self.assertEqual(sim.world.collisions,0)
        self.assertTrue(all(j['owner']!=0 for j in sim.world.jobs()))
        self.assertEqual(len([e for e in sim.world.events if e['kind']=='pickup']),9)
        self.assertGreater(sum(a.transfers for a in sim.agents),0)

    def test_picked_cargo_is_never_transferred(self):
        sim=Simulation(make_config(206,job_count=3),MODEL)
        for _ in range(1500):
            sim.step()
            picked=[a for a in sim.agents if a.stage=='delivery']
            if picked:break
        self.assertTrue(picked);agent=picked[0];jid=agent.active;owner=agent.id
        sim.world.available[owner]=False
        self.assertTrue(sim.run(700)['completed'])
        self.assertEqual(next(j for j in sim.world.jobs() if j['id']==jid)['owner'],owner)

    def test_network_partition_waits_then_recovers(self):
        sim=Simulation(make_config(204,job_count=6,scenario='network'),MODEL)
        sim.world.partitioned=True
        for _ in range(60):sim.step()
        self.assertTrue(all(not a.held for a in sim.agents));self.assertEqual(sim.world.collisions,0)
        sim.world.partitioned=False
        self.assertTrue(sim.run(650)['completed']);self.assertEqual(sim.world.collisions,0)

    def test_dynamic_closure_causes_safe_replan(self):
        sim=Simulation(make_config(203,job_count=6),MODEL)
        chosen=None
        for _ in range(500):
            sim.step()
            for agent in sim.agents:
                if agent.stage=='pickup':
                    remaining=agent.route[agent.route_index+2:agent.pick_index+1]
                    for a,b in zip(remaining,remaining[1:]):
                        key=edge_key(a,b)
                        if not sim.world.edge_occupied(key):chosen=key;break
                if chosen:break
            if chosen:break
        self.assertIsNotNone(chosen);sim.world.set_edge(chosen,True)
        result=sim.run(650)
        self.assertTrue(result['completed']);self.assertEqual(result['collisions'],0)
        self.assertGreater(result['reroutes'],0)
        self.assertEqual(len([e for e in sim.world.events if e['kind']=='delivery']),6)

    def test_loaded_reroute_retains_owner_and_delivers_once(self):
        sim=Simulation(make_config(208,job_count=3),MODEL)
        chosen=None
        for _ in range(1800):
            sim.step()
            for agent in sim.agents:
                if agent.stage=='delivery':
                    segment=agent.route[agent.route_index+2:agent.drop_index+1]
                    for a,b in zip(segment,segment[1:]):
                        key=edge_key(a,b)
                        if not sim.world.edge_occupied(key):
                            chosen=(key,agent.id,agent.active);break
                if chosen:break
            if chosen:break
        self.assertIsNotNone(chosen)
        key,owner,jid=chosen;sim.world.set_edge(key,True)
        # If no owned retreat exists, reopening is the supported safe action.
        for _ in range(150):sim.step()
        sim.world.set_edge(key,False)
        self.assertTrue(sim.run(700)['completed'])
        self.assertEqual(next(j for j in sim.world.jobs() if j['id']==jid)['owner'],owner)
        self.assertEqual(len([e for e in sim.world.events if e['kind']=='delivery' and jid in e['detail']]),1)
        self.assertEqual(sim.world.collisions,0)

    def test_all_maintenance_then_service_recovers_auction(self):
        sim=Simulation(make_config(209,job_count=3),MODEL)
        sim.world.available=[False]*3
        for _ in range(40):sim.step()
        self.assertTrue(all(not a.active for a in sim.agents))
        sim.world.available=[True]*3
        self.assertTrue(sim.run(650)['completed'])
        self.assertEqual(sim.world.collisions,0)

    def test_live_job_after_completion(self):
        sim=Simulation(make_config(201,job_count=1),MODEL);self.assertTrue(sim.run()['completed'])
        job=sim.world.add_job('N00','N32',3)
        self.assertTrue(sim.run(700)['completed'])
        self.assertEqual(len(sim.world.jobs()),2)
        self.assertEqual(sim.world.jobs()[-1]['id'],job['id'])

    def test_duplicate_stale_and_wrong_epoch_grants(self):
        agent=Agent(0,make_config(),MODEL)
        agent.request={'zone':'ROUTE','zones':['N00'],'key':(9,0),'grants':set()}
        for sender,epoch,key in [(1,agent.config['epoch'],[9,0]),(1,agent.config['epoch'],[9,0]),(2,'old',[9,0]),(2,agent.config['epoch'],[8,0])]:
            agent.receive({'sender':sender,'to':0,'epoch':epoch,'kind':'GRANT','clock':11,'data':{'zone':'ROUTE','key':key}})
        self.assertEqual(agent.request['grants'],{1})

    def test_authenticated_packets_reject_modification(self):
        raw=pack({'sender':0,'value':1},b'a'*32)
        self.assertEqual(unpack(raw,b'a'*32)['value'],1)
        with self.assertRaises(ValueError):unpack(raw[:-1]+b'0',b'a'*32)
        with self.assertRaises(ValueError):unpack(raw,b'b'*32)

    def test_swept_detector_finds_between_tick_collision(self):
        self.assertEqual(swept_separation((0,0),(1,0),(1,0),(0,0)),0)

    def test_process_runtime_uses_distinct_peers(self):
        runtime=ProcessRuntime(make_config(203,job_count=3),MODEL)
        try:
            for _ in range(4500):
                if runtime.step():break
            self.assertTrue(runtime.world.done());self.assertEqual(runtime.world.collisions,0)
            self.assertEqual(len({r['pid'] for r in runtime.world.states}),3)
            self.assertTrue(all(r['sent']>0 and r['received']>0 for r in runtime.world.states))
        finally:runtime.close()

    def test_killed_owner_keeps_resource_blocked(self):
        runtime=ProcessRuntime(make_config(200,job_count=3),MODEL)
        try:
            for _ in range(150):
                runtime.step()
                owners=[r for r in runtime.world.states if r['held']]
                if owners:break
            self.assertTrue(owners);rid=owners[0]['id'];held=set(owners[0]['held']);runtime.kill(rid)
            for _ in range(180):runtime.step()
            self.assertEqual(runtime.world.collisions,0)
            self.assertTrue(all(not held.intersection(r['held']) for r in runtime.world.states if r['id']!=rid))
        finally:runtime.close()

    def test_history_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            config=make_config();store=RunStore(directory);store.create('abc',config)
            store.save('abc',{'time':1,'complete':0,'total_jobs':9},'paused');store.close()
            store=RunStore(directory)
            self.assertEqual(store.get('abc',True)['frames'][0]['time'],1)
            self.assertEqual(store.list()[0]['status'],'interrupted')
            self.assertFalse(store.get('abc')['snapshot']['playing']);store.close()

    def test_configuration_rejects_invalid_numbers(self):
        for value in [True,'3',None,2,7,3.5]:
            with self.assertRaises(ValueError):integer(value,3,6,'robots')
        self.assertEqual(integer(3,3,6,'robots'),3)

if __name__=='__main__':unittest.main(verbosity=2)
