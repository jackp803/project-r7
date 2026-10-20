"""Bounded genuine cleanup regressions: TradingCleanupRacesV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingCleanupRacesV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_actual_second_connection_append_at_claim_writer_blocks_claim_and_cancel(self):
        self.flat();prepared=self.prepare(self.reads());original=self.service.dispatch.claim_stop_cleanup
        def append_then_claim(*args,**kwargs):
            self.append_unknown_entry();return original(*args,**kwargs)
        with patch.object(self.service.dispatch,'claim_stop_cleanup',side_effect=append_then_claim):
            with self.assertRaises(ValueError):self.execute(prepared)
        self.assertIsNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])

    def test_actual_second_connection_append_after_claim_blocks_final_provider_guard(self):
        self.flat();prepared=self.prepare(self.reads());original=self.service.dispatch.claim_stop_cleanup
        def claim_then_append(*args,**kwargs):
            claimed=original(*args,**kwargs);self.append_unknown_entry();return claimed
        with patch.object(self.service.dispatch,'claim_stop_cleanup',side_effect=claim_then_append):
            with self.assertRaises(ValueError):self.execute(prepared)
        self.assertIsNotNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,prepared.stop_operation_id))
        self.assertEqual(self.cancel_calls(),[])
