"""Scoped cloud history. PostgreSQL in hosting; explicit SQLite mode for local tests."""
import json
import sqlite3
import threading
import time
import zlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from storage import RunStore


class StorageUnavailable(RuntimeError):
    pass


def pack(value):
    return zlib.compress(json.dumps(value, separators=(',', ':'), allow_nan=False).encode(), 3)


def unpack(value):
    return json.loads(zlib.decompress(bytes(value)))


class CloudDatabase:
    def __init__(self, url=None, sqlite_path=None):
        self.pg = bool(url)
        self.lock = threading.RLock()
        if self.pg:
            from psycopg_pool import ConnectionPool
            self.pool = ConnectionPool(url, min_size=0, max_size=4, timeout=8,
                                       max_idle=60, kwargs={'connect_timeout': 8, 'prepare_threshold': None})
        elif sqlite_path:
            self.connection = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.connection.execute('PRAGMA foreign_keys=ON')
            self.connection.execute('PRAGMA journal_mode=WAL')
        else:
            raise ValueError('DATABASE_URL is required. SQLite requires an explicit local path.')

    @contextmanager
    def transaction(self):
        try:
            if self.pg:
                with self.pool.connection() as connection:
                    with connection.transaction():
                        connection.execute("SET LOCAL statement_timeout = '8000ms'")
                        yield connection
            else:
                with self.lock, self.connection:
                    yield self.connection
        except (KeyError, ValueError):
            raise
        except Exception as exc:
            raise StorageUnavailable('Saved-data service unavailable. Please retry shortly.') from exc

    def sql(self, connection, query, args=()):
        return connection.execute(query.replace('?', '%s') if self.pg else query, args)

    def migrate(self):
        script = (Path(__file__).parent/'migrations/001_cloud.sql').read_text()
        if not self.pg:
            script = script.replace('BYTEA', 'BLOB')
        with self.transaction() as conn:
            for statement in script.split(';'):
                if statement.strip():
                    conn.execute(statement)

    def boot(self):
        with self.transaction() as conn:
            self.sql(conn, "SELECT version FROM fm_schema WHERE version=1").fetchone()
            self.sql(conn, "UPDATE fm_runs SET status='interrupted' WHERE status IN ('running','paused','starting')")
        self.prune()

    def prune(self):
        with self.transaction() as conn:
            self.sql(conn, 'DELETE FROM fm_commands WHERE created < ?', (time.time()-7*86400,))
            # Never remove a live run. Global bound keeps the public demo within a small DB.
            self.sql(conn, "DELETE FROM fm_runs WHERE status NOT IN ('running','paused','starting') AND (started < ? OR id IN (SELECT id FROM fm_runs ORDER BY started DESC LIMIT 100000 OFFSET 80))", (time.time()-7*86400,))

    def create(self, owner, rid, config):
        with self.transaction() as conn:
            self.sql(conn, 'INSERT INTO fm_runs VALUES (?,?,?,?,?,?)',
                     (rid, owner, time.time(), 'running', json.dumps(config), pack({})))

    def save(self, owner, rid, snapshot, status, frame=True):
        data = pack(snapshot)
        with self.transaction() as conn:
            cur = self.sql(conn, 'UPDATE fm_runs SET snapshot=?,status=? WHERE id=? AND owner=?', (data, status, rid, owner))
            if not cur.rowcount:
                raise KeyError('Run not found')
            if frame:
                tick = round(snapshot['time']*10)
                self.sql(conn, 'INSERT INTO fm_frames VALUES (?,?,?) ON CONFLICT(run_id,tick) DO UPDATE SET snapshot=excluded.snapshot', (rid, tick, data))
                # Retain recent sampled frames; exact final state/events remain in the run record.
                self.sql(conn, 'DELETE FROM fm_frames WHERE run_id=? AND tick IN (SELECT tick FROM fm_frames WHERE run_id=? ORDER BY tick DESC LIMIT 100000 OFFSET 900)', (rid, rid))

    def records(self, owner, rid=None, frames=False):
        with self.transaction() as conn:
            query = 'SELECT id,started,status,config,snapshot FROM fm_runs WHERE owner=?'
            args = (owner,)
            if rid:
                query += ' AND id=?'; args += (rid,)
            rows = self.sql(conn, query+' ORDER BY started DESC LIMIT 80', args).fetchall()
            results = []
            for row in rows:
                rid_, started, status, config, snapshot = row
                started = datetime.fromtimestamp(started, timezone.utc).isoformat()
                decoded = (rid_, started, status, config, json.dumps(unpack(snapshot)))
                result = RunStore.decode(self, decoded, bool(rid))
                if rid and frames:
                    result['frames'] = [unpack(v[0]) for v in self.sql(conn, 'SELECT snapshot FROM fm_frames WHERE run_id=? ORDER BY tick', (rid_,))]
                    result['replay_note'] = 'Sampled at most once per wall-clock second, plus control/terminal checkpoints; up to 900 recent frames.'
                results.append(result)
        if rid and not results:
            raise KeyError('Run not found')
        return results[0] if rid else results

    def begin_command(self, owner, request_id, signature):
        with self.transaction() as conn:
            existing = self.sql(conn, 'SELECT signature,result FROM fm_commands WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
            if not existing and self.sql(conn, 'SELECT COUNT(*) FROM fm_commands').fetchone()[0] >= 10000:
                raise ValueError('The free demo has reached its saved-command capacity. Existing history is still available.')
            cur = self.sql(conn, 'INSERT INTO fm_commands VALUES (?,?,?,?,?) ON CONFLICT(owner,request_id) DO NOTHING',
                           (owner, request_id, signature, None, time.time()))
            if cur.rowcount:
                return None
            old, result = self.sql(conn, 'SELECT signature,result FROM fm_commands WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
            if old != signature:
                raise ValueError('Request ID was already used for a different command.')
            if result is None:
                raise ValueError('Previous command outcome is unconfirmed. Inspect the run before issuing a new command.')
            return json.loads(result)

    def end_command(self, owner, request_id, result):
        with self.transaction() as conn:
            self.sql(conn, 'UPDATE fm_commands SET result=? WHERE owner=? AND request_id=?', (json.dumps(result), owner, request_id))

    def close(self):
        self.pool.close() if self.pg else self.connection.close()


class ScopedStore:
    """One bounded, coalescing writer per visitor; simulation ticks never wait for SQL."""
    def __init__(self, database, owner):
        self.db, self.owner = database, owner
        self.condition = threading.Condition()
        self.pending = {}
        self.writing = False
        self.closed = False
        self.error = None
        self.last_frame = 0.
        self.revision = 0
        self.saved_revision = 0
        self.thread = threading.Thread(target=self._write, daemon=True)
        self.thread.start()

    def create(self, rid, config):
        self.flush()
        self.db.create(self.owner, rid, config)

    def save(self, rid, snapshot, status='running', frame=True):
        now = time.monotonic()
        with self.condition:
            # Snapshot is already copied by Session; latest wins under DB backpressure.
            take_frame = frame and (status != 'running' or now-self.last_frame >= 1)
            if take_frame:
                self.last_frame = now
            if rid in self.pending:
                take_frame |= self.pending[rid][2]
            self.revision += 1
            self.pending[rid] = (snapshot, status, take_frame, self.revision)
            self.condition.notify_all()

    def _write(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.pending or self.closed)
                if self.closed and not self.pending:
                    return
                # Coalesce high-speed simulation checkpoints into bounded SQL traffic.
                if not self.closed:
                    self.condition.wait_for(lambda: self.closed, timeout=.75)
                pending, self.pending = self.pending, {}
                if not pending:
                    continue
                self.writing = True
            try:
                for rid, (snapshot, status, frame, revision) in pending.items():
                    self.db.save(self.owner, rid, snapshot, status, frame)
                self.saved_revision = max(self.saved_revision, *(item[3] for item in pending.values()))
                self.error = None
            except KeyError:
                self.error = 'This saved run has expired under the public demo retention limit.'
                self.saved_revision = max(self.saved_revision, *(item[3] for item in pending.values()))
            except StorageUnavailable:
                self.error = 'History is temporarily unsaved. Simulation continues; reconnect to save the latest state.'
                with self.condition:
                    if not self.closed:
                        for rid, item in pending.items():
                            self.pending.setdefault(rid, item)
                time.sleep(1)
            finally:
                with self.condition:
                    self.writing = False
                    self.condition.notify_all()

    def flush(self, timeout=10):
        with self.condition:
            target = self.revision
            if not self.condition.wait_for(lambda: self.saved_revision >= target, timeout):
                raise StorageUnavailable('History save is pending. Retry after the database reconnects.')

    def list(self):
        self.flush()
        return self.db.records(self.owner)

    def get(self, rid, frames=False):
        self.flush()
        return self.db.records(self.owner, rid, frames)

    def close(self):
        try:
            self.flush(timeout=4)
        finally:
            with self.condition:
                self.closed = True
                self.pending.clear()
                self.condition.notify_all()
            self.thread.join(10)
