"""Local cooperative requests target one observed process incarnation only."""
import importlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import time
from types import SimpleNamespace

from application.config import ProductConfig
from application.platform.shutdown import ManagedStop
from application.platform.supervision import ProcessSupervisor,process_health


class ManagedProductStopTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='r7-managed-stop-');self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.config=ProductConfig(schema_version='r7-product-config-v0.2',cloud_root=None,local_data_root=root/'data',database_path=root/'data/canonical.sqlite3',
            product_instance_id='managed-stop-fixture',execution_mode='FIXTURE')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.platform.service_stop'))
        return importlib.import_module('application.platform.service_stop')

    def test_request_never_starts_or_allocates_and_owning_loop_observes_exact_incarnation(self):
        m=self.module();root=self.config.local_data_root
        self.assertEqual(m.request_service_stop(self.config,'runtime')['status'],'NO_CURRENT_PROCESS')
        self.assertFalse(root.exists())
        with ProcessSupervisor(self.config,'runtime') as supervisor:
            stop=ManagedStop()
            self.assertFalse(m.observe_service_stop(supervisor,stop));self.assertFalse(stop.requested)
            result=m.request_service_stop(self.config,'runtime')
            self.assertEqual(result['status'],'COOPERATIVE_STOP_REQUESTED')
            self.assertEqual(result['generation'],supervisor.identity['generation'])
            self.assertTrue(m.observe_service_stop(supervisor,stop));self.assertTrue(stop.requested)
            self.assertEqual(m.request_service_stop(self.config,'runtime'),result)
        with ProcessSupervisor(self.config,'runtime') as successor:
            stop=ManagedStop();self.assertFalse(m.observe_service_stop(successor,stop));self.assertFalse(stop.requested)
        self.assertEqual(process_health(self.config,'runtime')['state'],'STOPPED')

    def test_foreign_or_malformed_request_never_clears_pause_or_claims_flat(self):
        m=self.module()
        with ProcessSupervisor(self.config,'control') as supervisor:
            m.request_service_stop(self.config,'control')
            path=m._request_path(self.config,supervisor.identity['process_generation_id'])
            path.write_text('{}',encoding='utf-8')
            with self.assertRaises(ValueError):m.observe_service_stop(supervisor,ManagedStop())
        with self.assertRaises(ValueError):m.request_service_stop(self.config,'arbitrary-pid')

    def test_control_observer_fencing_requests_exit_and_surfaces_failure(self):
        from application.entrypoints import serve
        from application.platform.supervision import SupervisionError
        servers=[]
        class Server:
            def __init__(self, config):
                self.should_exit=False;self.started=True;servers.append(self)
            def run(self):
                deadline=time.monotonic()+1.5
                while not self.should_exit and time.monotonic()<deadline:time.sleep(.01)
        # Real supervisor and PID; only the race at the second fence is injected.
        def fenced_observation(supervisor, stop):
            raise SupervisionError('TEST_SECOND_FENCE_CHANGED')
        with patch('application.entrypoints.create_local_app',return_value=SimpleNamespace(state=SimpleNamespace())), \
                patch('uvicorn.Server',Server), \
                patch('application.platform.service_stop.observe_service_stop',side_effect=fenced_observation):
            with self.assertRaisesRegex(SupervisionError,'TEST_SECOND_FENCE_CHANGED'):
                serve(self.config)
        self.assertTrue(servers[0].should_exit)


if __name__=='__main__':unittest.main()
