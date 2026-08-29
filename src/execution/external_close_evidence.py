from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

from src.position.external_close_policy import (
    validate_external_manual_close_convergence_evidence,
    validate_external_provider_ownership_evidence,
)
from src.position.external_close_reinterpretation import ExternalCloseReinterpretationError
from src.position.lifecycle_execution_binding import (
    LifecycleExecutionBindingError,
    validate_position_lifecycle_execution_evidence_binding,
)
from src.position.lifecycle_projection import (
    LifecycleProjectionError,
    validate_position_lifecycle_projection,
)

SCHEMA_VERSION = "contracts-v0.1"
FP04_PROFILE_VERSION = "external-provider-object-ownership-reconciliation-v0.1"
FP10_PROFILE_VERSION = "external-manual-close-lifecycle-convergence-v0.1"

CURRENT = "CURRENT"
STALE = "STALE"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"
CONSISTENT = "CONSISTENT"

LINEAGE_CURRENT_GENERATION = "CURRENT_GENERATION"
LINEAGE_PRIOR_GENERATION = "PRIOR_GENERATION"
LINEAGE_EXTERNAL = "EXTERNAL"
LINEAGE_CONFLICT = "CONFLICT"
LINEAGE_UNKNOWN = "UNKNOWN"

PROVIDER_BINDING_EXACT = "EXACT"
PROVIDER_BINDING_MISMATCH = "MISMATCH"
PROVIDER_BINDING_UNKNOWN = "UNKNOWN"

MULTIPLICITY_SINGLE = "SINGLE"
MULTIPLICITY_MULTIPLE = "MULTIPLE"
MULTIPLICITY_UNKNOWN = "UNKNOWN"

KNOWN_OWNED_CURRENT_GENERATION = "KNOWN_OWNED_CURRENT_GENERATION"
KNOWN_OWNED_PRIOR_GENERATION = "KNOWN_OWNED_PRIOR_GENERATION"
EXTERNAL_UNTRACKED = "EXTERNAL_UNTRACKED"
CONFLICTING_OWNERSHIP_EVIDENCE = "CONFLICTING_OWNERSHIP_EVIDENCE"
OWNERSHIP_UNKNOWN = "UNKNOWN"

CURRENT_KNOWN_OWNED = "CURRENT_KNOWN_OWNED"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
CONVERGENCE_REQUIRED = "CONVERGENCE_REQUIRED"

NO_ACTION_CURRENT_KNOWN_OWNED = "NO_ACTION_CURRENT_KNOWN_OWNED"
NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE = "NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"

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
FP05_NOT_APPLICABLE = "NOT_APPLICABLE"

