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
TRADE_RESULT_PROFILE_VERSION = "trade-result-v0.1"
PNL_PROFILE_VERSION = "linear-base-asset-pnl-v0.1"
FUNDING_EVIDENCE_PROFILE_VERSION = "funding-allocation-v0.1"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
QUANTITY_ASSET = "BTC"
PNL_CURRENCY = "USDT"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
CONSISTENT = "CONSISTENT"

EXIT = "EXIT"
EMERGENCY_EXIT = "EMERGENCY_EXIT"
PROTECT = "PROTECT"
POSITION_EXIT_ROLE = "POSITION_EXIT"
EMERGENCY_EXIT_ROLE = "EMERGENCY_EXIT"
PROTECTION_STOP_ROLE = "PROTECTION_STOP"
POSITION_ACTION_AUTHORIZATION = "POSITION_ACTION"
MARKET = "MARKET"
STOP_MARKET = "STOP_MARKET"
ZERO_CONFIRMED = "ZERO_CONFIRMED"
INCLUDED = "INCLUDED"
PROTECTION_STOP_FILLED_REASON = "PROTECTION_STOP_FILLED"
FUNDING_INTERVAL_SEMANTICS = "START_INCLUSIVE_END_EXCLUSIVE"
SUPPORTED_FUNDING_SOURCE_KINDS = frozenset({"PAPER_MODEL", "BROKER_LEDGER"})

