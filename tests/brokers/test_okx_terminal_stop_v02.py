"""Terminal target facts stay separate from the live-only inventory parser."""
from datetime import timedelta
import json
import unittest

import tests.brokers.test_okx_product_readback_v02 as readback_fixtures
from registry.product_assessment import digest


class OKXTerminalStopV02Tests(unittest.TestCase):
    def setUp(self):
        self.helper=readback_fixtures.OKXProductReadbackV02Tests(methodName='runTest')
        self.prepared,self.now=self.helper.stop()

    def response(self,**changes):
        created=str(int((self.now-timedelta(seconds=1)).timestamp()*1000))
        updated=str(int(self.now.timestamp()*1000))
        return self.helper.algo(self.prepared,state='canceled',cTime=created,uTime=updated,**changes)

    def parse(self,response):
        from brokers.okx_terminal_stop import parse_product_terminal_stop
        return parse_product_terminal_stop(response,self.prepared,received_at=self.now,expected_provider_id='2345')

    def test_exact_canceled_original_target_preserves_broker_clocks_and_full_row_hash(self):
        response=self.response();value=self.parse(response)
        self.assertEqual('CANCELED',value.status)
        self.assertEqual('2345',value.provider_algo_id)
        self.assertEqual(self.now-timedelta(seconds=1),value.provider_created_at)
        self.assertEqual(self.now,value.provider_updated_at)
        self.assertEqual(self.now,value.received_at)
        self.assertEqual(response['data'][0],json.loads(value.row_json))
        raw=json.dumps(response['data'][0],sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
        self.assertEqual(digest(raw),value.source_hash)
        response['data'][0]['state']='live'
        self.assertEqual('canceled',json.loads(value.row_json)['state'])
        from brokers.okx_product_inventory import parse_product_algo_page
        with self.assertRaises(ValueError):
            parse_product_algo_page(self.response(),algo_type='conditional',received_at=self.now)

    def test_ack_absence_live_triggered_failed_or_filled_stop_never_proves_clean_terminal(self):
        responses=[dict(code='0',data=[]),dict(code='51000',data=[]),
            dict(code='0',data=[dict(algoId='2345',sCode='0')])]
        for change in (dict(state='live'),dict(state='effective',ordIdList=['3456'],ordId='3456'),
                       dict(actualSz='1'),dict(ordIdList=['3456'],ordId='3456'),dict(failCode='51000'),
                       dict(algoId='9999'),dict(slTriggerPxType='mark')):
            response=self.response();response['data'][0].update(change);responses.append(response)
        for response in responses:
            with self.subTest(response=response),self.assertRaises(ValueError):self.parse(response)

    def test_missing_future_inverted_or_unbounded_material_is_rejected(self):
        for change in (dict(uTime=''),dict(cTime=''),dict(uTime='abc'),
                       dict(uTime=str(int((self.now+timedelta(seconds=1)).timestamp()*1000))),
                       dict(cTime=str(int((self.now+timedelta(seconds=1)).timestamp()*1000))),
                       dict(uTime=str(int((self.now-timedelta(seconds=2)).timestamp()*1000))),
                       dict(unrecognized='x'*65536)):
            response=self.response();response['data'][0].update(change)
            with self.subTest(change=next(iter(change))),self.assertRaises(ValueError):self.parse(response)
        response=self.response();response['data'].append(dict(response['data'][0]))
        with self.assertRaises(ValueError):self.parse(response)
