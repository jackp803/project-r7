"""Actual canonical E5/FP04/FP11 projection and E6 replay; fake provider only."""
import unittest
import json
from datetime import timedelta
from unittest.mock import patch

import tests.product.test_trading_position_v02 as position_fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures


class TradingProtectionMonitorV02Tests(unittest.TestCase):
    def setUp(self):
        self.helper=position_fixtures.TradingPositionV02Tests(methodName='runTest')
        self.addCleanup(self.helper.doCleanups);self.helper.setUp();self.fixture=self.helper.fixture
        self.inventory=inventory_fixtures.TradingInventoryV02Tests(methodName='runTest')

    def context(self,*,active=True,extra=False,readback=True,inventory_empty=False):
        service,stop=self.helper.helper.stop()
        now=self.fixture.clock[0]
        algo=dict(stop.materialization.body,instType='SWAP',algoId='2345',
            state='live' if active else 'canceled',ordIdList=[],actualSz='0',failCode='',
            cTime=str(int(now.timestamp()*1000)),uTime=str(int(now.timestamp()*1000)))
        rows=[algo] if active else []
        if extra:rows.append(dict(algo,algoId='2344',algoClOrdId='EXTERNALSTOP'))
        if inventory_empty:rows=[]
        script=[dict(code='0',data=[dict(algoId='2345',algoClOrdId=algo['algoClOrdId'],sCode='0')])]
        if readback:script.append(dict(code='0',data=[algo]))
        script.append(self.helper.response())
        script.extend(self.inventory.scans(rows))
        provider=self.helper.helper.api().FakeProductProvider(script);service.provider=provider
        service.execute(stop,expected_revision=self.fixture.revision)
        self.fixture.clock[0]+=timedelta(seconds=1)
        if readback:service.reconcile(stop.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        metadata,proof=self.helper.current_metadata()
        position=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.helper.project(service,position,metadata,proof)
        inventory=service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        return service,provider,stop,metadata,proof,position,inventory

    def monitor(self,context):
        service,provider,stop,metadata,proof,position,inventory=context
        return service.project_protection(stop.canonical_request.order_request_id,position,inventory,
            metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def test_verified_exact_single_owned_stop_projects_actual_e5_protected_and_fp12(self):
        context=self.context();outcome=self.monitor(context)
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('OPEN_PROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual('PROTECTION_VERIFIED',recovered.current_position_projection.payload['lifecycle_event'])
        self.assertEqual('PROTECTION_PROJECTED',outcome.status)
        service,provider,stop,*_=context
        batch=service.dispatch.latest_position_publication('fixture-run',stop.canonical_request.order_request_id)
        self.assertIn('EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED',batch.observation_json)
        self.assertIn('CURRENT_GENERATION_OWNERSHIP_PROVEN',batch.observation_json)
        self.assertEqual(1,len([item for item in provider.calls if item['method']=='POST']))
        before=len(recovered.lifecycle_history);self.monitor(context)
        self.assertEqual(before,len(self.helper.recover().lifecycle_history))

    def test_duplicate_or_external_active_stop_blocks_healthy_claim_without_cleanup(self):
        context=self.context(extra=True);self.monitor(context)
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('RECONCILIATION_REQUIRED',recovered.current_position_projection.payload['lifecycle_state'])
        batch=context[0].dispatch.latest_position_publication('fixture-run',context[2].canonical_request.order_request_id)
        self.assertIn('MULTIPLE_ACTIVE_PROTECTIONS',batch.observation_json)
        self.assertIn('EXTERNAL_UNTRACKED',batch.observation_json)
        self.assertEqual(1,len([item for item in context[1].calls if item['method']=='POST']))

    def test_ack_and_pending_inventory_without_exact_readback_do_not_promote_protection(self):
        context=self.context(readback=False);self.monitor(context)
        self.assertEqual('RECONCILIATION_REQUIRED',self.helper.recover().current_position_projection.payload['lifecycle_state'])
        self.assertEqual(1,len([item for item in context[1].calls if item['method']=='POST']))

    def test_exact_canceled_stop_and_current_empty_scan_projects_e5_emergency_not_closed(self):
        context=self.context(active=False);self.monitor(context)
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('EMERGENCY',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual('PROTECTION_FAILED',recovered.current_position_projection.payload['lifecycle_event'])
        self.assertIsNone(recovered.trade_result)

    def test_crash_after_projection_replays_original_binding_without_provider_io(self):
        context=self.context();service,provider,stop,*_=context
        with patch.object(type(self.helper.canonical),'persist_lifecycle_execution_binding',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):self.monitor(context)
        pending=service.dispatch.pending_position_publications('fixture-run')
        self.assertEqual(1,len(pending));self.assertEqual(stop.canonical_request.order_request_id,pending[0].operation_id)
        before=len(provider.calls)
        service.lease=service.dispatch.begin_process('fixture-run','protection-recovery:2',expected_generation=1,now=self.fixture.clock[0])
        service.recover_publications()
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('OPEN_PROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual(before,len(provider.calls))
        self.assertEqual((),service.dispatch.pending_position_publications('fixture-run'))

    def test_lost_verified_stop_uses_current_position_and_e5_protection_lost_event(self):
        context=self.context();self.monitor(context)
        service,original_provider,stop,*_=context
        self.fixture.clock[0]+=timedelta(seconds=1);now=self.fixture.clock[0]
        canceled=dict(stop.materialization.body,instType='SWAP',algoId='2345',state='canceled',
            ordIdList=[],actualSz='0',failCode='',cTime=str(int((now-timedelta(seconds=2)).timestamp()*1000)),
            uTime=str(int(now.timestamp()*1000)))
        provider=self.helper.helper.api().FakeProductProvider([dict(code='0',data=[canceled]),
            self.helper.response(),*self.inventory.scans()]);service.provider=provider
        service.reconcile(stop.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        metadata,proof=self.helper.current_metadata()
        position=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.helper.project(service,position,metadata,proof)
        inventory=service.read_algo_inventory(metadata=metadata,proof=proof,expected_revision=self.fixture.revision)
        self.monitor((service,provider,stop,metadata,proof,position,inventory))
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('EMERGENCY',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertEqual('PROTECTION_LOST',recovered.current_position_projection.payload['lifecycle_event'])
        self.assertEqual('0.0004',recovered.current_position_projection.payload['actual_quantity'])
        self.assertIsNone(recovered.trade_result)
        self.assertTrue(all(item['method']=='GET' for item in provider.calls))

    def test_other_local_historical_claim_is_unknown_and_cannot_be_labeled_untracked_external(self):
        from brokers.okx_product_state import durable_product_intent
        context=self.context(extra=True);service,provider,stop,*_=context
        current=service.admission.evaluate(self.fixture.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        service.dispatch.ensure_run('other-local-stop',current.owner_permission,now=self.fixture.clock[0])
        lease=service.dispatch.begin_process('other-local-stop','other-local:1',expected_generation=0,now=self.fixture.clock[0])
        original=durable_product_intent(stop)
        legacy={key:original[key] for key in ('role','path','native_client_id','body','canonical_request_hash','authority_hash')}
        legacy['native_client_id']='EXTERNALSTOP';legacy['body']=dict(legacy['body'],algoClOrdId='EXTERNALSTOP')
        service.dispatch.prepare('other-local-stop','other-claimed-stop',legacy,lease=lease,now=self.fixture.clock[0])
        service.dispatch.claim_dispatch('other-local-stop','other-claimed-stop',lease=lease,now=self.fixture.clock[0])
        self.monitor(context)
        batch=service.dispatch.latest_position_publication('fixture-run',stop.canonical_request.order_request_id)
        dependencies=json.loads(batch.observation_json)['fp04_evidence']
        other=next(item for item in dependencies if item['provider_object_ref']=='OKX:algo:2344')
        self.assertEqual('UNKNOWN',other['ownership_classification'])
        self.assertEqual('RECONCILIATION_REQUIRED',self.helper.recover().current_position_projection.payload['lifecycle_state'])
        self.assertEqual(1,len([item for item in provider.calls if item['method']=='POST']))

    def test_exact_active_query_with_missing_current_inventory_cannot_promote_protection(self):
        context=self.context(inventory_empty=True);self.monitor(context)
        recovered=self.helper.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual('OPEN_UNPROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.assertNotEqual('PROTECTION_VERIFIED',recovered.current_position_projection.payload['lifecycle_event'])
        self.assertIsNone(recovered.trade_result)
        self.assertEqual(1,len([item for item in context[1].calls if item['method']=='POST']))

    def test_local_stop_after_1000_claims_remains_unknown_without_cleanup(self):
        from tests.storage.test_product_claim_inventory_v02 import seed_claim_history
        from brokers.okx_product_state import durable_product_intent
        context=self.context(extra=True);service,provider,stop,*_=context
        current=service.admission.evaluate(self.fixture.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        seed_claim_history(service.dispatch,current.owner_permission,service.lease,self.fixture.clock[0],
            count=1001,role='PROTECTION_STOP',prefix='oldstop')
        original=durable_product_intent(stop)
        legacy={key:original[key] for key in ('role','path','native_client_id','body','canonical_request_hash','authority_hash')}
        legacy['native_client_id']='EXTERNALSTOP';legacy['body']=dict(legacy['body'],algoClOrdId='EXTERNALSTOP')
        service.dispatch.prepare('fixture-run','zz-last-local-stop',legacy,lease=service.lease,now=self.fixture.clock[0])
        service.dispatch.claim_dispatch('fixture-run','zz-last-local-stop',lease=service.lease,now=self.fixture.clock[0])
        self.monitor(context)
        batch=service.dispatch.latest_position_publication('fixture-run',stop.canonical_request.order_request_id)
        other=next(item for item in json.loads(batch.observation_json)['fp04_evidence'] if item['provider_object_ref']=='OKX:algo:2344')
        self.assertEqual('UNKNOWN',other['ownership_classification'])
        self.assertEqual('RECONCILIATION_REQUIRED',self.helper.recover().current_position_projection.payload['lifecycle_state'])
        self.assertEqual(1,len([item for item in provider.calls if item['method']=='POST']))

    def test_claim_append_after_owner_interpretation_invalidates_protection_publication(self):
        from tests.storage.test_product_claim_inventory_v02 import seed_claim_history
        from application.trading import protection_monitor
        context=self.context();service,provider,stop,*_=context
        current=service.admission.evaluate(self.fixture.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        original=protection_monitor.interpret_protection_registry_evidence
        def append_claim(*args,**kwargs):
            result=original(*args,**kwargs)
            seed_claim_history(service.dispatch,current.owner_permission,service.lease,self.fixture.clock[0],
                count=1,role='PROTECTION_STOP',prefix='late')
            return result
        with patch.object(protection_monitor,'interpret_protection_registry_evidence',side_effect=append_claim):
            with self.assertRaisesRegex(ValueError,'DISPATCH_CLAIM_INVENTORY_CHANGED'):
                self.monitor(context)
        self.assertEqual('OPEN_UNPROTECTED',self.helper.recover().current_position_projection.payload['lifecycle_state'])
        self.assertIsNone(service.dispatch.latest_position_publication('fixture-run',stop.canonical_request.order_request_id))

    def test_claim_append_at_outbox_boundary_is_rejected_in_actual_writer_transaction(self):
        from tests.storage.test_product_claim_inventory_v02 import seed_claim_history
        context=self.context();service,provider,stop,*_=context
        current=service.admission.evaluate(self.fixture.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        original=service.dispatch.observe_position
        def append_claim(*args,**kwargs):
            seed_claim_history(service.dispatch,current.owner_permission,service.lease,self.fixture.clock[0],
                count=1,role='PROTECTION_STOP',prefix='boundary')
            return original(*args,**kwargs)
        with patch.object(service.dispatch,'observe_position',side_effect=append_claim):
            with self.assertRaisesRegex(ValueError,'DISPATCH_CLAIM_INVENTORY_CHANGED'):
                self.monitor(context)
        self.assertEqual('OPEN_UNPROTECTED',self.helper.recover().current_position_projection.payload['lifecycle_state'])
        self.assertIsNone(service.dispatch.latest_position_publication('fixture-run',stop.canonical_request.order_request_id))


if __name__=='__main__':unittest.main()
