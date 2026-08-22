from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Union

from .runtime import SUPPORTED_SHARED_SCHEMA_VERSION, StrategyError

ENTRY_PROFILE_VERSION = "entry-v0.1"
ENTRY_ORDER_TYPE_MARKET = "MARKET"

_REQUIRED_SIGNAL_FIELDS = {
    "schema_version",
    "signal_id",
    "strategy_id",
    "strategy_version",
    "symbol",
    "evaluated_at",
    "direction",
    "market_boundary_ref",
}

_PROVIDER_SPECIFIC_KEYS = {
    "provider",
    "provider_name",
    "exchange",
    "exchange_name",
    "instrument_id",
    "provider_instrument_id",
    "okx_instrument_id",
    "okx_order_type",
    "pionex_order_type",
    "ordtype",
    "sz",
    "tdmode",
    "posside",
}

_FORBIDDEN_AUTHORITY_KEYS = {
    "quantity",
    "approved_quantity",
    "leverage",
    "approved_leverage",
    "margin",
    "margin_mode",
    "risk_decision_id",
    "risk_policy_version",
    "risk_approved",
    "broker_credentials",
    "api_key",
    "api_secret",
    "order_request_id",
    "client_order_id",
}

_UNSUPPORTED_EXECUTION_KEYS = {
    "limit_price",
    "stop_price",
    "trigger_price",
    "time_in_force",
    "post_only",
    "ioc",
    "fok",
    "trailing_entry",
}


