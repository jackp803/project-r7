from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from .state_machine import PositionEvent, PositionLifecycleState, transition

SCHEMA_VERSION = "contracts-v0.1"
CLOSE_PROFILE_VERSION = "close-v0.1"
CLOSE_ORDER_TYPE = "MARKET"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
CANONICAL_BTC_SYMBOL = "BTC_USDT_PERP"
CANONICAL_BTC_ASSET = "BTC"
CONSISTENT = "CONSISTENT"

EXIT = "EXIT"
EMERGENCY_EXIT = "EMERGENCY_EXIT"

DEFAULT_EXIT_REASON_CODES = ("E5_EXIT_REQUESTED",)
DEFAULT_EMERGENCY_EXIT_REASON_CODES = ("E5_EMERGENCY_EXIT_REQUIRED",)

_ORDINARY_EXIT_STATES = frozenset(
    {
        PositionLifecycleState.OPEN_UNPROTECTED.value,
        PositionLifecycleState.OPEN_PROTECTED.value,
        PositionLifecycleState.PROFIT_PROTECTED.value,
    }
)
_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,95}$")


class CloseActionError(ValueError):
    """Fail-closed validation error for the E5 close-v0.1 boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CloseActionOutcome:
    """E5-internal authorization result; not a shared serialized DTO."""

    position_action: dict[str, Any]
    event: PositionEvent
    next_state: PositionLifecycleState


def default_close_reason_codes(action: str) -> tuple[str, ...]:
    """Return the minimal deterministic E5-owned reason sequence for V0.1."""

    if action == EXIT:
        return DEFAULT_EXIT_REASON_CODES
    if action == EMERGENCY_EXIT:
        return DEFAULT_EMERGENCY_EXIT_REASON_CODES
    raise CloseActionError(
        "UNSUPPORTED_CLOSE_ACTION",
        "close-v0.1 supports EXIT or EMERGENCY_EXIT only",
    )


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CloseActionError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise CloseActionError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise CloseActionError(
            "INVALID_DECIMAL",
            f"{field} must be Decimal or a base-10 decimal string",
        )
    if not parsed.is_finite():
        raise CloseActionError("INVALID_DECIMAL", f"{field} must be finite")
    return parsed


def _positive_decimal(value: Any, field: str) -> Decimal:
    parsed = _decimal(value, field)
    if parsed <= 0:
        raise CloseActionError("NON_POSITIVE_DECIMAL", f"{field} must be > 0")
    return parsed


def _utc_text(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CloseActionError(
            "INVALID_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CloseActionError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CloseActionError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _utc_datetime(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise CloseActionError("INVALID_TIMESTAMP", f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise CloseActionError(
            "INVALID_TIMESTAMP",
            f"{field} must be timezone-aware UTC",
        )
    return value.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_reason_codes(
    action: str,
    reason_codes: Sequence[str] | None,
) -> tuple[str, ...]:
    values = default_close_reason_codes(action) if reason_codes is None else tuple(reason_codes)
    if not values:
        raise CloseActionError(
            "CLOSE_REASON_CODES_REQUIRED",
            "close-v0.1 requires a non-empty E5-owned reason sequence",
        )

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or _REASON_CODE_PATTERN.fullmatch(value) is None:
            raise CloseActionError(
                "INVALID_CLOSE_REASON_CODE",
                "reason codes must be deterministic uppercase E5 audit codes",
            )
        if value in seen:
            raise CloseActionError(
                "DUPLICATE_CLOSE_REASON_CODE",
                "reason_codes must not contain duplicates",
            )
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


def _validate_parent_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise CloseActionError("INVALID_PARENT_PLAN", "ApprovedTradePlan must be a mapping")

    required = (
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
    )
    missing = [field for field in required if field not in plan]
    if missing:
        raise CloseActionError("PARENT_PLAN_INCOMPLETE", f"missing parent fields: {missing}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise CloseActionError("UNSUPPORTED_SCHEMA_VERSION", "parent plan schema_version is unsupported")

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
        _nonempty_text(plan.get(field), f"ApprovedTradePlan.{field}")

    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise CloseActionError("INVALID_PARENT_DIRECTION", "parent direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise CloseActionError(
            "UNSUPPORTED_QUANTITY_PROFILE",
            "parent quantity profile must be base-asset-v0.1",
        )
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise CloseActionError("UNSUPPORTED_QUANTITY_UNIT", "parent quantity unit must be BASE_ASSET")
    quantity_asset = _nonempty_text(plan.get("quantity_asset"), "ApprovedTradePlan.quantity_asset")
    if plan.get("symbol") == CANONICAL_BTC_SYMBOL and quantity_asset != CANONICAL_BTC_ASSET:
        raise CloseActionError(
            "QUANTITY_ASSET_MISMATCH",
            "BTC_USDT_PERP parent quantity asset must be BTC",
        )

    maximum_quantity = _positive_decimal(plan.get("quantity"), "ApprovedTradePlan.quantity")
    _positive_decimal(plan.get("leverage"), "ApprovedTradePlan.leverage")

    if not isinstance(plan.get("entry_instruction"), Mapping):
        raise CloseActionError("INVALID_PARENT_ENTRY_INSTRUCTION", "entry_instruction must be a mapping")
    if not isinstance(plan.get("protection_instruction"), Mapping):
        raise CloseActionError(
            "INVALID_PARENT_PROTECTION_INSTRUCTION",
            "protection_instruction must be a mapping",
        )

    plan_created_at = _utc_text(plan.get("created_at"), "ApprovedTradePlan.created_at")
    plan_expires_at = _utc_text(plan.get("expires_at"), "ApprovedTradePlan.expires_at")
    if plan_expires_at <= plan_created_at:
        raise CloseActionError(
            "INVALID_PARENT_PLAN_EXPIRY",
            "ApprovedTradePlan.expires_at must be after created_at",
        )

    return {"maximum_quantity": maximum_quantity}


def _validate_position(
    position: Mapping[str, Any],
    plan: Mapping[str, Any],
    action: str,
) -> dict[str, Any]:
    if not isinstance(position, Mapping):
        raise CloseActionError("INVALID_POSITION", "Position observation must be a mapping")

    required = (
        "schema_version",
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "average_entry_price",
        "opened_at",
        "broker_state_observed_at",
        "reconciliation_status",
        "lifecycle_state",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    )
    missing = [field for field in required if field not in position]
    if missing:
        raise CloseActionError("POSITION_INCOMPLETE", f"missing Position fields: {missing}")
    if position.get("schema_version") != SCHEMA_VERSION:
        raise CloseActionError("UNSUPPORTED_SCHEMA_VERSION", "Position schema_version is unsupported")

    _nonempty_text(position.get("position_id"), "Position.position_id")
    _nonempty_text(position.get("symbol"), "Position.symbol")
    if position.get("side") not in {"LONG", "SHORT"}:
        raise CloseActionError("INVALID_POSITION_SIDE", "Position.side must be LONG or SHORT")
    if position.get("reconciliation_status") != CONSISTENT:
        raise CloseActionError(
            "POSITION_RECONCILIATION_NOT_CONSISTENT",
            "close-v0.1 requires reconciliation_status=CONSISTENT",
        )

    lifecycle = position.get("lifecycle_state")
    if action == EXIT:
        if lifecycle not in _ORDINARY_EXIT_STATES:
            raise CloseActionError(
                "EXIT_SOURCE_LIFECYCLE_NOT_ALLOWED",
                "EXIT requires OPEN_UNPROTECTED, OPEN_PROTECTED, or PROFIT_PROTECTED",
            )
    elif action == EMERGENCY_EXIT:
        if lifecycle != PositionLifecycleState.EMERGENCY.value:
            raise CloseActionError(
                "EMERGENCY_EXIT_SOURCE_LIFECYCLE_NOT_ALLOWED",
                "EMERGENCY_EXIT requires lifecycle_state=EMERGENCY",
            )
    else:
        raise CloseActionError(
            "UNSUPPORTED_CLOSE_ACTION",
            "close-v0.1 supports EXIT or EMERGENCY_EXIT only",
        )

    actual_quantity = _positive_decimal(position.get("actual_quantity"), "Position.actual_quantity")
    _positive_decimal(position.get("average_entry_price"), "Position.average_entry_price")
    opened_at = _utc_text(position.get("opened_at"), "Position.opened_at")
    observed_at = _utc_text(
        position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
    )
    if observed_at < opened_at:
        raise CloseActionError(
            "POSITION_TIME_INCONSISTENT",
            "broker_state_observed_at cannot be before opened_at",
        )

    if position.get("symbol") != plan.get("symbol"):
        raise CloseActionError("POSITION_SYMBOL_MISMATCH", "Position symbol does not match parent plan")
    if position.get("side") != plan.get("direction"):
        raise CloseActionError("POSITION_SIDE_MISMATCH", "Position side does not match parent plan direction")
    if position.get("quantity_profile_version") != plan.get("quantity_profile_version"):
        raise CloseActionError(
            "POSITION_QUANTITY_PROFILE_MISMATCH",
            "Position quantity profile does not match parent plan",
        )
    if position.get("quantity_unit") != plan.get("quantity_unit"):
        raise CloseActionError(
            "POSITION_QUANTITY_UNIT_MISMATCH",
            "Position quantity unit does not match parent plan",
        )
    if position.get("quantity_asset") != plan.get("quantity_asset"):
        raise CloseActionError(
            "POSITION_QUANTITY_ASSET_MISMATCH",
            "Position quantity asset does not match parent plan",
        )

    return {
        "actual_quantity": actual_quantity,
        "observed_at": observed_at,
        "lifecycle_state": lifecycle,
    }


def _identity_material(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "close_profile_version": action.get("close_profile_version"),
        "action": action.get("action"),
        "reason_codes": action.get("reason_codes"),
        "trade_plan_id": action.get("trade_plan_id"),
        "risk_decision_id": action.get("risk_decision_id"),
        "strategy_id": action.get("strategy_id"),
        "strategy_version": action.get("strategy_version"),
        "risk_policy_version": action.get("risk_policy_version"),
        "position_id": action.get("position_id"),
        "symbol": action.get("symbol"),
        "position_side": action.get("position_side"),
        "source_lifecycle_state": action.get("source_lifecycle_state"),
        "position_observed_at": action.get("position_observed_at"),
        "position_reconciliation_status": action.get("position_reconciliation_status"),
        "quantity": action.get("quantity"),
        "quantity_profile_version": action.get("quantity_profile_version"),
        "quantity_unit": action.get("quantity_unit"),
        "quantity_asset": action.get("quantity_asset"),
        "close_order_type": action.get("close_order_type"),
        "created_at": action.get("created_at"),
        "expires_at": action.get("expires_at"),
    }


def _stable_action_id(material: Mapping[str, Any]) -> str:
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return "posact_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_close_position_action(
    action: Mapping[str, Any],
    position: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    *,
    now: datetime,
) -> None:
    """Validate one executable E5 close-v0.1 EXIT/EMERGENCY_EXIT action."""

    if not isinstance(action, Mapping):
        raise CloseActionError("INVALID_POSITION_ACTION", "PositionAction must be a mapping")

    action_type = action.get("action")
    if action_type not in {EXIT, EMERGENCY_EXIT}:
        raise CloseActionError("UNSUPPORTED_CLOSE_ACTION", "close-v0.1 action is unsupported")

    plan_facts = _validate_parent_plan(parent_plan)
    position_facts = _validate_position(position, parent_plan, action_type)

    required = (
        "schema_version",
        "close_profile_version",
        "position_action_id",
        "position_id",
        "action",
        "reason_codes",
        "risk_policy_version",
        "trade_plan_id",
        "risk_decision_id",
        "strategy_id",
        "strategy_version",
        "symbol",
        "position_side",
        "source_lifecycle_state",
        "position_observed_at",
        "position_reconciliation_status",
        "quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "close_order_type",
        "created_at",
        "expires_at",
    )
    missing = [field for field in required if field not in action]
    if missing:
        raise CloseActionError("POSITION_ACTION_INCOMPLETE", f"missing PositionAction fields: {missing}")

    if action.get("schema_version") != SCHEMA_VERSION:
        raise CloseActionError("UNSUPPORTED_SCHEMA_VERSION", "PositionAction schema_version is unsupported")
    if action.get("close_profile_version") != CLOSE_PROFILE_VERSION:
        raise CloseActionError("UNSUPPORTED_CLOSE_PROFILE", "executable close requires close-v0.1")
    if action.get("close_order_type") != CLOSE_ORDER_TYPE:
        raise CloseActionError("UNSUPPORTED_CLOSE_ORDER_TYPE", "close-v0.1 requires MARKET")
    if action.get("position_reconciliation_status") != CONSISTENT:
        raise CloseActionError(
            "POSITION_ACTION_RECONCILIATION_NOT_CONSISTENT",
            "PositionAction requires position_reconciliation_status=CONSISTENT",
        )

    normalized_reasons = _normalize_reason_codes(action_type, action.get("reason_codes"))
    if list(normalized_reasons) != action.get("reason_codes"):
        raise CloseActionError(
            "CLOSE_REASON_SEQUENCE_NOT_CANONICAL",
            "PositionAction reason_codes must preserve the exact deterministic E5 sequence",
        )

    lineage_pairs = (
        ("trade_plan_id", "trade_plan_id"),
        ("risk_decision_id", "risk_decision_id"),
        ("strategy_id", "strategy_id"),
        ("strategy_version", "strategy_version"),
        ("risk_policy_version", "risk_policy_version"),
        ("symbol", "symbol"),
    )
    for action_field, plan_field in lineage_pairs:
        if action.get(action_field) != parent_plan.get(plan_field):
            raise CloseActionError(
                "POSITION_ACTION_LINEAGE_MISMATCH",
                f"{action_field} does not match parent ApprovedTradePlan",
            )

    position_pairs = (
        ("position_id", "position_id"),
        ("position_side", "side"),
        ("source_lifecycle_state", "lifecycle_state"),
        ("position_observed_at", "broker_state_observed_at"),
        ("position_reconciliation_status", "reconciliation_status"),
        ("quantity_profile_version", "quantity_profile_version"),
        ("quantity_unit", "quantity_unit"),
        ("quantity_asset", "quantity_asset"),
    )
    for action_field, position_field in position_pairs:
        if action.get(action_field) != position.get(position_field):
            raise CloseActionError(
                "POSITION_ACTION_POSITION_MISMATCH",
                f"{action_field} does not match source Position",
            )

    action_quantity = _positive_decimal(action.get("quantity"), "PositionAction.quantity")
    if action_quantity != position_facts["actual_quantity"]:
        raise CloseActionError(
            "CLOSE_QUANTITY_NOT_ACTUAL_EXPOSURE",
            "PositionAction.quantity must equal exact Position.actual_quantity",
        )
    if action_quantity > plan_facts["maximum_quantity"]:
        raise CloseActionError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "actual exposure exceeds the parent ApprovedTradePlan maximum",
        )

    if action.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise CloseActionError("UNSUPPORTED_QUANTITY_PROFILE", "close quantity profile is unsupported")
    if action.get("quantity_unit") != QUANTITY_UNIT:
        raise CloseActionError("UNSUPPORTED_QUANTITY_UNIT", "close quantity unit is unsupported")
    if action.get("symbol") == CANONICAL_BTC_SYMBOL and action.get("quantity_asset") != CANONICAL_BTC_ASSET:
        raise CloseActionError("QUANTITY_ASSET_MISMATCH", "BTC_USDT_PERP close quantity asset must be BTC")

    created_at = _utc_text(action.get("created_at"), "PositionAction.created_at")
    expires_at = _utc_text(action.get("expires_at"), "PositionAction.expires_at")
    if created_at < position_facts["observed_at"]:
        raise CloseActionError(
            "POSITION_OBSERVATION_AFTER_ACTION_CREATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expires_at <= created_at:
        raise CloseActionError("INVALID_ACTION_EXPIRY", "PositionAction.expires_at must be after created_at")

    now_utc = _utc_datetime(now, "now")
    if now_utc >= expires_at:
        raise CloseActionError("POSITION_ACTION_EXPIRED", "PositionAction is expired")

    expected_id = _stable_action_id(_identity_material(action))
    if action.get("position_action_id") != expected_id:
        raise CloseActionError(
            "POSITION_ACTION_ID_MISMATCH",
            "position_action_id does not match authority-bearing close material",
        )


def build_close_position_action(
    position: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    *,
    action: str,
    created_at: datetime,
    expires_at: datetime,
    reason_codes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build E5's provider-neutral close-v0.1 EXIT/EMERGENCY_EXIT authority."""

    plan_facts = _validate_parent_plan(parent_plan)
    position_facts = _validate_position(position, parent_plan, action)
    reasons = _normalize_reason_codes(action, reason_codes)
    created = _utc_datetime(created_at, "created_at")
    expiry = _utc_datetime(expires_at, "expires_at")

    if created < position_facts["observed_at"]:
        raise CloseActionError(
            "POSITION_OBSERVATION_AFTER_ACTION_CREATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expiry <= created:
        raise CloseActionError("INVALID_ACTION_EXPIRY", "expires_at must be after created_at")
    if position_facts["actual_quantity"] > plan_facts["maximum_quantity"]:
        raise CloseActionError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "actual exposure exceeds the parent ApprovedTradePlan maximum",
        )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "close_profile_version": CLOSE_PROFILE_VERSION,
        "position_id": position["position_id"],
        "action": action,
        "reason_codes": list(reasons),
        "risk_policy_version": parent_plan["risk_policy_version"],
        "trade_plan_id": parent_plan["trade_plan_id"],
        "risk_decision_id": parent_plan["risk_decision_id"],
        "strategy_id": parent_plan["strategy_id"],
        "strategy_version": parent_plan["strategy_version"],
        "symbol": parent_plan["symbol"],
        "position_side": position["side"],
        "source_lifecycle_state": position["lifecycle_state"],
        "position_observed_at": position["broker_state_observed_at"],
        "position_reconciliation_status": CONSISTENT,
        "quantity": format(position_facts["actual_quantity"], "f"),
        "quantity_profile_version": parent_plan["quantity_profile_version"],
        "quantity_unit": parent_plan["quantity_unit"],
        "quantity_asset": parent_plan["quantity_asset"],
        "close_order_type": CLOSE_ORDER_TYPE,
        "created_at": _fmt_utc(created),
        "expires_at": _fmt_utc(expiry),
    }
    payload["position_action_id"] = _stable_action_id(_identity_material(payload))

    validate_close_position_action(payload, position, parent_plan, now=created)
    return payload


def authorize_close_position_action(
    position: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    *,
    action: str,
    created_at: datetime,
    expires_at: datetime,
    reason_codes: Sequence[str] | None = None,
) -> CloseActionOutcome:
    """Produce close authority and the existing EXIT_REQUESTED lifecycle intent.

    This function does not mutate Position truth and never emits POSITION_CLOSED.
    """

    position_action = build_close_position_action(
        position,
        parent_plan,
        action=action,
        created_at=created_at,
        expires_at=expires_at,
        reason_codes=reason_codes,
    )
    try:
        source_state = PositionLifecycleState(position["lifecycle_state"])
    except (KeyError, ValueError) as exc:
        raise CloseActionError(
            "INVALID_SOURCE_LIFECYCLE",
            "source Position lifecycle state is invalid",
        ) from exc

    next_state = transition(source_state, PositionEvent.EXIT_REQUESTED)
    return CloseActionOutcome(
        position_action=position_action,
        event=PositionEvent.EXIT_REQUESTED,
        next_state=next_state,
    )
