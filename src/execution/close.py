from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from .models import (
    SCHEMA_VERSION,
    OrderRequest,
    Side,
    stable_order_request_id,
    stable_position_action_client_order_id,
)

CLOSE_PROFILE_VERSION = "close-v0.1"
CLOSE_ORDER_TYPE = "MARKET"
AUTHORIZATION_TYPE = "POSITION_ACTION"
POSITION_EXIT_ROLE = "POSITION_EXIT"
EMERGENCY_EXIT_ROLE = "EMERGENCY_EXIT"
EXIT = "EXIT"
EMERGENCY_EXIT = "EMERGENCY_EXIT"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
QUANTITY_ASSET = "BTC"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
CONSISTENT = "CONSISTENT"

_ORDINARY_EXIT_STATES = frozenset(
    {"OPEN_UNPROTECTED", "OPEN_PROTECTED", "PROFIT_PROTECTED"}
)


class CloseAuthorityError(ValueError):
    """Fail-closed E4 consumer-boundary error for close-v0.1."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


_PARENT_REQUIRED_FIELDS = {
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

_POSITION_REQUIRED_FIELDS = {
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
}

_ACTION_REQUIRED_FIELDS = {
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
}


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CloseAuthorityError("INVALID_MAPPING", f"{field} must be a mapping")
    return value


def _require_nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CloseAuthorityError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    return value


def _parse_positive_decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise CloseAuthorityError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise CloseAuthorityError(
            "INVALID_DECIMAL",
            f"{field} must be Decimal or a base-10 decimal string",
        )
    if not parsed.is_finite() or parsed <= 0:
        raise CloseAuthorityError("INVALID_DECIMAL", f"{field} must be finite and > 0")
    return parsed


def _parse_utc_text(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CloseAuthorityError(
            "INVALID_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CloseAuthorityError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CloseAuthorityError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _require_utc_datetime(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise CloseAuthorityError("INVALID_TIMESTAMP", f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise CloseAuthorityError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
    return value.astimezone(timezone.utc)


def _validate_reason_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CloseAuthorityError(
            "CLOSE_REASON_CODES_REQUIRED",
            "PositionAction.reason_codes must be a non-empty sequence",
        )
    reasons = tuple(value)
    if not reasons:
        raise CloseAuthorityError(
            "CLOSE_REASON_CODES_REQUIRED",
            "PositionAction.reason_codes must be a non-empty sequence",
        )
    for reason in reasons:
        _require_nonempty_text(reason, "PositionAction.reason_codes[]")
    return reasons


def _validate_parent_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    plan = _require_mapping(plan, "ApprovedTradePlan")
    missing = sorted(_PARENT_REQUIRED_FIELDS - set(plan.keys()))
    if missing:
        raise CloseAuthorityError(
            "PARENT_PLAN_INCOMPLETE",
            "ApprovedTradePlan missing required fields: " + ", ".join(missing),
        )
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "parent plan schema_version is unsupported")
    if plan.get("symbol") != CANONICAL_SYMBOL:
        raise CloseAuthorityError("UNSUPPORTED_SYMBOL", "current close-v0.1 supports BTC_USDT_PERP only")
    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise CloseAuthorityError("INVALID_PARENT_DIRECTION", "parent direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_PROFILE", "parent quantity profile must be base-asset-v0.1")
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_UNIT", "parent quantity unit must be BASE_ASSET")
    if plan.get("quantity_asset") != QUANTITY_ASSET:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_ASSET", "BTC_USDT_PERP parent quantity asset must be BTC")

    for field in (
        "trade_plan_id",
        "risk_decision_id",
        "intent_id",
        "strategy_id",
        "strategy_version",
        "margin_mode",
        "risk_policy_version",
    ):
        _require_nonempty_text(plan.get(field), f"ApprovedTradePlan.{field}")

    maximum_quantity = _parse_positive_decimal(plan.get("quantity"), "ApprovedTradePlan.quantity")
    _parse_positive_decimal(plan.get("leverage"), "ApprovedTradePlan.leverage")
    _require_mapping(plan.get("entry_instruction"), "ApprovedTradePlan.entry_instruction")
    _require_mapping(plan.get("protection_instruction"), "ApprovedTradePlan.protection_instruction")

    created_at = _parse_utc_text(plan.get("created_at"), "ApprovedTradePlan.created_at")
    expires_at = _parse_utc_text(plan.get("expires_at"), "ApprovedTradePlan.expires_at")
    if expires_at <= created_at:
        raise CloseAuthorityError(
            "INVALID_PARENT_PLAN_EXPIRY",
            "ApprovedTradePlan.expires_at must be after created_at",
        )

    # Parent entry TTL is immutable lineage only after exposure exists. It is
    # intentionally not compared with current time for close authority.
    return {"maximum_quantity": maximum_quantity}


def _validate_position(position: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    position = _require_mapping(position, "Position")
    missing = sorted(_POSITION_REQUIRED_FIELDS - set(position.keys()))
    if missing:
        raise CloseAuthorityError(
            "POSITION_INCOMPLETE",
            "Position missing required fields: " + ", ".join(missing),
        )
    if position.get("schema_version") != SCHEMA_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "Position schema_version is unsupported")
    _require_nonempty_text(position.get("position_id"), "Position.position_id")
    if position.get("symbol") != plan.get("symbol"):
        raise CloseAuthorityError("POSITION_SYMBOL_MISMATCH", "Position symbol does not match parent plan")
    if position.get("side") not in {"LONG", "SHORT"} or position.get("side") != plan.get("direction"):
        raise CloseAuthorityError("POSITION_SIDE_MISMATCH", "Position side does not match parent direction")
    if position.get("reconciliation_status") != CONSISTENT:
        raise CloseAuthorityError(
            "POSITION_RECONCILIATION_NOT_CONSISTENT",
            "close-v0.1 requires Position reconciliation_status=CONSISTENT",
        )
    if position.get("quantity_profile_version") != plan.get("quantity_profile_version"):
        raise CloseAuthorityError("POSITION_QUANTITY_PROFILE_MISMATCH", "Position quantity profile is incompatible")
    if position.get("quantity_unit") != plan.get("quantity_unit"):
        raise CloseAuthorityError("POSITION_QUANTITY_UNIT_MISMATCH", "Position quantity unit is incompatible")
    if position.get("quantity_asset") != plan.get("quantity_asset"):
        raise CloseAuthorityError("POSITION_QUANTITY_ASSET_MISMATCH", "Position quantity asset is incompatible")

    actual_quantity = _parse_positive_decimal(position.get("actual_quantity"), "Position.actual_quantity")
    _parse_positive_decimal(position.get("average_entry_price"), "Position.average_entry_price")
    opened_at = _parse_utc_text(position.get("opened_at"), "Position.opened_at")
    observed_at = _parse_utc_text(
        position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
    )
    if observed_at < opened_at:
        raise CloseAuthorityError(
            "POSITION_TIME_INCONSISTENT",
            "Position.broker_state_observed_at cannot be before opened_at",
        )
    return {
        "actual_quantity": actual_quantity,
        "observed_at": observed_at,
        "lifecycle_state": position.get("lifecycle_state"),
    }


def validate_close_authority(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Validate exact E5 close-v0.1 authority against parent and current Position truth."""

    now_utc = _require_utc_datetime(now, "now")
    plan_facts = _validate_parent_plan(parent_plan)
    position_facts = _validate_position(current_position, parent_plan)
    action = _require_mapping(action, "PositionAction")

    missing = sorted(_ACTION_REQUIRED_FIELDS - set(action.keys()))
    if missing:
        raise CloseAuthorityError(
            "POSITION_ACTION_INCOMPLETE",
            "PositionAction missing required fields: " + ", ".join(missing),
        )
    if action.get("schema_version") != SCHEMA_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "PositionAction schema_version is unsupported")
    if action.get("close_profile_version") != CLOSE_PROFILE_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_CLOSE_PROFILE", "executable close requires close-v0.1")

    action_type = action.get("action")
    if action_type not in {EXIT, EMERGENCY_EXIT}:
        raise CloseAuthorityError("UNSUPPORTED_CLOSE_ACTION", "close-v0.1 supports EXIT or EMERGENCY_EXIT only")
    if action.get("close_order_type") != CLOSE_ORDER_TYPE:
        raise CloseAuthorityError("UNSUPPORTED_CLOSE_ORDER_TYPE", "close-v0.1 requires MARKET")
    if action.get("position_reconciliation_status") != CONSISTENT:
        raise CloseAuthorityError(
            "POSITION_ACTION_RECONCILIATION_NOT_CONSISTENT",
            "PositionAction requires position_reconciliation_status=CONSISTENT",
        )
    _validate_reason_codes(action.get("reason_codes"))

    for field in (
        "position_action_id",
        "position_id",
        "trade_plan_id",
        "risk_decision_id",
        "strategy_id",
        "strategy_version",
        "risk_policy_version",
    ):
        _require_nonempty_text(action.get(field), f"PositionAction.{field}")

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
            raise CloseAuthorityError(
                "POSITION_ACTION_LINEAGE_MISMATCH",
                f"PositionAction.{action_field} does not match parent ApprovedTradePlan",
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
        if action.get(action_field) != current_position.get(position_field):
            raise CloseAuthorityError(
                "POSITION_ACTION_POSITION_MISMATCH",
                f"PositionAction.{action_field} does not match current Position.{position_field}",
            )

    lifecycle = position_facts["lifecycle_state"]
    if action_type == EXIT:
        if lifecycle not in _ORDINARY_EXIT_STATES:
            raise CloseAuthorityError(
                "EXIT_SOURCE_LIFECYCLE_NOT_ALLOWED",
                "EXIT requires OPEN_UNPROTECTED, OPEN_PROTECTED, or PROFIT_PROTECTED",
            )
    else:
        if lifecycle != "EMERGENCY":
            raise CloseAuthorityError(
                "EMERGENCY_EXIT_SOURCE_LIFECYCLE_NOT_ALLOWED",
                "EMERGENCY_EXIT requires lifecycle_state=EMERGENCY",
            )

    action_quantity = _parse_positive_decimal(action.get("quantity"), "PositionAction.quantity")
    if action_quantity != position_facts["actual_quantity"]:
        raise CloseAuthorityError(
            "CLOSE_QUANTITY_NOT_ACTUAL_EXPOSURE",
            "PositionAction.quantity must equal exact current Position.actual_quantity",
        )
    if action_quantity > plan_facts["maximum_quantity"]:
        raise CloseAuthorityError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "current actual exposure exceeds parent ApprovedTradePlan maximum",
        )
    if action.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_PROFILE", "close quantity profile is unsupported")
    if action.get("quantity_unit") != QUANTITY_UNIT:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_UNIT", "close quantity unit is unsupported")
    if action.get("quantity_asset") != QUANTITY_ASSET:
        raise CloseAuthorityError("UNSUPPORTED_QUANTITY_ASSET", "BTC_USDT_PERP close quantity asset must be BTC")

    action_observed_at = _parse_utc_text(
        action.get("position_observed_at"),
        "PositionAction.position_observed_at",
    )
    if action_observed_at != position_facts["observed_at"]:
        raise CloseAuthorityError(
            "POSITION_OBSERVATION_MISMATCH",
            "PositionAction source observation is not the exact current Position observation",
        )
    created_at = _parse_utc_text(action.get("created_at"), "PositionAction.created_at")
    expires_at = _parse_utc_text(action.get("expires_at"), "PositionAction.expires_at")
    if created_at < action_observed_at:
        raise CloseAuthorityError(
            "ACTION_BEFORE_POSITION_OBSERVATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expires_at <= created_at:
        raise CloseAuthorityError("INVALID_ACTION_EXPIRY", "PositionAction.expires_at must be after created_at")
    if now_utc >= expires_at:
        raise CloseAuthorityError("POSITION_ACTION_EXPIRED", "PositionAction is expired")

    return {"quantity": action_quantity, "action": action_type}


def prepare_close_order(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    *,
    now: datetime,
) -> OrderRequest:
    """Mechanically translate accepted close-v0.1 authority into canonical reduce-only MARKET."""

    facts = validate_close_authority(
        action,
        parent_plan,
        current_position,
        now=now,
    )
    order_role = POSITION_EXIT_ROLE if facts["action"] == EXIT else EMERGENCY_EXIT_ROLE
    client_order_id = stable_position_action_client_order_id(
        action["position_action_id"],
        order_role,
    )
    side = Side.SELL if action["position_side"] == "LONG" else Side.BUY

    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_order_id),
        trade_plan_id=action["trade_plan_id"],
        client_order_id=client_order_id,
        symbol=action["symbol"],
        side=side,
        order_type=CLOSE_ORDER_TYPE,
        quantity=facts["quantity"],
        quantity_profile_version=action["quantity_profile_version"],
        quantity_unit=action["quantity_unit"],
        quantity_asset=action["quantity_asset"],
        created_at=_require_utc_datetime(now, "now"),
        authorization_type=AUTHORIZATION_TYPE,
        position_action_id=action["position_action_id"],
        position_id=action["position_id"],
        risk_decision_id=action["risk_decision_id"],
        order_role=order_role,
        limit_price=None,
        stop_price=None,
        reduce_only=True,
        time_in_force=None,
    )
