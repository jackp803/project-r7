from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

from .lifecycle_execution_binding import (
    LifecycleExecutionBindingError,
    validate_position_lifecycle_execution_evidence_binding,
)
from .lifecycle_projection import (
    LifecycleProjectionError,
    validate_position_lifecycle_projection,
)
from .state_machine import (
    PositionEvent,
    PositionLifecycleState,
    UnsafeTransitionError,
    transition,
)

SCHEMA_VERSION = "contracts-v0.1"
FP04_PROFILE_VERSION = "external-provider-object-ownership-reconciliation-v0.1"
FP10_PROFILE_VERSION = "external-manual-close-lifecycle-convergence-v0.1"

CURRENT = "CURRENT"
STALE = "STALE"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"
CONSISTENT = "CONSISTENT"

LIFECYCLE_CLOSE_ELIGIBLE = "LIFECYCLE_CLOSE_ELIGIBLE"
EXPOSURE_STILL_OPEN = "EXPOSURE_STILL_OPEN"
EXPOSURE_REDUCED_NOT_FLAT = "EXPOSURE_REDUCED_NOT_FLAT"
FLAT_PROVIDER_TRUTH_PROVEN = "FLAT_PROVIDER_TRUTH_PROVEN"
FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED = "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED"
FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED = (
    "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED"
)
EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED = "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED"
OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED = "OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED"
RESIDUAL_UNREPRESENTABLE_NOT_FLAT = "RESIDUAL_UNREPRESENTABLE_NOT_FLAT"
CONVERGENCE_EVIDENCE_STALE = "CONVERGENCE_EVIDENCE_STALE"
CONVERGENCE_UNKNOWN = "CONVERGENCE_UNKNOWN"

TERMINAL_PROTECTION_CLEAR = "TERMINAL_PROTECTION_CLEAR"
TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED = (
    "TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED"
)
TERMINAL_PROTECTION_OBSERVATION_STALE = "TERMINAL_PROTECTION_OBSERVATION_STALE"
TERMINAL_PROTECTION_OBSERVATION_UNKNOWN = "TERMINAL_PROTECTION_OBSERVATION_UNKNOWN"

RESIDUAL_NONZERO_REPRESENTABLE = "RESIDUAL_NONZERO_REPRESENTABLE"
RESIDUAL_NONZERO_UNREPRESENTABLE = "RESIDUAL_NONZERO_UNREPRESENTABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"

CURRENT_GENERATION_PROJECT = "CURRENT_GENERATION_PROJECT"
PRIOR_GENERATION_PROJECT = "PRIOR_GENERATION_PROJECT"
EXTERNAL_MANUAL = "EXTERNAL_MANUAL"
MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"

KNOWN_OWNED_CURRENT_GENERATION = "KNOWN_OWNED_CURRENT_GENERATION"
KNOWN_OWNED_PRIOR_GENERATION = "KNOWN_OWNED_PRIOR_GENERATION"
EXTERNAL_UNTRACKED = "EXTERNAL_UNTRACKED"
ADOPTABLE_BY_EXPLICIT_POLICY = "ADOPTABLE_BY_EXPLICIT_POLICY"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
CONFLICTING_OWNERSHIP_EVIDENCE = "CONFLICTING_OWNERSHIP_EVIDENCE"

CURRENT_KNOWN_OWNED = "CURRENT_KNOWN_OWNED"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
ADOPTION_EVALUATION_REQUIRED = "ADOPTION_EVALUATION_REQUIRED"
CONVERGENCE_REQUIRED = "CONVERGENCE_REQUIRED"

NO_ACTION_CURRENT_KNOWN_OWNED = "NO_ACTION_CURRENT_KNOWN_OWNED"
NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE = "NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"
TRADE_RESULT_EVIDENCE_INCOMPLETE = "TRADE_RESULT_EVIDENCE_INCOMPLETE"
LIFECYCLE_CLOSE_ELIGIBLE_PROVEN = "LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"

DECISION_RETAIN_OPEN = "RETAIN_OPEN"
DECISION_CLOSE = "CLOSE"
DECISION_RECONCILE = "RECONCILE"
DECISION_REATTEST = "REATTEST"
DECISION_HOLD_SAFE = "HOLD_SAFE"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FP04_ID_RE = re.compile(r"^extownrec_[0-9a-f]{64}$")
_FP10_ID_RE = re.compile(r"^extcloseconv_[0-9a-f]{64}$")
_DECISION_ID_RE = re.compile(r"^e5extclose_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_FP04_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "external_provider_ownership_profile_version",
        "ownership_evidence_id",
        "provider_object_class",
        "provider_identity_ref",
        "provider_identity_hash",
        "canonical_symbol",
        "provider_instrument_ref",
        "provider_object_ref",
        "provider_snapshot_ref",
        "provider_snapshot_hash",
        "provider_observation_generation_id",
        "provider_observed_at",
        "provider_received_at",
        "current_project_revision",
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
        "local_lineage_evidence",
        "local_registry_evidence",
        "ownership_classification",
        "reconciliation_status",
        "required_dispositions",
        "reason_codes",
        "adoption_decision_ref",
        "supersedes_ownership_evidence_id",
        "evaluated_at",
    }
)

