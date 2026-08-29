from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

from .lifecycle_execution_binding import (
    LifecycleExecutionBindingError,
    validate_position_lifecycle_execution_evidence_binding,
)
from .lifecycle_projection import LifecycleProjectionError, validate_position_lifecycle_projection
from .state_machine import PositionEvent, PositionLifecycleState, UnsafeTransitionError, transition

SCHEMA_VERSION = "contracts-v0.1"
FP11_PROFILE_VERSION = "protection-registry-multiplicity-v0.1"

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
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED = (
    "FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED"
)

DECISION_PRESERVE_PROTECTED = "PRESERVE_PROTECTED"
DECISION_PROTECTION_LOST = "PROTECTION_LOST"
DECISION_RECONCILE = "RECONCILE"
DECISION_HOLD_SAFE = "HOLD_SAFE"

CURRENT = "CURRENT"
COMPLETE = "COMPLETE"
EXACT_MATCH = "EXACT_MATCH"
KNOWN_OWNED_CURRENT_GENERATION = "KNOWN_OWNED_CURRENT_GENERATION"
CURRENT_KNOWN_OWNED = "CURRENT_KNOWN_OWNED"

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
        "E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED",
        "MULTIPLICITY_CONVERGENCE_REQUIRED",
        "ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED",
        "OWNERSHIP_MANUAL_REVIEW_REQUIRED",
        "REFRESH_PROVIDER_PROTECTION_SET_REQUIRED",
        "BLOCK_NEW_EXPOSURE",
        "BLOCK_PROTECTION_CREATE_REPLACE",
        "BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL",
        "LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED",
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
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^protregmul_[0-9a-f]{64}$")


