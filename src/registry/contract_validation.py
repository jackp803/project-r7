from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import (
    EVIDENCE_STATUSES,
    VERIFICATION_KINDS,
    EvidenceGateError,
    SUPPORTED_SHARED_SCHEMA_VERSION,
    VALIDATION_DECISIONS,
)

BACKTEST_IDENTITY_REPRODUCIBILITY_FIELDS = (
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
)

BACKTEST_CORE_METRIC_FIELDS = (
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

VALIDATION_DECISION_FIELDS = (
    "schema_version",
    "validation_decision_id",
    "strategy_id",
    "strategy_version",
    "backtest_result_id",
    "validation_policy_version",
    "decision",
    "reason_codes",
    "decided_at",
)


@dataclass(frozen=True)
class BacktestContractView:
    schema_version: str
    backtest_result_id: str
    strategy_id: str
    strategy_version: str
    strategy_content_hash: str


@dataclass(frozen=True)
class ValidationDecisionContractView:
    schema_version: str
    validation_decision_id: str
    strategy_id: str
    strategy_version: str
    backtest_result_id: str
    decision: str


def _require_mapping(payload: Any, object_name: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise EvidenceGateError(f"{object_name} must be a mapping")
    return payload


def _require_fields(payload: Mapping[str, Any], fields: Sequence[str], object_name: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise EvidenceGateError(
            f"{object_name} missing required fields: {', '.join(sorted(missing))}"
        )


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceGateError(f"{field} must be a non-empty string")
    return value


def _require_utc_timestamp(value: Any, field: str) -> datetime:
    text = _require_nonempty_string(value, field)
    if not text.endswith("Z"):
        raise EvidenceGateError(f"{field} must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceGateError(f"{field} must be a valid RFC 3339 UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise EvidenceGateError(f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _require_nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise EvidenceGateError(f"{field} must be a non-negative integer")
    return value


def _require_decimal_string(value: Any, field: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value.strip():
        raise EvidenceGateError(f"{field} must be a base-10 decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise EvidenceGateError(f"{field} must be a valid base-10 decimal string") from exc
    if not parsed.is_finite():
        raise EvidenceGateError(f"{field} must be a finite base-10 decimal string")
    return value


def validate_verification_metadata(*, status: str, verification_kind: str) -> None:
    if status not in EVIDENCE_STATUSES:
        raise EvidenceGateError("unsupported evidence verification_status")
    if verification_kind not in VERIFICATION_KINDS:
        raise EvidenceGateError("unsupported evidence verification_kind")


def validate_backtest_result_contract(payload: Any) -> BacktestContractView:
    raw = _require_mapping(payload, "BacktestResult")
    _require_fields(
        raw,
        BACKTEST_IDENTITY_REPRODUCIBILITY_FIELDS + BACKTEST_CORE_METRIC_FIELDS,
        "BacktestResult",
    )

    schema = _require_nonempty_string(raw["schema_version"], "BacktestResult.schema_version")
    if schema != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise EvidenceGateError(
            f"unsupported BacktestResult schema_version={schema}; "
            f"expected {SUPPORTED_SHARED_SCHEMA_VERSION}"
        )

    backtest_result_id = _require_nonempty_string(
        raw["backtest_result_id"], "BacktestResult.backtest_result_id"
    )
    strategy_id = _require_nonempty_string(raw["strategy_id"], "BacktestResult.strategy_id")
    strategy_version = _require_nonempty_string(
        raw["strategy_version"], "BacktestResult.strategy_version"
    )
    strategy_content_hash = _require_nonempty_string(
        raw["strategy_content_hash"], "BacktestResult.strategy_content_hash"
    )
    _require_nonempty_string(raw["runtime_version"], "BacktestResult.runtime_version")
    _require_nonempty_string(raw["dataset_id"], "BacktestResult.dataset_id")
    _require_nonempty_string(raw["dataset_hash"], "BacktestResult.dataset_hash")
    dataset_start = _require_utc_timestamp(raw["dataset_start"], "BacktestResult.dataset_start")
    dataset_end = _require_utc_timestamp(raw["dataset_end"], "BacktestResult.dataset_end")
    if dataset_start > dataset_end:
        raise EvidenceGateError("BacktestResult.dataset_start must not be after dataset_end")
    _require_nonempty_string(raw["cost_model_version"], "BacktestResult.cost_model_version")
    _require_utc_timestamp(raw["created_at"], "BacktestResult.created_at")

    for field in ("total_trades", "wins", "losses", "breakeven", "max_consecutive_losses"):
        _require_nonnegative_int(raw[field], f"BacktestResult.{field}")

    for field in (
        "gross_pnl",
        "net_pnl",
        "total_fees",
        "expectancy",
        "max_drawdown",
    ):
        _require_decimal_string(raw[field], f"BacktestResult.{field}")
    _require_decimal_string(
        raw["profit_factor"],
        "BacktestResult.profit_factor",
        allow_none=True,
    )

    return BacktestContractView(
        schema_version=schema,
        backtest_result_id=backtest_result_id,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        strategy_content_hash=strategy_content_hash,
    )


def validate_validation_decision_contract(payload: Any) -> ValidationDecisionContractView:
    raw = _require_mapping(payload, "ValidationDecision")
    _require_fields(raw, VALIDATION_DECISION_FIELDS, "ValidationDecision")

    schema = _require_nonempty_string(raw["schema_version"], "ValidationDecision.schema_version")
    if schema != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise EvidenceGateError(
            f"unsupported ValidationDecision schema_version={schema}; "
            f"expected {SUPPORTED_SHARED_SCHEMA_VERSION}"
        )

    validation_decision_id = _require_nonempty_string(
        raw["validation_decision_id"], "ValidationDecision.validation_decision_id"
    )
    strategy_id = _require_nonempty_string(
        raw["strategy_id"], "ValidationDecision.strategy_id"
    )
    strategy_version = _require_nonempty_string(
        raw["strategy_version"], "ValidationDecision.strategy_version"
    )
    backtest_result_id = _require_nonempty_string(
        raw["backtest_result_id"], "ValidationDecision.backtest_result_id"
    )
    _require_nonempty_string(
        raw["validation_policy_version"], "ValidationDecision.validation_policy_version"
    )

    decision = _require_nonempty_string(raw["decision"], "ValidationDecision.decision")
    if decision not in VALIDATION_DECISIONS:
        allowed = " | ".join(VALIDATION_DECISIONS)
        raise EvidenceGateError(
            f"ValidationDecision.decision must be one of: {allowed}"
        )

    reason_codes = raw["reason_codes"]
    if isinstance(reason_codes, (str, bytes, bytearray)) or not isinstance(reason_codes, Sequence):
        raise EvidenceGateError("ValidationDecision.reason_codes must be a sequence of strings")
    for index, reason in enumerate(reason_codes):
        _require_nonempty_string(reason, f"ValidationDecision.reason_codes[{index}]")

    _require_utc_timestamp(raw["decided_at"], "ValidationDecision.decided_at")

    return ValidationDecisionContractView(
        schema_version=schema,
        validation_decision_id=validation_decision_id,
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        backtest_result_id=backtest_result_id,
        decision=decision,
    )