_FP10_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "external_manual_close_convergence_profile_version",
        "close_convergence_evidence_id",
        "position_id",
        "canonical_symbol",
        "provider_identity_ref",
        "provider_identity_hash",
        "provider_instrument_ref",
        "provider_position_snapshot_ref",
        "provider_position_snapshot_hash",
        "provider_position_observation_generation_id",
        "provider_position_observed_at",
        "provider_position_received_at",
        "provider_position_currentness_status",
        "normalized_position_ref",
        "normalized_position_hash",
        "normalized_position_broker_state_observed_at",
        "normalized_position_reconciliation_status",
        "normalized_actual_quantity",
        "normalized_quantity_profile_version",
        "normalized_quantity_unit",
        "normalized_quantity_asset",
        "execution_evidence",
        "execution_evidence_set_hash",
        "fp04_ownership_evidence",
        "fp04_evidence_set_hash",
        "fp05_close_residual_sizing_ref",
        "fp05_close_residual_sizing_hash",
        "fp05_residual_state",
        "fp11_prior_registry_evidence_ref",
        "fp11_prior_registry_evidence_hash",
        "terminal_protection_observation_ref",
        "terminal_protection_observation_hash",
        "terminal_protection_observed_at",
        "terminal_protection_received_at",
        "terminal_protection_status",
        "lifecycle_projection_ref",
        "lifecycle_projection_hash",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "lifecycle_state",
        "lifecycle_execution_binding_ref",
        "lifecycle_execution_binding_hash",
        "lifecycle_execution_snapshot_hash",
        "current_project_revision",
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
        "exposure_change_origin_classification",
        "convergence_state",
        "required_dispositions",
        "reason_codes",
        "supersedes_close_convergence_evidence_id",
        "evaluated_at",
    }
)

_FP04_OBJECT_CLASSES = frozenset(
    {
        "POSITION_EXPOSURE",
        "OPEN_ORDER",
        "TERMINAL_ORDER",
        "FILL_EXECUTION",
        "ACTIVE_PROTECTION",
        "UNCLASSIFIED_PROVIDER_OBJECT",
    }
)
_FP04_OWNERSHIP = frozenset(
    {
        KNOWN_OWNED_CURRENT_GENERATION,
        KNOWN_OWNED_PRIOR_GENERATION,
        EXTERNAL_UNTRACKED,
        ADOPTABLE_BY_EXPLICIT_POLICY,
        MANUAL_REVIEW_REQUIRED,
        CONFLICTING_OWNERSHIP_EVIDENCE,
        UNKNOWN,
    }
)
_FP04_RECONCILIATION = frozenset(
    {
        CURRENT_KNOWN_OWNED,
        RECONCILIATION_REQUIRED,
        ADOPTION_EVALUATION_REQUIRED,
        MANUAL_REVIEW_REQUIRED,
        CONVERGENCE_REQUIRED,
        UNKNOWN,
    }
)
_FP10_STATES = frozenset(
    {
        EXPOSURE_STILL_OPEN,
        EXPOSURE_REDUCED_NOT_FLAT,
        FLAT_PROVIDER_TRUTH_PROVEN,
        FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED,
        FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED,
        EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED,
        OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED,
        RESIDUAL_UNREPRESENTABLE_NOT_FLAT,
        CONVERGENCE_EVIDENCE_STALE,
        CONVERGENCE_UNKNOWN,
        LIFECYCLE_CLOSE_ELIGIBLE,
    }
)
_FP10_TERMINAL_PROTECTION = frozenset(
    {
        TERMINAL_PROTECTION_CLEAR,
        TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED,
        TERMINAL_PROTECTION_OBSERVATION_STALE,
        TERMINAL_PROTECTION_OBSERVATION_UNKNOWN,
    }
)
_FP10_ORIGINS = frozenset(
    {
        CURRENT_GENERATION_PROJECT,
        PRIOR_GENERATION_PROJECT,
        EXTERNAL_MANUAL,
        MIXED_OR_UNKNOWN,
    }
)

