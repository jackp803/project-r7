from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from position.external_close_policy import validate_external_provider_ownership_evidence
from position.external_close_reinterpretation import ExternalCloseReinterpretationError

from .external_close_evidence import (
    CONFLICTING_OWNERSHIP_EVIDENCE,
    CURRENT,
    CURRENT_KNOWN_OWNED,
    EXTERNAL_UNTRACKED,
    KNOWN_OWNED_CURRENT_GENERATION,
    KNOWN_OWNED_PRIOR_GENERATION,
    NO_ACTION_CURRENT_KNOWN_OWNED,
    OWNERSHIP_UNKNOWN,
    ExternalCloseEvidenceError,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    canonical_evidence_hash,
    external_provider_ownership_evidence_is_current,
)

SCHEMA_VERSION = "contracts-v0.1"
PROFILE_VERSION = "protection-registry-multiplicity-v0.1"
FP04_PROFILE_VERSION = "external-provider-object-ownership-reconciliation-v0.1"
ACTIVE_PROTECTION = "ACTIVE_PROTECTION"

COMPLETE = "COMPLETE"
INCOMPLETE = "INCOMPLETE"
UNKNOWN = "UNKNOWN"
STALE = "STALE"

EXACT_MATCH = "EXACT_MATCH"
NOT_MATCH = "NOT_MATCH"

NO_ACTIVE_PROTECTION_OBSERVED = "NO_ACTIVE_PROTECTION_OBSERVED"
EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION = "EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION"
MULTIPLE_ACTIVE_PROTECTIONS = "MULTIPLE_ACTIVE_PROTECTIONS"
ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT = "ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT"
OWNERSHIP_CONFLICT_PRESENT = "OWNERSHIP_CONFLICT_PRESENT"
PROTECTION_SET_STALE = "PROTECTION_SET_STALE"
PROTECTION_SET_UNKNOWN = "PROTECTION_SET_UNKNOWN"

CONVERGED_EXACTLY_ONE_INTENDED = "CONVERGED_EXACTLY_ONE_INTENDED"
MISSING_PROTECTION_REINTERPRETATION_REQUIRED = "MISSING_PROTECTION_REINTERPRETATION_REQUIRED"
MULTIPLICITY_CONVERGENCE_REQUIRED = "MULTIPLICITY_CONVERGENCE_REQUIRED"
ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED = "ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED"
OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED = "OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED"
PROVIDER_SET_REFRESH_REQUIRED = "PROVIDER_SET_REFRESH_REQUIRED"
LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED = "LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED"
REGISTRY_UNKNOWN = "UNKNOWN"

NO_ACTION_REGISTRY_CONVERGED = "NO_ACTION_REGISTRY_CONVERGED"
E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED = "E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED"
MULTIPLICITY_CONVERGENCE_DISPOSITION = "MULTIPLICITY_CONVERGENCE_REQUIRED"
ORPHAN_EXTERNAL_RECONCILIATION_DISPOSITION = "ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED"
OWNERSHIP_MANUAL_REVIEW_REQUIRED = "OWNERSHIP_MANUAL_REVIEW_REQUIRED"
REFRESH_PROVIDER_PROTECTION_SET_REQUIRED = "REFRESH_PROVIDER_PROTECTION_SET_REQUIRED"
BLOCK_NEW_EXPOSURE = "BLOCK_NEW_EXPOSURE"
BLOCK_PROTECTION_CREATE_REPLACE = "BLOCK_PROTECTION_CREATE_REPLACE"
BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL = "BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL"
LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED = (
    "LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED"
)
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED = (
    "FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED"
)

_MULTIPLICITY_STATES = frozenset(
    {
        NO_ACTIVE_PROTECTION_OBSERVED,
        EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION,
        MULTIPLE_ACTIVE_PROTECTIONS,
        ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT,
        OWNERSHIP_CONFLICT_PRESENT,
        PROTECTION_SET_STALE,
        PROTECTION_SET_UNKNOWN,
    }
)
_REGISTRY_STATUSES = frozenset(
    {
        CONVERGED_EXACTLY_ONE_INTENDED,
        MISSING_PROTECTION_REINTERPRETATION_REQUIRED,
        MULTIPLICITY_CONVERGENCE_REQUIRED,
        ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED,
        OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED,
        PROVIDER_SET_REFRESH_REQUIRED,
        LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED,
        REGISTRY_UNKNOWN,
    }
)
_DISPOSITIONS = frozenset(
    {
        NO_ACTION_REGISTRY_CONVERGED,
        E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED,
        MULTIPLICITY_CONVERGENCE_DISPOSITION,
        ORPHAN_EXTERNAL_RECONCILIATION_DISPOSITION,
        OWNERSHIP_MANUAL_REVIEW_REQUIRED,
        REFRESH_PROVIDER_PROTECTION_SET_REQUIRED,
        BLOCK_NEW_EXPOSURE,
        BLOCK_PROTECTION_CREATE_REPLACE,
        BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL,
        LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED,
        FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED,
    }
)
_REASON_ORDER = (
    "PROTECTION_REGISTRY_PROFILE_UNSUPPORTED",
    "POSITION_REFERENCE_MISSING_OR_MISMATCHED",
    "POSITION_EVIDENCE_STALE",
    "INTENDED_PROTECTION_LINEAGE_MISSING",
    "INTENDED_PROTECTION_LINEAGE_MISMATCH",
    "INTENDED_PROTECTION_LINEAGE_STALE",
    "PROVIDER_PROTECTION_OBSERVATION_INCOMPLETE",
    "PROVIDER_PROTECTION_SET_STALE",
    "PROVIDER_PROTECTION_SET_UNKNOWN",
    "PROTECTION_OWNERSHIP_EVIDENCE_MISSING",
    "PROTECTION_OWNERSHIP_EVIDENCE_STALE",
    "PROTECTION_OWNERSHIP_EVIDENCE_MISMATCH",
    "NO_ACTIVE_PROTECTION_OBSERVED",
    "MULTIPLE_ACTIVE_PROTECTIONS_OBSERVED",
    "EXTERNAL_OR_ORPHAN_PROTECTION_PRESENT",
    "PRIOR_GENERATION_PROTECTION_PRESENT",
    "PROTECTION_OWNERSHIP_CONFLICT_PRESENT",
    "INTENDED_PROTECTION_OBJECT_IDENTITY_MISMATCH",
    "LIFECYCLE_PROTECTION_STATE_CONTRADICTION",
    "PROVIDER_PROTECTION_SET_CHANGED_SINCE_EVALUATION",
    "PROTECTION_REGISTRY_EVIDENCE_IDENTITY_INVALID",
    "FRESH_PROTECTION_RECONCILIATION_REQUIRED",
    "E5_PROTECTION_REINTERPRETATION_REQUIRED",
    "PROTECTION_MULTIPLICITY_CONVERGENCE_REQUIRED",
    "PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED",
    "EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED",
)
_REASON_INDEX = {value: index for index, value in enumerate(_REASON_ORDER)}

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^protregmul_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_CURRENTNESS = frozenset({CURRENT, STALE, UNKNOWN})
_COVERAGE = frozenset({COMPLETE, INCOMPLETE, UNKNOWN})
_BINDING_STATUSES = frozenset({EXACT_MATCH, NOT_MATCH, UNKNOWN})
_PROTECTED_LIFECYCLE_STATES = frozenset({"OPEN_PROTECTED", "PROFIT_PROTECTED"})

