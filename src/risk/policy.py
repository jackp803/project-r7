from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskPolicy:
    """Versioned E5 policy inputs.

    No capital-risk values are defaulted here. The caller must supply an explicit
    policy version and every limit before an approval can be produced.
    """

    version: str
    max_margin: Decimal
    max_notional: Decimal
    max_leverage: Decimal
    min_reward_risk: Decimal
    max_estimated_cost: Decimal
    max_trades_per_day: int
    max_open_positions: int
    max_drawdown: Decimal
    max_consecutive_losses: int
    max_intent_age_seconds: int
    max_hold_seconds: int
    plan_ttl_seconds: int
    margin_mode: str

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("risk policy version must be non-empty")
        for field_name in (
            "max_margin",
            "max_notional",
            "max_leverage",
            "min_reward_risk",
            "max_estimated_cost",
            "max_drawdown",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ValueError(f"{field_name} must be a finite non-negative Decimal")
        if self.max_margin <= 0 or self.max_notional <= 0 or self.max_leverage <= 0:
            raise ValueError("margin, notional, and leverage caps must be positive")
        if self.min_reward_risk <= 0:
            raise ValueError("minimum reward/risk must be positive")
        for field_name in (
            "max_trades_per_day",
            "max_open_positions",
            "max_consecutive_losses",
            "max_intent_age_seconds",
            "max_hold_seconds",
            "plan_ttl_seconds",
        ):
            value = getattr(self, field_name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if not self.margin_mode.strip():
            raise ValueError("margin_mode must be non-empty")
