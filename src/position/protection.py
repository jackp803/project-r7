from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SCHEMA_VERSION = "contracts-v0.1"
PROTECTION_PROFILE_VERSION = "protection-v0.1"
PROTECTION_ACTION = "PROTECT"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
CANONICAL_BTC_SYMBOL = "BTC_USDT_PERP"
CANONICAL_BTC_ASSET = "BTC"
CONSISTENT = "CONSISTENT"
OPEN_UNPROTECTED = "OPEN_UNPROTECTED"


class ProtectionActionError(ValueError):
    """Fail-closed validation error for the E5 protection-v0.1 boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtectionActionError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ProtectionActionError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise ProtectionActionError("INVALID_DECIMAL", f"{field} must be Decimal or a decimal string")
    if not parsed.is_finite():
        raise ProtectionActionError("INVALID_DECIMAL", f"{field} must be finite")
    return parsed


def _positive_decimal(value: Any, field: str) -> Decimal:
    parsed = _decimal(value, field)
    if parsed <= 0:
        raise ProtectionActionError("NON_POSITIVE_DECIMAL", f"{field} must be > 0")
    return parsed


def _utc_text(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtectionActionError("INVALID_TIMESTAMP", f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionActionError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionActionError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _utc_datetime(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ProtectionActionError("INVALID_TIMESTAMP", f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ProtectionActionError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
    return value.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_action_id(material: Mapping[str, Any]) -> str:
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return "posact_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_parent_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise ProtectionActionError("INVALID_PARENT_PLAN", "ApprovedTradePlan must be a mapping")

    required = (
        "schema_version",
        "trade_plan_id",
        "risk_decision_id",
        "symbol",
        "direction",
        "quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "protection_instruction",
        "risk_policy_version",
    )
    missing = [field for field in required if field not in plan]
    if missing:
        raise ProtectionActionError("PARENT_PLAN_INCOMPLETE", f"missing parent fields: {missing}")
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionActionError("UNSUPPORTED_SCHEMA_VERSION", "parent plan schema_version is unsupported")

    for field in ("trade_plan_id", "risk_decision_id", "symbol", "risk_policy_version"):
        _nonempty_text(plan.get(field), f"ApprovedTradePlan.{field}")

    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise ProtectionActionError("INVALID_PARENT_DIRECTION", "parent plan direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise ProtectionActionError("UNSUPPORTED_QUANTITY_PROFILE", "parent quantity profile must be base-asset-v0.1")
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise ProtectionActionError("UNSUPPORTED_QUANTITY_UNIT", "parent quantity unit must be BASE_ASSET")
    quantity_asset = _nonempty_text(plan.get("quantity_asset"), "ApprovedTradePlan.quantity_asset")
    if plan.get("symbol") == CANONICAL_BTC_SYMBOL and quantity_asset != CANONICAL_BTC_ASSET:
        raise ProtectionActionError("QUANTITY_ASSET_MISMATCH", "BTC_USDT_PERP parent quantity asset must be BTC")

    maximum_quantity = _positive_decimal(plan.get("quantity"), "ApprovedTradePlan.quantity")

    instruction = plan.get("protection_instruction")
    if not isinstance(instruction, Mapping):
        raise ProtectionActionError("INVALID_PROTECTION_INSTRUCTION", "parent protection_instruction must be a mapping")
    required_instruction = {"stop_level", "max_hold_seconds"}
    missing_instruction = sorted(required_instruction - set(instruction.keys()))
    if missing_instruction:
        raise ProtectionActionError(
            "PROTECTION_INSTRUCTION_INCOMPLETE",
            f"missing protection fields: {missing_instruction}",
        )
    _positive_decimal(instruction.get("stop_level"), "protection_instruction.stop_level")
    if instruction.get("target_level") is not None:
        _positive_decimal(instruction.get("target_level"), "protection_instruction.target_level")
    max_hold_seconds = instruction.get("max_hold_seconds")
    if type(max_hold_seconds) is not int or max_hold_seconds <= 0:
        raise ProtectionActionError(
            "INVALID_MAX_HOLD_SECONDS",
            "protection_instruction.max_hold_seconds must be a positive integer",
        )

    copied_instruction: dict[str, Any] = {
        "stop_level": instruction["stop_level"],
        "max_hold_seconds": max_hold_seconds,
    }
    if instruction.get("target_level") is not None:
        copied_instruction["target_level"] = instruction["target_level"]

    return {
        "maximum_quantity": maximum_quantity,
        "protection_instruction": copied_instruction,
    }


def _validate_position(position: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(position, Mapping):
        raise ProtectionActionError("INVALID_POSITION", "Position observation must be a mapping")

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
        raise ProtectionActionError("POSITION_INCOMPLETE", f"missing Position fields: {missing}")
    if position.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionActionError("UNSUPPORTED_SCHEMA_VERSION", "Position schema_version is unsupported")

    _nonempty_text(position.get("position_id"), "Position.position_id")
    _nonempty_text(position.get("symbol"), "Position.symbol")
    if position.get("side") not in {"LONG", "SHORT"}:
        raise ProtectionActionError("INVALID_POSITION_SIDE", "Position.side must be LONG or SHORT")
    if position.get("reconciliation_status") != CONSISTENT:
        raise ProtectionActionError(
            "POSITION_RECONCILIATION_NOT_CONSISTENT",
            "ordinary PROTECT requires reconciliation_status=CONSISTENT",
        )
    if position.get("lifecycle_state") != OPEN_UNPROTECTED:
        raise ProtectionActionError(
            "POSITION_NOT_OPEN_UNPROTECTED",
            "initial protection requires lifecycle_state=OPEN_UNPROTECTED",
        )

    actual_quantity = _positive_decimal(position.get("actual_quantity"), "Position.actual_quantity")
    _positive_decimal(position.get("average_entry_price"), "Position.average_entry_price")
    opened_at = _utc_text(position.get("opened_at"), "Position.opened_at")
    observed_at = _utc_text(position.get("broker_state_observed_at"), "Position.broker_state_observed_at")
    if observed_at < opened_at:
        raise ProtectionActionError(
            "POSITION_TIME_INCONSISTENT",
            "broker_state_observed_at cannot be before opened_at",
        )

    if position.get("symbol") != plan.get("symbol"):
        raise ProtectionActionError("POSITION_SYMBOL_MISMATCH", "Position symbol does not match parent plan")
    if position.get("side") != plan.get("direction"):
        raise ProtectionActionError("POSITION_SIDE_MISMATCH", "Position side does not match parent plan direction")
    if position.get("quantity_profile_version") != plan.get("quantity_profile_version"):
        raise ProtectionActionError("POSITION_QUANTITY_PROFILE_MISMATCH", "Position quantity profile does not match parent plan")
    if position.get("quantity_unit") != plan.get("quantity_unit"):
        raise ProtectionActionError("POSITION_QUANTITY_UNIT_MISMATCH", "Position quantity unit does not match parent plan")
    if position.get("quantity_asset") != plan.get("quantity_asset"):
        raise ProtectionActionError("POSITION_QUANTITY_ASSET_MISMATCH", "Position quantity asset does not match parent plan")

    return {
        "actual_quantity": actual_quantity,
        "observed_at": observed_at,
    }


def _identity_material(action: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "action": action.get("action"),
        "trade_plan_id": action.get("trade_plan_id"),
        "risk_decision_id": action.get("risk_decision_id"),
        "position_id": action.get("position_id"),
        "symbol": action.get("symbol"),
        "position_side": action.get("position_side"),
        "position_observed_at": action.get("position_observed_at"),
        "position_reconciliation_status": action.get("position_reconciliation_status"),
        "quantity": action.get("quantity"),
        "quantity_profile_version": action.get("quantity_profile_version"),
        "quantity_unit": action.get("quantity_unit"),
        "quantity_asset": action.get("quantity_asset"),
        "protection_instruction": action.get("protection_instruction"),
        "risk_policy_version": action.get("risk_policy_version"),
        "created_at": action.get("created_at"),
        "expires_at": action.get("expires_at"),
    }


def validate_protection_action(
    action: Mapping[str, Any],
    position: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    *,
    now: datetime,
) -> None:
    """Validate one executable E5 protection-v0.1 PROTECT authorization.

    This is an E5 producer-side contract check only. It does not translate or
    submit an E4 OrderRequest and it does not mark protection as verified.
    """

    if not isinstance(action, Mapping):
        raise ProtectionActionError("INVALID_POSITION_ACTION", "PositionAction must be a mapping")
    plan_facts = _validate_parent_plan(parent_plan)
    position_facts = _validate_position(position, parent_plan)

    required = (
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
    )
    missing = [field for field in required if field not in action]
    if missing:
        raise ProtectionActionError("POSITION_ACTION_INCOMPLETE", f"missing PositionAction fields: {missing}")
    if action.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionActionError("UNSUPPORTED_SCHEMA_VERSION", "PositionAction schema_version is unsupported")
    if action.get("protection_profile_version") != PROTECTION_PROFILE_VERSION:
        raise ProtectionActionError("UNSUPPORTED_PROTECTION_PROFILE", "executable protection requires protection-v0.1")
    if action.get("action") != PROTECTION_ACTION:
        raise ProtectionActionError("UNSUPPORTED_PROTECTION_ACTION", "protection-v0.1 executes PROTECT only")
    if action.get("reason_codes") not in ([], ()):
        raise ProtectionActionError("POSITION_ACTION_REASON_MISMATCH", "ordinary PROTECT must not carry rejection reasons")

    lineage_pairs = (
        ("trade_plan_id", "trade_plan_id"),
        ("risk_decision_id", "risk_decision_id"),
        ("risk_policy_version", "risk_policy_version"),
        ("symbol", "symbol"),
    )
    for action_field, plan_field in lineage_pairs:
        if action.get(action_field) != parent_plan.get(plan_field):
            raise ProtectionActionError("POSITION_ACTION_LINEAGE_MISMATCH", f"{action_field} does not match parent plan")

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
        if action.get(action_field) != position.get(position_field):
            raise ProtectionActionError("POSITION_ACTION_POSITION_MISMATCH", f"{action_field} does not match source Position")

    action_quantity = _positive_decimal(action.get("quantity"), "PositionAction.quantity")
    if action_quantity != position_facts["actual_quantity"]:
        raise ProtectionActionError(
            "PROTECTION_QUANTITY_NOT_ACTUAL_EXPOSURE",
            "PositionAction.quantity must equal exact Position.actual_quantity",
        )
    if action_quantity > plan_facts["maximum_quantity"]:
        raise ProtectionActionError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "actual exposure exceeds the parent ApprovedTradePlan maximum",
        )

    if action.get("protection_instruction") != plan_facts["protection_instruction"]:
        raise ProtectionActionError(
            "PROTECTION_BOUND_MISMATCH",
            "PositionAction protection bounds must exactly equal parent ApprovedTradePlan bounds",
        )

    created_at = _utc_text(action.get("created_at"), "PositionAction.created_at")
    expires_at = _utc_text(action.get("expires_at"), "PositionAction.expires_at")
    if created_at < position_facts["observed_at"]:
        raise ProtectionActionError(
            "POSITION_OBSERVATION_AFTER_ACTION_CREATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expires_at <= created_at:
        raise ProtectionActionError("INVALID_ACTION_EXPIRY", "PositionAction.expires_at must be after created_at")

    now_utc = _utc_datetime(now, "now")
    if now_utc >= expires_at:
        raise ProtectionActionError("POSITION_ACTION_EXPIRED", "PositionAction is expired")

    expected_id = _stable_action_id(_identity_material(action))
    if action.get("position_action_id") != expected_id:
        raise ProtectionActionError(
            "POSITION_ACTION_ID_MISMATCH",
            "position_action_id does not match authority-bearing material",
        )


def build_protect_position_action(
    position: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    *,
    created_at: datetime,
    expires_at: datetime,
) -> dict[str, Any]:
    """Build E5's provider-neutral protection-v0.1 PROTECT authorization.

    The source Position.actual_quantity is authoritative. Creating this action
    does not change the lifecycle from OPEN_UNPROTECTED and does not imply
    PROTECTION_VERIFIED.
    """

    plan_facts = _validate_parent_plan(parent_plan)
    position_facts = _validate_position(position, parent_plan)
    created = _utc_datetime(created_at, "created_at")
    expiry = _utc_datetime(expires_at, "expires_at")

    if created < position_facts["observed_at"]:
        raise ProtectionActionError(
            "POSITION_OBSERVATION_AFTER_ACTION_CREATION",
            "PositionAction cannot be created before its source Position observation",
        )
    if expiry <= created:
        raise ProtectionActionError("INVALID_ACTION_EXPIRY", "expires_at must be after created_at")
    if position_facts["actual_quantity"] > plan_facts["maximum_quantity"]:
        raise ProtectionActionError(
            "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            "actual exposure exceeds the parent ApprovedTradePlan maximum",
        )

    action: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protection_profile_version": PROTECTION_PROFILE_VERSION,
        "trade_plan_id": parent_plan["trade_plan_id"],
        "risk_decision_id": parent_plan["risk_decision_id"],
        "position_id": position["position_id"],
        "action": PROTECTION_ACTION,
        "reason_codes": [],
        "risk_policy_version": parent_plan["risk_policy_version"],
        "symbol": parent_plan["symbol"],
        "position_side": position["side"],
        "position_observed_at": position["broker_state_observed_at"],
        "position_reconciliation_status": CONSISTENT,
        "quantity": format(position_facts["actual_quantity"], "f"),
        "quantity_profile_version": parent_plan["quantity_profile_version"],
        "quantity_unit": parent_plan["quantity_unit"],
        "quantity_asset": parent_plan["quantity_asset"],
        "protection_instruction": dict(plan_facts["protection_instruction"]),
        "created_at": _fmt_utc(created),
        "expires_at": _fmt_utc(expiry),
    }
    action["position_action_id"] = _stable_action_id(_identity_material(action))

    # Producer-side self-check at creation time. This validates contract shape,
    # exact source/parent binding, and action freshness without executing E4.
    validate_protection_action(action, position, parent_plan, now=created)
    return action
