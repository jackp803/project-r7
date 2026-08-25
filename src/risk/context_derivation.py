from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .engine import RiskContext, SUPPORTED_SHARED_SCHEMA_VERSION

GATE_C_SYMBOL = "BTC_USDT_PERP"
GATE_C_MARKET_SOURCE = "OKX_PUBLIC_TICKER"
GATE_C_MARKET_MAX_AGE_MS = 5_000
GATE_C_CLOCK_TOLERANCE_MS = 5_000
GATE_C_PROVIDER = "OKX"
GATE_C_API_VERSION = "V5"
GATE_C_ENVIRONMENT = "production_read_only_shadow"
GATE_C_PROVIDER_INSTRUMENT = "BTC-USDT-SWAP"
GATE_C_PERMISSION = "read_only"
GATE_C_ACCOUNT_LEVEL = "2"
GATE_C_SUBACCOUNT_STATUS = "SUBACCOUNT"
GATE_C_POSITION_MODES = frozenset({"net_mode", "long_short_mode"})
GATE_C_EXPECTED_PRIVATE_GET_COUNT = 6


class RiskContextDerivationError(ValueError):
    """Invalid E5-owned risk-runtime input that cannot safely form a RiskContext."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, repr=False)
class GateCRiskContextDerivation:
    """Runtime-only derivation result; repr deliberately never renders balance/context."""

    _context: RiskContext
    reason_codes: tuple[str, ...]

    @property
    def context(self) -> RiskContext:
        return self._context

    @property
    def safe_for_new_exposure(self) -> bool:
        return not self.reason_codes and self._context.new_exposure_allowed is True

    def __repr__(self) -> str:
        return (
            "GateCRiskContextDerivation(safe_for_new_exposure={!r}, reason_codes={!r}, "
            "context=<runtime-sensitive>)"
        ).format(self.safe_for_new_exposure, self.reason_codes)


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    if value.utcoffset() != timezone.utc.utcoffset(value):
        return None
    return value.astimezone(timezone.utc)


def _safe_attr(value: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(value, name)
    except (AttributeError, RuntimeError, ValueError):
        return default


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _validate_e5_state(
    *,
    kill_switch_active: Any,
    trades_today: Any,
    consecutive_losses: Any,
    drawdown: Any,
) -> tuple[bool, int, int, Decimal]:
    if type(kill_switch_active) is not bool:
        raise RiskContextDerivationError(
            "INVALID_KILL_SWITCH_STATE",
            "kill_switch_active must be bool",
        )
    if not _nonnegative_int(trades_today):
        raise RiskContextDerivationError(
            "INVALID_RISK_COUNTER_STATE",
            "trades_today must be a non-negative integer",
        )
    if not _nonnegative_int(consecutive_losses):
        raise RiskContextDerivationError(
            "INVALID_RISK_COUNTER_STATE",
            "consecutive_losses must be a non-negative integer",
        )
    if not isinstance(drawdown, Decimal) or not drawdown.is_finite() or drawdown < 0:
        raise RiskContextDerivationError(
            "INVALID_DRAWDOWN_STATE",
            "drawdown must be a finite non-negative Decimal",
        )
    return kill_switch_active, trades_today, consecutive_losses, drawdown


def _market_safety(market_snapshot: Any, risk_evaluation_time: datetime) -> tuple[bool, bool, tuple[str, ...]]:
    reasons: list[str] = []
    stale = False

    schema_version = _safe_attr(market_snapshot, "schema_version")
    symbol = _safe_attr(market_snapshot, "symbol")
    health_status = _safe_attr(market_snapshot, "health_status")
    source = _safe_attr(market_snapshot, "source")
    observed_at = _utc(_safe_attr(market_snapshot, "observed_at"))
    received_at = _utc(_safe_attr(market_snapshot, "received_at"))
    freshness_ms = _safe_attr(market_snapshot, "freshness_ms")

    if schema_version != SUPPORTED_SHARED_SCHEMA_VERSION:
        reasons.append("GATE_C_MARKET_SCHEMA_UNSUPPORTED")
    if symbol != GATE_C_SYMBOL:
        reasons.append("GATE_C_MARKET_SYMBOL_MISMATCH")
    if source != GATE_C_MARKET_SOURCE:
        reasons.append("GATE_C_MARKET_SOURCE_MISMATCH")
    if health_status != "HEALTHY":
        reasons.append("GATE_C_MARKET_NOT_HEALTHY")
    if observed_at is None or received_at is None:
        reasons.append("GATE_C_MARKET_TIME_INVALID")
        return False, stale, tuple(sorted(set(reasons)))
    if type(freshness_ms) is not int or freshness_ms < 0:
        reasons.append("GATE_C_MARKET_FRESHNESS_INVALID")
        return False, stale, tuple(sorted(set(reasons)))

    receipt_age_ms = int((received_at - observed_at).total_seconds() * 1000)
    expected_receipt_freshness_ms = max(0, receipt_age_ms)
    if receipt_age_ms < -GATE_C_CLOCK_TOLERANCE_MS:
        reasons.append("GATE_C_MARKET_FUTURE_AT_RECEIPT")
    if freshness_ms != expected_receipt_freshness_ms:
        reasons.append("GATE_C_MARKET_FRESHNESS_CONTRADICTION")
    if freshness_ms > GATE_C_MARKET_MAX_AGE_MS:
        reasons.append("GATE_C_MARKET_RECEIPT_STALE")
        stale = True
    if received_at > risk_evaluation_time:
        reasons.append("GATE_C_MARKET_RECEIVED_AFTER_DECISION")

    decision_age_ms = int((risk_evaluation_time - observed_at).total_seconds() * 1000)
    if decision_age_ms < -GATE_C_CLOCK_TOLERANCE_MS:
        reasons.append("GATE_C_MARKET_FUTURE_AT_DECISION")
    elif decision_age_ms > GATE_C_MARKET_MAX_AGE_MS:
        reasons.append("GATE_C_MARKET_STALE_AT_DECISION")
        stale = True

    safe = not reasons
    return safe, stale, tuple(sorted(set(reasons)))


def _okx_hostname(value: Any) -> bool:
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    hostname = value.lower()
    return hostname == "okx.com" or hostname.endswith(".okx.com")


def _checkpoint_known(value: Any) -> bool:
    if value is None:
        return False
    latest = _safe_attr(value, "latest_fill_timestamp_ms")
    records = _safe_attr(value, "records_at_latest_timestamp")
    if latest is None:
        return records == 0
    return _nonnegative_int(latest) and type(records) is int and records > 0


def _shadow_safety(shadow_read_result: Any, risk_evaluation_time: datetime) -> tuple[bool, bool, bool, Decimal | None, tuple[str, ...]]:
    """Return account_safe, position_safe, order_safe, runtime_balance, reasons."""

    reasons: list[str] = []
    observation = _safe_attr(shadow_read_result, "sanitized_observation")
    runtime_balance = _safe_attr(shadow_read_result, "runtime_available_balance")
    if observation is None:
        return False, False, False, None, ("GATE_C_SHADOW_OBSERVATION_MISSING",)

    identity_safe = True
    identity_checks = (
        (_safe_attr(observation, "provider") == GATE_C_PROVIDER, "GATE_C_SHADOW_PROVIDER_MISMATCH"),
        (_safe_attr(observation, "api_version") == GATE_C_API_VERSION, "GATE_C_SHADOW_API_VERSION_MISMATCH"),
        (_safe_attr(observation, "environment") == GATE_C_ENVIRONMENT, "GATE_C_SHADOW_ENVIRONMENT_MISMATCH"),
        (_safe_attr(observation, "canonical_symbol") == GATE_C_SYMBOL, "GATE_C_SHADOW_SYMBOL_MISMATCH"),
        (_safe_attr(observation, "provider_instrument_id") == GATE_C_PROVIDER_INSTRUMENT, "GATE_C_SHADOW_INSTRUMENT_MISMATCH"),
        (_okx_hostname(_safe_attr(observation, "rest_hostname")), "GATE_C_SHADOW_REST_HOST_INVALID"),
    )
    for valid, code in identity_checks:
        if not valid:
            identity_safe = False
            reasons.append(code)

    observed_at = _utc(_safe_attr(observation, "observed_at"))
    provider_time = _utc(_safe_attr(observation, "provider_time"))
    if observed_at is None or observed_at > risk_evaluation_time:
        reasons.append("GATE_C_SHADOW_OBSERVATION_TIME_INVALID")
        identity_safe = False
    if provider_time is None:
        reasons.append("GATE_C_SHADOW_PROVIDER_TIME_UNKNOWN")
        identity_safe = False

    reason_codes = _safe_attr(observation, "reason_codes")
    if not isinstance(reason_codes, tuple):
        reasons.append("GATE_C_SHADOW_REASON_CODES_INVALID")
        batch_healthy = False
    else:
        batch_healthy = _safe_attr(observation, "health_status") == "HEALTHY" and not reason_codes
        if _safe_attr(observation, "health_status") != "HEALTHY":
            reasons.append("GATE_C_SHADOW_NOT_HEALTHY")
        if reason_codes:
            reasons.append("GATE_C_SHADOW_BLOCKING_REASON_PRESENT")

    clock_skew_ms = _safe_attr(observation, "clock_skew_ms")
    clock_safe = (
        _safe_attr(observation, "clock_status") == "HEALTHY"
        and _nonnegative_int(clock_skew_ms)
        and clock_skew_ms <= GATE_C_CLOCK_TOLERANCE_MS
    )
    if not clock_safe:
        reasons.append("GATE_C_SHADOW_CLOCK_UNSAFE")

    permission_safe = _safe_attr(observation, "permission_category") == GATE_C_PERMISSION
    if not permission_safe:
        reasons.append("GATE_C_SHADOW_PERMISSION_NOT_READ_ONLY")

    account_config_safe = (
        _safe_attr(observation, "account_config_known") is True
        and _safe_attr(observation, "account_level") == GATE_C_ACCOUNT_LEVEL
        and _safe_attr(observation, "position_mode") in GATE_C_POSITION_MODES
        and _safe_attr(observation, "subaccount_status") == GATE_C_SUBACCOUNT_STATUS
        and _safe_attr(observation, "isolated_leverage_known") is True
        and _safe_attr(observation, "isolated_leverage_ok") is True
        and _safe_attr(observation, "private_get_count") == GATE_C_EXPECTED_PRIVATE_GET_COUNT
    )
    if not account_config_safe:
        reasons.append("GATE_C_SHADOW_ACCOUNT_CONFIG_UNSAFE")

    balance_safe = (
        _safe_attr(observation, "usdt_balance_known") is True
        and isinstance(runtime_balance, Decimal)
        and runtime_balance.is_finite()
        and runtime_balance >= 0
    )
    if not balance_safe:
        reasons.append("GATE_C_SHADOW_BALANCE_UNSAFE")
        runtime_balance = None

    position_safe = (
        batch_healthy
        and identity_safe
        and clock_safe
        and _safe_attr(observation, "position_known") is True
        and _safe_attr(observation, "unexpected_exposure") is False
    )
    if not position_safe:
        reasons.append("GATE_C_SHADOW_POSITION_UNSAFE")

    pending_orders = _safe_attr(observation, "pending_order_count")
    recent_fill_count = _safe_attr(observation, "recent_fill_window_count")
    unreconciled_fill_count = _safe_attr(observation, "new_unreconciled_fill_count")
    order_facts_safe = (
        type(pending_orders) is int
        and pending_orders == 0
        and _nonnegative_int(recent_fill_count)
        and type(unreconciled_fill_count) is int
        and unreconciled_fill_count == 0
        and _checkpoint_known(_safe_attr(observation, "fill_checkpoint"))
    )
    order_safe = batch_healthy and identity_safe and clock_safe and order_facts_safe
    if not order_safe:
        reasons.append("GATE_C_SHADOW_ORDER_UNSAFE")

    account_safe = (
        batch_healthy
        and identity_safe
        and clock_safe
        and permission_safe
        and account_config_safe
        and balance_safe
    )
    if not account_safe:
        reasons.append("GATE_C_SHADOW_ACCOUNT_UNSAFE")

    return account_safe, position_safe, order_safe, runtime_balance, tuple(sorted(set(reasons)))


def derive_gate_c_risk_context(
    market_snapshot: Any,
    shadow_read_result: Any,
    *,
    risk_evaluation_time: datetime,
    kill_switch_active: bool,
    trades_today: int,
    consecutive_losses: int,
    drawdown: Decimal,
) -> GateCRiskContextDerivation:
    """Derive the existing RiskContext from accepted normalized Gate C facts.

    No caller-provided market/account/position/order safe flags are accepted.
    Provider reads, credentials, persistence and risk-policy thresholds remain
    outside this pure derivation boundary.
    """

    evaluation_time = _utc(risk_evaluation_time)
    if evaluation_time is None:
        raise RiskContextDerivationError(
            "INVALID_RISK_EVALUATION_TIME",
            "risk_evaluation_time must be timezone-aware UTC",
        )
    kill_switch_active, trades_today, consecutive_losses, drawdown = _validate_e5_state(
        kill_switch_active=kill_switch_active,
        trades_today=trades_today,
        consecutive_losses=consecutive_losses,
        drawdown=drawdown,
    )

    market_safe, market_stale, market_reasons = _market_safety(
        market_snapshot,
        evaluation_time,
    )
    account_safe, position_safe, order_safe, runtime_balance, shadow_reasons = _shadow_safety(
        shadow_read_result,
        evaluation_time,
    )

    reasons = set(market_reasons) | set(shadow_reasons)
    if kill_switch_active:
        reasons.add("GATE_C_KILL_SWITCH_ACTIVE")

    all_observation_axes_safe = market_safe and account_safe and position_safe and order_safe
    new_exposure_allowed = all_observation_axes_safe and not kill_switch_active

    context = RiskContext(
        market_health_status="HEALTHY" if market_safe else ("STALE" if market_stale else "UNKNOWN"),
        market_data_fresh=market_safe,
        account_state_status="KNOWN" if account_safe else "UNKNOWN",
        account_state_known=account_safe,
        position_state_status="FLAT" if position_safe else "UNKNOWN",
        position_state_known=position_safe,
        order_state_status="KNOWN" if order_safe else "UNKNOWN",
        order_state_known=order_safe,
        kill_switch_active=kill_switch_active,
        new_exposure_allowed=new_exposure_allowed,
        trades_today=trades_today,
        open_position_count=0 if position_safe else 1,
        same_symbol_position_open=False if position_safe else True,
        consecutive_losses=consecutive_losses,
        drawdown=drawdown,
        available_balance=runtime_balance if account_safe else None,
    )
    return GateCRiskContextDerivation(
        _context=context,
        reason_codes=tuple(sorted(reasons)),
    )
