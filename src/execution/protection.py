from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .models import (
    SCHEMA_VERSION,
    OrderRequest,
    Side,
    stable_order_request_id,
    stable_position_action_client_order_id,
)

PROTECTION_PROFILE_VERSION = "protection-v0.1"
PROTECTION_ACTION = "PROTECT"
AUTHORIZATION_TYPE = "POSITION_ACTION"
ORDER_ROLE = "PROTECTION_STOP"
ORDER_TYPE = "STOP_MARKET"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
QUANTITY_ASSET = "BTC"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
CONSISTENT = "CONSISTENT"
OPEN_UNPROTECTED = "OPEN_UNPROTECTED"
ENTRY_PROFILE_VERSION = "entry-v0.1"
ENTRY_ORDER_TYPE = "MARKET"


class ProtectionAuthorityError(ValueError):
    """Fail-closed E4 consumer-boundary error for protection-v0.1."""

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

_ACTION_REQUIRED_FIELDS = {
    "schema_version",
    "protection_profile_version",
    "position_action_id",
    "trade_plan_id",
    "risk_decision_id",
    "position_id",
    "action",
    "reason_codes",
    "risk_policy_version",
    "symbol",
    "position_side",
    "position_observed_at",
    "position_reconciliation_status",
    "quantity",
    "quantity_profile_version",
    "quantity_unit",
    "quantity_asset",
    "protection_instruction",
    "created_at",
    "expires_at",
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

_ALLOWED_ENTRY_FIELDS = {"profile_version", "order_type", "reference_price"}
_FORBIDDEN_EXECUTABLE_ENTRY_FIELDS = {
    "limit_price",
    "stop_price",
    "trigger_price",
    "time_in_force",
}
_ALLOWED_PROTECTION_FIELDS = {"stop_level", "target_level", "max_hold_seconds"}


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtectionAuthorityError("INVALID_MAPPING", f"{field} must be a mapping")
    return value


def _require_nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtectionAuthorityError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    return value


def _parse_positive_decimal(value: Any, field: str) -> Decimal:
    if not isinstance(value, str):
        raise ProtectionAuthorityError(
            "INVALID_DECIMAL",
            f"{field} must be a base-10 decimal string",
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ProtectionAuthorityError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ProtectionAuthorityError("INVALID_DECIMAL", f"{field} must be finite and > 0")
    return parsed


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtectionAuthorityError(
            "INVALID_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionAuthorityError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionAuthorityError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _require_utc_datetime(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ProtectionAuthorityError("INVALID_TIMESTAMP", f"{field} must be datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ProtectionAuthorityError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
    return value.astimezone(timezone.utc)


def _normalize_protection_instruction(value: Any, field: str) -> tuple[Decimal, Decimal | None, int]:
    instruction = _require_mapping(value, field)
    unknown = sorted(set(instruction.keys()) - _ALLOWED_PROTECTION_FIELDS)
    if unknown:
        raise ProtectionAuthorityError(
            "UNSUPPORTED_PROTECTION_FIELD",
            f"{field} contains unsupported fields: {', '.join(unknown)}",
        )
    if "stop_level" not in instruction or "max_hold_seconds" not in instruction:
        raise ProtectionAuthorityError(
            "PROTECTION_INSTRUCTION_INCOMPLETE",
            f"{field} requires stop_level and max_hold_seconds",
        )
    stop = _parse_positive_decimal(instruction.get("stop_level"), f"{field}.stop_level")
    target_raw = instruction.get("target_level")
    target = None
    if target_raw is not None:
        target = _parse_positive_decimal(target_raw, f"{field}.target_level")
    max_hold = instruction.get("max_hold_seconds")
    if type(max_hold) is not int or max_hold <= 0:
        raise ProtectionAuthorityError(
            "INVALID_MAX_HOLD_SECONDS",
            f"{field}.max_hold_seconds must be a positive integer",
        )
    return stop, target, max_hold


def _validate_entry_profile_without_ttl(plan: Mapping[str, Any]) -> None:
    instruction = _require_mapping(plan.get("entry_instruction"), "ApprovedTradePlan.entry_instruction")
    forbidden = sorted(set(instruction.keys()) & _FORBIDDEN_EXECUTABLE_ENTRY_FIELDS)
    if forbidden:
        raise ProtectionAuthorityError(
            "INVALID_PARENT_ENTRY_PROFILE",
            "parent entry-v0.1 contains forbidden executable fields: " + ", ".join(forbidden),
        )
    unknown = sorted(set(instruction.keys()) - _ALLOWED_ENTRY_FIELDS)
    if unknown:
        raise ProtectionAuthorityError(
            "INVALID_PARENT_ENTRY_PROFILE",
            "parent entry-v0.1 contains unsupported fields: " + ", ".join(unknown),
        )
    if instruction.get("profile_version") != ENTRY_PROFILE_VERSION:
        raise ProtectionAuthorityError(
            "INVALID_PARENT_ENTRY_PROFILE",
            "parent ApprovedTradePlan must retain entry-v0.1 profile lineage",
        )
    if instruction.get("order_type") != ENTRY_ORDER_TYPE:
        raise ProtectionAuthorityError(
            "INVALID_PARENT_ENTRY_PROFILE",
            "parent entry-v0.1 order_type must be MARKET",
        )
    if "reference_price" in instruction:
        _parse_positive_decimal(
            instruction.get("reference_price"),
            "ApprovedTradePlan.entry_instruction.reference_price",
        )


def _validate_parent_plan_for_protection(plan: Mapping[str, Any]) -> dict[str, Any]:
    plan = _require_mapping(plan, "ApprovedTradePlan")
    missing = sorted(_PARENT_REQUIRED_FIELDS - set(plan.keys()))
    if missing:
        raise ProtectionAuthorityError(
            "PARENT_PLAN_INCOMPLETE",
            "ApprovedTradePlan missing required fields: " + ", ".join(missing),
        )
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "parent plan schema_version is unsupported")
    if plan.get("symbol") != CANONICAL_SYMBOL:
        raise ProtectionAuthorityError("UNSUPPORTED_SYMBOL", "current protection-v0.1 supports BTC_USDT_PERP only")
    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise ProtectionAuthorityError("INVALID_PARENT_DIRECTION", "parent direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_PROFILE", "parent quantity profile must be base-asset-v0.1")
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_UNIT", "parent quantity unit must be BASE_ASSET")
    if plan.get("quantity_asset") != QUANTITY_ASSET:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_ASSET", "BTC_USDT_PERP parent quantity asset must be BTC")

    for field in (
        "trade_plan_id",
        "risk_decision_id",
        "intent_id",
        "strategy_id",
        "strategy_version",
        "risk_policy_version",
        "margin_mode",
    ):
        _require_nonempty_text(plan.get(field), f"ApprovedTradePlan.{field}")

    maximum_quantity = _parse_positive_decimal(plan.get("quantity"), "ApprovedTradePlan.quantity")
    _parse_positive_decimal(plan.get("leverage"), "ApprovedTradePlan.leverage")
    _validate_entry_profile_without_ttl(plan)
    protection = _normalize_protection_instruction(
        plan.get("protection_instruction"),
        "ApprovedTradePlan.protection_instruction",
    )

    # The parent entry TTL is immutable lineage only after exposure exists. It
    # must be structurally valid, but it is intentionally not compared with now.
    created_at = _parse_utc(plan.get("created_at"), "ApprovedTradePlan.created_at")
    expires_at = _parse_utc(plan.get("expires_at"), "ApprovedTradePlan.expires_at")
    if expires_at <= created_at:
        raise ProtectionAuthorityError(
            "INVALID_PARENT_PLAN_EXPIRY",
            "ApprovedTradePlan.expires_at must be after created_at",
        )

    return {
        "maximum_quantity": maximum_quantity,
        "protection_instruction": protection,
    }


def _validate_current_position(position: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    position = _require_mapping(position, "Position")
    missing = sorted(_POSITION_REQUIRED_FIELDS - set(position.keys()))
    if missing:
        raise ProtectionAuthorityError(
            "POSITION_INCOMPLETE",
            "Position missing required fields: " + ", ".join(missing),
        )
    if position.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "Position schema_version is unsupported")
    _require_nonempty_text(position.get("position_id"), "Position.position_id")
    if position.get("symbol") != CANONICAL_SYMBOL or position.get("symbol") != plan.get("symbol"):
        raise ProtectionAuthorityError("POSITION_SYMBOL_MISMATCH", "Position symbol does not match parent canonical symbol")
    if position.get("side") not in {"LONG", "SHORT"} or position.get("side") != plan.get("direction"):
        raise ProtectionAuthorityError("POSITION_SIDE_MISMATCH", "Position side does not match parent direction")
    if position.get("reconciliation_status") != CONSISTENT:
        raise ProtectionAuthorityError(
            "POSITION_RECONCILIATION_NOT_CONSISTENT",
            "protection requires current Position reconciliation_status=CONSISTENT",
        )
    if position.get("lifecycle_state") != OPEN_UNPROTECTED:
        raise ProtectionAuthorityError(
            "POSITION_NOT_OPEN_UNPROTECTED",
            "initial protection request requires Position lifecycle_state=OPEN_UNPROTECTED",
        )
    if position.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION or position.get("quantity_profile_version") != plan.get("quantity_profile_version"):
        raise ProtectionAuthorityError("POSITION_QUANTITY_PROFILE_MISMATCH", "Position quantity profile is incompatible")
    if position.get("quantity_unit") != QUANTITY_UNIT or position.get("quantity_unit") != plan.get("quantity_unit"):
        raise ProtectionAuthorityError("POSITION_QUANTITY_UNIT_MISMATCH", "Position quantity unit is incompatible")
    if position.get("quantity_asset") != QUANTITY_ASSET or position.get("quantity_asset") != plan.get("quantity_asset"):
        raise ProtectionAuthorityError("POSITION_QUANTITY_ASSET_MISMATCH", "Position quantity asset is incompatible")

    actual_quantity = _parse_positive_decimal(position.get("actual_quantity"), "Position.actual_quantity")
    _parse_positive_decimal(position.get("average_entry_price"), "Position.average_entry_price")
    opened_at = _parse_utc(position.get("opened_at"), "Position.opened_at")
    observed_at = _parse_utc(
        position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
    )
    if observed_at < opened_at:
        raise ProtectionAuthorityError(
            "POSITION_TIME_INCONSISTENT",
            "Position.broker_state_observed_at cannot be before opened_at",
        )
    return {"actual_quantity": actual_quantity, "observed_at": observed_at}


def validate_protection_authority(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Validate exact E5 PROTECT authority, immutable parent lineage and current Position truth."""
    now_utc = _require_utc_datetime(now, "now")
    plan_facts = _validate_parent_plan_for_protection(parent_plan)
    position_facts = _validate_current_position(current_position, parent_plan)
    action = _require_mapping(action, "PositionAction")

    missing = sorted(_ACTION_REQUIRED_FIELDS - set(action.keys()))
    if missing:
        raise ProtectionAuthorityError(
            "POSITION_ACTION_INCOMPLETE",
            "PositionAction missing required fields: " + ", ".join(missing),
        )
    if action.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionAuthorityError("UNSUPPORTED_SCHEMA_VERSION", "PositionAction schema_version is unsupported")
    if action.get("protection_profile_version") != PROTECTION_PROFILE_VERSION:
        raise ProtectionAuthorityError(
            "UNSUPPORTED_PROTECTION_PROFILE",
            "executable protection requires protection-v0.1",
        )
    if action.get("action") != PROTECTION_ACTION:
        raise ProtectionAuthorityError(
            "UNSUPPORTED_PROTECTION_ACTION",
            "protection-v0.1 executes PROTECT only",
        )
    if action.get("position_reconciliation_status") != CONSISTENT:
        raise ProtectionAuthorityError(
            "POSITION_ACTION_RECONCILIATION_NOT_CONSISTENT",
            "PositionAction requires position_reconciliation_status=CONSISTENT",
        )
    if action.get("symbol") != CANONICAL_SYMBOL:
        raise ProtectionAuthorityError("UNSUPPORTED_SYMBOL", "PositionAction symbol is unsupported")
    if action.get("position_side") not in {"LONG", "SHORT"}:
        raise ProtectionAuthorityError("INVALID_POSITION_SIDE", "PositionAction.position_side must be LONG or SHORT")
    if action.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_PROFILE", "PositionAction quantity profile is unsupported")
    if action.get("quantity_unit") != QUANTITY_UNIT:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_UNIT", "PositionAction quantity unit is unsupported")
    if action.get("quantity_asset") != QUANTITY_ASSET:
        raise ProtectionAuthorityError("UNSUPPORTED_QUANTITY_ASSET", "PositionAction quantity asset is unsupported")

    for field in (
        "position_action_id",
        "trade_plan_id",
        "risk_decision_id",
        "position_id",
        "risk_policy_version",
    ):
        _require_nonempty_text(action.get(field), f"PositionAction.{field}")

    lineage_pairs = (
        ("trade_plan_id", "trade_plan_id"),
        ("risk_decision_id", "risk_decision_id"),
        ("risk_policy_version", "risk_policy_version"),
        ("symbol", "symbol"),
    )
    for action_field, plan_field in lineage_pairs:
        if action.get(action_field) != parent_plan.get(plan_field):
            raise ProtectionAuthorityError(
                "POSITION_ACTION_LINEAGE_MISMATCH",
                f"PositionAction.{action_field} does not match parent ApprovedTradePlan",
            )

    position_pairs = (
        ("position_id", "position_id"),
        ("position_observed_at", "broker_state_observed_at"),
        ("position_side", "side"),
        ("position_reconciliation_status", "reconciliation_status"),
        ("quantity_profile_version", "quantity_profile_version"),
        ("quantity_unit", "quantity_unit"),
        ("quantity_asset", "quantity_asset"),
    )
    for action_field, position_field in position_pairs:
        if action.get(action_field) != current_position.get(position_field):
            raise ProtectionAuthorityError(
                "POSITION_ACTION_POSITION_MISMATCH",
                f"PositionAction.{action_field} does not match current Position.{position_field}",
            )

    action_quantity = _parse_positive_decimal(action.get("quantity"), "PositionAction.quantity")
    if action_quantity != position_facts["actual_quantity"]:
        raise ProtectionAuthorityError(
            "PROTECTION_QUANTITY_NOT_ACTUAL_EXPOSURE",
            "PositionAction.quantity must equal exact current Position.actual_quantity",
        )
    if action_quantity > plan_facts["maximum_quantity"]:
        raise ProtectionAuthorityError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "current actual exposure exceeds parent ApprovedTradePlan maximum",
        )

    action_protection = _normalize_protection_instruction(
        action.get("protection_instruction"),
        "PositionAction.protection_instruction",
    )
    if action_protection != plan_facts["protection_instruction"]:
        raise ProtectionAuthorityError(
            "PROTECTION_BOUND_MISMATCH",
            "PositionAction protection bounds do not equal the exact parent ApprovedTradePlan bounds",
        )

    action_observed_at = _parse_utc(
        action.get("position_observed_at"),
        "PositionAction.position_observed_at",
    )
    if action_observed_at != position_facts["observed_at"]:
        raise ProtectionAuthorityError(
            "POSITION_OBSERVATION_MISMATCH",
            "PositionAction source observation is not the exact current Position observation",
        )
    created_at = _parse_utc(action.get("created_at"), "PositionAction.created_at")
    expires_at = _parse_utc(action.get("expires_at"), "PositionAction.expires_at")
    if created_at < action_observed_at:
        raise ProtectionAuthorityError(
            "ACTION_BEFORE_POSITION_OBSERVATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expires_at <= created_at:
        raise ProtectionAuthorityError(
            "INVALID_ACTION_EXPIRY",
            "PositionAction.expires_at must be after created_at",
        )
    if now_utc >= expires_at:
        raise ProtectionAuthorityError("POSITION_ACTION_EXPIRED", "PositionAction is expired")

    return {
        "quantity": action_quantity,
        "stop_level": action_protection[0],
    }


def prepare_protection_order(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    *,
    now: datetime,
) -> OrderRequest:
    """Mechanically translate accepted protection-v0.1 authority into one canonical STOP_MARKET request."""
    facts = validate_protection_authority(
        action,
        parent_plan,
        current_position,
        now=now,
    )
    client_order_id = stable_position_action_client_order_id(
        action["position_action_id"],
        ORDER_ROLE,
    )
    side = Side.SELL if action["position_side"] == "LONG" else Side.BUY
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_order_id),
        trade_plan_id=action["trade_plan_id"],
        client_order_id=client_order_id,
        symbol=action["symbol"],
        side=side,
        order_type=ORDER_TYPE,
        quantity=facts["quantity"],
        quantity_profile_version=action["quantity_profile_version"],
        quantity_unit=action["quantity_unit"],
        quantity_asset=action["quantity_asset"],
        created_at=_require_utc_datetime(now, "now"),
        authorization_type=AUTHORIZATION_TYPE,
        position_action_id=action["position_action_id"],
        position_id=action["position_id"],
        risk_decision_id=action["risk_decision_id"],
        order_role=ORDER_ROLE,
        limit_price=None,
        stop_price=facts["stop_level"],
        reduce_only=True,
        time_in_force=None,
    )
