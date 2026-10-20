"""Original finalization refusal scenario; genuine owner flow."""
from dataclasses import replace
from datetime import timedelta
import unittest
from tests.product.trading_finalization_fixtures import FinalizationFixture


class TradingFinalizationTargetKindV02Tests(FinalizationFixture,unittest.TestCase):
    def test_cancel_ack_and_empty_scan_cannot_replace_terminal_target_readback(self):
        self.settled(terminal=False)
        self.assert_denied_without_final_effect(self.final_reads(terminal=False))
