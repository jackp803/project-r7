"""Pure E5 source fixtures; no native provider, funding or LIVE qualification."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import importlib
import unittest

from brokers.paper import PaperBroker
from execution.close import prepare_close_order
from execution.gateway import ExecutionGateway
from execution.models import PositionExposureSnapshot,Side
from position import authorize_close_position_action
from position.entry_observation import build_product_entry_projection
from position.lifecycle_execution_binding import validate_position_lifecycle_execution_evidence_binding
from tests.storage.test_paper_runtime_durability import approved_plan


NOW=datetime(2026,8,24,7,0,10,tzinfo=timezone.utc)


class ProductCloseObservationTests(unittest.TestCase):
    def api(self):
        return importlib.import_module('position.close_observation').build_product_close_projection

    def actual(self,side='LONG'):
        plan=approved_plan();plan['direction']=side
        if side=='SHORT':plan['protection_instruction'].update(stop_level='60600',target_level='58800')
        broker=PaperBroker()
        entry=ExecutionGateway().prepare_entry_order(plan,now=NOW-timedelta(seconds=1))
        broker.submit_order(entry)
        broker.record_fill(entry.client_order_id,quantity=entry.quantity,price=Decimal('60000'),filled_at=NOW)
        entry_result=broker.query_order(entry.client_order_id);entries=broker.query_fills(entry.client_order_id)
        source=build_product_entry_projection(plan,entry,entry_result,entries,broker.query_position(entry.symbol),
            observed_at=NOW).projections[-1].lifecycle_projection
        authority=authorize_close_position_action(source,plan,action='EXIT',created_at=NOW+timedelta(seconds=1),
            expires_at=NOW+timedelta(seconds=31)).position_action
        close=prepare_close_order(authority,plan,source,now=NOW+timedelta(seconds=1))
        broker.submit_order(close)
        broker.record_fill(close.client_order_id,quantity=Decimal('.001'),price=Decimal('60100'),filled_at=NOW+timedelta(seconds=2))
        arguments=dict(plan=plan,authority=authority,entry_request=entry,entry_result=entry_result,entry_fills=entries,
            exit_request=close,exit_result=broker.query_order(close.client_order_id),exit_fills=broker.query_fills(close.client_order_id),
            position_snapshot=broker.query_position(close.symbol),source_position=source,previous_projection=source,
            observed_at=NOW+timedelta(seconds=2))
        return broker,arguments

    def test_actual_partial_then_flat_preserves_first_fill_and_never_finalizes_closed(self):
        build=self.api()
        for side in ('LONG','SHORT'):
            with self.subTest(side=side):
                broker,args=self.actual(side);first=build(**args)
                partial=first.projections[-1].lifecycle_projection
                self.assertEqual(first.profile,'product-close-observation-v0.2')
                self.assertEqual((partial['actual_quantity'],partial['lifecycle_state']),('0.002','EXIT_REQUESTED'))
                self.assertEqual(partial['opened_at'],args['source_position']['opened_at'])
                self.assertEqual(partial['average_entry_price'],'60000')
                self.assertEqual(partial['position_id'],args['source_position']['position_id'])
                close=args['exit_request'];at=NOW+timedelta(seconds=3)
                broker.record_fill(close.client_order_id,quantity=Decimal('.002'),price=Decimal('60200'),filled_at=at)
                later=dict(args,previous_projection=partial,exit_result=broker.query_order(close.client_order_id),
                    exit_fills=broker.query_fills(close.client_order_id),position_snapshot=broker.query_position(close.symbol),observed_at=at)
                final=build(**later).projections[-1]
                self.assertEqual((final.lifecycle_projection['actual_quantity'],final.lifecycle_projection['lifecycle_state']),('0.000','EXIT_REQUESTED'))
                self.assertEqual(final.lifecycle_projection['lifecycle_projection_kind'],'REATTESTATION')
                self.assertNotIn('closed_at',final.lifecycle_projection)
                validate_position_lifecycle_execution_evidence_binding(final.execution_binding,final.lifecycle_projection)

    def test_ack_or_filled_without_actual_fills_and_mismatched_native_residual_are_denied(self):
        build=self.api();_,args=self.actual()
        for changed in (dict(exit_fills=()),dict(position_snapshot=PositionExposureSnapshot('BTC_USDT_PERP',Decimal('0'))),
                        dict(exit_result=replace(args['exit_result'],filled_quantity=Decimal('.003')))):
            with self.subTest(changed=tuple(changed)),self.assertRaises(ValueError):build(**dict(args,**changed))

    def test_exit_lineage_duplicates_nonfinite_and_overclose_are_denied(self):
        build=self.api();_,args=self.actual();fill=args['exit_fills'][0]
        for changed in (dict(trade_plan_id='foreign'),dict(client_order_id='foreign'),dict(broker_order_id='foreign'),
                        dict(position_id='foreign'),dict(position_action_id='foreign'),dict(order_role='ENTRY'),
                        dict(side=Side.BUY),dict(symbol='foreign'),dict(quantity=Decimal('0')),
                        dict(quantity=Decimal('NaN')),dict(price=Decimal('Infinity')),dict(price=Decimal('-1')),
                        dict(quantity=Decimal('.004')),dict(filled_at=NOW),dict(filled_at=NOW+timedelta(seconds=3))):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                build(**dict(args,exit_fills=(replace(fill,**changed),)))
        with self.assertRaises(ValueError):build(**dict(args,exit_fills=(fill,fill)))
        with self.assertRaises(ValueError):build(**dict(args,exit_fills=(*args['exit_fills'],args['entry_fills'][0])))

    def test_source_identity_entry_basis_and_authority_are_not_caller_replaceable(self):
        build=self.api();_,args=self.actual()
        for key,value in (('position_id','foreign'),('average_entry_price','61000'),('actual_quantity','0.004'),
                          ('opened_at','2026-08-24T07:00:09Z')):
            with self.subTest(key=key),self.assertRaises(ValueError):
                build(**dict(args,source_position=dict(args['source_position'],**{key:value})))
        with self.assertRaises(ValueError):build(**dict(args,authority=dict(args['authority'],quantity='0.004')))
        with self.assertRaises(ValueError):build(**dict(args,exit_request=replace(args['exit_request'],reduce_only=False)))
        with self.assertRaises(ValueError):build(**dict(args,entry_fills=(replace(args['entry_fills'][0],price=Decimal('61000')),)))

    def test_clock_regression_equal_time_conflict_and_residual_increase_are_denied(self):
        build=self.api();_,args=self.actual();partial=build(**args).projections[-1].lifecycle_projection
        with self.assertRaises(ValueError):build(**dict(args,observed_at=NOW+timedelta(seconds=1)))
        with self.assertRaises(ValueError):build(**dict(args,previous_projection=partial,exit_fills=()))
        earlier=dict(args,exit_fills=(replace(args['exit_fills'][0],quantity=Decimal('.0005')),),
            exit_result=replace(args['exit_result'],filled_quantity=Decimal('.0005')),
            position_snapshot=PositionExposureSnapshot('BTC_USDT_PERP',Decimal('.0025')))
        for at in (args['observed_at'],args['observed_at']+timedelta(seconds=1)):
            with self.subTest(at=at),self.assertRaises(ValueError):build(**dict(earlier,previous_projection=partial,observed_at=at))

    def test_later_read_does_not_retrospectively_expire_executed_close_authority(self):
        build=self.api();_,args=self.actual()
        current=build(**dict(args,observed_at=NOW+timedelta(seconds=60))).projections[-1].lifecycle_projection
        self.assertEqual(current['lifecycle_state'],'EXIT_REQUESTED')
        self.assertEqual(current['actual_quantity'],'0.002')

    def test_close_request_and_fill_cannot_predate_original_action_creation(self):
        build=self.api();_,args=self.actual()
        # Deliberately corrupt only typed historical clocks from actual owner
        # facts; the former E4 consumer also allowed producing this request.
        with self.assertRaises(ValueError):
            build(**dict(args,exit_request=replace(args['exit_request'],created_at=NOW),
                exit_fills=tuple(replace(fill,filled_at=NOW) for fill in args['exit_fills'])))

    def test_same_inputs_are_deterministic_and_do_not_mutate_authoritative_facts(self):
        from copy import deepcopy
        build=self.api();_,args=self.actual();before=deepcopy(args)
        self.assertEqual(build(**args),build(**args))
        self.assertEqual(args,before)

    def test_unknown_fees_do_not_hide_exposure_and_input_is_bounded(self):
        build=self.api();_,args=self.actual();fill=args['exit_fills'][0]
        outcome=build(**dict(args,exit_fills=(replace(fill,fee=None,fee_currency=None),)))
        self.assertEqual(outcome.projections[-1].lifecycle_projection['actual_quantity'],'0.002')
        with self.assertRaises(ValueError):build(**dict(args,exit_fills=(fill,)*100_001))

    def test_complete_fill_permutation_keeps_the_same_projection_and_binding(self):
        build=self.api();broker,args=self.actual();request=args['exit_request'];at=NOW+timedelta(seconds=3)
        broker.record_fill(request.client_order_id,quantity=Decimal('.002'),price=Decimal('60200'),filled_at=at)
        current=dict(args,exit_result=broker.query_order(request.client_order_id),exit_fills=broker.query_fills(request.client_order_id),
            position_snapshot=broker.query_position(request.symbol),observed_at=at)
        self.assertEqual(build(**current),build(**dict(current,exit_fills=tuple(reversed(current['exit_fills'])))))


if __name__=='__main__':unittest.main()
