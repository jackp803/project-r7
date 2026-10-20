"""Bounded genuine cleanup regressions: TradingCleanupInventoryV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingCleanupInventoryV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_empty_inventory_or_competing_active_object_is_not_cleanup_authority(self):
        self.flat()
        for empty,extra in ((True,False),(False,True)):
            with self.subTest(empty=empty,extra=extra),self.assertRaises(ValueError):
                self.prepare(self.reads(empty=empty,extra=extra))
        self.assertEqual(self.cancel_calls(),[])

    def test_provider_or_execution_replacement_denies_before_any_cancel(self):
        from application.trading.provider import FakeProductProvider
        self.flat();prepared=self.prepare(self.reads());old=self.service.provider
        self.service.provider=FakeProductProvider([])
        with self.assertRaises(ValueError):self.execute(prepared)
        self.service.provider=old;self.service.execution='PRODUCTION'
        with self.assertRaises(ValueError):self.execute(prepared)
        self.assertEqual(self.cancel_calls(),[])