CURRENT_GENERATION_PROJECT = "CURRENT_GENERATION_PROJECT"
PRIOR_GENERATION_PROJECT = "PRIOR_GENERATION_PROJECT"
EXTERNAL_MANUAL = "EXTERNAL_MANUAL"
MIXED_OR_UNKNOWN = "MIXED_OR_UNKNOWN"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FP04_ID_RE = re.compile(r"^extownrec_[0-9a-f]{64}$")
_FP10_ID_RE = re.compile(r"^extcloseconv_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

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
_LINEAGE_OWNERS = frozenset({"E4", "E5", "E6"})
_LINEAGE_ROLES = frozenset(
    {
        "APPROVED_TRADE_PLAN",
        "POSITION_ACTION",
        "ORDER_REQUEST",
        "CLIENT_ORDER_IDENTITY",
        "ORDER_RESULT",
        "FILL",
        "POSITION",
        "LIFECYCLE_PROJECTION",
        "LIFECYCLE_EXECUTION_BINDING",
        "OTHER_ACCEPTED_LINEAGE",
    }
)
_CLAIM_STATUSES = frozenset(
    {"CLAIMS_OWNERSHIP", "SUPPORTS_LINEAGE", "CONTRADICTS_LINEAGE", "UNKNOWN"}
)
_REGISTRY_CURRENTNESS = frozenset({CURRENT, STALE, CONFLICT, UNKNOWN})

_FP04_REASON_ORDER = (
    "EXTERNAL_OWNERSHIP_PROFILE_UNSUPPORTED",
    "PROVIDER_OBJECT_CLASS_UNKNOWN",
    "PROVIDER_IDENTITY_UNBOUND",
    "PROVIDER_SNAPSHOT_UNBOUND",
    "PROVIDER_OBJECT_LINEAGE_NOT_PROVEN",
    "PROVIDER_OBJECT_PRIOR_RUNTIME_GENERATION",
    "EXTERNAL_PROVIDER_OBJECT_UNTRACKED",
    "EXPLICIT_ADOPTION_POLICY_REQUIRED",
    "OWNERSHIP_MANUAL_REVIEW_REQUIRED",
    "LOCAL_LINEAGE_OWNERSHIP_CONFLICT",
    "PROVIDER_OBJECT_MULTIPLICITY_CONFLICT",
    "LINEAGE_PROVIDER_IDENTIFIER_MISMATCH",
    "LINEAGE_PROVIDER_SNAPSHOT_MISMATCH",
    "PROVIDER_OBJECT_INSTRUMENT_MISMATCH",
    "PROVIDER_OBJECT_SIDE_MISMATCH",
    "PROVIDER_OBJECT_QUANTITY_MISMATCH",
    "PROVIDER_OBSERVATION_NEWER_THAN_OWNERSHIP_EVIDENCE",
    "LOCAL_EVIDENCE_NEWER_OR_CONTRADICTORY",
    "OWNERSHIP_EVIDENCE_STALE",
    "ADOPTION_EVIDENCE_MISSING_OR_INVALID",
    "ADOPTION_EVIDENCE_STALE_OR_MISMATCHED",
    "ADOPTION_EVIDENCE_ALREADY_CONSUMED",
    "PROTECTION_REGISTRY_CONVERGENCE_REQUIRED",
    "LIFECYCLE_REINTERPRETATION_REQUIRED",
    "TERMINAL_FLAT_CONVERGENCE_PENDING",
    "OWNERSHIP_RECONCILIATION_INCOMPLETE",
    "CURRENT_GENERATION_OWNERSHIP_PROVEN",
)
_FP04_REASON_INDEX = {value: index for index, value in enumerate(_FP04_REASON_ORDER)}

_FP04_DISPOSITIONS = frozenset(
    {
        "NO_ACTION_CURRENT_KNOWN_OWNED",
        "FRESH_RECONCILIATION_REQUIRED",
        "BLOCK_NEW_EXPOSURE",
        "BLOCK_PROTECTION_MUTATION",
        "BLOCK_CLOSE_EXIT_MUTATION",
        "ADOPTION_POLICY_EVALUATION_REQUIRED",
        "DETACH_IGNORE_POLICY_EVALUATION_REQUIRED",
        "MANUAL_REVIEW_REQUIRED",
        "LIFECYCLE_REINTERPRETATION_REQUIRED",
        "PROTECTION_REGISTRY_CONVERGENCE_REQUIRED",
        "TERMINAL_FLAT_CONVERGENCE_PENDING",
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
_FP05_STATES = frozenset(
    {
        "FULLY_REDUCIBLE",
        "PARTIALLY_REDUCIBLE",
        RESIDUAL_NONZERO_REPRESENTABLE,
        RESIDUAL_NONZERO_UNREPRESENTABLE,
        "EXPOSURE_ALREADY_FLAT",
        "REDUCIBLE_EXPOSURE_UNKNOWN",
        "METADATA_STALE_OR_UNKNOWN",
        "RECONCILIATION_REQUIRED",
        "CLOSE_CAPABILITY_UNPROVEN",
        FP05_NOT_APPLICABLE,
    }
)
_FP10_EXECUTION_CLASSES = frozenset(
    {
        "ORDER_REQUEST",
        "ORDER_RESULT_SET",
        "FILL_SET",
        "AMBIGUOUS_OUTCOME_RECONCILIATION",
        "EXTERNAL_EXECUTION_OBSERVATION",
        "OTHER_ACCEPTED_CLOSE_EVIDENCE",
    }
)
_FP10_EXECUTION_OWNERS = frozenset({"E4", "E5"})
_FP10_EXECUTION_CURRENTNESS = frozenset({CURRENT, STALE, CONFLICT, UNKNOWN})
_FP10_POSITION_COMPATIBILITY = frozenset({"COMPATIBLE", "CONTRADICTS", UNKNOWN})
_FP10_LINEAGE_ORIGINS = frozenset(
    {CURRENT_GENERATION_PROJECT, PRIOR_GENERATION_PROJECT, EXTERNAL_MANUAL, UNKNOWN}
)
_FP10_FP04_CURRENTNESS = frozenset({CURRENT, STALE, CONFLICT, UNKNOWN})

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
    "TRADE_RESULT_EVIDENCE_INCOMPLETE",
    "TERMINAL_PROTECTION_CLEAR",
    "LIFECYCLE_CLOSE_ELIGIBLE_PROVEN",
)
_FP10_REASON_INDEX = {value: index for index, value in enumerate(_FP10_REASON_ORDER)}
_FP10_DISPOSITIONS = frozenset(
    {
        "NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE",
        "FRESH_PROVIDER_POSITION_RECONCILIATION_REQUIRED",
        "EXECUTION_FILL_RECONCILIATION_REQUIRED",
        "OWNERSHIP_RECONCILIATION_REQUIRED",
        "FP05_RESIDUAL_REEVALUATION_REQUIRED",
        "TERMINAL_PROTECTION_CONVERGENCE_REQUIRED",
        "E5_LIFECYCLE_REINTERPRETATION_REQUIRED",
        "E6_CURRENTNESS_REVALIDATION_REQUIRED",
        "MANUAL_REVIEW_REQUIRED",
        "BLOCK_NEW_EXPOSURE",
        "BLOCK_CLOSE_RETRY_MUTATION",
        "BLOCK_UNCERTAIN_PROTECTION_CLEANUP",
        "TRADE_RESULT_EVIDENCE_INCOMPLETE",
    }
)

_LINEAGE_FIELDS = frozenset(
    {
        "owner",
        "evidence_class",
        "evidence_ref",
        "evidence_hash",
        "evidence_generation_id",
        "observed_or_created_at",
        "lineage_role",
        "claim_status",
    }
)
_REGISTRY_FIELDS = frozenset(
    {
        "owner",
        "evidence_class",
        "evidence_ref",
        "evidence_hash",
        "evidence_generation_id",
        "observed_at",
        "currentness_status",
    }
)
_EXECUTION_FIELDS = frozenset(
    {
        "owner",
        "evidence_class",
        "evidence_ref",
        "evidence_hash",
        "evidence_generation_id",
        "latest_observed_at",
        "currentness_status",
        "position_compatibility_status",
        "lineage_origin",
    }
)


class ExternalCloseEvidenceError(ValueError):
    """Fail-closed E4 FP-04/FP-10 evidence production error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProviderObjectObservation:
    provider_object_class: str
    provider_identity_ref: str
    provider_identity: Mapping[str, Any]
    canonical_symbol: str
    provider_instrument_ref: str
    provider_object_ref: str
    provider_snapshot_ref: str
    provider_snapshot: Mapping[str, Any]
    provider_observation_generation_id: str
    provider_observed_at: str | datetime
    provider_received_at: str | datetime


@dataclass(frozen=True)
class OwnershipEvaluationContext:
    current_project_revision: str
    local_lineage_evidence: Sequence[Mapping[str, Any]]
    local_registry_evidence: Sequence[Mapping[str, Any]]
    lineage_generation_status: str
    provider_binding_status: str
    multiplicity_status: str
    evaluated_at: str | datetime
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None
    adoption_decision_ref: str | None = None


@dataclass(frozen=True)
class ProviderPositionObservation:
    provider_identity_ref: str
    provider_identity: Mapping[str, Any]
    provider_instrument_ref: str
    provider_position_snapshot_ref: str
    provider_position_snapshot: Mapping[str, Any]
    provider_position_observation_generation_id: str
    provider_position_observed_at: str | datetime
    provider_position_received_at: str | datetime
    provider_position_currentness_status: str
    position_id: str
    canonical_symbol: str
    position_side: str
    normalized_actual_quantity: str | Decimal


@dataclass(frozen=True)
class FP04EvidenceDependency:
    evidence: Mapping[str, Any]
    currentness_status: str = CURRENT


@dataclass(frozen=True)
class TerminalProtectionObservation:
    observation_ref: str
    observation_payload: Mapping[str, Any]
    observed_at: str | datetime
    received_at: str | datetime
    status: str


@dataclass(frozen=True)
class CloseConvergenceAssemblyInput:
    provider_position: ProviderPositionObservation
    normalized_position_ref: str
    normalized_position: Mapping[str, Any]
    execution_evidence: Sequence[Mapping[str, Any]]
    fp04_dependencies: Sequence[FP04EvidenceDependency]
    terminal_protection: TerminalProtectionObservation
    lifecycle_projection_ref: str
    lifecycle_projection: Mapping[str, Any]
    lifecycle_execution_binding_ref: str
    lifecycle_execution_binding: Mapping[str, Any]
    current_project_revision: str
    exposure_change_origin_classification: str
    convergence_state: str
    required_dispositions: Sequence[str]
    reason_codes: Sequence[str]
    evaluated_at: str | datetime
    fp05_close_residual_sizing_ref: str | None = None
    fp05_close_residual_sizing_hash: str | None = None
    fp05_residual_state: str = FP05_NOT_APPLICABLE
    fp11_prior_registry_evidence_ref: str | None = None
    fp11_prior_registry_evidence_hash: str | None = None
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ExternalCloseEvidenceError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        return _utc_text(value, "datetime")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ExternalCloseEvidenceError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ExternalCloseEvidenceError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ExternalCloseEvidenceError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical value type: {type(value).__name__}",
    )


def canonical_evidence_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_evidence_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_evidence_json(value).encode("utf-8")).hexdigest()


def _stable_id(prefix: str, payload: Mapping[str, Any], id_field: str) -> str:
    material = dict(payload)
    material.pop(id_field, None)
    return prefix + hashlib.sha256(canonical_evidence_json(material).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExternalCloseEvidenceError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise ExternalCloseEvidenceError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _utc_text(value: str | datetime, field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ExternalCloseEvidenceError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExternalCloseEvidenceError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExternalCloseEvidenceError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalCloseEvidenceError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_dt(value: str | datetime, field: str) -> datetime:
    text = _utc_text(value, field)
    return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(timezone.utc)


def _quantity_text(value: Any, field: str) -> str:
    if isinstance(value, Decimal):
        parsed = value
        text = format(value, "f")
    elif isinstance(value, str) and _DECIMAL_RE.fullmatch(value) is not None:
        text = value
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ExternalCloseEvidenceError("INVALID_QUANTITY", f"{field} is invalid") from exc
    else:
        raise ExternalCloseEvidenceError("INVALID_QUANTITY", f"{field} must be a canonical decimal string")
    if not parsed.is_finite() or parsed < 0:
        raise ExternalCloseEvidenceError("INVALID_QUANTITY", f"{field} must be finite and non-negative")
    return text


def _optional_ref_hash(ref: Any, digest: Any, label: str) -> tuple[str | None, str | None]:
    if ref is None and digest is None:
        return None, None
    if ref is None or digest is None:
        raise ExternalCloseEvidenceError("REFERENCE_HASH_PAIR_INCOMPLETE", f"{label} ref/hash must both be set or null")
    return _text(ref, f"{label}_ref"), _hash(digest, f"{label}_hash")


def _sorted_reasons(values: Sequence[str], *, fp10: bool = False) -> list[str]:
    order = _FP10_REASON_INDEX if fp10 else _FP04_REASON_INDEX
    result = [_text(value, "reason_code") for value in values]
    if any(value not in order for value in result):
        raise ExternalCloseEvidenceError("REASON_UNKNOWN", "reason code is outside the accepted profile vocabulary")
    return sorted(set(result), key=order.__getitem__)


def _sorted_dispositions(values: Sequence[str], *, fp10: bool = False) -> list[str]:
    allowed = _FP10_DISPOSITIONS if fp10 else _FP04_DISPOSITIONS
    result = [_text(value, "required_disposition") for value in values]
    if not result or any(value not in allowed for value in result):
        raise ExternalCloseEvidenceError("DISPOSITION_UNKNOWN", "disposition is outside the accepted profile vocabulary")
    return sorted(set(result))


def _normalize_lineage(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in items:
        item = _canonicalize(raw)
        if not isinstance(item, dict) or set(item) != _LINEAGE_FIELDS:
            raise ExternalCloseEvidenceError("FP04_LINEAGE_FIELDS_INVALID", "local lineage entry fields mismatch")
        if item["owner"] not in _LINEAGE_OWNERS:
            raise ExternalCloseEvidenceError("FP04_LINEAGE_OWNER_INVALID", "local lineage owner unsupported")
        if item["lineage_role"] not in _LINEAGE_ROLES:
            raise ExternalCloseEvidenceError("FP04_LINEAGE_ROLE_INVALID", "local lineage role unsupported")
        if item["claim_status"] not in _CLAIM_STATUSES:
            raise ExternalCloseEvidenceError("FP04_CLAIM_STATUS_INVALID", "local lineage claim status unsupported")
        for field in ("evidence_class", "evidence_ref", "evidence_generation_id"):
            _text(item[field], f"local_lineage_evidence.{field}")
        _hash(item["evidence_hash"], "local_lineage_evidence.evidence_hash")
        item["observed_or_created_at"] = _utc_text(
            item["observed_or_created_at"],
            "local_lineage_evidence.observed_or_created_at",
        )
        normalized.append(item)
    normalized.sort(key=lambda item: (item["owner"], item["evidence_class"], item["evidence_ref"]))
    keys = [(item["owner"], item["evidence_class"], item["evidence_ref"]) for item in normalized]
    if len(keys) != len(set(keys)):
        raise ExternalCloseEvidenceError("FP04_LINEAGE_DUPLICATE", "local lineage keys must be unique")
    return normalized


def _normalize_registry(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in items:
        item = _canonicalize(raw)
        if not isinstance(item, dict) or set(item) != _REGISTRY_FIELDS:
            raise ExternalCloseEvidenceError("FP04_REGISTRY_FIELDS_INVALID", "local registry entry fields mismatch")
        if item["owner"] not in _LINEAGE_OWNERS:
            raise ExternalCloseEvidenceError("FP04_REGISTRY_OWNER_INVALID", "registry owner unsupported")
        if item["currentness_status"] not in _REGISTRY_CURRENTNESS:
            raise ExternalCloseEvidenceError("FP04_REGISTRY_CURRENTNESS_INVALID", "registry currentness unsupported")
        for field in ("evidence_class", "evidence_ref", "evidence_generation_id"):
            _text(item[field], f"local_registry_evidence.{field}")
        _hash(item["evidence_hash"], "local_registry_evidence.evidence_hash")
        item["observed_at"] = _utc_text(item["observed_at"], "local_registry_evidence.observed_at")
        normalized.append(item)
    normalized.sort(key=lambda item: (item["owner"], item["evidence_class"], item["evidence_ref"]))
    keys = [(item["owner"], item["evidence_class"], item["evidence_ref"]) for item in normalized]
    if len(keys) != len(set(keys)):
        raise ExternalCloseEvidenceError("FP04_REGISTRY_DUPLICATE", "local registry keys must be unique")
    return normalized


def _fp04_blocking_dispositions(provider_object_class: str, *, fresh_reconcile: bool) -> set[str]:
    dispositions = {"BLOCK_NEW_EXPOSURE", "LIFECYCLE_REINTERPRETATION_REQUIRED"}
    if fresh_reconcile:
        dispositions.add("FRESH_RECONCILIATION_REQUIRED")
    if provider_object_class in {
        "POSITION_EXPOSURE",
        "OPEN_ORDER",
        "TERMINAL_ORDER",
        "FILL_EXECUTION",
        "UNCLASSIFIED_PROVIDER_OBJECT",
    }:
        dispositions.add("BLOCK_CLOSE_EXIT_MUTATION")
    if provider_object_class == "ACTIVE_PROTECTION":
        dispositions.update(
            {
                "BLOCK_PROTECTION_MUTATION",
                "PROTECTION_REGISTRY_CONVERGENCE_REQUIRED",
            }
        )
    return dispositions


def _derive_fp04_outcome(
    provider_object_class: str,
    lineage: Sequence[Mapping[str, Any]],
    registry: Sequence[Mapping[str, Any]],
    context: OwnershipEvaluationContext,
) -> tuple[str, str, list[str], list[str]]:
    if context.lineage_generation_status not in {
        LINEAGE_CURRENT_GENERATION,
        LINEAGE_PRIOR_GENERATION,
        LINEAGE_EXTERNAL,
        LINEAGE_CONFLICT,
        LINEAGE_UNKNOWN,
    }:
        raise ExternalCloseEvidenceError("FP04_LINEAGE_GENERATION_STATUS_INVALID", "lineage generation status unsupported")
    if context.provider_binding_status not in {
        PROVIDER_BINDING_EXACT,
        PROVIDER_BINDING_MISMATCH,
        PROVIDER_BINDING_UNKNOWN,
    }:
        raise ExternalCloseEvidenceError("FP04_PROVIDER_BINDING_STATUS_INVALID", "provider binding status unsupported")
    if context.multiplicity_status not in {
        MULTIPLICITY_SINGLE,
        MULTIPLICITY_MULTIPLE,
        MULTIPLICITY_UNKNOWN,
    }:
        raise ExternalCloseEvidenceError("FP04_MULTIPLICITY_STATUS_INVALID", "multiplicity status unsupported")

    claim_statuses = {item["claim_status"] for item in lineage}
    registry_statuses = {item["currentness_status"] for item in registry}
    conflict_reasons: list[str] = []
    if context.lineage_generation_status == LINEAGE_CONFLICT or "CONTRADICTS_LINEAGE" in claim_statuses:
        conflict_reasons.append("LOCAL_LINEAGE_OWNERSHIP_CONFLICT")
    if context.provider_binding_status == PROVIDER_BINDING_MISMATCH:
        conflict_reasons.append("LINEAGE_PROVIDER_SNAPSHOT_MISMATCH")
    if context.multiplicity_status == MULTIPLICITY_MULTIPLE:
        conflict_reasons.append("PROVIDER_OBJECT_MULTIPLICITY_CONFLICT")
    if CONFLICT in registry_statuses:
        conflict_reasons.append("LOCAL_EVIDENCE_NEWER_OR_CONTRADICTORY")
    if conflict_reasons:
        dispositions = _fp04_blocking_dispositions(provider_object_class, fresh_reconcile=True)
        if provider_object_class == "ACTIVE_PROTECTION":
            conflict_reasons.append("PROTECTION_REGISTRY_CONVERGENCE_REQUIRED")
        conflict_reasons.append("OWNERSHIP_RECONCILIATION_INCOMPLETE")
        return (
            CONFLICTING_OWNERSHIP_EVIDENCE,
            RECONCILIATION_REQUIRED,
            _sorted_dispositions(dispositions),
            _sorted_reasons(conflict_reasons),
        )

    stale_or_unknown = (
        context.lineage_generation_status == LINEAGE_UNKNOWN
        or context.provider_binding_status == PROVIDER_BINDING_UNKNOWN
        or context.multiplicity_status == MULTIPLICITY_UNKNOWN
        or "UNKNOWN" in claim_statuses
        or bool(registry_statuses & {STALE, UNKNOWN})
    )
    if stale_or_unknown:
        reasons = ["PROVIDER_OBJECT_LINEAGE_NOT_PROVEN", "OWNERSHIP_RECONCILIATION_INCOMPLETE"]
        if STALE in registry_statuses:
            reasons.append("OWNERSHIP_EVIDENCE_STALE")
        dispositions = _fp04_blocking_dispositions(provider_object_class, fresh_reconcile=True)
        return (
            OWNERSHIP_UNKNOWN,
            RECONCILIATION_REQUIRED,
            _sorted_dispositions(dispositions),
            _sorted_reasons(reasons),
        )

    if context.lineage_generation_status == LINEAGE_PRIOR_GENERATION:
        if not any(item["claim_status"] in {"CLAIMS_OWNERSHIP", "SUPPORTS_LINEAGE"} for item in lineage):
            raise ExternalCloseEvidenceError("FP04_PRIOR_LINEAGE_UNPROVEN", "prior-generation classification requires concrete lineage evidence")
        dispositions = _fp04_blocking_dispositions(provider_object_class, fresh_reconcile=True)
        return (
            KNOWN_OWNED_PRIOR_GENERATION,
            RECONCILIATION_REQUIRED,
            _sorted_dispositions(dispositions),
            _sorted_reasons(
                [
                    "PROVIDER_OBJECT_PRIOR_RUNTIME_GENERATION",
                    "LIFECYCLE_REINTERPRETATION_REQUIRED",
                    "OWNERSHIP_RECONCILIATION_INCOMPLETE",
                ]
            ),
        )

    if context.lineage_generation_status == LINEAGE_EXTERNAL:
        dispositions = _fp04_blocking_dispositions(provider_object_class, fresh_reconcile=False)
        return (
            EXTERNAL_UNTRACKED,
            CONVERGENCE_REQUIRED,
            _sorted_dispositions(dispositions),
            _sorted_reasons(
                ["EXTERNAL_PROVIDER_OBJECT_UNTRACKED", "LIFECYCLE_REINTERPRETATION_REQUIRED"]
            ),
        )

    if context.provider_binding_status != PROVIDER_BINDING_EXACT or context.multiplicity_status != MULTIPLICITY_SINGLE:
        raise ExternalCloseEvidenceError("FP04_CURRENT_BINDING_NOT_EXACT", "current-generation ownership requires exact single-object binding")
    if not any(item["claim_status"] == "CLAIMS_OWNERSHIP" for item in lineage):
        raise ExternalCloseEvidenceError("FP04_CURRENT_OWNERSHIP_UNPROVEN", "current-generation ownership requires an explicit ownership claim")
    if any(item["currentness_status"] != CURRENT for item in registry):
        raise ExternalCloseEvidenceError("FP04_CURRENT_REGISTRY_NOT_CURRENT", "current-generation ownership requires current registry evidence")
    return (
        KNOWN_OWNED_CURRENT_GENERATION,
        CURRENT_KNOWN_OWNED,
        [NO_ACTION_CURRENT_KNOWN_OWNED],
        ["CURRENT_GENERATION_OWNERSHIP_PROVEN"],
    )


def build_external_provider_ownership_evidence(
    observation: ProviderObjectObservation,
    context: OwnershipEvaluationContext,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce immutable FP-04 evidence from already-observed provider/local facts only."""

    if observation.provider_object_class not in _FP04_OBJECT_CLASSES:
        raise ExternalCloseEvidenceError("FP04_OBJECT_CLASS_INVALID", "provider object class unsupported")
    for field, value in (
        ("provider_identity_ref", observation.provider_identity_ref),
        ("canonical_symbol", observation.canonical_symbol),
        ("provider_instrument_ref", observation.provider_instrument_ref),
        ("provider_object_ref", observation.provider_object_ref),
        ("provider_snapshot_ref", observation.provider_snapshot_ref),
        ("provider_observation_generation_id", observation.provider_observation_generation_id),
        ("current_project_revision", context.current_project_revision),
    ):
        _text(value, field)
    if not isinstance(observation.provider_identity, Mapping) or not observation.provider_identity:
        raise ExternalCloseEvidenceError("PROVIDER_IDENTITY_UNBOUND", "provider identity material is required")
    if not isinstance(observation.provider_snapshot, Mapping) or not observation.provider_snapshot:
        raise ExternalCloseEvidenceError("PROVIDER_SNAPSHOT_UNBOUND", "provider snapshot material is required")

    observed_at = _utc_text(observation.provider_observed_at, "provider_observed_at")
    received_at = _utc_text(observation.provider_received_at, "provider_received_at")
    evaluated_at = _utc_text(context.evaluated_at, "evaluated_at")
    if _utc_dt(received_at, "provider_received_at") < _utc_dt(observed_at, "provider_observed_at"):
        raise ExternalCloseEvidenceError("FP04_TEMPORAL_ORDER_INVALID", "provider receipt cannot precede observation")

    lineage = _normalize_lineage(context.local_lineage_evidence)
    registry = _normalize_registry(context.local_registry_evidence)
    latest_local_times = [
        _utc_dt(item["observed_or_created_at"], "local_lineage_evidence.observed_or_created_at")
        for item in lineage
    ] + [_utc_dt(item["observed_at"], "local_registry_evidence.observed_at") for item in registry]
    evaluation_dt = _utc_dt(evaluated_at, "evaluated_at")
    if evaluation_dt < _utc_dt(received_at, "provider_received_at") or any(
        evaluation_dt < item_time for item_time in latest_local_times
    ):
        raise ExternalCloseEvidenceError("FP04_TEMPORAL_ORDER_INVALID", "evaluation predates bound evidence")

    ownership, reconciliation, dispositions, reasons = _derive_fp04_outcome(
        observation.provider_object_class,
        lineage,
        registry,
        context,
    )

    supersedes_id = None
    if supersedes_evidence is not None:
        try:
            validate_external_provider_ownership_evidence(supersedes_evidence)
        except ExternalCloseReinterpretationError as exc:
            raise ExternalCloseEvidenceError("FP04_SUPERSESSION_INVALID", exc.message) from exc
        if (
            supersedes_evidence.get("provider_object_class") != observation.provider_object_class
            or supersedes_evidence.get("provider_object_ref") != observation.provider_object_ref
            or supersedes_evidence.get("provider_instrument_ref") != observation.provider_instrument_ref
        ):
            raise ExternalCloseEvidenceError("FP04_SUPERSESSION_LINEAGE_MISMATCH", "superseded evidence must belong to the same logical provider object lineage")
        supersedes_id = supersedes_evidence["ownership_evidence_id"]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "external_provider_ownership_profile_version": FP04_PROFILE_VERSION,
        "provider_object_class": observation.provider_object_class,
        "provider_identity_ref": observation.provider_identity_ref,
        "provider_identity_hash": canonical_evidence_hash(observation.provider_identity),
        "canonical_symbol": observation.canonical_symbol,
        "provider_instrument_ref": observation.provider_instrument_ref,
        "provider_object_ref": observation.provider_object_ref,
        "provider_snapshot_ref": observation.provider_snapshot_ref,
        "provider_snapshot_hash": canonical_evidence_hash(observation.provider_snapshot),
        "provider_observation_generation_id": observation.provider_observation_generation_id,
        "provider_observed_at": observed_at,
        "provider_received_at": received_at,
        "current_project_revision": context.current_project_revision,
        "runtime_preflight_ref": _optional_text(context.runtime_preflight_ref, "runtime_preflight_ref"),
        "runtime_process_instance_id": _optional_text(context.runtime_process_instance_id, "runtime_process_instance_id"),
        "runtime_process_start_generation_id": _optional_text(
            context.runtime_process_start_generation_id,
            "runtime_process_start_generation_id",
        ),
        "runtime_config_generation_id": _optional_text(context.runtime_config_generation_id, "runtime_config_generation_id"),
        "local_lineage_evidence": lineage,
        "local_registry_evidence": registry,
        "ownership_classification": ownership,
        "reconciliation_status": reconciliation,
        "required_dispositions": dispositions,
        "reason_codes": reasons,
        "adoption_decision_ref": _optional_text(context.adoption_decision_ref, "adoption_decision_ref"),
        "supersedes_ownership_evidence_id": supersedes_id,
        "evaluated_at": evaluated_at,
    }
    payload["ownership_evidence_id"] = _stable_id("extownrec_", payload, "ownership_evidence_id")
    try:
        validate_external_provider_ownership_evidence(payload)
    except ExternalCloseReinterpretationError as exc:
        raise ExternalCloseEvidenceError("FP04_EMITTED_EVIDENCE_INVALID", exc.message) from exc
    return payload


def external_provider_ownership_evidence_is_current(
    evidence: Mapping[str, Any],
    observation: ProviderObjectObservation,
    context: OwnershipEvaluationContext,
) -> bool:
    """Check exact material currentness; evaluated_at alone is intentionally ignored."""

    try:
        validate_external_provider_ownership_evidence(evidence)
        lineage = _normalize_lineage(context.local_lineage_evidence)
        registry = _normalize_registry(context.local_registry_evidence)
        ownership, reconciliation, dispositions, reasons = _derive_fp04_outcome(
            observation.provider_object_class,
            lineage,
            registry,
            context,
        )
    except (ExternalCloseReinterpretationError, ExternalCloseEvidenceError):
        return False

    expected = {
        "provider_object_class": observation.provider_object_class,
        "provider_identity_ref": observation.provider_identity_ref,
        "provider_identity_hash": canonical_evidence_hash(observation.provider_identity),
        "canonical_symbol": observation.canonical_symbol,
        "provider_instrument_ref": observation.provider_instrument_ref,
        "provider_object_ref": observation.provider_object_ref,
        "provider_snapshot_ref": observation.provider_snapshot_ref,
        "provider_snapshot_hash": canonical_evidence_hash(observation.provider_snapshot),
        "provider_observation_generation_id": observation.provider_observation_generation_id,
        "provider_observed_at": _utc_text(observation.provider_observed_at, "provider_observed_at"),
        "provider_received_at": _utc_text(observation.provider_received_at, "provider_received_at"),
        "current_project_revision": context.current_project_revision,
        "runtime_preflight_ref": context.runtime_preflight_ref,
        "runtime_process_instance_id": context.runtime_process_instance_id,
        "runtime_process_start_generation_id": context.runtime_process_start_generation_id,
        "runtime_config_generation_id": context.runtime_config_generation_id,
        "local_lineage_evidence": lineage,
        "local_registry_evidence": registry,
        "ownership_classification": ownership,
        "reconciliation_status": reconciliation,
        "required_dispositions": dispositions,
        "reason_codes": reasons,
        "adoption_decision_ref": context.adoption_decision_ref,
    }
    return all(evidence.get(field) == value for field, value in expected.items())


def _normalize_execution_evidence(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in items:
        item = _canonicalize(raw)
        if not isinstance(item, dict) or set(item) != _EXECUTION_FIELDS:
            raise ExternalCloseEvidenceError("FP10_EXECUTION_FIELDS_INVALID", "execution evidence entry fields mismatch")
        if item["owner"] not in _FP10_EXECUTION_OWNERS:
            raise ExternalCloseEvidenceError("FP10_EXECUTION_OWNER_INVALID", "execution evidence owner unsupported")
        if item["evidence_class"] not in _FP10_EXECUTION_CLASSES:
            raise ExternalCloseEvidenceError("FP10_EXECUTION_CLASS_INVALID", "execution evidence class unsupported")
        if item["currentness_status"] not in _FP10_EXECUTION_CURRENTNESS:
            raise ExternalCloseEvidenceError("FP10_EXECUTION_CURRENTNESS_INVALID", "execution currentness unsupported")
        if item["position_compatibility_status"] not in _FP10_POSITION_COMPATIBILITY:
            raise ExternalCloseEvidenceError("FP10_POSITION_COMPATIBILITY_INVALID", "position compatibility unsupported")
        if item["lineage_origin"] not in _FP10_LINEAGE_ORIGINS:
            raise ExternalCloseEvidenceError("FP10_LINEAGE_ORIGIN_INVALID", "execution lineage origin unsupported")
        for field in ("evidence_ref", "evidence_generation_id"):
            _text(item[field], f"execution_evidence.{field}")
        _hash(item["evidence_hash"], "execution_evidence.evidence_hash")
        item["latest_observed_at"] = _utc_text(item["latest_observed_at"], "execution_evidence.latest_observed_at")
        normalized.append(item)
    normalized.sort(
        key=lambda item: (
            item["evidence_class"],
            item["owner"],
            item["evidence_ref"],
            item["evidence_hash"],
        )
    )
    keys = [
        (item["evidence_class"], item["owner"], item["evidence_ref"], item["evidence_hash"])
        for item in normalized
    ]
    if len(keys) != len(set(keys)):
        raise ExternalCloseEvidenceError("FP10_EXECUTION_DUPLICATE", "execution evidence keys must be unique")
    return normalized


def _fp04_rows(
    dependencies: Sequence[FP04EvidenceDependency],
    *,
    current_project_revision: str,
    runtime_preflight_ref: str | None,
    runtime_process_instance_id: str | None,
    runtime_process_start_generation_id: str | None,
    runtime_config_generation_id: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dependency in dependencies:
        if dependency.currentness_status not in _FP10_FP04_CURRENTNESS:
            raise ExternalCloseEvidenceError("FP10_FP04_CURRENTNESS_INVALID", "FP-04 dependency currentness unsupported")
        evidence = dependency.evidence
        try:
            validate_external_provider_ownership_evidence(evidence)
        except ExternalCloseReinterpretationError as exc:
            raise ExternalCloseEvidenceError("FP10_FP04_EVIDENCE_INVALID", exc.message) from exc
        generation_matches = (
            evidence.get("current_project_revision") == current_project_revision
            and evidence.get("runtime_preflight_ref") == runtime_preflight_ref
            and evidence.get("runtime_process_instance_id") == runtime_process_instance_id
            and evidence.get("runtime_process_start_generation_id") == runtime_process_start_generation_id
            and evidence.get("runtime_config_generation_id") == runtime_config_generation_id
        )
        if dependency.currentness_status == CURRENT and not generation_matches:
            raise ExternalCloseEvidenceError(
                "FP10_FP04_GENERATION_MISMATCH",
                "FP-04 dependency marked CURRENT but project/runtime generation differs",
            )
        rows.append(
            {
                "provider_object_class": evidence["provider_object_class"],
                "provider_object_ref": evidence["provider_object_ref"],
                "provider_snapshot_hash": evidence["provider_snapshot_hash"],
                "ownership_evidence_ref": evidence["ownership_evidence_id"],
                "ownership_evidence_hash": canonical_evidence_hash(evidence),
                "ownership_classification": evidence["ownership_classification"],
                "ownership_reconciliation_status": evidence["reconciliation_status"],
                "ownership_currentness_status": dependency.currentness_status,
            }
        )
    rows.sort(
        key=lambda row: (
            row["provider_object_class"],
            row["provider_object_ref"],
            row["ownership_evidence_ref"],
        )
    )
    keys = [
        (row["provider_object_class"], row["provider_object_ref"], row["ownership_evidence_ref"])
        for row in rows
    ]
    if len(keys) != len(set(keys)):
        raise ExternalCloseEvidenceError("FP10_FP04_DUPLICATE", "FP-04 dependency keys must be unique")
    return rows


def _validate_normalized_position(
    provider_position: ProviderPositionObservation,
    normalized_position: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    position = _canonicalize(normalized_position)
    if not isinstance(position, dict):
        raise ExternalCloseEvidenceError("FP10_POSITION_INVALID", "normalized Position must be a mapping")
    for field in (
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "broker_state_observed_at",
        "reconciliation_status",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    ):
        if field not in position:
            raise ExternalCloseEvidenceError("FP10_POSITION_INCOMPLETE", f"normalized Position missing {field}")
    quantity = _quantity_text(position["actual_quantity"], "normalized_position.actual_quantity")
    provider_quantity = _quantity_text(
        provider_position.normalized_actual_quantity,
        "provider_position.normalized_actual_quantity",
    )
    if (
        position["position_id"] != provider_position.position_id
        or position["symbol"] != provider_position.canonical_symbol
        or position["side"] != provider_position.position_side
        or Decimal(quantity) != Decimal(provider_quantity)
    ):
        raise ExternalCloseEvidenceError(
            "FP10_PROVIDER_NORMALIZED_POSITION_MISMATCH",
            "normalized Position identity/side/quantity does not match provider Position facts",
        )
    observed = _utc_text(position["broker_state_observed_at"], "normalized_position.broker_state_observed_at")
    provider_observed = _utc_text(
        provider_position.provider_position_observed_at,
        "provider_position_observed_at",
    )
    if observed != provider_observed:
        raise ExternalCloseEvidenceError(
            "FP10_PROVIDER_NORMALIZED_POSITION_MISMATCH",
            "normalized Position observation anchor must equal provider Position observation",
        )
    position["actual_quantity"] = quantity
    position["broker_state_observed_at"] = observed
    return position, quantity


def _validate_fp10_structural_invariants(
    assembly: CloseConvergenceAssemblyInput,
    *,
    quantity: Decimal,
    execution: Sequence[Mapping[str, Any]],
    fp04_rows: Sequence[Mapping[str, Any]],
    lifecycle_projection: Mapping[str, Any],
) -> None:
    state = assembly.convergence_state
    if state not in _FP10_STATES:
        raise ExternalCloseEvidenceError("FP10_STATE_INVALID", "convergence state unsupported")
    if assembly.exposure_change_origin_classification not in _FP10_ORIGINS:
        raise ExternalCloseEvidenceError("FP10_ORIGIN_INVALID", "exposure origin unsupported")
    if assembly.provider_position.provider_position_currentness_status not in {CURRENT, STALE, UNKNOWN}:
        raise ExternalCloseEvidenceError("FP10_PROVIDER_CURRENTNESS_INVALID", "provider Position currentness unsupported")
    if assembly.terminal_protection.status not in _FP10_TERMINAL_PROTECTION:
        raise ExternalCloseEvidenceError("FP10_TERMINAL_PROTECTION_STATUS_INVALID", "terminal protection status unsupported")
    if assembly.fp05_residual_state not in _FP05_STATES:
        raise ExternalCloseEvidenceError("FP10_FP05_STATE_INVALID", "FP-05 residual state unsupported")

    dispositions = _sorted_dispositions(assembly.required_dispositions, fp10=True)
    reasons = _sorted_reasons(assembly.reason_codes, fp10=True)
    if state == LIFECYCLE_CLOSE_ELIGIBLE:
        if quantity != 0:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exact zero exposure")
        if assembly.provider_position.provider_position_currentness_status != CURRENT:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires current provider Position truth")
        if assembly.normalized_position.get("reconciliation_status") != CONSISTENT:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires CONSISTENT normalized Position")
        if assembly.terminal_protection.status != TERMINAL_PROTECTION_CLEAR:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires terminal protection clear")
        if dispositions != [NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE]:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exclusive no-action disposition")
        if reasons != ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]:
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires exact success reason")
        if not execution or any(
            item["currentness_status"] != CURRENT
            or item["position_compatibility_status"] != "COMPATIBLE"
            for item in execution
        ):
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires current compatible execution evidence")
        if not fp04_rows:
            raise ExternalCloseEvidenceError("FP10_FP04_REQUIRED", "close eligibility requires materially relevant FP-04 evidence")
        if any(
            item["ownership_currentness_status"] != CURRENT
            or item["ownership_classification"] in {CONFLICTING_OWNERSHIP_EVIDENCE, OWNERSHIP_UNKNOWN}
            or item["ownership_reconciliation_status"] == OWNERSHIP_UNKNOWN
            for item in fp04_rows
        ):
            raise ExternalCloseEvidenceError("FP10_FALSE_CLOSE_ELIGIBLE", "close eligibility requires current non-conflicting FP-04 evidence")
        if assembly.fp05_residual_state in {
            RESIDUAL_NONZERO_REPRESENTABLE,
            RESIDUAL_NONZERO_UNREPRESENTABLE,
            "PARTIALLY_REDUCIBLE",
            "FULLY_REDUCIBLE",
        }:
            raise ExternalCloseEvidenceError("FP10_FP05_CONTRADICTS_FLAT", "positive/reducible FP-05 state contradicts flat close eligibility")
        if lifecycle_projection.get("lifecycle_source_broker_state_observed_at") != assembly.normalized_position.get(
            "broker_state_observed_at"
        ):
            raise ExternalCloseEvidenceError(
                "FP10_LIFECYCLE_NOT_CURRENT_FOR_POSITION",
                "close eligibility requires lifecycle interpretation bound to current Position observation",
            )

    if quantity > 0 and state in {
        LIFECYCLE_CLOSE_ELIGIBLE,
        FLAT_PROVIDER_TRUTH_PROVEN,
        FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED,
        FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED,
    }:
        raise ExternalCloseEvidenceError("FP10_FALSE_FLAT", "positive authoritative exposure cannot be flat/close eligible")
    if quantity > 0 and assembly.fp05_residual_state == RESIDUAL_NONZERO_UNREPRESENTABLE:
        if state != RESIDUAL_UNREPRESENTABLE_NOT_FLAT:
            raise ExternalCloseEvidenceError(
                "FP10_UNREPRESENTABLE_RESIDUAL_STATE_REQUIRED",
                "positive unrepresentable residual requires explicit non-flat state",
            )
        if "BLOCK_CLOSE_RETRY_MUTATION" not in dispositions:
            raise ExternalCloseEvidenceError(
                "FP10_UNREPRESENTABLE_RESIDUAL_RETRY_BLOCK_REQUIRED",
                "unchanged unrepresentable residual must block close retry mutation",
            )
    if quantity == 0 and state == RESIDUAL_UNREPRESENTABLE_NOT_FLAT:
        raise ExternalCloseEvidenceError("FP10_FALSE_RESIDUAL", "unrepresentable residual requires positive exposure")
    if state == FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED and quantity != 0:
        raise ExternalCloseEvidenceError("FP10_FALSE_FLAT", "flat execution reconciliation state requires zero exposure")
    if state == FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED and quantity != 0:
        raise ExternalCloseEvidenceError("FP10_FALSE_FLAT", "flat protection convergence state requires zero exposure")
    if state == EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED and assembly.exposure_change_origin_classification not in {
        PRIOR_GENERATION_PROJECT,
        EXTERNAL_MANUAL,
        MIXED_OR_UNKNOWN,
    }:
        raise ExternalCloseEvidenceError("FP10_EXTERNAL_ORIGIN_REQUIRED", "external/manual reinterpretation requires non-current origin")
    if quantity == 0 and any(
        item["currentness_status"] != CURRENT or item["position_compatibility_status"] != "COMPATIBLE"
        for item in execution
    ) and state == LIFECYCLE_CLOSE_ELIGIBLE:
        raise ExternalCloseEvidenceError("FP10_EXECUTION_RECONCILIATION_REQUIRED", "ambiguous execution cannot be close eligible")


def build_external_manual_close_convergence_evidence(
    assembly: CloseConvergenceAssemblyInput,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble immutable FP-10 evidence without deciding E5 lifecycle policy."""

    provider = assembly.provider_position
    for field, value in (
        ("provider_identity_ref", provider.provider_identity_ref),
        ("provider_instrument_ref", provider.provider_instrument_ref),
        ("provider_position_snapshot_ref", provider.provider_position_snapshot_ref),
        ("provider_position_observation_generation_id", provider.provider_position_observation_generation_id),
        ("position_id", provider.position_id),
        ("canonical_symbol", provider.canonical_symbol),
        ("position_side", provider.position_side),
        ("normalized_position_ref", assembly.normalized_position_ref),
        ("lifecycle_projection_ref", assembly.lifecycle_projection_ref),
        ("lifecycle_execution_binding_ref", assembly.lifecycle_execution_binding_ref),
        ("current_project_revision", assembly.current_project_revision),
        ("terminal_protection_observation_ref", assembly.terminal_protection.observation_ref),
    ):
        _text(value, field)
    if not isinstance(provider.provider_identity, Mapping) or not provider.provider_identity:
        raise ExternalCloseEvidenceError("FP10_PROVIDER_IDENTITY_REQUIRED", "provider identity material is required")
    if not isinstance(provider.provider_position_snapshot, Mapping) or not provider.provider_position_snapshot:
        raise ExternalCloseEvidenceError("FP10_PROVIDER_POSITION_SNAPSHOT_REQUIRED", "provider Position snapshot material is required")
    if not isinstance(assembly.terminal_protection.observation_payload, Mapping) or not assembly.terminal_protection.observation_payload:
        raise ExternalCloseEvidenceError("FP10_TERMINAL_PROTECTION_SNAPSHOT_REQUIRED", "terminal protection observation material is required")

    normalized_position, quantity_text = _validate_normalized_position(provider, assembly.normalized_position)
    quantity = Decimal(quantity_text)
    execution = _normalize_execution_evidence(assembly.execution_evidence)
    fp04_rows = _fp04_rows(
        assembly.fp04_dependencies,
        current_project_revision=assembly.current_project_revision,
        runtime_preflight_ref=assembly.runtime_preflight_ref,
        runtime_process_instance_id=assembly.runtime_process_instance_id,
        runtime_process_start_generation_id=assembly.runtime_process_start_generation_id,
        runtime_config_generation_id=assembly.runtime_config_generation_id,
    )

    try:
        validate_position_lifecycle_projection(assembly.lifecycle_projection)
        validate_position_lifecycle_execution_evidence_binding(
            assembly.lifecycle_execution_binding,
            assembly.lifecycle_projection,
        )
    except (LifecycleProjectionError, LifecycleExecutionBindingError) as exc:
        raise ExternalCloseEvidenceError("FP10_LIFECYCLE_EVIDENCE_INVALID", str(exc)) from exc
    lifecycle_projection = _canonicalize(assembly.lifecycle_projection)
    lifecycle_binding = _canonicalize(assembly.lifecycle_execution_binding)
    if not isinstance(lifecycle_projection, dict) or not isinstance(lifecycle_binding, dict):
        raise ExternalCloseEvidenceError("FP10_LIFECYCLE_EVIDENCE_INVALID", "lifecycle evidence must be mappings")
    if lifecycle_projection.get("position_id") != provider.position_id:
        raise ExternalCloseEvidenceError("FP10_LIFECYCLE_POSITION_MISMATCH", "lifecycle projection belongs to a different Position")
    if assembly.lifecycle_projection_ref != lifecycle_projection.get("lifecycle_projection_id"):
        raise ExternalCloseEvidenceError("FP10_LIFECYCLE_REF_MISMATCH", "lifecycle projection ref must equal projection ID")
    if assembly.lifecycle_execution_binding_ref != lifecycle_binding.get("lifecycle_execution_binding_id"):
        raise ExternalCloseEvidenceError("FP10_EXECUTION_BINDING_REF_MISMATCH", "lifecycle execution binding ref must equal binding ID")

    fp05_ref, fp05_hash = _optional_ref_hash(
        assembly.fp05_close_residual_sizing_ref,
        assembly.fp05_close_residual_sizing_hash,
        "fp05_close_residual_sizing",
    )
    fp11_ref, fp11_hash = _optional_ref_hash(
        assembly.fp11_prior_registry_evidence_ref,
        assembly.fp11_prior_registry_evidence_hash,
        "fp11_prior_registry_evidence",
    )
    if fp05_ref is None and assembly.fp05_residual_state != FP05_NOT_APPLICABLE:
        raise ExternalCloseEvidenceError("FP10_FP05_REF_REQUIRED", "non-NOT_APPLICABLE FP-05 state requires exact ref/hash")
    if fp05_ref is not None and assembly.fp05_residual_state == FP05_NOT_APPLICABLE:
        raise ExternalCloseEvidenceError("FP10_FP05_STATE_REQUIRED", "FP-05 ref/hash requires an applicable residual state")

    provider_observed = _utc_text(provider.provider_position_observed_at, "provider_position_observed_at")
    provider_received = _utc_text(provider.provider_position_received_at, "provider_position_received_at")
    terminal_observed = _utc_text(assembly.terminal_protection.observed_at, "terminal_protection_observed_at")
    terminal_received = _utc_text(assembly.terminal_protection.received_at, "terminal_protection_received_at")
    evaluated_at = _utc_text(assembly.evaluated_at, "evaluated_at")
    if _utc_dt(provider_received, "provider_position_received_at") < _utc_dt(
        provider_observed,
        "provider_position_observed_at",
    ):
        raise ExternalCloseEvidenceError("FP10_TEMPORAL_ORDER_INVALID", "provider Position receipt precedes observation")
    if _utc_dt(terminal_received, "terminal_protection_received_at") < _utc_dt(
        terminal_observed,
        "terminal_protection_observed_at",
    ):
        raise ExternalCloseEvidenceError("FP10_TEMPORAL_ORDER_INVALID", "terminal protection receipt precedes observation")
    if _utc_dt(evaluated_at, "evaluated_at") < max(
        _utc_dt(provider_received, "provider_position_received_at"),
        _utc_dt(terminal_received, "terminal_protection_received_at"),
    ):
        raise ExternalCloseEvidenceError("FP10_TEMPORAL_ORDER_INVALID", "evaluation predates bound provider evidence")
    if assembly.convergence_state == LIFECYCLE_CLOSE_ELIGIBLE and _utc_dt(
        terminal_received,
        "terminal_protection_received_at",
    ) < _utc_dt(provider_received, "provider_position_received_at"):
        raise ExternalCloseEvidenceError(
            "FP10_TERMINAL_PROTECTION_PRECEDES_FLAT_ACCEPTANCE",
            "close eligibility requires terminal protection observation after flat Position acceptance",
        )

    _validate_fp10_structural_invariants(
        assembly,
        quantity=quantity,
        execution=execution,
        fp04_rows=fp04_rows,
        lifecycle_projection=lifecycle_projection,
    )
    dispositions = _sorted_dispositions(assembly.required_dispositions, fp10=True)
    reasons = _sorted_reasons(assembly.reason_codes, fp10=True)

    supersedes_id = None
    if supersedes_evidence is not None:
        try:
            validate_external_manual_close_convergence_evidence(supersedes_evidence)
        except ExternalCloseReinterpretationError as exc:
            raise ExternalCloseEvidenceError("FP10_SUPERSESSION_INVALID", exc.message) from exc
        if supersedes_evidence.get("position_id") != provider.position_id:
            raise ExternalCloseEvidenceError("FP10_SUPERSESSION_POSITION_MISMATCH", "superseded FP-10 evidence belongs to another Position")
        supersedes_id = supersedes_evidence["close_convergence_evidence_id"]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "external_manual_close_convergence_profile_version": FP10_PROFILE_VERSION,
        "position_id": provider.position_id,
        "canonical_symbol": provider.canonical_symbol,
        "provider_identity_ref": provider.provider_identity_ref,
        "provider_identity_hash": canonical_evidence_hash(provider.provider_identity),
        "provider_instrument_ref": provider.provider_instrument_ref,
        "provider_position_snapshot_ref": provider.provider_position_snapshot_ref,
        "provider_position_snapshot_hash": canonical_evidence_hash(provider.provider_position_snapshot),
        "provider_position_observation_generation_id": provider.provider_position_observation_generation_id,
        "provider_position_observed_at": provider_observed,
        "provider_position_received_at": provider_received,
        "provider_position_currentness_status": provider.provider_position_currentness_status,
        "normalized_position_ref": assembly.normalized_position_ref,
        "normalized_position_hash": canonical_evidence_hash(normalized_position),
        "normalized_position_broker_state_observed_at": normalized_position["broker_state_observed_at"],
        "normalized_position_reconciliation_status": normalized_position["reconciliation_status"],
        "normalized_actual_quantity": quantity_text,
        "normalized_quantity_profile_version": normalized_position["quantity_profile_version"],
        "normalized_quantity_unit": normalized_position["quantity_unit"],
        "normalized_quantity_asset": normalized_position["quantity_asset"],
        "execution_evidence": execution,
        "execution_evidence_set_hash": canonical_evidence_hash(execution),
        "fp04_ownership_evidence": fp04_rows,
        "fp04_evidence_set_hash": canonical_evidence_hash(fp04_rows),
        "fp05_close_residual_sizing_ref": fp05_ref,
        "fp05_close_residual_sizing_hash": fp05_hash,
        "fp05_residual_state": assembly.fp05_residual_state,
        "fp11_prior_registry_evidence_ref": fp11_ref,
        "fp11_prior_registry_evidence_hash": fp11_hash,
        "terminal_protection_observation_ref": assembly.terminal_protection.observation_ref,
        "terminal_protection_observation_hash": canonical_evidence_hash(
            assembly.terminal_protection.observation_payload
        ),
        "terminal_protection_observed_at": terminal_observed,
        "terminal_protection_received_at": terminal_received,
        "terminal_protection_status": assembly.terminal_protection.status,
        "lifecycle_projection_ref": assembly.lifecycle_projection_ref,
        "lifecycle_projection_hash": canonical_evidence_hash(lifecycle_projection),
        "lifecycle_projection_id": lifecycle_projection["lifecycle_projection_id"],
        "lifecycle_revision": lifecycle_projection["lifecycle_revision"],
        "lifecycle_state": lifecycle_projection["lifecycle_state"],
        "lifecycle_execution_binding_ref": assembly.lifecycle_execution_binding_ref,
        "lifecycle_execution_binding_hash": canonical_evidence_hash(lifecycle_binding),
        "lifecycle_execution_snapshot_hash": lifecycle_binding["execution_snapshot_hash"],
        "current_project_revision": assembly.current_project_revision,
        "runtime_preflight_ref": _optional_text(assembly.runtime_preflight_ref, "runtime_preflight_ref"),
        "runtime_process_instance_id": _optional_text(assembly.runtime_process_instance_id, "runtime_process_instance_id"),
        "runtime_process_start_generation_id": _optional_text(
            assembly.runtime_process_start_generation_id,
            "runtime_process_start_generation_id",
        ),
        "runtime_config_generation_id": _optional_text(assembly.runtime_config_generation_id, "runtime_config_generation_id"),
        "exposure_change_origin_classification": assembly.exposure_change_origin_classification,
        "convergence_state": assembly.convergence_state,
        "required_dispositions": dispositions,
        "reason_codes": reasons,
        "supersedes_close_convergence_evidence_id": supersedes_id,
        "evaluated_at": evaluated_at,
    }
    payload["close_convergence_evidence_id"] = _stable_id(
        "extcloseconv_",
        payload,
        "close_convergence_evidence_id",
    )
    try:
        validate_external_manual_close_convergence_evidence(payload)
    except ExternalCloseReinterpretationError as exc:
        raise ExternalCloseEvidenceError("FP10_EMITTED_EVIDENCE_INVALID", exc.message) from exc
    return payload


def external_manual_close_convergence_evidence_is_current(
    evidence: Mapping[str, Any],
    assembly: CloseConvergenceAssemblyInput,
) -> bool:
    """Check material FP-10 currentness while ignoring a later evaluation timestamp alone."""

    try:
        validate_external_manual_close_convergence_evidence(evidence)
        current = build_external_manual_close_convergence_evidence(
            CloseConvergenceAssemblyInput(
                **{
                    **assembly.__dict__,
                    "evaluated_at": evidence["evaluated_at"],
                }
            ),
            supersedes_evidence=None,
        )
    except (ExternalCloseReinterpretationError, ExternalCloseEvidenceError, TypeError):
        return False

    ignored = {
        "close_convergence_evidence_id",
        "evaluated_at",
        "supersedes_close_convergence_evidence_id",
    }
    return all(evidence.get(field) == value for field, value in current.items() if field not in ignored)
