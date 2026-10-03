"""Native position facts are data; no ACK, empty response or cache proves flat."""
import importlib
import unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal

import tests.brokers.test_okx_demo_adapter as fixtures


class OKXProductPositionV02Tests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,3,0,0,tzinfo=timezone.utc)
        self.metadata=replace(fixtures._metadata(self.now),ct_val=Decimal('0.0001'))

    def api(self):
        try:return importlib.import_module('brokers.okx_product_position')
        except ModuleNotFoundError:self.fail('Missing native product position observation')

    def response(self,**changes):
        row=dict(instType='SWAP',instId='BTC-USDT-SWAP',mgnMode='isolated',posSide='net',
                 ccy='USDT',posId='5678',pos='4',avgPx='60000',
                 uTime=str(int((self.now-timedelta(hours=1)).timestamp()*1000)))
        row.update(changes);return dict(code='0',data=[row])

    def parse(self,response=None,**kwargs):
        args=dict(metadata=self.metadata,request_started_at=self.now-timedelta(milliseconds=10),received_at=self.now,
                  expected_provider_position_id=None)
        args.update(kwargs)
        return self.api().parse_product_position_response(self.response() if response is None else response,**args)

    def test_signed_contract_conversion_preserves_native_update_and_actual_read_clocks(self):
        value=self.parse()
        self.assertEqual(Decimal('0.0004'),value.exposure.net_quantity)
        self.assertEqual('BTC_USDT_PERP',value.exposure.symbol)
        self.assertEqual(Decimal('60000'),value.average_entry_price)
        self.assertEqual(self.now-timedelta(hours=1),value.provider_updated_at)
        self.assertEqual(self.now,value.received_at)
        self.assertEqual('5678',value.provider_position_id)
        short=self.parse(self.response(pos='-3'))
        self.assertEqual(Decimal('-0.0003'),short.exposure.net_quantity)

    def test_flat_requires_explicit_same_native_position_and_never_empty_or_error_response(self):
        flat=self.parse(self.response(pos='0',avgPx=''),expected_provider_position_id='5678')
        self.assertEqual(Decimal('0'),flat.exposure.net_quantity)
        self.assertIsNone(flat.average_entry_price)
        for response in (dict(code='0',data=[]),dict(code='51000',data=[]),self.response(posId='999',pos='0',avgPx='')):
            with self.subTest(response=response),self.assertRaises(ValueError):
                self.parse(response,expected_provider_position_id='5678')

    def test_unknown_profile_duplicate_rows_decimal_or_future_native_clock_fail_closed(self):
        changes=({'instId':'ETH-USDT-SWAP'},{'instType':'FUTURES'},{'mgnMode':'cross'},
                 {'posSide':'long'},{'ccy':'BTC'},{'posId':'private payload'},{'pos':'NaN'},
                 {'pos':'1e3'},{'pos':True},{'avgPx':'0'},
                 {'uTime':str(int((self.now+timedelta(seconds=1)).timestamp()*1000))},{'uTime':'1.5'})
        for item in changes:
            with self.subTest(item=item),self.assertRaises(ValueError):self.parse(self.response(**item))
        response=self.response();response['data']*=2
        with self.assertRaises(ValueError):self.parse(response)

    def test_read_duration_metadata_age_or_non_utc_clock_cannot_renew_freshness(self):
        for args in (dict(request_started_at=self.now+timedelta(seconds=1)),
                     dict(request_started_at=self.now-timedelta(seconds=31)),
                     dict(received_at=self.now.replace(tzinfo=None)),
                     dict(metadata=replace(self.metadata,observed_at=self.now-timedelta(seconds=6))),
                     dict(metadata=replace(self.metadata,ct_type='inverse'))):
            with self.subTest(args=args),self.assertRaises(ValueError):self.parse(**args)

    def test_exact_position_query_allows_one_native_id_without_expanding_instrument_scope(self):
        from brokers.okx_production_transport import OKXProductionTransportConfig,prepare_production_private_request
        from brokers.okx_demo import OKXCredentials
        config=OKXProductionTransportConfig('https://www.okx.com','https://www.okx.com')
        arguments=dict(config=config,credentials=OKXCredentials('fixture-key','fixture-secret','fixture-passphrase'),
                       method='GET',path='/api/v5/account/positions',timestamp='2026-10-03T00:00:00.000Z')
        request=prepare_production_private_request(**arguments,query=dict(instId='BTC-USDT-SWAP',posId='5678'))
        self.assertEqual('/api/v5/account/positions?instId=BTC-USDT-SWAP&posId=5678',request.request_path)
        for query in (dict(posId='5678'),dict(instId='ETH-USDT-SWAP',posId='5678'),
                      dict(instId='BTC-USDT-SWAP',posId='5678,999'),dict(instId='BTC-USDT-SWAP',posId='')):
            with self.subTest(query=query),self.assertRaises(ValueError):
                prepare_production_private_request(**arguments,query=query)


if __name__=='__main__':unittest.main()