_FUNDING_IDENTITY_FIELDS = (
    "schema_version",
    "funding_evidence_profile_version",
    "source_kind",
    "source",
    "source_version",
    "source_material_hash",
    "source_record_count",
    "source_complete_through",
    "trade_plan_id",
    "position_id",
    "symbol",
    "interval_start",
    "interval_end",
    "interval_semantics",
    "status",
    "funding_cost",
    "cost_currency",
)
_FUNDING_REQUIRED_FIELDS = frozenset(
    _FUNDING_IDENTITY_FIELDS + ("funding_evidence_id", "calculated_at")
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_FUNDEV_RE = re.compile(r"^fundev_[0-9a-f]{64}$")
_DECIMAL_STRING_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class TradeResultBuildError(ValueError):
    """Fail-closed validation error for trade-result-v0.1 finalization."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FundingEvidence:
    """Legacy E5-private helper retained only for migration diagnostics.

    Current Gate B finalization MUST NOT accept this object. build_trade_result()
    requires the canonical serialized funding-allocation-v0.1 shared evidence
    mapping defined by E7. This type is intentionally not a shared DTO.
    """

    status: str
    source_version: str
    position_id: str
    interval_start: datetime | str
    interval_end: datetime | str
    funding_cost: Decimal | str | None = None


@dataclass(frozen=True)
class TradeResultBuildOutcome:
    """E5-internal lifecycle/result outcome; not a shared serialized DTO."""

    trade_result: dict[str, Any]
    event: PositionEvent
    next_state: PositionLifecycleState


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _nonempty_text(value: Any, field: str) -> str:
    value = _value(value)
    if not isinstance(value, str) or not value.strip():
        raise TradeResultBuildError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    return value.strip()


def _canonical_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise TradeResultBuildError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    if value != value.strip():
        raise TradeResultBuildError("NONCANONICAL_TEXT_FIELD", f"{field} must not contain surrounding whitespace")
    return value


def _decimal(
    value: Any,
    field: str,
    *,
    allow_zero: bool = True,
    signed: bool = False,
) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise TradeResultBuildError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise TradeResultBuildError(
            "INVALID_DECIMAL",
            f"{field} must be Decimal or a base-10 decimal string",
        )
    if not parsed.is_finite():
        raise TradeResultBuildError("INVALID_DECIMAL", f"{field} must be finite")
    if not signed and (parsed < 0 or (parsed == 0 and not allow_zero)):
        comparator = ">= 0" if allow_zero else "> 0"
        raise TradeResultBuildError("INVALID_DECIMAL", f"{field} must be {comparator}")
    return parsed


def _positive_decimal(value: Any, field: str) -> Decimal:
    return _decimal(value, field, allow_zero=False, signed=False)


def _canonical_signed_decimal_string(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_STRING_RE.fullmatch(value) is None:
        raise TradeResultBuildError(
            "FUNDING_COST_INVALID",
            f"{field} must be a canonical finite base-10 decimal string",
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise TradeResultBuildError("FUNDING_COST_INVALID", f"{field} is not a valid decimal") from exc
    if not parsed.is_finite():
        raise TradeResultBuildError("FUNDING_COST_INVALID", f"{field} must be finite")
    if parsed == 0 and value.startswith("-"):
        raise TradeResultBuildError("FUNDING_COST_INVALID", f"{field} must not encode negative zero")
    return parsed


def _utc(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise TradeResultBuildError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str) or not value.endswith("Z"):
        raise TradeResultBuildError("INVALID_TIMESTAMP", f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TradeResultBuildError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise TradeResultBuildError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _serialized_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise TradeResultBuildError(
            "FUNDING_TIMESTAMP_NOT_SERIALIZED",
            f"{field} must be an RFC 3339 UTC Z string at the shared boundary",
        )
    return _utc(value, field)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fmt_decimal(value: Decimal) -> str:
    return format(value, "f")


def _side(value: Any, field: str) -> str:
    normalized = _nonempty_text(_value(value), field)
    if normalized not in {"BUY", "SELL"}:
        raise TradeResultBuildError("INVALID_SIDE", f"{field} must be BUY or SELL")
    return normalized


def _sequence(value: Any, field: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TradeResultBuildError("INVALID_SEQUENCE", f"{field} must be a sequence")
    return tuple(value)


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TradeResultBuildError("INVALID_MAPPING", f"{field} must be a mapping")
    return value


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _validate_parent_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    plan = _require_mapping(plan, "ApprovedTradePlan")
    required = {
        "schema_version",
        "trade_plan_id",
        "risk_decision_id",
        "strategy_id",
        "strategy_version",
        "symbol",
        "direction",
        "quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "created_at",
        "expires_at",
        "risk_policy_version",
    }
    missing = sorted(required - set(plan.keys()))
    if missing:
        raise TradeResultBuildError("PARENT_PLAN_INCOMPLETE", "missing parent fields: " + ", ".join(missing))
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise TradeResultBuildError("UNSUPPORTED_SCHEMA_VERSION", "ApprovedTradePlan schema_version is unsupported")
    if plan.get("symbol") != CANONICAL_SYMBOL:
        raise TradeResultBuildError("UNSUPPORTED_SYMBOL", "trade-result-v0.1 supports BTC_USDT_PERP only")
    if plan.get("direction") not in {"LONG", "SHORT"}:
        raise TradeResultBuildError("INVALID_DIRECTION", "ApprovedTradePlan.direction must be LONG or SHORT")
    if plan.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise TradeResultBuildError("UNSUPPORTED_QUANTITY_PROFILE", "parent quantity profile must be base-asset-v0.1")
    if plan.get("quantity_unit") != QUANTITY_UNIT:
        raise TradeResultBuildError("UNSUPPORTED_QUANTITY_UNIT", "parent quantity unit must be BASE_ASSET")
    if plan.get("quantity_asset") != QUANTITY_ASSET:
        raise TradeResultBuildError("UNSUPPORTED_QUANTITY_ASSET", "BTC_USDT_PERP quantity asset must be BTC")
    for field in (
        "trade_plan_id",
        "risk_decision_id",
        "strategy_id",
        "strategy_version",
        "risk_policy_version",
    ):
        _nonempty_text(plan.get(field), f"ApprovedTradePlan.{field}")
    maximum_quantity = _positive_decimal(plan.get("quantity"), "ApprovedTradePlan.quantity")
    created_at = _utc(plan.get("created_at"), "ApprovedTradePlan.created_at")
    expires_at = _utc(plan.get("expires_at"), "ApprovedTradePlan.expires_at")
    if expires_at <= created_at:
        raise TradeResultBuildError("INVALID_PARENT_PLAN_EXPIRY", "ApprovedTradePlan.expires_at must be after created_at")
    return {
        "direction": plan["direction"],
        "entry_side": "BUY" if plan["direction"] == "LONG" else "SELL",
        "exit_side": "SELL" if plan["direction"] == "LONG" else "BUY",
        "maximum_quantity": maximum_quantity,
    }


def _order_request_facts(request: Any, field: str) -> dict[str, Any]:
    if _field(request, "schema_version") != SCHEMA_VERSION:
        raise TradeResultBuildError("ORDER_REQUEST_SCHEMA_INVALID", f"{field}.schema_version is unsupported")
    return {
        "request": request,
        "order_request_id": _nonempty_text(_field(request, "order_request_id"), f"{field}.order_request_id"),
        "client_order_id": _nonempty_text(_field(request, "client_order_id"), f"{field}.client_order_id"),
        "trade_plan_id": _nonempty_text(_field(request, "trade_plan_id"), f"{field}.trade_plan_id"),
        "symbol": _nonempty_text(_field(request, "symbol"), f"{field}.symbol"),
        "side": _side(_field(request, "side"), f"{field}.side"),
        "order_type": _nonempty_text(_field(request, "order_type"), f"{field}.order_type"),
        "quantity": _positive_decimal(_field(request, "quantity"), f"{field}.quantity"),
        "quantity_profile_version": _nonempty_text(
            _field(request, "quantity_profile_version"), f"{field}.quantity_profile_version"
        ),
        "quantity_unit": _nonempty_text(_field(request, "quantity_unit"), f"{field}.quantity_unit"),
        "quantity_asset": _nonempty_text(_field(request, "quantity_asset"), f"{field}.quantity_asset"),
    }


def _validate_entry_requests(
    requests: Sequence[Any],
    plan: Mapping[str, Any],
    expected_side: str,
) -> dict[str, dict[str, Any]]:
    values = _sequence(requests, "entry_order_requests")
    if not values:
        raise TradeResultBuildError("ENTRY_ORDER_REQUESTS_REQUIRED", "at least one entry OrderRequest is required")
    by_client: dict[str, dict[str, Any]] = {}
    request_ids: set[str] = set()
    for index, request in enumerate(values):
        facts = _order_request_facts(request, f"entry_order_requests[{index}]")
        if facts["client_order_id"] in by_client or facts["order_request_id"] in request_ids:
            raise TradeResultBuildError("DUPLICATE_ENTRY_ORDER_REQUEST", "entry OrderRequest identities must be unique")
        if facts["trade_plan_id"] != plan["trade_plan_id"] or facts["symbol"] != plan["symbol"]:
            raise TradeResultBuildError("ENTRY_ORDER_LINEAGE_MISMATCH", "entry OrderRequest plan/symbol lineage mismatch")
        if facts["side"] != expected_side or facts["order_type"] != MARKET:
            raise TradeResultBuildError("ENTRY_ORDER_SEMANTICS_MISMATCH", "entry OrderRequest side/type is incompatible")
        if (
            facts["quantity_profile_version"] != plan["quantity_profile_version"]
            or facts["quantity_unit"] != plan["quantity_unit"]
            or facts["quantity_asset"] != plan["quantity_asset"]
        ):
            raise TradeResultBuildError("ENTRY_ORDER_QUANTITY_PROFILE_MISMATCH", "entry OrderRequest quantity semantics mismatch")
        if _field(request, "authorization_type") is not None:
            raise TradeResultBuildError("ENTRY_ORDER_AUTHORITY_MISMATCH", "entry OrderRequest must remain plan-authorized")
        if _field(request, "position_action_id") is not None or _field(request, "position_id") is not None:
            raise TradeResultBuildError("ENTRY_ORDER_AUTHORITY_MISMATCH", "entry OrderRequest cannot carry PositionAction authority")
        if _field(request, "order_role") is not None:
            raise TradeResultBuildError("ENTRY_ORDER_ROLE_MISMATCH", "entry OrderRequest must not carry an exit/protection role")
        by_client[facts["client_order_id"]] = facts
        request_ids.add(facts["order_request_id"])
    return by_client


def _fill_facts(fill: Any, field: str) -> dict[str, Any]:
    if _field(fill, "schema_version") != SCHEMA_VERSION:
        raise TradeResultBuildError("FILL_SCHEMA_INVALID", f"{field}.schema_version is unsupported")
    fee_raw = _field(fill, "fee")
    if fee_raw is None:
        raise TradeResultBuildError("FILL_FEE_MISSING", f"{field}.fee must be explicitly known")
    fee = _decimal(fee_raw, f"{field}.fee", signed=True)
    fee_currency_raw = _field(fill, "fee_currency")
    fee_currency = None if fee_currency_raw is None else _nonempty_text(fee_currency_raw, f"{field}.fee_currency")
    if fee != 0 and fee_currency != PNL_CURRENCY:
        raise TradeResultBuildError("UNSUPPORTED_FEE_CURRENCY", f"{field} non-zero fee must be USDT")
    if fee == 0 and fee_currency not in {None, PNL_CURRENCY}:
        raise TradeResultBuildError("UNSUPPORTED_FEE_CURRENCY", f"{field} zero fee currency must be absent or USDT")
    return {
        "fill": fill,
        "fill_id": _nonempty_text(_field(fill, "fill_id"), f"{field}.fill_id"),
        "broker_order_id": _nonempty_text(_field(fill, "broker_order_id"), f"{field}.broker_order_id"),
        "client_order_id": _nonempty_text(_field(fill, "client_order_id"), f"{field}.client_order_id"),
        "trade_plan_id": _nonempty_text(_field(fill, "trade_plan_id"), f"{field}.trade_plan_id"),
        "symbol": _nonempty_text(_field(fill, "symbol"), f"{field}.symbol"),
        "side": _side(_field(fill, "side"), f"{field}.side"),
        "quantity": _positive_decimal(_field(fill, "quantity"), f"{field}.quantity"),
        "price": _positive_decimal(_field(fill, "price"), f"{field}.price"),
        "filled_at": _utc(_field(fill, "filled_at"), f"{field}.filled_at"),
        "fee": fee,
        "fee_currency": fee_currency,
        "position_action_id": _field(fill, "position_action_id"),
        "position_id": _field(fill, "position_id"),
        "order_role": _value(_field(fill, "order_role")),
    }


def _ordered_fill_facts(fills: Sequence[Any], field: str) -> list[dict[str, Any]]:
    values = _sequence(fills, field)
    if not values:
        raise TradeResultBuildError("FILL_SET_REQUIRED", f"{field} must be non-empty")
    facts = [_fill_facts(fill, f"{field}[{index}]") for index, fill in enumerate(values)]
    ids = [item["fill_id"] for item in facts]
    if len(ids) != len(set(ids)):
        raise TradeResultBuildError("DUPLICATE_FILL_ID", f"{field} contains duplicate fill_id")
    facts.sort(key=lambda item: (item["filled_at"], item["fill_id"]))
    return facts


def _validate_entry_fill_binding(
    fills: list[dict[str, Any]],
    requests_by_client: dict[str, dict[str, Any]],
    plan: Mapping[str, Any],
    expected_side: str,
) -> list[str]:
    used_clients: list[str] = []
    seen_clients: set[str] = set()
    quantity_by_client: dict[str, Decimal] = {}
    for facts in fills:
        if facts["trade_plan_id"] != plan["trade_plan_id"] or facts["symbol"] != plan["symbol"]:
            raise TradeResultBuildError("ENTRY_FILL_LINEAGE_MISMATCH", "entry Fill plan/symbol lineage mismatch")
        if facts["side"] != expected_side:
            raise TradeResultBuildError("ENTRY_FILL_SIDE_MISMATCH", "entry Fill side is inconsistent with parent direction")
        request = requests_by_client.get(facts["client_order_id"])
        if request is None:
            raise TradeResultBuildError(
                "ENTRY_FILL_REQUEST_BINDING_MISSING",
                "entry Fill must bind to an exact declared entry OrderRequest, not trade_plan_id alone",
            )
        if facts["position_action_id"] is not None or facts["position_id"] is not None or facts["order_role"] is not None:
            raise TradeResultBuildError("ENTRY_FILL_AUTHORITY_MISMATCH", "entry Fill cannot carry close/protection authority")
        quantity_by_client[facts["client_order_id"]] = quantity_by_client.get(
            facts["client_order_id"], Decimal("0")
        ) + facts["quantity"]
        if quantity_by_client[facts["client_order_id"]] > request["quantity"]:
            raise TradeResultBuildError("ENTRY_FILL_EXCEEDS_REQUEST", "entry Fill quantity exceeds exact declared OrderRequest")
        if facts["client_order_id"] not in seen_clients:
            seen_clients.add(facts["client_order_id"])
            used_clients.append(facts["client_order_id"])
    if seen_clients != set(requests_by_client):
        raise TradeResultBuildError("UNUSED_ENTRY_ORDER_REQUEST", "every declared entry OrderRequest must have included Fill evidence")
    return [requests_by_client[client]["order_request_id"] for client in used_clients]


def _validate_explicit_authority(
    action: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> tuple[str, list[str], str]:
    action = _require_mapping(action, "exit_authority")
    if action.get("schema_version") != SCHEMA_VERSION or action.get("close_profile_version") != "close-v0.1":
        raise TradeResultBuildError("UNSUPPORTED_EXIT_AUTHORITY", "explicit closure requires close-v0.1 authority")
    action_type = action.get("action")
    if action_type not in {EXIT, EMERGENCY_EXIT}:
        raise TradeResultBuildError("UNSUPPORTED_EXIT_AUTHORITY", "explicit closure authority must be EXIT or EMERGENCY_EXIT")
    for action_field, plan_field in (
        ("trade_plan_id", "trade_plan_id"),
        ("risk_decision_id", "risk_decision_id"),
        ("strategy_id", "strategy_id"),
        ("strategy_version", "strategy_version"),
        ("risk_policy_version", "risk_policy_version"),
        ("symbol", "symbol"),
    ):
        if action.get(action_field) != plan.get(plan_field):
            raise TradeResultBuildError("EXIT_AUTHORITY_LINEAGE_MISMATCH", f"exit authority {action_field} mismatch")
    _nonempty_text(action.get("position_action_id"), "exit_authority.position_action_id")
    _nonempty_text(action.get("position_id"), "exit_authority.position_id")
    if action.get("position_side") != plan.get("direction"):
        raise TradeResultBuildError("EXIT_AUTHORITY_SIDE_MISMATCH", "exit authority position side mismatch")
    if action.get("position_reconciliation_status") != CONSISTENT:
        raise TradeResultBuildError("EXIT_AUTHORITY_RECONCILIATION_MISMATCH", "exit authority must bind CONSISTENT Position truth")
    source_state = action.get("source_lifecycle_state")
    if action_type == EXIT and source_state not in {"OPEN_UNPROTECTED", "OPEN_PROTECTED", "PROFIT_PROTECTED"}:
        raise TradeResultBuildError("EXIT_AUTHORITY_SOURCE_STATE_INVALID", "EXIT source lifecycle is not an accepted open state")
    if action_type == EMERGENCY_EXIT and source_state != "EMERGENCY":
        raise TradeResultBuildError("EXIT_AUTHORITY_SOURCE_STATE_INVALID", "EMERGENCY_EXIT source lifecycle must be EMERGENCY")
    if action.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION or action.get("quantity_unit") != QUANTITY_UNIT or action.get("quantity_asset") != QUANTITY_ASSET:
        raise TradeResultBuildError("EXIT_AUTHORITY_QUANTITY_PROFILE_MISMATCH", "exit authority quantity semantics mismatch")
    if action.get("close_order_type") != MARKET:
        raise TradeResultBuildError("EXIT_AUTHORITY_ORDER_TYPE_MISMATCH", "close-v0.1 requires MARKET")
    _positive_decimal(action.get("quantity"), "exit_authority.quantity")
    _utc(action.get("position_observed_at"), "exit_authority.position_observed_at")
    created_at = _utc(action.get("created_at"), "exit_authority.created_at")
    expires_at = _utc(action.get("expires_at"), "exit_authority.expires_at")
    if expires_at <= created_at:
        raise TradeResultBuildError("EXIT_AUTHORITY_EXPIRY_INVALID", "exit authority expires_at must follow created_at")
    reasons = _sequence(action.get("reason_codes"), "exit_authority.reason_codes")
    if not reasons:
        raise TradeResultBuildError("EXIT_REASON_CODES_REQUIRED", "explicit exit authority reason_codes must be non-empty")
    normalized_reasons = [_nonempty_text(reason, "exit_authority.reason_codes[]") for reason in reasons]
    if len(normalized_reasons) != len(set(normalized_reasons)):
        raise TradeResultBuildError("DUPLICATE_EXIT_REASON_CODE", "exit authority reason_codes must not contain duplicates")
    expected_role = POSITION_EXIT_ROLE if action_type == EXIT else EMERGENCY_EXIT_ROLE
    return action_type, normalized_reasons, expected_role


def _validate_protection_authority(
    action: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> tuple[str, list[str], str]:
    action = _require_mapping(action, "exit_authority")
    if action.get("schema_version") != SCHEMA_VERSION or action.get("protection_profile_version") != "protection-v0.1":
        raise TradeResultBuildError("UNSUPPORTED_EXIT_AUTHORITY", "protection closure requires protection-v0.1 authority")
    if action.get("action") != PROTECT:
        raise TradeResultBuildError("UNSUPPORTED_EXIT_AUTHORITY", "protection closure authority must be PROTECT")
    for action_field, plan_field in (
        ("trade_plan_id", "trade_plan_id"),
        ("risk_decision_id", "risk_decision_id"),
        ("risk_policy_version", "risk_policy_version"),
        ("symbol", "symbol"),
    ):
        if action.get(action_field) != plan.get(plan_field):
            raise TradeResultBuildError("EXIT_AUTHORITY_LINEAGE_MISMATCH", f"protection authority {action_field} mismatch")
    _nonempty_text(action.get("position_action_id"), "exit_authority.position_action_id")
    _nonempty_text(action.get("position_id"), "exit_authority.position_id")
    if action.get("position_side") != plan.get("direction"):
        raise TradeResultBuildError("EXIT_AUTHORITY_SIDE_MISMATCH", "protection authority position side mismatch")
    if action.get("position_reconciliation_status") != CONSISTENT:
        raise TradeResultBuildError("EXIT_AUTHORITY_RECONCILIATION_MISMATCH", "protection authority must bind CONSISTENT Position truth")
    if action.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION or action.get("quantity_unit") != QUANTITY_UNIT or action.get("quantity_asset") != QUANTITY_ASSET:
        raise TradeResultBuildError("EXIT_AUTHORITY_QUANTITY_PROFILE_MISMATCH", "protection authority quantity semantics mismatch")
    _positive_decimal(action.get("quantity"), "exit_authority.quantity")
    instruction = action.get("protection_instruction")
    if not isinstance(instruction, Mapping) or instruction != plan.get("protection_instruction"):
        raise TradeResultBuildError("PROTECTION_BOUND_MISMATCH", "PROTECT authority must retain exact parent protection bounds")
    if action.get("reason_codes") not in ([], ()):
        raise TradeResultBuildError("PROTECTION_REASON_MISMATCH", "ordinary PROTECT authority must not invent close reasons")
    return PROTECT, [PROTECTION_STOP_FILLED_REASON], PROTECTION_STOP_ROLE


def _validate_exit_request(
    request: Any,
    authority: Mapping[str, Any],
    plan: Mapping[str, Any],
    expected_side: str,
    expected_role: str,
) -> dict[str, Any]:
    facts = _order_request_facts(request, "exit_order_request")
    if facts["trade_plan_id"] != plan["trade_plan_id"] or facts["symbol"] != plan["symbol"]:
        raise TradeResultBuildError("EXIT_ORDER_LINEAGE_MISMATCH", "exit OrderRequest plan/symbol lineage mismatch")
    if facts["side"] != expected_side:
        raise TradeResultBuildError("EXIT_ORDER_SIDE_MISMATCH", "exit OrderRequest must be opposite parent direction")
    if _field(request, "authorization_type") != POSITION_ACTION_AUTHORIZATION:
        raise TradeResultBuildError("EXIT_ORDER_AUTHORITY_MISMATCH", "exit OrderRequest must be PositionAction-authorized")
    if _field(request, "position_action_id") != authority.get("position_action_id"):
        raise TradeResultBuildError("EXIT_ORDER_AUTHORITY_MISMATCH", "exit OrderRequest position_action_id mismatch")
    if _field(request, "position_id") != authority.get("position_id"):
        raise TradeResultBuildError("EXIT_ORDER_POSITION_MISMATCH", "exit OrderRequest position_id mismatch")
    if _field(request, "risk_decision_id") != plan.get("risk_decision_id"):
        raise TradeResultBuildError("EXIT_ORDER_RISK_LINEAGE_MISMATCH", "exit OrderRequest risk_decision_id mismatch")
    if _value(_field(request, "order_role")) != expected_role:
        raise TradeResultBuildError("EXIT_ORDER_ROLE_MISMATCH", "exit OrderRequest order_role mismatch")
    if _field(request, "reduce_only") is not True:
        raise TradeResultBuildError("EXIT_ORDER_NOT_REDUCE_ONLY", "exit OrderRequest must be reduce_only=true")
    if facts["quantity"] != _positive_decimal(authority.get("quantity"), "exit_authority.quantity"):
        raise TradeResultBuildError("EXIT_ORDER_QUANTITY_MISMATCH", "exit OrderRequest quantity must equal E5 authority quantity")
    if facts["quantity_profile_version"] != QUANTITY_PROFILE_VERSION or facts["quantity_unit"] != QUANTITY_UNIT or facts["quantity_asset"] != QUANTITY_ASSET:
        raise TradeResultBuildError("EXIT_ORDER_QUANTITY_PROFILE_MISMATCH", "exit OrderRequest quantity semantics mismatch")
    if expected_role in {POSITION_EXIT_ROLE, EMERGENCY_EXIT_ROLE}:
        if facts["order_type"] != MARKET or _field(request, "stop_price") is not None:
            raise TradeResultBuildError("EXIT_ORDER_TYPE_MISMATCH", "explicit close requires MARKET without stop_price")
    else:
        if facts["order_type"] != STOP_MARKET:
            raise TradeResultBuildError("EXIT_ORDER_TYPE_MISMATCH", "protection close requires STOP_MARKET")
        instruction = authority.get("protection_instruction")
        if not isinstance(instruction, Mapping):
            raise TradeResultBuildError("PROTECTION_INSTRUCTION_MISSING", "PROTECT authority requires protection_instruction")
        stop_price = _field(request, "stop_price")
        if stop_price is None or _decimal(stop_price, "exit_order_request.stop_price") != _positive_decimal(
            instruction.get("stop_level"), "exit_authority.protection_instruction.stop_level"
        ):
            raise TradeResultBuildError("PROTECTION_STOP_PRICE_MISMATCH", "protection stop price does not match E5 authority")
    if _field(request, "limit_price") is not None or _field(request, "time_in_force") is not None:
        raise TradeResultBuildError("EXIT_ORDER_EXECUTION_FIELD_MISMATCH", "V0.1 exit request forbids limit_price/time_in_force")
    return facts


def _validate_exit_fill_binding(
    fills: list[dict[str, Any]],
    request: dict[str, Any],
    authority: Mapping[str, Any],
    plan: Mapping[str, Any],
    expected_side: str,
    expected_role: str,
) -> None:
    for facts in fills:
        if facts["trade_plan_id"] != plan["trade_plan_id"] or facts["symbol"] != plan["symbol"]:
            raise TradeResultBuildError("EXIT_FILL_LINEAGE_MISMATCH", "exit Fill plan/symbol lineage mismatch")
        if facts["client_order_id"] != request["client_order_id"]:
            raise TradeResultBuildError("EXIT_FILL_REQUEST_BINDING_MISMATCH", "exit Fill must bind to exact exit OrderRequest")
        if facts["side"] != expected_side:
            raise TradeResultBuildError("EXIT_FILL_SIDE_MISMATCH", "exit Fill side must be opposite parent direction")
        if facts["position_action_id"] != authority.get("position_action_id"):
            raise TradeResultBuildError("EXIT_FILL_AUTHORITY_MISMATCH", "exit Fill position_action_id mismatch")
        if facts["position_id"] != authority.get("position_id"):
            raise TradeResultBuildError("EXIT_FILL_POSITION_MISMATCH", "exit Fill position_id mismatch")
        if facts["order_role"] != expected_role:
            raise TradeResultBuildError("EXIT_FILL_ROLE_MISMATCH", "exit Fill order_role mismatch")


def _validate_final_position(
    position: Mapping[str, Any],
    plan: Mapping[str, Any],
    authority: Mapping[str, Any],
    earliest_entry_at: datetime,
    latest_exit_at: datetime,
) -> datetime:
    position = _require_mapping(position, "final_position")
    required = {
        "schema_version",
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "opened_at",
        "broker_state_observed_at",
        "reconciliation_status",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    }
    missing = sorted(required - set(position.keys()))
    if missing:
        raise TradeResultBuildError("FINAL_POSITION_INCOMPLETE", "final Position missing fields: " + ", ".join(missing))
    if position.get("schema_version") != SCHEMA_VERSION:
        raise TradeResultBuildError("FINAL_POSITION_SCHEMA_INVALID", "final Position schema_version is unsupported")
    if position.get("position_id") != authority.get("position_id"):
        raise TradeResultBuildError("FINAL_POSITION_ID_MISMATCH", "final Position position_id mismatch")
    if position.get("symbol") != plan.get("symbol") or position.get("side") != plan.get("direction"):
        raise TradeResultBuildError("FINAL_POSITION_LINEAGE_MISMATCH", "final Position symbol/side mismatch")
    if position.get("reconciliation_status") != CONSISTENT:
        raise TradeResultBuildError("FINAL_POSITION_NOT_CONSISTENT", "final Position must be reconciliation_status=CONSISTENT")
    if _decimal(position.get("actual_quantity"), "final_position.actual_quantity") != Decimal("0"):
        raise TradeResultBuildError("FINAL_POSITION_NOT_FLAT", "authoritative final Position actual_quantity must equal zero")
    if position.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION or position.get("quantity_unit") != QUANTITY_UNIT or position.get("quantity_asset") != QUANTITY_ASSET:
        raise TradeResultBuildError("FINAL_POSITION_QUANTITY_PROFILE_MISMATCH", "final Position quantity semantics mismatch")
    opened_at = _utc(position.get("opened_at"), "final_position.opened_at")
    if opened_at != earliest_entry_at:
        raise TradeResultBuildError("FINAL_POSITION_OPENED_AT_CONFLICT", "final Position opened_at conflicts with earliest entry Fill")
    observed_at = _utc(position.get("broker_state_observed_at"), "final_position.broker_state_observed_at")
    if observed_at < latest_exit_at:
        raise TradeResultBuildError("FINAL_POSITION_STALE", "final Position observation predates latest exit Fill")
    if position.get("closed_at") is not None and _utc(position.get("closed_at"), "final_position.closed_at") != observed_at:
        raise TradeResultBuildError("FINAL_POSITION_CLOSED_AT_CONFLICT", "final Position closed_at conflicts with flat observation")
    return observed_at


def _funding_identity_material(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {field: evidence[field] for field in _FUNDING_IDENTITY_FIELDS}


def _stable_funding_evidence_id(evidence: Mapping[str, Any]) -> str:
    material = _funding_identity_material(evidence)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "fundev_" + digest


def _validate_canonical_funding_evidence(
    evidence: Mapping[str, Any],
    *,
    trade_plan_id: str,
    position_id: str,
    symbol: str,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[str, Decimal, str, dict[str, Any]]:
    if not isinstance(evidence, Mapping):
        raise TradeResultBuildError(
            "CANONICAL_FUNDING_EVIDENCE_REQUIRED",
            "current Gate B finalization requires serialized funding-allocation-v0.1 evidence",
        )
    missing = sorted(_FUNDING_REQUIRED_FIELDS - set(evidence.keys()))
    if missing:
        raise TradeResultBuildError(
            "FUNDING_EVIDENCE_INCOMPLETE",
            "FundingAllocationEvidence missing required fields: " + ", ".join(missing),
        )
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise TradeResultBuildError("FUNDING_SCHEMA_UNSUPPORTED", "FundingAllocationEvidence schema_version is unsupported")
    if evidence.get("funding_evidence_profile_version") != FUNDING_EVIDENCE_PROFILE_VERSION:
        raise TradeResultBuildError("FUNDING_PROFILE_UNSUPPORTED", "FundingAllocationEvidence profile is unsupported")

    evidence_id = _canonical_text(evidence.get("funding_evidence_id"), "funding_evidence.funding_evidence_id")
    if _FUNDEV_RE.fullmatch(evidence_id) is None:
        raise TradeResultBuildError("FUNDING_EVIDENCE_ID_INVALID", "funding_evidence_id must be fundev_<sha256>")
    source_kind = _canonical_text(evidence.get("source_kind"), "funding_evidence.source_kind")
    if source_kind not in SUPPORTED_FUNDING_SOURCE_KINDS:
        raise TradeResultBuildError("FUNDING_SOURCE_KIND_UNSUPPORTED", "funding source_kind is unsupported")
    _canonical_text(evidence.get("source"), "funding_evidence.source")
    _canonical_text(evidence.get("source_version"), "funding_evidence.source_version")
    source_hash = _canonical_text(evidence.get("source_material_hash"), "funding_evidence.source_material_hash")
    if _SHA256_RE.fullmatch(source_hash) is None:
        raise TradeResultBuildError("FUNDING_SOURCE_HASH_INVALID", "source_material_hash must be lowercase SHA-256 hex")

    source_record_count = evidence.get("source_record_count")
    if type(source_record_count) is not int or source_record_count < 0:
        raise TradeResultBuildError("FUNDING_SOURCE_RECORD_COUNT_INVALID", "source_record_count must be a non-negative integer")

    source_complete_through = _serialized_utc(
        evidence.get("source_complete_through"), "funding_evidence.source_complete_through"
    )
    interval_start = _serialized_utc(evidence.get("interval_start"), "funding_evidence.interval_start")
    interval_end = _serialized_utc(evidence.get("interval_end"), "funding_evidence.interval_end")
    calculated_at = _serialized_utc(evidence.get("calculated_at"), "funding_evidence.calculated_at")
    if interval_start >= interval_end:
        raise TradeResultBuildError("FUNDING_INTERVAL_INVALID", "funding interval must be non-empty")
    if source_complete_through < interval_end:
        raise TradeResultBuildError("FUNDING_SOURCE_INCOMPLETE", "funding source completeness watermark is before interval_end")
    if calculated_at < interval_end:
        raise TradeResultBuildError("FUNDING_CALCULATED_PREMATURELY", "calculated_at must be at or after interval_end")

    if evidence.get("trade_plan_id") != trade_plan_id:
        raise TradeResultBuildError("FUNDING_TRADE_PLAN_MISMATCH", "funding evidence trade_plan_id mismatch")
    if evidence.get("position_id") != position_id:
        raise TradeResultBuildError("FUNDING_POSITION_MISMATCH", "funding evidence position_id mismatch")
    if evidence.get("symbol") != symbol:
        raise TradeResultBuildError("FUNDING_SYMBOL_MISMATCH", "funding evidence symbol mismatch")
    if interval_start != opened_at or interval_end != closed_at:
        raise TradeResultBuildError("FUNDING_INTERVAL_MISMATCH", "funding evidence must cover the exact position interval")
    if evidence.get("interval_semantics") != FUNDING_INTERVAL_SEMANTICS:
        raise TradeResultBuildError("FUNDING_INTERVAL_SEMANTICS_UNSUPPORTED", "funding interval semantics are unsupported")

    status = evidence.get("status")
    if status not in {ZERO_CONFIRMED, INCLUDED}:
        raise TradeResultBuildError("FUNDING_EVIDENCE_STATUS_INVALID", "funding status must be ZERO_CONFIRMED or INCLUDED")
    if evidence.get("cost_currency") != PNL_CURRENCY:
        raise TradeResultBuildError("FUNDING_CURRENCY_UNSUPPORTED", "funding cost_currency must be USDT")
    cost = _canonical_signed_decimal_string(evidence.get("funding_cost"), "funding_evidence.funding_cost")
    if status == ZERO_CONFIRMED:
        if source_record_count != 0 or evidence.get("funding_cost") != "0":
            raise TradeResultBuildError(
                "ZERO_FUNDING_CONTRADICTION",
                "ZERO_CONFIRMED requires source_record_count=0 and funding_cost='0'",
            )
    else:
        if source_record_count < 1:
            raise TradeResultBuildError("INCLUDED_FUNDING_RECORDS_REQUIRED", "INCLUDED requires at least one source record")

    expected_id = _stable_funding_evidence_id(evidence)
    if evidence_id != expected_id:
        raise TradeResultBuildError(
            "FUNDING_EVIDENCE_ID_MISMATCH",
            "funding_evidence_id does not match the canonical 17-field identity material",
        )
    return status, cost, evidence_id, _funding_identity_material(evidence)


def _authority_ref(authority: Mapping[str, Any], action_type: str, role: str) -> dict[str, str]:
    return {
        "position_action_id": _nonempty_text(authority.get("position_action_id"), "exit_authority.position_action_id"),
        "position_id": _nonempty_text(authority.get("position_id"), "exit_authority.position_id"),
        "action": action_type,
        "order_role": role,
    }


def _stable_trade_result_id(material: Mapping[str, Any]) -> str:
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return "traderes_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_trade_result(
    parent_plan: Mapping[str, Any],
    *,
    current_lifecycle_state: PositionLifecycleState | str,
    exit_authority: Mapping[str, Any],
    entry_order_requests: Sequence[Any],
    entry_fills: Sequence[Any],
    exit_order_request: Any,
    exit_fills: Sequence[Any],
    final_position: Mapping[str, Any],
    funding_evidence: Mapping[str, Any],
) -> TradeResultBuildOutcome:
    """Finalize one trade-result-v0.1 from exact E4/E5 + canonical funding evidence.

    The function aggregates and validates already-authoritative facts only. It
    never imports an E4 funding implementation, submits/queries broker orders,
    invents funding, persists state, or treats OrderStatus.FILLED as flat proof.
    Current Gate B finalization requires one canonical serialized
    funding-allocation-v0.1 FundingAllocationEvidence object.
    """

    plan_facts = _validate_parent_plan(parent_plan)
    try:
        lifecycle = PositionLifecycleState(current_lifecycle_state)
    except ValueError as exc:
        raise TradeResultBuildError("INVALID_LIFECYCLE_STATE", "current lifecycle state is unsupported") from exc

    authority_action = exit_authority.get("action") if isinstance(exit_authority, Mapping) else None
    if authority_action in {EXIT, EMERGENCY_EXIT}:
        action_type, exit_reasons, expected_role = _validate_explicit_authority(exit_authority, parent_plan)
        if lifecycle != PositionLifecycleState.EXIT_REQUESTED:
            raise TradeResultBuildError(
                "EXPLICIT_EXIT_LIFECYCLE_NOT_REQUESTED",
                "explicit EXIT/EMERGENCY_EXIT finalization requires current lifecycle EXIT_REQUESTED",
            )
    elif authority_action == PROTECT:
        action_type, exit_reasons, expected_role = _validate_protection_authority(exit_authority, parent_plan)
        if lifecycle not in {PositionLifecycleState.OPEN_PROTECTED, PositionLifecycleState.PROFIT_PROTECTED}:
            raise TradeResultBuildError(
                "PROTECTION_CLOSE_LIFECYCLE_INVALID",
                "PROTECTION_STOP finalization requires OPEN_PROTECTED or PROFIT_PROTECTED lifecycle",
            )
    else:
        raise TradeResultBuildError("UNSUPPORTED_EXIT_AUTHORITY", "closure authority is unsupported")

    entry_requests = _validate_entry_requests(entry_order_requests, parent_plan, plan_facts["entry_side"])
    ordered_entry = _ordered_fill_facts(entry_fills, "entry_fills")
    entry_order_request_ids = _validate_entry_fill_binding(
        ordered_entry,
        entry_requests,
        parent_plan,
        plan_facts["entry_side"],
    )

    ordered_exit = _ordered_fill_facts(exit_fills, "exit_fills")
    entry_ids = {item["fill_id"] for item in ordered_entry}
    exit_ids = {item["fill_id"] for item in ordered_exit}
    if entry_ids & exit_ids:
        raise TradeResultBuildError("CROSS_SET_DUPLICATE_FILL", "a Fill cannot appear in both entry and exit sets")

    exit_request = _validate_exit_request(
        exit_order_request,
        exit_authority,
        parent_plan,
        plan_facts["exit_side"],
        expected_role,
    )
    _validate_exit_fill_binding(
        ordered_exit,
        exit_request,
        exit_authority,
        parent_plan,
        plan_facts["exit_side"],
        expected_role,
    )

    entry_qty = sum((item["quantity"] for item in ordered_entry), Decimal("0"))
    exit_qty = sum((item["quantity"] for item in ordered_exit), Decimal("0"))
    if entry_qty <= 0:
        raise TradeResultBuildError("ENTRY_QUANTITY_INVALID", "entry quantity must be positive")
    if entry_qty > plan_facts["maximum_quantity"]:
        raise TradeResultBuildError("ENTRY_QUANTITY_EXCEEDS_APPROVED_MAXIMUM", "entry Fill quantity exceeds ApprovedTradePlan maximum")
    if entry_qty != exit_qty:
        raise TradeResultBuildError("QUANTITY_CONSERVATION_FAILED", "entry and exit Fill quantities must match exactly")
    if exit_qty != exit_request["quantity"] or exit_qty != _positive_decimal(
        exit_authority.get("quantity"), "exit_authority.quantity"
    ):
        raise TradeResultBuildError(
            "EXIT_AUTHORITY_QUANTITY_NOT_FULLY_FILLED",
            "finalization requires full Fill quantity for the exact exit authority/request",
        )

    earliest_entry_at = ordered_entry[0]["filled_at"]
    latest_entry_at = ordered_entry[-1]["filled_at"]
    earliest_exit_at = ordered_exit[0]["filled_at"]
    latest_exit_at = ordered_exit[-1]["filled_at"]
    if earliest_exit_at < latest_entry_at:
        raise TradeResultBuildError("FILL_TIME_ORDER_CONFLICT", "exit Fill cannot precede completion of the included entry Fill set")

    flat_observed_at = _validate_final_position(
        final_position,
        parent_plan,
        exit_authority,
        earliest_entry_at,
        latest_exit_at,
    )

    funding_status, funding_cost, funding_evidence_id, funding_identity_material = (
        _validate_canonical_funding_evidence(
            funding_evidence,
            trade_plan_id=parent_plan["trade_plan_id"],
            position_id=_nonempty_text(exit_authority.get("position_id"), "exit_authority.position_id"),
            symbol=parent_plan["symbol"],
            opened_at=earliest_entry_at,
            closed_at=flat_observed_at,
        )
    )

    entry_notional = sum((item["quantity"] * item["price"] for item in ordered_entry), Decimal("0"))
    exit_notional = sum((item["quantity"] * item["price"] for item in ordered_exit), Decimal("0"))
    average_entry_price = entry_notional / entry_qty
    average_exit_price = exit_notional / exit_qty
    gross_pnl = (
        exit_notional - entry_notional
        if parent_plan["direction"] == "LONG"
        else entry_notional - exit_notional
    )
    total_fees = sum((item["fee"] for item in ordered_entry + ordered_exit), Decimal("0"))
    net_pnl = gross_pnl - total_fees - funding_cost

    # Lifecycle closure is intentionally last. No invalid funding/financial or
    # broker evidence may reach POSITION_CLOSED.
    next_state = transition(lifecycle, PositionEvent.POSITION_CLOSED)
    if next_state != PositionLifecycleState.CLOSED:
        raise TradeResultBuildError("LIFECYCLE_CLOSURE_FAILED", "POSITION_CLOSED did not produce CLOSED")

    authority_ref = _authority_ref(exit_authority, action_type, expected_role)
    entry_fill_ids = [item["fill_id"] for item in ordered_entry]
    exit_fill_ids = [item["fill_id"] for item in ordered_exit]
    exit_order_request_ids = [exit_request["order_request_id"]]

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "trade_result_profile_version": TRADE_RESULT_PROFILE_VERSION,
        "pnl_profile_version": PNL_PROFILE_VERSION,
        "strategy_id": parent_plan["strategy_id"],
        "strategy_version": parent_plan["strategy_version"],
        "trade_plan_id": parent_plan["trade_plan_id"],
        "risk_decision_id": parent_plan["risk_decision_id"],
        "risk_policy_version": parent_plan["risk_policy_version"],
        "position_id": exit_authority["position_id"],
        "symbol": parent_plan["symbol"],
        "direction": parent_plan["direction"],
        "quantity_profile_version": QUANTITY_PROFILE_VERSION,
        "quantity_unit": QUANTITY_UNIT,
        "quantity_asset": QUANTITY_ASSET,
        "pnl_currency": PNL_CURRENCY,
        "opened_at": _fmt_utc(earliest_entry_at),
        "closed_at": _fmt_utc(flat_observed_at),
        "flat_position_observed_at": _fmt_utc(flat_observed_at),
        "entry_quantity": _fmt_decimal(entry_qty),
        "average_entry_price": _fmt_decimal(average_entry_price),
        "average_exit_price": _fmt_decimal(average_exit_price),
        "gross_pnl": _fmt_decimal(gross_pnl),
        "net_pnl": _fmt_decimal(net_pnl),
        "total_fees": _fmt_decimal(total_fees),
        "exit_reason_codes": list(exit_reasons),
        "entry_fill_ids": entry_fill_ids,
        "exit_fill_ids": exit_fill_ids,
        "entry_order_request_ids": entry_order_request_ids,
        "exit_order_request_ids": exit_order_request_ids,
        "exit_authority_refs": [authority_ref],
        "funding_evidence_profile_version": FUNDING_EVIDENCE_PROFILE_VERSION,
        "funding_evidence_id": funding_evidence_id,
        "funding_evidence_status": funding_status,
    }
    if funding_status == INCLUDED:
        result["funding_cost"] = _fmt_decimal(funding_cost)

    fill_material = {
        "entry": [
            {
                "fill_id": item["fill_id"],
                "client_order_id": item["client_order_id"],
                "quantity": _fmt_decimal(item["quantity"]),
                "price": _fmt_decimal(item["price"]),
                "fee": _fmt_decimal(item["fee"]),
                "fee_currency": item["fee_currency"],
                "filled_at": _fmt_utc(item["filled_at"]),
            }
            for item in ordered_entry
        ],
        "exit": [
            {
                "fill_id": item["fill_id"],
                "client_order_id": item["client_order_id"],
                "position_action_id": item["position_action_id"],
                "position_id": item["position_id"],
                "order_role": item["order_role"],
                "quantity": _fmt_decimal(item["quantity"]),
                "price": _fmt_decimal(item["price"]),
                "fee": _fmt_decimal(item["fee"]),
                "fee_currency": item["fee_currency"],
                "filled_at": _fmt_utc(item["filled_at"]),
            }
            for item in ordered_exit
        ],
    }
    identity_material = {
        **result,
        "fill_financial_material": fill_material,
        "funding_allocation_identity_material": funding_identity_material,
    }
    result["trade_result_id"] = _stable_trade_result_id(identity_material)

    return TradeResultBuildOutcome(
        trade_result=result,
        event=PositionEvent.POSITION_CLOSED,
        next_state=next_state,
    )
