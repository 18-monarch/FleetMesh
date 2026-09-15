"""Bounded public demo server. Agent algorithms remain in the original processes."""
import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import threading
import time
from collections import OrderedDict, deque
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from cloud_storage import CloudDatabase, ScopedStore, StorageUnavailable
from server import Session, make_handler
from version import VERSION


class CapacityError(ValueError):
    pass


class CloudSession(Session):
    def __init__(self, database, owner):
        super().__init__(None, ScopedStore(database, owner))
        self.last_seen = time.monotonic()
        self.started_wall = 0
        self.last_snapshot = None
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def start(self, options):
        super().start(options)
        self.started_wall = time.monotonic()
        self.last_snapshot = None

    def snapshot(self):
        if not self.runtime and self.last_snapshot:
            from copy import deepcopy
            result = deepcopy(self.last_snapshot)
            result.update(playing=False, released=True)
        else:
            result = super().snapshot()
        result.update(cloud=True, storage_error=self.store.error,
                      retention='Saved for up to 7 days; latest 80 runs across this demo. This browser holds your access cookie.')
        return result

    def release(self, status='interrupted'):
        with self.lock:
            if self.runtime:
                if self.status not in ('completed', 'timeout', 'failed'):
                    self.status = status
                self.playing = False
                self.last_snapshot = self.snapshot()
                try:
                    self.persist()
                finally:
                    self.runtime.close()
                    self.runtime = None

    def loop(self):
        while not self.quit:
            started = time.monotonic()
            with self.lock:
                if self.playing and self.runtime:
                    try:
                        if self.demonstration:
                            self.demonstration.advance(self.runtime.world)
                        if self.runtime.step():
                            self.playing = False; self.status = 'completed'
                        elif self.runtime.world.time >= self.runtime.config['max_seconds']:
                            self.playing = False; self.status = 'timeout'
                        if self.runtime.world.time-self.last_save >= 1 or not self.playing:
                            self.persist()
                    except Exception:
                        self.error = 'A robot process failed. Inspect the saved run and start a new experiment.'
                        self.status = 'failed'; self.playing = False
                        self.release('failed')
            time.sleep(max(.004, .1/self.rate-(time.monotonic()-started)))

    def close(self):
        self.quit = True
        self.release()
        self.thread.join(3)
        self.store.close()