_FP10_REASON_ORDER = (
    "CLOSE_CONVERGENCE_PROFILE_UNSUPPORTED",
    "PROVIDER_POSITION_EVIDENCE_MISSING",
    "PROVIDER_POSITION_EVIDENCE_STALE",
    "PROVIDER_NORMALIZED_POSITION_MISMATCH",
    "POSITION_RECONCILIATION_NOT_CONSISTENT",
    "POSITIVE_EXPOSURE_REMAINS",
    RESIDUAL_NONZERO_REPRESENTABLE,
    RESIDUAL_NONZERO_UNREPRESENTABLE,
    "TERMINAL_ORDER_WITHOUT_FLAT_POSITION_PROOF",
    "PRIOR_CLOSE_OUTCOME_RECONCILIATION_REQUIRED",
    "EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN",
    "EXECUTION_FILL_POSITION_CONTRADICTION",
    "EXTERNAL_MANUAL_EXECUTION_OBSERVED",
    "FP04_OWNERSHIP_EVIDENCE_MISSING",
    "FP04_OWNERSHIP_EVIDENCE_STALE",
    "FP04_OWNERSHIP_CONFLICT",
    "FP04_EXTERNAL_MANUAL_REINTERPRETATION_REQUIRED",
    "FP05_RESIDUAL_EVIDENCE_MISSING_OR_STALE",
    "FP05_RESIDUAL_STATE_CONTRADICTS_POSITION",
    "FP11_PRIOR_REGISTRY_EVIDENCE_MISSING_OR_STALE",
    "TERMINAL_PROTECTION_OBSERVATION_MISSING_OR_STALE",
    "TERMINAL_PROTECTION_OBJECT_PRESENT",
    "TERMINAL_PROTECTION_OWNERSHIP_CONFLICT",
    "LIFECYCLE_PROJECTION_STALE_OR_MISMATCHED",
    "LIFECYCLE_EXECUTION_BINDING_STALE_OR_MISMATCHED",
    "EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED",
    "RUNTIME_GENERATION_STALE_OR_MISMATCHED",
    "CONVERGENCE_EVIDENCE_SUPERSEDED",
    "CONVERGENCE_EVIDENCE_IDENTITY_INVALID",
    "CONVERGENCE_TEMPORAL_ORDER_INVALID",
    TRADE_RESULT_EVIDENCE_INCOMPLETE,
    TERMINAL_PROTECTION_CLEAR,
    LIFECYCLE_CLOSE_ELIGIBLE_PROVEN,
)
_FP10_REASON_INDEX = {value: index for index, value in enumerate(_FP10_REASON_ORDER)}


