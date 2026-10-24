"""Offline fixed public quotes may protect exposure, never authorize entry."""
from dataclasses import asdict,replace
from datetime import timedelta
from copy import deepcopy
import threading,time,unittest,uuid
from unittest.mock import patch

from application.paper import public_acquisition as acquisition
from application.paper import public_feed as feed_module
from application.paper import public_market
from application.paper.capture_archive import PublicCaptureArchive,ROOT
from brokers.paper import PaperBroker
from tests.application import test_public_paper_acquisition as public_fixture
from tests.application import test_public_paper_feed as feed_fixture
from tests.application.test_public_paper_market import profile
from tests.product import test_paper_encoded_checkpoint_consumers as encoded


class ExposureOnlyMarketTests(unittest.TestCase):
    def public(self):
        helper=public_fixture.PublicPaperAcquisitionTests();helper.setUp();self.addCleanup(helper.doCleanups)
        helper.subscription=replace(helper.subscription,exposure_open=True)
        return helper

    def test_fixed_ticker_only_capture_has_one_actual_count_and_no_history_or_entry_scope(self):
        h=self.public();calls=[]
        def opener(request,**kwargs):calls.append(request.full_url);return h.opener(request,**kwargs)
        result=acquisition.acquire_batch(h.root,(h.subscription,),_opener=opener,
            _clock=lambda:public_fixture.NOW,_minimum_interval=0,_exposure_only=True)
        self.assertEqual(result['provider_requests'],1);self.assertEqual(result['provider_responses'],1)
        self.assertTrue(result['management_only']);self.assertEqual(result['candles'],{})
        self.assertEqual(len(calls),1);self.assertIn('/market/ticker?',calls[0])
        event=acquisition.event_for(h.subscription,result,now=public_fixture.NOW)
        self.assertTrue(event.management_only);self.assertEqual(event.candles,())
        self.assertIsNone(acquisition.event_for(replace(h.subscription,exposure_open=False),result,now=public_fixture.NOW))
        self.assertIsNone(acquisition.event_for(replace(h.subscription,exposure_open='yes'),result,now=public_fixture.NOW))
        injected=deepcopy(result);injected['candles']={'4h':[]}
        with self.assertRaises(ValueError):acquisition.event_for(h.subscription,injected,now=public_fixture.NOW)

    def test_no_exposure_or_nonboolean_scope_cannot_dispatch_quote_reserve(self):
        h=self.public()
        with patch.object(acquisition.PaperPublicTransport,'get') as get:
            for rows,scope in (((replace(h.subscription,exposure_open=False),),True),((h.subscription,),1)):
                with self.subTest(scope=scope),self.assertRaises(ValueError):
                    acquisition.acquire_batch(h.root,rows,_exposure_only=scope)
        get.assert_not_called()

    def test_only_actual_owner_exposure_is_exported_and_pending_flat_does_not_spend_reserve(self):
        case=encoded.EncodedRecordedFundingRegressionTests();self.addCleanup(case.doCleanups)
        case.prepare(instance_id='exposure-subscription-regression')
        token=case.supervisor.identity['process_generation_id']
        descriptor=lambda:public_market.subscription(case.runtime,'LOCAL_RESEARCH',token)
        self.assertFalse(descriptor().exposure_open)
        case.runtime.on_market_event(case.event(0,bars=True));case.runtime.on_market_event(case.event(1))
        self.assertTrue(descriptor().exposure_open)
        case.runtime.on_market_event(case.event(2,price='60020'));case.runtime.on_market_event(case.event(3,price='60020'))
        self.assertIsNotNone(case.service.process.management_snapshot(case.ref.run_id).state['runtime']['pending_funding'])
        self.assertFalse(descriptor().exposure_open)

    def test_management_quote_and_later_deadline_cannot_first_fill_actual_entry_ack(self):
        case=encoded.EncodedRecordedFundingRegressionTests();self.addCleanup(case.doCleanups)
        case.prepare(instance_id='exposure-first-fill-regression')
        self.assertEqual(case.runtime.on_market_event(case.event(0,bars=True)).status,'ACKNOWLEDGED')
        outcome=case.runtime.on_market_event(replace(case.event(1),management_only=True))
        state=case.service.process.management_snapshot(case.ref.run_id).state
        self.assertIn('PUBLIC_MARKET_MANAGEMENT_ONLY',outcome.reason_codes)
        self.assertEqual(PaperBroker.from_state(state['broker']).query_position('BTC_USDT_PERP').net_quantity,0)
        case.runtime.on_deadline(case.clock[0])
        state=case.service.process.management_snapshot(case.ref.run_id).state
        self.assertEqual(PaperBroker.from_state(state['broker']).query_position('BTC_USDT_PERP').net_quantity,0)
        self.assertFalse(state['runtime']['forward']['last_healthy'])
        case.runtime.on_market_event(case.event(2))
        state=case.service.process.management_snapshot(case.ref.run_id).state
        self.assertNotIn('market_management_only',state['runtime'])

    def test_management_quote_still_triggers_original_protective_exit_and_retains_pending_funding(self):
        case=encoded.EncodedRecordedFundingRegressionTests();self.addCleanup(case.doCleanups)
        case.prepare(instance_id='exposure-protective-exit-regression')
        case.runtime.on_market_event(case.event(0,bars=True));case.runtime.on_market_event(case.event(1))
        self.assertEqual(case.runtime.on_market_event(replace(case.event(2,price='60020'),management_only=True)).status,'EXIT_REQUESTED')
        self.assertEqual(case.runtime.on_market_event(replace(case.event(3,price='60020'),management_only=True)).status,'FUNDING_PENDING')
        state=case.service.process.management_snapshot(case.ref.run_id).state
        self.assertIsNotNone(state['runtime']['pending_funding']);self.assertEqual(state['runtime']['closed_trades'],[])
        self.assertEqual(PaperBroker.from_state(state['broker']).query_position('BTC_USDT_PERP').net_quantity,0)
        self.assertFalse(state['runtime']['forward']['last_healthy'])
        successor=case.enterContext(case.selected.owners.service());runtime=successor.runtime(case.ref.run_id)
        recovered=successor.process.management_snapshot(case.ref.run_id)
        self.assertTrue(recovered.state['runtime']['market_management_only'])
        self.assertFalse(successor.history_ready(case.ref.run_id))
        from tests.product.test_paper_recorded_funding import floor
        case.clock[0]=floor(case.initial)+timedelta(hours=8,seconds=1);case.observe(case.clock[0])
        runtime.on_deadline(case.clock[0])
        finalized=successor.process.management_snapshot(case.ref.run_id).state['runtime']
        self.assertIsNone(finalized['pending_funding']);self.assertEqual(len(finalized['closed_trades']),1)
        self.assertFalse(finalized['forward']['last_healthy'])

    def test_normal_capacity_refusal_uses_finite_reserve_only_for_exposed_subscriptions(self):
        h=self.public();fixture=feed_fixture.PublicPaperFeedTests();self.addCleanup(fixture.doCleanups)
        config_path,config=fixture.configured()
        from application.paper import capture_archive
        with patch.object(feed_module,'_guard',return_value=(config,profile())),\
                patch.object(capture_archive,'MAX_TOTAL_BYTES',16*1024**2),\
                patch.object(feed_module,'spawn_owned',side_effect=OSError('controlled pre-IO refusal')) as spawn,\
                patch.object(PublicCaptureArchive,'reserve',autospec=True,side_effect=PublicCaptureArchive.reserve) as reserve:
            with self.assertRaises(feed_module.MarketAttemptIncomplete):
                feed_module.check_batch_once(config_path,h.subscription.runtime_token,(h.subscription,),threading.Event())
        self.assertEqual(reserve.call_count,2)
        self.assertTrue(reserve.call_args.kwargs['emergency']);self.assertEqual(reserve.call_args.kwargs['maximum_requests'],1)
        self.assertIn('--exposure-only',spawn.call_args.args[0])
        summary=PublicCaptureArchive(config.local_data_root/ROOT).summary()
        self.assertEqual(summary['request_accounting'],'INCOMPLETE');self.assertIsNone(summary['provider_requests'])

    def test_exhausted_reserve_or_corrupt_committed_head_never_dispatches_or_resets_counts(self):
        h=self.public();fixture=feed_fixture.PublicPaperFeedTests();self.addCleanup(fixture.doCleanups)
        config_path,config=fixture.configured()
        from application.paper import capture_archive
        with patch.object(feed_module,'_guard',return_value=(config,profile())),\
                patch.object(capture_archive,'MAX_TOTAL_BYTES',1024**2),patch.object(feed_module,'spawn_owned') as spawn:
            with self.assertRaisesRegex(ValueError,'CAPACITY'):
                feed_module.check_batch_once(config_path,h.subscription.runtime_token,(h.subscription,),threading.Event())
        spawn.assert_not_called()

        archive=PublicCaptureArchive(config.local_data_root/ROOT)
        self.assertEqual(archive.summary()['provider_requests'],0)
        (config.local_data_root/ROOT/'head.json').write_bytes(b'{}')
        with patch.object(feed_module,'_guard',return_value=(config,profile())),patch.object(feed_module,'spawn_owned') as spawn:
            with self.assertRaises(ValueError):
                feed_module.check_batch_once(config_path,h.subscription.runtime_token,(h.subscription,),threading.Event())
        spawn.assert_not_called()

    def test_fresh_feed_discloses_persistent_unknown_archive_counts_separately_from_current_batch(self):
        h=self.public();fixture=feed_fixture.PublicPaperFeedTests();self.addCleanup(fixture.doCleanups)
        config_path,config=fixture.configured();archive=feed_module._archive_for(config);capture=str(uuid.uuid4())
        archive.reserve(capture,kind='market',maximum_requests=1,maximum_bytes=65536,maximum_files=1)
        archive.commit(capture,{'interrupted.json':b'{}'},requests=0,responses=0,complete=False)
        result=acquisition.acquire_batch(h.root,(h.subscription,),_opener=h.opener,_clock=lambda:public_fixture.NOW,
            _minimum_interval=0,_exposure_only=True)
        with patch.object(feed_module,'check_batch_once',return_value=result),\
                feed_module.PublicMarketFeed(config,config_path,h.subscription.runtime_token) as feed:
            feed.update((h.subscription,));deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                summary=feed.summary()
                if summary.get('cumulative_capture_accounting')=='INCOMPLETE':break
                time.sleep(.01)
            self.assertEqual(summary['request_count_scope'],'THIS_FEED_INSTANCE')
            self.assertEqual(summary['provider_requests'],1)
            self.assertEqual(summary['cumulative_capture_accounting'],'INCOMPLETE')
            self.assertIsNone(summary['cumulative_provider_requests'])
            self.assertEqual(summary['cumulative_request_budget_upper'],1)

    def test_post_dispatch_capture_persistence_failure_keeps_unknown_accounting_signal(self):
        h=self.public();fixture=feed_fixture.PublicPaperFeedTests();self.addCleanup(fixture.doCleanups)
        config_path,config=fixture.configured()
        from application.paper import capture_archive
        with patch.object(feed_module,'_guard',return_value=(config,profile())),\
                patch.object(capture_archive,'MAX_TOTAL_BYTES',16*1024**2),\
                patch.object(feed_module,'spawn_owned',side_effect=OSError('controlled dispatch boundary')),\
                patch.object(PublicCaptureArchive,'commit_directory',side_effect=OSError('controlled retained disk failure')):
            with self.assertRaises(feed_module.MarketAttemptIncomplete):
                feed_module.check_batch_once(config_path,h.subscription.runtime_token,(h.subscription,),threading.Event())
        summary=PublicCaptureArchive(config.local_data_root/ROOT).summary()
        self.assertEqual(summary['request_accounting'],'PENDING');self.assertIsNone(summary['provider_requests'])
        self.assertEqual(summary['request_budget_upper'],1)


if __name__=='__main__':unittest.main()
