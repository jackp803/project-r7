"""Actual E6/E7 read admission, E4 position facts and E5 durable projection."""
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import tests.product.test_trading_dispatch_v02 as fixtures
import tests.brokers.test_okx_demo_adapter as metadata_fixtures
from brokers.okx_demo import OKXAccountConfigSnapshot
from position.entry_observation import product_entry_position_id


class TradingPositionV02Tests(unittest.TestCase):
    def setUp(self):
        self.helper=fixtures.TradingDispatchV02Tests(methodName='runTest')
        self.addCleanup(self.helper.doCleanups);self.helper.setUp();self.fixture=self.helper.fixture
        self.canonical=self.helper.canonical;self.dispatch=self.helper.dispatch

    def response(self,**changes):
        now=self.fixture.clock[0]
        row=dict(instType='SWAP',instId='BTC-USDT-SWAP',mgnMode='isolated',posSide='net',
                 ccy='USDT',posId='5678',pos='4',avgPx='60000',uTime=str(int(now.timestamp()*1000)))
        row.update(changes);return dict(code='0',data=[row])

    def current_metadata(self):
        now=self.fixture.clock[0]
        metadata=replace(metadata_fixtures._metadata(now),ct_val=Decimal('0.0001'))
        proof=self.helper.capabilities.issue('READ_ONLY_RECONCILIATION',OKXAccountConfigSnapshot('2','net_mode','123','123'),
            metadata,observed_at=now,now=now)
        return metadata,proof

    def entered(self,next_position=None,**changes):
        script=[self.helper.ack(),self.helper.order(state='partially_filled',accFillSz='4',avgPx='60000'),
                self.helper.fill_rows(),self.response(**changes)]
        if next_position is not None:script.append(next_position)
        service,provider=self.helper.service(script)
        service.execute(self.helper.prepared,expected_revision=self.fixture.revision)
        self.fixture.clock[0]+=timedelta(seconds=2)
        service.reconcile(self.helper.prepared.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        metadata,proof=self.current_metadata()
        value=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        return service,provider,metadata,proof,value

    def project(self,service,value,metadata,proof):
        return service.project_entry_position(self.helper.prepared.canonical_request.order_request_id,value,
            metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def recover(self):
        return self.canonical.recover(trade_plan_id=self.helper.plan['trade_plan_id'],
            position_id=product_entry_position_id(self.helper.plan['trade_plan_id']))

    def test_actual_partial_position_becomes_restart_authoritative_without_native_id_leak(self):
        service,provider,metadata,proof,value=self.entered()
        outcome=self.project(service,value,metadata,proof)
        recovered=self.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('OPEN_UNPROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual('0.0004',recovered.current_position_projection.payload['actual_quantity'])
        self.assertEqual(2,len(recovered.lifecycle_history))
        self.assertEqual(2,len(recovered.lifecycle_execution_bindings))
        self.assertNotIn('provider_position_id',recovered.current_position_projection.payload)
        self.assertEqual('POSITION_PROJECTED',outcome.status)
        self.assertEqual(['POST','GET','GET','GET'],[item['method'] for item in provider.calls])
        repeated=self.project(service,value,metadata,proof)
        self.assertEqual(outcome,repeated)
        self.assertEqual(2,len(self.recover().lifecycle_history))

    def test_copied_mutated_stale_or_old_generation_position_cannot_create_projection(self):
        service,provider,metadata,proof,value=self.entered()
        for candidate in (replace(value),replace(value,canonical_net_quantity=Decimal('0.001'))):
            with self.subTest(candidate=candidate),self.assertRaises(ValueError):self.project(service,candidate,metadata,proof)
        self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.project(service,value,metadata,proof)
        self.assertIsNone(self.canonical.recover(trade_plan_id=self.helper.plan['trade_plan_id']).current_position_projection)

    def reject_disagreement(self,**changes):
        service,provider,metadata,proof,value=self.entered(**changes)
        with self.assertRaises(ValueError):self.project(service,value,metadata,proof)
        self.assertIsNone(self.canonical.recover(trade_plan_id=self.helper.plan['trade_plan_id']).current_position_projection)
        self.assertEqual(1,len([item for item in provider.calls if item['method']=='POST']))

    def test_native_quantity_disagreement_with_complete_entry_facts_fails_closed(self):
        self.reject_disagreement(pos='3')

    def test_native_price_disagreement_with_complete_entry_facts_fails_closed(self):
        self.reject_disagreement(avgPx='59999')

    def test_projection_publication_failure_replays_exact_bundle_after_process_restart_without_http(self):
        service,provider,metadata,proof,value=self.entered()
        with patch.object(type(self.canonical),'persist_lifecycle_execution_binding',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):self.project(service,value,metadata,proof)
        self.assertEqual(1,len(self.dispatch.pending_position_publications('fixture-run')))
        lease=self.dispatch.begin_process('fixture-run','position-recovery:2',expected_generation=1,now=self.fixture.clock[0])
        with self.assertRaises(ValueError):self.project(service,value,metadata,proof)
        service.lease=lease;service.recover_publications()
        self.assertEqual((),self.dispatch.pending_position_publications('fixture-run'))
        recovered=self.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual(2,len(recovered.lifecycle_history))
        self.assertEqual(['POST','GET','GET','GET'],[item['method'] for item in provider.calls])

    def test_new_native_position_identity_cannot_reattest_the_original_e5_instance(self):
        service,provider,metadata,proof,value=self.entered(next_position=self.response(posId='999'))
        self.project(service,value,metadata,proof)
        self.fixture.clock[0]+=timedelta(seconds=2)
        metadata,proof=self.current_metadata()
        current=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        with self.assertRaises(ValueError):self.project(service,current,metadata,proof)
        self.assertEqual(2,len(self.recover().lifecycle_history))

    def test_pending_stop_facts_require_fresh_native_position_and_actual_e5_reattestation(self):
        service,stop=self.helper.stop()
        native=stop.materialization.provider_cl_ord_id
        provider=self.helper.api().FakeProductProvider([dict(code='0',data=[dict(algoId='2345',algoClOrdId=native,sCode='0')]),
                                                       self.response()])
        service.provider=provider
        service.execute(stop,expected_revision=self.fixture.revision)
        self.assertIn('E5_EXECUTION_REINTERPRETATION_REQUIRED',self.recover().reason_codes)
        self.fixture.clock[0]+=timedelta(seconds=1)
        metadata,proof=self.current_metadata()
        value=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.project(service,value,metadata,proof)
        recovered=self.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('OPEN_UNPROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual(1,len(recovered.current_lifecycle_execution_binding.payload['order_evidence']))
        self.assertEqual('PENDING',next(item.payload['order_status'] for item in recovered.current_order_results
            if item.payload['order_request_id']==stop.canonical_request.order_request_id))
        self.assertEqual(['POST','GET'],[item['method'] for item in provider.calls])

    def test_prior_unbound_protection_claim_blocks_another_initial_stop_before_post(self):
        from brokers.okx_product_state import durable_product_intent
        from application.trading.admission import RuntimeAdmissionError
        service,stop=self.helper.stop()
        current=self.helper.admission.evaluate(self.fixture.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        self.dispatch.ensure_run('historical-protection',current.owner_permission,now=self.fixture.clock[0])
        lease=self.dispatch.begin_process('historical-protection','historic:1',expected_generation=0,now=self.fixture.clock[0])
        original=durable_product_intent(stop)
        # A historical data-only intent lacks canonical instance binding. It
        # cannot clear ambiguity merely because a current pending view is empty.
        old={key:original[key] for key in ('role','path','native_client_id','body','canonical_request_hash','authority_hash')}
        old['native_client_id']='HISTORICSTOP';old['body']=dict(old['body'],algoClOrdId='HISTORICSTOP')
        self.dispatch.prepare('historical-protection','historic-stop',old,lease=lease,now=self.fixture.clock[0])
        self.dispatch.claim_dispatch('historical-protection','historic-stop',lease=lease,now=self.fixture.clock[0])
        provider=self.helper.api().FakeProductProvider([dict(code='0',data=[dict(algoId='2345',
            algoClOrdId=stop.materialization.provider_cl_ord_id,sCode='0')])]);service.provider=provider
        with self.assertRaises(RuntimeAdmissionError):service.execute(stop,expected_revision=self.fixture.revision)
        self.assertEqual([],provider.calls)
        self.assertIsNone(self.dispatch.operation('fixture-run',stop.canonical_request.order_request_id))

    def test_empty_position_response_and_stale_owner_version_are_denied_without_projection(self):
        service,provider=self.helper.service([dict(code='0',data=[])])
        metadata,proof=self.current_metadata()
        with self.assertRaises(ValueError):
            service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision+1)
        self.assertEqual([],provider.calls)
        with self.assertRaises(ValueError):
            service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.assertEqual(['GET'],[item['method'] for item in provider.calls])
        self.assertIsNone(self.canonical.recover(trade_plan_id=self.helper.plan['trade_plan_id']).current_position_projection)

    def test_provider_changed_during_native_read_cannot_issue_the_old_response_to_new_provider(self):
        service,provider=self.helper.service([self.response()]);metadata,proof=self.current_metadata()
        original=service._read
        def changed(*args,**kwargs):
            value=original(*args,**kwargs)
            service.provider=self.helper.api().FakeProductProvider([])
            return value
        with patch.object(service,'_read',side_effect=changed),self.assertRaises(ValueError):
            service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.assertEqual(['GET'],[item['method'] for item in provider.calls])


if __name__=='__main__':unittest.main()
