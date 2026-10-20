"""Missing actual canonical funding must deny finalization."""
import unittest
from tests.product.trading_finalization_fixtures import FinalizationFixture


class TradingFinalizationMissingFundingV02Tests(FinalizationFixture,unittest.TestCase):
    def test_missing_funding_denies_even_actual_terminal_stop_and_original_zero(self):
        self.settled(with_funding=False)
        self.assert_denied_without_final_effect(self.final_reads())
