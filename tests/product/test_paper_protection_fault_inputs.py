"""Closed FIXTURE E4 read/cancel inputs, actual E5 outcomes, no stored verdict."""
from dataclasses import replace
from datetime import timedelta
import unittest

from brokers.paper import PaperBroker
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderStatus
from tests.product import test_paper_protection_recovery as recovery
from tests.product import test_paper_runtime_v02 as fixture


class PaperProtectionFaultInputTests(unittest.TestCase):
    setUp=fixture.PaperRuntimeV02Tests.setUp
    make_service=fixture.PaperRuntimeV02Tests.make_service
    start=fixture.PaperRuntimeV02Tests.start
    event=fixture.PaperRuntimeV02Tests.event
    protected=recovery.PaperProtectionRecoveryTests.protected

    def test_broker_missing_and_stale_reads_preserve_actual_order_and_cancel_uses_existing_owner(self):
        runtime,state=self.protected();broker=PaperBroker.from_state(self.process.recover(runtime.run_id).state['broker'])
        request=decode_fact(OrderRequest,state['protection_request']);before=broker.export_state()
        missing=broker.observe_fixture_protection(request,namespace='FIXTURE',mode='MISSING',observed_at=self.clock[0])
        self.assertTrue(missing.query_performed);self.assertIsNone(missing.queried_order);self.assertEqual(broker.export_state(),before)
        stale=broker.observe_fixture_protection(request,namespace='FIXTURE',mode='STALE',observed_at=self.clock[0])
        self.assertFalse(stale.query_performed);self.assertEqual(stale.queried_order,broker.query_order(request.client_order_id))
        self.assertEqual(broker.export_state(),before)
        for namespace,mode,selected in (('LOCAL_RESEARCH','MISSING',request),('FIXTURE','PASS',request),
                                       ('FIXTURE','MISSING',replace(request,client_order_id='wrong-stop'))):
            with self.subTest(namespace=namespace,mode=mode),self.assertRaises(ValueError):
                broker.observe_fixture_protection(selected,namespace=namespace,mode=mode,observed_at=self.clock[0])
        canceled=broker.observe_fixture_protection(request,namespace='FIXTURE',mode='CANCELED',observed_at=self.clock[0]+timedelta(seconds=1))
        self.assertEqual(canceled.queried_order.order_status,OrderStatus.CANCELED)
        self.assertNotEqual(broker.export_state(),before)

    def selected(self,mode):
        policy=fixture.simulation_fixture();policy.update(schema_version='r7-paper-simulation-policy-v0.4',fixture_protection_observation=mode)
        self.service=self.make_service(policy);self.boundary._resolve=self.service.resolve_owner_evidence

    def read_outage(self,mode):
        self.selected(mode);runtime,original=self.protected()
        runtime.on_market_event(self.event(2));unknown=self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(unknown['position']['lifecycle_state'],'RECONCILIATION_REQUIRED')
        successor=self.make_service(self.service.simulation.as_dict()).runtime(runtime.run_id)
        successor.on_market_event(self.event(5));current=self.process.recover(runtime.run_id).state['runtime']
        self.assertEqual(current['position']['lifecycle_state'],'OPEN_PROTECTED')
        self.assertEqual(current['position']['lifecycle_event'],'RECONCILED_OPEN_PROTECTED')
        self.assertEqual(current['protection_request'],original['protection_request'])

    def test_missing_query_recovers_from_actual_broker_without_new_stop(self):self.read_outage('MISSING')
    def test_stale_query_recovers_from_actual_broker_without_new_stop(self):self.read_outage('STALE')

    def test_selected_actual_cancel_produces_e5_loss_and_emergency_exit_without_fake_flatness(self):
        self.selected('CANCELED');runtime,original=self.protected();runtime.on_market_event(self.event(2))
        current=self.process.recover(runtime.run_id).state['runtime'];self.assertEqual(current['position']['lifecycle_state'],'EXIT_REQUESTED')
        self.assertGreater(float(current['position']['actual_quantity']),0)
        graph=self.canonical.recover(position_id=current['position']['position_id'])
        self.assertTrue(any(row.payload['lifecycle_event']=='PROTECTION_LOST' and row.payload['lifecycle_state']=='EMERGENCY' for row in graph.lifecycle_history))
        runtime.on_market_event(self.event(3));self.assertEqual(self.process.recover(runtime.run_id).state['runtime']['position']['lifecycle_state'],'CLOSED')
