from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import ast,importlib,json,os,sqlite3,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler,build_opener
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.entrypoints import initialize_profile
from application.platform.processes import ResourceLimits,spawn_owned
PUBLIC=dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')
@contextmanager
def endpoint(location=None):
    hits=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path);self.send_response(302 if location else 200)
            self.send_header('Location',location) if location else self.send_header('Content-Type','application/json')
            self.end_headers();self.wfile.write(b'' if location else json.dumps(PUBLIC).encode())
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield server.server_port,hits
    finally:server.shutdown();server.server_close();thread.join(2)

class NativeAccessHarnessTests(unittest.TestCase):
    def collision(self,port):
        temp=tempfile.TemporaryDirectory(prefix='S13-native-harness-collision-',dir=base);self.addCleanup(temp.cleanup)
        root=Path(temp.name);config=root/'product.json'
        initialize_profile(config,root/'data',instance_id='native-harness-collision',port=port)
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
        log=root/'collision.log'
        with log.open('xb') as stream:
            owner=spawn_owned([sys.executable,str(repo/'packaging/entrypoint.py'),'serve','--config',str(config)],cwd=root,
                limits=ResourceLimits(20),stdout=stream,stderr=-2,env=env)
            code=owner.wait(timeout=15)
        self.assertEqual(code,3)
        text=log.read_text(encoding='utf-8').lower()
        self.assertTrue('10048' in text or 'address already in use' in text,'Actual occupied-port bind failure required')
        self.assertTrue(owner.termination_report.reaped)
        return owner,config

    def test_original_readiness_opener_follows_actual_controlled_redirect(self):
        tree=ast.parse((base/'s13_native_ssh_probe_reviewed_v1.py').read_text(encoding='utf-8'))
        original=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='opener' for t in n.targets))
        self.assertIsInstance(original,ast.Call);self.assertEqual(original.func.id,'build_opener')
        opener=eval(compile(ast.Expression(original),'original-readiness-opener-only','eval'),dict(build_opener=build_opener,ProxyHandler=ProxyHandler))
        with endpoint() as (destination,hits),endpoint(f'http://127.0.0.1:{destination}/redirected') as (port,_):
            with opener.open(f'http://127.0.0.1:{port}/api/v1/auth/status',timeout=2) as response:self.assertEqual(response.status,200)
        self.assertEqual(hits,['/redirected'])

    def test_guarded_readiness_denies_redirect_without_contacting_controlled_destination(self):
        guard=importlib.import_module('s13_native_access_integrity')
        with endpoint() as (destination,hits),endpoint(f'http://127.0.0.1:{destination}/must-not-contact') as (port,_):
            with self.assertRaises(HTTPError) as error:guard.build_loopback_opener().open(f'http://127.0.0.1:{port}/api/v1/auth/status',timeout=2)
            self.assertEqual(error.exception.code,302);error.exception.close()
        self.assertEqual(hits,[])

    def test_original_success_and_cleanup_can_accept_actual_exited_port_collision(self):
        with endpoint() as (port,_):
            owner,config=self.collision(port)
            with build_opener(ProxyHandler({})).open(f'http://127.0.0.1:{port}/api/v1/auth/status',timeout=2) as response:
                success=json.loads(response.read())==PUBLIC
            tree=ast.parse((base/'s13_native_ssh_probe_reviewed_v1.py').read_text(encoding='utf-8'))
            test=next(n for n in ast.walk(tree) if isinstance(n,ast.BoolOp) and ast.unparse(n)=='success and termination.reaped')
            self.assertTrue(eval(compile(ast.Expression(test),'original-owner-pass-expression-only','eval'),
                dict(success=success,termination=owner.termination_report)))
            self.assertEqual(owner.process.poll(),3)

    def test_actual_exited_owner_with_matching_controlled_endpoint_is_denied(self):
        guard=importlib.import_module('s13_native_access_integrity')
        with endpoint() as (port,_):
            owner,config=self.collision(port)
            with self.assertRaises(ValueError):guard.require_owned_generation(owner,config,dict(executable_revision='a'*40,build_hash='sha256:'+'b'*64))

if __name__=='__main__':unittest.main()
