"""Owned feed lifecycle without real network or financial selection."""
from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import datetime,timezone
import io,json,threading,time,unittest,uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from application import cli
from application.config import load_config
from application.datasets.catalog import canonical
from tests.application.test_public_paper_market import profile
from tests.application import test_public_paper_acquisition as fixture

class PublicPaperFeedTests(unittest.TestCase):
    def module(self):
        import importlib
        return importlib.import_module('application.paper.public_feed')
    def configured(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        config=root/'config.json';selection=root/'market.json';selection.write_text(canonical(profile()),encoding='utf-8')
        with redirect_stdout(io.StringIO()):
            cli.main(['init-profile','--config',str(config),'--data-root',str(root/'data'),'--instance-id','public-feed','--enable-paper-runtime'])
            cli.main(['configure-market-data','--config',str(config),'--selection-profile',str(selection)])
        return config,load_config(config)
    def test_missing_actual_runtime_refuses_before_spawn_or_public_io(self):
        module=self.module();config_path,config=self.configured()
        helper=fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with self.assertRaises(ValueError):
            module.check_batch_once(config_path,helper.subscription.runtime_token,(helper.subscription,),threading.Event())
        self.assertFalse((config.local_data_root/'public-market-observations').exists())

    def test_actual_fixed_child_rejects_fixture_request_before_network_and_is_reaped(self):
        module=self.module();config_path,config=self.configured()
        from application.platform.supervision import ProcessSupervisor,config_hash
        from application.platform.private_files import create_private_directory
        from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
        from application.datasets.catalog import digest
        from dataclasses import replace
        import subprocess,sys,os
        helper=fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups)
        with ProcessSupervisor(config,'runtime',config_path=config_path) as supervisor:
            token=supervisor.identity['process_generation_id'];attempt=str(uuid.uuid4())
            module._guard(config_path,token)
            root=config.local_data_root/module.ROOT
            for folder in (root,root/token,root/token/attempt):create_private_directory(folder)
            raw=canonical([asdict(replace(helper.subscription,runtime_token=token,namespace='FIXTURE'))]).encode()
            (root/token/attempt/'request.json').write_bytes(raw)
            argv=[sys.executable,'-m','application','_paper-market-acquire','--config',str(config_path),
                '--runtime-token',token,'--attempt-id',attempt,'--request-hash',digest(raw),
                '--expected-config-hash',config_hash(config),'--selection-hash',digest(canonical(profile()).encode())]
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
            owned=spawn_owned(argv,cwd=config_path.parent,limits=ResourceLimits(10),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
            try:
                self.assertEqual(owned.wait(timeout=12),2);output=owned.process.stdout.read(65536)
                self.assertTrue(owned.termination_report.reaped);self.assertNotIn(b'Traceback',output)
                self.assertFalse((root/token/attempt/'capture').exists())
            finally:
                self.assertTrue(terminate_owned(owned,deadline_seconds=3).reaped);owned.process.stdout.close()
    def test_background_stall_does_not_block_owner_poll_and_stop_cancels_outside_owner_thread(self):
        module=self.module();config_path,config=self.configured();entered=threading.Event();finished=threading.Event()
        helper=fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups)
        def pending(*args):
            entered.set();args[-1].wait(3);finished.set();raise module.MarketAttemptIncomplete(True)
        with patch.object(module,'check_batch_once',pending),module.PublicMarketFeed(config,config_path,helper.subscription.runtime_token) as feed:
            feed.update((helper.subscription,));self.assertTrue(entered.wait(3))
            start=time.monotonic();self.assertIsNone(feed.take());self.assertLess(time.monotonic()-start,.1)
        self.assertTrue(finished.is_set());self.assertIsNone(feed.summary()['provider_requests'])
        self.assertEqual(feed.summary()['request_accounting'],'INCOMPLETE')
    def test_completed_actual_counts_preserved_and_new_result_never_held_as_current_health(self):
        module=self.module();config_path,config=self.configured();done=threading.Event()
        helper=fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups);result=helper.acquire()
        def acquired(*args):done.set();return result
        with patch.object(module,'check_batch_once',acquired),module.PublicMarketFeed(config,config_path,helper.subscription.runtime_token) as feed:
            feed.update((helper.subscription,));self.assertTrue(done.wait(3))
            deadline=time.monotonic()+3
            while feed.summary()['completed_batches']==0 and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(feed.take(),result);self.assertIsNone(feed.take())
            self.assertEqual(feed.summary()['provider_requests'],2);self.assertEqual(feed.summary()['provider_responses'],2)
    def test_empty_owner_subscription_never_starts_network_child(self):
        module=self.module();config_path,config=self.configured()
        with patch.object(module,'check_batch_once') as request,module.PublicMarketFeed(config,config_path,str(uuid.uuid4())) as feed:
            feed.update(());time.sleep(.1)
        request.assert_not_called();self.assertEqual(feed.summary()['provider_requests'],0)

    def test_raised_cleanup_retains_actual_owned_handle_closes_pipe_and_stops_successors(self):
        module=self.module();config_path,config=self.configured()
        helper=fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups)
        from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
        import subprocess,sys
        owned=spawn_owned([sys.executable,'-c','import time; time.sleep(60)'],cwd=config_path.parent,limits=ResourceLimits(65),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        cancel=threading.Event();timer=threading.Timer(.2,cancel.set);timer.start()
        try:
            with patch.object(module,'_guard',return_value=(config,profile())),patch.object(module,'spawn_owned',return_value=owned),\
                    patch.object(module,'terminate_owned',side_effect=OSError('controlled cleanup fault')):
                with self.assertRaises(module.MarketAttemptIncomplete) as caught:
                    module.check_batch_once(config_path,helper.subscription.runtime_token,(helper.subscription,),cancel)
            self.assertFalse(caught.exception.reaped);self.assertTrue(owned.process.stdout.closed)
            self.assertIn(owned,module._unreaped)
        finally:
            timer.cancel();self.assertTrue(terminate_owned(owned,deadline_seconds=3).reaped)
            if owned in module._unreaped:module._unreaped.remove(owned)