class Manager:
    def __init__(self, database, secret, origins, max_active=2, idle_seconds=120, max_seconds=600):
        if len(secret) < 32:
            raise ValueError('SESSION_SECRET must contain at least 32 characters.')
        self.db, self.secret, self.origins = database, secret.encode(), set(origins)
        self.max_active, self.idle_seconds, self.max_seconds = max_active, idle_seconds, max_seconds
        self.sessions = OrderedDict()
        self.lock = threading.RLock()
        self.rates = OrderedDict()
        self.stop = threading.Event()
        self.cleaner = threading.Thread(target=self.cleanup, daemon=True)
        self.cleaner.start()

    def signature(self, value):
        return hmac.new(self.secret, value.encode(), hashlib.sha256).hexdigest()

    def issue(self):
        value = f'{int(time.time())}:{secrets.token_hex(24)}'
        return value+'.'+self.signature(value)

    def owner(self, cookie):
        try:
            value, signature = cookie.rsplit('.', 1)
            stamp, nonce = value.split(':')
            if not re.fullmatch('[0-9a-f]{48}', nonce) or not 0 <= time.time()-int(stamp) <= 7*86400:
                return None
            if hmac.compare_digest(signature, self.signature(value)):
                return hashlib.sha256(value.encode()).hexdigest()
        except (ValueError, AttributeError):
            pass
        return None

    def csrf(self, owner):
        return self.signature('csrf:'+owner)

    def allowed(self, key, count, seconds=60):
        with self.lock:
            now = time.monotonic()
            bucket = self.rates.setdefault(key, deque())
            self.rates.move_to_end(key)
            while bucket and bucket[0] < now-seconds:
                bucket.popleft()
            if len(bucket) >= count:
                return False
            bucket.append(now)
            while len(self.rates) > 256:
                self.rates.popitem(last=False)
            return True

    def get(self, owner):
        with self.lock:
            if owner not in self.sessions:
                if len(self.sessions) >= 24:
                    raise CapacityError('The demo is busy. Please retry in two minutes.')
                self.sessions[owner] = CloudSession(self.db, owner)
            session = self.sessions[owner]
            session.last_seen = time.monotonic()
            return session

    def execute(self, owner, action, options, request_id):
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,80}', request_id or ''):
            raise ValueError('A valid request ID is required.')
        if action not in ('start','demo','speed','pause','maintenance','network','kill','aisle','job'):
            raise ValueError('Unknown action')
        session = self.get(owner)
        # Serialize admission, not the simulation ticks of each independent visitor.
        with self.lock, session.lock:
            if action in ('start','demo'):
                session.options(options if action == 'start' else {})
                active = sum(s.runtime is not None for s in self.sessions.values() if s is not session)
                if active >= self.max_active:
                    for other in self.sessions.values():
                        if other is not session and other.runtime and other.status in ('completed','failed','timeout'):
                            other.release()
                    active = sum(s.runtime is not None for s in self.sessions.values() if s is not session)
                if active >= self.max_active:
                    raise CapacityError('Both demo slots are in use. Watch the recorded demo or retry shortly.')
            signature = json.dumps([action, options], sort_keys=True, separators=(',', ':'), allow_nan=False)
            previous = self.db.begin_command(owner, request_id, signature)
            if previous is not None:
                return dict(previous, replayed=True)
            try:
                result = session.execute(action, options, request_id)
                session.store.flush()
            except (ValueError, TypeError) as exc:
                result = {'ok':False, 'error':str(exc)}
            # A failure here leaves a durable pending command. Retrying cannot duplicate it.
            self.db.end_command(owner, request_id, result)
            return result

    def cleanup(self):
        last_prune = time.monotonic()
        while not self.stop.wait(5):
            expired = []
            with self.lock:
                now = time.monotonic()
                for owner, session in list(self.sessions.items()):
                    if session.runtime and now-session.started_wall > self.max_seconds:
                        session.release('timeout')
                    if now-session.last_seen > self.idle_seconds:
                        expired.append(self.sessions.pop(owner))
            for session in expired:
                try:
                    session.close()
                except StorageUnavailable:
                    pass
            if time.monotonic()-last_prune > 300:
                try:
                    self.db.prune()
                except StorageUnavailable:
                    pass
                last_prune = time.monotonic()

    def close(self):
        self.stop.set()
        self.cleaner.join(6)
        for session in list(self.sessions.values()):
            try:
                session.close()
            except StorageUnavailable:
                pass
        self.db.close()


