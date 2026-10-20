"""Actual owner composition and native-script mechanics; no real provider I/O."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import unittest

from application.trading.admission import RuntimeAdmissionError
from brokers.okx_demo import OKXAccountConfigSnapshot
import tests.product.test_trading_position_v02 as position_fixtures


class TradingCloseV02Tests(unittest.TestCase):
    def setUp(self):
        self.position=position_fixtures.TradingPositionV02Tests(methodName='runTest');self.position.setUp()
        self.addCleanup(self.position.doCleanups)
        self.helper=self.position.helper;self.fixture=self.helper.fixture

    def entered(self):
        helper=self.helper;contracts=format(helper.prepared.materialization.provider_contract_quantity,'f')
        fills=helper.fill_rows();fills['data'][0].update(fillSz=contracts,fee='-0.03')
        service,provider=helper.service([helper.ack(),helper.order(state='filled',accFillSz=contracts,avgPx='60000'),
            fills,self.position.response(pos=contracts)])
        service.execute(helper.prepared,expected_revision=self.fixture.revision)
        self.fixture.clock[0]+=timedelta(seconds=2)
        outcome=service.reconcile(helper.prepared.canonical_request.order_request_id,expected_revision=self.fixture.revision)
        self.assertEqual(outcome.status,'ORDER_OBSERVED')
        metadata,read_proof=self.position.current_metadata()
        observed=service.read_position(metadata=metadata,proof=read_proof,expected_revision=self.fixture.revision)
        self.position.project(service,observed,metadata,read_proof)
        close_proof=helper.capabilities.issue('POSITION_EXIT',OKXAccountConfigSnapshot('2','net_mode','123','123'),
            metadata,observed_at=self.fixture.clock[0],now=self.fixture.clock[0])
        return service,provider,metadata,read_proof,close_proof,observed

    def prepare(self,context,observed=None):
        service,_,metadata,read_proof,close_proof,native=context
        return service.prepare_fixture_close(self.helper.plan['trade_plan_id'],native if observed is None else observed,
            metadata=metadata,read_proof=read_proof,close_proof=close_proof,expected_revision=self.fixture.revision)

    def append_ack(self,provider,prepared):
        from application.trading.provider import FakeProductProvider
        script=FakeProductProvider([dict(code='0',data=[dict(ordId='3456',
            clOrdId=prepared.materialization.provider_cl_ord_id,sCode='0')])])
        provider._responses.extend(script._responses)

    def test_preparation_uses_original_native_binding_and_real_e5_action_without_post_or_state_change(self):
        context=self.entered();service,provider,*_=context;before=self.position.recover()
        prepared=self.prepare(context);after=self.position.recover()
        self.assertEqual(prepared.role,'POSITION_EXIT')
        self.assertTrue(prepared.canonical_request.reduce_only)
        self.assertEqual(prepared.canonical_request.quantity,Decimal(before.current_position_projection.payload['actual_quantity']))
        self.assertEqual(prepared.materialization.body['sz'],'10')
        self.assertEqual(after.current_position_projection,before.current_position_projection)
        self.assertEqual(after.current_lifecycle_execution_binding,before.current_lifecycle_execution_binding)
        self.assertEqual(len(provider.calls),4)
        action=next(row for row in after.position_actions if row.canonical_id==prepared.canonical_request.position_action_id)
        self.assertEqual(action.payload['action'],'EXIT')
        self.assertEqual(action.payload['position_id'],before.current_position_projection.payload['position_id'])

    def test_copied_mutated_or_stale_position_read_cannot_create_close_authority(self):
        context=self.entered();service,provider,*_,observed=context
        before=self.position.recover()
        for candidate in (replace(observed),replace(observed,provider_position_id='9999')):
            with self.subTest(candidate=candidate.provider_position_id),self.assertRaises(RuntimeAdmissionError):
                self.prepare(context,candidate)
        self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.prepare(context)
        self.assertEqual(self.position.recover().position_actions,before.position_actions)
        self.assertEqual(len(provider.calls),4)

    def test_actual_close_post_is_reduce_only_and_ack_never_proves_flat_or_closed(self):
        context=self.entered();service,provider,*_=context;prepared=self.prepare(context)
        self.append_ack(provider,prepared)
        outcome=service.execute(prepared,expected_revision=self.fixture.revision)
        self.assertEqual(outcome.status,'ACK_PENDING')
        self.assertEqual(provider.calls[-1]['method'],'POST')
        self.assertTrue(provider.calls[-1]['body']['reduceOnly'])
        self.assertEqual(provider.calls[-1]['body']['sz'],'10')
        recovered=self.position.recover()
        self.assertIsNone(recovered.trade_result)
        self.assertEqual(recovered.current_position_projection.payload['actual_quantity'],'0.0010')
        self.assertNotEqual(recovered.current_position_projection.payload['lifecycle_state'],'CLOSED')

    def test_provider_replacement_after_preparation_denies_before_another_effect(self):
        from application.trading.provider import FakeProductProvider
        context=self.entered();service,provider,*_=context;prepared=self.prepare(context)
        replacement=FakeProductProvider([]);self.append_ack(replacement,prepared);service.provider=replacement
        with self.assertRaises(RuntimeAdmissionError):service.execute(prepared,expected_revision=self.fixture.revision)
        self.assertEqual(replacement.calls,[])
        self.assertEqual(len(provider.calls),4)

    def test_close_requires_exact_independent_role_profile_binding_without_creating_an_action(self):
        from application.trading.close_owner import fixture_close_profile
        context=self.entered();service,provider,metadata,read_proof,close_proof,native=context
        profile,binding=fixture_close_profile(metadata,'POSITION_EXIT');before=self.position.recover()
        for provided,bound in ((True,binding),({'status':'PASS'},binding),
                               (profile,replace(binding,instrument_metadata_hash='sha256:'+'f'*64))):
            with self.subTest(profile_type=type(provided).__name__),self.assertRaises(ValueError):
                service.prepare_close(self.helper.plan['trade_plan_id'],native,metadata=metadata,read_proof=read_proof,
                    close_proof=close_proof,expected_revision=self.fixture.revision,
                    metadata_applicability=provided,metadata_binding=bound)
        self.assertEqual(self.position.recover().position_actions,before.position_actions)
        self.assertEqual(len(provider.calls),4)

    def test_lost_original_close_issuer_cannot_reuse_a_preparation_for_an_effect(self):
        context=self.entered();service,provider,*_=context;prepared=self.prepare(context)
        self.append_ack(provider,prepared);service._close_preparations.clear()
        with self.assertRaises(RuntimeAdmissionError):service.execute(prepared,expected_revision=self.fixture.revision)
        self.assertEqual(len(provider.calls),4)

    def append_foreign_claim_after_current(self,service,role):
        from unittest.mock import patch
        from storage.product_dispatch import open_product_dispatch_journal
        original=service.dispatch.claim_dispatch
        decision=service.admission.evaluate(service.identity,expected_revision=self.fixture.revision,
            permission='MANAGE_EXISTING',execution=service.execution)
        self.assertTrue(decision.allowed)
        def claim_then_append(run,operation,**kwargs):
            claimed=original(run,operation,**kwargs)
            with open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite') as writer:
                writer.ensure_run('other-close',decision.owner_permission,now=self.fixture.clock[0])
                lease=writer.begin_process('other-close','other-close:1',expected_generation=0,now=self.fixture.clock[0])
                unknown=dict(role=role,path='/api/v5/trade/order',native_client_id='OTHERCLOSE',
                    body=dict(instId='BTC-USDT-SWAP',tdMode='isolated',posSide='net',side='sell',ordType='market',
                        sz='10',clOrdId='OTHERCLOSE',reduceOnly=True),canonical_request_hash='sha256:'+'1'*64,authority_hash='sha256:'+'2'*64)
                if role=='ENTRY':
                    unknown['body']['side']='buy';unknown['body'].pop('reduceOnly')
                writer.prepare('other-close','other-close-operation',unknown,lease=lease,now=self.fixture.clock[0])
                writer.claim_dispatch('other-close','other-close-operation',lease=lease,now=self.fixture.clock[0])
            return claimed
        return patch.object(service.dispatch,'claim_dispatch',side_effect=claim_then_append)

    def test_cross_role_claim_appended_after_actual_claim_blocks_final_provider_effect(self):
        context=self.entered();service,provider,*_=context;prepared=self.prepare(context)
        self.append_ack(provider,prepared)
        with self.append_foreign_claim_after_current(service,'EMERGENCY_EXIT'):
            with self.assertRaises(RuntimeAdmissionError) as caught:
                service.execute(prepared,expected_revision=self.fixture.revision)
        self.assertIn('PRIOR_ACCOUNT_CLOSE_RECONCILIATION_REQUIRED',caught.exception.reason_codes)
        self.assertEqual(len(provider.calls),4)
        self.assertEqual(service.dispatch.operation(service.run_id,prepared.canonical_request.order_request_id).recovery_disposition,'READBACK_REQUIRED')

    def test_unknown_entry_appended_after_close_claim_blocks_final_provider_effect(self):
        context=self.entered();service,provider,*_=context;prepared=self.prepare(context)
        self.append_ack(provider,prepared)
        with self.append_foreign_claim_after_current(service,'ENTRY'):
            with self.assertRaises(RuntimeAdmissionError):service.execute(prepared,expected_revision=self.fixture.revision)
        self.assertEqual(len(provider.calls),4)
        self.assertEqual(service.dispatch.operation(service.run_id,prepared.canonical_request.order_request_id).recovery_disposition,'READBACK_REQUIRED')


if __name__=='__main__':unittest.main()
