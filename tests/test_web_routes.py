"""Real HTTP checks for the locally bundled cinematic experience."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Session,make_handler
from version import VERSION

class WebRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.session=Session(cls.temp.name)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.session))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.session.close();cls.temp.cleanup()

    def get(self,path,headers=None,method='GET'):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        connection.request(method,path,headers=headers or {})
        response=connection.getresponse();data=response.read();headers=dict(response.getheaders());status=response.status;connection.close()
        return status,headers,data

    def test_entry_and_console_are_separate_and_read_only(self):
        status,headers,home=self.get('/')
        self.assertEqual(status,200);self.assertIn(b'Every robot.',home)
        self.assertNotIn(b'__VERSION__',home);self.assertNotIn(b'fleetmesh-token',home)
        for route in ['/app','/app/']:
            status,headers,app=self.get(route)
            self.assertEqual(status,200);self.assertIn(self.session.token.encode(),app);self.assertIn(b'/cinema.css',app)
        self.assertIsNone(self.session.runtime);self.assertEqual(self.session.store.list(),[])

    def test_all_local_assets_have_correct_mime_and_csp(self):
        routes={'/favicon.svg':'image/svg+xml','/favicon.ico':'image/svg+xml','/app.js':'text/javascript','/workspace.js':'text/javascript','/entry.js':'text/javascript','/experience.js':'text/javascript','/journey.js':'text/javascript','/warehouse-scene.js':'text/javascript','/vendor/three.module.min.js':'text/javascript','/vendor/three.core.min.js':'text/javascript','/style.css':'text/css','/cinema.css':'text/css','/experience.css':'text/css','/warehouse-poster.svg':'image/svg+xml'}
        for route,kind in routes.items():
            with self.subTest(route=route):
                status,headers,data=self.get(route)
                self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],kind);self.assertGreater(len(data),50)
                self.assertIn("script-src 'self'",headers['Content-Security-Policy']);self.assertEqual(headers['X-Content-Type-Options'],'nosniff')

    def test_non_local_hosts_and_unlisted_paths_stay_restricted(self):
        self.assertEqual(self.get('/app',{'Host':'example.com'})[0],403)
        for path in ['/web/experience.html','/vendor/../server.py','/vendor/package.json','/web/package.json']:
            self.assertEqual(self.get(path)[0],404)

    def test_home_metrics_use_the_same_retained_evidence_as_console(self):
        status,headers,content=self.get('/api/evidence');data=json.loads(content)
        self.assertEqual(status,200);self.assertEqual(data['total_runs'],160);self.assertEqual(len(data['cohorts']),5)
        status,headers,content=self.get('/api/state');self.assertIsNone(json.loads(content)['run_id'])

    def test_frame_sequence_is_local_and_explicitly_illustrative(self):
        status,headers,home=self.get('/')
        self.assertIn(b'AI-GENERATED VISUALS',home);self.assertIn(('data-frames="/media/warehouse-frames/frame-{index}.webp?v='+VERSION+'"').encode(),home)
        self.assertIn(b'data-count="141"',home);self.assertIn(b'<canvas',home);self.assertNotIn(b'<video',home)
        self.assertIn(b'Coordination concept',home);self.assertIn(b'Illustrative still',home);self.assertNotIn(b'concept-label',home)
        self.assertIn("media-src 'self'",headers['Content-Security-Policy'])
        for path,kind in [('/sequence-player.js','text/javascript'),('/film-player.js','text/javascript'),('/media/warehouse-film-poster.webp','image/webp'),('/media/warehouse-opening.png','image/png'),('/media/warehouse-coordination.png','image/png')]:
            status,headers,data=self.get(path);self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],kind)

    def test_frame_images_are_byte_exact_cacheable_and_head_safe(self):
        base=Path(__file__).resolve().parents[1]/'web/media/warehouse-frames'
        for index in [0,70,140]:
            name=f'frame-{index:03d}.webp';expected=(base/name).read_bytes()
            status,headers,data=self.get('/media/warehouse-frames/'+name+'?v=1.8.0')
            self.assertEqual(status,200);self.assertEqual(data,expected)
            self.assertEqual(headers['Content-Type'],'image/webp')
            self.assertEqual(headers['Cache-Control'],'private, max-age=3600')
            status,headers,data=self.get('/media/warehouse-frames/'+name,method='HEAD')
            self.assertEqual(status,200);self.assertEqual(data,b'');self.assertEqual(int(headers['Content-Length']),len(expected))

    def test_frame_route_is_bounded_and_cannot_escape_media(self):
        for name in ['frame-141.webp','frame-999.webp','frame--01.webp','frame-0.webp','frame-0000.webp','frame-000.png','../warehouse-film.mp4','%2e%2e/server.py']:
            with self.subTest(name=name):self.assertEqual(self.get('/media/warehouse-frames/'+name)[0],404)
        self.assertEqual(self.get('/media/warehouse-frames/frame-000.webp',{'Host':'example.com'})[0],403)
        self.assertIsNone(self.session.runtime)

    def test_complete_film_matches_file_and_head_is_bodyless(self):
        expected=(Path(__file__).resolve().parents[1]/'web/media/warehouse-film.mp4').read_bytes()
        status,headers,data=self.get('/media/warehouse-film.mp4?v=1.8.0')
        self.assertEqual(status,200);self.assertEqual(data,expected);self.assertEqual(headers['Accept-Ranges'],'bytes')
        status,headers,data=self.get('/media/warehouse-film.mp4',{'Range':'bytes=0-1'},method='HEAD')
        self.assertEqual(status,200);self.assertEqual(data,b'');self.assertEqual(int(headers['Content-Length']),len(expected))

    def test_byte_ranges_match_exact_requested_bytes(self):
        expected=(Path(__file__).resolve().parents[1]/'web/media/warehouse-film.mp4').read_bytes();size=len(expected)
        for value,start,end in [('bytes=0-1',0,1),('bytes=200-511',200,511),('bytes=-128',size-128,size-1),(f'bytes={size-16}-',size-16,size-1),(f'bytes={size-5}-{size+100}',size-5,size-1)]:
            with self.subTest(value=value):
                status,headers,data=self.get('/media/warehouse-film.mp4',{'Range':value})
                self.assertEqual(status,206);self.assertEqual(data,expected[start:end+1]);self.assertEqual(headers['Content-Range'],f'bytes {start}-{end}/{size}')
                self.assertEqual(int(headers['Content-Length']),end-start+1)

    def test_unsatisfiable_ranges_return_416(self):
        size=(Path(__file__).resolve().parents[1]/'web/media/warehouse-film.mp4').stat().st_size
        for value in [f'bytes={size}-','bytes=-0','bytes=80-20']:
            status,headers,data=self.get('/media/warehouse-film.mp4',{'Range':value})
            self.assertEqual(status,416);self.assertEqual(headers['Content-Range'],f'bytes */{size}');self.assertEqual(data,b'')

    def test_unsupported_ranges_and_unvalidated_if_range_use_full_response(self):
        size=(Path(__file__).resolve().parents[1]/'web/media/warehouse-film.mp4').stat().st_size
        for headers in [{'Range':'items=0-2'},{'Range':'bytes=0-2,6-8'},{'Range':'bytes=-'},{'Range':'bytes=nope'},{'Range':'bytes=0-2','If-Range':'unknown-version'}]:
            status,returned,data=self.get('/media/warehouse-film.mp4',headers)
            self.assertEqual(status,200);self.assertEqual(len(data),size)

    def test_media_cannot_bypass_local_host_or_static_allowlist(self):
        self.assertEqual(self.get('/media/warehouse-film.mp4',{'Host':'example.com','Range':'bytes=0-1'})[0],403)
        for path in ['/media/../server.py','/media/other.mp4','/media/warehouse-film.mp4/extra']:
            self.assertEqual(self.get(path)[0],404)
        self.assertEqual(self.session.store.list(),[]);self.assertIsNone(self.session.runtime)

if __name__=='__main__':unittest.main()
