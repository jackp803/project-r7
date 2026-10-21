"""Funding runs independently from the owner; no real provider requests."""
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from application.platform.supervision import config_hash
from tests.application import test_public_paper_feed as feed_fixture
from tests.application import test_public_paper_funding as funding_fixture

NOW=funding_fixture.NOW


class PublicFundingFeedTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.funding_feed'),
            'Ordinary Paper has no independent owned funding acquisition/health port')
        return importlib.import_module('application.paper.funding_feed')

    def configured(self):
        helper=feed_fixture.PublicPaperFeedTests(); path,config=helper.configured(); self.addCleanup(helper.doCleanups)
        capture=funding_fixture.PublicPaperFundingTests(); capture.setUp(); self.addCleanup(capture.doCleanups)
        capture.subject['config_hash']=config_hash(config)
        return path,config,capture

    def test_missing_actual_owner_refuses_before_any_child_or_capture(self):
        module=self.module(); path,config,capture=self.configured()
        with patch.object(module,'spawn_owned') as spawn:
            with self.assertRaises(ValueError): module.check_funding_once(path,capture.request,threading.Event())
        spawn.assert_not_called()
        self.assertFalse((config.local_data_root/'public-funding-observations').exists())

    def test_stalled_source_never_blocks_owner_take_and_shutdown_cancels(self):
        module=self.module(); path,config,capture=self.configured()
        entered=threading.Event(); finished=threading.Event()
        def stalled(*args):
            entered.set(); args[2].wait(3); finished.set(); raise module.FundingAttemptIncomplete(True)
        with patch.object(module,'check_funding_once',stalled), \
                module.PublicFundingFeed(config,path,capture.request,_clock=lambda:NOW) as feed:
            self.assertTrue(entered.wait(3)); began=time.monotonic()
            self.assertIsNone(feed.take()); self.assertLess(time.monotonic()-began,.1)
        self.assertTrue(finished.is_set()); self.assertEqual(feed.summary()['request_accounting'],'INCOMPLETE')
        self.assertIsNone(feed.summary()['provider_requests'])

    def test_observation_is_source_owned_and_ageing_never_advances_capture_clock(self):
        module=self.module(); path,config,capture=self.configured()
        result=capture.acquire()
        files={p.relative_to(capture.root).as_posix():p.read_bytes() for p in capture.root.rglob('*') if p.is_file()}
        def acquired(*args): return result,None,files
        now=[NOW]
        with patch.object(module,'check_funding_once',acquired),patch.object(module,'publish_health'), \
                module.PublicFundingFeed(config,path,capture.request,_clock=lambda:now[0]) as feed:
            until=time.monotonic()+3
            while feed.summary()['completed_batches']==0 and time.monotonic()<until: time.sleep(.01)
            observed=feed.take(); self.assertIsNotNone(observed)
            feed.model.require(observed); self.assertTrue(feed.summary()['healthy'])
            self.assertEqual(feed.summary()['provider_requests'],1)
            now[0]+=timedelta(seconds=61)
            self.assertFalse(feed.summary()['healthy']); self.assertEqual(observed.observed_at,NOW.isoformat().replace('+00:00','Z'))

    def test_new_config_or_invalid_selection_rejected_before_thread_or_io(self):
        module=self.module(); path,config,capture=self.configured()
        for key,value in (('config_hash','sha256:'+'5'*64),('funding_model','ZERO'),('namespace','FIXTURE')):
            request={**capture.request,'subject':{**capture.subject,key:value}}
            with self.subTest(key=key),self.assertRaises(ValueError): module.PublicFundingFeed(config,path,request)

    def test_no_funding_selection_cannot_open_a_network_feed(self):
        module=self.module(); path,config,capture=self.configured()
        with self.assertRaises(ValueError): module.PublicFundingFeed(config,path,None)

    def test_source_failure_discards_current_health_but_preserves_completed_counts(self):
        module=self.module(); path,config,capture=self.configured()
        result=capture.acquire()
        files={p.relative_to(capture.root).as_posix():p.read_bytes() for p in capture.root.rglob('*') if p.is_file()}
        done=threading.Event(); calls=[]
        def acquire(*args):
            calls.append(1)
            if len(calls)==1:return result,None,files
            done.set(); raise module.FundingAttemptIncomplete(True)
        with patch.object(module,'check_funding_once',acquire),patch.object(module,'publish_health'), \
                patch.object(module,'REFRESH_SECONDS',.01), \
                module.PublicFundingFeed(config,path,capture.request,_clock=lambda:NOW) as feed:
            self.assertTrue(done.wait(3))
            self.assertFalse(feed.summary()['healthy'])
            self.assertEqual(feed.summary()['completed_batch_requests'],1)
            self.assertIsNone(feed.summary()['provider_requests'])
            self.assertIsNone(feed.current(),'A failed source cannot keep serving the previous current observation')

    def health_document(self):
        from tests.application import test_native_paper_release_observation as native_fixture
        from application.datasets.catalog import canonical,digest
        from application.platform.private_files import create_private_directory,write_private_new
        from storage.paper_selection import OperationalSelection
        helper=native_fixture.NativePaperObservationTests();helper.setUp();self.addCleanup(helper.doCleanups)
        selection,_,identity=helper.subject(); record=selection.as_dict()
        record['owner']['simulation_policy'].update(schema_version='r7-paper-simulation-policy-v0.5',
            funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1')
        selection=OperationalSelection(1,selection.config_hash,canonical(record))
        request=dict(schema_version='r7-public-paper-funding-request-v0.1',subject=dict(namespace='LOCAL_RESEARCH',
            runtime_token=identity['process_generation_id'],config_hash=config_hash(helper.config),
            selection_hash=digest(selection.canonical_json.encode()),funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1'),
            coverage_start='2026-10-21T00:00:00Z')
        document=dict(schema_version='r7-public-paper-funding-health-v0.1',subject=request['subject'],runtime=identity,
            selection_generation=selection.generation,state='PUBLIC_FUNDING_ACQUIRED',reason_code=None,
            snapshot_hash='a'*64,observed_at='2026-10-21T08:01:00Z',complete_through='2026-10-21T08:00:00Z',
            coverage_start=request['coverage_start'],event_count=2,
            archive_capture=dict(pack='000001.pack',offset=10,size=100,sha256='sha256:'+'b'*64),
            provider_requests=1,provider_responses=1)
        folder=helper.data/'public-funding-observations';create_private_directory(folder)
        folder=folder/identity['process_generation_id'];create_private_directory(folder)
        path=folder/'current.json';write_private_new(path,canonical(document).encode())
        return helper.config,selection,identity,document,path

    def test_current_health_is_read_only_fresh_bound_to_both_actual_owner_reads(self):
        from types import SimpleNamespace
        module=self.module(); config,selection,identity,document,path=self.health_document()
        before=path.read_bytes(); snapshot=SimpleNamespace(identity=identity)
        with patch.object(module,'read_runtime_identity',return_value=snapshot),patch.object(module,'spawn_owned') as spawn:
            self.assertTrue(module.current_funding_health(config,selection,identity,now=NOW)['healthy'])
            self.assertFalse(module.current_funding_health(config,selection,identity,now=NOW+timedelta(seconds=61))['healthy'])
            self.assertFalse(module.current_funding_health(config,selection,identity,now=NOW-timedelta(seconds=1))['healthy'])
        spawn.assert_not_called(); self.assertEqual(path.read_bytes(),before)
        with patch.object(module,'read_runtime_identity',side_effect=[snapshot,SimpleNamespace(identity={**identity,'generation':3})]),self.assertRaises(ValueError):
            module.current_funding_health(config,selection,identity,now=NOW)

    def test_malformed_positive_projection_cannot_establish_funding_health(self):
        from types import SimpleNamespace
        from application.datasets.catalog import canonical
        module=self.module(); config,selection,identity,document,path=self.health_document()
        for changes in ({'snapshot_hash':'caller-PASS'},{'archive_capture':{}},{'event_count':True},
                {'event_count':1001},{'event_count':3},{'provider_requests':0},{'provider_responses':0},
                {'reason_code':'SOURCE_INVALID'},{'subject':{**document['subject'],'namespace':'FIXTURE'}}):
            path.write_bytes(canonical({**document,**changes}).encode())
            with self.subTest(changes=changes),patch.object(module,'read_runtime_identity',return_value=SimpleNamespace(identity=identity)):
                try: healthy=module.current_funding_health(config,selection,identity,now=NOW)['healthy']
                except ValueError:healthy=False
                self.assertFalse(healthy)


if __name__=='__main__': unittest.main()
