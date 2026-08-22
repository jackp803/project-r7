from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence


ZERO = Decimal("0")


def _read(trade: Any, field_name: str) -> Any:
    if isinstance(trade, Mapping):
        return trade[field_name]
    return getattr(trade, field_name)


def _decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{field_name} must not use binary float")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class MetricsSummary:
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fees: Decimal
    total_slippage_cost: Decimal
    total_funding_cost: Decimal
    profit_factor: Decimal | None
    expectancy: Decimal
    max_drawdown: Decimal
    max_consecutive_losses: int

    def to_contract_fields(self) -> dict[str, int | str | None]:
        return {
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "breakeven": self.breakeven,
            "win_rate": str(self.win_rate),
            "average_win": str(self.average_win),
            "average_loss": str(self.average_loss),
            "gross_pnl": str(self.gross_pnl),
            "net_pnl": str(self.net_pnl),
            "total_fees": str(self.total_fees),
            "total_slippage_cost": str(self.total_slippage_cost),
            "total_funding_cost": str(self.total_funding_cost),
            "profit_factor": None if self.profit_factor is None else str(self.profit_factor),
            "expectancy": str(self.expectancy),
            "max_drawdown": str(self.max_drawdown),
            "max_consecutive_losses": self.max_consecutive_losses,
        }


def calculate_metrics(trades: Sequence[Any]) -> MetricsSummary:
    total = len(trades)
    net_values = [_decimal(_read(trade, "net_pnl"), "net_pnl") for trade in trades]
    gross_values = [_decimal(_read(trade, "gross_pnl"), "gross_pnl") for trade in trades]
    fee_values = [_decimal(_read(trade, "total_fees"), "total_fees") for trade in trades]
    slippage_values = [
        _decimal(_read(trade, "slippage_cost"), "slippage_cost") for trade in trades
    ]
    funding_values = [
        _decimal(_read(trade, "funding_cost"), "funding_cost") for trade in trades
    ]

    positives = [value for value in net_values if value > ZERO]
    negatives = [value for value in net_values if value < ZERO]
    wins = len(positives)
    losses = len(negatives)
    breakeven = total - wins - losses

    gross_profit = sum(positives, ZERO)
    gross_loss_abs = abs(sum(negatives, ZERO))
    if gross_loss_abs == ZERO:
        profit_factor = None
    else:
        profit_factor = gross_profit / gross_loss_abs

    win_rate = ZERO if total == 0 else Decimal(wins) / Decimal(total)
    average_win = ZERO if wins == 0 else gross_profit / Decimal(wins)
    average_loss = ZERO if losses == 0 else sum(negatives, ZERO) / Decimal(losses)
    net_pnl = sum(net_values, ZERO)
    expectancy = ZERO if total == 0 else net_pnl / Decimal(total)

    equity = ZERO
    peak = ZERO
    max_drawdown = ZERO
    current_loss_streak = 0
    max_loss_streak = 0
    for value in net_values:
        equity += value
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        if value < ZERO:
            current_loss_streak += 1
            if current_loss_streak > max_loss_streak:
                max_loss_streak = current_loss_streak
        else:
            current_loss_streak = 0

    return MetricsSummary(
        total_trades=total,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=win_rate,
        average_win=average_win,
        average_loss=average_loss,
        gross_pnl=sum(gross_values, ZERO),
        net_pnl=net_pnl,
        total_fees=sum(fee_values, ZERO),
        total_slippage_cost=sum(slippage_values, ZERO),
        total_funding_cost=sum(funding_values, ZERO),
        profit_factor=profit_factor,
        expectancy=expectancy,
        max_drawdown=max_drawdown,
        max_consecutive_losses=max_loss_streak,
    )
