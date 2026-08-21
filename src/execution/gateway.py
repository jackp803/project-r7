from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Protocol

from .models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderResult,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)

ENTRY_PROFILE_VERSION = "entry-v0.1"
ENTRY_ORDER_TYPE = "MARKET"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
QUANTITY_ASSET = "BTC"
CANONICAL_SYMBOL = "BTC_USDT_PERP"


class AuthorityBoundaryError(ValueError):
    pass


class ContractMismatchError(ValueError):
    pass


@dataclass(frozen=True)
class TranslatedEntryInstruction:
    order_type: str
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    reduce_only: bool | None = None
    time_in_force: str | None = None


class BrokerSubmitter(Protocol):
    def submit_order(self, request: OrderRequest) -> OrderResult:
        ...


_REQUIRED_PLAN_FIELDS = {
    "schema_version",
    "trade_plan_id",
    "risk_decision_id",
    "intent_id",
    "strategy_id",
    "strategy_version",
    "symbol",
    "direction",
    "quantity",
    "quantity_profile_version",
    "quantity_unit",
    "quantity_asset",
    "leverage",
    "margin_mode",
    "entry_instruction",
    "protection_instruction",
    "created_at",
    "expires_at",
    "risk_policy_version",
}

_ALLOWED_ENTRY_FIELDS = {"profile_version", "order_type", "reference_price"}
_FORBIDDEN_EXECUTABLE_ENTRY_FIELDS = {
    "limit_price",
    "stop_price",
    "trigger_price",
    "time_in_force",
}


def _parse_decimal(value: Any, field: str) -> Decimal:
    if not isinstance(value, str):
        raise AuthorityBoundaryError(f"{field} must be a base-10 decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise AuthorityBoundaryError(f"{field} is not a valid decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise AuthorityBoundaryError(f"{field} must be finite and > 0")
    return parsed


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AuthorityBoundaryError(f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AuthorityBoundaryError(f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise AuthorityBoundaryError(f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def validate_approved_trade_plan(plan: Mapping[str, Any], *, now: datetime) -> None:
    """Fail closed unless input is the current executable ApprovedTradePlan profile."""
    if not isinstance(plan, Mapping):
        raise AuthorityBoundaryError("execution input must be an ApprovedTradePlan mapping")
    missing = sorted(_REQUIRED_PLAN_FIELDS - set(plan.keys()))
    if missing:
        raise AuthorityBoundaryError(
            "execution accepts only profiled ApprovedTradePlan; missing required fields: "
            + ", ".join(missing)
        )
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityBoundaryError("unsupported ApprovedTradePlan schema_version")
    if plan.get("symbol") != CANONICAL_SYMBOL:
        raise AuthorityBoundaryError("unsupported canonical symbol for current E4 execution profile")
    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise AuthorityBoundaryError("ApprovedTradePlan direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise AuthorityBoundaryError("unsupported quantity_profile_version")
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise AuthorityBoundaryError("unsupported quantity_unit")
    if plan.get("quantity_asset") != QUANTITY_ASSET:
        raise AuthorityBoundaryError("unsupported quantity_asset")

    for field in (
        "trade_plan_id",
        "risk_decision_id",
        "intent_id",
        "strategy_id",
        "strategy_version",
        "symbol",
        "margin_mode",
        "risk_policy_version",
    ):
        value = plan.get(field)
        if not isinstance(value, str) or not value.strip():
            raise AuthorityBoundaryError(f"ApprovedTradePlan {field} must be non-empty")

    _parse_decimal(plan.get("quantity"), "quantity")
    _parse_decimal(plan.get("leverage"), "leverage")
    if not isinstance(plan.get("entry_instruction"), Mapping):
        raise AuthorityBoundaryError("entry_instruction must be a mapping")
    if not isinstance(plan.get("protection_instruction"), Mapping):
        raise AuthorityBoundaryError("protection_instruction must be a mapping")

    created_at = _parse_utc(plan.get("created_at"), "created_at")
    expires_at = _parse_utc(plan.get("expires_at"), "expires_at")
    if expires_at <= created_at:
        raise AuthorityBoundaryError("ApprovedTradePlan expires_at must be after created_at")
    if now.tzinfo is None or now.utcoffset() != timezone.utc.utcoffset(now):
        raise ValueError("now must be timezone-aware UTC")
    if now >= expires_at:
        raise AuthorityBoundaryError("ApprovedTradePlan is expired")


class CanonicalEntryV01Translator:
    """Mechanical entry-v0.1 translator; MARKET only and no executable price/TIF."""

    def translate(self, plan: Mapping[str, Any]) -> TranslatedEntryInstruction:
        instruction = plan.get("entry_instruction")
        if not isinstance(instruction, Mapping):
            raise ContractMismatchError("entry_instruction must be a mapping")

        keys = set(instruction.keys())
        forbidden = sorted(keys & _FORBIDDEN_EXECUTABLE_ENTRY_FIELDS)
        if forbidden:
            raise ContractMismatchError(
                "entry-v0.1 MARKET forbids executable entry fields: " + ", ".join(forbidden)
            )
        unknown = sorted(keys - _ALLOWED_ENTRY_FIELDS)
        if unknown:
            raise ContractMismatchError(
                "entry-v0.1 contains unsupported entry_instruction fields: " + ", ".join(unknown)
            )
        if instruction.get("profile_version") != ENTRY_PROFILE_VERSION:
            raise ContractMismatchError("unsupported or missing entry profile_version")
        if instruction.get("order_type") != ENTRY_ORDER_TYPE:
            raise ContractMismatchError("entry-v0.1 supports MARKET only")

        if "reference_price" in instruction:
            _parse_decimal(instruction["reference_price"], "entry_instruction.reference_price")

        # reference_price is advisory/audit context only and is intentionally not
        # promoted into limit_price, stop_price, trigger_price, or time_in_force.
        return TranslatedEntryInstruction(order_type=ENTRY_ORDER_TYPE)


class ExecutionGateway:
    """Authority boundary from an E5 ApprovedTradePlan to E4 Broker submission."""

    def prepare_entry_order(
        self,
        plan: Mapping[str, Any],
        *,
        now: datetime,
        logical_order_key: str = "entry",
    ) -> OrderRequest:
        validate_approved_trade_plan(plan, now=now)
        translated = CanonicalEntryV01Translator().translate(plan)

        quantity = _parse_decimal(plan["quantity"], "quantity")
        client_order_id = stable_client_order_id(plan["trade_plan_id"], logical_order_key)
        side = Side.BUY if plan["direction"] == "LONG" else Side.SELL
        return OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id=plan["trade_plan_id"],
            client_order_id=client_order_id,
            symbol=plan["symbol"],
            side=side,
            order_type=translated.order_type,
            quantity=quantity,
            quantity_profile_version=plan["quantity_profile_version"],
            quantity_unit=plan["quantity_unit"],
            quantity_asset=plan["quantity_asset"],
            created_at=now,
            limit_price=None,
            stop_price=None,
            reduce_only=None,
            time_in_force=None,
        )

    def submit_approved_plan(
        self,
        plan: Mapping[str, Any],
        *,
        broker: BrokerSubmitter,
        now: datetime,
        logical_order_key: str = "entry",
    ) -> OrderResult:
        request = self.prepare_entry_order(
            plan,
            now=now,
            logical_order_key=logical_order_key,
        )
        return broker.submit_order(request)
