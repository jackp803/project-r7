from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

SCHEMA_VERSION = "contracts-v0.1"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class ExecutionHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class OrderRequest:
    schema_version: str
    order_request_id: str
    trade_plan_id: str
    client_order_id: str
    symbol: str
    side: Side
    order_type: str
    quantity: Decimal
    quantity_profile_version: str
    quantity_unit: str
    quantity_asset: str
    created_at: datetime
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    reduce_only: bool | None = None
    time_in_force: str | None = None

    def safety_fingerprint(self) -> tuple[object, ...]:
        """Fields that must not change for one idempotent logical order."""
        return (
            self.trade_plan_id,
            self.client_order_id,
            self.symbol,
            self.side,
            self.order_type,
            self.quantity,
            self.quantity_profile_version,
            self.quantity_unit,
            self.quantity_asset,
            self.limit_price,
            self.stop_price,
            self.reduce_only,
            self.time_in_force,
        )


@dataclass(frozen=True)
class OrderResult:
    schema_version: str
    order_request_id: str
    client_order_id: str
    broker_order_id: str | None
    order_status: OrderStatus
    observed_at: datetime
    execution_health_status: ExecutionHealthStatus
    requested_quantity: Decimal
    filled_quantity: Decimal
    average_fill_price: Decimal | None = None
    reject_reason: str | None = None


@dataclass(frozen=True)
class Fill:
    schema_version: str
    fill_id: str
    broker_order_id: str
    client_order_id: str
    trade_plan_id: str
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
    filled_at: datetime
    fee: Decimal | None = None
    fee_currency: str | None = None
    liquidity_role: str | None = None


@dataclass(frozen=True)
class PositionExposureSnapshot:
    symbol: str
    net_quantity: Decimal


@dataclass(frozen=True)
class ReconciliationResult:
    client_order_id: str
    resolved_status: OrderStatus
    retry_allowed: bool
    reason: str
    retry_token: str | None = None


def require_utc(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{field} must be timezone-aware UTC")


def stable_client_order_id(trade_plan_id: str, logical_order_key: str) -> str:
    """Stable idempotency identity for one logical order under one approved plan."""
    material = f"{trade_plan_id}\x1f{logical_order_key}".encode("utf-8")
    return "e4_" + hashlib.sha256(material).hexdigest()[:32]


def stable_order_request_id(client_order_id: str) -> str:
    return "ordreq_" + hashlib.sha256(client_order_id.encode("utf-8")).hexdigest()[:32]