_INTENDED_LINEAGE_FIELDS = frozenset(
    {
        "position_ref",
        "position_hash",
        "position_id",
        "position_observed_at",
        "position_side",
        "position_quantity_ref",
        "position_action_ref",
        "position_action_hash",
        "position_action_id",
        "approved_trade_plan_ref",
        "approved_trade_plan_hash",
        "risk_decision_ref",
        "protection_order_request_ref",
        "protection_order_request_hash",
        "client_order_identity_ref",
        "lifecycle_projection_ref",
        "lifecycle_execution_binding_ref",
        "trigger_validity_ref",
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
        "ownership_reconciliation_generation_ref",
    }
)
_OBSERVED_SET_FIELDS = frozenset(
    {
        "provider_identity_ref",
        "provider_identity_hash",
        "canonical_symbol",
        "provider_instrument_ref",
        "provider_observation_generation_id",
        "provider_observed_at",
        "provider_received_at",
        "observation_coverage_status",
        "set_currentness_status",
        "objects",
        "observed_set_hash",
    }
)
_ENTRY_FIELDS = frozenset(
    {
        "provider_object_ref",
        "provider_snapshot_ref",
        "provider_snapshot_hash",
        "provider_object_observed_at",
        "ownership_evidence_ref",
        "ownership_evidence_hash",
        "ownership_classification",
        "ownership_reconciliation_status",
        "intended_lineage_binding_status",
        "intended_lineage_binding_ref",
        "intended_lineage_binding_hash",
    }
)
_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "protection_registry_multiplicity_profile_version",
        "protection_registry_evidence_id",
        "position_id",
        "position_ref",
        "position_hash",
        "position_observed_at",
        "intended_protection_lineage",
        "intended_protection_lineage_hash",
        "provider_identity_ref",
        "provider_instrument_ref",
        "provider_observation_generation_id",
        "provider_observed_at",
        "provider_received_at",
        "observation_coverage_status",
        "provider_set_currentness_status",
        "observed_active_protection_objects",
        "observed_active_protection_set_hash",
        "active_protection_count",
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
        "lifecycle_projection_ref",
        "lifecycle_execution_binding_ref",
        "multiplicity_state",
        "registry_status",
        "required_dispositions",
        "reason_codes",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    }
)


