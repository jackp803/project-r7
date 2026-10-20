"""Bounded genuine cleanup regressions: TradingStopCleanupV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingStopCleanupV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_one_exact_target_cancel_ack_leaves_original_stop_unsettled_and_duplicate_never_resends(self):
        self.flat();reads=self.reads();before=self.flow.recover();prepared=self.prepare(reads)
        self.assertEqual(self.flow.recover(),before);self.assertEqual(self.cancel_calls(),[])
        self.flow.append(dict(code='0',data=[dict(algoId='2345',sCode='0')]))
        outcome=self.execute(prepared)
        self.assertEqual(outcome.status,'CLEANUP_READBACK_REQUIRED')
        self.assertEqual(self.execute(prepared),outcome)
        self.assertEqual(self.execute(self.prepare(self.reads())),outcome)
        calls=self.cancel_calls();self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['method'],'POST');self.assertEqual(calls[0]['body'],[dict(instId='BTC-USDT-SWAP',algoId='2345')])
        after=self.flow.recover();self.assertEqual(after,before)
        self.assertIsNone(after.trade_result);self.assertEqual(after.current_position_projection.payload['lifecycle_state'],'EXIT_REQUESTED')

    def test_before_original_flat_cleanup_refuses_without_cancel(self):
        with self.assertRaises(ValueError):self.prepare(self.reads(net='10'))
        self.assertEqual(self.cancel_calls(),[])
