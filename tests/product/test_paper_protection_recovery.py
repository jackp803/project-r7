"""Actual E4 read outage -> E5 uncertainty -> queried recovery, no DB repair."""
from datetime import timedelta
from unittest.mock import patch
import unittest

from brokers.paper import PaperBroker
from tests.product import test_paper_runtime_v02 as fixture


class PaperProtectionRecoveryTests(unittest.TestCase):
    setUp=fixture.PaperRuntimeV02Tests.setUp
    make_service=fixture.PaperRuntimeV02Tests.make_service
    start=fixture.PaperRuntimeV02Tests.start
    event=fixture.PaperRuntimeV02Tests.event

    def protected(self):
        runtime=self.start();runtime.on_market_event(self.event(0,bars=True));runtime.on_market_event(self.event(1))
        state=self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(state['position']['lifecycle_state'],'OPEN_PROTECTED')
        return runtime,state

    def unavailable(self,runtime,state,seconds):
        original=PaperBroker.query_order;client=state['protection_request']['client_order_id']
        def query(broker,key):return None if key==client else original(broker,key)
        with patch.object(PaperBroker,'query_order',query):outcome=runtime.on_market_event(self.event(seconds))
        self.assertEqual(outcome.status,'BLOCKED')
        self.assertEqual(self.process.recover(runtime.run_id).state['runtime']['position']['lifecycle_state'],'RECONCILIATION_REQUIRED')

    def assert_recovered(self,runtime,original,seconds):
        runtime.on_market_event(self.event(seconds));current=self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(current['position']['lifecycle_state'],'OPEN_PROTECTED')
        self.assertEqual(current['position']['lifecycle_event'],'RECONCILED_OPEN_PROTECTED')
        self.assertEqual(current['position']['opened_at'],original['position']['opened_at'])
        self.assertEqual(current['position']['actual_quantity'],original['position']['actual_quantity'])
        self.assertEqual(current['protection_request'],original['protection_request'])
        self.assertEqual(current['exit_anchor']['payload']['first_fill_at'],original['exit_anchor']['payload']['first_fill_at'])
        self.assertEqual(self.canonical.recover(position_id=current['position']['position_id']).status,'READY')

    def test_queried_original_open_stop_recovers_actual_e5_graph(self):
        runtime,original=self.protected();self.unavailable(runtime,original,2)
        self.assert_recovered(runtime,original,3)

    def test_restart_requeries_original_stop_without_resuming_paused_entries(self):
        runtime,original=self.protected();self.service.stop_new_entries(runtime.run_id,'operator-pause-before-outage')
        self.unavailable(runtime,original,2)
        successor=self.make_service(fixture.simulation_fixture()).runtime(runtime.run_id)
        self.assertGreater(successor.coordinator.generation,runtime.coordinator.generation)
        self.assert_recovered(successor,original,3)
        self.assertFalse(self.process.recover(runtime.run_id).state['runtime']['paper_entries_allowed'])

    def test_repeated_missing_query_does_not_claim_recovery_or_replace_stop(self):
        runtime,original=self.protected();self.unavailable(runtime,original,2);self.unavailable(runtime,original,3)
        current=self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(current['protection_request'],original['protection_request'])
        self.assertEqual(len(self.process.recover(runtime.run_id).state['broker']['payload']['submissions']),2)

    def test_changed_query_identity_or_current_exposure_never_recovers_uncertain_position(self):
        from dataclasses import replace
        from decimal import Decimal
        runtime,original=self.protected();self.unavailable(runtime,original,2)
        order_query=PaperBroker.query_order;position_query=PaperBroker.query_position
        def wrong_order(broker,key):
            actual=order_query(broker,key)
            return replace(actual,client_order_id='unrelated-stop') if key==original['protection_request']['client_order_id'] else actual
        def wrong_position(broker,symbol):return replace(position_query(broker,symbol),net_quantity=Decimal('9'))
        for seconds,method,query in ((3,'query_order',wrong_order),(4,'query_position',wrong_position)):
            with self.subTest(method=method),patch.object(PaperBroker,method,query):
                outcome=runtime.on_market_event(self.event(seconds));self.assertEqual(outcome.status,'BLOCKED')
                current=self.process.recover(runtime.run_id).state['runtime']
                self.assertEqual(current['position']['lifecycle_state'],'RECONCILIATION_REQUIRED')
                self.assertEqual(current['protection_request'],original['protection_request'])
                self.assertEqual(current['position']['actual_quantity'],original['position']['actual_quantity'])
