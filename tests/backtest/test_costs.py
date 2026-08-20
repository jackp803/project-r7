from datetime import datetime, timezone
from decimal import Decimal
import unittest

from src.backtest.costs import FeeModel, FixedFundingModel, SlippageModel

UTC = timezone.utc


class CostModelTests(unittest.TestCase):
    def test_fee_model_supports_entry_exit_roles(self) -> None:
        model = FeeModel(
            version="fee-test-v1",
            maker_bps=Decimal("1"),
            taker_bps=Decimal("5"),
            entry_liquidity_role="TAKER",
            exit_liquidity_role="MAKER",
        )
        self.assertEqual(model.fee(Decimal("1000"), "ENTRY"), Decimal("0.5"))
        self.assertEqual(model.fee(Decimal("1000"), "EXIT"), Decimal("0.1"))

    def test_slippage_is_adverse_for_buy_and_sell(self) -> None:
        model = SlippageModel(
            version="slippage-test-v1",
            entry_bps=Decimal("10"),
            exit_bps=Decimal("10"),
        )
        self.assertEqual(
            model.fill_price(Decimal("100"), "BUY", "ENTRY"), Decimal("100.100")
        )
        self.assertEqual(
            model.fill_price(Decimal("100"), "SELL", "EXIT"), Decimal("99.900")
        )

    def test_fixed_funding_counts_only_events_while_position_is_open(self) -> None:
        model = FixedFundingModel(
            version="funding-test-v1",
            rate_per_event=Decimal("0.0001"),
            interval_seconds=8 * 60 * 60,
            first_event_at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        )
        opened = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        closed = datetime(2026, 1, 2, 1, 0, tzinfo=UTC)
        self.assertEqual(model.event_count(opened, closed), 3)
        self.assertEqual(
            model.cost("LONG", Decimal("1"), Decimal("1000"), opened, closed),
            Decimal("0.3000"),
        )
        self.assertEqual(
            model.cost("SHORT", Decimal("1"), Decimal("1000"), opened, closed),
            Decimal("-0.3000"),
        )


if __name__ == "__main__":
    unittest.main()
