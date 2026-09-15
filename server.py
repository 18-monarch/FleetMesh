"""FleetMesh local operations console. Standard library only."""
import argparse
import csv
import io
import json
import math
import os
import re
import secrets
import signal
import threading
import time
import uuid
import webbrowser
from copy import deepcopy
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from storage import RunStore
from transport import ProcessRuntime
from warehouse import MAPS, build_map, edge_key, make_config
from demonstration import Demonstration, run_report
from version import VERSION
from insights import summarize_run

ROOT=Path(__file__).resolve().parent

class InstanceLock:
    def __init__(self,directory):
        Path(directory).mkdir(parents=True,exist_ok=True)
        self.file=open(Path(directory)/'instance.lock','a+b')
        self.file.seek(0);self.file.write(b'0');self.file.flush();self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('FleetMesh is already using this data folder. Open the existing console or choose --data-dir.')
    def close(self):self.file.close()

class Session:
    def __init__(self,directory,store=None):
        self.lock=threading.RLock();self.store=store if store is not None else RunStore(directory);self.runtime=None
        self.run_id=None;self.playing=False;self.rate=8.;self.quit=False;self.status='ready';self.error=None;self.last_save=-1
        self.token=secrets.token_urlsafe(32)
        self.demonstration=None
        self.requests=OrderedDict()
        try:self.model=json.loads((ROOT/'model.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):self.model=None
    def options(self,options):
        if not isinstance(options,dict):raise ValueError('JSON object required')
        map_name=options.get('map','warehouse');scenario=options.get('scenario','normal');mode=options.get('mode','heuristic')
        if map_name not in MAPS or scenario not in ('normal','congestion','network','blocked') or mode not in ('baseline','atomic','heuristic','predictive'):
            raise ValueError('Unknown map, scenario or policy')
        if mode=='predictive' and not self.valid_model():
            raise ValueError('The learned model is unavailable or invalid. Select the fixed rule.')
        seed=integer(options.get('seed',200),0,999999,'seed');count=integer(options.get('robots',3),3,6,'robots');jobs=integer(options.get('jobs',9),1,30,'jobs')
        return make_config(seed,map_name,count,jobs,scenario,mode)
    def start(self,options):
        config=self.options(options)
        with self.lock:
            self.finish('replaced')
            self.demonstration=None
            self.error=None;self.run_id=None;self.status='starting'
            try:
                self.runtime=ProcessRuntime(config,self.model)
                rid=uuid.uuid4().hex
                self.store.create(rid,self.runtime.config)
                self.run_id=rid;self.status='running';self.playing=True;self.last_save=-1
                self.persist()
            except Exception as exc:
                if self.runtime:self.runtime.close()
                self.runtime=None;self.playing=False;self.status='failed';self.error='Could not start robot processes: '+str(exc)
                self.run_id=None
                raise RuntimeError(self.error) from exc
    def valid_model(self):
        weights=self.model.get('weights') if isinstance(self.model,dict) else None
        return isinstance(weights,list) and len(weights)==3 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in weights)
    def execute(self,action,options,request_id=None):
        """Retry protection for local commands, scoped to this server lifetime."""
        if request_id is not None and (not isinstance(request_id,str) or not 8<=len(request_id)<=80 or not all(c.isalnum() or c in '-_' for c in request_id)):
            raise ValueError('Invalid request ID')
        signature=json.dumps([action,options],sort_keys=True,separators=(',',':'))
        with self.lock:
            if request_id in self.requests:
                previous,result=self.requests[request_id]
                if previous!=signature:raise ValueError('Request ID already used for a different command')
                return dict(result,replayed=True)
            self.command(action,options)
            result={'ok':True,'run_id':self.run_id,'request_id':request_id}
            if request_id:
                self.requests[request_id]=(signature,result)
                while len(self.requests)>256:self.requests.popitem(last=False)
            return result
    def persist(self):
        if self.runtime and self.run_id:
            self.store.save(self.run_id,self.snapshot(),self.status)
            self.last_save=self.runtime.world.time
    def finish(self,status):
        if self.runtime:
            if self.status not in ('completed','timeout','failed'):self.status=status
            self.playing=False;self.persist();self.runtime.close();self.runtime=None
    def snapshot(self):
        with self.lock:
            if self.runtime:state=self.runtime.world.snapshot()
            else:state={'time':0,'robots':[],'jobs':[],'events':[],'collisions':0,'minimum_separation':None,'complete':0,'delivered':0,'total_jobs':0,'wait_seconds':0,'distance':0,'transfers':0,'reroutes':0,'map_changes':{},'pending_closures':[],'partitioned':False,'map':build_map()}
            return deepcopy(dict(state,run_id=self.run_id,playing=self.playing,rate=self.rate,status=self.status,error=self.error,
                        backend='Independent processes / authenticated UDP',model_available=self.valid_model(),version=VERSION,
                        demonstration=self.demonstration.snapshot(self.runtime.world) if self.demonstration and self.runtime else None,
                        policy=self.runtime.config['mode'] if self.runtime else 'heuristic'))
    def command(self,action,options):
        with self.lock:
            if action=='start':self.start(options);return
            if action=='demo':
                self.start({'map':'warehouse','scenario':'normal','mode':'heuristic','seed':200,'robots':3,'jobs':6})
                self.demonstration=Demonstration();self.rate=8.;self.persist();return
            if action=='speed':
                rate=options.get('rate',8)
                if isinstance(rate,bool) or rate not in [1,2,4,8,16,32]:raise ValueError('Choose a supported playback speed')
                self.rate=float(rate);return
            if not self.runtime:raise ValueError('Start an experiment first')
            if self.status in ('failed','timeout') or (self.status=='completed' and action!='job'):
                raise ValueError('This run has ended. Start a new experiment; completed runs also accept a new mission.')
            w=self.runtime.world
            if action=='pause':
                if self.status in ('completed','timeout','failed'):raise ValueError('Start a new experiment to continue')
                self.playing=not self.playing;self.status='running' if self.playing else 'paused';self.persist()
            elif action=='maintenance':
                rid=integer(options.get('robot'),0,w.count-1,'robot')
                if rid in w.dead:raise ValueError('An offline process needs a new run')
                value=options.get('available')
                if not isinstance(value,bool):raise ValueError('available must be true or false')
                w.available[rid]=value;w.event('availability',f'R{rid+1} '+('available for new work' if value else 'will hand off unpicked jobs and dock'),rid)
            elif action=='network':
                value=options.get('partitioned')
                if not isinstance(value,bool):raise ValueError('partitioned must be true or false')
                w.partitioned=value;w.event('network','Peer communication '+('interrupted' if value else 'restored'))
            elif action=='kill':self.runtime.kill(integer(options.get('robot'),0,w.count-1,'robot'))
            elif action=='aisle':
                value=options.get('blocked')
                if not isinstance(value,bool):raise ValueError('blocked must be true or false')
                w.set_edge(str(options.get('edge','')),value)
            elif action=='job':
                if len(w.catalog)>=100:raise ValueError('This run has reached the 100-job limit')
                w.add_job(str(options.get('pickup','')),str(options.get('drop','')),integer(options.get('priority',1),1,3,'priority'))
                if self.status=='completed':self.status='running';self.playing=True
            else:raise ValueError('Unknown action')
            self.persist()
    def loop(self):
        while not self.quit:
            started=time.monotonic()
            with self.lock:
                if self.playing and self.runtime:
                    try:
                        if self.demonstration:self.demonstration.advance(self.runtime.world)
                        if self.runtime.step():self.playing=False;self.status='completed'
                        elif self.runtime.world.time>=self.runtime.config['max_seconds']:self.playing=False;self.status='timeout'
                        if self.runtime.world.time-self.last_save>=1 or not self.playing:self.persist()
                    except Exception as exc:
                        self.error=str(exc);self.status='failed';self.playing=False;self.persist()
            time.sleep(max(.002,.1/self.rate-(time.monotonic()-started)))
    def close(self):
        self.quit=True
        with self.lock:self.finish('stopped');self.store.close()

def integer(value,low,high,name):
    if isinstance(value,bool) or not isinstance(value,int) or not low<=value<=high:
        raise ValueError(f'{name} must be an integer from {low} to {high}')
    return value

def media_range(value,size):
    """One HTTP byte range. Ignore unsupported/malformed forms; reject unsatisfiable ranges."""
    if not value or len(value)>160:return None
    match=re.fullmatch(r'bytes=([0-9]*)-([0-9]*)',value.strip())
    if not match or not any(match.groups()):return None
    first,last=match.groups()
    if not first:
        count=int(last)
        if count<=0 or size<=0:raise ValueError('Range not satisfiable')
        return max(0,size-count),size-1
    start=int(first);end=int(last) if last else size-1
    if start>=size or start>end:raise ValueError('Range not satisfiable')
    return start,min(end,size-1)

def make_handler(session):
    class Handler(BaseHTTPRequestHandler):
        timeout=15
        def log_message(self,*args):pass
        def security_headers(self):
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        def respond(self,data,kind='application/json',status=200,filename=None,headers=None,cache_control='no-store'):
            if isinstance(data,(dict,list)):data=json.dumps(data).encode()
            elif isinstance(data,str):data=data.encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Cache-Control',cache_control)
            self.send_header('Content-Length',str(len(data)))
            self.security_headers()
            for key,value in (headers or {}).items():self.send_header(key,value)
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers()
            if self.command=='HEAD':return
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def stream_media(self,file):
            with file.open('rb') as stream:
                size=os.fstat(stream.fileno()).st_size
                # No validator is emitted, so If-Range falls back to the complete representation.
                value=self.headers.get('Range') if self.command=='GET' and not self.headers.get('If-Range') else None
                try:part=media_range(value,size)
                except ValueError:return self.respond(b'',kind='video/mp4',status=416,headers={'Content-Range':f'bytes */{size}','Accept-Ranges':'bytes'})
                start,end=part if part else (0,size-1);remaining=max(0,end-start+1)
                self.send_response(206 if part else 200)
                self.send_header('Content-Type','video/mp4');self.send_header('Content-Length',str(remaining))
                self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','private, max-age=3600')
                if part:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.security_headers();self.end_headers()
                if self.command=='HEAD':return
                stream.seek(start)
                try:
                    while remaining:
                        chunk=stream.read(min(65536,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
                except (BrokenPipeError,ConnectionResetError):pass
        def valid_host(self):
            return self.headers.get('Host','').split(':')[0] in ('127.0.0.1','localhost')
        def do_HEAD(self):self.do_GET()
        def do_GET(self):
            if not self.valid_host():return self.respond({'error':'Local host required'},status=403)
            parsed=urlparse(self.path);path=parsed.path
            try:
                if path in ('/','/app','/app/'):
                    page='experience.html' if path=='/' else 'index.html'
                    return self.respond((ROOT/'web'/page).read_text(encoding='utf-8').replace('__TOKEN__',session.token).replace('__VERSION__',VERSION),'text/html; charset=utf-8')
                static={
                    '/favicon.svg':('favicon.svg', 'image/svg+xml'),
                    '/favicon.ico':('favicon.svg', 'image/svg+xml'),
                    '/app.js':('app.js', 'text/javascript'),
                    '/workspace.js':('workspace.js', 'text/javascript'),
                    '/entry.js':('entry.js', 'text/javascript'),
                    '/style.css':('style.css', 'text/css'),
                    '/cinema.css':('cinema.css', 'text/css'),
                    '/experience.css':('experience.css', 'text/css'),
                    '/experience.js':('experience.js', 'text/javascript'),
                    '/film-player.js':('film-player.js', 'text/javascript'),
                    '/sequence-player.js':('sequence-player.js', 'text/javascript'),
                    '/media/warehouse-film.mp4':('media/warehouse-film.mp4', 'video/mp4'),
                    '/media/warehouse-film-poster.webp':('media/warehouse-film-poster.webp', 'image/webp'),
                    '/media/warehouse-opening.png':('media/warehouse-opening.png', 'image/png'),
                    '/media/warehouse-coordination.png':('media/warehouse-coordination.png', 'image/png'),
                    '/warehouse-scene.js':('warehouse-scene.js', 'text/javascript'),
                    '/journey.js':('journey.js', 'text/javascript'),
                    '/warehouse-poster.svg':('warehouse-poster.svg', 'image/svg+xml'),
                    '/vendor/three.module.min.js':('vendor/three.module.min.js', 'text/javascript'),
                    '/vendor/three.core.min.js':('vendor/three.core.min.js', 'text/javascript'),
                    '/guide':('../docs/guide.html', 'text/html; charset=utf-8'),
                }
                if path in static:
                    file,kind=static[path]
                    if kind=='video/mp4':return self.stream_media(ROOT/'web'/file)
                    return self.respond((ROOT/'web'/file).read_bytes(),kind)
                frame=re.fullmatch(r'/media/warehouse-frames/frame-([0-9]{3})\.webp',path)
                if frame and int(frame.group(1))<141:
                    file=ROOT/'web/media/warehouse-frames'/('frame-'+frame.group(1)+'.webp')
                    return self.respond(file.read_bytes(),'image/webp',cache_control='private, max-age=3600')
                if path=='/api/state':return self.respond(session.snapshot())
                if path=='/api/health':return self.respond({'ok':True,'version':VERSION})
                if path=='/api/evidence':
                    file=ROOT/'evidence/summary.json'
                    return self.respond(json.loads(file.read_text(encoding='utf-8')) if file.exists() else {'cohorts':[],'total_runs':0,'limits':['Run evaluate.py to generate evidence.']})
                if path=='/api/runs':return self.respond(session.store.list())
                if path in ('/api/sample','/api/sample/insights','/api/sample/report'):
                    sample=json.loads((ROOT/'evidence/demonstration.json').read_text(encoding='utf-8'))['record']
                    if path.endswith('/insights'):return self.respond(summarize_run(sample))
                    if path.endswith('/report'):return self.respond(run_report(sample),'text/html; charset=utf-8',filename='fleetmesh-recorded-sample.html')
                    return self.respond(sample)
                if path.startswith('/api/runs/'):
                    parts=path.strip('/').split('/');rid=parts[2]
                    if len(rid)!=32 or any(c not in '0123456789abcdef' for c in rid):raise KeyError('Run not found')
                    if len(parts)>4 or (len(parts)==4 and parts[3] not in ('csv','report','insights')):raise KeyError('Run not found')
                    with session.lock:
                        if rid==session.run_id:session.persist()
                    record=session.store.get(rid,frames=parse_qs(parsed.query).get('frames')==['1'] or path.endswith('/insights'))
                    if len(parts)==4 and parts[3]=='insights':return self.respond(summarize_run(record))
                    if len(parts)==4 and parts[3]=='report':
                        return self.respond(run_report(record),'text/html; charset=utf-8',filename='fleetmesh-report-'+rid[:8]+'.html')
                    if len(parts)==4 and parts[3]=='csv':
                        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['job','owner','state','pickup','drop','priority','delivered_at','completed_at'])
                        for j in record['snapshot'].get('jobs',[]):writer.writerow([j.get(k,'') for k in ['id','owner','state','pickup','drop','priority','delivered_at','completed_at']])
                        return self.respond(stream.getvalue(),'text/csv; charset=utf-8',filename='fleetmesh-jobs-'+rid[:8]+'.csv')
                    return self.respond(record,filename='fleetmesh-run-'+rid[:8]+'.json' if parse_qs(parsed.query).get('download') else None)
                return self.respond({'error':'Not found'},status=404)
            except KeyError:return self.respond({'error':'Run not found'},status=404)
            except Exception as exc:return self.respond({'error':str(exc)},status=500)
        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-FleetMesh-Token')!=session.token:return self.respond({'error':'Invalid local session token'},status=403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.respond({'error':'JSON required'},status=415)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<=length<=4096:raise ValueError('Request too large')
                options=json.loads(self.rfile.read(length) or '{}')
                if not isinstance(options,dict):raise ValueError('JSON object required')
                path=urlparse(self.path).path
                if not path.startswith('/api/'):raise ValueError('Unknown route')
                self.respond(session.execute(path[5:],options,self.headers.get('X-FleetMesh-Request-ID')))
            except (ValueError,TypeError) as exc:self.respond({'error':str(exc)},status=400)
            except Exception as exc:self.respond({'error':str(exc)},status=500)
    return Handler

def main():
    parser=argparse.ArgumentParser(description='FleetMesh local warehouse coordination simulator')
    parser.add_argument('--port',type=int,default=9292);parser.add_argument('--data-dir',type=Path,default=ROOT/'data');parser.add_argument('--open',action='store_true');args=parser.parse_args()
    instance=InstanceLock(args.data_dir);session=Session(args.data_dir);server=None
    try:
        for port in ([0] if args.port==0 else range(args.port,min(args.port+11,65536))):
            try:server=ThreadingHTTPServer(('127.0.0.1',port),make_handler(session));break
            except OSError:continue
        if server is None:raise RuntimeError('No local port available; choose --port 9400')
        thread=threading.Thread(target=session.loop,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        print('FleetMesh '+VERSION+' running at '+url,flush=True)
        print('Keep this terminal open. Ctrl+C stops the simulation. Data: '+str(args.data_dir),flush=True)
        if args.open:webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        session.close();instance.close()
        if server:server.server_close()
if __name__=='__main__':main()