class ProtectionRegistryPolicyError(ValueError):
    """Fail-closed E5 FP-11 consumer error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CurrentProtectionRegistryAuthority:
    """Exact current material required to interpret one immutable FP-11 object."""

    position_ref: str
    position_hash: str
    position: Mapping[str, Any]
    lifecycle_projection: Mapping[str, Any]
    lifecycle_execution_binding: Mapping[str, Any] | None
    provider_identity_ref: str
    provider_instrument_ref: str
    provider_observation_generation_id: str
    provider_observed_at: str
    provider_received_at: str
    observed_active_protection_set_hash: str
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None


@dataclass(frozen=True)
class ProtectionRegistryPolicyDecision:
    """E5-internal policy interpretation; never provider mutation authority."""

    decision_id: str
    decision: str
    event: PositionEvent | None
    next_state: PositionLifecycleState
    reason_codes: tuple[str, ...]
    source_required_dispositions: tuple[str, ...]
    source_reason_codes: tuple[str, ...]
    source_registry_evidence_id: str | None
    source_registry_evidence_hash: str | None
    source_registry_material_hash: str | None
    healthy_protection: bool
    terminal_close_dependency: bool
    provider_mutation_authorized: bool
    cleanup_target_ref: None
    evidence_current: bool


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ProtectionRegistryPolicyError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ProtectionRegistryPolicyError("NONCANONICAL_TIMESTAMP", "datetime must be UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, float):
        raise ProtectionRegistryPolicyError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtectionRegistryPolicyError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise ProtectionRegistryPolicyError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical type: {type(value).__name__}",
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_protection_registry_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _evidence_id(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    material.pop("protection_registry_evidence_id", None)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "protregmul_" + digest


def _material_hash(evidence: Mapping[str, Any]) -> str:
    material = dict(evidence)
    for field in (
        "protection_registry_evidence_id",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    ):
        material.pop(field, None)
    return canonical_protection_registry_hash(material)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProtectionRegistryPolicyError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _hash(value: Any, field: str) -> str:
    value = _text(value, field)
    if _HASH_RE.fullmatch(value) is None:
        raise ProtectionRegistryPolicyError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return value


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtectionRegistryPolicyError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionRegistryPolicyError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionRegistryPolicyError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _quantity(position: Mapping[str, Any]) -> Decimal:
    value = position.get("actual_quantity")
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ProtectionRegistryPolicyError("POSITION_QUANTITY_INVALID", "actual_quantity is invalid") from exc
    else:
        raise ProtectionRegistryPolicyError("POSITION_QUANTITY_INVALID", "actual_quantity must be decimal text")
    if not parsed.is_finite() or parsed < 0:
        raise ProtectionRegistryPolicyError("POSITION_QUANTITY_INVALID", "actual_quantity must be finite and non-negative")
    return parsed


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


def validate_fp11_registry_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate the shared FP-11 immutable object without importing E4 policy code."""

    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        raise ProtectionRegistryPolicyError("FP11_FIELDS_INVALID", "FP-11 evidence fields mismatch")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionRegistryPolicyError("FP11_SCHEMA_UNSUPPORTED", "FP-11 schema_version is unsupported")
    if evidence.get("protection_registry_multiplicity_profile_version") != FP11_PROFILE_VERSION:
        raise ProtectionRegistryPolicyError("FP11_PROFILE_UNSUPPORTED", "FP-11 profile is unsupported")

    evidence_id = evidence.get("protection_registry_evidence_id")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None or evidence_id != _evidence_id(evidence):
        raise ProtectionRegistryPolicyError("FP11_IDENTITY_INVALID", "FP-11 evidence identity is invalid")

    for field in (
        "position_id",
        "position_ref",
        "provider_identity_ref",
        "provider_instrument_ref",
        "provider_observation_generation_id",
    ):
        _text(evidence.get(field), field)
    for field in (
        "position_hash",
        "intended_protection_lineage_hash",
        "observed_active_protection_set_hash",
    ):
        _hash(evidence.get(field), field)

    position_observed_at = _utc(evidence.get("position_observed_at"), "position_observed_at")
    provider_observed_at = _utc(evidence.get("provider_observed_at"), "provider_observed_at")
    provider_received_at = _utc(evidence.get("provider_received_at"), "provider_received_at")
    evaluated_at = _utc(evidence.get("evaluated_at"), "evaluated_at")
    if provider_received_at < provider_observed_at:
        raise ProtectionRegistryPolicyError("FP11_TIME_INVALID", "provider receipt precedes observation")
    if evaluated_at < max(position_observed_at, provider_received_at):
        raise ProtectionRegistryPolicyError("FP11_TIME_INVALID", "evaluation predates bound current evidence")

    lineage = evidence.get("intended_protection_lineage")
    if not isinstance(lineage, Mapping) or set(lineage) != _INTENDED_LINEAGE_FIELDS:
        raise ProtectionRegistryPolicyError("FP11_LINEAGE_INVALID", "intended protection lineage fields mismatch")
    if canonical_protection_registry_hash(lineage) != evidence["intended_protection_lineage_hash"]:
        raise ProtectionRegistryPolicyError("FP11_LINEAGE_HASH_INVALID", "intended protection lineage hash mismatch")
    if (
        lineage.get("position_ref") != evidence["position_ref"]
        or lineage.get("position_hash") != evidence["position_hash"]
        or lineage.get("position_id") != evidence["position_id"]
        or lineage.get("position_observed_at") != evidence["position_observed_at"]
        or lineage.get("lifecycle_projection_ref") != evidence["lifecycle_projection_ref"]
        or lineage.get("lifecycle_execution_binding_ref") != evidence["lifecycle_execution_binding_ref"]
        or lineage.get("runtime_preflight_ref") != evidence["runtime_preflight_ref"]
        or lineage.get("runtime_process_instance_id") != evidence["runtime_process_instance_id"]
        or lineage.get("runtime_process_start_generation_id") != evidence["runtime_process_start_generation_id"]
        or lineage.get("runtime_config_generation_id") != evidence["runtime_config_generation_id"]
    ):
        raise ProtectionRegistryPolicyError("FP11_LINEAGE_BINDING_INVALID", "FP-11 lineage does not bind outer evidence")

    entries = evidence.get("observed_active_protection_objects")
    if isinstance(entries, (str, bytes)) or not isinstance(entries, Sequence):
        raise ProtectionRegistryPolicyError("FP11_OBJECT_SET_INVALID", "observed active protection objects must be a sequence")
    normalized_entries: list[Mapping[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != _ENTRY_FIELDS:
            raise ProtectionRegistryPolicyError("FP11_OBJECT_ENTRY_INVALID", "observed protection entry fields mismatch")
        for field in (
            "provider_object_ref",
            "provider_snapshot_ref",
            "ownership_evidence_ref",
            "ownership_classification",
            "ownership_reconciliation_status",
            "intended_lineage_binding_status",
        ):
            _text(entry.get(field), f"entry.{field}")
        for field in ("provider_snapshot_hash", "ownership_evidence_hash"):
            _hash(entry.get(field), f"entry.{field}")
        _utc(entry.get("provider_object_observed_at"), "entry.provider_object_observed_at")
        binding_status = entry.get("intended_lineage_binding_status")
        if binding_status not in {EXACT_MATCH, "NOT_MATCH", "UNKNOWN"}:
            raise ProtectionRegistryPolicyError("FP11_LINEAGE_BINDING_STATUS_INVALID", "unsupported lineage binding status")
        binding_ref = entry.get("intended_lineage_binding_ref")
        binding_hash = entry.get("intended_lineage_binding_hash")
        if binding_status == "UNKNOWN":
            if binding_ref is not None or binding_hash is not None:
                raise ProtectionRegistryPolicyError("FP11_LINEAGE_BINDING_INVALID", "UNKNOWN binding requires null ref/hash")
        else:
            _text(binding_ref, "entry.intended_lineage_binding_ref")
            _hash(binding_hash, "entry.intended_lineage_binding_hash")
        normalized_entries.append(entry)

    sorted_entries = sorted(
        normalized_entries,
        key=lambda item: (
            item["provider_object_ref"],
            item["provider_snapshot_hash"],
            item["ownership_evidence_ref"],
        ),
    )
    if list(normalized_entries) != sorted_entries:
        raise ProtectionRegistryPolicyError("FP11_OBJECT_SET_ORDER_INVALID", "observed object set is not canonical sorted order")
    if evidence.get("active_protection_count") != len(normalized_entries):
        raise ProtectionRegistryPolicyError("FP11_OBJECT_COUNT_INVALID", "active protection count mismatch")
    if evidence["observed_active_protection_set_hash"] != _set_hash_from_evidence(evidence):
        raise ProtectionRegistryPolicyError("FP11_OBJECT_SET_HASH_INVALID", "observed active protection set hash mismatch")

    if evidence.get("observation_coverage_status") not in {COMPLETE, "INCOMPLETE", "UNKNOWN"}:
        raise ProtectionRegistryPolicyError("FP11_COVERAGE_INVALID", "unsupported provider observation coverage")
    if evidence.get("provider_set_currentness_status") not in {CURRENT, "STALE", "UNKNOWN"}:
        raise ProtectionRegistryPolicyError("FP11_CURRENTNESS_INVALID", "unsupported provider set currentness")
    if evidence.get("multiplicity_state") not in _MULTIPLICITY_STATES:
        raise ProtectionRegistryPolicyError("FP11_MULTIPLICITY_STATE_INVALID", "unsupported multiplicity state")
    if evidence.get("registry_status") not in _REGISTRY_STATUSES:
        raise ProtectionRegistryPolicyError("FP11_REGISTRY_STATUS_INVALID", "unsupported registry status")

    dispositions = evidence.get("required_dispositions")
    if not isinstance(dispositions, list) or not dispositions or any(item not in _DISPOSITIONS for item in dispositions):
        raise ProtectionRegistryPolicyError("FP11_DISPOSITION_INVALID", "unsupported/empty FP-11 disposition set")
    if dispositions != sorted(set(dispositions)):
        raise ProtectionRegistryPolicyError("FP11_DISPOSITION_ORDER_INVALID", "FP-11 dispositions must be sorted and unique")
    if NO_ACTION_REGISTRY_CONVERGED in dispositions and dispositions != [NO_ACTION_REGISTRY_CONVERGED]:
        raise ProtectionRegistryPolicyError("FP11_FALSE_NO_ACTION", "NO_ACTION_REGISTRY_CONVERGED is exclusive")

    reasons = evidence.get("reason_codes")
    if not isinstance(reasons, list) or not reasons or any(item not in _REASON_INDEX for item in reasons):
        raise ProtectionRegistryPolicyError("FP11_REASON_INVALID", "unsupported/empty FP-11 reason set")
    if reasons != sorted(set(reasons), key=_REASON_INDEX.__getitem__):
        raise ProtectionRegistryPolicyError("FP11_REASON_ORDER_INVALID", "FP-11 reasons are not deterministic")

    success = (
        evidence["multiplicity_state"] == EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
        and evidence["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED
    )
    if success:
        if (
            evidence["active_protection_count"] != 1
            or dispositions != [NO_ACTION_REGISTRY_CONVERGED]
            or reasons != ["EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"]
            or evidence["observation_coverage_status"] != COMPLETE
            or evidence["provider_set_currentness_status"] != CURRENT
        ):
            raise ProtectionRegistryPolicyError("FP11_FALSE_CONVERGENCE", "FP-11 success tuple is incomplete")
        entry = normalized_entries[0]
        if (
            entry["ownership_classification"] != KNOWN_OWNED_CURRENT_GENERATION
            or entry["ownership_reconciliation_status"] != CURRENT_KNOWN_OWNED
            or entry["intended_lineage_binding_status"] != EXACT_MATCH
        ):
            raise ProtectionRegistryPolicyError("FP11_FALSE_CONVERGENCE", "FP-11 success object lacks exact ownership/lineage")
    elif evidence["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED:
        raise ProtectionRegistryPolicyError("FP11_FALSE_CONVERGENCE", "only exact-one intended state may converge")

    supersedes = evidence.get("supersedes_registry_evidence_id")
    if supersedes is not None and (not isinstance(supersedes, str) or _ID_RE.fullmatch(supersedes) is None):
        raise ProtectionRegistryPolicyError("FP11_SUPERSESSION_INVALID", "invalid supersedes_registry_evidence_id")


def _validate_current_authority(authority: CurrentProtectionRegistryAuthority) -> tuple[dict[str, Any], str | None]:
    if not isinstance(authority, CurrentProtectionRegistryAuthority):
        raise ProtectionRegistryPolicyError("CURRENT_AUTHORITY_INVALID", "current authority must be typed")
    if not isinstance(authority.position, Mapping):
        raise ProtectionRegistryPolicyError("CURRENT_POSITION_INVALID", "current Position must be a mapping")
    _text(authority.position_ref, "current.position_ref")
    if authority.position_hash != canonical_protection_registry_hash(authority.position):
        raise ProtectionRegistryPolicyError("CURRENT_POSITION_HASH_INVALID", "current Position hash is invalid")
    if authority.position.get("position_id") is None or authority.position.get("broker_state_observed_at") is None:
        raise ProtectionRegistryPolicyError("CURRENT_POSITION_INCOMPLETE", "current Position identity/observation is missing")
    _quantity(authority.position)

    try:
        projection_facts = validate_position_lifecycle_projection(authority.lifecycle_projection)
    except LifecycleProjectionError as exc:
        raise ProtectionRegistryPolicyError("CURRENT_LIFECYCLE_INVALID", exc.message) from exc
    if (
        authority.lifecycle_projection.get("position_id") != authority.position.get("position_id")
        or authority.lifecycle_projection.get("broker_state_observed_at") != authority.position.get("broker_state_observed_at")
        or authority.lifecycle_projection.get("lifecycle_state") != authority.position.get("lifecycle_state")
    ):
        raise ProtectionRegistryPolicyError("CURRENT_POSITION_LIFECYCLE_MISMATCH", "current Position and lifecycle projection disagree")

    binding_id: str | None = None
    if authority.lifecycle_execution_binding is not None:
        try:
            validate_position_lifecycle_execution_evidence_binding(
                authority.lifecycle_execution_binding,
                authority.lifecycle_projection,
            )
        except LifecycleExecutionBindingError as exc:
            raise ProtectionRegistryPolicyError("CURRENT_EXECUTION_BINDING_INVALID", exc.message) from exc
        binding_id = authority.lifecycle_execution_binding.get("lifecycle_execution_binding_id")

    for field, value in (
        ("provider_identity_ref", authority.provider_identity_ref),
        ("provider_instrument_ref", authority.provider_instrument_ref),
        ("provider_observation_generation_id", authority.provider_observation_generation_id),
    ):
        _text(value, f"current.{field}")
    _utc(authority.provider_observed_at, "current.provider_observed_at")
    _utc(authority.provider_received_at, "current.provider_received_at")
    _hash(authority.observed_active_protection_set_hash, "current.observed_active_protection_set_hash")

    runtime = (
        authority.runtime_preflight_ref,
        authority.runtime_process_instance_id,
        authority.runtime_process_start_generation_id,
        authority.runtime_config_generation_id,
    )
    if any(item is not None for item in runtime) and not all(item is not None for item in runtime):
        raise ProtectionRegistryPolicyError("CURRENT_RUNTIME_GENERATION_INCOMPLETE", "runtime generation is all-or-none")
    return projection_facts, binding_id


def fp11_registry_evidence_is_current(
    evidence: Mapping[str, Any],
    authority: CurrentProtectionRegistryAuthority,
) -> bool:
    """Check exact material currentness; evaluated_at is intentionally not a refresh axis."""

    try:
        validate_fp11_registry_evidence(evidence)
        projection_facts, binding_id = _validate_current_authority(authority)
    except ProtectionRegistryPolicyError:
        return False

    if evidence.get("provider_set_currentness_status") != CURRENT:
        return False
    position = authority.position
    lineage = evidence["intended_protection_lineage"]
    expected = {
        "position_id": position.get("position_id"),
        "position_ref": authority.position_ref,
        "position_hash": authority.position_hash,
        "position_observed_at": position.get("broker_state_observed_at"),
        "provider_identity_ref": authority.provider_identity_ref,
        "provider_instrument_ref": authority.provider_instrument_ref,
        "provider_observation_generation_id": authority.provider_observation_generation_id,
        "provider_observed_at": authority.provider_observed_at,
        "provider_received_at": authority.provider_received_at,
        "observed_active_protection_set_hash": authority.observed_active_protection_set_hash,
        "lifecycle_projection_ref": projection_facts["projection_id"],
        "lifecycle_execution_binding_ref": binding_id,
        "runtime_preflight_ref": authority.runtime_preflight_ref,
        "runtime_process_instance_id": authority.runtime_process_instance_id,
        "runtime_process_start_generation_id": authority.runtime_process_start_generation_id,
        "runtime_config_generation_id": authority.runtime_config_generation_id,
    }
    if any(evidence.get(field) != value for field, value in expected.items()):
        return False
    if (
        lineage.get("position_ref") != authority.position_ref
        or lineage.get("position_hash") != authority.position_hash
        or lineage.get("position_id") != position.get("position_id")
        or lineage.get("position_observed_at") != position.get("broker_state_observed_at")
        or lineage.get("lifecycle_projection_ref") != projection_facts["projection_id"]
        or lineage.get("lifecycle_execution_binding_ref") != binding_id
        or lineage.get("runtime_preflight_ref") != authority.runtime_preflight_ref
        or lineage.get("runtime_process_instance_id") != authority.runtime_process_instance_id
        or lineage.get("runtime_process_start_generation_id") != authority.runtime_process_start_generation_id
        or lineage.get("runtime_config_generation_id") != authority.runtime_config_generation_id
    ):
        return False
    return True


def _unknown_transition(current_state: PositionLifecycleState) -> tuple[PositionEvent | None, PositionLifecycleState]:
    if current_state == PositionLifecycleState.RECONCILIATION_REQUIRED:
        return None, current_state
    try:
        event = PositionEvent.STATE_UNKNOWN
        return event, transition(current_state, event)
    except UnsafeTransitionError:
        return None, current_state


def _decision_id(material: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "e5protreg_" + digest


def _source_hashes(evidence: Mapping[str, Any]) -> tuple[str | None, str | None, str | None]:
    evidence_id = evidence.get("protection_registry_evidence_id") if isinstance(evidence, Mapping) else None
    try:
        full_hash = canonical_protection_registry_hash(evidence)
        material_hash = _material_hash(evidence)
    except ProtectionRegistryPolicyError:
        full_hash = None
        material_hash = None
    return evidence_id if isinstance(evidence_id, str) else None, full_hash, material_hash


def _build_decision(
    evidence: Mapping[str, Any],
    authority: CurrentProtectionRegistryAuthority,
    *,
    decision: str,
    event: PositionEvent | None,
    next_state: PositionLifecycleState,
    reason: str,
    healthy_protection: bool,
    terminal_close_dependency: bool,
    evidence_current: bool,
) -> ProtectionRegistryPolicyDecision:
    projection_facts, binding_id = _validate_current_authority(authority)
    source_id, source_hash, source_material_hash = _source_hashes(evidence)
    source_dispositions = tuple(evidence.get("required_dispositions", ())) if isinstance(evidence, Mapping) else ()
    source_reasons = tuple(evidence.get("reason_codes", ())) if isinstance(evidence, Mapping) else ()
    material = {
        "position_ref": authority.position_ref,
        "position_hash": authority.position_hash,
        "position_observed_at": authority.position.get("broker_state_observed_at"),
        "lifecycle_projection_id": projection_facts["projection_id"],
        "lifecycle_revision": projection_facts["revision"],
        "lifecycle_execution_binding_id": binding_id,
        "source_registry_material_hash": source_material_hash,
        "decision": decision,
        "event": None if event is None else event.value,
        "next_state": next_state.value,
        "reason_codes": [reason],
        "source_required_dispositions": list(source_dispositions),
        "source_reason_codes": list(source_reasons),
        "healthy_protection": healthy_protection,
        "terminal_close_dependency": terminal_close_dependency,
        "provider_mutation_authorized": False,
        "cleanup_target_ref": None,
        "evidence_current": evidence_current,
    }
    return ProtectionRegistryPolicyDecision(
        decision_id=_decision_id(material),
        decision=decision,
        event=event,
        next_state=next_state,
        reason_codes=(reason,),
        source_required_dispositions=source_dispositions,
        source_reason_codes=source_reasons,
        source_registry_evidence_id=source_id,
        source_registry_evidence_hash=source_hash,
        source_registry_material_hash=source_material_hash,
        healthy_protection=healthy_protection,
        terminal_close_dependency=terminal_close_dependency,
        provider_mutation_authorized=False,
        cleanup_target_ref=None,
        evidence_current=evidence_current,
    )


def _reconcile(
    evidence: Mapping[str, Any],
    authority: CurrentProtectionRegistryAuthority,
    *,
    reason: str,
    evidence_current: bool,
    terminal_close_dependency: bool = False,
) -> ProtectionRegistryPolicyDecision:
    current_state = PositionLifecycleState(authority.lifecycle_projection["lifecycle_state"])
    event, next_state = _unknown_transition(current_state)
    return _build_decision(
        evidence,
        authority,
        decision=DECISION_RECONCILE,
        event=event,
        next_state=next_state,
        reason=reason,
        healthy_protection=False,
        terminal_close_dependency=terminal_close_dependency,
        evidence_current=evidence_current,
    )


def interpret_protection_registry_evidence(
    evidence: Mapping[str, Any],
    authority: CurrentProtectionRegistryAuthority,
) -> ProtectionRegistryPolicyDecision:
    """Interpret one current FP-11 object into existing E5 lifecycle semantics only."""

    _validate_current_authority(authority)
    try:
        validate_fp11_registry_evidence(evidence)
    except ProtectionRegistryPolicyError:
        return _reconcile(
            evidence,
            authority,
            reason="E5_FP11_EVIDENCE_INVALID",
            evidence_current=False,
        )

    if not fp11_registry_evidence_is_current(evidence, authority):
        return _reconcile(
            evidence,
            authority,
            reason="E5_FP11_EVIDENCE_STALE_OR_MISMATCHED",
            evidence_current=False,
        )

    current_state = PositionLifecycleState(authority.lifecycle_projection["lifecycle_state"])
    quantity = _quantity(authority.position)
    multiplicity = evidence["multiplicity_state"]
    registry_status = evidence["registry_status"]
    dispositions = evidence["required_dispositions"]
    terminal_dependency = FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED in dispositions

    if terminal_dependency:
        return _reconcile(
            evidence,
            authority,
            reason="E5_FP11_FP10_TERMINAL_PROTECTION_CONVERGENCE_REQUIRED",
            evidence_current=True,
            terminal_close_dependency=True,
        )

    success = (
        multiplicity == EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
        and registry_status == CONVERGED_EXACTLY_ONE_INTENDED
        and dispositions == [NO_ACTION_REGISTRY_CONVERGED]
        and evidence["reason_codes"] == ["EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"]
    )
    if success:
        if quantity == 0:
            return _reconcile(
                evidence,
                authority,
                reason="E5_FP11_FLAT_WITH_ACTIVE_PROTECTION_CONTRADICTION",
                evidence_current=True,
                terminal_close_dependency=True,
            )
        if current_state in {
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        }:
            return _build_decision(
                evidence,
                authority,
                decision=DECISION_PRESERVE_PROTECTED,
                event=None,
                next_state=current_state,
                reason="E5_FP11_UNIQUE_PROTECTION_PRESERVED",
                healthy_protection=True,
                terminal_close_dependency=False,
                evidence_current=True,
            )
        return _reconcile(
            evidence,
            authority,
            reason="E5_FP11_CONVERGED_REGISTRY_LIFECYCLE_INCOMPATIBLE",
            evidence_current=True,
        )

    missing = (
        multiplicity == NO_ACTIVE_PROTECTION_OBSERVED
        and registry_status == MISSING_PROTECTION_REINTERPRETATION_REQUIRED
    )
    if missing:
        if quantity == 0:
            return _build_decision(
                evidence,
                authority,
                decision=DECISION_HOLD_SAFE,
                event=None,
                next_state=current_state,
                reason="E5_FP11_FLAT_NO_ACTIVE_PROTECTION_DEFER_TO_FP10",
                healthy_protection=False,
                terminal_close_dependency=False,
                evidence_current=True,
            )
        if current_state in {
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        }:
            event = PositionEvent.PROTECTION_LOST
            return _build_decision(
                evidence,
                authority,
                decision=DECISION_PROTECTION_LOST,
                event=event,
                next_state=transition(current_state, event),
                reason="E5_FP11_ACTIVE_PROTECTION_MISSING",
                healthy_protection=False,
                terminal_close_dependency=False,
                evidence_current=True,
            )
        if current_state in {
            PositionLifecycleState.OPEN_UNPROTECTED,
            PositionLifecycleState.EMERGENCY,
            PositionLifecycleState.EXIT_REQUESTED,
            PositionLifecycleState.RECONCILIATION_REQUIRED,
        }:
            return _build_decision(
                evidence,
                authority,
                decision=DECISION_HOLD_SAFE,
                event=None,
                next_state=current_state,
                reason="E5_FP11_MISSING_PROTECTION_POLICY_REQUIRED_NO_MUTATION_AUTHORITY",
                healthy_protection=False,
                terminal_close_dependency=False,
                evidence_current=True,
            )
        return _reconcile(
            evidence,
            authority,
            reason="E5_FP11_MISSING_PROTECTION_LIFECYCLE_INCOMPATIBLE",
            evidence_current=True,
        )

    if multiplicity == MULTIPLE_ACTIVE_PROTECTIONS:
        reason = "E5_FP11_MULTIPLICITY_RECONCILIATION_REQUIRED"
    elif multiplicity == ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT:
        reason = "E5_FP11_ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED"
    elif multiplicity == OWNERSHIP_CONFLICT_PRESENT:
        reason = "E5_FP11_OWNERSHIP_MANUAL_REVIEW_REQUIRED"
    elif multiplicity in {PROTECTION_SET_STALE, PROTECTION_SET_UNKNOWN}:
        reason = "E5_FP11_PROVIDER_SET_REFRESH_OR_RECONCILIATION_REQUIRED"
    else:
        reason = "E5_FP11_NONCONVERGED_RECONCILIATION_REQUIRED"
    return _reconcile(
        evidence,
        authority,
        reason=reason,
        evidence_current=True,
    )


def protection_registry_interpretation_is_current(
    decision: ProtectionRegistryPolicyDecision,
    latest_evidence: Mapping[str, Any],
    authority: CurrentProtectionRegistryAuthority,
) -> bool:
    """Material changes invalidate old E5 interpretation; timestamp-only refresh does not."""

    if not isinstance(decision, ProtectionRegistryPolicyDecision):
        return False
    try:
        latest = interpret_protection_registry_evidence(latest_evidence, authority)
    except (ProtectionRegistryPolicyError, ValueError):
        return False
    return decision.decision_id == latest.decision_id
