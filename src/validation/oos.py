"""Deterministic E3 OOS validation policy and ValidationDecision producer.

This module is research-only. It consumes a canonical BacktestResult contract,
requires explicit OOS bindings and caller-supplied policy thresholds, and emits
a canonical contracts-v0.1 ValidationDecision. It has no Registry, lifecycle,
risk-sizing, broker, PAPER, SHADOW, or LIVE authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = "contracts-v0.1"
EXECUTION_EXECUTED = "EXECUTED"
EXECUTION_NOT_RUN = "NOT_RUN"
_ALLOWED_EXECUTION_STATES = {EXECUTION_EXECUTED, EXECUTION_NOT_RUN}
_ALLOWED_DECISIONS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}

_REQUIRED_BACKTEST_FIELDS = (
    "schema_version",
    "backtest_result_id",
    "strategy_id",
    "strategy_version",
    "strategy_content_hash",
    "runtime_version",
    "dataset_id",
    "dataset_hash",
    "dataset_start",
    "dataset_end",
    "cost_model_version",
    "created_at",
    "total_trades",
    "wins",
    "losses",
    "breakeven",
    "gross_pnl",
    "net_pnl",
    "total_fees",
    "profit_factor",
    "expectancy",
    "max_drawdown",
    "max_consecutive_losses",
)

BLOCK_REASON_ORDER = (
    "BACKTEST_RESULT_TYPE_INVALID",
    "BACKTEST_RESULT_SERIALIZATION_FAILED",
    "BACKTEST_REQUIRED_FIELD_MISSING",
    "BACKTEST_SCHEMA_UNSUPPORTED",
    "BACKTEST_IDENTITY_INVALID",
    "BACKTEST_TIMESTAMP_INVALID",
    "BACKTEST_TIME_RANGE_INVALID",
    "BACKTEST_COUNT_INVALID",
    "BACKTEST_TRADE_COUNTS_INCONSISTENT",
    "BACKTEST_DECIMAL_INVALID",
    "BACKTEST_STRATEGY_ID_MISMATCH",
    "BACKTEST_STRATEGY_VERSION_MISMATCH",
    "BACKTEST_RESULT_ID_MISMATCH",
    "OOS_CONTEXT_MISSING",
    "OOS_CONTEXT_INVALID",
    "OOS_TIME_RANGE_INVALID",
    "TRAIN_OOS_DATASET_ID_COLLISION",
    "TRAIN_OOS_DATASET_HASH_COLLISION",
    "OOS_POLICY_VERSION_MISMATCH",
    "OOS_BACKTEST_DATASET_ID_MISMATCH",
    "OOS_BACKTEST_DATASET_HASH_MISMATCH",
    "OOS_BACKTEST_DATASET_START_MISMATCH",
    "OOS_BACKTEST_DATASET_END_MISMATCH",
    "EXECUTION_STATE_INVALID",
)

FAIL_REASON_ORDER = (
    "MIN_TOTAL_TRADES_NOT_MET",
    "MIN_NET_PNL_NOT_MET",
    "MAX_DRAWDOWN_EXCEEDED",
    "MAX_CONSECUTIVE_LOSSES_EXCEEDED",
    "PROFIT_FACTOR_REQUIRED_BUT_NULL",
    "MIN_PROFIT_FACTOR_NOT_MET",
)

PASS_REASON_CODE = "OOS_POLICY_CRITERIA_PASSED"
NOT_RUN_REASON_CODE = "EXECUTION_NOT_RUN"


class ValidationConfigurationError(ValueError):
    """Raised when decision-authority configuration cannot form a canonical decision."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_id(prefix: str, material: Any) -> str:
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return f"{prefix}{digest}"


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationConfigurationError(f"{field} must be a non-empty string")
    return value