class TradeIntentError(StrategyError):
    """Structured E2 TradeIntent production/serialization error."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise TradeIntentError(
            "NON_SERIALIZABLE_TRADE_INTENT",
            "TradeIntent material must be deterministically JSON serializable",
        ) from exc


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeIntentError(
            "INVALID_TRADE_INTENT_INPUT",
            f"{field} must be a non-empty string",
            field=field,
        )
    return value


def _normalize_utc(value: Union[str, datetime], field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise TradeIntentError(
                "INVALID_UTC_TIMESTAMP",
                f"{field} must be timezone-aware UTC",
                field=field,
            )
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    if not isinstance(value, str) or not value.endswith("Z"):
        raise TradeIntentError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
            field=field,
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TradeIntentError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be valid RFC 3339 UTC",
            field=field,
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise TradeIntentError(
            "INVALID_UTC_TIMESTAMP",
            f"{field} must be UTC",
            field=field,
        )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive_decimal_string(value: Union[str, Decimal], field: str) -> str:
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise TradeIntentError(
                "INVALID_ADVISORY_PRICE",
                f"{field} must be a valid base-10 decimal string",
                field=field,
            ) from exc
    else:
        raise TradeIntentError(
            "INVALID_ADVISORY_PRICE",
            f"{field} must use Decimal internally or a decimal string at interchange",
            field=field,
        )

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise TradeIntentError(
            "INVALID_ADVISORY_PRICE",
            f"{field} must be a positive finite decimal",
            field=field,
        )
    return format(decimal_value, "f")


def _validate_signal(signal: Mapping[str, Any]) -> None:
    missing = sorted(field for field in _REQUIRED_SIGNAL_FIELDS if field not in signal)
    if missing:
        raise TradeIntentError(
            "INVALID_SIGNAL_INPUT",
            "Signal is missing fields required for TradeIntent production",
            fields=missing,
        )

    schema_version = _require_non_empty_string(signal["schema_version"], "Signal.schema_version")
    if schema_version != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise TradeIntentError(
            "UNSUPPORTED_SIGNAL_SCHEMA_VERSION",
            "Signal schema_version is not supported for TradeIntent production",
            supported=SUPPORTED_SHARED_SCHEMA_VERSION,
            actual=schema_version,
        )

    for field in ("signal_id", "strategy_id", "strategy_version", "symbol", "market_boundary_ref"):
        _require_non_empty_string(signal[field], f"Signal.{field}")

    _normalize_utc(signal["evaluated_at"], "Signal.evaluated_at")

    direction = signal["direction"]
    if direction not in {"LONG", "SHORT"}:
        raise TradeIntentError(
            "NON_ACTIONABLE_SIGNAL",
            "TradeIntent can be produced only from LONG or SHORT Signal",
            direction=direction,
        )


def _reject_extra_fields(extra_fields: Mapping[str, Any]) -> None:
    for key in sorted(extra_fields):
        normalized = key.lower()
        if (
            normalized in _PROVIDER_SPECIFIC_KEYS
            or "provider" in normalized
            or "exchange" in normalized
            or "okx" in normalized
            or "pionex" in normalized
            or "instrument_id" in normalized
        ):
            raise TradeIntentError(
                "PROVIDER_SPECIFIC_ENTRY_SEMANTICS",
                "Provider/exchange-specific entry semantics are forbidden in E2 TradeIntent",
                field=key,
            )
        if normalized in _FORBIDDEN_AUTHORITY_KEYS:
            raise TradeIntentError(
                "FORBIDDEN_TRADE_INTENT_AUTHORITY",
                "Risk, sizing, leverage, margin, broker, or order authority is forbidden in E2 TradeIntent",
                field=key,
            )
        if normalized in _UNSUPPORTED_EXECUTION_KEYS:
            raise TradeIntentError(
                "UNSUPPORTED_ENTRY_EXECUTION_FIELD",
                "entry-v0.1 does not support executable price/TIF/conditional entry fields",
                field=key,
            )
        raise TradeIntentError(
            "UNKNOWN_TRADE_INTENT_FIELD",
            "Unknown TradeIntent production field is rejected rather than inferred",
            field=key,
        )


def build_trade_intent(
    signal: Mapping[str, Any],
    *,
    entry_profile_version: Optional[str] = None,
    entry_order_type: Optional[str] = None,
    generated_at: Optional[Union[str, datetime]] = None,
    entry_style: Optional[str] = None,
    entry_reference_price: Optional[Union[str, Decimal]] = None,
    strategy_stop_level: Optional[Union[str, Decimal]] = None,
    strategy_target_level: Optional[Union[str, Decimal]] = None,
    max_hold_seconds: Optional[int] = None,
    **extra_fields: Any,
) -> Dict[str, Any]:
    """Build a deterministic provider-neutral TradeIntent from an E2 Signal.

    A TradeIntent becomes executable-profile eligible only when the caller
    explicitly supplies entry_profile_version="entry-v0.1" and
    entry_order_type="MARKET". Legacy entry_style and entry_reference_price
    remain advisory and are never promoted into executable order semantics.
    """
    if not isinstance(signal, Mapping):
        raise TradeIntentError(
            "INVALID_SIGNAL_INPUT",
            "signal must be a mapping produced by the E2 Strategy Runtime",
        )
    _validate_signal(signal)
    _reject_extra_fields(extra_fields)

    if entry_profile_version is None:
        if entry_order_type is not None:
            raise TradeIntentError(
                "MISSING_ENTRY_PROFILE_VERSION",
                "Executable entry_order_type requires an explicit supported entry profile",
                entry_order_type=entry_order_type,
            )
    else:
        if entry_profile_version != ENTRY_PROFILE_VERSION:
            raise TradeIntentError(
                "UNSUPPORTED_ENTRY_PROFILE_VERSION",
                "TradeIntent entry profile is not supported by this E2 producer",
                supported=ENTRY_PROFILE_VERSION,
                actual=entry_profile_version,
            )
        if entry_order_type is None:
            raise TradeIntentError(
                "MISSING_ENTRY_ORDER_TYPE",
                "entry-v0.1 requires explicit entry_order_type",
                profile_version=ENTRY_PROFILE_VERSION,
            )
        if entry_order_type != ENTRY_ORDER_TYPE_MARKET:
            raise TradeIntentError(
                "UNSUPPORTED_ENTRY_ORDER_TYPE",
                "entry-v0.1 supports MARKET only",
                supported=ENTRY_ORDER_TYPE_MARKET,
                actual=entry_order_type,
            )

    if entry_style is not None:
        entry_style = _require_non_empty_string(entry_style, "entry_style")

    if max_hold_seconds is not None and (type(max_hold_seconds) is not int or max_hold_seconds <= 0):
        raise TradeIntentError(
            "INVALID_MAX_HOLD_SECONDS",
            "max_hold_seconds must be a positive integer when present",
            actual=max_hold_seconds,
        )

    evaluated_at = _normalize_utc(signal["evaluated_at"], "Signal.evaluated_at")
    normalized_generated_at = _normalize_utc(
        generated_at if generated_at is not None else evaluated_at,
        "generated_at",
    )

    material: Dict[str, Any] = {
        "schema_version": SUPPORTED_SHARED_SCHEMA_VERSION,
        "signal_id": signal["signal_id"],
        "strategy_id": signal["strategy_id"],
        "strategy_version": signal["strategy_version"],
        "symbol": signal["symbol"],
        "direction": signal["direction"],
        "generated_at": normalized_generated_at,
        "market_boundary_ref": signal["market_boundary_ref"],
    }

    if entry_profile_version is not None:
        material["entry_profile_version"] = ENTRY_PROFILE_VERSION
        material["entry_order_type"] = ENTRY_ORDER_TYPE_MARKET

    if entry_style is not None:
        material["entry_style"] = entry_style
    if entry_reference_price is not None:
        material["entry_reference_price"] = _positive_decimal_string(
            entry_reference_price, "entry_reference_price"
        )
    if strategy_stop_level is not None:
        material["strategy_stop_level"] = _positive_decimal_string(
            strategy_stop_level, "strategy_stop_level"
        )
    if strategy_target_level is not None:
        material["strategy_target_level"] = _positive_decimal_string(
            strategy_target_level, "strategy_target_level"
        )
    if max_hold_seconds is not None:
        material["max_hold_seconds"] = max_hold_seconds

    intent_id = "intent_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return {
        "schema_version": material["schema_version"],
        "intent_id": intent_id,
        **{key: value for key, value in material.items() if key != "schema_version"},
    }
