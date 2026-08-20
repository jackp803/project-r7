from decimal import Decimal
from types import SimpleNamespace
import unittest

from src.backtest.metrics import calculate_metrics


def trade(*, gross: str, net: str, fees: str, slippage: str, funding: str):
    return SimpleNamespace(
        gross_pnl=Decimal(gross),
        net_pnl=Decimal(net),
        total_fees=Decimal(fees),
        slippage_cost=Decimal(slippage),
        funding_cost=Decimal(funding),
    )


class MetricsTests(unittest.TestCase):
    def test_known_trade_sequence_metrics(self) -> None:
        summary = calculate_metrics(
            [
                trade(gross="12", net="10", fees="2", slippage="1", funding="0"),
                trade(gross="-4", net="-5", fees="1", slippage="0.5", funding="0"),
                trade(gross="-1", net="-2", fees="1", slippage="0", funding="0"),
                trade(gross="0", net="0", fees="0", slippage="0", funding="0"),
            ]
        )
        self.assertEqual(summary.total_trades, 4)
        self.assertEqual(summary.wins, 1)
        self.assertEqual(summary.losses, 2)
        self.assertEqual(summary.breakeven, 1)
        self.assertEqual(summary.win_rate, Decimal("0.25"))
        self.assertEqual(summary.profit_factor, Decimal("10") / Decimal("7"))
        self.assertEqual(summary.expectancy, Decimal("0.75"))
        self.assertEqual(summary.max_drawdown, Decimal("7"))
        self.assertEqual(summary.max_consecutive_losses, 2)
        self.assertEqual(summary.net_pnl, Decimal("3"))
        self.assertEqual(summary.gross_pnl, Decimal("7"))
        self.assertEqual(summary.total_fees, Decimal("4"))
        self.assertEqual(summary.total_slippage_cost, Decimal("1.5"))

    def test_profit_factor_field_is_null_when_losing_pnl_is_zero_with_a_winner(self) -> None:
        summary = calculate_metrics(
            [
                trade(gross="10", net="8", fees="2", slippage="1", funding="0"),
                trade(gross="0", net="0", fees="0", slippage="0", funding="0"),
            ]
        )

        self.assertEqual(summary.wins, 1)
        self.assertEqual(summary.losses, 0)
        self.assertGreater(summary.net_pnl, Decimal("0"))
        self.assertIsNone(summary.profit_factor)

        contract_fields = summary.to_contract_fields()
        self.assertIn("profit_factor", contract_fields)
        self.assertIsNone(contract_fields["profit_factor"])

    def test_empty_metrics_are_defined_without_fake_profit_factor(self) -> None:
        summary = calculate_metrics([])
        self.assertEqual(summary.total_trades, 0)
        self.assertEqual(summary.expectancy, Decimal("0"))
        self.assertEqual(summary.max_drawdown, Decimal("0"))
        self.assertIsNone(summary.profit_factor)


if __name__ == "__main__":
    unittest.main()
