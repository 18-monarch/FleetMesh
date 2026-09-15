"""Real HTTP/process/storage checks for public visitor isolation and recovery."""
import json
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud import Manager, BoundedServer, make_cloud_handler
from cloud_storage import CloudDatabase, StorageUnavailable
from warehouse import make_config


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name)/'cloud.db')
        self.start()

    def start(self):
        self.db = CloudDatabase(sqlite_path=self.path)
        self.db.migrate(); self.db.boot()
        self.manager = Manager(self.db, 'test-secret-'*5, ['https://fleet.example'], max_active=2)
        self.server = BoundedServer(('127.0.0.1',0), make_cloud_handler(self.manager, secure=False))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.manager.close()

    def tearDown(self):
        self.stop(); self.tmp.cleanup()

    def request(self, path, visitor=None, data=None, headers=None):
        h = dict(headers or {})
        if visitor:
            h['Cookie'], h['X-FleetMesh-Token'] = visitor
        if data is not None:
            h.setdefault('Content-Type','application/json')
            h.setdefault('X-FleetMesh-Request-ID','request-'+str(time.time_ns()))
            h.setdefault('Origin','https://fleet.example')
        conn=HTTPConnection('127.0.0.1',self.server.server_port,timeout=20)
        conn.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,h)
        response=conn.getresponse(); raw=response.read(); result_headers=dict(response.getheaders())
        status=response.status;conn.close()
        try: result=json.loads(raw)
        except ValueError: result=raw.decode()
        return status,result,result_headers

    def visitor(self):
        status,data,headers=self.request('/api/session',headers={'X-FleetMesh-Client':'web'})
        self.assertEqual(status,200)
        self.assertIn('HttpOnly',headers['Set-Cookie']); self.assertIn('SameSite=Lax',headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';')[0],data['token']

    def launch(self, visitor, request='start-123456'):
        status,data,_=self.request('/api/start',visitor,{'jobs':3}, {'X-FleetMesh-Request-ID':request})
        self.assertEqual(status,200,data)
        return data['run_id']

    def test_private_reads_require_session_and_responses_are_not_cached(self):
        self.assertEqual(self.request('/api/state')[0],401)
        self.assertEqual(self.request('/api/runs')[0],401)
        visitor=self.visitor()
        status,_,headers=self.request('/api/state',visitor)
        self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store')

    def test_two_visitors_cannot_read_or_control_each_others_run(self):
        a,b=self.visitor(),self.visitor();rid=self.launch(a)
        self.assertEqual(self.request('/api/runs/'+rid,b)[0],404)
        self.assertEqual(self.request('/api/runs',b)[1],[])
        self.assertEqual(self.request('/api/pause',(b[0],a[1]),{})[0],403)
        self.assertIsNone(self.request('/api/state',b)[1]['run_id'])

    def test_origin_cookie_tampering_and_invalid_json_are_rejected(self):
        visitor=self.visitor()
        self.assertEqual(self.request('/api/start',visitor,{}, {'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('/api/state',(visitor[0]+'bad',visitor[1]))[0],401)
        self.assertEqual(self.request('/api/start',visitor,{'seed':float('nan')})[0],400)
        self.assertEqual(self.request('/api/start',visitor,{'jobs':True})[0],400)

    def test_duplicate_start_and_job_are_applied_once(self):
        visitor=self.visitor();rid=self.launch(visitor)
        self.assertEqual(self.launch(visitor),rid)
        job={'pickup':'N00','drop':'N32','priority':3}
        headers={'X-FleetMesh-Request-ID':'unique-job-12345'}
        self.assertEqual(self.request('/api/job',visitor,job,headers)[0],200)
        self.assertTrue(self.request('/api/job',visitor,job,headers)[1]['replayed'])
        self.assertEqual(self.request('/api/state',visitor)[1]['total_jobs'],4)
        self.assertEqual(self.request('/api/job',visitor,dict(job,priority=1),headers)[0],400)

    def test_restart_preserves_owner_history_replay_and_command_receipt(self):
        visitor=self.visitor();rid=self.launch(visitor)
        self.request('/api/pause',visitor,{})
        before=self.request('/api/runs/'+rid+'?frames=1',visitor)[1]
        self.assertGreater(len(before['frames']),0)
        self.stop();self.start()
        after=self.request('/api/runs/'+rid+'?frames=1',visitor)[1]
        self.assertEqual(after['status'],'interrupted');self.assertFalse(after['snapshot']['playing'])
        self.assertEqual(self.launch(visitor),rid)
        self.assertIsNone(self.request('/api/state',visitor)[1]['run_id'])

    def test_capacity_bounds_real_processes_and_preserves_existing_runs(self):
        visitors=[self.visitor() for _ in range(3)]
        ids=[self.launch(visitors[i]) for i in range(2)]
        self.assertEqual(self.request('/api/start',visitors[2],{})[0],429)
        self.assertEqual(self.request('/api/state',visitors[0])[1]['run_id'],ids[0])
        pids={p.pid for s in self.manager.sessions.values() if s.runtime for p in s.runtime.processes}
        self.assertEqual(len(pids),6)

    def test_missing_database_never_falls_back_and_failure_is_redacted(self):
        with self.assertRaises(ValueError):CloudDatabase()
        visitor=self.visitor()
        with patch.object(self.db,'begin_command',side_effect=StorageUnavailable('postgres://sensitive')):
            status,data,_=self.request('/api/start',visitor,{})
        self.assertEqual(status,503);self.assertNotIn('sensitive',json.dumps(data))
        self.assertIsNone(self.request('/api/state',visitor)[1]['run_id'])

    def test_incomplete_command_receipt_cannot_reexecute_after_failure(self):
        visitor=self.visitor();owner=self.manager.owner(visitor[0].split('=',1)[1])
        signature=json.dumps(['start',{'jobs':3}],sort_keys=True,separators=(',',':'))
        self.db.begin_command(owner,'start-123456',signature)
        self.assertEqual(self.request('/api/start',visitor,{'jobs':3},{'X-FleetMesh-Request-ID':'start-123456'})[0],400)
        self.assertIsNone(self.request('/api/state',visitor)[1]['run_id'])

    def test_session_cookie_recovers_same_identity_and_expires(self):
        visitor=self.visitor();cookie=visitor[0].split('=',1)[1]
        owner=self.manager.owner(cookie)
        self.assertTrue(owner)
        with patch('cloud.time.time',return_value=time.time()+8*86400):
            self.assertIsNone(self.manager.owner(cookie))

    def test_database_owner_scope_and_idempotent_schema(self):
        self.db.migrate()
        self.db.create('alice','test-run',make_config())
        self.db.save('alice','test-run',{'time':1,'complete':0,'total_jobs':9},'paused')
        with self.assertRaises(KeyError):self.db.records('bob','test-run',True)
        with self.assertRaises(KeyError):self.db.save('bob','test-run',{'time':2},'completed')
        self.assertEqual(self.db.records('alice','test-run')['seconds'],1)


if __name__=='__main__':unittest.main()