class ExternalCloseReinterpretationError(ValueError):
    """Fail-closed error for the E5 FP-04/FP-10 consumer boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CurrentExternalCloseAuthority:
    """E5-internal current-authority envelope; not a shared serialized contract."""

    normalized_position: Mapping[str, Any] | None
    normalized_position_ref: str | None
    provider_identity_ref: str | None
    provider_identity_hash: str | None
    provider_instrument_ref: str | None
    provider_position_snapshot_ref: str | None
    provider_position_snapshot_hash: str | None
    provider_position_observation_generation_id: str | None
    provider_position_observed_at: str | None
    provider_position_received_at: str | None
    execution_evidence_set_hash: str | None
    fp04_ownership_evidence: Sequence[Mapping[str, Any]]
    fp05_close_residual_sizing_ref: str | None
    fp05_close_residual_sizing_hash: str | None
    fp05_residual_state: str
    terminal_protection_observation_ref: str | None
    terminal_protection_observation_hash: str | None
    terminal_protection_observed_at: str | None
    terminal_protection_received_at: str | None
    terminal_protection_status: str
    lifecycle_projection: Mapping[str, Any] | None
    lifecycle_projection_ref: str | None
    lifecycle_execution_binding: Mapping[str, Any] | None
    lifecycle_execution_binding_ref: str | None
    current_project_revision: str
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None


@dataclass(frozen=True)
class ExternalCloseReinterpretationDecision:
    """E5-owned provider-neutral lifecycle interpretation result."""

    decision_id: str
    decision: str
    event: PositionEvent | None
    next_state: PositionLifecycleState
    reason_codes: tuple[str, ...]
    close_eligible: bool
    trade_result_evidence_incomplete: bool
    evidence_current: bool


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ExternalCloseReinterpretationError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ExternalCloseReinterpretationError("NONCANONICAL_TIME", "datetime must be timezone-aware UTC")
        return _fmt_utc(value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ExternalCloseReinterpretationError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ExternalCloseReinterpretationError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ExternalCloseReinterpretationError(
        "NONCANONICAL_VALUE", f"unsupported canonical type: {type(value).__name__}"
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _utc_text(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExternalCloseReinterpretationError("INVALID_TEXT", f"{field} must be canonical non-empty text")
    return value


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise ExternalCloseReinterpretationError("INVALID_HASH", f"{field} must be sha256:<hex>")
    return text


def _quantity(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise ExternalCloseReinterpretationError("INVALID_QUANTITY", f"{field} must be canonical non-negative decimal text")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ExternalCloseReinterpretationError("INVALID_QUANTITY", f"{field} is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ExternalCloseReinterpretationError("INVALID_QUANTITY", f"{field} must be finite and non-negative")
    return parsed


def stable_external_provider_ownership_evidence_id(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    material.pop("ownership_evidence_id", None)
    return "extownrec_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def stable_external_close_convergence_evidence_id(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    material.pop("close_convergence_evidence_id", None)
    return "extcloseconv_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _validate_sorted_refs(items: Any, *, fields: tuple[str, ...], label: str) -> None:
    if not isinstance(items, list):
        raise ExternalCloseReinterpretationError("INVALID_SEQUENCE", f"{label} must be a list")
    keys: list[tuple[Any, ...]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ExternalCloseReinterpretationError("INVALID_SEQUENCE", f"{label} entries must be mappings")
        keys.append(tuple(item.get(field) for field in fields))
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ExternalCloseReinterpretationError("NONDETERMINISTIC_SEQUENCE", f"{label} must be uniquely sorted")


def validate_external_provider_ownership_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate self-contained FP-04 shared evidence without manufacturing provider truth."""

    if not isinstance(evidence, Mapping) or set(evidence) != _FP04_REQUIRED_FIELDS:
        raise ExternalCloseReinterpretationError("FP04_FIELDS_INVALID", "FP-04 evidence fields mismatch")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ExternalCloseReinterpretationError("FP04_SCHEMA_UNSUPPORTED", "FP-04 schema unsupported")
    if evidence.get("external_provider_ownership_profile_version") != FP04_PROFILE_VERSION:
        raise ExternalCloseReinterpretationError("FP04_PROFILE_UNSUPPORTED", "FP-04 profile unsupported")
    evidence_id = evidence.get("ownership_evidence_id")
    if not isinstance(evidence_id, str) or _FP04_ID_RE.fullmatch(evidence_id) is None:
        raise ExternalCloseReinterpretationError("FP04_ID_INVALID", "ownership_evidence_id is invalid")
    if evidence_id != stable_external_provider_ownership_evidence_id(evidence):
        raise ExternalCloseReinterpretationError("FP04_IDENTITY_MISMATCH", "ownership evidence identity mismatch")

    if evidence.get("provider_object_class") not in _FP04_OBJECT_CLASSES:
        raise ExternalCloseReinterpretationError("FP04_OBJECT_CLASS_INVALID", "provider object class unsupported")
    if evidence.get("ownership_classification") not in _FP04_OWNERSHIP:
        raise ExternalCloseReinterpretationError("FP04_OWNERSHIP_INVALID", "ownership classification unsupported")
    if evidence.get("reconciliation_status") not in _FP04_RECONCILIATION:
        raise ExternalCloseReinterpretationError("FP04_RECONCILIATION_INVALID", "reconciliation status unsupported")

    for field in (
        "provider_identity_ref",
        "canonical_symbol",
        "provider_instrument_ref",
        "provider_object_ref",
        "provider_snapshot_ref",
        "provider_observation_generation_id",
        "current_project_revision",
    ):
        _text(evidence.get(field), field)
    for field in ("provider_identity_hash", "provider_snapshot_hash"):
        _hash(evidence.get(field), field)
    observed = _utc_text(evidence.get("provider_observed_at"), "provider_observed_at")
    received = _utc_text(evidence.get("provider_received_at"), "provider_received_at")
    evaluated = _utc_text(evidence.get("evaluated_at"), "evaluated_at")
    if received < observed or evaluated < received:
        raise ExternalCloseReinterpretationError("FP04_TEMPORAL_ORDER_INVALID", "FP-04 temporal ordering invalid")

    _validate_sorted_refs(
        evidence.get("local_lineage_evidence"),
        fields=("owner", "evidence_class", "evidence_ref"),
        label="local_lineage_evidence",
    )
    _validate_sorted_refs(
        evidence.get("local_registry_evidence"),
        fields=("owner", "evidence_class", "evidence_ref"),
        label="local_registry_evidence",
    )
    if not isinstance(evidence.get("required_dispositions"), list) or not evidence["required_dispositions"]:
        raise ExternalCloseReinterpretationError("FP04_DISPOSITIONS_INVALID", "required_dispositions must be non-empty")
    if not isinstance(evidence.get("reason_codes"), list) or not evidence["reason_codes"]:
        raise ExternalCloseReinterpretationError("FP04_REASONS_INVALID", "reason_codes must be non-empty")

    if evidence["reconciliation_status"] == CURRENT_KNOWN_OWNED:
        if (
            evidence["ownership_classification"] != KNOWN_OWNED_CURRENT_GENERATION
            or evidence["required_dispositions"] != [NO_ACTION_CURRENT_KNOWN_OWNED]
            or evidence["reason_codes"] != ["CURRENT_GENERATION_OWNERSHIP_PROVEN"]
        ):
            raise ExternalCloseReinterpretationError(
                "FP04_FALSE_CURRENT_OWNERSHIP", "CURRENT_KNOWN_OWNED requires exact current-owned success tuple"
            )