class ProtectionRegistryEvidenceError(ValueError):
    """Fail-closed E4 FP-11 evidence production/validation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FP04ActiveProtectionDependency:
    observation: ProviderObjectObservation
    context: OwnershipEvaluationContext
    evidence: Mapping[str, Any]


@dataclass(frozen=True)
class ProtectionRegistryMultiplicityInput:
    position_ref: str
    position: Mapping[str, Any]
    intended_protection_lineage: Mapping[str, Any]
    observed_active_protection_set: Mapping[str, Any]
    fp04_dependencies: Sequence[FP04ActiveProtectionDependency]
    evaluated_at: str | datetime
    lifecycle_projection_ref: str | None = None
    lifecycle_execution_binding_ref: str | None = None
    lifecycle_currentness_status: str = CURRENT
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None
    runtime_currentness_status: str = CURRENT


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ProtectionRegistryEvidenceError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        return _utc_text(value, "datetime")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtectionRegistryEvidenceError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ProtectionRegistryEvidenceError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ProtectionRegistryEvidenceError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical value: {type(value).__name__}",
    )


def canonical_protection_registry_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_protection_registry_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_protection_registry_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProtectionRegistryEvidenceError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise ProtectionRegistryEvidenceError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _utc_text(value: str | datetime, field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ProtectionRegistryEvidenceError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtectionRegistryEvidenceError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionRegistryEvidenceError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionRegistryEvidenceError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_dt(value: str | datetime, field: str) -> datetime:
    text = _utc_text(value, field)
    return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(timezone.utc)


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str) and _DECIMAL_RE.fullmatch(value) is not None:
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ProtectionRegistryEvidenceError("INVALID_DECIMAL", f"{field} is invalid") from exc
    else:
        raise ProtectionRegistryEvidenceError("INVALID_DECIMAL", f"{field} must be a decimal string or Decimal")
    if not parsed.is_finite():
        raise ProtectionRegistryEvidenceError("INVALID_DECIMAL", f"{field} must be finite")
    return parsed


def _optional_ref_hash(ref: Any, digest: Any, label: str) -> tuple[str | None, str | None]:
    if ref is None and digest is None:
        return None, None
    if ref is None or digest is None:
        raise ProtectionRegistryEvidenceError("REFERENCE_HASH_PAIR_INCOMPLETE", f"{label} ref/hash must both be set or null")
    return _text(ref, f"{label}_ref"), _hash(digest, f"{label}_hash")


def _sorted_reasons(values: Sequence[str]) -> list[str]:
    result = [_text(value, "reason_code") for value in values]
    if any(value not in _REASON_INDEX for value in result):
        raise ProtectionRegistryEvidenceError("REASON_UNKNOWN", "reason code is outside protection-registry-multiplicity-v0.1")
    return sorted(set(result), key=_REASON_INDEX.__getitem__)


def _sorted_dispositions(values: Sequence[str]) -> list[str]:
    result = [_text(value, "required_disposition") for value in values]
    if not result or any(value not in _DISPOSITIONS for value in result):
        raise ProtectionRegistryEvidenceError("DISPOSITION_UNKNOWN", "disposition is outside protection-registry-multiplicity-v0.1")
    normalized = sorted(set(result))
    if NO_ACTION_REGISTRY_CONVERGED in normalized and normalized != [NO_ACTION_REGISTRY_CONVERGED]:
        raise ProtectionRegistryEvidenceError("CONVERGED_DISPOSITION_NOT_EXCLUSIVE", "NO_ACTION_REGISTRY_CONVERGED must be exclusive")
    return normalized


def _normalize_intended_lineage(value: Mapping[str, Any]) -> dict[str, Any]:
    lineage = _canonicalize(value)
    if not isinstance(lineage, dict) or set(lineage) != _INTENDED_LINEAGE_FIELDS:
        raise ProtectionRegistryEvidenceError("INTENDED_LINEAGE_FIELDS_INVALID", "IntendedProtectionLineageReference fields mismatch")

    for field in (
        "position_ref",
        "position_id",
        "position_quantity_ref",
        "position_action_ref",
        "position_action_id",
        "approved_trade_plan_ref",
        "risk_decision_ref",
        "ownership_reconciliation_generation_ref",
    ):
        _text(lineage[field], f"intended_protection_lineage.{field}")
    for field in ("position_hash", "position_action_hash", "approved_trade_plan_hash"):
        _hash(lineage[field], f"intended_protection_lineage.{field}")
    _utc_text(lineage["position_observed_at"], "intended_protection_lineage.position_observed_at")
    if lineage["position_side"] not in {"LONG", "SHORT"}:
        raise ProtectionRegistryEvidenceError("INTENDED_LINEAGE_SIDE_INVALID", "position_side must be LONG or SHORT")

    _optional_ref_hash(
        lineage["protection_order_request_ref"],
        lineage["protection_order_request_hash"],
        "intended_protection_lineage.protection_order_request",
    )
    for field in (
        "client_order_identity_ref",
        "lifecycle_projection_ref",
        "lifecycle_execution_binding_ref",
        "trigger_validity_ref",
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
    ):
        _optional_text(lineage[field], f"intended_protection_lineage.{field}")

    runtime_values = (
        lineage["runtime_preflight_ref"],
        lineage["runtime_process_instance_id"],
        lineage["runtime_process_start_generation_id"],
        lineage["runtime_config_generation_id"],
    )
    if any(value is not None for value in runtime_values) and not all(value is not None for value in runtime_values):
        raise ProtectionRegistryEvidenceError("INTENDED_LINEAGE_RUNTIME_INCOMPLETE", "runtime lineage is all-or-none")
    return lineage


def _normalize_entry(value: Mapping[str, Any]) -> dict[str, Any]:
    entry = _canonicalize(value)
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise ProtectionRegistryEvidenceError("OBSERVED_ENTRY_FIELDS_INVALID", "ObservedActiveProtectionEntry fields mismatch")
    for field in (
        "provider_object_ref",
        "provider_snapshot_ref",
        "ownership_evidence_ref",
        "ownership_classification",
        "ownership_reconciliation_status",
    ):
        _text(entry[field], f"observed_entry.{field}")
    for field in ("provider_snapshot_hash", "ownership_evidence_hash"):
        _hash(entry[field], f"observed_entry.{field}")
    _utc_text(entry["provider_object_observed_at"], "observed_entry.provider_object_observed_at")

    binding_status = entry["intended_lineage_binding_status"]
    if binding_status not in _BINDING_STATUSES:
        raise ProtectionRegistryEvidenceError("INTENDED_LINEAGE_BINDING_STATUS_INVALID", "lineage binding status unsupported")
    binding_ref = entry["intended_lineage_binding_ref"]
    binding_hash = entry["intended_lineage_binding_hash"]
    if binding_status == UNKNOWN:
        if binding_ref is not None or binding_hash is not None:
            raise ProtectionRegistryEvidenceError("UNKNOWN_LINEAGE_BINDING_HAS_PROOF", "UNKNOWN lineage binding must not carry ref/hash")
    else:
        if binding_ref is None or binding_hash is None:
            raise ProtectionRegistryEvidenceError("LINEAGE_BINDING_PROOF_REQUIRED", "EXACT_MATCH/NOT_MATCH requires exact binding ref/hash")
        _text(binding_ref, "observed_entry.intended_lineage_binding_ref")
        _hash(binding_hash, "observed_entry.intended_lineage_binding_hash")
    return entry


def active_protection_set_hash(observed_set: Mapping[str, Any]) -> str:
    """Return the section-12 canonical complete provider-set hash."""

    raw = _canonicalize(observed_set)
    if not isinstance(raw, dict):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_INVALID", "ObservedActiveProtectionSet must be a mapping")
    objects = raw.get("objects")
    if isinstance(objects, (str, bytes)) or not isinstance(objects, Sequence):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_OBJECTS_INVALID", "objects must be a sequence")
    normalized = [_normalize_entry(item) for item in objects]
    normalized.sort(
        key=lambda item: (
            item["provider_object_ref"],
            item["provider_snapshot_hash"],
            item["ownership_evidence_ref"],
        )
    )
    material = {
        "provider_identity_ref": _text(raw.get("provider_identity_ref"), "provider_identity_ref"),
        "provider_instrument_ref": _text(raw.get("provider_instrument_ref"), "provider_instrument_ref"),
        "provider_observation_generation_id": _text(
            raw.get("provider_observation_generation_id"),
            "provider_observation_generation_id",
        ),
        "provider_observed_at": _utc_text(raw.get("provider_observed_at"), "provider_observed_at"),
        "observation_coverage_status": raw.get("observation_coverage_status"),
        "provider_set_currentness_status": raw.get("set_currentness_status"),
        "objects": normalized,
    }
    if material["observation_coverage_status"] not in _COVERAGE:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_COVERAGE_INVALID", "observation coverage unsupported")
    if material["provider_set_currentness_status"] not in _CURRENTNESS:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_CURRENTNESS_INVALID", "provider set currentness unsupported")
    return canonical_protection_registry_hash(material)


def _normalize_observed_set(value: Mapping[str, Any]) -> dict[str, Any]:
    observed = _canonicalize(value)
    if not isinstance(observed, dict) or set(observed) != _OBSERVED_SET_FIELDS:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_FIELDS_INVALID", "ObservedActiveProtectionSet fields mismatch")
    for field in (
        "provider_identity_ref",
        "canonical_symbol",
        "provider_instrument_ref",
        "provider_observation_generation_id",
    ):
        _text(observed[field], f"observed_set.{field}")
    _hash(observed["provider_identity_hash"], "observed_set.provider_identity_hash")
    observed["provider_observed_at"] = _utc_text(observed["provider_observed_at"], "observed_set.provider_observed_at")
    observed["provider_received_at"] = _utc_text(observed["provider_received_at"], "observed_set.provider_received_at")
    if _utc_dt(observed["provider_received_at"], "provider_received_at") < _utc_dt(
        observed["provider_observed_at"], "provider_observed_at"
    ):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_TEMPORAL_ORDER_INVALID", "provider_received_at cannot precede provider_observed_at")
    if observed["observation_coverage_status"] not in _COVERAGE:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_COVERAGE_INVALID", "observation coverage unsupported")
    if observed["set_currentness_status"] not in _CURRENTNESS:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_CURRENTNESS_INVALID", "provider set currentness unsupported")
    if isinstance(observed["objects"], (str, bytes)) or not isinstance(observed["objects"], Sequence):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_OBJECTS_INVALID", "objects must be a sequence")
    entries = [_normalize_entry(item) for item in observed["objects"]]
    entries.sort(
        key=lambda item: (
            item["provider_object_ref"],
            item["provider_snapshot_hash"],
            item["ownership_evidence_ref"],
        )
    )
    object_keys = [
        (item["provider_object_ref"], item["provider_snapshot_hash"], item["ownership_evidence_ref"])
        for item in entries
    ]
    if len(object_keys) != len(set(object_keys)):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_DUPLICATE_ENTRY", "observed active protection entries must be unique")
    observed["objects"] = entries
    expected_hash = active_protection_set_hash(observed)
    if observed["observed_set_hash"] != expected_hash:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_HASH_MISMATCH", "observed_set_hash does not match canonical complete set")
    return observed


def _validate_position(value: ProtectionRegistryMultiplicityInput) -> tuple[dict[str, Any], Decimal, str]:
    position = _canonicalize(value.position)
    if not isinstance(position, dict):
        raise ProtectionRegistryEvidenceError("POSITION_INVALID", "Position must be a mapping")
    for field in (
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "broker_state_observed_at",
        "reconciliation_status",
        "lifecycle_state",
    ):
        if field not in position:
            raise ProtectionRegistryEvidenceError("POSITION_INCOMPLETE", f"Position missing {field}")
    _text(value.position_ref, "position_ref")
    _text(position["position_id"], "Position.position_id")
    _text(position["symbol"], "Position.symbol")
    if position["side"] not in {"LONG", "SHORT"}:
        raise ProtectionRegistryEvidenceError("POSITION_SIDE_INVALID", "Position.side must be LONG or SHORT")
    quantity = _decimal(position["actual_quantity"], "Position.actual_quantity")
    if quantity < 0:
        raise ProtectionRegistryEvidenceError("POSITION_QUANTITY_INVALID", "Position.actual_quantity must be non-negative")
    observed_at = _utc_text(position["broker_state_observed_at"], "Position.broker_state_observed_at")
    return position, quantity, observed_at


def _lineage_matches_current(
    value: ProtectionRegistryMultiplicityInput,
    position: Mapping[str, Any],
    position_observed_at: str,
    lineage: Mapping[str, Any],
) -> tuple[bool, bool]:
    position_matches = (
        lineage["position_ref"] == value.position_ref
        and lineage["position_hash"] == canonical_protection_registry_hash(position)
        and lineage["position_id"] == position["position_id"]
        and lineage["position_observed_at"] == position_observed_at
        and lineage["position_side"] == position["side"]
    )

    lifecycle_matches = (
        lineage["lifecycle_projection_ref"] == value.lifecycle_projection_ref
        and lineage["lifecycle_execution_binding_ref"] == value.lifecycle_execution_binding_ref
    )
    runtime_matches = (
        lineage["runtime_preflight_ref"] == value.runtime_preflight_ref
        and lineage["runtime_process_instance_id"] == value.runtime_process_instance_id
        and lineage["runtime_process_start_generation_id"] == value.runtime_process_start_generation_id
        and lineage["runtime_config_generation_id"] == value.runtime_config_generation_id
    )
    return position_matches, lifecycle_matches and runtime_matches


def _validate_generation_currentness(value: ProtectionRegistryMultiplicityInput) -> None:
    if value.lifecycle_currentness_status not in _CURRENTNESS:
        raise ProtectionRegistryEvidenceError("LIFECYCLE_CURRENTNESS_INVALID", "lifecycle currentness unsupported")
    if value.runtime_currentness_status not in _CURRENTNESS:
        raise ProtectionRegistryEvidenceError("RUNTIME_CURRENTNESS_INVALID", "runtime currentness unsupported")
    runtime_values = (
        value.runtime_preflight_ref,
        value.runtime_process_instance_id,
        value.runtime_process_start_generation_id,
        value.runtime_config_generation_id,
    )
    if any(item is not None for item in runtime_values) and not all(item is not None for item in runtime_values):
        raise ProtectionRegistryEvidenceError("RUNTIME_GENERATION_INCOMPLETE", "runtime generation refs are all-or-none")
    for field, item in (
        ("lifecycle_projection_ref", value.lifecycle_projection_ref),
        ("lifecycle_execution_binding_ref", value.lifecycle_execution_binding_ref),
        ("runtime_preflight_ref", value.runtime_preflight_ref),
        ("runtime_process_instance_id", value.runtime_process_instance_id),
        ("runtime_process_start_generation_id", value.runtime_process_start_generation_id),
        ("runtime_config_generation_id", value.runtime_config_generation_id),
    ):
        _optional_text(item, field)


def _dependency_map(
    value: ProtectionRegistryMultiplicityInput,
    observed: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], set[str], set[str]]:
    dependencies: dict[str, FP04ActiveProtectionDependency] = {}
    for dependency in value.fp04_dependencies:
        if not isinstance(dependency, FP04ActiveProtectionDependency):
            raise ProtectionRegistryEvidenceError("FP04_DEPENDENCY_INVALID", "FP-04 dependencies must be typed")
        evidence = dependency.evidence
        try:
            validate_external_provider_ownership_evidence(evidence)
        except ExternalCloseReinterpretationError as exc:
            raise ProtectionRegistryEvidenceError("FP04_EVIDENCE_INVALID", exc.message) from exc
        evidence_ref = _text(evidence.get("ownership_evidence_id"), "ownership_evidence_id")
        if evidence_ref in dependencies:
            raise ProtectionRegistryEvidenceError("FP04_DEPENDENCY_DUPLICATE", "FP-04 dependency refs must be unique")
        dependencies[evidence_ref] = dependency

    entry_refs = {item["ownership_evidence_ref"] for item in observed["objects"]}
    if set(dependencies) != entry_refs:
        raise ProtectionRegistryEvidenceError(
            "FP04_DEPENDENCY_SET_MISMATCH",
            "every observed protection entry requires exactly one FP-04 dependency and no extras",
        )

    stale_refs: set[str] = set()
    unknown_refs: set[str] = set()
    normalized_by_ref: dict[str, Mapping[str, Any]] = {}
    for entry in observed["objects"]:
        ref = entry["ownership_evidence_ref"]
        dependency = dependencies[ref]
        evidence = dependency.evidence
        observation = dependency.observation
        if evidence.get("external_provider_ownership_profile_version") != FP04_PROFILE_VERSION:
            raise ProtectionRegistryEvidenceError("FP04_PROFILE_UNSUPPORTED", "FP-04 dependency profile unsupported")
        if evidence.get("provider_object_class") != ACTIVE_PROTECTION:
            raise ProtectionRegistryEvidenceError("FP04_OBJECT_CLASS_MISMATCH", "FP-11 admits only ACTIVE_PROTECTION FP-04 evidence")
        expected_evidence_hash = canonical_evidence_hash(evidence)
        if entry["ownership_evidence_hash"] != expected_evidence_hash:
            raise ProtectionRegistryEvidenceError("FP04_EVIDENCE_HASH_MISMATCH", "entry ownership_evidence_hash does not match FP-04 evidence")
        if entry["ownership_classification"] != evidence.get("ownership_classification"):
            raise ProtectionRegistryEvidenceError("FP04_CLASSIFICATION_MISMATCH", "entry ownership classification differs from FP-04 evidence")
        if entry["ownership_reconciliation_status"] != evidence.get("reconciliation_status"):
            raise ProtectionRegistryEvidenceError("FP04_RECONCILIATION_MISMATCH", "entry reconciliation status differs from FP-04 evidence")
        if (
            evidence.get("provider_identity_ref") != observed["provider_identity_ref"]
            or evidence.get("provider_identity_hash") != observed["provider_identity_hash"]
            or evidence.get("canonical_symbol") != observed["canonical_symbol"]
            or evidence.get("provider_instrument_ref") != observed["provider_instrument_ref"]
            or evidence.get("provider_observation_generation_id") != observed["provider_observation_generation_id"]
            or evidence.get("provider_object_ref") != entry["provider_object_ref"]
            or evidence.get("provider_snapshot_ref") != entry["provider_snapshot_ref"]
            or evidence.get("provider_snapshot_hash") != entry["provider_snapshot_hash"]
            or evidence.get("provider_observed_at") != entry["provider_object_observed_at"]
        ):
            raise ProtectionRegistryEvidenceError("FP04_PROVIDER_BINDING_MISMATCH", "FP-04 evidence does not bind exact observed provider protection object")
        if (
            observation.provider_object_class != ACTIVE_PROTECTION
            or observation.provider_object_ref != entry["provider_object_ref"]
            or observation.provider_snapshot_ref != entry["provider_snapshot_ref"]
            or canonical_evidence_hash(observation.provider_snapshot) != entry["provider_snapshot_hash"]
            or observation.provider_identity_ref != observed["provider_identity_ref"]
            or canonical_evidence_hash(observation.provider_identity) != observed["provider_identity_hash"]
            or observation.canonical_symbol != observed["canonical_symbol"]
            or observation.provider_instrument_ref != observed["provider_instrument_ref"]
            or observation.provider_observation_generation_id != observed["provider_observation_generation_id"]
        ):
            raise ProtectionRegistryEvidenceError("FP04_OBSERVATION_BINDING_MISMATCH", "FP-04 currentness observation differs from observed provider set")

        try:
            current = external_provider_ownership_evidence_is_current(
                evidence,
                observation,
                dependency.context,
            )
        except ExternalCloseEvidenceError:
            current = False
        if not current:
            stale_refs.add(ref)
        if evidence.get("ownership_classification") == OWNERSHIP_UNKNOWN or evidence.get("reconciliation_status") == UNKNOWN:
            unknown_refs.add(ref)
        normalized_by_ref[ref] = evidence
    return normalized_by_ref, stale_refs, unknown_refs


def _base_fail_closed_dispositions(*, uncertain_cleanup: bool = True) -> set[str]:
    values = {BLOCK_NEW_EXPOSURE, BLOCK_PROTECTION_CREATE_REPLACE}
    if uncertain_cleanup:
        values.add(BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL)
    return values


def _derive_state(
    value: ProtectionRegistryMultiplicityInput,
    position: Mapping[str, Any],
    quantity: Decimal,
    lineage: Mapping[str, Any],
    observed: Mapping[str, Any],
    fp04_by_ref: Mapping[str, Mapping[str, Any]],
    stale_fp04_refs: set[str],
    unknown_fp04_refs: set[str],
    *,
    position_matches: bool,
    generation_matches: bool,
) -> tuple[str, str, list[str], list[str]]:
    reasons: list[str] = []
    dispositions: set[str] = set()
    entries = observed["objects"]
    coverage = observed["observation_coverage_status"]
    set_currentness = observed["set_currentness_status"]

    if not position_matches:
        reasons.extend(["POSITION_REFERENCE_MISSING_OR_MISMATCHED", "INTENDED_PROTECTION_LINEAGE_MISMATCH"])
        dispositions.update(_base_fail_closed_dispositions())
        state = PROTECTION_SET_UNKNOWN
        status = REGISTRY_UNKNOWN
    elif value.lifecycle_currentness_status == STALE or value.runtime_currentness_status == STALE or not generation_matches:
        reasons.extend(["POSITION_EVIDENCE_STALE", "INTENDED_PROTECTION_LINEAGE_STALE"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_STALE
        status = PROVIDER_SET_REFRESH_REQUIRED
    elif value.lifecycle_currentness_status == UNKNOWN or value.runtime_currentness_status == UNKNOWN:
        reasons.extend(["INTENDED_PROTECTION_LINEAGE_STALE", "PROVIDER_PROTECTION_SET_UNKNOWN"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_UNKNOWN
        status = REGISTRY_UNKNOWN
    elif coverage == INCOMPLETE:
        reasons.extend(["PROVIDER_PROTECTION_OBSERVATION_INCOMPLETE", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_UNKNOWN
        status = PROVIDER_SET_REFRESH_REQUIRED
    elif coverage == UNKNOWN:
        reasons.extend(["PROVIDER_PROTECTION_SET_UNKNOWN", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_UNKNOWN
        status = PROVIDER_SET_REFRESH_REQUIRED
    elif set_currentness == STALE:
        reasons.extend(["PROVIDER_PROTECTION_SET_STALE", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_STALE
        status = PROVIDER_SET_REFRESH_REQUIRED
    elif set_currentness == UNKNOWN:
        reasons.extend(["PROVIDER_PROTECTION_SET_UNKNOWN", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_UNKNOWN
        status = PROVIDER_SET_REFRESH_REQUIRED
    elif stale_fp04_refs:
        reasons.extend(["PROTECTION_OWNERSHIP_EVIDENCE_STALE", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
        dispositions.update(_base_fail_closed_dispositions())
        dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
        state = PROTECTION_SET_STALE
        status = PROVIDER_SET_REFRESH_REQUIRED
    else:
        conflict_entries = [
            entry
            for entry in entries
            if fp04_by_ref[entry["ownership_evidence_ref"]].get("ownership_classification")
            == CONFLICTING_OWNERSHIP_EVIDENCE
        ]
        if conflict_entries:
            reasons.extend(
                [
                    "PROTECTION_OWNERSHIP_CONFLICT_PRESENT",
                    "PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED",
                ]
            )
            dispositions.update(_base_fail_closed_dispositions())
            dispositions.add(OWNERSHIP_MANUAL_REVIEW_REQUIRED)
            state = OWNERSHIP_CONFLICT_PRESENT
            status = OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED
        elif len(entries) == 0:
            reasons.extend(["NO_ACTIVE_PROTECTION_OBSERVED", "E5_PROTECTION_REINTERPRETATION_REQUIRED"])
            dispositions.update({
                E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED,
                BLOCK_NEW_EXPOSURE,
                BLOCK_PROTECTION_CREATE_REPLACE,
            })
            state = NO_ACTIVE_PROTECTION_OBSERVED
            status = MISSING_PROTECTION_REINTERPRETATION_REQUIRED
        elif len(entries) >= 2:
            reasons.extend(
                [
                    "MULTIPLE_ACTIVE_PROTECTIONS_OBSERVED",
                    "PROTECTION_MULTIPLICITY_CONVERGENCE_REQUIRED",
                ]
            )
            dispositions.update(_base_fail_closed_dispositions())
            dispositions.add(MULTIPLICITY_CONVERGENCE_DISPOSITION)
            if any(
                fp04_by_ref[entry["ownership_evidence_ref"]].get("ownership_classification")
                in {EXTERNAL_UNTRACKED, KNOWN_OWNED_PRIOR_GENERATION}
                or entry["intended_lineage_binding_status"] != EXACT_MATCH
                for entry in entries
            ):
                reasons.append("EXTERNAL_OR_ORPHAN_PROTECTION_PRESENT")
                dispositions.add(ORPHAN_EXTERNAL_RECONCILIATION_DISPOSITION)
            if any(
                fp04_by_ref[entry["ownership_evidence_ref"]].get("ownership_classification")
                == KNOWN_OWNED_PRIOR_GENERATION
                for entry in entries
            ):
                reasons.append("PRIOR_GENERATION_PROTECTION_PRESENT")
            if unknown_fp04_refs or any(entry["intended_lineage_binding_status"] == UNKNOWN for entry in entries):
                reasons.append("PROTECTION_OWNERSHIP_EVIDENCE_MISSING")
                dispositions.add(OWNERSHIP_MANUAL_REVIEW_REQUIRED)
            state = MULTIPLE_ACTIVE_PROTECTIONS
            status = MULTIPLICITY_CONVERGENCE_REQUIRED
        else:
            entry = entries[0]
            fp04 = fp04_by_ref[entry["ownership_evidence_ref"]]
            classification = fp04.get("ownership_classification")
            reconciliation = fp04.get("reconciliation_status")
            binding = entry["intended_lineage_binding_status"]
            if unknown_fp04_refs or binding == UNKNOWN:
                reasons.extend(["PROTECTION_OWNERSHIP_EVIDENCE_MISSING", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"])
                dispositions.update(_base_fail_closed_dispositions())
                dispositions.add(REFRESH_PROVIDER_PROTECTION_SET_REQUIRED)
                state = PROTECTION_SET_UNKNOWN
                status = REGISTRY_UNKNOWN
            elif (
                classification == KNOWN_OWNED_CURRENT_GENERATION
                and reconciliation == CURRENT_KNOWN_OWNED
                and fp04.get("required_dispositions") == [NO_ACTION_CURRENT_KNOWN_OWNED]
                and binding == EXACT_MATCH
            ):
                state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
                status = CONVERGED_EXACTLY_ONE_INTENDED
                dispositions = {NO_ACTION_REGISTRY_CONVERGED}
                reasons = ["EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"]
            else:
                reasons.append("EXTERNAL_OR_ORPHAN_PROTECTION_PRESENT")
                dispositions.update(_base_fail_closed_dispositions())
                dispositions.add(ORPHAN_EXTERNAL_RECONCILIATION_DISPOSITION)
                if classification == KNOWN_OWNED_PRIOR_GENERATION:
                    reasons.append("PRIOR_GENERATION_PROTECTION_PRESENT")
                if binding == NOT_MATCH:
                    reasons.append("INTENDED_PROTECTION_OBJECT_IDENTITY_MISMATCH")
                state = ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT
                status = ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED

    terminal_or_flat = quantity == 0 or position.get("lifecycle_state") == "CLOSED"
    if terminal_or_flat and entries:
        if status == CONVERGED_EXACTLY_ONE_INTENDED:
            status = LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED
            dispositions = _base_fail_closed_dispositions()
            reasons = ["LIFECYCLE_PROTECTION_STATE_CONTRADICTION", "FRESH_PROTECTION_RECONCILIATION_REQUIRED"]
        else:
            dispositions.update(_base_fail_closed_dispositions())
            if "LIFECYCLE_PROTECTION_STATE_CONTRADICTION" not in reasons:
                reasons.append("LIFECYCLE_PROTECTION_STATE_CONTRADICTION")
        dispositions.add(FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED)

    if status != CONVERGED_EXACTLY_ONE_INTENDED and position.get("lifecycle_state") in _PROTECTED_LIFECYCLE_STATES:
        dispositions.add(LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED)
        if "LIFECYCLE_PROTECTION_STATE_CONTRADICTION" not in reasons:
            reasons.append("LIFECYCLE_PROTECTION_STATE_CONTRADICTION")

    return state, status, _sorted_dispositions(dispositions), _sorted_reasons(reasons)


def _evidence_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("protection_registry_evidence_id", None)
    digest = hashlib.sha256(canonical_protection_registry_json(material).encode("utf-8")).hexdigest()
    return "protregmul_" + digest


def _same_logical_lineage(old: Mapping[str, Any], new_lineage: Mapping[str, Any], position_id: str) -> bool:
    old_lineage = old.get("intended_protection_lineage")
    if not isinstance(old_lineage, Mapping):
        return False
    return (
        old.get("position_id") == position_id
        and old_lineage.get("position_action_id") == new_lineage.get("position_action_id")
        and old_lineage.get("approved_trade_plan_ref") == new_lineage.get("approved_trade_plan_ref")
        and old_lineage.get("protection_order_request_ref") == new_lineage.get("protection_order_request_ref")
        and old_lineage.get("client_order_identity_ref") == new_lineage.get("client_order_identity_ref")
    )


def _material_without_refresh_fields(evidence: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(evidence)
    for field in (
        "protection_registry_evidence_id",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    ):
        material.pop(field, None)
    return material


def build_protection_registry_multiplicity_evidence(
    value: ProtectionRegistryMultiplicityInput,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce immutable provider-neutral FP-11 evidence from supplied facts only."""

    if not isinstance(value, ProtectionRegistryMultiplicityInput):
        raise ProtectionRegistryEvidenceError("INPUT_TYPE_INVALID", "FP-11 requires ProtectionRegistryMultiplicityInput")
    _validate_generation_currentness(value)
    position, quantity, position_observed_at = _validate_position(value)
    lineage = _normalize_intended_lineage(value.intended_protection_lineage)
    observed = _normalize_observed_set(value.observed_active_protection_set)
    if observed["canonical_symbol"] != position["symbol"]:
        raise ProtectionRegistryEvidenceError("POSITION_PROVIDER_SYMBOL_MISMATCH", "provider set canonical symbol differs from Position")

    position_matches, generation_matches = _lineage_matches_current(
        value,
        position,
        position_observed_at,
        lineage,
    )
    fp04_by_ref, stale_fp04_refs, unknown_fp04_refs = _dependency_map(value, observed)

    evaluated_at = _utc_text(value.evaluated_at, "evaluated_at")
    evaluation_dt = _utc_dt(evaluated_at, "evaluated_at")
    required_times = [
        _utc_dt(position_observed_at, "position_observed_at"),
        _utc_dt(observed["provider_received_at"], "provider_received_at"),
    ]
    for entry in observed["objects"]:
        required_times.append(_utc_dt(entry["provider_object_observed_at"], "provider_object_observed_at"))
        fp04 = fp04_by_ref[entry["ownership_evidence_ref"]]
        required_times.append(_utc_dt(fp04["evaluated_at"], "fp04.evaluated_at"))
    if any(evaluation_dt < item for item in required_times):
        raise ProtectionRegistryEvidenceError("EVALUATION_TEMPORAL_ORDER_INVALID", "evaluated_at predates bound evidence")

    state, status, dispositions, reasons = _derive_state(
        value,
        position,
        quantity,
        lineage,
        observed,
        fp04_by_ref,
        stale_fp04_refs,
        unknown_fp04_refs,
        position_matches=position_matches,
        generation_matches=generation_matches,
    )

    supersedes_id = None
    if supersedes_evidence is not None:
        validate_protection_registry_multiplicity_evidence(supersedes_evidence)
        if not _same_logical_lineage(supersedes_evidence, lineage, position["position_id"]):
            raise ProtectionRegistryEvidenceError(
                "SUPERSESSION_LINEAGE_MISMATCH",
                "supersession must remain within the same logical Position/intended-protection lineage",
            )
        if evaluation_dt < _utc_dt(supersedes_evidence["evaluated_at"], "superseded.evaluated_at"):
            raise ProtectionRegistryEvidenceError("SUPERSESSION_TIME_REVERSED", "superseding evidence cannot evaluate earlier")
        supersedes_id = supersedes_evidence["protection_registry_evidence_id"]

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protection_registry_multiplicity_profile_version": PROFILE_VERSION,
        "position_id": position["position_id"],
        "position_ref": value.position_ref,
        "position_hash": canonical_protection_registry_hash(position),
        "position_observed_at": position_observed_at,
        "intended_protection_lineage": lineage,
        "intended_protection_lineage_hash": canonical_protection_registry_hash(lineage),
        "provider_identity_ref": observed["provider_identity_ref"],
        "provider_instrument_ref": observed["provider_instrument_ref"],
        "provider_observation_generation_id": observed["provider_observation_generation_id"],
        "provider_observed_at": observed["provider_observed_at"],
        "provider_received_at": observed["provider_received_at"],
        "observation_coverage_status": observed["observation_coverage_status"],
        "provider_set_currentness_status": observed["set_currentness_status"],
        "observed_active_protection_objects": observed["objects"],
        "observed_active_protection_set_hash": observed["observed_set_hash"],
        "active_protection_count": len(observed["objects"]),
        "runtime_preflight_ref": value.runtime_preflight_ref,
        "runtime_process_instance_id": value.runtime_process_instance_id,
        "runtime_process_start_generation_id": value.runtime_process_start_generation_id,
        "runtime_config_generation_id": value.runtime_config_generation_id,
        "lifecycle_projection_ref": value.lifecycle_projection_ref,
        "lifecycle_execution_binding_ref": value.lifecycle_execution_binding_ref,
        "multiplicity_state": state,
        "registry_status": status,
        "required_dispositions": dispositions,
        "reason_codes": reasons,
        "supersedes_registry_evidence_id": supersedes_id,
        "evaluated_at": evaluated_at,
    }
    payload["protection_registry_evidence_id"] = _evidence_id(payload)
    validate_protection_registry_multiplicity_evidence(payload)

    if supersedes_evidence is not None:
        if _material_without_refresh_fields(supersedes_evidence) == _material_without_refresh_fields(payload):
            raise ProtectionRegistryEvidenceError(
                "SUPERSESSION_REQUIRES_MATERIAL_CHANGE",
                "evaluated_at alone cannot justify FP-11 supersession",
            )
    return payload


