from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._sqlite_registry import _apply_migrations, _connect

SCHEMA_VERSION = "contracts-v0.1"
FP11_PROFILE_VERSION = "protection-registry-multiplicity-v0.1"

HEALTHY_UNIQUE_PROTECTION = "HEALTHY_UNIQUE_PROTECTION"
STATUS_RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_CONFLICT = "CONFLICT"
STATUS_STALE = "STALE"
STATUS_UNKNOWN = "UNKNOWN"

CURRENT = "CURRENT"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
COMPLETE = "COMPLETE"
ACTIVE_PROTECTION = "ACTIVE_PROTECTION"

EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION = "EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION"
CONVERGED_EXACTLY_ONE_INTENDED = "CONVERGED_EXACTLY_ONE_INTENDED"
NO_ACTION_REGISTRY_CONVERGED = "NO_ACTION_REGISTRY_CONVERGED"
EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED = "EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"
FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED = (
    "FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED"
)

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FP11_ID_RE = re.compile(r"^protregmul_[0-9a-f]{64}$")
_E5_DECISION_ID_RE = re.compile(r"^e5protreg_[0-9a-f]{64}$")

_FP11_FIELDS = frozenset(
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
_DECISION_FIELDS = frozenset(
    {
        "decision_id",
        "position_id",
        "position_ref",
        "position_hash",
        "position_observed_at",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "lifecycle_execution_binding_id",
        "source_registry_evidence_id",
        "source_registry_evidence_hash",
        "source_registry_material_hash",
        "decision",
        "event",
        "next_state",
        "reason_codes",
        "source_required_dispositions",
        "source_reason_codes",
        "healthy_protection",
        "terminal_close_dependency",
        "provider_mutation_authorized",
        "cleanup_target_ref",
        "evidence_current",
    }
)

_MULTIPLICITY_STATES = frozenset(
    {
        "NO_ACTIVE_PROTECTION_OBSERVED",
        EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION,
        "MULTIPLE_ACTIVE_PROTECTIONS",
        "ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT",
        "OWNERSHIP_CONFLICT_PRESENT",
        "PROTECTION_SET_STALE",
        "PROTECTION_SET_UNKNOWN",
    }
)
_REGISTRY_STATUSES = frozenset(
    {
        CONVERGED_EXACTLY_ONE_INTENDED,
        "MISSING_PROTECTION_REINTERPRETATION_REQUIRED",
        "MULTIPLICITY_CONVERGENCE_REQUIRED",
        "ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED",
        "OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED",
        "PROVIDER_SET_REFRESH_REQUIRED",
        "LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED",
        UNKNOWN,
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
    EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED,
)
_REASON_INDEX = {value: index for index, value in enumerate(_REASON_ORDER)}


class ProtectionRegistryCurrentnessError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ProtectionRegistryValidationError(ProtectionRegistryCurrentnessError):
    pass


class ProtectionRegistryConflictError(ProtectionRegistryCurrentnessError):
    pass


@dataclass(frozen=True)
class StoredProtectionRegistryRecord:
    object_kind: str
    canonical_id: str
    payload_json: str
    payload_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise ProtectionRegistryValidationError(
                "STORED_PAYLOAD_NOT_OBJECT",
                "stored FP-11 material is not a JSON object",
            )
        return value


@dataclass(frozen=True)
class ProtectionRegistryCurrentAuthority:
    """E6-local mechanical currentness input assembled from owner-authoritative material."""

    position_ref: str
    position: Mapping[str, Any]
    intended_protection_lineage: Mapping[str, Any]
    lifecycle_projection: Mapping[str, Any]
    lifecycle_execution_binding: Mapping[str, Any] | None
    provider_identity_ref: str
    provider_instrument_ref: str
    provider_observation_generation_id: str
    provider_observed_at: str
    provider_received_at: str
    observed_active_protection_set_hash: str | None
    runtime_preflight_ref: str | None = None
    runtime_process_instance_id: str | None = None
    runtime_process_start_generation_id: str | None = None
    runtime_config_generation_id: str | None = None


@dataclass(frozen=True)
class ProtectionRegistryReadModel:
    status: str
    reason_codes: tuple[str, ...]
    position_id: str | None
    current_fp11: StoredProtectionRegistryRecord | None
    current_interpretation: StoredProtectionRegistryRecord | None
    current_lifecycle_projection_id: str | None
    current_lifecycle_state: str | None
    healthy_protection: bool
    terminal_close_dependency: bool
    provider_mutation_authorized: bool
    cleanup_target_ref: None


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ProtectionRegistryValidationError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ProtectionRegistryValidationError("NONCANONICAL_TIMESTAMP", "datetime must be UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtectionRegistryValidationError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ProtectionRegistryValidationError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ProtectionRegistryValidationError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical value: {type(value).__name__}",
    )


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            _canonicalize(value),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProtectionRegistryValidationError("NONCANONICAL_JSON", "material is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_hash(payload_json: str) -> str:
    return "sha256:" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProtectionRegistryValidationError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise ProtectionRegistryValidationError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _utc(value: Any, field: str) -> datetime:
    text = _text(value, field)
    if not text.endswith("Z"):
        raise ProtectionRegistryValidationError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionRegistryValidationError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionRegistryValidationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _string_sequence(value: Any, field: str, *, nonempty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise ProtectionRegistryValidationError("INVALID_SEQUENCE", f"{field} must be a list")
    result = [_text(item, f"{field}[]") for item in value]
    if nonempty and not result:
        raise ProtectionRegistryValidationError("INVALID_SEQUENCE", f"{field} must be non-empty")
    if len(result) != len(set(result)):
        raise ProtectionRegistryValidationError("DUPLICATE_SEQUENCE", f"{field} must be unique")
    return result


def _stable_fp11_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("protection_registry_evidence_id", None)
    return "protregmul_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _fp11_material_hash(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    for field in (
        "protection_registry_evidence_id",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    ):
        material.pop(field, None)
    return _sha256_json(material)


def _logical_lineage_material(position_id: str, lineage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "position_id": position_id,
        "position_action_id": lineage.get("position_action_id"),
        "approved_trade_plan_ref": lineage.get("approved_trade_plan_ref"),
        "protection_order_request_ref": lineage.get("protection_order_request_ref"),
        "client_order_identity_ref": lineage.get("client_order_identity_ref"),
    }


def _logical_lineage_hash(position_id: str, lineage: Mapping[str, Any]) -> str:
    material = _logical_lineage_material(position_id, lineage)
    _text(material["position_id"], "lineage.position_id")
    _text(material["position_action_id"], "lineage.position_action_id")
    _text(material["approved_trade_plan_ref"], "lineage.approved_trade_plan_ref")
    _optional_text(material["protection_order_request_ref"], "lineage.protection_order_request_ref")
    _optional_text(material["client_order_identity_ref"], "lineage.client_order_identity_ref")
    return _sha256_json(material)


def _observed_set_hash(payload: Mapping[str, Any]) -> str:
    material = {
        "provider_identity_ref": payload["provider_identity_ref"],
        "provider_instrument_ref": payload["provider_instrument_ref"],
        "provider_observation_generation_id": payload["provider_observation_generation_id"],
        "provider_observed_at": payload["provider_observed_at"],
        "observation_coverage_status": payload["observation_coverage_status"],
        "provider_set_currentness_status": payload["provider_set_currentness_status"],
        "objects": payload["observed_active_protection_objects"],
    }
    return _sha256_json(material)


def _validate_intended_lineage(value: Any) -> dict[str, Any]:
    lineage = _canonicalize(value)
    if not isinstance(lineage, dict) or set(lineage) != _INTENDED_LINEAGE_FIELDS:
        raise ProtectionRegistryValidationError(
            "FP11_INTENDED_LINEAGE_FIELDS_INVALID",
            "intended protection lineage fields mismatch",
        )
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
    _utc(lineage["position_observed_at"], "intended_protection_lineage.position_observed_at")
    if lineage.get("position_side") not in {"LONG", "SHORT"}:
        raise ProtectionRegistryValidationError("FP11_POSITION_SIDE_INVALID", "lineage position_side invalid")
    if (lineage.get("protection_order_request_ref") is None) != (
        lineage.get("protection_order_request_hash") is None
    ):
        raise ProtectionRegistryValidationError(
            "FP11_ORDER_REQUEST_REF_HASH_INCOMPLETE",
            "protection order request ref/hash must be both set or null",
        )
    if lineage.get("protection_order_request_ref") is not None:
        _text(lineage["protection_order_request_ref"], "intended_protection_lineage.protection_order_request_ref")
        _hash(lineage["protection_order_request_hash"], "intended_protection_lineage.protection_order_request_hash")
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
    runtime = (
        lineage["runtime_preflight_ref"],
        lineage["runtime_process_instance_id"],
        lineage["runtime_process_start_generation_id"],
        lineage["runtime_config_generation_id"],
    )
    if any(item is not None for item in runtime) and not all(item is not None for item in runtime):
        raise ProtectionRegistryValidationError("FP11_LINEAGE_RUNTIME_INCOMPLETE", "runtime lineage is all-or-none")
    return lineage


def _validate_entry(value: Any) -> dict[str, Any]:
    entry = _canonicalize(value)
    if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
        raise ProtectionRegistryValidationError("FP11_ENTRY_FIELDS_INVALID", "observed entry fields mismatch")
    for field in (
        "provider_object_ref",
        "provider_snapshot_ref",
        "ownership_evidence_ref",
        "ownership_classification",
        "ownership_reconciliation_status",
        "intended_lineage_binding_status",
    ):
        _text(entry[field], f"entry.{field}")
    for field in ("provider_snapshot_hash", "ownership_evidence_hash"):
        _hash(entry[field], f"entry.{field}")
    _utc(entry["provider_object_observed_at"], "entry.provider_object_observed_at")
    binding = entry["intended_lineage_binding_status"]
    if binding not in {"EXACT_MATCH", "NOT_MATCH", UNKNOWN}:
        raise ProtectionRegistryValidationError("FP11_ENTRY_BINDING_STATUS_INVALID", "binding status invalid")
    if binding == UNKNOWN:
        if entry["intended_lineage_binding_ref"] is not None or entry["intended_lineage_binding_hash"] is not None:
            raise ProtectionRegistryValidationError("FP11_UNKNOWN_BINDING_HAS_PROOF", "UNKNOWN binding must have null proof")
    else:
        _text(entry["intended_lineage_binding_ref"], "entry.intended_lineage_binding_ref")
        _hash(entry["intended_lineage_binding_hash"], "entry.intended_lineage_binding_hash")
    return entry


def _validate_fp11(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str, str]:
    material = _canonicalize(payload)
    if not isinstance(material, dict) or set(material) != _FP11_FIELDS:
        raise ProtectionRegistryValidationError("FP11_FIELDS_INVALID", "FP-11 evidence fields mismatch")
    if material.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionRegistryValidationError("FP11_SCHEMA_UNSUPPORTED", "FP-11 schema unsupported")
    if material.get("protection_registry_multiplicity_profile_version") != FP11_PROFILE_VERSION:
        raise ProtectionRegistryValidationError("FP11_PROFILE_UNSUPPORTED", "FP-11 profile unsupported")
    evidence_id = _text(material.get("protection_registry_evidence_id"), "protection_registry_evidence_id")
    if _FP11_ID_RE.fullmatch(evidence_id) is None or evidence_id != _stable_fp11_id(material):
        raise ProtectionRegistryValidationError("FP11_IDENTITY_INVALID", "FP-11 evidence identity invalid")

    for field in (
        "position_id",
        "position_ref",
        "provider_identity_ref",
        "provider_instrument_ref",
        "provider_observation_generation_id",
    ):
        _text(material[field], field)
    for field in ("position_hash", "intended_protection_lineage_hash", "observed_active_protection_set_hash"):
        _hash(material[field], field)

    position_observed = _utc(material["position_observed_at"], "position_observed_at")
    provider_observed = _utc(material["provider_observed_at"], "provider_observed_at")
    provider_received = _utc(material["provider_received_at"], "provider_received_at")
    evaluated = _utc(material["evaluated_at"], "evaluated_at")
    if provider_received < provider_observed or evaluated < provider_received or evaluated < position_observed:
        raise ProtectionRegistryValidationError("FP11_TEMPORAL_ORDER_INVALID", "FP-11 temporal ordering invalid")

    lineage = _validate_intended_lineage(material["intended_protection_lineage"])
    if material["position_id"] != lineage["position_id"] or material["position_ref"] != lineage["position_ref"]:
        raise ProtectionRegistryValidationError("FP11_LINEAGE_POSITION_MISMATCH", "lineage Position identity mismatch")
    if material["position_hash"] != lineage["position_hash"] or material["position_observed_at"] != lineage["position_observed_at"]:
        raise ProtectionRegistryValidationError("FP11_LINEAGE_POSITION_MISMATCH", "lineage Position authority mismatch")
    if material["intended_protection_lineage_hash"] != _sha256_json(lineage):
        raise ProtectionRegistryValidationError("FP11_LINEAGE_HASH_MISMATCH", "intended lineage hash mismatch")

    entries_raw = material["observed_active_protection_objects"]
    if not isinstance(entries_raw, list):
        raise ProtectionRegistryValidationError("FP11_ENTRY_SET_INVALID", "observed entries must be a list")
    entries = [_validate_entry(item) for item in entries_raw]
    sorted_entries = sorted(
        entries,
        key=lambda item: (
            item["provider_object_ref"],
            item["provider_snapshot_hash"],
            item["ownership_evidence_ref"],
        ),
    )
    if entries != sorted_entries:
        raise ProtectionRegistryValidationError("FP11_ENTRY_ORDER_INVALID", "observed entries not canonical sorted order")
    keys = [
        (item["provider_object_ref"], item["provider_snapshot_hash"], item["ownership_evidence_ref"])
        for item in entries
    ]
    if len(keys) != len(set(keys)):
        raise ProtectionRegistryValidationError("FP11_DUPLICATE_ENTRY", "observed entries must be unique")
    if type(material["active_protection_count"]) is not int or material["active_protection_count"] != len(entries):
        raise ProtectionRegistryValidationError("FP11_ACTIVE_COUNT_INVALID", "active protection count mismatch")
    if material["observed_active_protection_set_hash"] != _observed_set_hash(material):
        raise ProtectionRegistryValidationError("FP11_SET_HASH_MISMATCH", "observed active protection set hash mismatch")

    if material["observation_coverage_status"] not in {COMPLETE, "INCOMPLETE", UNKNOWN}:
        raise ProtectionRegistryValidationError("FP11_COVERAGE_INVALID", "coverage unsupported")
    if material["provider_set_currentness_status"] not in {CURRENT, STALE, UNKNOWN}:
        raise ProtectionRegistryValidationError("FP11_CURRENTNESS_INVALID", "provider set currentness unsupported")
    if material["multiplicity_state"] not in _MULTIPLICITY_STATES:
        raise ProtectionRegistryValidationError("FP11_MULTIPLICITY_INVALID", "multiplicity state unsupported")
    if material["registry_status"] not in _REGISTRY_STATUSES:
        raise ProtectionRegistryValidationError("FP11_REGISTRY_STATUS_INVALID", "registry status unsupported")

    dispositions = _string_sequence(material["required_dispositions"], "required_dispositions")
    if any(item not in _DISPOSITIONS for item in dispositions) or dispositions != sorted(dispositions):
        raise ProtectionRegistryValidationError("FP11_DISPOSITIONS_INVALID", "FP-11 dispositions invalid")
    if NO_ACTION_REGISTRY_CONVERGED in dispositions and dispositions != [NO_ACTION_REGISTRY_CONVERGED]:
        raise ProtectionRegistryValidationError("FP11_FALSE_NO_ACTION", "NO_ACTION_REGISTRY_CONVERGED is exclusive")
    reasons = _string_sequence(material["reason_codes"], "reason_codes")
    if any(item not in _REASON_INDEX for item in reasons) or reasons != sorted(reasons, key=_REASON_INDEX.__getitem__):
        raise ProtectionRegistryValidationError("FP11_REASONS_INVALID", "FP-11 reasons invalid")

    success = (
        material["multiplicity_state"] == EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
        and material["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED
    )
    if success:
        if (
            material["active_protection_count"] != 1
            or dispositions != [NO_ACTION_REGISTRY_CONVERGED]
            or reasons != [EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED]
            or material["observation_coverage_status"] != COMPLETE
            or material["provider_set_currentness_status"] != CURRENT
        ):
            raise ProtectionRegistryValidationError("FP11_FALSE_CONVERGENCE", "FP-11 success tuple incomplete")
        entry = entries[0]
        if (
            entry["ownership_classification"] != "KNOWN_OWNED_CURRENT_GENERATION"
            or entry["ownership_reconciliation_status"] != "CURRENT_KNOWN_OWNED"
            or entry["intended_lineage_binding_status"] != "EXACT_MATCH"
        ):
            raise ProtectionRegistryValidationError("FP11_FALSE_CONVERGENCE", "FP-11 success ownership/lineage invalid")
    elif material["registry_status"] == CONVERGED_EXACTLY_ONE_INTENDED:
        raise ProtectionRegistryValidationError("FP11_FALSE_CONVERGENCE", "non-exact-one registry cannot converge")

    runtime = (
        material["runtime_preflight_ref"],
        material["runtime_process_instance_id"],
        material["runtime_process_start_generation_id"],
        material["runtime_config_generation_id"],
    )
    for index, field in enumerate(
        (
            "runtime_preflight_ref",
            "runtime_process_instance_id",
            "runtime_process_start_generation_id",
            "runtime_config_generation_id",
        )
    ):
        _optional_text(runtime[index], field)
    if any(item is not None for item in runtime) and not all(item is not None for item in runtime):
        raise ProtectionRegistryValidationError("FP11_RUNTIME_INCOMPLETE", "runtime generation is all-or-none")
    _optional_text(material["lifecycle_projection_ref"], "lifecycle_projection_ref")
    _optional_text(material["lifecycle_execution_binding_ref"], "lifecycle_execution_binding_ref")
    supersedes = material["supersedes_registry_evidence_id"]
    if supersedes is not None:
        supersedes = _text(supersedes, "supersedes_registry_evidence_id")
        if _FP11_ID_RE.fullmatch(supersedes) is None or supersedes == evidence_id:
            raise ProtectionRegistryValidationError("FP11_SUPERSESSION_INVALID", "FP-11 supersession reference invalid")

    payload_json = _canonical_json(material)
    return material, payload_json, _payload_hash(payload_json), _logical_lineage_hash(material["position_id"], lineage)


def _decision_attr(decision: Any, field: str) -> Any:
    if isinstance(decision, Mapping):
        if field not in decision:
            raise ProtectionRegistryValidationError("E5_FP11_DECISION_FIELD_MISSING", f"decision missing {field}")
        value = decision[field]
    else:
        if not hasattr(decision, field):
            raise ProtectionRegistryValidationError("E5_FP11_DECISION_FIELD_MISSING", f"decision missing {field}")
        value = getattr(decision, field)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    return value


def _stable_e5_decision_id(material: Mapping[str, Any]) -> str:
    return "e5protreg_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _validate_decision(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    material = _canonicalize(payload)
    if not isinstance(material, dict) or set(material) != _DECISION_FIELDS:
        raise ProtectionRegistryValidationError("E5_FP11_DECISION_FIELDS_INVALID", "E5 FP-11 decision envelope fields mismatch")
    decision_id = _text(material["decision_id"], "decision_id")
    if _E5_DECISION_ID_RE.fullmatch(decision_id) is None:
        raise ProtectionRegistryValidationError("E5_FP11_DECISION_ID_INVALID", "E5 FP-11 decision ID invalid")
    for field in (
        "position_id",
        "position_ref",
        "position_observed_at",
        "lifecycle_projection_id",
        "source_registry_evidence_id",
        "decision",
        "next_state",
    ):
        _text(material[field], field)
    if _FP11_ID_RE.fullmatch(material["source_registry_evidence_id"]) is None:
        raise ProtectionRegistryValidationError("E5_FP11_SOURCE_ID_INVALID", "source FP-11 ID invalid")
    for field in ("position_hash", "source_registry_evidence_hash", "source_registry_material_hash"):
        _hash(material[field], field)
    _utc(material["position_observed_at"], "position_observed_at")
    revision = material["lifecycle_revision"]
    if type(revision) is not int or revision < 0:
        raise ProtectionRegistryValidationError("E5_FP11_LIFECYCLE_REVISION_INVALID", "lifecycle revision invalid")
    binding_id = _optional_text(material["lifecycle_execution_binding_id"], "lifecycle_execution_binding_id")
    _optional_text(material["event"], "event")
    reasons = _string_sequence(material["reason_codes"], "reason_codes")
    source_dispositions = _string_sequence(material["source_required_dispositions"], "source_required_dispositions")
    source_reasons = _string_sequence(material["source_reason_codes"], "source_reason_codes")
    for field in (
        "healthy_protection",
        "terminal_close_dependency",
        "provider_mutation_authorized",
        "evidence_current",
    ):
        if type(material[field]) is not bool:
            raise ProtectionRegistryValidationError("E5_FP11_DECISION_BOOLEAN_INVALID", f"{field} must be boolean")
    if material["provider_mutation_authorized"] is not False or material["cleanup_target_ref"] is not None:
        raise ProtectionRegistryValidationError(
            "E5_FP11_FORBIDDEN_MUTATION_AUTHORITY",
            "FP-11 interpretation cannot persist provider mutation or cleanup authority",
        )

    id_material = {
        "position_ref": material["position_ref"],
        "position_hash": material["position_hash"],
        "position_observed_at": material["position_observed_at"],
        "lifecycle_projection_id": material["lifecycle_projection_id"],
        "lifecycle_revision": revision,
        "lifecycle_execution_binding_id": binding_id,
        "source_registry_material_hash": material["source_registry_material_hash"],
        "decision": material["decision"],
        "event": material["event"],
        "next_state": material["next_state"],
        "reason_codes": reasons,
        "source_required_dispositions": source_dispositions,
        "source_reason_codes": source_reasons,
        "healthy_protection": material["healthy_protection"],
        "terminal_close_dependency": material["terminal_close_dependency"],
        "provider_mutation_authorized": False,
        "cleanup_target_ref": None,
        "evidence_current": material["evidence_current"],
    }
    if decision_id != _stable_e5_decision_id(id_material):
        raise ProtectionRegistryValidationError(
            "E5_FP11_DECISION_IDENTITY_MISMATCH",
            "E5 FP-11 decision ID does not match accepted producer material",
        )
    payload_json = _canonical_json(material)
    return material, payload_json, _payload_hash(payload_json)


def _validate_authority(authority: ProtectionRegistryCurrentAuthority) -> dict[str, Any]:
    if not isinstance(authority, ProtectionRegistryCurrentAuthority):
        raise ProtectionRegistryValidationError("CURRENT_AUTHORITY_INVALID", "authority must be typed")
    if not isinstance(authority.position, Mapping):
        raise ProtectionRegistryValidationError("CURRENT_POSITION_INVALID", "current Position must be mapping")
    position = _canonicalize(authority.position)
    if not isinstance(position, dict):
        raise ProtectionRegistryValidationError("CURRENT_POSITION_INVALID", "current Position must be object")
    position_id = _text(position.get("position_id"), "current.position_id")
    position_observed_at = _text(position.get("broker_state_observed_at"), "current.broker_state_observed_at")
    _utc(position_observed_at, "current.broker_state_observed_at")
    _text(position.get("lifecycle_state"), "current.lifecycle_state")
    quantity_text = _text(str(position.get("actual_quantity")), "current.actual_quantity")
    try:
        quantity = Decimal(quantity_text)
    except InvalidOperation as exc:
        raise ProtectionRegistryValidationError("CURRENT_POSITION_QUANTITY_INVALID", "current quantity invalid") from exc
    if not quantity.is_finite() or quantity < 0:
        raise ProtectionRegistryValidationError("CURRENT_POSITION_QUANTITY_INVALID", "current quantity invalid")

    _text(authority.position_ref, "current.position_ref")
    lineage = _validate_intended_lineage(authority.intended_protection_lineage)
    if lineage["position_id"] != position_id or lineage["position_ref"] != authority.position_ref:
        raise ProtectionRegistryValidationError("CURRENT_LINEAGE_POSITION_MISMATCH", "current lineage Position mismatch")

    projection = _canonicalize(authority.lifecycle_projection)
    if not isinstance(projection, dict):
        raise ProtectionRegistryValidationError("CURRENT_LIFECYCLE_INVALID", "current lifecycle projection invalid")
    projection_id = _text(projection.get("lifecycle_projection_id"), "current.lifecycle_projection_id")
    revision = projection.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise ProtectionRegistryValidationError("CURRENT_LIFECYCLE_REVISION_INVALID", "current lifecycle revision invalid")
    if (
        projection.get("position_id") != position_id
        or projection.get("broker_state_observed_at") != position_observed_at
        or projection.get("lifecycle_state") != position.get("lifecycle_state")
    ):
        raise ProtectionRegistryValidationError("CURRENT_POSITION_LIFECYCLE_MISMATCH", "current Position/lifecycle mismatch")

    binding_id = None
    if authority.lifecycle_execution_binding is not None:
        binding = _canonicalize(authority.lifecycle_execution_binding)
        if not isinstance(binding, dict):
            raise ProtectionRegistryValidationError("CURRENT_BINDING_INVALID", "current execution binding invalid")
        binding_id = _text(binding.get("lifecycle_execution_binding_id"), "current.lifecycle_execution_binding_id")
        if (
            binding.get("position_id") != position_id
            or binding.get("lifecycle_projection_id") != projection_id
            or binding.get("lifecycle_revision") != revision
        ):
            raise ProtectionRegistryValidationError("CURRENT_BINDING_MISMATCH", "current execution binding mismatch")

    for field, value in (
        ("provider_identity_ref", authority.provider_identity_ref),
        ("provider_instrument_ref", authority.provider_instrument_ref),
        ("provider_observation_generation_id", authority.provider_observation_generation_id),
    ):
        _text(value, f"current.{field}")
    _utc(authority.provider_observed_at, "current.provider_observed_at")
    _utc(authority.provider_received_at, "current.provider_received_at")
    if authority.observed_active_protection_set_hash is None:
        raise ProtectionRegistryValidationError("CURRENT_PROVIDER_SET_UNAVAILABLE", "current provider protection set hash unavailable")
    _hash(authority.observed_active_protection_set_hash, "current.observed_active_protection_set_hash")

    runtime = (
        authority.runtime_preflight_ref,
        authority.runtime_process_instance_id,
        authority.runtime_process_start_generation_id,
        authority.runtime_config_generation_id,
    )
    for index, field in enumerate(
        (
            "runtime_preflight_ref",
            "runtime_process_instance_id",
            "runtime_process_start_generation_id",
            "runtime_config_generation_id",
        )
    ):
        _optional_text(runtime[index], f"current.{field}")
    if any(item is not None for item in runtime) and not all(item is not None for item in runtime):
        raise ProtectionRegistryValidationError("CURRENT_RUNTIME_INCOMPLETE", "current runtime generation is all-or-none")

    return {
        "position": position,
        "position_id": position_id,
        "position_ref": authority.position_ref,
        "position_hash": _sha256_json(position),
        "position_observed_at": position_observed_at,
        "quantity": quantity,
        "lifecycle_state": position["lifecycle_state"],
        "lineage": lineage,
        "lineage_hash": _sha256_json(lineage),
        "lineage_key_hash": _logical_lineage_hash(position_id, lineage),
        "projection": projection,
        "projection_id": projection_id,
        "lifecycle_revision": revision,
        "binding_id": binding_id,
        "provider_identity_ref": authority.provider_identity_ref,
        "provider_instrument_ref": authority.provider_instrument_ref,
        "provider_observation_generation_id": authority.provider_observation_generation_id,
        "provider_observed_at": authority.provider_observed_at,
        "provider_received_at": authority.provider_received_at,
        "provider_set_hash": authority.observed_active_protection_set_hash,
        "runtime_preflight_ref": authority.runtime_preflight_ref,
        "runtime_process_instance_id": authority.runtime_process_instance_id,
        "runtime_process_start_generation_id": authority.runtime_process_start_generation_id,
        "runtime_config_generation_id": authority.runtime_config_generation_id,
    }


class ProtectionRegistryCurrentnessStore:
    """E6 provider-neutral FP-11 persistence/currentness/restart read model."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _stored(kind: str, canonical_id: str, row: sqlite3.Row) -> StoredProtectionRegistryRecord:
        return StoredProtectionRegistryRecord(kind, canonical_id, row["payload_json"], row["payload_hash"])

    def _record_conflict(
        self,
        reason_code: str,
        object_kind: str,
        *,
        canonical_id: str | None,
        position_id: str | None,
        existing_payload_hash: str | None,
        incoming_payload_hash: str | None,
    ) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO external_currentness_conflicts (
                    reason_code, object_kind, canonical_id, position_id,
                    existing_payload_hash, incoming_payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    reason_code,
                    object_kind,
                    canonical_id,
                    position_id,
                    existing_payload_hash,
                    incoming_payload_hash,
                ),
            )
            self._connection.commit()
        except sqlite3.Error:
            self._connection.rollback()

    def _immutable_conflict(
        self,
        *,
        object_kind: str,
        canonical_id: str,
        position_id: str | None,
        existing_payload_hash: str,
        incoming_payload_hash: str,
    ) -> None:
        self._connection.rollback()
        self._record_conflict(
            "IMMUTABLE_ID_PAYLOAD_CONFLICT",
            object_kind,
            canonical_id=canonical_id,
            position_id=position_id,
            existing_payload_hash=existing_payload_hash,
            incoming_payload_hash=incoming_payload_hash,
        )
        raise ProtectionRegistryConflictError(
            "IMMUTABLE_ID_PAYLOAD_CONFLICT",
            f"{object_kind} ID/source already exists with different canonical content",
        )

    def persist_fp11(self, evidence: Mapping[str, Any]) -> StoredProtectionRegistryRecord:
        declared_id = evidence.get("protection_registry_evidence_id") if isinstance(evidence, Mapping) else None
        incoming_json = _canonical_json(evidence) if isinstance(evidence, Mapping) else ""
        incoming_hash = _payload_hash(incoming_json) if incoming_json else ""
        if isinstance(declared_id, str):
            existing = self._connection.execute(
                "SELECT * FROM protection_registry_multiplicity_evidence WHERE protection_registry_evidence_id = ?",
                (declared_id,),
            ).fetchone()
            if existing is not None and existing["payload_json"] != incoming_json:
                position_id = evidence.get("position_id") if isinstance(evidence.get("position_id"), str) else None
                self._immutable_conflict(
                    object_kind="FP11_PROTECTION_REGISTRY_EVIDENCE",
                    canonical_id=declared_id,
                    position_id=position_id,
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=incoming_hash,
                )
            if existing is not None:
                _validate_fp11(json.loads(existing["payload_json"]))
                return self._stored("FP11_PROTECTION_REGISTRY_EVIDENCE", declared_id, existing)

        material, payload_json, payload_hash, lineage_key_hash = _validate_fp11(evidence)
        lineage = material["intended_protection_lineage"]
        self._connection.execute(
            """
            INSERT INTO protection_registry_multiplicity_evidence (
                protection_registry_evidence_id, position_id, position_ref,
                position_hash, position_observed_at, position_action_id,
                approved_trade_plan_ref, protection_order_request_ref,
                client_order_identity_ref, lineage_key_hash,
                intended_protection_lineage_hash, provider_identity_ref,
                provider_instrument_ref, provider_observation_generation_id,
                provider_observed_at, provider_received_at,
                observation_coverage_status, provider_set_currentness_status,
                observed_active_protection_set_hash, lifecycle_projection_ref,
                lifecycle_execution_binding_ref, runtime_preflight_ref,
                runtime_process_instance_id, runtime_process_start_generation_id,
                runtime_config_generation_id, multiplicity_state, registry_status,
                supersedes_registry_evidence_id, evaluated_at, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                material["protection_registry_evidence_id"],
                material["position_id"],
                material["position_ref"],
                material["position_hash"],
                material["position_observed_at"],
                lineage["position_action_id"],
                lineage["approved_trade_plan_ref"],
                lineage["protection_order_request_ref"],
                lineage["client_order_identity_ref"],
                lineage_key_hash,
                material["intended_protection_lineage_hash"],
                material["provider_identity_ref"],
                material["provider_instrument_ref"],
                material["provider_observation_generation_id"],
                material["provider_observed_at"],
                material["provider_received_at"],
                material["observation_coverage_status"],
                material["provider_set_currentness_status"],
                material["observed_active_protection_set_hash"],
                material["lifecycle_projection_ref"],
                material["lifecycle_execution_binding_ref"],
                material["runtime_preflight_ref"],
                material["runtime_process_instance_id"],
                material["runtime_process_start_generation_id"],
                material["runtime_config_generation_id"],
                material["multiplicity_state"],
                material["registry_status"],
                material["supersedes_registry_evidence_id"],
                material["evaluated_at"],
                payload_json,
                payload_hash,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM protection_registry_multiplicity_evidence WHERE protection_registry_evidence_id = ?",
            (material["protection_registry_evidence_id"],),
        ).fetchone()
        assert row is not None
        return self._stored("FP11_PROTECTION_REGISTRY_EVIDENCE", material["protection_registry_evidence_id"], row)

    def persist_e5_interpretation(
        self,
        decision: Any,
        *,
        evidence: Mapping[str, Any],
        authority: ProtectionRegistryCurrentAuthority,
    ) -> StoredProtectionRegistryRecord:
        fp11, _, fp11_hash, _ = _validate_fp11(evidence)
        current = _validate_authority(authority)
        source_id = fp11["protection_registry_evidence_id"]
        source_row = self._connection.execute(
            "SELECT * FROM protection_registry_multiplicity_evidence WHERE protection_registry_evidence_id = ?",
            (source_id,),
        ).fetchone()
        if source_row is None:
            raise ProtectionRegistryValidationError(
                "E5_FP11_SOURCE_NOT_PERSISTED",
                "E5 FP-11 interpretation requires the exact source evidence to be durable first",
            )
        if source_row["payload_hash"] != fp11_hash:
            raise ProtectionRegistryValidationError("E5_FP11_SOURCE_HASH_MISMATCH", "stored source FP-11 hash mismatch")

        event = _decision_attr(decision, "event")
        next_state = _decision_attr(decision, "next_state")
        envelope = {
            "decision_id": _decision_attr(decision, "decision_id"),
            "position_id": current["position_id"],
            "position_ref": current["position_ref"],
            "position_hash": current["position_hash"],
            "position_observed_at": current["position_observed_at"],
            "lifecycle_projection_id": current["projection_id"],
            "lifecycle_revision": current["lifecycle_revision"],
            "lifecycle_execution_binding_id": current["binding_id"],
            "source_registry_evidence_id": source_id,
            "source_registry_evidence_hash": _sha256_json(fp11),
            "source_registry_material_hash": _fp11_material_hash(fp11),
            "decision": _decision_attr(decision, "decision"),
            "event": event,
            "next_state": next_state,
            "reason_codes": _decision_attr(decision, "reason_codes"),
            "source_required_dispositions": _decision_attr(decision, "source_required_dispositions"),
            "source_reason_codes": _decision_attr(decision, "source_reason_codes"),
            "healthy_protection": _decision_attr(decision, "healthy_protection"),
            "terminal_close_dependency": _decision_attr(decision, "terminal_close_dependency"),
            "provider_mutation_authorized": _decision_attr(decision, "provider_mutation_authorized"),
            "cleanup_target_ref": _decision_attr(decision, "cleanup_target_ref"),
            "evidence_current": _decision_attr(decision, "evidence_current"),
        }
        if _decision_attr(decision, "source_registry_evidence_id") != source_id:
            raise ProtectionRegistryValidationError("E5_FP11_SOURCE_ID_MISMATCH", "decision source FP-11 ID mismatch")
        if _decision_attr(decision, "source_registry_evidence_hash") != envelope["source_registry_evidence_hash"]:
            raise ProtectionRegistryValidationError("E5_FP11_SOURCE_HASH_MISMATCH", "decision source FP-11 full hash mismatch")
        if _decision_attr(decision, "source_registry_material_hash") != envelope["source_registry_material_hash"]:
            raise ProtectionRegistryValidationError("E5_FP11_SOURCE_MATERIAL_HASH_MISMATCH", "decision source material hash mismatch")

        material, payload_json, payload_hash = _validate_decision(envelope)
        existing = self._connection.execute(
            """
            SELECT * FROM protection_registry_policy_interpretations
            WHERE decision_id = ? AND source_registry_evidence_id = ?
            """,
            (material["decision_id"], source_id),
        ).fetchone()
        if existing is not None and existing["payload_json"] != payload_json:
            self._immutable_conflict(
                object_kind="E5_FP11_POLICY_INTERPRETATION",
                canonical_id=material["decision_id"],
                position_id=current["position_id"],
                existing_payload_hash=existing["payload_hash"],
                incoming_payload_hash=payload_hash,
            )
        if existing is None:
            self._connection.execute(
                """
                INSERT INTO protection_registry_policy_interpretations (
                    decision_id, source_registry_evidence_id, position_id,
                    position_ref, position_hash, position_observed_at,
                    lifecycle_projection_id, lifecycle_revision,
                    lifecycle_execution_binding_id, source_registry_evidence_hash,
                    source_registry_material_hash, decision, event, next_state,
                    healthy_protection, terminal_close_dependency,
                    provider_mutation_authorized, cleanup_target_ref,
                    evidence_current, payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    material["decision_id"],
                    source_id,
                    current["position_id"],
                    material["position_ref"],
                    material["position_hash"],
                    material["position_observed_at"],
                    material["lifecycle_projection_id"],
                    material["lifecycle_revision"],
                    material["lifecycle_execution_binding_id"],
                    material["source_registry_evidence_hash"],
                    material["source_registry_material_hash"],
                    material["decision"],
                    material["event"],
                    material["next_state"],
                    1 if material["healthy_protection"] else 0,
                    1 if material["terminal_close_dependency"] else 0,
                    1 if material["provider_mutation_authorized"] else 0,
                    material["cleanup_target_ref"],
                    1 if material["evidence_current"] else 0,
                    payload_json,
                    payload_hash,
                ),
            )
            self._connection.commit()
            existing = self._connection.execute(
                """
                SELECT * FROM protection_registry_policy_interpretations
                WHERE decision_id = ? AND source_registry_evidence_id = ?
                """,
                (material["decision_id"], source_id),
            ).fetchone()
        assert existing is not None
        return self._stored("E5_FP11_POLICY_INTERPRETATION", material["decision_id"], existing)

    def fp11_history(self, position_id: str, position_action_id: str) -> tuple[StoredProtectionRegistryRecord, ...]:
        position_id = _text(position_id, "position_id")
        position_action_id = _text(position_action_id, "position_action_id")
        rows = self._connection.execute(
            """
            SELECT * FROM protection_registry_multiplicity_evidence
            WHERE position_id = ? AND position_action_id = ?
            ORDER BY protection_registry_evidence_id
            """,
            (position_id, position_action_id),
        ).fetchall()
        return tuple(
            self._stored("FP11_PROTECTION_REGISTRY_EVIDENCE", row["protection_registry_evidence_id"], row)
            for row in rows
        )

    def interpretation_history(self, position_id: str) -> tuple[StoredProtectionRegistryRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM protection_registry_policy_interpretations
            WHERE position_id = ? ORDER BY source_registry_evidence_id, decision_id
            """,
            (_text(position_id, "position_id"),),
        ).fetchall()
        return tuple(
            self._stored("E5_FP11_POLICY_INTERPRETATION", row["decision_id"], row)
            for row in rows
        )

    def _resolve_head(self, current: Mapping[str, Any]) -> tuple[sqlite3.Row | None, str, tuple[str, ...]]:
        rows = self._connection.execute(
            """
            SELECT * FROM protection_registry_multiplicity_evidence
            WHERE position_id = ? AND lineage_key_hash = ?
            """,
            (current["position_id"], current["lineage_key_hash"]),
        ).fetchall()
        if not rows:
            return None, STATUS_INCOMPLETE, ("FP11_EVIDENCE_MISSING_FOR_CURRENT_LINEAGE",)

        by_id = {row["protection_registry_evidence_id"]: row for row in rows}
        payloads: dict[str, dict[str, Any]] = {}
        for evidence_id, row in by_id.items():
            try:
                payload, canonical, digest, lineage_key_hash = _validate_fp11(json.loads(row["payload_json"]))
            except (json.JSONDecodeError, ProtectionRegistryCurrentnessError):
                return None, STATUS_CONFLICT, ("STORED_FP11_INVALID",)
            if (
                payload["protection_registry_evidence_id"] != evidence_id
                or canonical != row["payload_json"]
                or digest != row["payload_hash"]
                or lineage_key_hash != row["lineage_key_hash"]
                or payload.get("supersedes_registry_evidence_id") != row["supersedes_registry_evidence_id"]
            ):
                return None, STATUS_CONFLICT, ("STORED_FP11_CANONICAL_OR_INDEX_MISMATCH",)
            payloads[evidence_id] = payload

        superseded: set[str] = set()
        missing_predecessor = False
        graph: dict[str, str | None] = {}
        for evidence_id, payload in payloads.items():
            predecessor = payload.get("supersedes_registry_evidence_id")
            graph[evidence_id] = predecessor
            if predecessor is None:
                continue
            predecessor_row = self._connection.execute(
                "SELECT * FROM protection_registry_multiplicity_evidence WHERE protection_registry_evidence_id = ?",
                (predecessor,),
            ).fetchone()
            if predecessor_row is None:
                missing_predecessor = True
                continue
            if predecessor_row["lineage_key_hash"] != current["lineage_key_hash"]:
                return None, STATUS_CONFLICT, ("FP11_SUPERSESSION_LINEAGE_MISMATCH",)
            if predecessor not in by_id:
                return None, STATUS_CONFLICT, ("FP11_SUPERSESSION_LINEAGE_MISMATCH",)
            superseded.add(predecessor)

        for start in graph:
            visited: set[str] = set()
            cursor: str | None = start
            while cursor is not None and cursor in graph:
                if cursor in visited:
                    return None, STATUS_CONFLICT, ("FP11_SUPERSESSION_CYCLE",)
                visited.add(cursor)
                cursor = graph[cursor]

        heads = sorted(set(by_id) - superseded)
        if len(heads) != 1:
            return None, STATUS_CONFLICT, ("FP11_COMPETING_UNSUPERSEDED_HEADS",)
        if missing_predecessor:
            return by_id[heads[0]], STATUS_INCOMPLETE, ("FP11_SUPERSESSION_PREDECESSOR_MISSING",)

        visited: set[str] = set()
        cursor: str | None = heads[0]
        while cursor is not None:
            if cursor in visited:
                return None, STATUS_CONFLICT, ("FP11_SUPERSESSION_CYCLE",)
            visited.add(cursor)
            cursor = graph.get(cursor)
        if len(visited) != len(by_id):
            return None, STATUS_CONFLICT, ("FP11_DISCONNECTED_SUPERSESSION_HISTORY",)
        return by_id[heads[0]], CURRENT, ()

    def _fp04_reference_state(self, entry: Mapping[str, Any], fp11: Mapping[str, Any]) -> tuple[str, str | None]:
        evidence_id = entry.get("ownership_evidence_ref")
        if not isinstance(evidence_id, str):
            return STATUS_CONFLICT, "FP11_FP04_REFERENCE_INVALID"
        row = self._connection.execute(
            "SELECT * FROM external_provider_ownership_evidence WHERE ownership_evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return STATUS_INCOMPLETE, "FP11_FP04_DEPENDENCY_MISSING"
        try:
            payload = json.loads(row["payload_json"])
            if not isinstance(payload, dict):
                raise ValueError("payload not object")
            canonical = _canonical_json(payload)
            digest = _payload_hash(canonical)
        except (json.JSONDecodeError, ValueError, ProtectionRegistryCurrentnessError):
            return STATUS_CONFLICT, "FP11_FP04_STORED_PAYLOAD_INVALID"
        if canonical != row["payload_json"] or digest != row["payload_hash"]:
            return STATUS_CONFLICT, "FP11_FP04_STORED_HASH_MISMATCH"
        if entry.get("ownership_evidence_hash") != row["payload_hash"]:
            return STATUS_CONFLICT, "FP11_FP04_EVIDENCE_HASH_MISMATCH"
        if (
            payload.get("provider_object_class") != ACTIVE_PROTECTION
            or payload.get("provider_object_ref") != entry.get("provider_object_ref")
            or payload.get("provider_snapshot_ref") != entry.get("provider_snapshot_ref")
            or payload.get("provider_snapshot_hash") != entry.get("provider_snapshot_hash")
            or payload.get("provider_identity_ref") != fp11.get("provider_identity_ref")
            or payload.get("provider_instrument_ref") != fp11.get("provider_instrument_ref")
            or payload.get("provider_observation_generation_id") != fp11.get("provider_observation_generation_id")
            or payload.get("provider_observed_at") != entry.get("provider_object_observed_at")
            or payload.get("ownership_classification") != entry.get("ownership_classification")
            or payload.get("reconciliation_status") != entry.get("ownership_reconciliation_status")
        ):
            return STATUS_CONFLICT, "FP11_FP04_PROVIDER_OR_OWNERSHIP_BINDING_MISMATCH"

        object_rows = self._connection.execute(
            """
            SELECT * FROM external_provider_ownership_evidence
            WHERE provider_object_class = ? AND provider_identity_ref = ? AND provider_object_ref = ?
            """,
            (ACTIVE_PROTECTION, payload.get("provider_identity_ref"), payload.get("provider_object_ref")),
        ).fetchall()
        object_by_id = {item["ownership_evidence_id"]: item for item in object_rows}
        superseded: set[str] = set()
        for item in object_rows:
            try:
                item_payload = json.loads(item["payload_json"])
            except json.JSONDecodeError:
                return STATUS_CONFLICT, "FP11_FP04_STORED_PAYLOAD_INVALID"
            predecessor = item_payload.get("supersedes_ownership_evidence_id") if isinstance(item_payload, dict) else None
            if predecessor is not None:
                if predecessor not in object_by_id:
                    return STATUS_INCOMPLETE, "FP11_FP04_SUPERSESSION_PREDECESSOR_MISSING"
                superseded.add(predecessor)
        heads = set(object_by_id) - superseded
        if len(heads) != 1:
            return STATUS_CONFLICT, "FP11_FP04_COMPETING_CURRENT_HEADS"
        if evidence_id not in heads:
            return STATUS_STALE, "FP11_FP04_REFERENCE_SUPERSEDED"
        return CURRENT, None

    @staticmethod
    def _status_rank(status: str) -> int:
        return {
            HEALTHY_UNIQUE_PROTECTION: 0,
            STATUS_RECONCILIATION_REQUIRED: 1,
            STATUS_STALE: 2,
            STATUS_UNKNOWN: 3,
            STATUS_INCOMPLETE: 4,
            STATUS_CONFLICT: 5,
        }[status]

    @classmethod
    def _merge_status(cls, current: str, incoming: str) -> str:
        return incoming if cls._status_rank(incoming) > cls._status_rank(current) else current

    def recover(self, authority: ProtectionRegistryCurrentAuthority) -> ProtectionRegistryReadModel:
        try:
            current = _validate_authority(authority)
        except ProtectionRegistryCurrentnessError as exc:
            return ProtectionRegistryReadModel(
                status=STATUS_UNKNOWN,
                reason_codes=(exc.code,),
                position_id=None,
                current_fp11=None,
                current_interpretation=None,
                current_lifecycle_projection_id=None,
                current_lifecycle_state=None,
                healthy_protection=False,
                terminal_close_dependency=False,
                provider_mutation_authorized=False,
                cleanup_target_ref=None,
            )

        status = HEALTHY_UNIQUE_PROTECTION
        reasons: list[str] = []
        current_interpretation: StoredProtectionRegistryRecord | None = None
        terminal_dependency = False

        def add(incoming: str, reason: str) -> None:
            nonlocal status
            status = self._merge_status(status, incoming)
            if reason not in reasons:
                reasons.append(reason)

        head_row, head_status, head_reasons = self._resolve_head(current)
        for reason in head_reasons:
            add(head_status, reason)
        if head_row is None:
            return ProtectionRegistryReadModel(
                status=status,
                reason_codes=tuple(reasons),
                position_id=current["position_id"],
                current_fp11=None,
                current_interpretation=None,
                current_lifecycle_projection_id=current["projection_id"],
                current_lifecycle_state=current["lifecycle_state"],
                healthy_protection=False,
                terminal_close_dependency=False,
                provider_mutation_authorized=False,
                cleanup_target_ref=None,
            )

        current_fp11 = self._stored(
            "FP11_PROTECTION_REGISTRY_EVIDENCE",
            head_row["protection_registry_evidence_id"],
            head_row,
        )
        try:
            fp11, canonical, digest, lineage_key_hash = _validate_fp11(current_fp11.payload)
            if canonical != head_row["payload_json"] or digest != head_row["payload_hash"] or lineage_key_hash != head_row["lineage_key_hash"]:
                raise ProtectionRegistryValidationError("STORED_FP11_CANONICAL_MISMATCH", "stored FP-11 canonical mismatch")
        except ProtectionRegistryCurrentnessError:
            add(STATUS_CONFLICT, "STORED_FP11_INVALID")
            fp11 = {}

        exact_pairs = (
            ("position_id", current["position_id"]),
            ("position_ref", current["position_ref"]),
            ("position_hash", current["position_hash"]),
            ("position_observed_at", current["position_observed_at"]),
            ("intended_protection_lineage_hash", current["lineage_hash"]),
            ("provider_identity_ref", current["provider_identity_ref"]),
            ("provider_instrument_ref", current["provider_instrument_ref"]),
            ("provider_observation_generation_id", current["provider_observation_generation_id"]),
            ("provider_observed_at", current["provider_observed_at"]),
            ("provider_received_at", current["provider_received_at"]),
            ("observed_active_protection_set_hash", current["provider_set_hash"]),
            ("lifecycle_projection_ref", current["projection_id"]),
            ("lifecycle_execution_binding_ref", current["binding_id"]),
            ("runtime_preflight_ref", current["runtime_preflight_ref"]),
            ("runtime_process_instance_id", current["runtime_process_instance_id"]),
            ("runtime_process_start_generation_id", current["runtime_process_start_generation_id"]),
            ("runtime_config_generation_id", current["runtime_config_generation_id"]),
        )
        if any(fp11.get(field) != expected for field, expected in exact_pairs):
            add(STATUS_STALE, "FP11_CURRENT_AUTHORITY_MISMATCH")
        if fp11.get("intended_protection_lineage") != current["lineage"]:
            add(STATUS_STALE, "FP11_INTENDED_LINEAGE_SUPERSEDED_OR_MISMATCHED")

        if fp11.get("provider_set_currentness_status") == STALE:
            add(STATUS_STALE, "FP11_PROVIDER_SET_STALE")
        elif fp11.get("provider_set_currentness_status") == UNKNOWN:
            add(STATUS_UNKNOWN, "FP11_PROVIDER_SET_UNKNOWN")
        if fp11.get("observation_coverage_status") == UNKNOWN:
            add(STATUS_UNKNOWN, "FP11_PROVIDER_COVERAGE_UNKNOWN")
        elif fp11.get("observation_coverage_status") != COMPLETE:
            add(STATUS_RECONCILIATION_REQUIRED, "FP11_PROVIDER_COVERAGE_INCOMPLETE")

        for entry in fp11.get("observed_active_protection_objects", []):
            dep_status, dep_reason = self._fp04_reference_state(entry, fp11)
            if dep_reason is not None:
                add(dep_status, dep_reason)

        projection_current = self._connection.execute(
            "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
            (current["position_id"],),
        ).fetchone()
        if projection_current is None:
            add(STATUS_INCOMPLETE, "CURRENT_LIFECYCLE_PROJECTION_MISSING")
        elif (
            projection_current["lifecycle_projection_id"] != current["projection_id"]
            or projection_current["lifecycle_revision"] != current["lifecycle_revision"]
            or projection_current["payload_hash"] != current["position_hash"]
        ):
            add(STATUS_STALE, "CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED")

        projection_row = self._connection.execute(
            "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
            (current["projection_id"],),
        ).fetchone()
        if projection_row is None:
            add(STATUS_INCOMPLETE, "FP11_LIFECYCLE_PROJECTION_DEPENDENCY_MISSING")
        elif projection_row["payload_hash"] != current["position_hash"]:
            add(STATUS_CONFLICT, "FP11_LIFECYCLE_PROJECTION_HASH_MISMATCH")

        binding_row = self._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE lifecycle_projection_id = ?",
            (current["projection_id"],),
        ).fetchone()
        if current["binding_id"] is None:
            if fp11.get("lifecycle_execution_binding_ref") is not None:
                add(STATUS_STALE, "FP11_LIFECYCLE_BINDING_CURRENTNESS_MISMATCH")
        elif binding_row is None:
            add(STATUS_INCOMPLETE, "FP11_LIFECYCLE_BINDING_DEPENDENCY_MISSING")
        elif binding_row["lifecycle_execution_binding_id"] != current["binding_id"]:
            add(STATUS_STALE, "FP11_LIFECYCLE_BINDING_SUPERSEDED_OR_MISMATCHED")

        decision_rows = self._connection.execute(
            """
            SELECT * FROM protection_registry_policy_interpretations
            WHERE source_registry_evidence_id = ? AND position_id = ?
            ORDER BY decision_id
            """,
            (head_row["protection_registry_evidence_id"], current["position_id"]),
        ).fetchall()
        decision: dict[str, Any] = {}
        if not decision_rows:
            add(STATUS_INCOMPLETE, "CURRENT_E5_FP11_INTERPRETATION_MISSING")
        elif len(decision_rows) > 1:
            add(STATUS_CONFLICT, "COMPETING_E5_FP11_INTERPRETATIONS")
        else:
            decision_row = decision_rows[0]
            current_interpretation = self._stored(
                "E5_FP11_POLICY_INTERPRETATION",
                decision_row["decision_id"],
                decision_row,
            )
            try:
                decision, canonical, digest = _validate_decision(current_interpretation.payload)
                if canonical != decision_row["payload_json"] or digest != decision_row["payload_hash"]:
                    raise ProtectionRegistryValidationError("STORED_E5_FP11_DECISION_CANONICAL_MISMATCH", "stored decision mismatch")
            except ProtectionRegistryCurrentnessError:
                add(STATUS_CONFLICT, "STORED_E5_FP11_INTERPRETATION_INVALID")
                decision = {}

            if decision.get("source_registry_evidence_hash") != _sha256_json(fp11):
                add(STATUS_CONFLICT, "E5_FP11_SOURCE_HASH_MISMATCH")
            if decision.get("source_registry_material_hash") != _fp11_material_hash(fp11):
                add(STATUS_STALE, "E5_FP11_SOURCE_MATERIAL_SUPERSEDED")
            for field, expected in (
                ("position_id", current["position_id"]),
                ("position_ref", current["position_ref"]),
                ("position_hash", current["position_hash"]),
                ("position_observed_at", current["position_observed_at"]),
                ("lifecycle_projection_id", current["projection_id"]),
                ("lifecycle_revision", current["lifecycle_revision"]),
                ("lifecycle_execution_binding_id", current["binding_id"]),
            ):
                if decision.get(field) != expected:
                    add(STATUS_STALE, "E5_FP11_CURRENT_AUTHORITY_MISMATCH")
                    break
            if decision.get("evidence_current") is not True:
                add(STATUS_STALE, "E5_FP11_INTERPRETATION_NOT_CURRENT")
            if decision.get("provider_mutation_authorized") is not False or decision.get("cleanup_target_ref") is not None:
                add(STATUS_CONFLICT, "E5_FP11_FORBIDDEN_MUTATION_AUTHORITY")
            terminal_dependency = bool(decision.get("terminal_close_dependency"))

        if FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED in fp11.get("required_dispositions", []):
            terminal_dependency = True
            add(
                STATUS_RECONCILIATION_REQUIRED,
                FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED,
            )

        if current["quantity"] == 0 and fp11.get("active_protection_count", 0) > 0:
            terminal_dependency = True
            add(STATUS_RECONCILIATION_REQUIRED, "FP11_FLAT_POSITION_ACTIVE_PROTECTION_UNRESOLVED")
        if current["lifecycle_state"] == "CLOSED" and fp11.get("active_protection_count", 0) > 0:
            terminal_dependency = True
            add(STATUS_RECONCILIATION_REQUIRED, "FP11_FALSE_GREEN_CLOSED_PROTECTION_BLOCKED")

        evidence_success = (
            fp11.get("multiplicity_state") == EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
            and fp11.get("registry_status") == CONVERGED_EXACTLY_ONE_INTENDED
            and fp11.get("required_dispositions") == [NO_ACTION_REGISTRY_CONVERGED]
            and fp11.get("reason_codes") == [EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED]
            and fp11.get("provider_set_currentness_status") == CURRENT
            and fp11.get("observation_coverage_status") == COMPLETE
            and fp11.get("active_protection_count") == 1
        )
        decision_success = (
            bool(decision)
            and decision.get("healthy_protection") is True
            and decision.get("evidence_current") is True
            and decision.get("provider_mutation_authorized") is False
            and decision.get("cleanup_target_ref") is None
            and decision.get("next_state") == current["lifecycle_state"]
            and current["lifecycle_state"] in {"OPEN_PROTECTED", "PROFIT_PROTECTED"}
            and current["quantity"] > 0
            and not terminal_dependency
        )

        if not evidence_success:
            if fp11.get("provider_set_currentness_status") == STALE or fp11.get("multiplicity_state") == "PROTECTION_SET_STALE":
                add(STATUS_STALE, "FP11_NONCURRENT_REGISTRY_EVIDENCE")
            elif fp11.get("registry_status") == UNKNOWN or fp11.get("multiplicity_state") == "PROTECTION_SET_UNKNOWN":
                add(STATUS_UNKNOWN, "FP11_REGISTRY_UNKNOWN")
            else:
                add(STATUS_RECONCILIATION_REQUIRED, "FP11_REGISTRY_NOT_CONVERGED")
        if evidence_success and not decision_success:
            add(STATUS_RECONCILIATION_REQUIRED, "FP11_HEALTHY_EVIDENCE_REQUIRES_CURRENT_E5_INTERPRETATION")

        healthy = status == HEALTHY_UNIQUE_PROTECTION and evidence_success and decision_success
        if not healthy and status == HEALTHY_UNIQUE_PROTECTION:
            status = STATUS_RECONCILIATION_REQUIRED

        return ProtectionRegistryReadModel(
            status=status,
            reason_codes=tuple(reasons),
            position_id=current["position_id"],
            current_fp11=current_fp11,
            current_interpretation=current_interpretation,
            current_lifecycle_projection_id=current["projection_id"],
            current_lifecycle_state=current["lifecycle_state"],
            healthy_protection=healthy,
            terminal_close_dependency=terminal_dependency,
            provider_mutation_authorized=False,
            cleanup_target_ref=None,
        )


def open_protection_registry_currentness_store(path: str | Path) -> ProtectionRegistryCurrentnessStore:
    connection = _connect(path)
    try:
        _apply_migrations(connection)
        return ProtectionRegistryCurrentnessStore(connection)
    except Exception:
        connection.close()
        raise


__all__ = [
    "HEALTHY_UNIQUE_PROTECTION",
    "STATUS_CONFLICT",
    "STATUS_INCOMPLETE",
    "STATUS_RECONCILIATION_REQUIRED",
    "STATUS_STALE",
    "STATUS_UNKNOWN",
    "ProtectionRegistryConflictError",
    "ProtectionRegistryCurrentAuthority",
    "ProtectionRegistryCurrentnessError",
    "ProtectionRegistryCurrentnessStore",
    "ProtectionRegistryReadModel",
    "ProtectionRegistryValidationError",
    "StoredProtectionRegistryRecord",
    "open_protection_registry_currentness_store",
]
