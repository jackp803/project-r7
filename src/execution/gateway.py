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


class EntryInstructionTranslator(Protocol):
    def translate(self, plan: Mapping[str, Any]) -> TranslatedEntryInstruction:
        ...


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
    "leverage",
    "margin_mode",
    "entry_instruction",
    "protection_instruction",
    "created_at",
    "expires_at",
    "risk_policy_version",
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
    """Fail closed unless the input has the canonical ApprovedTradePlan envelope."""
    if not isinstance(plan, Mapping):
        raise AuthorityBoundaryError("execution input must be an ApprovedTradePlan mapping")
    missing = sorted(_REQUIRED_PLAN_FIELDS - set(plan.keys()))
    if missing:
        raise AuthorityBoundaryError(
            "execution accepts only ApprovedTradePlan; missing required fields: " + ", ".join(missing)
        )
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityBoundaryError("unsupported ApprovedTradePlan schema_version")
    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise AuthorityBoundaryError("ApprovedTradePlan direction must be LONG or SHORT")
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


class CurrentE5ProvisionalEntryTranslator:
    """Fail-closed adapter for E5's currently provisional nested instruction shape.

    E5 currently emits entry_instruction.style (plus optional reference_price),
    while contracts-v0.1 does not define how those values map to OrderRequest.order_type
    or conditional price semantics. E4 must not stabilize that missing shared meaning.
    """

    def translate(self, plan: Mapping[str, Any]) -> TranslatedEntryInstruction:
        instruction = plan.get("entry_instruction")
        if isinstance(instruction, Mapping) and "style" in instruction:
            raise ContractMismatchError(
                "CONTRACT MISMATCH: contracts-v0.1 does not define how "
                "ApprovedTradePlan.entry_instruction.style maps to OrderRequest.order_type; "
                "E7 approval is required before E4 can translate the current E5 nested shape"
            )
        raise ContractMismatchError(
            "CONTRACT MISMATCH: ApprovedTradePlan.entry_instruction has no E7-approved "
            "mapping to OrderRequest fields"
        )


class ExecutionGateway:
    """Authority boundary from an E5 ApprovedTradePlan to E4 Broker submission."""

    def prepare_entry_order(
        self,
        plan: Mapping[str, Any],
        *,
        translator: EntryInstructionTranslator,
        now: datetime,
        logical_order_key: str = "entry",
    ) -> OrderRequest:
        validate_approved_trade_plan(plan, now=now)
        translated = translator.translate(plan)
        if not translated.order_type or not translated.order_type.strip():
            raise ContractMismatchError("translated order_type must be non-empty")

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
            created_at=now,
            limit_price=translated.limit_price,
            stop_price=translated.stop_price,
            reduce_only=translated.reduce_only,
            time_in_force=translated.time_in_force,
        )

    def submit_approved_plan(
        self,
        plan: Mapping[str, Any],
        *,
        translator: EntryInstructionTranslator,
        broker: BrokerSubmitter,
        now: datetime,
        logical_order_key: str = "entry",
    ) -> OrderResult:
        request = self.prepare_entry_order(
            plan,
            translator=translator,
            now=now,
            logical_order_key=logical_order_key,
        )
        return broker.submit_order(request)
