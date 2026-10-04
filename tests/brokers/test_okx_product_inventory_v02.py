"""Bounded native inventory truth; no page or ACK grants financial authority."""
import importlib
import unittest
from datetime import datetime, timedelta, timezone


class ProductInventoryV02Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 3, tzinfo=timezone.utc)

    def api(self):
        return importlib.import_module('brokers.okx_product_inventory')

    def row(self, native='200', kind='conditional', **changes):
        row = dict(algoId=native, algoClOrdId='R7STOP', instType='SWAP',
                   instId='BTC-USDT-SWAP', ordType=kind, state='live',
                   tdMode='isolated', posSide='net', side='sell', sz='4',
                   reduceOnly='true', slTriggerPx='59400', slOrdPx='-1',
                   slTriggerPxType='last', actualSz='0', ordIdList=[],
                   cTime=str(int((self.now-timedelta(minutes=1)).timestamp()*1000)),
                   uTime=str(int((self.now-timedelta(seconds=1)).timestamp()*1000)))
        row.update(changes)
        return row

    def page(self, rows, **kwargs):
        return self.api().parse_product_algo_page(dict(code='0', data=rows),
            algo_type='conditional', received_at=self.now, **kwargs)

    def test_exact_scope_native_clocks_and_sanitized_immutable_objects(self):
        original=self.row(tag='personal arbitrary tag', unknownField='private arbitrary value')
        result=self.page([original])
        self.assertEqual('200',result[0].provider_algo_id)
        self.assertEqual(self.now-timedelta(seconds=1),result[0].provider_updated_at)
        self.assertNotIn('personal',result[0].row_json)
        self.assertNotIn('private',result[0].row_json)
        original['sz']='9'
        self.assertEqual('4',result[0].row['sz'])
        decoded=result[0].row;decoded['sz']='10'
        self.assertEqual('4',result[0].row['sz'])

    def test_errors_wrong_scope_duplicate_forward_or_invalid_clocks_never_mean_empty(self):
        invalid=[self.row(instId='ETH-USDT-SWAP'),self.row(instType='SPOT'),
                 self.row(ordType='oco'),self.row(state='effective'),self.row(algoId=''),
                 self.row(cTime='NaN'),self.row(uTime=str(int((self.now+timedelta(seconds=1)).timestamp()*1000))),
                 self.row(uTime='1'),self.row(algoClOrdId=[]),self.row(algoClOrdId='x'*33)]
        for row in invalid:
            with self.subTest(row=row),self.assertRaises(ValueError):self.page([row])
        with self.assertRaises(ValueError):self.page([self.row(),self.row()])
        with self.assertRaises(ValueError):
            self.api().parse_product_algo_page(dict(code='50000',data=[]),algo_type='conditional',received_at=self.now)
        self.assertEqual((),self.page([]))

    def test_cursor_order_and_bounded_pages_reject_overlap_without_dropping_rows(self):
        self.assertEqual(2,len(self.page([self.row('199'),self.row('198')],after='200')))
        for rows in ([self.row('201')],[self.row('200')],[self.row('198'),self.row('199')],
                     [self.row(str(500-i)) for i in range(101)]):
            with self.subTest(rows=len(rows)),self.assertRaises(ValueError):self.page(rows,after='200')

    def test_all_documented_algo_types_are_read_only_transport_scopes(self):
        from brokers.okx_production_transport import _query
        self.assertEqual(('conditional','oco','chase','trigger','move_order_stop',
                          'iceberg','twap','smart_iceberg'),self.api().ALGO_TYPES)
        for kind in self.api().ALGO_TYPES:
            _query('/api/v5/trade/orders-algo-pending',dict(instId='BTC-USDT-SWAP',ordType=kind,limit='100'))
        for kind in ('conditional,oco','unknown','market'):
            with self.assertRaises(ValueError):
                _query('/api/v5/trade/orders-algo-pending',dict(instId='BTC-USDT-SWAP',ordType=kind))

    def test_external_shapes_remain_observed_and_do_not_become_supported_stops(self):
        row=self.row(tdMode='cross',posSide='long',reduceOnly='false',slTriggerPx='',slOrdPx='')
        observed=self.page([row])[0]
        self.assertEqual('cross',observed.row['tdMode'])
        self.assertEqual('false',observed.row['reduceOnly'])
        self.assertNotEqual(self.page([self.row()])[0].source_hash,observed.source_hash)


if __name__=='__main__':unittest.main()