def _set_hash_from_evidence(evidence: Mapping[str, Any]) -> str:
    material = {
        "provider_identity_ref": evidence["provider_identity_ref"],
        "provider_instrument_ref": evidence["provider_instrument_ref"],
        "provider_observation_generation_id": evidence["provider_observation_generation_id"],
        "provider_observed_at": evidence["provider_observed_at"],
        "observation_coverage_status": evidence["observation_coverage_status"],
        "provider_set_currentness_status": evidence["provider_set_currentness_status"],
        "objects": evidence["observed_active_protection_objects"],
    }
    return canonical_protection_registry_hash(material)


def validate_protection_registry_multiplicity_evidence(evidence: Mapping[str, Any]) -> None:
    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        raise ProtectionRegistryEvidenceError("EVIDENCE_FIELDS_INVALID", "ProtectionRegistryMultiplicityEvidence fields mismatch")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionRegistryEvidenceError("SCHEMA_VERSION_UNSUPPORTED", "schema_version unsupported")
    if evidence.get("protection_registry_multiplicity_profile_version") != PROFILE_VERSION:
        raise ProtectionRegistryEvidenceError("PROTECTION_REGISTRY_PROFILE_UNSUPPORTED", "FP-11 profile unsupported")
    evidence_id = evidence.get("protection_registry_evidence_id")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None:
        raise ProtectionRegistryEvidenceError("PROTECTION_REGISTRY_EVIDENCE_IDENTITY_INVALID", "evidence id invalid")
    if evidence_id != _evidence_id(evidence):
        raise ProtectionRegistryEvidenceError("PROTECTION_REGISTRY_EVIDENCE_IDENTITY_INVALID", "evidence id does not match canonical payload")

    for field in (
        "position_id",
        "position_ref",
        "provider_identity_ref",
        "provider_instrument_ref",
        "provider_observation_generation_id",
    ):
        _text(evidence[field], field)
    for field in ("position_hash", "intended_protection_lineage_hash", "observed_active_protection_set_hash"):
        _hash(evidence[field], field)
    _utc_text(evidence["position_observed_at"], "position_observed_at")
    _utc_text(evidence["provider_observed_at"], "provider_observed_at")
    _utc_text(evidence["provider_received_at"], "provider_received_at")
    _utc_text(evidence["evaluated_at"], "evaluated_at")
    if _utc_dt(evidence["provider_received_at"], "provider_received_at") < _utc_dt(
        evidence["provider_observed_at"], "provider_observed_at"
    ):
        raise ProtectionRegistryEvidenceError("EVIDENCE_TEMPORAL_ORDER_INVALID", "provider receipt precedes observation")

    lineage = _normalize_intended_lineage(evidence["intended_protection_lineage"])
    if canonical_protection_registry_hash(lineage) != evidence["intended_protection_lineage_hash"]:
        raise ProtectionRegistryEvidenceError("INTENDED_LINEAGE_HASH_MISMATCH", "intended lineage hash invalid")
    entries_raw = evidence["observed_active_protection_objects"]
    if isinstance(entries_raw, (str, bytes)) or not isinstance(entries_raw, Sequence):
        raise ProtectionRegistryEvidenceError("EVIDENCE_ENTRIES_INVALID", "observed entries must be a sequence")
    entries = [_normalize_entry(item) for item in entries_raw]
    sorted_entries = sorted(
        entries,
        key=lambda item: (
            item["provider_object_ref"],
            item["provider_snapshot_hash"],
            item["ownership_evidence_ref"],
        ),
    )
    if entries != sorted_entries:
        raise ProtectionRegistryEvidenceError("EVIDENCE_ENTRY_ORDER_INVALID", "observed entries must be canonical sorted order")
    if evidence["active_protection_count"] != len(entries):
        raise ProtectionRegistryEvidenceError("ACTIVE_PROTECTION_COUNT_MISMATCH", "active_protection_count must equal observed set length")
    if evidence["observed_active_protection_set_hash"] != _set_hash_from_evidence(evidence):
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_HASH_MISMATCH", "evidence set hash invalid")

    if evidence["observation_coverage_status"] not in _COVERAGE:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_COVERAGE_INVALID", "coverage unsupported")
    if evidence["provider_set_currentness_status"] not in _CURRENTNESS:
        raise ProtectionRegistryEvidenceError("OBSERVED_SET_CURRENTNESS_INVALID", "set currentness unsupported")
    if evidence["multiplicity_state"] not in _MULTIPLICITY_STATES:
        raise ProtectionRegistryEvidenceError("MULTIPLICITY_STATE_INVALID", "multiplicity state unsupported")
    if evidence["registry_status"] not in _REGISTRY_STATUSES:
        raise ProtectionRegistryEvidenceError("REGISTRY_STATUS_INVALID", "registry status unsupported")
    dispositions = evidence["required_dispositions"]
    reasons = evidence["reason_codes"]
    if not isinstance(dispositions, list) or dispositions != _sorted_dispositions(dispositions):
        raise ProtectionRegistryEvidenceError("DISPOSITION_ORDER_INVALID", "required_dispositions must be deterministic")
    if not isinstance(reasons, list) or not reasons or reasons != _sorted_reasons(reasons):
        raise ProtectionRegistryEvidenceError("REASON_ORDER_INVALID", "reason_codes must be deterministic and non-empty")

    success = (
        evidence["multiplicity_state"] == EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
        and evidence["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED
    )
    if success:
        if evidence["active_protection_count"] != 1:
            raise ProtectionRegistryEvidenceError("FALSE_REGISTRY_CONVERGENCE", "converged registry requires exactly one active protection")
        if dispositions != [NO_ACTION_REGISTRY_CONVERGED]:
            raise ProtectionRegistryEvidenceError("FALSE_REGISTRY_CONVERGENCE", "converged registry requires exclusive no-action disposition")
        if reasons != ["EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"]:
            raise ProtectionRegistryEvidenceError("FALSE_REGISTRY_CONVERGENCE", "converged registry requires exact success reason")
        entry = entries[0]
        if (
            entry["ownership_classification"] != KNOWN_OWNED_CURRENT_GENERATION
            or entry["ownership_reconciliation_status"] != CURRENT_KNOWN_OWNED
            or entry["intended_lineage_binding_status"] != EXACT_MATCH
            or evidence["observation_coverage_status"] != COMPLETE
            or evidence["provider_set_currentness_status"] != CURRENT
        ):
            raise ProtectionRegistryEvidenceError("FALSE_REGISTRY_CONVERGENCE", "success tuple lacks exact section-8 invariants")
    elif evidence["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED:
        raise ProtectionRegistryEvidenceError("FALSE_REGISTRY_CONVERGENCE", "only exact-one intended state may be converged")

    supersedes = evidence["supersedes_registry_evidence_id"]
    if supersedes is not None and (not isinstance(supersedes, str) or _ID_RE.fullmatch(supersedes) is None):
        raise ProtectionRegistryEvidenceError("SUPERSESSION_ID_INVALID", "supersedes_registry_evidence_id invalid")


def protection_registry_multiplicity_evidence_is_current(
    evidence: Mapping[str, Any],
    current_input: ProtectionRegistryMultiplicityInput,
) -> bool:
    """Return material currentness; evaluated_at alone is intentionally ignored."""

    try:
        validate_protection_registry_multiplicity_evidence(evidence)
        fresh = build_protection_registry_multiplicity_evidence(current_input)
    except ProtectionRegistryEvidenceError:
        return False
    ignored = {
        "protection_registry_evidence_id",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    }
    return all(evidence.get(field) == fresh.get(field) for field in _EVIDENCE_FIELDS if field not in ignored)
