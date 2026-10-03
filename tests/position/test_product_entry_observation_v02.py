import unittest
from dataclasses import replace
from decimal import Decimal
from datetime import timedelta
import tests.brokers.test_okx_product_translation_v02 as fixtures
from brokers.okx_product_readback import parse_product_order, parse_product_fills
from execution.models import PositionExposureSnapshot
from position.entry_observation import build_entry_projection


class ProductEntryObservationV02Tests(unittest.TestCase):
    def setUp(self):
        helper=fixtures.OKXProductTranslationV02Tests(methodName='runTest'); helper.setUp()
        import tests.execution.test_gateway as gateway_fixtures
        self.plan=gateway_fixtures._approved_plan(helper.now); self.plan['quantity']='0.0105'
        self.prepared=helper.entry(plan=self.plan); self.now=helper.now+timedelta(seconds=2)
        row=dict(self.prepared.materialization.body)
        row.update(instType='SWAP',ordId='1234',state='partially_filled',accFillSz='4',avgPx='60000',reduceOnly=False)
        self.result=parse_product_order(dict(code='0',data=[row]),self.prepared,observed_at=self.now).result
        raw=dict(instId='BTC-USDT-SWAP',clOrdId=self.prepared.materialization.provider_cl_ord_id,
                 ordId='1234',tradeId='1',side='buy',posSide='net',fillSz='4',fillPx='60000',
                 fillTime=str(int(helper.now.timestamp()*1000)),fee='-0.1',feeCcy='USDT')
        self.fills=parse_product_fills(dict(code='0',data=[raw]),self.prepared,expected_provider_id='1234')
        self.position=PositionExposureSnapshot('BTC_USDT_PERP',Decimal('0.004'))

    def produce(self, request=None):
        from position.entry_observation import build_product_entry_projection
        return build_product_entry_projection(self.plan, self.prepared.canonical_request if request is None else request,
            self.result,self.fills,self.position,observed_at=self.now)

    def test_original_strict_paper_profile_still_rejects_a_quantized_request(self):
        with self.assertRaises(ValueError):
            build_entry_projection(self.plan,self.prepared.canonical_request,self.result,self.fills,self.position,observed_at=self.now)

    def test_bounded_product_profile_observes_actual_fill_without_changing_original_approval(self):
        outcome=self.produce()
        self.assertEqual('product-entry-observation-v0.2',outcome.profile)
        current=outcome.projections[-1].lifecycle_projection
        self.assertEqual('OPEN_UNPROTECTED',current['lifecycle_state'])
        self.assertEqual('0.004',current['actual_quantity'])
        self.assertTrue(current['position_id'].startswith('r7pos_'))
        self.assertEqual('0.0105',self.plan['quantity'])
        self.assertEqual(Decimal('0.010'),self.prepared.canonical_request.quantity)

    def test_enlarged_quantity_or_other_changed_authority_fields_are_not_observed(self):
        for changes in (dict(quantity=Decimal('0.011')),dict(trade_plan_id='other'),dict(reduce_only=True),
                        dict(position_action_id='other'),dict(client_order_id='other')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.produce(replace(self.prepared.canonical_request,**changes))


if __name__=='__main__':unittest.main()
