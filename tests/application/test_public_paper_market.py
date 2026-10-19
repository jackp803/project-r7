"""Offline public market composition boundaries; no real provider requests."""
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError
import io,json,threading
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application import cli
from application.config import load_config
from application.datasets.catalog import canonical
from application.platform.scope_lock import ProcessScopeLock,ScopeBusy,operational_lock_root
from tests.application.paper_owner_fixtures import PaperOwnerFixture

def profile():return dict(schema_version='r7-public-market-v0.2',namespace='LOCAL_RESEARCH',provider='OKX_PUBLIC',
    symbol='BTC_USDT_PERP',source_kind='PUBLIC_MARKET',read_only=True,workflow_authorized=True,poll_interval_seconds=1)

class PublicPaperMarketTests(unittest.TestCase):
    def module(self):
        import importlib
        return importlib.import_module('application.paper.public_market')

    def test_closed_public_profile_rejects_keys_private_sources_and_implicit_consent(self):
        module=self.module();self.assertEqual(module.validate_profile(profile()),profile())
        for change in (dict(api_key='forbidden'),dict(provider='PRIVATE'),dict(symbol='ETH_USDT_PERP'),dict(namespace='FIXTURE'),
                       dict(read_only=False),dict(workflow_authorized=False),dict(poll_interval_seconds=True),dict(poll_interval_seconds=0)):
            with self.subTest(change=change),self.assertRaises(ValueError):module.validate_profile(dict(profile(),**change))

    def configured(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        config_path=root/'config.json';selection=root/'explicit-market.json';selection.write_text(canonical(profile()),encoding='utf-8')
        with redirect_stdout(io.StringIO()):
            cli.main(['init-profile','--config',str(config_path),'--data-root',str(root/'data'),'--instance-id','public-paper-market-source'])
        return config_path,load_config(config_path),selection

    def test_normal_stopped_owner_setup_is_idempotent_no_database_no_network(self):
        module=self.module();config_path,config,selection=self.configured()
        with redirect_stdout(io.StringIO()) as output:
            code=cli.main(['configure-market-data','--config',str(config_path),'--selection-profile',str(selection)])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['status'],'PUBLIC_MARKET_CONFIGURED')
        self.assertFalse(config.database_path.exists())
        self.assertEqual(module.configure_market_data(config_path,selection)['status'],'ALREADY_CONFIGURED')
        self.assertEqual(module.load_market_profile(config),profile())

    def test_active_coordinator_and_cloud_borne_profile_cannot_change_public_selection(self):
        module=self.module();config_path,config,selection=self.configured()
        with ProcessScopeLock('coordinator:'+config.product_instance_id,lock_root=operational_lock_root(config)),self.assertRaises(ScopeBusy):
            module.configure_market_data(config_path,selection)
        self.assertFalse((config.local_data_root/module.SELECTION_FILE).exists())

    def test_initialized_private_data_is_preserved_during_normal_market_setup(self):
        module=self.module();config_path,config,selection=self.configured()
        from application.platform.private_files import create_private_directory
        create_private_directory(config.local_data_root)
        marker=config.local_data_root/'existing-research.marker';marker.write_bytes(b'preserve')
        self.assertEqual(module.configure_market_data(config_path,selection)['status'],'PUBLIC_MARKET_CONFIGURED')
        self.assertEqual(marker.read_bytes(),b'preserve')

    def test_changed_config_at_scope_handoff_cannot_publish_to_stale_root(self):
        from contextlib import contextmanager
        from unittest.mock import patch
        module=self.module();config_path,config,selection=self.configured();changed=False
        @contextmanager
        def handoff(*args,**kwargs):
            nonlocal changed
            with ProcessScopeLock(*args,**kwargs):
                if not changed:
                    value=json.loads(config_path.read_bytes());value['product_instance_id']='changed-instance'
                    config_path.write_text(canonical(value),encoding='utf-8');changed=True
                yield
        with patch.object(module,'ProcessScopeLock',handoff),self.assertRaises(ValueError):module.configure_market_data(config_path,selection)
        self.assertFalse((config.local_data_root/module.SELECTION_FILE).exists())

    def test_fenced_attached_e6_owner_cannot_export_successor_generation(self):
        from application.paper.worker import PaperOwnerWorker
        fixture=PaperOwnerFixture(self);run=fixture.start()
        with PaperOwnerWorker(fixture.config,fixture.factory,namespace='FIXTURE') as worker:
            worker.tick();before=fixture.recover(run)
            worker.service.process.begin_process(run,'actual-successor-owner',expected_generation=before.process_generation,now=fixture.h.clock[0])
            self.assertEqual(worker.market_subscriptions(),())

    def test_actual_owner_exports_immutable_both_generation_fences_without_promoting_fixture(self):
        from application.paper.worker import PaperOwnerWorker,PaperWorkerError
        fixture=PaperOwnerFixture(self);run=fixture.start()
        with PaperOwnerWorker(fixture.config,fixture.factory,namespace='FIXTURE') as worker:
            worker.tick();descriptors=worker.market_subscriptions()
            self.assertEqual(len(descriptors),1);descriptor=descriptors[0]
            self.assertEqual(descriptor.run_id,run);self.assertEqual(descriptor.namespace,'FIXTURE')
            self.assertEqual(descriptor.runtime_token,worker.supervisor.identity['process_generation_id'])
            self.assertEqual(descriptor.e6_generation,fixture.recover(run).process_generation)
            with self.assertRaises(FrozenInstanceError):descriptor.run_id='another'
            errors=[]
            def foreign():
                try:worker.market_subscriptions()
                except PaperWorkerError as error:errors.append(str(error))
            thread=threading.Thread(target=foreign);thread.start();thread.join(timeout=5)
            self.assertEqual(errors,['PAPER_OWNER_THREAD_REQUIRED'])
