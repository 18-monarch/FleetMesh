"""Local SQLite experiment records. Parameterized queries and atomic writes."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

class RunStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.directory/'fleetmesh.sqlite3', check_same_thread=False)
        self.lock = threading.RLock()
        with self.connection:
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, started TEXT, status TEXT, config TEXT, snapshot TEXT)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS frames (run_id TEXT, tick INTEGER, snapshot TEXT, PRIMARY KEY(run_id,tick))')
            # A new server cannot resume the old process fleet. Retain the evidence,
            # but never advertise a stale running/paused record as a live session.
            self.connection.execute("UPDATE runs SET status='interrupted' WHERE status IN ('running','paused')")
    def create(self, run_id, config):
        with self.lock, self.connection:
            self.connection.execute('INSERT INTO runs VALUES (?,?,?,?,?)', (run_id,datetime.now(timezone.utc).isoformat(),'running',json.dumps(config),'{}'))
    def save(self, run_id, snapshot, status='running', frame=True):
        raw = json.dumps(snapshot, separators=(',', ':'))
        with self.lock, self.connection:
            self.connection.execute('UPDATE runs SET snapshot=?, status=? WHERE id=?',(raw,status,run_id))
            if frame:
                self.connection.execute('INSERT OR REPLACE INTO frames VALUES (?,?,?)',(run_id,round(snapshot['time']*10),raw))
    def list(self):
        with self.lock:
            rows=self.connection.execute('SELECT id,started,status,config,snapshot FROM runs ORDER BY started DESC LIMIT 100').fetchall()
        return [self.decode(row, False) for row in rows]
    def decode(self,row,full):
        rid,started,status,config,snapshot=row;config=json.loads(config);snapshot=json.loads(snapshot)
        result={'id':rid,'started':started,'status':status,'map':config['map']['name'],'robots':config['robots'],
                'seed':config['seed'],'mode':config['mode'],'scenario':config['scenario'],
                'seconds':snapshot.get('time',0),'complete':snapshot.get('complete',0),
                'jobs':snapshot.get('total_jobs',len(config['jobs'])),'collisions':snapshot.get('collisions',0)}
        if full:
            snapshot=dict(snapshot,status=status)
            if status=='interrupted':snapshot['playing']=False
            result.update(config=config,snapshot=snapshot)
        return result
    def get(self,run_id,frames=False):
        with self.lock:
            row=self.connection.execute('SELECT id,started,status,config,snapshot FROM runs WHERE id=?',(run_id,)).fetchone()
            if not row:raise KeyError('Run not found')
            result=self.decode(row,True)
            if frames:
                result['frames']=[json.loads(row[0]) for row in self.connection.execute('SELECT snapshot FROM frames WHERE run_id=? ORDER BY tick LIMIT 2000',(run_id,))]
        return result
    def close(self):
        self.connection.close()
