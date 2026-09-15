"""Real hosted HTTP/process/history smoke check. Uses only the standard library.

python scripts/cloud-smoke.py https://your-site --state-file /tmp/fm-check.json
Restart the backend, then repeat with --verify-restart. The private state file
contains a visitor cookie: do not commit/share it. Checks fail loudly.
"""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid


class Visitor:
    def __init__(self, url, cookie=None):
        self.url=url.rstrip('/');self.cookie=cookie
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.token=self.request('/api/session',headers={'X-FleetMesh-Client':'web'})['token']

    def request(self,path,data=None,request_id=None,headers=None,expected=200):
        h={'Origin':self.url,**(headers or {})}
        if self.cookie:h['Cookie']=self.cookie
        if data is not None:
            h.update({'Content-Type':'application/json','X-FleetMesh-Token':self.token,'X-FleetMesh-Request-ID':request_id or uuid.uuid4().hex})
        req=urllib.request.Request(self.url+path,json.dumps(data).encode() if data is not None else None,h)
        for attempt in range(3):
            try:
                response=self.opener.open(req,timeout=45);break
            except urllib.error.HTTPError as exc:
                response=exc;break
            except (urllib.error.URLError,TimeoutError):
                if attempt==2:raise
                time.sleep(2)
        raw=response.read();assert response.status==expected,(path,response.status,raw[:200])
        if path.startswith('/api/'):
            assert 'no-store' in response.headers.get('Cache-Control',''), 'Private API response cached'
        if response.headers.get('Set-Cookie'):
            self.cookie=response.headers['Set-Cookie'].split(';')[0]
        try:return json.loads(raw)
        except ValueError:return raw.decode()

    def complete(self):
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            state=self.request('/api/state')
            if state['status'] in ('completed','failed','timeout'):
                assert state['status']=='completed',state['status']
                assert state['complete']==state['total_jobs']
                return state
            time.sleep(1)
        raise AssertionError('Run did not finish within 180 wall-clock seconds')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('url');parser.add_argument('--state-file',required=True)
    parser.add_argument('--verify-restart',action='store_true');parser.add_argument('--prepare-restart',action='store_true');args=parser.parse_args()
    path=Path(args.state_file)
    if args.prepare_restart:
        saved=json.loads(path.read_text());visitor=Visitor(args.url,saved['cookie'])
        visitor.request('/api/speed',{'rate':1});request_id=uuid.uuid4().hex
        rid=visitor.request('/api/start',{'jobs':30},request_id)['run_id']
        visitor.request('/api/pause',{})
        assert visitor.request('/api/runs/'+rid+'?frames=1')['frames']
        saved.update(paused_id=rid,start_request=request_id)
        path.write_text(json.dumps(saved));print('Paused run saved; ready for backend restart.');return
    if args.verify_restart:
        saved=json.loads(path.read_text());visitor=Visitor(args.url,saved['cookie'])
        run=visitor.request('/api/runs/'+saved['paused_id']+'?frames=1')
        assert run['status']=='interrupted' and not run['snapshot']['playing']
        assert run['frames'];assert visitor.request('/api/state')['run_id'] is None
        receipt=visitor.request('/api/start',{'jobs':30},saved['start_request'])
        assert receipt['replayed'] and receipt['run_id']==saved['paused_id']
        assert visitor.request('/api/state')['run_id'] is None
        for row in saved['measurements']:
            record=visitor.request('/api/runs/'+row['id']+'?frames=1')
            assert record['status']=='completed' and record['seconds']==row['seconds'] and record['frames']
        print(json.dumps({'restart_persistence':'passed','measurements':saved['measurements']},indent=2));return
    visitor=Visitor(args.url);other=Visitor(args.url)
    def checkpoint(value):
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,'w') as file:json.dump(value,file)
    checkpoint({'cookie':visitor.cookie,'measurements':[]})
    rows=[];workload=None
    for mode in ('baseline','heuristic'):
        options={'seed':200,'robots':3,'jobs':6,'map':'warehouse','scenario':'normal','mode':mode}
        request_id=uuid.uuid4().hex
        start=visitor.request('/api/start',options,request_id)
        assert visitor.request('/api/start',options,request_id)['replayed']
        rid=start['run_id'];other.request('/api/runs/'+rid,expected=404)
        assert other.request('/api/runs')==[]
        visitor.request('/api/speed',{'rate':32})
        state=visitor.complete()
        pids={robot['pid'] for robot in state['robots']};assert len(pids)==3
        run=visitor.request('/api/runs/'+rid+'?frames=1');assert run['frames']
        assert run['seconds']==state['time'] and run['collisions']==state['collisions']
        current={key:run['config'][key] for key in ('seed','robots','jobs','map','scenario')}
        if workload is not None:assert current==workload, 'Comparison workloads differ'
        workload=current
        assert 'job,owner,state' in visitor.request('/api/runs/'+rid+'/csv')
        assert '<html' in visitor.request('/api/runs/'+rid+'/report').lower()
        rows.append({'id':rid,'mode':mode,'seconds':state['time'],'collisions':state['collisions'],'frames':len(run['frames'])})
        checkpoint({'cookie':visitor.cookie,'measurements':rows})
        print(json.dumps(rows[-1]),flush=True)
    # A real fault/recovery run, separate from the matched performance pair.
    rid=visitor.request('/api/demo',{})['run_id'];state=visitor.complete()
    run=visitor.request('/api/runs/'+rid+'?frames=1')
    assert not state['partitioned'] and state['complete']==7
    rows.append({'id':rid,'mode':'disruption-demo','seconds':state['time'],'collisions':state['collisions'],'frames':len(run['frames'])})
    checkpoint({'cookie':visitor.cookie,'measurements':rows})
    visitor.request('/api/speed',{'rate':1})
    request_id=uuid.uuid4().hex
    rid=visitor.request('/api/start',{'jobs':30},request_id)['run_id']
    visitor.request('/api/pause',{})
    assert visitor.request('/api/runs/'+rid+'?frames=1')['frames']
    saved={'cookie':visitor.cookie,'paused_id':rid,'start_request':request_id,'measurements':rows}
    checkpoint(saved)
    print(json.dumps({'http_isolation_exports':'passed','measurements':rows,'restart':'ready; restart backend then use --verify-restart'},indent=2))


if __name__=='__main__':main()
