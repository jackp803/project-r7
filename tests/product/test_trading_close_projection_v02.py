"""Actual scripted-native close/fill/position ownership, never a real account."""
from datetime import timedelta
from unittest.mock import patch
import unittest

import tests.product.test_trading_close_v02 as close_fixtures


class TradingCloseProjectionV02Tests(unittest.TestCase):
    def setUp(self):
        self.owner=close_fixtures.TradingCloseV02Tests(methodName='runTest');self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.fixture=self.owner.fixture;self.position=self.owner.position

    def closing(self):
        context=self.owner.entered();service,provider,*_=context
        prepared=self.owner.prepare(context);self.owner.append_ack(provider,prepared)
        service.execute(prepared,expected_revision=self.fixture.revision)
        return context,prepared

    def readback(self,context,prepared,*,filled='4',net='6',native_id='5678',old_update=False,
                 advance_seconds=2,first_fill_offset_seconds=1):
        from application.trading.provider import FakeProductProvider
        service,provider,*_=context;self.fixture.clock[0]+=timedelta(seconds=advance_seconds)
        now=self.fixture.clock[0]
        order=dict(prepared.materialization.body,instType='SWAP',ordId='3456',
            state='filled' if filled=='10' else 'partially_filled',accFillSz=filled,avgPx='61000')
        quantities=('4','6') if filled=='10' else ('4',)
        rows=[dict(instId='BTC-USDT-SWAP',clOrdId=prepared.materialization.provider_cl_ord_id,
            ordId='3456',tradeId=str(index+2),side='sell',posSide='net',fillSz=quantity,fillPx='61000',
            fillTime=str(int((now-timedelta(seconds=first_fill_offset_seconds if index==0 else 0)).timestamp()*1000)),
            fee='-0.01',feeCcy='USDT') for index,quantity in enumerate(quantities)]
        # Original fill identity/time is immutable across cumulative readbacks.
        if filled=='10':rows[0]['fillTime']=str(int((now-timedelta(seconds=3)).timestamp()*1000))
        position=self.position.response(pos=net,posId=native_id,avgPx='0' if net=='0' else '60000')
        if old_update:position['data'][0]['uTime']=str(int((now-timedelta(seconds=3)).timestamp()*1000))
        script=FakeProductProvider([dict(code='0',data=[order]),dict(code='0',data=rows),position])
        provider._responses.extend(script._responses)
        result=service.reconcile(prepared.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        self.assertEqual(result.status,'ORDER_OBSERVED')
        metadata,proof=self.position.current_metadata()
        native=service.read_position(metadata=metadata,proof=proof,expected_revision=self.fixture.revision,
                                     expected_provider_position_id=native_id)
        return native,metadata,proof

    def project(self,context,prepared,read):
        native,metadata,proof=read
        return context[0].project_close_position(prepared.canonical_request.order_request_id,native,
            metadata=metadata,proof=proof,expected_revision=self.fixture.revision)

    def test_actual_partial_then_explicit_same_position_zero_preserves_basis_and_never_finalizes(self):
        context,prepared=self.closing();service,provider,*_=context
        partial=self.readback(context,prepared);outcome=self.project(context,prepared,partial)
        recovered=self.position.recover();projection=recovered.current_position_projection.payload
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual(projection['actual_quantity'],'0.0006')
        self.assertEqual(projection['lifecycle_state'],'EXIT_REQUESTED')
        self.assertEqual(projection['average_entry_price'],'60000')
        count=len(recovered.lifecycle_history)
        self.assertEqual(self.project(context,prepared,partial),outcome)
        self.assertEqual(len(self.position.recover().lifecycle_history),count)
        flat=self.readback(context,prepared,filled='10',net='0');self.project(context,prepared,flat)
        recovered=self.position.recover();projection=recovered.current_position_projection.payload
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual(projection['actual_quantity'],'0.0000')
        self.assertEqual(projection['lifecycle_state'],'EXIT_REQUESTED')
        self.assertEqual(projection['average_entry_price'],'60000')
        self.assertNotIn('provider_position_id',projection)
        self.assertIsNone(recovered.trade_result)
        self.assertEqual(len([call for call in provider.calls if call['method']=='POST']),2)

    def test_other_issued_native_position_cannot_adopt_original_close_lineage(self):
        context,prepared=self.closing();read=self.readback(context,prepared,native_id='9999')
        before=self.position.recover()
        with self.assertRaises(ValueError):self.project(context,prepared,read)
        self.assertEqual(self.position.recover().lifecycle_history,before.lifecycle_history)
        self.assertIsNone(context[0].dispatch.position_publication('fixture-run',prepared.canonical_request.order_request_id,read[0].received_at))

    def test_later_actual_entry_readback_preserves_original_source_and_full_close_history(self):
        from application.trading.provider import FakeProductProvider
        from datetime import datetime
        context,prepared=self.closing();service,provider,*_=context
        original=self.position.recover();source=original.current_position_projection
        self.fixture.clock[0]+=timedelta(seconds=1)
        entry_fill=next(row.payload for row in original.fills if row.payload['order_role'] in (None,'ENTRY'))
        rows=self.owner.helper.fill_rows();rows['data'][0].update(fillSz='10',fee='-0.03',
            fillTime=str(int(datetime.fromisoformat(entry_fill['filled_at'].replace('Z','+00:00')).timestamp()*1000)))
        script=FakeProductProvider([self.owner.helper.order(state='filled',accFillSz='10',avgPx='60000'),rows])
        provider._responses.extend(script._responses)
        entry_id=self.owner.helper.prepared.canonical_request.order_request_id
        result=service.reconcile(entry_id,expected_revision=self.fixture.revision)
        self.assertEqual(result.status,'ORDER_OBSERVED')
        self.assertEqual(self.position.recover().current_position_projection,source)
        self.project(context,prepared,self.readback(context,prepared))
        self.project(context,prepared,self.readback(context,prepared,filled='10',net='0'))
        recovered=self.position.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual(recovered.current_position_projection.payload['actual_quantity'],'0.0000')
        actual_entries=[row for row in recovered.order_result_observations if row.payload['order_request_id']==entry_id]
        self.assertEqual(len(actual_entries),3)  # ACK, original fill, later actual re-read.

    def test_native_residual_disagreement_cannot_create_a_position_publication(self):
        context,prepared=self.closing();read=self.readback(context,prepared,net='7')
        before=self.position.recover()
        with self.assertRaises(ValueError):self.project(context,prepared,read)
        self.assertEqual(self.position.recover().lifecycle_history,before.lifecycle_history)
        self.assertEqual(context[0].dispatch.pending_position_publications('fixture-run'),())

    def test_copied_or_stale_read_cannot_renew_close_exposure(self):
        from dataclasses import replace
        context,prepared=self.closing();native,metadata,proof=self.readback(context,prepared)
        with self.assertRaises(ValueError):self.project(context,prepared,(replace(native),metadata,proof))
        self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.project(context,prepared,(native,metadata,proof))

    def test_native_update_before_actual_exit_fill_does_not_prove_residual(self):
        context,prepared=self.closing();read=self.readback(context,prepared,old_update=True)
        with self.assertRaises(ValueError):self.project(context,prepared,read)
        self.assertEqual(context[0].dispatch.pending_position_publications('fixture-run'),())

    def test_durable_close_bundle_replays_after_successor_process_without_http_or_resubmit(self):
        context,prepared=self.closing();service,provider,*_=context;read=self.readback(context,prepared)
        canonical=self.owner.helper.canonical
        with patch.object(type(canonical),'persist_lifecycle_execution_binding',side_effect=OSError('fixture disk failure')):
            with self.assertRaises(OSError):self.project(context,prepared,read)
        self.assertEqual(len(service.dispatch.pending_position_publications('fixture-run')),1)
        calls=list(provider.calls)
        lease=service.dispatch.begin_process('fixture-run','close-recovery:2',expected_generation=1,now=self.fixture.clock[0])
        with self.assertRaises(ValueError):self.project(context,prepared,read)
        service.lease=lease;service.recover_publications()
        self.assertEqual(provider.calls,calls)
        self.assertEqual(service.dispatch.pending_position_publications('fixture-run'),())
        recovered=self.position.recover()
        self.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        self.assertEqual(recovered.current_position_projection.payload['actual_quantity'],'0.0006')

    def test_actual_second_connection_claim_at_writer_boundary_blocks_close_publication(self):
        context,prepared=self.closing();service=context[0];read=self.readback(context,prepared)
        before=self.position.recover();original=service.dispatch.observe_position
        def append_then_observe(*args,**kwargs):
            with self.owner.append_foreign_claim_after_current(service,'ENTRY'):
                service.dispatch.claim_dispatch('fixture-run',prepared.canonical_request.order_request_id,
                    lease=service.lease,now=self.fixture.clock[0])
            return original(*args,**kwargs)
        with patch.object(service.dispatch,'observe_position',side_effect=append_then_observe):
            with self.assertRaises(ValueError):self.project(context,prepared,read)
        self.assertEqual(self.position.recover().lifecycle_history,before.lifecycle_history)
        self.assertEqual(service.dispatch.pending_position_publications('fixture-run'),())

    def test_delayed_actual_bundle_cannot_be_inserted_behind_a_newer_flat_observation(self):
        context,prepared=self.closing();service=context[0];partial=self.readback(context,prepared)
        captured=[]
        def pause_before_write(*args,**kwargs):
            captured.append((args,kwargs));raise OSError('fixture delayed writer')
        with patch.object(service.dispatch,'observe_position',side_effect=pause_before_write):
            with self.assertRaises(OSError):self.project(context,prepared,partial)
        self.project(context,prepared,self.readback(context,prepared,filled='10',net='0'))
        self.assertEqual(len(captured),1)
        args,kwargs=captured[0]
        # A fresh data fence cannot make an obsolete actual E5 bundle current.
        kwargs.update(now=self.fixture.clock[0],claim_inventory_generation=service.dispatch.claim_inventory_generation())
        with self.assertRaises(ValueError):service.dispatch.observe_position(*args,**kwargs)
        self.assertEqual(service.dispatch.pending_position_publications('fixture-run'),())


if __name__=='__main__':unittest.main()
