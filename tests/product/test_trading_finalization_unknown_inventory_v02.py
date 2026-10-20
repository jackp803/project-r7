"""Original finalization refusal scenario; genuine owner flow."""
from dataclasses import replace
from datetime import timedelta
import unittest
from tests.product.trading_finalization_fixtures import FinalizationFixture


class TradingFinalizationUnknownInventoryV02Tests(FinalizationFixture,unittest.TestCase):
    def test_unknown_active_inventory_denies_even_terminal_owned_target(self):
        self.settled()
        self.assert_denied_without_final_effect(self.final_reads(unknown_active=True))
