"""Local controlled public-endpoint facts; no SSH connection or owner stores."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,threading,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
from application.platform.ssh_access import plan_ssh_tunnel,probe_loopback_auth_status

PUBLIC=dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')

@contextmanager
def endpoint(*,body=None,status=200,headers=None,delay=0):
    observations=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            observations.append(dict(path=self.path,headers=dict(self.headers)))
            if delay:time.sleep(delay)
            try:
                self.send_response(status)
                for key,value in (headers or {'Content-Type':'application/json'}).items():self.send_header(key,value)
                self.end_headers();self.wfile.write(json.dumps(PUBLIC).encode() if body is None else body)
            except OSError:pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield server.server_port,observations
    finally:server.shutdown();server.server_close();thread.join(2)

class SSHAccessTests(unittest.TestCase):
    def test_exact_loopback_forward_has_no_remote_command_or_connection(self):
        with patch('subprocess.Popen',side_effect=AssertionError('Planner must not execute')):
            plan=plan_ssh_tunnel('r7.example.test','operator',api_port=8765,ssh_port=22)
        self.assertEqual(plan['argv'],['ssh','-N','-T','-a','-F','none','-o','ExitOnForwardFailure=yes',
            '-o','GatewayPorts=no','-o','StrictHostKeyChecking=yes','-p','22','-l','operator',
            '-L','127.0.0.1:8765:127.0.0.1:8765','r7.example.test'])
        self.assertEqual(plan['status'],'PLANNED_ONLY')
        self.assertEqual(plan['browser_url'],'http://127.0.0.1:8765/')
        self.assertEqual(plan['ssh_connection'],'NOT_STARTED')
        self.assertEqual(plan['credentials'],'NOT_READ')

    def test_deterministic_plan_binds_destination_and_exact_port(self):
        first=plan_ssh_tunnel('r7.example.test','operator')
        self.assertEqual(first,plan_ssh_tunnel('r7.example.test','operator'))
        self.assertNotEqual(first['plan_hash'],plan_ssh_tunnel('r7.example.test','operator',api_port=8766)['plan_hash'])
        self.assertNotEqual(first['plan_hash'],plan_ssh_tunnel('r8.example.test','operator')['plan_hash'])
        self.assertEqual(first['host_origin_boundary'],'SAME_LOCAL_AND_REMOTE_API_PORT_REQUIRED')

    def test_literal_ipv4_and_ipv6_ssh_destinations_are_supported(self):
        for host in ('192.0.2.10','2001:db8::7'):
            with self.subTest(host=host):self.assertEqual(plan_ssh_tunnel(host,'operator')['argv'][-1],host)

    def test_host_injection_url_ambiguous_names_and_credential_references_are_denied(self):
        for host in ('-oProxyCommand=evil','host;evil','user@host','https://host','host\nBad','a b','[2001:db8::7]',
                     'host:22','host.','-host','a..b','主機','a'*64+'.test','01.02.03.04','999.1.2.3'):
            with self.subTest(host=host),self.assertRaises(ValueError):plan_ssh_tunnel(host,'operator')

    def test_invalid_username_and_ports_are_denied(self):
        for username in ('root','-user','user@host','user name','user\n','a'*33,'主體'):
            with self.subTest(username=username),self.assertRaises(ValueError):plan_ssh_tunnel('host.test',username)
        for value in (True,0,1023,65536,'8765'):
            with self.subTest(port=value),self.assertRaises(ValueError):plan_ssh_tunnel('host.test','operator',api_port=value)
        for value in (True,0,65536,'22'):
            with self.subTest(ssh_port=value),self.assertRaises(ValueError):plan_ssh_tunnel('host.test','operator',ssh_port=value)

    def test_actual_public_endpoint_is_bounded_reaped_and_does_not_prove_tunnel(self):
        with endpoint() as (port,seen):result=probe_loopback_auth_status(port)
        self.assertEqual(result['status'],'PUBLIC_AUTH_STATUS_AVAILABLE')
        self.assertEqual(result['public_auth_status'],PUBLIC)
        self.assertTrue(result['tree_reaped'])
        self.assertEqual(result['tunnel_provenance'],'UNVERIFIED_LOCAL_ENDPOINT_ONLY')
        self.assertEqual(result['financial_authority'],'NONE')
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0]['path'],'/api/v1/auth/status')
        self.assertNotIn('Authorization',seen[0]['headers']);self.assertNotIn('Cookie',seen[0]['headers'])

    def test_environment_proxy_is_ignored_for_actual_loopback_probe(self):
        with patch.dict('os.environ',{'http_proxy':'http://192.0.2.99:9','HTTP_PROXY':'http://192.0.2.99:9','NO_PROXY':''}),endpoint() as (port,seen):
            result=probe_loopback_auth_status(port)
        self.assertEqual(result['status'],'PUBLIC_AUTH_STATUS_AVAILABLE');self.assertEqual(len(seen),1)

    def test_redirect_is_denied_without_contacting_destination(self):
        with endpoint(status=302,headers={'Location':'https://192.0.2.99/private'}) as (port,seen):
            result=probe_loopback_auth_status(port)
        self.assertEqual(result['status'],'UNAVAILABLE');self.assertEqual(result['reason_code'],'REDIRECT_FORBIDDEN')
        self.assertEqual(len(seen),1);self.assertTrue(result['tree_reaped'])

    def test_wrong_namespace_is_denied(self):
        with endpoint(body=json.dumps(dict(PUBLIC,namespace='FIXTURE')).encode()) as (port,seen):
            result=probe_loopback_auth_status(port)
        self.assertEqual(result['reason_code'],'PUBLIC_STATUS_INVALID')
        self.assertNotIn('public_auth_status',result)

    def test_malformed_duplicate_unknown_or_wrong_typed_json_is_denied(self):
        bodies=[b'{',b'{"configured":true,"configured":false,"namespace":"LOCAL_RESEARCH","enrollment":"LOCAL_CLI_ONLY"}',
            json.dumps(dict(PUBLIC,unexpected='must-not-echo')).encode(),json.dumps(dict(PUBLIC,configured=1)).encode(),
            json.dumps(dict(PUBLIC,enrollment='HTTP_ALLOWED')).encode()]
        for body in bodies:
            with self.subTest(body_hash=__import__('hashlib').sha256(body).hexdigest()),endpoint(body=body) as (port,seen):
                result=probe_loopback_auth_status(port)
            self.assertEqual(result['reason_code'],'PUBLIC_STATUS_INVALID');self.assertNotIn('must-not-echo',json.dumps(result))

    def test_oversized_non_json_and_server_failure_are_denied(self):
        cases=[dict(body=b'x'*2049),dict(headers={'Content-Type':'text/html'}),dict(status=503)]
        for options in cases:
            with self.subTest(options=sorted(options)),endpoint(**options) as (port,seen):result=probe_loopback_auth_status(port)
            self.assertEqual(result['status'],'UNAVAILABLE');self.assertTrue(result['tree_reaped'])

    def test_actual_slow_response_deadline_reaps_owned_child(self):
        with endpoint(delay=4) as (port,seen):
            started=time.monotonic();result=probe_loopback_auth_status(port,deadline_seconds=1)
            elapsed=time.monotonic()-started
        self.assertEqual(result['reason_code'],'PROBE_DEADLINE');self.assertTrue(result['tree_reaped']);self.assertLess(elapsed,3)

    def test_invalid_probe_facts_fail_before_child_or_socket(self):
        with patch('subprocess.Popen',side_effect=AssertionError('Invalid facts must not execute')):
            for port in (True,0,80,65536,'8765'):
                with self.subTest(port=port),self.assertRaises(ValueError):probe_loopback_auth_status(port)
            for namespace in ('LIVE','PAPER',None):
                with self.subTest(namespace=namespace),self.assertRaises(ValueError):probe_loopback_auth_status(8765,expected_namespace=namespace)
            for limit in (True,0,.5,11):
                with self.subTest(deadline=limit),self.assertRaises(ValueError):probe_loopback_auth_status(8765,deadline_seconds=limit)

    def test_failed_cleanup_returns_without_reading_an_actual_open_pipe(self):
        reader_fd,writer_fd=os.pipe()
        reader=os.fdopen(reader_fd,'rb',buffering=0);writer=os.fdopen(writer_fd,'wb',buffering=0)
        owned=SimpleNamespace(process=SimpleNamespace(stdout=reader),wait=lambda:0,
            termination_report=SimpleNamespace(reaped=False,reason='CLEANUP_FAILED'))
        done=threading.Event();results=[]
        def run():
            try:results.append(probe_loopback_auth_status(8765))
            finally:done.set()
        try:
            with patch('application.platform.ssh_access.spawn_owned',return_value=owned):
                thread=threading.Thread(target=run,daemon=True);thread.start()
                self.assertTrue(done.wait(.3),'Failed cleanup must return before pipe EOF')
                self.assertEqual(results[0]['reason_code'],'PROBE_CLEANUP_FAILED')
                self.assertTrue(reader.closed)
        finally:
            writer.close();thread.join(2);reader.close()
        self.assertFalse(thread.is_alive())

    def test_deadline_disposition_is_checked_before_reading_stdout(self):
        stream=SimpleNamespace(read=lambda *args:(_ for _ in ()).throw(AssertionError('Timed-out reply must not be read')),close=lambda:None)
        owned=SimpleNamespace(process=SimpleNamespace(stdout=stream),wait=lambda:124,
            termination_report=SimpleNamespace(reaped=True,reason='TIMEOUT'))
        with patch('application.platform.ssh_access.spawn_owned',return_value=owned):result=probe_loopback_auth_status(8765)
        self.assertEqual(result['reason_code'],'PROBE_DEADLINE')

if __name__=='__main__':unittest.main()
