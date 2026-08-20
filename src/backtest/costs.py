from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

BPS_DENOMINATOR = Decimal("10000")
UTC = timezone.utc

LiquidityRole = Literal["MAKER", "TAKER"]
OrderSide = Literal["BUY", "SELL"]
PositionSide = Literal["LONG", "SHORT"]
Phase = Literal["ENTRY", "EXIT"]


def _decimal(value: Decimal | str | int, field_name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{field_name} must use Decimal/string/integer semantics, not binary float")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - defensive conversion boundary
        raise TypeError(f"{field_name} is not a valid decimal value") from exc


def _utc_datetime(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value.astimezone(UTC)


def _to_z(value: datetime) -> str:
    return _utc_datetime(value, "timestamp").isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class FeeModel:
    """Configurable maker/taker fee assumptions with separate entry/exit roles."""

    version: str
    maker_bps: Decimal
    taker_bps: Decimal
    entry_liquidity_role: LiquidityRole = "TAKER"
    exit_liquidity_role: LiquidityRole = "TAKER"

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("fee model version is required")
        maker = _decimal(self.maker_bps, "maker_bps")
        taker = _decimal(self.taker_bps, "taker_bps")
        if maker <= -BPS_DENOMINATOR or taker <= -BPS_DENOMINATOR:
            raise ValueError("fee rebate cannot be 100% or more of notional")
        if self.entry_liquidity_role not in ("MAKER", "TAKER"):
            raise ValueError("entry_liquidity_role must be MAKER or TAKER")
        if self.exit_liquidity_role not in ("MAKER", "TAKER"):
            raise ValueError("exit_liquidity_role must be MAKER or TAKER")
        object.__setattr__(self, "maker_bps", maker)
        object.__setattr__(self, "taker_bps", taker)

    def fee(self, notional: Decimal, phase: Phase) -> Decimal:
        notional = _decimal(notional, "notional")
        if notional < 0:
            raise ValueError("notional must be non-negative")
        if phase == "ENTRY":
            role = self.entry_liquidity_role
        elif phase == "EXIT":
            role = self.exit_liquidity_role
        else:
            raise ValueError("phase must be ENTRY or EXIT")
        bps = self.maker_bps if role == "MAKER" else self.taker_bps
        return notional * bps / BPS_DENOMINATOR

    def assumptions(self) -> dict[str, str]:
        return {
            "version": self.version,
            "maker_bps": str(self.maker_bps),
            "taker_bps": str(self.taker_bps),
            "entry_liquidity_role": self.entry_liquidity_role,
            "exit_liquidity_role": self.exit_liquidity_role,
        }


@dataclass(frozen=True)
class SlippageModel:
    """Fixed adverse slippage in basis points, separately configurable by phase."""

    version: str
    entry_bps: Decimal
    exit_bps: Decimal

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("slippage model version is required")
        entry = _decimal(self.entry_bps, "entry_bps")
        exit_ = _decimal(self.exit_bps, "exit_bps")
        if entry < 0 or exit_ < 0:
            raise ValueError("slippage bps must be non-negative")
        if entry >= BPS_DENOMINATOR or exit_ >= BPS_DENOMINATOR:
            raise ValueError("slippage bps must remain below 100%")
        object.__setattr__(self, "entry_bps", entry)
        object.__setattr__(self, "exit_bps", exit_)

    def fill_price(self, reference_price: Decimal, order_side: OrderSide, phase: Phase) -> Decimal:
        reference_price = _decimal(reference_price, "reference_price")
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")
        if phase == "ENTRY":
            bps = self.entry_bps
        elif phase == "EXIT":
            bps = self.exit_bps
        else:
            raise ValueError("phase must be ENTRY or EXIT")
        fraction = bps / BPS_DENOMINATOR
        if order_side == "BUY":
            return reference_price * (Decimal("1") + fraction)
        if order_side == "SELL":
            return reference_price * (Decimal("1") - fraction)
        raise ValueError("order_side must be BUY or SELL")

    @staticmethod
    def slippage_cost(reference_price: Decimal, fill_price: Decimal, quantity: Decimal) -> Decimal:
        reference_price = _decimal(reference_price, "reference_price")
        fill_price = _decimal(fill_price, "fill_price")
        quantity = _decimal(quantity, "quantity")
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        return abs(fill_price - reference_price) * quantity

    def assumptions(self) -> dict[str, str]:
        return {
            "version": self.version,
            "entry_bps": str(self.entry_bps),
            "exit_bps": str(self.exit_bps),
            "direction": "ADVERSE",
        }


@dataclass(frozen=True)
class FixedFundingModel:
    """Deterministic fixed-rate funding assumption for Slice 1.

    Positive rates charge LONG and credit SHORT. Negative rates invert that relation.
    A position is considered exposed to a funding event when opened_at <= event < closed_at.
    The notional approximation uses entry fill price * fixed replay quantity.
    """

    version: str
    rate_per_event: Decimal
    interval_seconds: int
    first_event_at: datetime

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("funding model version is required")
        rate = _decimal(self.rate_per_event, "rate_per_event")
        if isinstance(self.interval_seconds, bool) or not isinstance(self.interval_seconds, int):
            raise TypeError("interval_seconds must be an integer")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        anchor = _utc_datetime(self.first_event_at, "first_event_at")
        object.__setattr__(self, "rate_per_event", rate)
        object.__setattr__(self, "first_event_at", anchor)

    def event_count(self, opened_at: datetime, closed_at: datetime) -> int:
        opened_at = _utc_datetime(opened_at, "opened_at")
        closed_at = _utc_datetime(closed_at, "closed_at")
        if closed_at <= opened_at:
            return 0

        event_at = self.first_event_at
        if event_at < opened_at:
            delta = opened_at - event_at
            elapsed_us = (
                delta.days * 86_400_000_000
                + delta.seconds * 1_000_000
                + delta.microseconds
            )
            interval_us = self.interval_seconds * 1_000_000
            steps = (elapsed_us + interval_us - 1) // interval_us
            event_at = event_at + timedelta(seconds=steps * self.interval_seconds)

        count = 0
        while event_at < closed_at:
            count += 1
            event_at = event_at + timedelta(seconds=self.interval_seconds)
        return count

    def cost(
        self,
        position_side: PositionSide,
        quantity: Decimal,
        entry_fill_price: Decimal,
        opened_at: datetime,
        closed_at: datetime,
    ) -> Decimal:
        quantity = _decimal(quantity, "quantity")
        entry_fill_price = _decimal(entry_fill_price, "entry_fill_price")
        if quantity < 0 or entry_fill_price <= 0:
            raise ValueError("funding quantity must be non-negative and price positive")
        count = self.event_count(opened_at, closed_at)
        notional = quantity * entry_fill_price
        raw = notional * self.rate_per_event * Decimal(count)
        if position_side == "LONG":
            return raw
        if position_side == "SHORT":
            return -raw
        raise ValueError("position_side must be LONG or SHORT")

    def assumptions(self) -> dict[str, str | int]:
        return {
            "version": self.version,
            "rate_per_event": str(self.rate_per_event),
            "interval_seconds": self.interval_seconds,
            "first_event_at": _to_z(self.first_event_at),
            "notional_basis": "ENTRY_FILL_PRICE_X_FIXED_QUANTITY",
            "event_window": "OPENED_AT_INCLUSIVE_CLOSED_AT_EXCLUSIVE",
        }