def _normalize_utc(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationConfigurationError(f"{field} must be timezone-aware UTC")
        normalized = value.astimezone(timezone.utc)
        if value.utcoffset() != timezone.utc.utcoffset(normalized):
            raise ValidationConfigurationError(f"{field} must be UTC")
        return normalized
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValidationConfigurationError(f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValidationConfigurationError(f"{field} must be a valid RFC 3339 UTC timestamp") from exc
    return parsed.astimezone(timezone.utc)


def _z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float) or isinstance(value, int):
        raise ValidationConfigurationError(
            f"{field} must use Decimal or a base-10 decimal string, not binary float/integer coercion"
        )
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValidationConfigurationError(f"{field} must be a valid base-10 decimal") from exc
    else:
        raise ValidationConfigurationError(f"{field} must be Decimal or a base-10 decimal string")
    if not parsed.is_finite():
        raise ValidationConfigurationError(f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    return format(normalized, "f")


def _ordered_reasons(reasons: list[str], vocabulary: tuple[str, ...]) -> tuple[str, ...]:
    present = set(reasons)
    ordered = [reason for reason in vocabulary if reason in present]
    ordered.extend(sorted(present.difference(vocabulary)))
    return tuple(ordered)


@dataclass(frozen=True)
class ValidationSubject:
    strategy_id: str
    strategy_version: str
    backtest_result_id: str

    def __post_init__(self) -> None:
        _nonempty(self.strategy_id, "subject.strategy_id")
        _nonempty(self.strategy_version, "subject.strategy_version")
        _nonempty(self.backtest_result_id, "subject.backtest_result_id")


@dataclass(frozen=True)
class ValidationPolicy:
    version: str
    min_total_trades: int
    min_net_pnl: Decimal | str
    max_drawdown: Decimal | str
    max_consecutive_losses: int
    min_profit_factor: Decimal | str | None

    def __post_init__(self) -> None:
        _nonempty(self.version, "policy.version")
        if type(self.min_total_trades) is not int or self.min_total_trades < 0:
            raise ValidationConfigurationError("policy.min_total_trades must be a non-negative integer")
        if type(self.max_consecutive_losses) is not int or self.max_consecutive_losses < 0:
            raise ValidationConfigurationError(
                "policy.max_consecutive_losses must be a non-negative integer"
            )
        min_net_pnl = _decimal(self.min_net_pnl, "policy.min_net_pnl")
        max_drawdown = _decimal(self.max_drawdown, "policy.max_drawdown")
        if max_drawdown < 0:
            raise ValidationConfigurationError("policy.max_drawdown must be non-negative")
        if self.min_profit_factor is None:
            min_profit_factor = None
        else:
            min_profit_factor = _decimal(self.min_profit_factor, "policy.min_profit_factor")
            if min_profit_factor < 0:
                raise ValidationConfigurationError("policy.min_profit_factor must be non-negative")
        object.__setattr__(self, "min_net_pnl", min_net_pnl)
        object.__setattr__(self, "max_drawdown", max_drawdown)
        object.__setattr__(self, "min_profit_factor", min_profit_factor)

    def material(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "min_total_trades": self.min_total_trades,
            "min_net_pnl": _decimal_text(self.min_net_pnl),
            "max_drawdown": _decimal_text(self.max_drawdown),
            "max_consecutive_losses": self.max_consecutive_losses,
            "min_profit_factor": (
                None if self.min_profit_factor is None else _decimal_text(self.min_profit_factor)
            ),
        }

    @property
    def identity(self) -> str:
        return _hash_id("validation_policy_", self.material())


@dataclass(frozen=True)
class OOSValidationContext:
    split_id: str
    oos_dataset_id: str
    oos_dataset_hash: str
    oos_dataset_start: datetime | str
    oos_dataset_end: datetime | str
    training_dataset_id: str
    training_dataset_hash: str
    validation_policy_version: str


@dataclass(frozen=True)
class _BacktestView:
    backtest_result_id: str
    strategy_id: str
    strategy_version: str
    dataset_id: str
    dataset_hash: str
    dataset_start: datetime
    dataset_end: datetime
    total_trades: int
    net_pnl: Decimal
    max_drawdown: Decimal
    max_consecutive_losses: int
    profit_factor: Decimal | None


@dataclass(frozen=True)
class ValidationDecision:
    validation_decision_id: str
    strategy_id: str
    strategy_version: str
    backtest_result_id: str
    validation_policy_version: str
    validation_policy_id: str
    oos_context_id: str
    decision: str
    reason_codes: tuple[str, ...]
    decided_at: datetime
    execution_state: str
    policy_material: dict[str, Any]
    oos_binding: dict[str, Any] | None

    def __post_init__(self) -> None:
        if self.decision not in _ALLOWED_DECISIONS:
            raise ValidationConfigurationError(f"unsupported validation decision: {self.decision}")

    def to_contract(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "validation_decision_id": self.validation_decision_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "backtest_result_id": self.backtest_result_id,
            "validation_policy_version": self.validation_policy_version,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "decided_at": _z(self.decided_at),
            "validation_policy_id": self.validation_policy_id,
            "oos_context_id": self.oos_context_id,
            "execution_state": self.execution_state,
            "policy_thresholds": dict(self.policy_material),
            "oos_binding": None if self.oos_binding is None else dict(self.oos_binding),
        }


def _coerce_backtest_payload(backtest_result: Any) -> tuple[Mapping[str, Any] | None, list[str]]:
    if isinstance(backtest_result, Mapping):
        return backtest_result, []
    serializer = getattr(backtest_result, "to_contract", None)
    if callable(serializer):
        try:
            payload = serializer()
        except Exception:
            return None, ["BACKTEST_RESULT_SERIALIZATION_FAILED"]
        if isinstance(payload, Mapping):
            return payload, []
        return None, ["BACKTEST_RESULT_TYPE_INVALID"]
    return None, ["BACKTEST_RESULT_TYPE_INVALID"]


def _parse_backtest_result(backtest_result: Any) -> tuple[_BacktestView | None, list[str]]:
    raw, reasons = _coerce_backtest_payload(backtest_result)
    if raw is None:
        return None, reasons

    missing = [field for field in _REQUIRED_BACKTEST_FIELDS if field not in raw]
    if missing:
        return None, ["BACKTEST_REQUIRED_FIELD_MISSING"]

    if raw["schema_version"] != SCHEMA_VERSION:
        reasons.append("BACKTEST_SCHEMA_UNSUPPORTED")

    identity_fields = (
        "backtest_result_id",
        "strategy_id",
        "strategy_version",
        "strategy_content_hash",
        "runtime_version",
        "dataset_id",
        "dataset_hash",
        "cost_model_version",
    )
    for field in identity_fields:
        if not isinstance(raw[field], str) or not raw[field].strip():
            reasons.append("BACKTEST_IDENTITY_INVALID")
            break

    timestamps: dict[str, datetime] = {}
    for field in ("dataset_start", "dataset_end", "created_at"):
        try:
            timestamps[field] = _normalize_utc(raw[field], f"BacktestResult.{field}")
        except ValidationConfigurationError:
            reasons.append("BACKTEST_TIMESTAMP_INVALID")
            break
    if len(timestamps) == 3 and timestamps["dataset_start"] > timestamps["dataset_end"]:
        reasons.append("BACKTEST_TIME_RANGE_INVALID")

    counts: dict[str, int] = {}
    for field in ("total_trades", "wins", "losses", "breakeven", "max_consecutive_losses"):
        value = raw[field]
        if type(value) is not int or value < 0:
            reasons.append("BACKTEST_COUNT_INVALID")
            break
        counts[field] = value
    if len(counts) == 5:
        if counts["wins"] + counts["losses"] + counts["breakeven"] != counts["total_trades"]:
            reasons.append("BACKTEST_TRADE_COUNTS_INCONSISTENT")

    decimal_values: dict[str, Decimal | None] = {}
    for field in ("gross_pnl", "net_pnl", "total_fees", "expectancy", "max_drawdown"):
        try:
            decimal_values[field] = _decimal(raw[field], f"BacktestResult.{field}")
        except ValidationConfigurationError:
            reasons.append("BACKTEST_DECIMAL_INVALID")
            break
    if "BACKTEST_DECIMAL_INVALID" not in reasons:
        if raw["profit_factor"] is None:
            decimal_values["profit_factor"] = None
        else:
            try:
                decimal_values["profit_factor"] = _decimal(
                    raw["profit_factor"], "BacktestResult.profit_factor"
                )
            except ValidationConfigurationError:
                reasons.append("BACKTEST_DECIMAL_INVALID")

    if reasons:
        return None, reasons

    return (
        _BacktestView(
            backtest_result_id=raw["backtest_result_id"],
            strategy_id=raw["strategy_id"],
            strategy_version=raw["strategy_version"],
            dataset_id=raw["dataset_id"],
            dataset_hash=raw["dataset_hash"],
            dataset_start=timestamps["dataset_start"],
            dataset_end=timestamps["dataset_end"],
            total_trades=counts["total_trades"],
            net_pnl=decimal_values["net_pnl"],
            max_drawdown=decimal_values["max_drawdown"],
            max_consecutive_losses=counts["max_consecutive_losses"],
            profit_factor=decimal_values["profit_factor"],
        ),
        [],
    )


def _safe_context_value(value: Any) -> Any:
    if isinstance(value, datetime):
        try:
            return _z(_normalize_utc(value, "context timestamp"))
        except ValidationConfigurationError:
            return {"invalid_type": "datetime"}
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return {"invalid_type": type(value).__name__}


def _context_material(context: OOSValidationContext | None) -> dict[str, Any] | None:
    if context is None:
        return None
    return {
        "split_id": _safe_context_value(context.split_id),
        "oos_dataset_id": _safe_context_value(context.oos_dataset_id),
        "oos_dataset_hash": _safe_context_value(context.oos_dataset_hash),
        "oos_dataset_start": _safe_context_value(context.oos_dataset_start),
        "oos_dataset_end": _safe_context_value(context.oos_dataset_end),
        "training_dataset_id": _safe_context_value(context.training_dataset_id),
        "training_dataset_hash": _safe_context_value(context.training_dataset_hash),
        "validation_policy_version": _safe_context_value(context.validation_policy_version),
    }


def _validate_context(
    context: OOSValidationContext | None,
    policy: ValidationPolicy,
    backtest: _BacktestView | None,
) -> tuple[list[str], dict[str, Any] | None, str]:
    material = _context_material(context)
    context_id = _hash_id("oos_context_", material)
    if context is None:
        return ["OOS_CONTEXT_MISSING"], None, context_id
    if not isinstance(context, OOSValidationContext):
        return ["OOS_CONTEXT_INVALID"], material, context_id

    reasons: list[str] = []
    for value in (
        context.split_id,
        context.oos_dataset_id,
        context.oos_dataset_hash,
        context.training_dataset_id,
        context.training_dataset_hash,
        context.validation_policy_version,
    ):
        if not isinstance(value, str) or not value.strip():
            reasons.append("OOS_CONTEXT_INVALID")
            break

    start: datetime | None = None
    end: datetime | None = None
    try:
        start = _normalize_utc(context.oos_dataset_start, "context.oos_dataset_start")
        end = _normalize_utc(context.oos_dataset_end, "context.oos_dataset_end")
    except ValidationConfigurationError:
        reasons.append("OOS_CONTEXT_INVALID")
    if start is not None and end is not None and start > end:
        reasons.append("OOS_TIME_RANGE_INVALID")

    if context.training_dataset_id == context.oos_dataset_id:
        reasons.append("TRAIN_OOS_DATASET_ID_COLLISION")
    if context.training_dataset_hash == context.oos_dataset_hash:
        reasons.append("TRAIN_OOS_DATASET_HASH_COLLISION")
    if context.validation_policy_version != policy.version:
        reasons.append("OOS_POLICY_VERSION_MISMATCH")

    if backtest is not None and start is not None and end is not None:
        if backtest.dataset_id != context.oos_dataset_id:
            reasons.append("OOS_BACKTEST_DATASET_ID_MISMATCH")
        if backtest.dataset_hash != context.oos_dataset_hash:
            reasons.append("OOS_BACKTEST_DATASET_HASH_MISMATCH")
        if backtest.dataset_start != start:
            reasons.append("OOS_BACKTEST_DATASET_START_MISMATCH")
        if backtest.dataset_end != end:
            reasons.append("OOS_BACKTEST_DATASET_END_MISMATCH")

    normalized_material = None
    if not reasons and start is not None and end is not None:
        normalized_material = {
            "split_id": context.split_id,
            "oos_dataset_id": context.oos_dataset_id,
            "oos_dataset_hash": context.oos_dataset_hash,
            "oos_dataset_start": _z(start),
            "oos_dataset_end": _z(end),
            "training_dataset_id": context.training_dataset_id,
            "training_dataset_hash": context.training_dataset_hash,
            "validation_policy_version": context.validation_policy_version,
        }
        context_id = _hash_id("oos_context_", normalized_material)
    return reasons, normalized_material if normalized_material is not None else material, context_id


def evaluate_oos_validation(
    *,
    subject: ValidationSubject,
    backtest_result: Any,
    context: OOSValidationContext | None,
    policy: ValidationPolicy,
    execution_state: str,
    decided_at: datetime | str,
) -> ValidationDecision:
    """Evaluate one explicit OOS BacktestResult against one explicit policy.

    Structural contract/OOS failures always resolve to BLOCKED. Quantitative
    criteria are evaluated only after all structural bindings are valid. An
    explicit execution_state=NOT_RUN then resolves to NOT_RUN without applying
    quantitative criteria. This function performs no persistence or lifecycle
    transition.
    """

    if not isinstance(subject, ValidationSubject):
        raise ValidationConfigurationError("subject must be ValidationSubject")
    if not isinstance(policy, ValidationPolicy):
        raise ValidationConfigurationError("policy must be ValidationPolicy")
    observed_at = _normalize_utc(decided_at, "decided_at")

    backtest, blocked_reasons = _parse_backtest_result(backtest_result)
    if backtest is not None:
        if backtest.strategy_id != subject.strategy_id:
            blocked_reasons.append("BACKTEST_STRATEGY_ID_MISMATCH")
        if backtest.strategy_version != subject.strategy_version:
            blocked_reasons.append("BACKTEST_STRATEGY_VERSION_MISMATCH")
        if backtest.backtest_result_id != subject.backtest_result_id:
            blocked_reasons.append("BACKTEST_RESULT_ID_MISMATCH")

    context_reasons, context_material, context_id = _validate_context(context, policy, backtest)
    blocked_reasons.extend(context_reasons)
    if execution_state not in _ALLOWED_EXECUTION_STATES:
        blocked_reasons.append("EXECUTION_STATE_INVALID")

    if blocked_reasons:
        decision = "BLOCKED"
        reason_codes = _ordered_reasons(blocked_reasons, BLOCK_REASON_ORDER)
    elif execution_state == EXECUTION_NOT_RUN:
        decision = "NOT_RUN"
        reason_codes = (NOT_RUN_REASON_CODE,)
    else:
        assert backtest is not None
        fail_reasons: list[str] = []
        if backtest.total_trades < policy.min_total_trades:
            fail_reasons.append("MIN_TOTAL_TRADES_NOT_MET")
        if backtest.net_pnl < policy.min_net_pnl:
            fail_reasons.append("MIN_NET_PNL_NOT_MET")
        if backtest.max_drawdown > policy.max_drawdown:
            fail_reasons.append("MAX_DRAWDOWN_EXCEEDED")
        if backtest.max_consecutive_losses > policy.max_consecutive_losses:
            fail_reasons.append("MAX_CONSECUTIVE_LOSSES_EXCEEDED")
        if policy.min_profit_factor is not None:
            if backtest.profit_factor is None:
                fail_reasons.append("PROFIT_FACTOR_REQUIRED_BUT_NULL")
            elif backtest.profit_factor < policy.min_profit_factor:
                fail_reasons.append("MIN_PROFIT_FACTOR_NOT_MET")

        if fail_reasons:
            decision = "FAIL"
            reason_codes = _ordered_reasons(fail_reasons, FAIL_REASON_ORDER)
        else:
            decision = "PASS"
            reason_codes = (PASS_REASON_CODE,)

    policy_material = policy.material()
    policy_id = policy.identity
    identity_material = {
        "schema_version": SCHEMA_VERSION,
        "strategy_id": subject.strategy_id,
        "strategy_version": subject.strategy_version,
        "backtest_result_id": subject.backtest_result_id,
        "validation_policy_version": policy.version,
        "validation_policy_id": policy_id,
        "oos_context_id": context_id,
        "execution_state": execution_state,
        "decision": decision,
        "reason_codes": list(reason_codes),
    }
    decision_id = _hash_id("validation_decision_", identity_material)

    return ValidationDecision(
        validation_decision_id=decision_id,
        strategy_id=subject.strategy_id,
        strategy_version=subject.strategy_version,
        backtest_result_id=subject.backtest_result_id,
        validation_policy_version=policy.version,
        validation_policy_id=policy_id,
        oos_context_id=context_id,
        decision=decision,
        reason_codes=reason_codes,
        decided_at=observed_at,
        execution_state=execution_state,
        policy_material=policy_material,
        oos_binding=context_material,
    )
