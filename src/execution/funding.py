from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SCHEMA_VERSION = "contracts-v0.1"
FUNDING_EVIDENCE_PROFILE_VERSION = "funding-allocation-v0.1"
PAPER_SOURCE_KIND = "PAPER_MODEL"
PAPER_SOURCE = "R7_PAPER_FUNDING_MODEL"
PAPER_ZERO_SOURCE_VERSION = "paper-zero-funding-v0.1"
INTERVAL_SEMANTICS = "START_INCLUSIVE_END_EXCLUSIVE"
ZERO_CONFIRMED = "ZERO_CONFIRMED"
COST_CURRENCY = "USDT"
ZERO_FUNDING_COST = "0"
ZERO_SOURCE_RECORD_COUNT = 0
ZERO_ASSERTION = "FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL"
COMPLETENESS_ASSERTION = "MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END"

_IDENTITY_FIELDS = (
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


class FundingEvidenceError(ValueError):
    """Fail-closed E4 producer error for funding-allocation-v0.1."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PaperZeroFundingModel:
    """Registered local Paper model asserting zero funding for every requested instant.

    The producer accepts only the exact registered V0.1 semantics below. A caller
    can construct a different instance for negative tests, but unsupported source
    material is rejected rather than treated as ZERO_CONFIRMED.
    """

    source_kind: str = PAPER_SOURCE_KIND
    source: str = PAPER_SOURCE
    source_version: str = PAPER_ZERO_SOURCE_VERSION
    zero_assertion: str = ZERO_ASSERTION
    completeness_assertion: str = COMPLETENESS_ASSERTION
    interval_semantics: str = INTERVAL_SEMANTICS
    status: str = ZERO_CONFIRMED
    funding_cost: str = ZERO_FUNDING_COST
    cost_currency: str = COST_CURRENCY
    source_record_count: int = ZERO_SOURCE_RECORD_COUNT


DEFAULT_PAPER_ZERO_FUNDING_MODEL = PaperZeroFundingModel()


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FundingEvidenceError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    if value != value.strip():
        raise FundingEvidenceError(
            "NONCANONICAL_TEXT_FIELD",
            f"{field} must not contain surrounding whitespace",
        )
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise FundingEvidenceError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise FundingEvidenceError(
            "INVALID_DECIMAL",
            f"{field} must be Decimal or a base-10 decimal string",
        )
    if not parsed.is_finite():
        raise FundingEvidenceError("INVALID_DECIMAL", f"{field} must be finite")
    return parsed


def _utc(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise FundingEvidenceError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FundingEvidenceError(
            "INVALID_TIMESTAMP",
            f"{field} must be RFC 3339 UTC ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FundingEvidenceError("INVALID_TIMESTAMP", f"{field} must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise FundingEvidenceError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> str:
    # Match the repository's existing deterministic identity convention.
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_material(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_registered_model(model: PaperZeroFundingModel) -> None:
    if not isinstance(model, PaperZeroFundingModel):
        raise FundingEvidenceError(
            "UNSUPPORTED_FUNDING_SOURCE",
            "funding producer requires the registered local Paper zero-funding model",
        )
    if type(model.source_record_count) is not int:
        raise FundingEvidenceError(
            "UNSUPPORTED_FUNDING_MODEL_VERSION",
            "source_record_count must be the exact registered integer zero",
        )
    expected = DEFAULT_PAPER_ZERO_FUNDING_MODEL
    fields = (
        "source_kind",
        "source",
        "source_version",
        "zero_assertion",
        "completeness_assertion",
        "interval_semantics",
        "status",
        "funding_cost",
        "cost_currency",
        "source_record_count",
    )
    for field in fields:
        if getattr(model, field) != getattr(expected, field):
            raise FundingEvidenceError(
                "UNSUPPORTED_FUNDING_MODEL_VERSION",
                f"unsupported Paper funding model semantics: {field}",
            )


def _validate_plan_and_flat_position(
    parent_plan: Mapping[str, Any],
    final_position: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(parent_plan, Mapping):
        raise FundingEvidenceError("INVALID_PARENT_PLAN", "ApprovedTradePlan must be a mapping")
    if not isinstance(final_position, Mapping):
        raise FundingEvidenceError("INVALID_FINAL_POSITION", "final Position must be a mapping")

    plan_required = {"schema_version", "trade_plan_id", "symbol"}
    position_required = {
        "schema_version",
        "position_id",
        "symbol",
        "actual_quantity",
        "reconciliation_status",
        "opened_at",
        "broker_state_observed_at",
    }
    missing_plan = sorted(plan_required - set(parent_plan.keys()))
    missing_position = sorted(position_required - set(final_position.keys()))
    if missing_plan:
        raise FundingEvidenceError(
            "PARENT_PLAN_INCOMPLETE",
            "ApprovedTradePlan missing required fields: " + ", ".join(missing_plan),
        )
    if missing_position:
        raise FundingEvidenceError(
            "FINAL_POSITION_INCOMPLETE",
            "final Position missing required fields: " + ", ".join(missing_position),
        )

    if parent_plan.get("schema_version") != SCHEMA_VERSION:
        raise FundingEvidenceError(
            "UNSUPPORTED_SCHEMA_VERSION",
            "ApprovedTradePlan schema_version is unsupported",
        )
    if final_position.get("schema_version") != SCHEMA_VERSION:
        raise FundingEvidenceError(
            "UNSUPPORTED_SCHEMA_VERSION",
            "final Position schema_version is unsupported",
        )

    trade_plan_id = _nonempty_text(parent_plan.get("trade_plan_id"), "ApprovedTradePlan.trade_plan_id")
    position_id = _nonempty_text(final_position.get("position_id"), "final Position.position_id")
    plan_symbol = _nonempty_text(parent_plan.get("symbol"), "ApprovedTradePlan.symbol")
    position_symbol = _nonempty_text(final_position.get("symbol"), "final Position.symbol")
    if position_symbol != plan_symbol:
        raise FundingEvidenceError(
            "PLAN_POSITION_SYMBOL_MISMATCH",
            "final Position symbol must match the exact parent ApprovedTradePlan symbol",
        )

    actual_quantity = _decimal(final_position.get("actual_quantity"), "final Position.actual_quantity")
    if actual_quantity != Decimal("0"):
        raise FundingEvidenceError(
            "FINAL_POSITION_NOT_FLAT",
            "funding evidence requires authoritative final Position actual_quantity=0",
        )
    if final_position.get("reconciliation_status") != "CONSISTENT":
        raise FundingEvidenceError(
            "FINAL_POSITION_NOT_CONSISTENT",
            "funding evidence requires final Position reconciliation_status=CONSISTENT",
        )

    interval_start_dt = _utc(final_position.get("opened_at"), "final Position.opened_at")
    interval_end_dt = _utc(
        final_position.get("broker_state_observed_at"),
        "final Position.broker_state_observed_at",
    )
    if interval_start_dt >= interval_end_dt:
        raise FundingEvidenceError(
            "INVALID_FUNDING_INTERVAL",
            "funding interval requires opened_at < broker_state_observed_at",
        )

    if final_position.get("closed_at") is not None:
        closed_at = _utc(final_position.get("closed_at"), "final Position.closed_at")
        if closed_at != interval_end_dt:
            raise FundingEvidenceError(
                "FINAL_POSITION_CLOSED_AT_CONFLICT",
                "final Position.closed_at must equal the authoritative flat observation time when present",
            )

    return {
        "trade_plan_id": trade_plan_id,
        "position_id": position_id,
        "symbol": plan_symbol,
        "interval_start": _fmt_utc(interval_start_dt),
        "interval_end": _fmt_utc(interval_end_dt),
        "interval_end_dt": interval_end_dt,
    }


def paper_zero_source_material(
    parent_plan: Mapping[str, Any],
    final_position: Mapping[str, Any],
    *,
    model: PaperZeroFundingModel = DEFAULT_PAPER_ZERO_FUNDING_MODEL,
) -> dict[str, Any]:
    """Return the normalized complete zero-model assertion material hashed by E4."""

    _validate_registered_model(model)
    facts = _validate_plan_and_flat_position(parent_plan, final_position)
    return {
        "assertion": model.zero_assertion,
        "completeness_assertion": model.completeness_assertion,
        "cost_currency": model.cost_currency,
        "funding_cost": model.funding_cost,
        "interval_end": facts["interval_end"],
        "interval_semantics": model.interval_semantics,
        "interval_start": facts["interval_start"],
        "position_id": facts["position_id"],
        "source": model.source,
        "source_complete_through": facts["interval_end"],
        "source_kind": model.source_kind,
        "source_record_count": model.source_record_count,
        "source_version": model.source_version,
        "status": model.status,
        "symbol": facts["symbol"],
        "trade_plan_id": facts["trade_plan_id"],
    }


def funding_evidence_identity_material(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Extract exactly the normative identity-bearing funding-allocation-v0.1 fields."""

    if not isinstance(evidence, Mapping):
        raise FundingEvidenceError("INVALID_EVIDENCE", "FundingAllocationEvidence must be a mapping")
    missing = [field for field in _IDENTITY_FIELDS if field not in evidence]
    if missing:
        raise FundingEvidenceError(
            "FUNDING_EVIDENCE_INCOMPLETE",
            "FundingAllocationEvidence missing identity fields: " + ", ".join(missing),
        )
    return {field: evidence[field] for field in _IDENTITY_FIELDS}


def stable_funding_evidence_id(evidence: Mapping[str, Any]) -> str:
    """Derive canonical fundev_<sha256> identity; calculated_at is intentionally excluded."""

    identity_material = funding_evidence_identity_material(evidence)
    return "fundev_" + _sha256_material(identity_material)


def produce_paper_zero_funding_evidence(
    parent_plan: Mapping[str, Any],
    final_position: Mapping[str, Any],
    *,
    calculated_at: datetime | str,
    model: PaperZeroFundingModel = DEFAULT_PAPER_ZERO_FUNDING_MODEL,
) -> dict[str, Any]:
    """Produce canonical funding-allocation-v0.1 ZERO_CONFIRMED Paper evidence.

    ZERO_CONFIRMED is authorized only by the exact registered model semantics,
    which affirmatively define zero funding for every instant in the exact
    [opened_at, flat-observed-at) interval. Missing/unavailable source data are
    never interpreted as zero by this producer.
    """

    _validate_registered_model(model)
    facts = _validate_plan_and_flat_position(parent_plan, final_position)
    calculated_dt = _utc(calculated_at, "calculated_at")
    if calculated_dt < facts["interval_end_dt"]:
        raise FundingEvidenceError(
            "CALCULATED_BEFORE_INTERVAL_END",
            "calculated_at must be at or after the authoritative interval_end",
        )

    source_material = paper_zero_source_material(
        parent_plan,
        final_position,
        model=model,
    )
    source_material_hash = _sha256_material(source_material)

    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "funding_evidence_profile_version": FUNDING_EVIDENCE_PROFILE_VERSION,
        "source_kind": model.source_kind,
        "source": model.source,
        "source_version": model.source_version,
        "source_material_hash": source_material_hash,
        "source_record_count": model.source_record_count,
        "source_complete_through": facts["interval_end"],
        "trade_plan_id": facts["trade_plan_id"],
        "position_id": facts["position_id"],
        "symbol": facts["symbol"],
        "interval_start": facts["interval_start"],
        "interval_end": facts["interval_end"],
        "interval_semantics": model.interval_semantics,
        "status": model.status,
        "funding_cost": model.funding_cost,
        "cost_currency": model.cost_currency,
        "calculated_at": _fmt_utc(calculated_dt),
    }
    evidence["funding_evidence_id"] = stable_funding_evidence_id(evidence)
    return {
        "schema_version": evidence["schema_version"],
        "funding_evidence_profile_version": evidence["funding_evidence_profile_version"],
        "funding_evidence_id": evidence["funding_evidence_id"],
        "source_kind": evidence["source_kind"],
        "source": evidence["source"],
        "source_version": evidence["source_version"],
        "source_material_hash": evidence["source_material_hash"],
        "source_record_count": evidence["source_record_count"],
        "source_complete_through": evidence["source_complete_through"],
        "trade_plan_id": evidence["trade_plan_id"],
        "position_id": evidence["position_id"],
        "symbol": evidence["symbol"],
        "interval_start": evidence["interval_start"],
        "interval_end": evidence["interval_end"],
        "interval_semantics": evidence["interval_semantics"],
        "status": evidence["status"],
        "funding_cost": evidence["funding_cost"],
        "cost_currency": evidence["cost_currency"],
        "calculated_at": evidence["calculated_at"],
    }
