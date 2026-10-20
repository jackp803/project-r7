"""Bounded genuine cleanup regressions: TradingCleanupExpiryV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingCleanupExpiryV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_copied_expired_native_nonzero_or_unowned_inventory_cannot_cancel(self):
        self.flat();reads=self.reads();stop,native,inventory,metadata,proof=reads
        for bad in ((replace(stop),native,inventory,metadata,proof),(stop,replace(native),inventory,metadata,proof),
                (stop,native,replace(inventory),metadata,proof)):
            with self.subTest(source=type(bad[0])),self.assertRaises(ValueError):self.prepare(bad)
        prepared=self.prepare(reads)
        with self.assertRaises(ValueError):self.execute(replace(prepared))
        self.fixture.clock[0]+=timedelta(seconds=6)
        with self.assertRaises(ValueError):self.execute(prepared)
        self.assertEqual(self.cancel_calls(),[])

    def test_reads_expiring_during_actual_post_guard_preserve_claim_without_cancel(self):
        import application.trading.stop_cleanup as cleanup
        self.flat();prepared=self.prepare(self.reads())
        self.fixture.clock[0]+=timedelta(seconds=4.9)
        self.flow.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
        original_request=self.provider.request;original_context=cleanup._context
        inside_post=[False];advanced=[False]
        def request(method,path,**kwargs):
            inside_post[0]=method=='POST' and path=='/api/v5/trade/cancel-algos'
            try:return original_request(method,path,**kwargs)
            finally:inside_post[0]=False
        def context(*args,**kwargs):
            value=original_context(*args,**kwargs)
            if inside_post[0] and not advanced[0]:
                self.fixture.clock[0]+=timedelta(seconds=0.2);advanced[0]=True
            return value
        denied=None
        with patch.object(self.provider,'request',side_effect=request),patch.object(cleanup,'_context',side_effect=context):
            try:self.execute(prepared)
            except ValueError as error:denied=error
        self.assertTrue(advanced[0],'Cross the boundary inside the actual provider final guard')
        self.assertIsNotNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])
        self.assertIsNotNone(denied)