def validate_external_manual_close_convergence_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate self-contained FP-10 convergence evidence and false-green invariants."""

    if not isinstance(evidence, Mapping) or set(evidence) != _FP10_REQUIRED_FIELDS:
        raise ExternalCloseReinterpretationError("FP10_FIELDS_INVALID", "FP-10 evidence fields mismatch")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ExternalCloseReinterpretationError("FP10_SCHEMA_UNSUPPORTED", "FP-10 schema unsupported")
    if evidence.get("external_manual_close_convergence_profile_version") != FP10_PROFILE_VERSION:
        raise ExternalCloseReinterpretationError("FP10_PROFILE_UNSUPPORTED", "FP-10 profile unsupported")

    evidence_id = evidence.get("close_convergence_evidence_id")
    if not isinstance(evidence_id, str) or _FP10_ID_RE.fullmatch(evidence_id) is None:
        raise ExternalCloseReinterpretationError("FP10_ID_INVALID", "close_convergence_evidence_id is invalid")
    if evidence_id != stable_external_close_convergence_evidence_id(evidence):
        raise ExternalCloseReinterpretationError("FP10_IDENTITY_MISMATCH", "FP-10 evidence identity mismatch")

    for field in (
        "position_id",
        "canonical_symbol",
        "provider_identity_ref",
        "provider_instrument_ref",
        "provider_position_snapshot_ref",
        "provider_position_observation_generation_id",
        "normalized_position_ref",
        "normalized_position_broker_state_observed_at",
        "normalized_position_reconciliation_status",
        "normalized_quantity_profile_version",
        "normalized_quantity_unit",
        "normalized_quantity_asset",
        "terminal_protection_observation_ref",
        "lifecycle_projection_ref",
        "lifecycle_projection_id",
        "lifecycle_state",
        "lifecycle_execution_binding_ref",
        "lifecycle_execution_snapshot_hash",
        "current_project_revision",
    ):
        _text(evidence.get(field), field)
    for field in (
        "provider_identity_hash",
        "provider_position_snapshot_hash",
        "normalized_position_hash",
        "execution_evidence_set_hash",
        "fp04_evidence_set_hash",
        "terminal_protection_observation_hash",
        "lifecycle_projection_hash",
        "lifecycle_execution_binding_hash",
        "lifecycle_execution_snapshot_hash",
    ):
        _hash(evidence.get(field), field)

    provider_observed = _utc_text(evidence.get("provider_position_observed_at"), "provider_position_observed_at")
    provider_received = _utc_text(evidence.get("provider_position_received_at"), "provider_position_received_at")
    terminal_observed = _utc_text(evidence.get("terminal_protection_observed_at"), "terminal_protection_observed_at")
    terminal_received = _utc_text(evidence.get("terminal_protection_received_at"), "terminal_protection_received_at")
    evaluated = _utc_text(evidence.get("evaluated_at"), "evaluated_at")
    if provider_received < provider_observed or terminal_received < terminal_observed:
        raise ExternalCloseReinterpretationError("FP10_TEMPORAL_ORDER_INVALID", "provider receipt precedes observation")
    if evaluated < provider_received or evaluated < terminal_received:
        raise ExternalCloseReinterpretationError("FP10_TEMPORAL_ORDER_INVALID", "evaluation predates required evidence")

    quantity = _quantity(evidence.get("normalized_actual_quantity"), "normalized_actual_quantity")
    if evidence.get("provider_position_currentness_status") not in {CURRENT, STALE, UNKNOWN}:
        raise ExternalCloseReinterpretationError("FP10_CURRENTNESS_INVALID", "provider Position currentness unsupported")
    if evidence.get("terminal_protection_status") not in _FP10_TERMINAL_PROTECTION:
        raise ExternalCloseReinterpretationError("FP10_PROTECTION_STATUS_INVALID", "terminal protection status unsupported")
    if evidence.get("exposure_change_origin_classification") not in _FP10_ORIGINS:
        raise ExternalCloseReinterpretationError("FP10_ORIGIN_INVALID", "exposure origin unsupported")
    if evidence.get("convergence_state") not in _FP10_STATES:
        raise ExternalCloseReinterpretationError("FP10_STATE_INVALID", "convergence state unsupported")
    revision = evidence.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise ExternalCloseReinterpretationError("FP10_LIFECYCLE_REVISION_INVALID", "lifecycle_revision invalid")

    _validate_sorted_refs(
        evidence.get("execution_evidence"),
        fields=("evidence_class", "owner", "evidence_ref", "evidence_hash"),
        label="execution_evidence",
    )
    _validate_sorted_refs(
        evidence.get("fp04_ownership_evidence"),
        fields=("provider_object_class", "provider_object_ref", "ownership_evidence_ref"),
        label="fp04_ownership_evidence",
    )
    if evidence["execution_evidence_set_hash"] != _sha256_json(evidence["execution_evidence"]):
        raise ExternalCloseReinterpretationError("FP10_EXECUTION_SET_HASH_MISMATCH", "execution evidence set hash invalid")
    if evidence["fp04_evidence_set_hash"] != _sha256_json(evidence["fp04_ownership_evidence"]):
        raise ExternalCloseReinterpretationError("FP10_FP04_SET_HASH_MISMATCH", "FP-04 evidence set hash invalid")

    reason_codes = evidence.get("reason_codes")
    dispositions = evidence.get("required_dispositions")
    if not isinstance(reason_codes, list) or not reason_codes:
        raise ExternalCloseReinterpretationError("FP10_REASONS_INVALID", "reason_codes must be non-empty")
    if any(code not in _FP10_REASON_INDEX for code in reason_codes):
        raise ExternalCloseReinterpretationError("FP10_REASON_UNKNOWN", "unknown FP-10 reason code")
    expected_reasons = sorted(set(reason_codes), key=_FP10_REASON_INDEX.__getitem__)
    if reason_codes != expected_reasons:
        raise ExternalCloseReinterpretationError("FP10_REASON_ORDER_INVALID", "FP-10 reasons must use contract order")
    if not isinstance(dispositions, list) or not dispositions:
        raise ExternalCloseReinterpretationError("FP10_DISPOSITIONS_INVALID", "required_dispositions must be non-empty")

    state = evidence["convergence_state"]
    if quantity > 0 and state in {
        LIFECYCLE_CLOSE_ELIGIBLE,
        FLAT_PROVIDER_TRUTH_PROVEN,
        FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED,
        FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED,
    }:
        raise ExternalCloseReinterpretationError("FP10_FALSE_FLAT", "positive authoritative exposure cannot be flat/close eligible")
    if state == RESIDUAL_UNREPRESENTABLE_NOT_FLAT and quantity <= 0:
        raise ExternalCloseReinterpretationError("FP10_RESIDUAL_STATE_INVALID", "unrepresentable residual requires positive exposure")
    if state == LIFECYCLE_CLOSE_ELIGIBLE:
        if quantity != 0:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exact zero exposure")
        if evidence["provider_position_currentness_status"] != CURRENT:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires current provider truth")
        if evidence["normalized_position_reconciliation_status"] != CONSISTENT:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires CONSISTENT Position")
        if evidence["terminal_protection_status"] != TERMINAL_PROTECTION_CLEAR:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires terminal protection clear")
        if dispositions != [NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE]:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exclusive no-action disposition")
        if reason_codes != [LIFECYCLE_CLOSE_ELIGIBLE_PROVEN]:
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exact success reason")
        if any(item.get("currentness_status") != CURRENT for item in evidence["execution_evidence"]):
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "execution evidence must be current")
        if any(item.get("position_compatibility_status") != "COMPATIBLE" for item in evidence["execution_evidence"]):
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "execution evidence must be compatible")
        if any(item.get("ownership_currentness_status") != CURRENT for item in evidence["fp04_ownership_evidence"]):
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "FP-04 evidence must be current")
        if any(
            item.get("ownership_classification") in {CONFLICTING_OWNERSHIP_EVIDENCE, UNKNOWN}
            or item.get("ownership_reconciliation_status") == UNKNOWN
            for item in evidence["fp04_ownership_evidence"]
        ):
            raise ExternalCloseReinterpretationError("FP10_FALSE_CLOSE_ELIGIBLE", "ownership evidence conflicts with close eligibility")


def _fp04_rows(evidence_set: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for evidence in evidence_set:
        validate_external_provider_ownership_evidence(evidence)
        rows.append(
            {
                "provider_object_class": evidence["provider_object_class"],
                "provider_object_ref": evidence["provider_object_ref"],
                "provider_snapshot_hash": evidence["provider_snapshot_hash"],
                "ownership_evidence_ref": evidence["ownership_evidence_id"],
                "ownership_evidence_hash": _sha256_json(evidence),
                "ownership_classification": evidence["ownership_classification"],
                "ownership_reconciliation_status": evidence["reconciliation_status"],
                "ownership_currentness_status": CURRENT,
            }
        )
    return sorted(rows, key=lambda row: (row["provider_object_class"], row["provider_object_ref"], row["ownership_evidence_ref"]))


def external_close_convergence_evidence_is_current(
    evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
) -> bool:
    """Return true only when immutable FP-10 evidence still matches all material current authority."""

    try:
        validate_external_manual_close_convergence_evidence(evidence)
    except ExternalCloseReinterpretationError:
        return False

    position = authority.normalized_position
    projection = authority.lifecycle_projection
    binding = authority.lifecycle_execution_binding
    if position is None or projection is None or binding is None:
        return False
    try:
        projection_facts = validate_position_lifecycle_projection(projection)
        validate_position_lifecycle_execution_evidence_binding(binding, projection)
        current_fp04_rows = _fp04_rows(authority.fp04_ownership_evidence)
    except (ExternalCloseReinterpretationError, LifecycleProjectionError, LifecycleExecutionBindingError):
        return False

    if evidence.get("position_id") != position.get("position_id"):
        return False
    if evidence.get("canonical_symbol") != position.get("symbol"):
        return False
    if evidence.get("normalized_position_ref") != authority.normalized_position_ref:
        return False
    try:
        if evidence.get("normalized_position_hash") != _sha256_json(position):
            return False
    except ExternalCloseReinterpretationError:
        return False
    if evidence.get("normalized_position_broker_state_observed_at") != position.get("broker_state_observed_at"):
        return False
    if evidence.get("normalized_position_reconciliation_status") != position.get("reconciliation_status"):
        return False
    if Decimal(evidence["normalized_actual_quantity"]) != Decimal(str(position.get("actual_quantity"))):
        return False
    for evidence_field, position_field in (
        ("normalized_quantity_profile_version", "quantity_profile_version"),
        ("normalized_quantity_unit", "quantity_unit"),
        ("normalized_quantity_asset", "quantity_asset"),
    ):
        if evidence.get(evidence_field) != position.get(position_field):
            return False

    exact_authority_pairs = (
        ("provider_identity_ref", authority.provider_identity_ref),
        ("provider_identity_hash", authority.provider_identity_hash),
        ("provider_instrument_ref", authority.provider_instrument_ref),
        ("provider_position_snapshot_ref", authority.provider_position_snapshot_ref),
        ("provider_position_snapshot_hash", authority.provider_position_snapshot_hash),
        ("provider_position_observation_generation_id", authority.provider_position_observation_generation_id),
        ("provider_position_observed_at", authority.provider_position_observed_at),
        ("provider_position_received_at", authority.provider_position_received_at),
        ("execution_evidence_set_hash", authority.execution_evidence_set_hash),
        ("fp05_close_residual_sizing_ref", authority.fp05_close_residual_sizing_ref),
        ("fp05_close_residual_sizing_hash", authority.fp05_close_residual_sizing_hash),
        ("fp05_residual_state", authority.fp05_residual_state),
        ("terminal_protection_observation_ref", authority.terminal_protection_observation_ref),
        ("terminal_protection_observation_hash", authority.terminal_protection_observation_hash),
        ("terminal_protection_observed_at", authority.terminal_protection_observed_at),
        ("terminal_protection_received_at", authority.terminal_protection_received_at),
        ("terminal_protection_status", authority.terminal_protection_status),
        ("current_project_revision", authority.current_project_revision),
        ("runtime_preflight_ref", authority.runtime_preflight_ref),
        ("runtime_process_instance_id", authority.runtime_process_instance_id),
        ("runtime_process_start_generation_id", authority.runtime_process_start_generation_id),
        ("runtime_config_generation_id", authority.runtime_config_generation_id),
    )
    if any(evidence.get(field) != expected for field, expected in exact_authority_pairs):
        return False

    if evidence.get("fp04_ownership_evidence") != current_fp04_rows:
        return False
    if evidence.get("fp04_evidence_set_hash") != _sha256_json(current_fp04_rows):
        return False

    if evidence.get("lifecycle_projection_ref") != authority.lifecycle_projection_ref:
        return False
    if evidence.get("lifecycle_projection_hash") != _sha256_json(projection):
        return False
    if evidence.get("lifecycle_projection_id") != projection_facts["projection_id"]:
        return False
    if evidence.get("lifecycle_revision") != projection_facts["revision"]:
        return False
    if evidence.get("lifecycle_state") != projection.get("lifecycle_state"):
        return False
    if evidence.get("lifecycle_execution_binding_ref") != authority.lifecycle_execution_binding_ref:
        return False
    if evidence.get("lifecycle_execution_binding_hash") != _sha256_json(binding):
        return False
    if evidence.get("lifecycle_execution_snapshot_hash") != binding.get("execution_snapshot_hash"):
        return False
    return True


def _decision_id(material: Mapping[str, Any]) -> str:
    return "e5extclose_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _state_unknown(current_state: PositionLifecycleState) -> tuple[PositionEvent | None, PositionLifecycleState]:
    if current_state == PositionLifecycleState.RECONCILIATION_REQUIRED:
        return None, current_state
    try:
        return PositionEvent.STATE_UNKNOWN, transition(current_state, PositionEvent.STATE_UNKNOWN)
    except UnsafeTransitionError:
        # CLOSED may be reopened to reconciliation by STATE_UNKNOWN; states not
        # admitting STATE_UNKNOWN remain fail-closed without manufacturing a transition.
        return None, current_state


def interpret_external_close_convergence(
    evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
) -> ExternalCloseReinterpretationDecision:
    """Interpret accepted current FP-04/FP-10 evidence into existing E5 lifecycle authority.

    The consumer never creates provider truth, execution lineage, TradeResult
    objects, cleanup targets, or provider mutation authority.
    """

    validate_external_manual_close_convergence_evidence(evidence)
    projection = authority.lifecycle_projection
    if projection is None:
        raise ExternalCloseReinterpretationError("CURRENT_LIFECYCLE_MISSING", "current lifecycle projection is required")
    try:
        projection_facts = validate_position_lifecycle_projection(projection)
    except LifecycleProjectionError as exc:
        raise ExternalCloseReinterpretationError("CURRENT_LIFECYCLE_INVALID", "current lifecycle projection invalid") from exc
    current_state = PositionLifecycleState(projection["lifecycle_state"])
    current = external_close_convergence_evidence_is_current(evidence, authority)
    trade_result_incomplete = TRADE_RESULT_EVIDENCE_INCOMPLETE in evidence.get("reason_codes", [])

    decision = DECISION_HOLD_SAFE
    event: PositionEvent | None = None
    next_state = current_state
    reasons: list[str] = []
    close_eligible = False

    if not current:
        event, next_state = _state_unknown(current_state)
        decision = DECISION_RECONCILE
        reasons = ["E5_EXTERNAL_CLOSE_EVIDENCE_STALE_OR_MISMATCHED"]
    else:
        state = evidence["convergence_state"]
        quantity = Decimal(evidence["normalized_actual_quantity"])

        if state == LIFECYCLE_CLOSE_ELIGIBLE:
            if quantity != 0 or evidence["normalized_position_reconciliation_status"] != CONSISTENT:
                event, next_state = _state_unknown(current_state)
                decision = DECISION_RECONCILE
                reasons = ["E5_FALSE_CLOSE_ELIGIBILITY_REJECTED"]
            elif current_state == PositionLifecycleState.RECONCILIATION_REQUIRED:
                event = PositionEvent.RECONCILED_FLAT
                next_state = transition(current_state, event)
                decision = DECISION_CLOSE
                close_eligible = True
                reasons = ["E5_RECONCILED_FLAT_FROM_CURRENT_FP10"]
            elif current_state in {
                PositionLifecycleState.OPEN_PROTECTED,
                PositionLifecycleState.PROFIT_PROTECTED,
                PositionLifecycleState.EXIT_REQUESTED,
                PositionLifecycleState.EMERGENCY,
            }:
                event = PositionEvent.POSITION_CLOSED
                next_state = transition(current_state, event)
                decision = DECISION_CLOSE
                close_eligible = True
                reasons = ["E5_POSITION_CLOSED_FROM_CURRENT_FP10"]
            elif current_state == PositionLifecycleState.CLOSED:
                decision = DECISION_REATTEST
                next_state = current_state
                close_eligible = True
                reasons = ["E5_CURRENT_FLAT_REATTESTED"]
            else:
                event, next_state = _state_unknown(current_state)
                decision = DECISION_RECONCILE
                reasons = ["E5_CLOSE_ELIGIBLE_REQUIRES_RECONCILIATION_PATH"]

        elif state in {EXPOSURE_STILL_OPEN, EXPOSURE_REDUCED_NOT_FLAT}:
            if quantity <= 0:
                event, next_state = _state_unknown(current_state)
                decision = DECISION_RECONCILE
                reasons = ["E5_NONFLAT_STATE_WITHOUT_POSITIVE_EXPOSURE"]
            elif evidence["exposure_change_origin_classification"] in {
                PRIOR_GENERATION_PROJECT,
                EXTERNAL_MANUAL,
                MIXED_OR_UNKNOWN,
            }:
                decision = DECISION_REATTEST
                reasons = ["E5_EXTERNAL_OR_MANUAL_POSITIVE_EXPOSURE_REINTERPRETED"]
            else:
                decision = DECISION_RETAIN_OPEN
                reasons = ["E5_AUTHORITATIVE_POSITIVE_EXPOSURE_RETAINS_OPEN_STATE"]

        elif state == RESIDUAL_UNREPRESENTABLE_NOT_FLAT:
            if quantity <= 0:
                event, next_state = _state_unknown(current_state)
                decision = DECISION_RECONCILE
                reasons = ["E5_RESIDUAL_UNREPRESENTABLE_WITHOUT_POSITIVE_EXPOSURE"]
            else:
                decision = DECISION_HOLD_SAFE
                reasons = ["E5_POSITIVE_UNREPRESENTABLE_RESIDUAL_FAIL_CLOSED"]

        elif state == EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED:
            if quantity == 0:
                event, next_state = _state_unknown(current_state)
                decision = DECISION_RECONCILE
                reasons = ["E5_EXTERNAL_FLAT_REQUIRES_TWO_STEP_REINTERPRETATION"]
            else:
                decision = DECISION_REATTEST
                reasons = ["E5_EXTERNAL_POSITIVE_EXPOSURE_REINTERPRETATION_REQUIRED"]

        elif state in {
            FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED,
            FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED,
            OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED,
            CONVERGENCE_EVIDENCE_STALE,
            CONVERGENCE_UNKNOWN,
        }:
            event, next_state = _state_unknown(current_state)
            decision = DECISION_RECONCILE
            if state == FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED:
                reasons = ["E5_FLAT_EXECUTION_FILL_RECONCILIATION_REQUIRED"]
            elif state == FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED:
                reasons = ["E5_FLAT_TERMINAL_PROTECTION_NOT_CONVERGED"]
            elif state == OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED:
                reasons = ["E5_FP04_OWNERSHIP_RECONCILIATION_REQUIRED"]
            else:
                reasons = ["E5_CLOSE_CONVERGENCE_NOT_CURRENT"]

        elif state == FLAT_PROVIDER_TRUTH_PROVEN:
            event, next_state = _state_unknown(current_state)
            decision = DECISION_RECONCILE
            reasons = ["E5_FLAT_PROVIDER_TRUTH_NOT_YET_CLOSE_ELIGIBLE"]
        else:
            event, next_state = _state_unknown(current_state)
            decision = DECISION_RECONCILE
            reasons = ["E5_UNSUPPORTED_CLOSE_CONVERGENCE_STATE"]

    material = {
        "close_convergence_evidence_id": evidence["close_convergence_evidence_id"],
        "position_id": evidence["position_id"],
        "lifecycle_projection_id": projection_facts["projection_id"],
        "lifecycle_revision": projection_facts["revision"],
        "lifecycle_execution_binding_id": None
        if authority.lifecycle_execution_binding is None
        else authority.lifecycle_execution_binding.get("lifecycle_execution_binding_id"),
        "evidence_current": current,
        "decision": decision,
        "event": None if event is None else event.value,
        "next_state": next_state.value,
        "reason_codes": reasons,
        "close_eligible": close_eligible,
        "trade_result_evidence_incomplete": trade_result_incomplete,
    }
    decision_id = _decision_id(material)
    if _DECISION_ID_RE.fullmatch(decision_id) is None:
        raise AssertionError("unreachable decision identity")
    return ExternalCloseReinterpretationDecision(
        decision_id=decision_id,
        decision=decision,
        event=event,
        next_state=next_state,
        reason_codes=tuple(reasons),
        close_eligible=close_eligible,
        trade_result_evidence_incomplete=trade_result_incomplete,
        evidence_current=current,
    )