def make_cloud_handler(manager, secure=True):
    local = threading.local()

    class Proxy:
        def __getattr__(self, name):
            if name == 'token':
                return ''  # Cloud HTML never embeds a credential.
            return getattr(local.session, name)

    base = make_handler(Proxy())

    class Handler(base):
        timeout = 10

        def valid_host(self):
            # Cloud CSRF/Origin checks and signed cookies replace the local-host boundary.
            return True

        def security_headers(self):
            super().security_headers()
            self.send_header('Referrer-Policy', 'same-origin')
            self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
            if getattr(self, 'new_cookie', None):
                self.send_header('Set-Cookie', 'fm_session='+self.new_cookie+'; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800'+('; Secure' if secure else ''))

        def respond(self, data, kind='application/json', status=200, **kwargs):
            if status >= 500:
                data = {'error':'The service is temporarily unavailable. Retry shortly; saved history is retained.'}
            return super().respond(data, kind, status, **kwargs)

        def identity(self):
            try:
                cookies = SimpleCookie(self.headers.get('Cookie',''))
                return manager.owner(cookies['fm_session'].value) if 'fm_session' in cookies else None
            except Exception:
                return None

        def check_origin(self):
            origin = self.headers.get('Origin')
            return not origin or origin in manager.origins

        def do_GET(self):
            path = urlparse(self.path).path
            if path == '/api/health':
                return self.respond({'ok':True,'version':VERSION,'mode':'cloud'})
            if path.startswith('/api/') and not self.check_origin():
                return self.respond({'error':'Origin not allowed'}, status=403)
            owner = self.identity()
            if path == '/api/session':
                if self.headers.get('X-FleetMesh-Client') != 'web':
                    return self.respond({'error':'Session initialization header required'}, status=403)
                if not owner:
                    if not manager.allowed('new-session', 30):
                        return self.respond({'error':'Too many new sessions. Retry in a minute.'}, status=429)
                    self.new_cookie = manager.issue()
                    owner = manager.owner(self.new_cookie)
                return self.respond({'token':manager.csrf(owner), 'cloud':True, 'poll_ms':1000,
                                     'history_days':7,'max_active':manager.max_active})
            private = path == '/api/state' or path == '/api/runs' or path.startswith('/api/runs/')
            if private:
                if not owner:
                    return self.respond({'error':'Open the console to initialize your visitor session.'}, status=401)
                if not manager.allowed(owner+':read', 180):
                    return self.respond({'error':'Please slow down and retry shortly.'}, status=429)
                try:
                    local.session = manager.get(owner)
                except CapacityError as exc:
                    return self.respond({'error':str(exc)}, status=429)
            try:
                return super().do_GET()
            finally:
                local.__dict__.clear()

        def do_POST(self):
            owner = self.identity()
            if not owner or not self.check_origin() or not hmac.compare_digest(self.headers.get('X-FleetMesh-Token',''), manager.csrf(owner)):
                return self.respond({'error':'Session expired or request not authorized. Reload the console.'}, status=403)
            if not manager.allowed(owner+':control', 40):
                return self.respond({'error':'Too many commands. Please wait a minute.'}, status=429)
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.respond({'error':'JSON required'}, status=415)
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Transfer encoding is not supported')
                length = int(self.headers.get('Content-Length','0'))
                if not 0 <= length <= 4096:
                    raise ValueError('Request too large')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('Incomplete request')
                options = json.loads(raw or '{}', parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Finite numbers required')))
                if not isinstance(options, dict):
                    raise ValueError('JSON object required')
                path = urlparse(self.path).path
                if not path.startswith('/api/'):
                    raise ValueError('Unknown action')
                result = manager.execute(owner, path[5:], options, self.headers.get('X-FleetMesh-Request-ID'))
                return self.respond(result, status=200 if result.get('ok') else 400)
            except CapacityError as exc:
                return self.respond({'error':str(exc)}, status=429)
            except (ValueError, TypeError) as exc:
                return self.respond({'error':str(exc)}, status=400)
            except StorageUnavailable:
                return self.respond({}, status=503)
            except Exception:
                return self.respond({}, status=500)

        def do_OPTIONS(self):
            return self.respond({'error':'Use the same-origin frontend API routes.'}, status=405)

    return Handler


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, *args, **kwargs):
        self.slots = threading.BoundedSemaphore(24)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            try:
                request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def main():
    local = os.environ.get('FLEETMESH_LOCAL_CLOUD') == '1'
    url = os.environ.get('DATABASE_URL')
    if not local and not url:
        raise SystemExit('DATABASE_URL is required for cloud hosting.')
    secret = os.environ.get('SESSION_SECRET','')
    if len(secret) < 32:
        raise SystemExit('Set a stable SESSION_SECRET of at least 32 characters.')
    origins = [v.strip().rstrip('/') for v in os.environ.get('ALLOWED_ORIGINS','').split(',') if v.strip()]
    if not origins:
        raise SystemExit('ALLOWED_ORIGINS must list the exact frontend HTTPS origin(s).')
    db = CloudDatabase(url=url, sqlite_path=os.environ.get('FLEETMESH_SQLITE_PATH','/tmp/fleetmesh-cloud.sqlite3') if local and not url else None)
    if local:
        db.migrate()
    try:
        db.boot()
    except Exception:
        db.close()
        raise SystemExit('Database startup failed. Apply migrate.py and verify connectivity; details redacted.')
    manager = Manager(db, secret, origins, max_active=int(os.environ.get('MAX_ACTIVE_RUNS','2')))
    server = BoundedServer(('127.0.0.1' if local else '0.0.0.0', int(os.environ.get('PORT','9292'))), make_cloud_handler(manager, secure=not local))
    def shutdown(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f'FleetMesh cloud ready on port {server.server_port}. Database: '+('PostgreSQL' if db.pg else 'local SQLite'), flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        manager.close()


if __name__ == '__main__':
    main()
