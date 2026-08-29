from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._sqlite_registry import _apply_migrations, _connect

SCHEMA_VERSION = "contracts-v0.1"
FP04_PROFILE_VERSION = "external-provider-object-ownership-reconciliation-v0.1"
FP10_PROFILE_VERSION = "external-manual-close-lifecycle-convergence-v0.1"

CURRENT = "CURRENT"
STALE = "STALE"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"

STATUS_CURRENT = "CURRENT"
STATUS_RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_CONFLICT = "CONFLICT"

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FP04_ID_RE = re.compile(r"^extownrec_[0-9a-f]{64}$")
_FP10_ID_RE = re.compile(r"^extcloseconv_[0-9a-f]{64}$")
_E5_DECISION_ID_RE = re.compile(r"^e5extclose_[0-9a-f]{64}$")

_FP04_FIELDS = frozenset(
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
_FP04_LINEAGE_FIELDS = frozenset(
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
_FP04_REGISTRY_FIELDS = frozenset(
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
_FP10_FIELDS = frozenset(
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
_FP10_EXECUTION_FIELDS = frozenset(
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
_FP10_FP04_FIELDS = frozenset(
    {
        "provider_object_class",
        "provider_object_ref",
        "provider_snapshot_hash",
        "ownership_evidence_ref",
        "ownership_evidence_hash",
        "ownership_classification",
        "ownership_reconciliation_status",
        "ownership_currentness_status",
    }
)
_DECISION_ENVELOPE_FIELDS = frozenset(
    {
        "decision_id",
        "position_id",
        "close_convergence_evidence_id",
        "close_convergence_evidence_hash",
        "lifecycle_projection_ref",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "lifecycle_execution_binding_ref",
        "lifecycle_execution_binding_id",
        "decision",
        "event",
        "next_state",
        "reason_codes",
        "close_eligible",
        "trade_result_evidence_incomplete",
        "evidence_current",
    }
)

_FP10_STATES = frozenset(
    {
        "EXPOSURE_STILL_OPEN",
        "EXPOSURE_REDUCED_NOT_FLAT",
        "FLAT_PROVIDER_TRUTH_PROVEN",
        "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED",
        "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
        "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED",
        "OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED",
        "RESIDUAL_UNREPRESENTABLE_NOT_FLAT",
        "CONVERGENCE_EVIDENCE_STALE",
        "CONVERGENCE_UNKNOWN",
        "LIFECYCLE_CLOSE_ELIGIBLE",
    }
)
_FP10_TERMINAL_PROTECTION = frozenset(
    {
        "TERMINAL_PROTECTION_CLEAR",
        "TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED",
        "TERMINAL_PROTECTION_OBSERVATION_STALE",
        "TERMINAL_PROTECTION_OBSERVATION_UNKNOWN",
    }
)


class ExternalCloseCurrentnessError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ExternalCloseValidationError(ExternalCloseCurrentnessError):
    pass


class ExternalCloseConflictError(ExternalCloseCurrentnessError):
    pass


@dataclass(frozen=True)
class StoredExternalRecord:
    object_kind: str
    canonical_id: str
    payload_json: str
    payload_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise ExternalCloseValidationError("STORED_PAYLOAD_NOT_OBJECT", "stored payload is not a JSON object")
        return value


@dataclass(frozen=True)
class ExternalCloseCurrentProjection:
    status: str
    reason_codes: tuple[str, ...]
    position_id: str
    current_fp10: StoredExternalRecord | None
    current_decision: StoredExternalRecord | None
    referenced_fp04: tuple[StoredExternalRecord, ...]
    current_lifecycle_projection_id: str | None
    current_lifecycle_state: str | None
    trade_result_evidence_incomplete: bool
    closed_presentation_allowed: bool


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ExternalCloseValidationError("NONCANONICAL_KEY", "canonical mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise ExternalCloseValidationError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden in canonical evidence")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ExternalCloseValidationError(
        "NONCANONICAL_VALUE",
        f"unsupported canonical evidence type: {type(value).__name__}",
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
        raise ExternalCloseValidationError("NONCANONICAL_JSON", "evidence is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _payload_hash(payload_json: str) -> str:
    return "sha256:" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExternalCloseValidationError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise ExternalCloseValidationError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _optional_hash(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _hash(value, field)


def _utc(value: Any, field: str) -> datetime:
    text = _text(value, field)
    if not text.endswith("Z"):
        raise ExternalCloseValidationError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ExternalCloseValidationError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalCloseValidationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _string_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise ExternalCloseValidationError("INVALID_SEQUENCE", f"{field} must be a list")
    result = [_text(item, f"{field}[]") for item in value]
    if nonempty and not result:
        raise ExternalCloseValidationError("INVALID_SEQUENCE", f"{field} must not be empty")
    if len(result) != len(set(result)):
        raise ExternalCloseValidationError("DUPLICATE_SEQUENCE_VALUE", f"{field} must not contain duplicates")
    return result


def _optional_pair(ref: Any, digest: Any, ref_field: str, hash_field: str) -> tuple[str | None, str | None]:
    if ref is None and digest is None:
        return None, None
    if ref is None or digest is None:
        raise ExternalCloseValidationError("REFERENCE_HASH_PAIR_INCOMPLETE", f"{ref_field}/{hash_field} must both be set or null")
    return _text(ref, ref_field), _hash(digest, hash_field)


def _validate_mapping_sequence(
    value: Any,
    *,
    fields: frozenset[str],
    sort_fields: tuple[str, ...],
    label: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ExternalCloseValidationError("INVALID_SEQUENCE", f"{label} must be a list")
    result: list[dict[str, Any]] = []
    keys: list[tuple[Any, ...]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != fields:
            raise ExternalCloseValidationError("INVALID_SEQUENCE_FIELDS", f"{label} entry fields mismatch")
        material = dict(item)
        result.append(material)
        keys.append(tuple(material.get(field) for field in sort_fields))
    if keys != sorted(keys) or len(keys) != len(set(keys)):
        raise ExternalCloseValidationError("NONDETERMINISTIC_SEQUENCE", f"{label} must be uniquely sorted")
    return result


def _stable_fp04_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("ownership_evidence_id", None)
    return "extownrec_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _stable_fp10_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("close_convergence_evidence_id", None)
    return "extcloseconv_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _stable_e5_decision_id(material: Mapping[str, Any]) -> str:
    return "e5extclose_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _validate_fp04(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    material = _canonicalize(payload)
    if not isinstance(material, dict) or set(material) != _FP04_FIELDS:
        raise ExternalCloseValidationError("FP04_FIELDS_INVALID", "FP-04 evidence fields mismatch")
    if material.get("schema_version") != SCHEMA_VERSION:
        raise ExternalCloseValidationError("FP04_SCHEMA_UNSUPPORTED", "FP-04 schema unsupported")
    if material.get("external_provider_ownership_profile_version") != FP04_PROFILE_VERSION:
        raise ExternalCloseValidationError("FP04_PROFILE_UNSUPPORTED", "FP-04 profile unsupported")

    evidence_id = _text(material.get("ownership_evidence_id"), "ownership_evidence_id")
    if _FP04_ID_RE.fullmatch(evidence_id) is None:
        raise ExternalCloseValidationError("FP04_ID_INVALID", "ownership_evidence_id is invalid")
    if evidence_id != _stable_fp04_id(material):
        raise ExternalCloseValidationError("FP04_IDENTITY_MISMATCH", "ownership evidence identity mismatch")

    for field in (
        "provider_object_class",
        "provider_identity_ref",
        "canonical_symbol",
        "provider_instrument_ref",
        "provider_object_ref",
        "provider_snapshot_ref",
        "provider_observation_generation_id",
        "current_project_revision",
        "ownership_classification",
        "reconciliation_status",
    ):
        _text(material.get(field), field)
    _hash(material.get("provider_identity_hash"), "provider_identity_hash")
    _hash(material.get("provider_snapshot_hash"), "provider_snapshot_hash")

    observed = _utc(material.get("provider_observed_at"), "provider_observed_at")
    received = _utc(material.get("provider_received_at"), "provider_received_at")
    evaluated = _utc(material.get("evaluated_at"), "evaluated_at")
    if received < observed or evaluated < received:
        raise ExternalCloseValidationError("FP04_TEMPORAL_ORDER_INVALID", "FP-04 temporal ordering is invalid")

    lineage = _validate_mapping_sequence(
        material.get("local_lineage_evidence"),
        fields=_FP04_LINEAGE_FIELDS,
        sort_fields=("owner", "evidence_class", "evidence_ref"),
        label="local_lineage_evidence",
    )
    for item in lineage:
        _hash(item.get("evidence_hash"), "local_lineage_evidence[].evidence_hash")
        _utc(item.get("observed_or_created_at"), "local_lineage_evidence[].observed_or_created_at")

    registry = _validate_mapping_sequence(
        material.get("local_registry_evidence"),
        fields=_FP04_REGISTRY_FIELDS,
        sort_fields=("owner", "evidence_class", "evidence_ref"),
        label="local_registry_evidence",
    )
    for item in registry:
        _hash(item.get("evidence_hash"), "local_registry_evidence[].evidence_hash")
        _utc(item.get("observed_at"), "local_registry_evidence[].observed_at")

    dispositions = _string_list(material.get("required_dispositions"), "required_dispositions", nonempty=True)
    if dispositions != sorted(dispositions):
        raise ExternalCloseValidationError("FP04_DISPOSITION_ORDER_INVALID", "FP-04 dispositions must be sorted")
    _string_list(material.get("reason_codes"), "reason_codes", nonempty=True)

    for field in (
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
        "adoption_decision_ref",
    ):
        _optional_text(material.get(field), field)
    supersedes = material.get("supersedes_ownership_evidence_id")
    if supersedes is not None:
        supersedes = _text(supersedes, "supersedes_ownership_evidence_id")
        if _FP04_ID_RE.fullmatch(supersedes) is None or supersedes == evidence_id:
            raise ExternalCloseValidationError("FP04_SUPERSESSION_INVALID", "FP-04 supersession reference is invalid")

    payload_json = _canonical_json(material)
    return material, payload_json, _payload_hash(payload_json)


def _validate_fp10(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    material = _canonicalize(payload)
    if not isinstance(material, dict) or set(material) != _FP10_FIELDS:
        raise ExternalCloseValidationError("FP10_FIELDS_INVALID", "FP-10 evidence fields mismatch")
    if material.get("schema_version") != SCHEMA_VERSION:
        raise ExternalCloseValidationError("FP10_SCHEMA_UNSUPPORTED", "FP-10 schema unsupported")
    if material.get("external_manual_close_convergence_profile_version") != FP10_PROFILE_VERSION:
        raise ExternalCloseValidationError("FP10_PROFILE_UNSUPPORTED", "FP-10 profile unsupported")

    evidence_id = _text(material.get("close_convergence_evidence_id"), "close_convergence_evidence_id")
    if _FP10_ID_RE.fullmatch(evidence_id) is None:
        raise ExternalCloseValidationError("FP10_ID_INVALID", "close_convergence_evidence_id is invalid")
    if evidence_id != _stable_fp10_id(material):
        raise ExternalCloseValidationError("FP10_IDENTITY_MISMATCH", "FP-10 evidence identity mismatch")

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
        "normalized_actual_quantity",
        "normalized_quantity_profile_version",
        "normalized_quantity_unit",
        "normalized_quantity_asset",
        "fp05_residual_state",
        "terminal_protection_observation_ref",
        "lifecycle_projection_ref",
        "lifecycle_projection_id",
        "lifecycle_state",
        "lifecycle_execution_binding_ref",
        "current_project_revision",
        "exposure_change_origin_classification",
        "convergence_state",
    ):
        _text(material.get(field), field)
    if material.get("convergence_state") not in _FP10_STATES:
        raise ExternalCloseValidationError("FP10_STATE_UNSUPPORTED", "FP-10 convergence_state unsupported")
    if material.get("provider_position_currentness_status") not in {CURRENT, STALE, UNKNOWN}:
        raise ExternalCloseValidationError("FP10_CURRENTNESS_UNSUPPORTED", "FP-10 provider Position currentness unsupported")
    if material.get("terminal_protection_status") not in _FP10_TERMINAL_PROTECTION:
        raise ExternalCloseValidationError("FP10_TERMINAL_PROTECTION_UNSUPPORTED", "FP-10 terminal protection status unsupported")

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
        _hash(material.get(field), field)

    _optional_pair(
        material.get("fp05_close_residual_sizing_ref"),
        material.get("fp05_close_residual_sizing_hash"),
        "fp05_close_residual_sizing_ref",
        "fp05_close_residual_sizing_hash",
    )
    _optional_pair(
        material.get("fp11_prior_registry_evidence_ref"),
        material.get("fp11_prior_registry_evidence_hash"),
        "fp11_prior_registry_evidence_ref",
        "fp11_prior_registry_evidence_hash",
    )

    provider_observed = _utc(material.get("provider_position_observed_at"), "provider_position_observed_at")
    provider_received = _utc(material.get("provider_position_received_at"), "provider_position_received_at")
    terminal_observed = _utc(material.get("terminal_protection_observed_at"), "terminal_protection_observed_at")
    terminal_received = _utc(material.get("terminal_protection_received_at"), "terminal_protection_received_at")
    evaluated = _utc(material.get("evaluated_at"), "evaluated_at")
    if provider_received < provider_observed or terminal_received < terminal_observed:
        raise ExternalCloseValidationError("FP10_TEMPORAL_ORDER_INVALID", "FP-10 receipt precedes observation")
    if evaluated < provider_received or evaluated < terminal_received:
        raise ExternalCloseValidationError("FP10_TEMPORAL_ORDER_INVALID", "FP-10 evaluation predates required evidence")

    execution = _validate_mapping_sequence(
        material.get("execution_evidence"),
        fields=_FP10_EXECUTION_FIELDS,
        sort_fields=("evidence_class", "owner", "evidence_ref", "evidence_hash"),
        label="execution_evidence",
    )
    for item in execution:
        _hash(item.get("evidence_hash"), "execution_evidence[].evidence_hash")
        _utc(item.get("latest_observed_at"), "execution_evidence[].latest_observed_at")
    if material.get("execution_evidence_set_hash") != _sha256_json(execution):
        raise ExternalCloseValidationError("FP10_EXECUTION_SET_HASH_MISMATCH", "FP-10 execution evidence set hash mismatch")

    fp04_rows = _validate_mapping_sequence(
        material.get("fp04_ownership_evidence"),
        fields=_FP10_FP04_FIELDS,
        sort_fields=("provider_object_class", "provider_object_ref", "ownership_evidence_ref"),
        label="fp04_ownership_evidence",
    )
    for item in fp04_rows:
        _hash(item.get("provider_snapshot_hash"), "fp04_ownership_evidence[].provider_snapshot_hash")
        _hash(item.get("ownership_evidence_hash"), "fp04_ownership_evidence[].ownership_evidence_hash")
        if item.get("ownership_currentness_status") not in {CURRENT, STALE, CONFLICT, UNKNOWN}:
            raise ExternalCloseValidationError("FP10_FP04_CURRENTNESS_INVALID", "FP-10 FP-04 currentness unsupported")
    if material.get("fp04_evidence_set_hash") != _sha256_json(fp04_rows):
        raise ExternalCloseValidationError("FP10_FP04_SET_HASH_MISMATCH", "FP-10 FP-04 evidence set hash mismatch")

    revision = material.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise ExternalCloseValidationError("FP10_LIFECYCLE_REVISION_INVALID", "lifecycle_revision must be non-negative integer")
    for field in (
        "runtime_preflight_ref",
        "runtime_process_instance_id",
        "runtime_process_start_generation_id",
        "runtime_config_generation_id",
    ):
        _optional_text(material.get(field), field)
    _string_list(material.get("required_dispositions"), "required_dispositions", nonempty=True)
    _string_list(material.get("reason_codes"), "reason_codes", nonempty=True)

    supersedes = material.get("supersedes_close_convergence_evidence_id")
    if supersedes is not None:
        supersedes = _text(supersedes, "supersedes_close_convergence_evidence_id")
        if _FP10_ID_RE.fullmatch(supersedes) is None or supersedes == evidence_id:
            raise ExternalCloseValidationError("FP10_SUPERSESSION_INVALID", "FP-10 supersession reference is invalid")

    payload_json = _canonical_json(material)
    return material, payload_json, _payload_hash(payload_json)


def _decision_attr(decision: Any, field: str) -> Any:
    if isinstance(decision, Mapping):
        if field not in decision:
            raise ExternalCloseValidationError("E5_DECISION_FIELD_MISSING", f"E5 decision missing {field}")
        value = decision[field]
    else:
        if not hasattr(decision, field):
            raise ExternalCloseValidationError("E5_DECISION_FIELD_MISSING", f"E5 decision missing {field}")
        value = getattr(decision, field)
    if isinstance(value, Enum):
        return value.value
    return value


def _validate_decision_envelope(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    material = _canonicalize(payload)
    if not isinstance(material, dict) or set(material) != _DECISION_ENVELOPE_FIELDS:
        raise ExternalCloseValidationError("E5_DECISION_FIELDS_INVALID", "E5 decision audit envelope fields mismatch")
    decision_id = _text(material.get("decision_id"), "decision_id")
    if _E5_DECISION_ID_RE.fullmatch(decision_id) is None:
        raise ExternalCloseValidationError("E5_DECISION_ID_INVALID", "E5 decision ID is invalid")
    position_id = _text(material.get("position_id"), "position_id")
    fp10_id = _text(material.get("close_convergence_evidence_id"), "close_convergence_evidence_id")
    if _FP10_ID_RE.fullmatch(fp10_id) is None:
        raise ExternalCloseValidationError("E5_DECISION_FP10_ID_INVALID", "E5 decision FP-10 reference is invalid")
    _hash(material.get("close_convergence_evidence_hash"), "close_convergence_evidence_hash")
    projection_ref = _text(material.get("lifecycle_projection_ref"), "lifecycle_projection_ref")
    projection_id = _text(material.get("lifecycle_projection_id"), "lifecycle_projection_id")
    revision = material.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise ExternalCloseValidationError("E5_DECISION_LIFECYCLE_REVISION_INVALID", "decision lifecycle_revision invalid")
    binding_ref = _optional_text(material.get("lifecycle_execution_binding_ref"), "lifecycle_execution_binding_ref")
    binding_id = _optional_text(material.get("lifecycle_execution_binding_id"), "lifecycle_execution_binding_id")
    _text(material.get("decision"), "decision")
    _optional_text(material.get("event"), "event")
    _text(material.get("next_state"), "next_state")
    reasons = _string_list(material.get("reason_codes"), "reason_codes", nonempty=True)
    for field in ("close_eligible", "trade_result_evidence_incomplete", "evidence_current"):
        if type(material.get(field)) is not bool:
            raise ExternalCloseValidationError("E5_DECISION_BOOLEAN_INVALID", f"{field} must be boolean")

    id_material = {
        "close_convergence_evidence_id": fp10_id,
        "position_id": position_id,
        "lifecycle_projection_id": projection_id,
        "lifecycle_revision": revision,
        "lifecycle_execution_binding_id": binding_id,
        "evidence_current": material["evidence_current"],
        "decision": material["decision"],
        "event": material["event"],
        "next_state": material["next_state"],
        "reason_codes": reasons,
        "close_eligible": material["close_eligible"],
        "trade_result_evidence_incomplete": material["trade_result_evidence_incomplete"],
    }
    if decision_id != _stable_e5_decision_id(id_material):
        raise ExternalCloseValidationError("E5_DECISION_IDENTITY_MISMATCH", "E5 decision identity does not match accepted producer material")

    # Keep exact refs in the immutable E6 envelope even though E5's deterministic
    # decision ID is intentionally based on IDs/revision rather than storage refs.
    _ = projection_ref, binding_ref
    payload_json = _canonical_json(material)
    return material, payload_json, _payload_hash(payload_json)


class ExternalCloseCurrentnessStore:
    """E6-only provider-neutral FP-04/FP-10 persistence and restart currentness consumer.

    The store persists owner-produced immutable material and validates only exact
    references, hashes, deterministic identities, supersession chains, and the
    already-persisted Position lifecycle projection/binding. It never infers
    provider ownership, flatness, lifecycle events, cleanup targets, or mutation
    authority.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    def _record_conflict(
        self,
        reason_code: str,
        object_kind: str,
        *,
        canonical_id: str | None = None,
        position_id: str | None = None,
        existing_payload_hash: str | None = None,
        incoming_payload_hash: str | None = None,
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
        raise ExternalCloseConflictError(
            "IMMUTABLE_ID_PAYLOAD_CONFLICT",
            f"{object_kind} ID already exists with different canonical content",
        )

    @staticmethod
    def _stored(kind: str, canonical_id: str, row: sqlite3.Row) -> StoredExternalRecord:
        return StoredExternalRecord(kind, canonical_id, row["payload_json"], row["payload_hash"])

    def persist_fp04(self, evidence: Mapping[str, Any]) -> StoredExternalRecord:
        declared_id = evidence.get("ownership_evidence_id") if isinstance(evidence, Mapping) else None
        incoming_json = _canonical_json(evidence) if isinstance(evidence, Mapping) else ""
        incoming_hash = _payload_hash(incoming_json) if incoming_json else None
        if isinstance(declared_id, str):
            existing = self._connection.execute(
                "SELECT * FROM external_provider_ownership_evidence WHERE ownership_evidence_id = ?",
                (declared_id,),
            ).fetchone()
            if existing is not None and existing["payload_json"] != incoming_json:
                self._immutable_conflict(
                    object_kind="FP04_OWNERSHIP_EVIDENCE",
                    canonical_id=declared_id,
                    position_id=None,
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=incoming_hash or "",
                )
            if existing is not None:
                _validate_fp04(json.loads(existing["payload_json"]))
                return self._stored("FP04_OWNERSHIP_EVIDENCE", declared_id, existing)

        material, payload_json, payload_hash = _validate_fp04(evidence)
        evidence_id = material["ownership_evidence_id"]
        self._connection.execute(
            """
            INSERT INTO external_provider_ownership_evidence (
                ownership_evidence_id, provider_object_class, provider_identity_ref,
                provider_object_ref, provider_snapshot_ref, provider_snapshot_hash,
                provider_observation_generation_id, supersedes_ownership_evidence_id,
                current_project_revision, evaluated_at, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                material["provider_object_class"],
                material["provider_identity_ref"],
                material["provider_object_ref"],
                material["provider_snapshot_ref"],
                material["provider_snapshot_hash"],
                material["provider_observation_generation_id"],
                material["supersedes_ownership_evidence_id"],
                material["current_project_revision"],
                material["evaluated_at"],
                payload_json,
                payload_hash,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM external_provider_ownership_evidence WHERE ownership_evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        assert row is not None
        return self._stored("FP04_OWNERSHIP_EVIDENCE", evidence_id, row)

    def persist_fp10(self, evidence: Mapping[str, Any]) -> StoredExternalRecord:
        declared_id = evidence.get("close_convergence_evidence_id") if isinstance(evidence, Mapping) else None
        incoming_json = _canonical_json(evidence) if isinstance(evidence, Mapping) else ""
        incoming_hash = _payload_hash(incoming_json) if incoming_json else None
        if isinstance(declared_id, str):
            existing = self._connection.execute(
                "SELECT * FROM external_manual_close_convergence_evidence WHERE close_convergence_evidence_id = ?",
                (declared_id,),
            ).fetchone()
            if existing is not None and existing["payload_json"] != incoming_json:
                position_id = evidence.get("position_id") if isinstance(evidence.get("position_id"), str) else None
                self._immutable_conflict(
                    object_kind="FP10_CLOSE_CONVERGENCE_EVIDENCE",
                    canonical_id=declared_id,
                    position_id=position_id,
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=incoming_hash or "",
                )
            if existing is not None:
                _validate_fp10(json.loads(existing["payload_json"]))
                return self._stored("FP10_CLOSE_CONVERGENCE_EVIDENCE", declared_id, existing)

        material, payload_json, payload_hash = _validate_fp10(evidence)
        evidence_id = material["close_convergence_evidence_id"]
        self._connection.execute(
            """
            INSERT INTO external_manual_close_convergence_evidence (
                close_convergence_evidence_id, position_id,
                provider_position_observation_generation_id,
                provider_position_snapshot_ref, provider_position_snapshot_hash,
                lifecycle_projection_id, lifecycle_revision, lifecycle_projection_hash,
                lifecycle_execution_binding_ref, lifecycle_execution_binding_hash,
                execution_evidence_set_hash, fp04_evidence_set_hash,
                terminal_protection_observation_ref, terminal_protection_observation_hash,
                convergence_state, supersedes_close_convergence_evidence_id,
                evaluated_at, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                material["position_id"],
                material["provider_position_observation_generation_id"],
                material["provider_position_snapshot_ref"],
                material["provider_position_snapshot_hash"],
                material["lifecycle_projection_id"],
                material["lifecycle_revision"],
                material["lifecycle_projection_hash"],
                material["lifecycle_execution_binding_ref"],
                material["lifecycle_execution_binding_hash"],
                material["execution_evidence_set_hash"],
                material["fp04_evidence_set_hash"],
                material["terminal_protection_observation_ref"],
                material["terminal_protection_observation_hash"],
                material["convergence_state"],
                material["supersedes_close_convergence_evidence_id"],
                material["evaluated_at"],
                payload_json,
                payload_hash,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM external_manual_close_convergence_evidence WHERE close_convergence_evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        assert row is not None
        return self._stored("FP10_CLOSE_CONVERGENCE_EVIDENCE", evidence_id, row)

    def persist_e5_reinterpretation_decision(
        self,
        decision: Any,
        *,
        position_id: str,
        close_convergence_evidence_id: str,
        close_convergence_evidence_hash: str,
        lifecycle_projection_ref: str,
        lifecycle_projection_id: str,
        lifecycle_revision: int,
        lifecycle_execution_binding_ref: str | None,
        lifecycle_execution_binding_id: str | None,
    ) -> StoredExternalRecord:
        event = _decision_attr(decision, "event")
        if isinstance(event, Enum):
            event = event.value
        next_state = _decision_attr(decision, "next_state")
        if isinstance(next_state, Enum):
            next_state = next_state.value
        reason_codes = _decision_attr(decision, "reason_codes")
        if isinstance(reason_codes, tuple):
            reason_codes = list(reason_codes)
        envelope = {
            "decision_id": _decision_attr(decision, "decision_id"),
            "position_id": position_id,
            "close_convergence_evidence_id": close_convergence_evidence_id,
            "close_convergence_evidence_hash": close_convergence_evidence_hash,
            "lifecycle_projection_ref": lifecycle_projection_ref,
            "lifecycle_projection_id": lifecycle_projection_id,
            "lifecycle_revision": lifecycle_revision,
            "lifecycle_execution_binding_ref": lifecycle_execution_binding_ref,
            "lifecycle_execution_binding_id": lifecycle_execution_binding_id,
            "decision": _decision_attr(decision, "decision"),
            "event": event,
            "next_state": next_state,
            "reason_codes": reason_codes,
            "close_eligible": _decision_attr(decision, "close_eligible"),
            "trade_result_evidence_incomplete": _decision_attr(decision, "trade_result_evidence_incomplete"),
            "evidence_current": _decision_attr(decision, "evidence_current"),
        }
        declared_id = envelope["decision_id"]
        incoming_json = _canonical_json(envelope)
        incoming_hash = _payload_hash(incoming_json)
        if isinstance(declared_id, str):
            existing = self._connection.execute(
                "SELECT * FROM external_close_reinterpretation_decisions WHERE decision_id = ?",
                (declared_id,),
            ).fetchone()
            if existing is not None and existing["payload_json"] != incoming_json:
                self._immutable_conflict(
                    object_kind="E5_EXTERNAL_CLOSE_REINTERPRETATION_DECISION",
                    canonical_id=declared_id,
                    position_id=position_id,
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=incoming_hash,
                )
            if existing is not None:
                _validate_decision_envelope(json.loads(existing["payload_json"]))
                return self._stored("E5_EXTERNAL_CLOSE_REINTERPRETATION_DECISION", declared_id, existing)

        material, payload_json, payload_hash = _validate_decision_envelope(envelope)
        self._connection.execute(
            """
            INSERT INTO external_close_reinterpretation_decisions (
                decision_id, position_id, close_convergence_evidence_id,
                close_convergence_evidence_hash, lifecycle_projection_ref,
                lifecycle_projection_id, lifecycle_revision,
                lifecycle_execution_binding_ref, lifecycle_execution_binding_id,
                decision, event, next_state, close_eligible,
                trade_result_evidence_incomplete, evidence_current,
                payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                material["decision_id"],
                material["position_id"],
                material["close_convergence_evidence_id"],
                material["close_convergence_evidence_hash"],
                material["lifecycle_projection_ref"],
                material["lifecycle_projection_id"],
                material["lifecycle_revision"],
                material["lifecycle_execution_binding_ref"],
                material["lifecycle_execution_binding_id"],
                material["decision"],
                material["event"],
                material["next_state"],
                1 if material["close_eligible"] else 0,
                1 if material["trade_result_evidence_incomplete"] else 0,
                1 if material["evidence_current"] else 0,
                payload_json,
                payload_hash,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM external_close_reinterpretation_decisions WHERE decision_id = ?",
            (material["decision_id"],),
        ).fetchone()
        assert row is not None
        return self._stored("E5_EXTERNAL_CLOSE_REINTERPRETATION_DECISION", material["decision_id"], row)

    def fp04_history(self, provider_object_class: str, provider_identity_ref: str, provider_object_ref: str) -> tuple[StoredExternalRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM external_provider_ownership_evidence
            WHERE provider_object_class = ? AND provider_identity_ref = ? AND provider_object_ref = ?
            ORDER BY ownership_evidence_id
            """,
            (provider_object_class, provider_identity_ref, provider_object_ref),
        ).fetchall()
        return tuple(self._stored("FP04_OWNERSHIP_EVIDENCE", row["ownership_evidence_id"], row) for row in rows)

    def fp10_history(self, position_id: str) -> tuple[StoredExternalRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM external_manual_close_convergence_evidence
            WHERE position_id = ? ORDER BY close_convergence_evidence_id
            """,
            (position_id,),
        ).fetchall()
        return tuple(self._stored("FP10_CLOSE_CONVERGENCE_EVIDENCE", row["close_convergence_evidence_id"], row) for row in rows)

    def decision_history(self, position_id: str) -> tuple[StoredExternalRecord, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM external_close_reinterpretation_decisions
            WHERE position_id = ? ORDER BY decision_id
            """,
            (position_id,),
        ).fetchall()
        return tuple(self._stored("E5_EXTERNAL_CLOSE_REINTERPRETATION_DECISION", row["decision_id"], row) for row in rows)

    def _resolve_fp10_head(self, position_id: str) -> tuple[sqlite3.Row | None, str, tuple[str, ...]]:
        rows = self._connection.execute(
            "SELECT * FROM external_manual_close_convergence_evidence WHERE position_id = ?",
            (position_id,),
        ).fetchall()
        if not rows:
            return None, STATUS_INCOMPLETE, ("FP10_EVIDENCE_MISSING",)

        by_id = {row["close_convergence_evidence_id"]: row for row in rows}
        payloads: dict[str, dict[str, Any]] = {}
        try:
            for evidence_id, row in by_id.items():
                material, payload_json, payload_hash = _validate_fp10(json.loads(row["payload_json"]))
                if payload_json != row["payload_json"] or payload_hash != row["payload_hash"] or material["close_convergence_evidence_id"] != evidence_id:
                    return None, STATUS_CONFLICT, ("STORED_FP10_CANONICAL_MISMATCH",)
                payloads[evidence_id] = material
        except (json.JSONDecodeError, ExternalCloseCurrentnessError):
            return None, STATUS_CONFLICT, ("STORED_FP10_INVALID",)

        superseded: set[str] = set()
        missing_predecessor = False
        for evidence_id, payload in payloads.items():
            predecessor = payload.get("supersedes_close_convergence_evidence_id")
            if predecessor is None:
                continue
            if predecessor not in by_id:
                missing_predecessor = True
                continue
            if payloads[predecessor].get("position_id") != position_id:
                return None, STATUS_CONFLICT, ("FP10_SUPERSESSION_LINEAGE_MISMATCH",)
            superseded.add(predecessor)

        heads = sorted(set(by_id) - superseded)
        if len(heads) != 1:
            return None, STATUS_CONFLICT, ("FP10_COMPETING_UNSUPERSEDED_HEADS",)
        head_id = heads[0]

        visited: set[str] = set()
        cursor: str | None = head_id
        while cursor is not None:
            if cursor in visited:
                return None, STATUS_CONFLICT, ("FP10_SUPERSESSION_CYCLE",)
            visited.add(cursor)
            predecessor = payloads[cursor].get("supersedes_close_convergence_evidence_id")
            if predecessor is not None and predecessor not in by_id:
                missing_predecessor = True
                break
            cursor = predecessor
        if len(visited) != len(by_id) and not missing_predecessor:
            return None, STATUS_CONFLICT, ("FP10_DISCONNECTED_SUPERSESSION_HISTORY",)
        if missing_predecessor:
            return by_id[head_id], STATUS_INCOMPLETE, ("FP10_SUPERSESSION_PREDECESSOR_MISSING",)
        return by_id[head_id], STATUS_CURRENT, ()

    def _fp04_reference_state(self, evidence_id: str) -> tuple[sqlite3.Row | None, str, tuple[str, ...]]:
        row = self._connection.execute(
            "SELECT * FROM external_provider_ownership_evidence WHERE ownership_evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        if row is None:
            return None, STATUS_INCOMPLETE, ("FP04_DEPENDENCY_MISSING",)
        try:
            reference, payload_json, payload_hash = _validate_fp04(json.loads(row["payload_json"]))
            if payload_json != row["payload_json"] or payload_hash != row["payload_hash"]:
                return row, STATUS_CONFLICT, ("STORED_FP04_CANONICAL_MISMATCH",)
        except (json.JSONDecodeError, ExternalCloseCurrentnessError):
            return row, STATUS_CONFLICT, ("STORED_FP04_INVALID",)

        key = (
            reference["provider_object_class"],
            reference["provider_identity_ref"],
            reference["provider_object_ref"],
        )
        rows = self._connection.execute(
            """
            SELECT * FROM external_provider_ownership_evidence
            WHERE provider_object_class = ? AND provider_identity_ref = ? AND provider_object_ref = ?
            """,
            key,
        ).fetchall()
        by_id = {item["ownership_evidence_id"]: item for item in rows}
        payloads: dict[str, dict[str, Any]] = {}
        try:
            for current_id, current_row in by_id.items():
                payload, canonical, digest = _validate_fp04(json.loads(current_row["payload_json"]))
                if canonical != current_row["payload_json"] or digest != current_row["payload_hash"]:
                    return row, STATUS_CONFLICT, ("STORED_FP04_CANONICAL_MISMATCH",)
                payloads[current_id] = payload
        except (json.JSONDecodeError, ExternalCloseCurrentnessError):
            return row, STATUS_CONFLICT, ("STORED_FP04_INVALID",)

        superseded: set[str] = set()
        missing_predecessor = False
        for current_id, payload in payloads.items():
            predecessor = payload.get("supersedes_ownership_evidence_id")
            if predecessor is None:
                continue
            if predecessor not in by_id:
                missing_predecessor = True
                continue
            predecessor_key = (
                payloads[predecessor]["provider_object_class"],
                payloads[predecessor]["provider_identity_ref"],
                payloads[predecessor]["provider_object_ref"],
            )
            if predecessor_key != key:
                return row, STATUS_CONFLICT, ("FP04_SUPERSESSION_LINEAGE_MISMATCH",)
            superseded.add(predecessor)

        heads = sorted(set(by_id) - superseded)
        if len(heads) != 1:
            return row, STATUS_CONFLICT, ("FP04_COMPETING_UNSUPERSEDED_HEADS",)
        if missing_predecessor:
            return row, STATUS_INCOMPLETE, ("FP04_SUPERSESSION_PREDECESSOR_MISSING",)
        derived = CURRENT if evidence_id == heads[0] else STALE
        return row, derived, ()

    @staticmethod
    def _merge_status(current: str, incoming: str) -> str:
        rank = {
            STATUS_CURRENT: 0,
            STATUS_RECONCILIATION_REQUIRED: 1,
            STATUS_INCOMPLETE: 2,
            STATUS_CONFLICT: 3,
        }
        return incoming if rank[incoming] > rank[current] else current

    def recover_position(self, position_id: str) -> ExternalCloseCurrentProjection:
        position_id = _text(position_id, "position_id")
        status = STATUS_CURRENT
        reasons: list[str] = []
        referenced_fp04: list[StoredExternalRecord] = []
        current_decision: StoredExternalRecord | None = None
        current_lifecycle_projection_id: str | None = None
        current_lifecycle_state: str | None = None
        trade_result_incomplete = False

        def add(new_status: str, reason: str) -> None:
            nonlocal status
            status = self._merge_status(status, new_status)
            if reason not in reasons:
                reasons.append(reason)

        fp10_row, fp10_status, fp10_reasons = self._resolve_fp10_head(position_id)
        for reason in fp10_reasons:
            add(fp10_status, reason)
        if fp10_row is None:
            return ExternalCloseCurrentProjection(
                status,
                tuple(reasons),
                position_id,
                None,
                None,
                (),
                None,
                None,
                False,
                False,
            )

        fp10_stored = self._stored(
            "FP10_CLOSE_CONVERGENCE_EVIDENCE",
            fp10_row["close_convergence_evidence_id"],
            fp10_row,
        )
        try:
            fp10 = fp10_stored.payload
            _validate_fp10(fp10)
        except ExternalCloseCurrentnessError:
            add(STATUS_CONFLICT, "STORED_FP10_INVALID")
            fp10 = {}

        if fp10.get("provider_position_currentness_status") != CURRENT:
            add(STATUS_RECONCILIATION_REQUIRED, "FP10_PROVIDER_POSITION_NOT_CURRENT")
        if fp10.get("convergence_state") in {
            "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED",
            "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
            "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED",
            "OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED",
            "CONVERGENCE_EVIDENCE_STALE",
            "CONVERGENCE_UNKNOWN",
            "FLAT_PROVIDER_TRUTH_PROVEN",
        }:
            add(STATUS_RECONCILIATION_REQUIRED, "FP10_CONVERGENCE_NOT_TERMINAL_CURRENT")

        for item in fp10.get("execution_evidence", []):
            if item.get("currentness_status") != CURRENT or item.get("position_compatibility_status") != "COMPATIBLE":
                add(STATUS_RECONCILIATION_REQUIRED, "FP10_EXECUTION_EVIDENCE_NOT_CURRENT_COMPATIBLE")
        if fp10.get("terminal_protection_status") != "TERMINAL_PROTECTION_CLEAR" and fp10.get("normalized_actual_quantity") == "0":
            add(STATUS_RECONCILIATION_REQUIRED, "FP10_TERMINAL_PROTECTION_NOT_CLEAR")

        for item in fp10.get("fp04_ownership_evidence", []):
            evidence_id = item.get("ownership_evidence_ref")
            if not isinstance(evidence_id, str):
                add(STATUS_CONFLICT, "FP10_FP04_REFERENCE_INVALID")
                continue
            row, derived_state, reference_reasons = self._fp04_reference_state(evidence_id)
            for reason in reference_reasons:
                if derived_state in {STATUS_CONFLICT, STATUS_INCOMPLETE}:
                    add(derived_state, reason)
            if row is None:
                continue
            stored = self._stored("FP04_OWNERSHIP_EVIDENCE", evidence_id, row)
            referenced_fp04.append(stored)
            payload = stored.payload
            if item.get("ownership_evidence_hash") != stored.payload_hash:
                add(STATUS_CONFLICT, "FP10_FP04_PAYLOAD_HASH_MISMATCH")
            if item.get("provider_object_class") != payload.get("provider_object_class"):
                add(STATUS_CONFLICT, "FP10_FP04_OBJECT_CLASS_MISMATCH")
            if item.get("provider_object_ref") != payload.get("provider_object_ref"):
                add(STATUS_CONFLICT, "FP10_FP04_OBJECT_REF_MISMATCH")
            if item.get("provider_snapshot_hash") != payload.get("provider_snapshot_hash"):
                add(STATUS_CONFLICT, "FP10_FP04_SNAPSHOT_HASH_MISMATCH")
            declared_currentness = item.get("ownership_currentness_status")
            if derived_state == STALE and declared_currentness == CURRENT:
                add(STATUS_RECONCILIATION_REQUIRED, "FP10_REFERENCES_SUPERSEDED_FP04")
            if declared_currentness != CURRENT:
                add(STATUS_RECONCILIATION_REQUIRED, "FP10_FP04_DECLARED_NOT_CURRENT")

        projection_current = self._connection.execute(
            "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
            (position_id,),
        ).fetchone()
        if projection_current is None:
            add(STATUS_INCOMPLETE, "CURRENT_LIFECYCLE_PROJECTION_MISSING")
        else:
            current_lifecycle_projection_id = projection_current["lifecycle_projection_id"]
            if (
                fp10.get("lifecycle_projection_id") != projection_current["lifecycle_projection_id"]
                or fp10.get("lifecycle_revision") != projection_current["lifecycle_revision"]
            ):
                add(STATUS_RECONCILIATION_REQUIRED, "FP10_LIFECYCLE_PROJECTION_SUPERSEDED")

        projection_row = None
        if isinstance(fp10.get("lifecycle_projection_id"), str):
            projection_row = self._connection.execute(
                "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
                (fp10["lifecycle_projection_id"],),
            ).fetchone()
        if projection_row is None:
            add(STATUS_INCOMPLETE, "FP10_LIFECYCLE_PROJECTION_DEPENDENCY_MISSING")
        else:
            if projection_row["position_id"] != position_id or projection_row["lifecycle_revision"] != fp10.get("lifecycle_revision"):
                add(STATUS_CONFLICT, "FP10_LIFECYCLE_PROJECTION_IDENTITY_MISMATCH")
            if projection_row["payload_hash"] != fp10.get("lifecycle_projection_hash"):
                add(STATUS_CONFLICT, "FP10_LIFECYCLE_PROJECTION_HASH_MISMATCH")
            try:
                projection_payload = json.loads(projection_row["payload_json"])
                if not isinstance(projection_payload, dict):
                    raise ValueError("projection payload not object")
                current_lifecycle_state = projection_payload.get("lifecycle_state")
            except (json.JSONDecodeError, ValueError):
                add(STATUS_CONFLICT, "STORED_LIFECYCLE_PROJECTION_INVALID")

        binding_row = None
        if isinstance(fp10.get("lifecycle_projection_id"), str):
            binding_row = self._connection.execute(
                """
                SELECT * FROM paper_position_lifecycle_execution_bindings
                WHERE lifecycle_projection_id = ?
                """,
                (fp10["lifecycle_projection_id"],),
            ).fetchone()
        if binding_row is None:
            add(STATUS_INCOMPLETE, "FP10_LIFECYCLE_BINDING_DEPENDENCY_MISSING")
        else:
            if binding_row["position_id"] != position_id or binding_row["lifecycle_revision"] != fp10.get("lifecycle_revision"):
                add(STATUS_CONFLICT, "FP10_LIFECYCLE_BINDING_IDENTITY_MISMATCH")
            if binding_row["payload_hash"] != fp10.get("lifecycle_execution_binding_hash"):
                add(STATUS_CONFLICT, "FP10_LIFECYCLE_BINDING_HASH_MISMATCH")
            if binding_row["execution_snapshot_hash"] != fp10.get("lifecycle_execution_snapshot_hash"):
                add(STATUS_CONFLICT, "FP10_LIFECYCLE_EXECUTION_SNAPSHOT_HASH_MISMATCH")

        decision_rows = self._connection.execute(
            """
            SELECT * FROM external_close_reinterpretation_decisions
            WHERE position_id = ? AND close_convergence_evidence_id = ?
            ORDER BY decision_id
            """,
            (position_id, fp10_row["close_convergence_evidence_id"]),
        ).fetchall()
        if not decision_rows:
            add(STATUS_INCOMPLETE, "CURRENT_E5_REINTERPRETATION_DECISION_MISSING")
        elif len(decision_rows) > 1:
            add(STATUS_CONFLICT, "COMPETING_E5_DECISIONS_FOR_CURRENT_FP10")
        else:
            decision_row = decision_rows[0]
            current_decision = self._stored(
                "E5_EXTERNAL_CLOSE_REINTERPRETATION_DECISION",
                decision_row["decision_id"],
                decision_row,
            )
            try:
                decision, canonical, digest = _validate_decision_envelope(current_decision.payload)
                if canonical != decision_row["payload_json"] or digest != decision_row["payload_hash"]:
                    raise ExternalCloseValidationError("STORED_E5_DECISION_CANONICAL_MISMATCH", "stored E5 decision mismatch")
            except ExternalCloseCurrentnessError:
                add(STATUS_CONFLICT, "STORED_E5_REINTERPRETATION_DECISION_INVALID")
                decision = {}

            if decision.get("close_convergence_evidence_hash") != fp10_row["payload_hash"]:
                add(STATUS_CONFLICT, "E5_DECISION_FP10_HASH_MISMATCH")
            for decision_field, fp10_field in (
                ("lifecycle_projection_ref", "lifecycle_projection_ref"),
                ("lifecycle_projection_id", "lifecycle_projection_id"),
                ("lifecycle_revision", "lifecycle_revision"),
                ("lifecycle_execution_binding_ref", "lifecycle_execution_binding_ref"),
            ):
                if decision.get(decision_field) != fp10.get(fp10_field):
                    add(STATUS_CONFLICT, "E5_DECISION_LIFECYCLE_REFERENCE_MISMATCH")
                    break
            if binding_row is not None and decision.get("lifecycle_execution_binding_id") != binding_row["lifecycle_execution_binding_id"]:
                add(STATUS_CONFLICT, "E5_DECISION_LIFECYCLE_BINDING_ID_MISMATCH")
            if decision.get("evidence_current") is not True:
                add(STATUS_RECONCILIATION_REQUIRED, "E5_DECISION_DECLARED_EVIDENCE_NOT_CURRENT")
            if decision.get("close_eligible") is True and fp10.get("convergence_state") != "LIFECYCLE_CLOSE_ELIGIBLE":
                add(STATUS_CONFLICT, "E5_DECISION_FALSE_CLOSE_ELIGIBILITY_BINDING")
            trade_result_incomplete = bool(decision.get("trade_result_evidence_incomplete"))

        closed_allowed = False
        if current_decision is not None:
            decision_payload = current_decision.payload
            closed_allowed = (
                status == STATUS_CURRENT
                and current_lifecycle_state == "CLOSED"
                and decision_payload.get("next_state") == "CLOSED"
                and decision_payload.get("close_eligible") is True
                and decision_payload.get("evidence_current") is True
            )
        if current_lifecycle_state == "CLOSED" and not closed_allowed:
            add(STATUS_RECONCILIATION_REQUIRED, "FALSE_GREEN_CLOSED_PRESENTATION_BLOCKED")
            closed_allowed = False

        return ExternalCloseCurrentProjection(
            status=status,
            reason_codes=tuple(reasons),
            position_id=position_id,
            current_fp10=fp10_stored,
            current_decision=current_decision,
            referenced_fp04=tuple(referenced_fp04),
            current_lifecycle_projection_id=current_lifecycle_projection_id,
            current_lifecycle_state=current_lifecycle_state,
            trade_result_evidence_incomplete=trade_result_incomplete,
            closed_presentation_allowed=closed_allowed,
        )


def open_external_close_currentness_store(path: str | Path) -> ExternalCloseCurrentnessStore:
    """Open the E6 provider-neutral FP-04/FP-10 durable currentness store."""

    connection = _connect(path)
    try:
        _apply_migrations(connection)
        return ExternalCloseCurrentnessStore(connection)
    except Exception:
        connection.close()
        raise


__all__ = [
    "ExternalCloseConflictError",
    "ExternalCloseCurrentProjection",
    "ExternalCloseCurrentnessError",
    "ExternalCloseCurrentnessStore",
    "ExternalCloseValidationError",
    "StoredExternalRecord",
    "open_external_close_currentness_store",
]
