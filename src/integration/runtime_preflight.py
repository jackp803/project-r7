from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "contracts-v0.1"
RUNTIME_PREFLIGHT_PROFILE_VERSION = "runtime-preflight-v0.1"

ELIGIBLE = "ELIGIBLE"
FAIL_CLOSED = "FAIL_CLOSED"

RUNTIME_ROLES = frozenset(
    {
        "CREDENTIAL_FREE_LOCAL_VERIFICATION",
        "PROVIDER_READ_ONLY_OBSERVATION",
        "SHADOW_RUNTIME",
        "PAPER_RUNTIME",
        "BOUNDED_LIVE_FIRE_RUNTIME",
    }
)
LAUNCH_INTENTS = frozenset({"START", "RESTART", "VERIFY_EXISTING"})
OPERATIONAL_MODES = frozenset({"RESEARCH", "PAPER", "SHADOW", "LIVE", "PAUSED", "LOCKED"})
WORKTREE_CLASSIFICATIONS = frozenset({"EXACT_CLEAN", "CLEAN_UNQUALIFIED", "DIRTY", "UNKNOWN"})
SINGLE_INSTANCE_STATUSES = frozenset({"SINGLE", "CONFLICT", "UNKNOWN"})
HEARTBEAT_FRESHNESS_STATUSES = frozenset({"FRESH", "STALE", "UNKNOWN"})
SUPERVISOR_COMPATIBILITY_STATUSES = frozenset({"ACCEPTED", "NOT_ACCEPTED", "UNKNOWN", "NOT_APPLICABLE"})
RESTART_PERMISSION_STATUSES = frozenset(
    {"ALLOWED_BY_CURRENT_EVIDENCE", "NOT_ALLOWED", "UNKNOWN", "NOT_APPLICABLE"}
)
CAPABILITY_STATUSES = frozenset({"READY", "NOT_READY", "UNKNOWN"})
RECONCILIATION_STATUSES = frozenset({"READY", "NOT_READY", "UNKNOWN"})
DEPENDENCY_READINESS_STATUSES = frozenset({"READY", "NOT_READY", "UNKNOWN"})
EXTERNAL_COMPATIBILITY_STATUSES = frozenset({"ACCEPTED", "NOT_ACCEPTED", "UNKNOWN"})
AUTHORIZATION_STATUSES = frozenset({"VALID", "MISSING", "MISMATCH", "EXPIRED", "CONSUMED", "UNKNOWN"})
DEPENDENCY_OWNERS = frozenset({"E1", "E4", "E5", "E6", "E7", "OPERATOR"})

ROLE_AUTHORIZATION_CLASS = {
    "CREDENTIAL_FREE_LOCAL_VERIFICATION": "CREDENTIAL_FREE_TASK",
    "PROVIDER_READ_ONLY_OBSERVATION": "PROVIDER_READ_ONLY",
    "SHADOW_RUNTIME": "SHADOW_RUNTIME",
    "PAPER_RUNTIME": "PAPER_RUNTIME",
    "BOUNDED_LIVE_FIRE_RUNTIME": "BOUNDED_LIVE_FIRE_RUNTIME",
}

RECONCILIATION_REQUIRED_ROLES = frozenset(
    {
        "PROVIDER_READ_ONLY_OBSERVATION",
        "SHADOW_RUNTIME",
        "PAPER_RUNTIME",
        "BOUNDED_LIVE_FIRE_RUNTIME",
    }
)
EXTERNAL_CONSUMER_ALWAYS_REQUIRED_ROLES = frozenset({"SHADOW_RUNTIME", "BOUNDED_LIVE_FIRE_RUNTIME"})

PREFLIGHT_REASON_ORDER = (
    "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
    "PREFLIGHT_REVISION_MISMATCH",
    "PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN",
    "PREFLIGHT_OPERATIONAL_MODE_UNKNOWN",
    "PREFLIGHT_OPERATIONAL_MODE_MISMATCH",
    "PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT",
    "PREFLIGHT_CONFIG_GENERATION_MISMATCH",
    "PREFLIGHT_PROCESS_IDENTITY_INVALID",
    "PREFLIGHT_SINGLE_INSTANCE_CONFLICT",
    "PREFLIGHT_PROCESS_START_GENERATION_MISMATCH",
    "PREFLIGHT_HEARTBEAT_POLICY_UNKNOWN",
    "PREFLIGHT_HEARTBEAT_MISSING",
    "PREFLIGHT_HEARTBEAT_WRONG_PROCESS",
    "PREFLIGHT_HEARTBEAT_PRIOR_BOOT",
    "PREFLIGHT_HEARTBEAT_STALE",
    "PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED",
    "PREFLIGHT_RESTART_NOT_AUTHORIZED",
    "PREFLIGHT_ACTION_CAPABILITY_MISSING",
    "PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED",
    "PREFLIGHT_RECONCILIATION_NOT_READY",
    "PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY",
    "PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED",
    "PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN",
    "PREFLIGHT_RUNTIME_AUTHORITY_CONSUMED",
    "PREFLIGHT_ROLE_AUTHORITY_EXCEEDED",
    "PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED",
    "PREFLIGHT_EVIDENCE_TIME_INVALID",
    "RUNTIME_PREFLIGHT_ELIGIBLE",
)
_REASON_INDEX = {value: index for index, value in enumerate(PREFLIGHT_REASON_ORDER)}
_FAILURE_REASONS = frozenset(PREFLIGHT_REASON_ORDER[:-1])

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_ID_RE = re.compile(r"^runtimepreflight_[0-9a-f]{64}$")

_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "runtime_preflight_profile_version",
        "runtime_preflight_id",
        "runtime_role",
        "launch_intent",
        "evaluated_at",
        "project_revision",
        "revision_authority_ref",
        "revision_authority_hash",
        "worktree_classification",
        "requested_operational_mode",
        "operational_mode_transition_id",
        "operational_mode_revision",
        "operational_mode_payload_hash",
        "runtime_config_generation_id",
        "runtime_config_hash",
        "process_instance_id",
        "process_start_generation_id",
        "process_started_at",
        "single_instance_status",
        "heartbeat_evidence",
        "supervisor_evidence",
        "capability_evidence",
        "reconciliation_evidence",
        "dependency_evidence",
        "external_consumer_evidence",
        "authorization_evidence",
        "preflight_status",
        "reason_codes",
    }
)
_INPUT_FIELDS = _TOP_LEVEL_FIELDS - {"runtime_preflight_id", "preflight_status", "reason_codes"}
_HEARTBEAT_FIELDS = frozenset(
    {
        "heartbeat_source_id",
        "heartbeat_policy_generation_id",
        "heartbeat_policy_hash",
        "heartbeat_process_instance_id",
        "heartbeat_process_start_generation_id",
        "heartbeat_observed_at",
        "heartbeat_received_at",
        "heartbeat_freshness_status",
    }
)
_SUPERVISOR_FIELDS = frozenset(
    {
        "supervisor_present",
        "supervisor_id",
        "supervisor_generation_id",
        "supervisor_config_hash",
        "supervisor_compatibility_status",
        "restart_permission_status",
    }
)
_CAPABILITY_FIELDS = frozenset(
    {
        "capability_snapshot_ref",
        "capability_snapshot_hash",
        "capability_generation_id",
        "required_action_ids",
        "registered_action_ids",
        "allowlisted_action_ids",
        "capability_status",
    }
)
_RECONCILIATION_FIELDS = frozenset(
    {
        "reconciliation_ref",
        "reconciliation_hash",
        "reconciliation_generation_id",
        "reconciliation_observed_at",
        "reconciliation_status",
        "fresh_reconciliation_required",
    }
)
_DEPENDENCY_FIELDS = frozenset(
    {
        "owner",
        "evidence_class",
        "evidence_ref",
        "evidence_hash",
        "evidence_generation_id",
        "observed_at",
        "readiness_status",
    }
)
_EXTERNAL_CONSUMER_FIELDS = frozenset(
    {
        "external_consumer_id",
        "external_consumer_generation_id",
        "external_consumer_config_hash",
        "compatibility_profile_ref",
        "compatibility_evidence_hash",
        "compatibility_status",
        "compatibility_observed_at",
    }
)
_AUTHORIZATION_FIELDS = frozenset(
    {
        "authorization_class",
        "authorization_ref",
        "authorization_generation_id",
        "authorized_project_revision",
        "authorized_runtime_role",
        "authorized_capability_set_hash",
        "authorization_status",
    }
)


class RuntimePreflightValidationError(ValueError):
    """Structural/canonical failure at the E7 runtime-preflight boundary."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RuntimePreflightInput:
    schema_version: str
    runtime_preflight_profile_version: str
    runtime_role: str
    launch_intent: str
    evaluated_at: str
    project_revision: str
    revision_authority_ref: str
    revision_authority_hash: str
    worktree_classification: str
    requested_operational_mode: str
    operational_mode_transition_id: str
    operational_mode_revision: int
    operational_mode_payload_hash: str
    runtime_config_generation_id: str
    runtime_config_hash: str
    process_instance_id: str
    process_start_generation_id: str
    process_started_at: str
    single_instance_status: str
    heartbeat_evidence: Mapping[str, Any]
    supervisor_evidence: Mapping[str, Any]
    capability_evidence: Mapping[str, Any]
    reconciliation_evidence: Mapping[str, Any]
    dependency_evidence: Sequence[Mapping[str, Any]]
    external_consumer_evidence: Mapping[str, Any] | None
    authorization_evidence: Mapping[str, Any]


@dataclass(frozen=True)
class RuntimePreflightAuthority:
    """Caller-supplied current authority facts; never runtime/provider authority creation."""

    revision_authority: Mapping[str, Any]
    operational_mode_authority: Mapping[str, Any]
    runtime_config_authority: Mapping[str, Any]
    heartbeat_policy_authority: Mapping[str, Any]
    supervisor_authority: Mapping[str, Any] | None
    capability_authority: Mapping[str, Any]
    reconciliation_authority: Mapping[str, Any]
    required_dependencies: Sequence[Mapping[str, Any]]
    external_consumer_authority: Mapping[str, Any] | None
    authorization_authority: Mapping[str, Any]


def _canonicalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RuntimePreflightValidationError(
                    "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                    "canonical mapping keys must be strings",
                )
            normalized[key] = _canonicalize(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "binary floats are not canonical runtime-preflight evidence",
        )
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise RuntimePreflightValidationError(
        "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
        f"unsupported canonical value type: {type(value).__name__}",
    )


def canonical_runtime_preflight_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def stable_runtime_preflight_id(evidence: Mapping[str, Any]) -> str:
    if not isinstance(evidence, Mapping):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "runtime-preflight evidence must be a mapping",
        )
    material = dict(evidence)
    material.pop("runtime_preflight_id", None)
    digest = hashlib.sha256(canonical_runtime_preflight_json(material).encode("utf-8")).hexdigest()
    return "runtimepreflight_" + digest


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _hash(value: Any) -> bool:
    return isinstance(value, str) and _HASH_RE.fullmatch(value) is not None


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed.astimezone(timezone.utc)


def _ordered_reasons(reasons: set[str]) -> list[str]:
    return [reason for reason in PREFLIGHT_REASON_ORDER[:-1] if reason in reasons]


def _exact_mapping(value: Any, field_set: frozenset[str]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping) or set(value) != field_set:
        return None
    return value


def _sorted_unique_texts(value: Any) -> list[str] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result = list(value)
    if any(not _text(item) for item in result):
        return None
    if result != sorted(result) or len(result) != len(set(result)):
        return None
    return result


def _dependency_key(item: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(item.get("owner")), str(item.get("evidence_class")), str(item.get("evidence_ref")))


def _validate_input_shape(value: RuntimePreflightInput) -> dict[str, Any]:
    if not isinstance(value, RuntimePreflightInput):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "evaluate_runtime_preflight requires RuntimePreflightInput",
        )
    payload = _canonicalize(value)
    if not isinstance(payload, dict) or set(payload) != _INPUT_FIELDS:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "runtime-preflight input fields do not match the accepted profile",
        )
    return payload


def _authority_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dependency_authority_matches(
    observed: Sequence[Mapping[str, Any]],
    required: Sequence[Mapping[str, Any]],
) -> bool:
    observed_by_key = {_dependency_key(item): item for item in observed if isinstance(item, Mapping)}
    for expected in required:
        if not isinstance(expected, Mapping):
            return False
        key = _dependency_key(expected)
        actual = observed_by_key.get(key)
        if actual is None:
            return False
        for field in ("evidence_hash", "evidence_generation_id"):
            if actual.get(field) != expected.get(field):
                return False
    return True


def evaluate_runtime_preflight(
    value: RuntimePreflightInput,
    authority: RuntimePreflightAuthority,
) -> dict[str, Any]:
    """Purely interpret supplied sanitized FP-16 evidence and current authority facts.

    The function performs no I/O and grants no provider, order, process-launch,
    restart, SHADOW/PAPER, bounded-live-fire, Gate D, LIVE, or capital authority.
    """

    payload = _validate_input_shape(value)
    if not isinstance(authority, RuntimePreflightAuthority):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "current runtime-preflight authority must use RuntimePreflightAuthority",
        )

    reasons: set[str] = set()
    role = payload["runtime_role"]
    launch_intent = payload["launch_intent"]
    evaluated_at = _utc(payload["evaluated_at"])
    process_started_at = _utc(payload["process_started_at"])

    if payload["schema_version"] != SCHEMA_VERSION or payload["runtime_preflight_profile_version"] != RUNTIME_PREFLIGHT_PROFILE_VERSION:
        reasons.add("PREFLIGHT_EVIDENCE_IDENTITY_INVALID")
    if role not in RUNTIME_ROLES or launch_intent not in LAUNCH_INTENTS:
        reasons.add("PREFLIGHT_ROLE_AUTHORITY_EXCEEDED")
    if evaluated_at is None or process_started_at is None or (
        evaluated_at is not None and process_started_at is not None and process_started_at > evaluated_at
    ):
        reasons.add("PREFLIGHT_EVIDENCE_TIME_INVALID")

    revision_authority = _authority_mapping(authority.revision_authority)
    if (
        not isinstance(payload["project_revision"], str)
        or _REVISION_RE.fullmatch(payload["project_revision"]) is None
        or payload["project_revision"] != revision_authority.get("project_revision")
        or payload["revision_authority_ref"] != revision_authority.get("revision_authority_ref")
        or payload["revision_authority_hash"] != revision_authority.get("revision_authority_hash")
        or not _hash(payload["revision_authority_hash"])
    ):
        reasons.add("PREFLIGHT_REVISION_MISMATCH")
    if (
        payload["worktree_classification"] != "EXACT_CLEAN"
        or revision_authority.get("worktree_classification") != "EXACT_CLEAN"
    ):
        reasons.add("PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN")

    mode_authority = _authority_mapping(authority.operational_mode_authority)
    if payload["requested_operational_mode"] not in OPERATIONAL_MODES or mode_authority.get("mode") not in OPERATIONAL_MODES:
        reasons.add("PREFLIGHT_OPERATIONAL_MODE_UNKNOWN")
    elif payload["requested_operational_mode"] != mode_authority.get("mode"):
        reasons.add("PREFLIGHT_OPERATIONAL_MODE_MISMATCH")
    if (
        payload["operational_mode_transition_id"] != mode_authority.get("transition_id")
        or payload["operational_mode_revision"] != mode_authority.get("mode_revision")
        or payload["operational_mode_payload_hash"] != mode_authority.get("payload_hash")
        or type(payload["operational_mode_revision"]) is not int
        or payload["operational_mode_revision"] < 0
        or not _hash(payload["operational_mode_payload_hash"])
    ):
        reasons.add("PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT")
    if role == "SHADOW_RUNTIME" and payload["requested_operational_mode"] != "SHADOW":
        reasons.add("PREFLIGHT_OPERATIONAL_MODE_MISMATCH")
    if role == "PAPER_RUNTIME" and payload["requested_operational_mode"] != "PAPER":
        reasons.add("PREFLIGHT_OPERATIONAL_MODE_MISMATCH")
    if role == "BOUNDED_LIVE_FIRE_RUNTIME":
        reasons.add("PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED")

    config_authority = _authority_mapping(authority.runtime_config_authority)
    if (
        payload["runtime_config_generation_id"] != config_authority.get("runtime_config_generation_id")
        or payload["runtime_config_hash"] != config_authority.get("runtime_config_hash")
        or not _text(payload["runtime_config_generation_id"])
        or not _hash(payload["runtime_config_hash"])
    ):
        reasons.add("PREFLIGHT_CONFIG_GENERATION_MISMATCH")

    if not _text(payload["process_instance_id"]) or not _text(payload["process_start_generation_id"]):
        reasons.add("PREFLIGHT_PROCESS_IDENTITY_INVALID")
    if payload["single_instance_status"] not in SINGLE_INSTANCE_STATUSES or payload["single_instance_status"] != "SINGLE":
        reasons.add("PREFLIGHT_SINGLE_INSTANCE_CONFLICT")

    heartbeat = _exact_mapping(payload["heartbeat_evidence"], _HEARTBEAT_FIELDS)
    heartbeat_policy_authority = _authority_mapping(authority.heartbeat_policy_authority)
    if heartbeat is None:
        reasons.add("PREFLIGHT_HEARTBEAT_MISSING")
    else:
        if (
            not _text(heartbeat.get("heartbeat_source_id"))
            or not _text(heartbeat.get("heartbeat_policy_generation_id"))
            or not _hash(heartbeat.get("heartbeat_policy_hash"))
            or heartbeat.get("heartbeat_policy_generation_id")
            != heartbeat_policy_authority.get("heartbeat_policy_generation_id")
            or heartbeat.get("heartbeat_policy_hash") != heartbeat_policy_authority.get("heartbeat_policy_hash")
        ):
            reasons.add("PREFLIGHT_HEARTBEAT_POLICY_UNKNOWN")
        if heartbeat.get("heartbeat_process_instance_id") != payload["process_instance_id"]:
            reasons.add("PREFLIGHT_HEARTBEAT_WRONG_PROCESS")
        if heartbeat.get("heartbeat_process_start_generation_id") != payload["process_start_generation_id"]:
            reasons.add("PREFLIGHT_HEARTBEAT_PRIOR_BOOT")
        if heartbeat.get("heartbeat_freshness_status") not in HEARTBEAT_FRESHNESS_STATUSES or heartbeat.get(
            "heartbeat_freshness_status"
        ) != "FRESH":
            reasons.add("PREFLIGHT_HEARTBEAT_STALE")
        heartbeat_observed = _utc(heartbeat.get("heartbeat_observed_at"))
        heartbeat_received = _utc(heartbeat.get("heartbeat_received_at"))
        if (
            heartbeat_observed is None
            or heartbeat_received is None
            or process_started_at is None
            or evaluated_at is None
            or heartbeat_observed < process_started_at
            or heartbeat_received < heartbeat_observed
            or heartbeat_received > evaluated_at
        ):
            reasons.add("PREFLIGHT_EVIDENCE_TIME_INVALID")

    supervisor = _exact_mapping(payload["supervisor_evidence"], _SUPERVISOR_FIELDS)
    supervisor_present = bool(supervisor and supervisor.get("supervisor_present") is True)
    supervisor_authority = _authority_mapping(authority.supervisor_authority)
    if supervisor is None:
        reasons.add("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED")
    elif supervisor_present:
        if (
            not _text(supervisor.get("supervisor_id"))
            or not _text(supervisor.get("supervisor_generation_id"))
            or not _hash(supervisor.get("supervisor_config_hash"))
            or supervisor.get("supervisor_generation_id") != supervisor_authority.get("supervisor_generation_id")
            or supervisor.get("supervisor_config_hash") != supervisor_authority.get("supervisor_config_hash")
            or supervisor.get("supervisor_compatibility_status") != "ACCEPTED"
        ):
            reasons.add("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED")
    else:
        if any(supervisor.get(field) is not None for field in ("supervisor_id", "supervisor_generation_id", "supervisor_config_hash")):
            reasons.add("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED")
        if supervisor.get("supervisor_compatibility_status") != "NOT_APPLICABLE":
            reasons.add("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED")
    if launch_intent == "RESTART" and (
        supervisor is None
        or not supervisor_present
        or supervisor.get("restart_permission_status") != "ALLOWED_BY_CURRENT_EVIDENCE"
    ):
        reasons.add("PREFLIGHT_RESTART_NOT_AUTHORIZED")
    if supervisor is not None:
        if supervisor.get("supervisor_compatibility_status") not in SUPERVISOR_COMPATIBILITY_STATUSES:
            reasons.add("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED")
        if supervisor.get("restart_permission_status") not in RESTART_PERMISSION_STATUSES:
            reasons.add("PREFLIGHT_RESTART_NOT_AUTHORIZED")

    capability = _exact_mapping(payload["capability_evidence"], _CAPABILITY_FIELDS)
    capability_authority = _authority_mapping(authority.capability_authority)
    if capability is None:
        reasons.add("PREFLIGHT_ACTION_CAPABILITY_MISSING")
    else:
        required = _sorted_unique_texts(capability.get("required_action_ids"))
        registered = _sorted_unique_texts(capability.get("registered_action_ids"))
        allowlisted = _sorted_unique_texts(capability.get("allowlisted_action_ids"))
        if (
            capability.get("capability_status") not in CAPABILITY_STATUSES
            or capability.get("capability_status") != "READY"
            or required is None
            or registered is None
            or allowlisted is None
            or capability.get("capability_snapshot_ref") != capability_authority.get("capability_snapshot_ref")
            or capability.get("capability_snapshot_hash") != capability_authority.get("capability_snapshot_hash")
            or capability.get("capability_generation_id") != capability_authority.get("capability_generation_id")
            or not _hash(capability.get("capability_snapshot_hash"))
        ):
            reasons.add("PREFLIGHT_ACTION_CAPABILITY_MISSING")
        if required is not None and registered is not None and any(action not in registered for action in required):
            reasons.add("PREFLIGHT_ACTION_CAPABILITY_MISSING")
        if required is not None and allowlisted is not None and any(action not in allowlisted for action in required):
            reasons.add("PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED")

    reconciliation = _exact_mapping(payload["reconciliation_evidence"], _RECONCILIATION_FIELDS)
    if reconciliation is not None:
        reconciliation_observed = _utc(reconciliation.get("reconciliation_observed_at"))
        if evaluated_at is None or reconciliation_observed is None or reconciliation_observed > evaluated_at:
            reasons.add("PREFLIGHT_EVIDENCE_TIME_INVALID")
    if role in RECONCILIATION_REQUIRED_ROLES:
        reconciliation_authority = _authority_mapping(authority.reconciliation_authority)
        if (
            reconciliation is None
            or reconciliation.get("reconciliation_status") not in RECONCILIATION_STATUSES
            or reconciliation.get("reconciliation_status") != "READY"
            or reconciliation.get("fresh_reconciliation_required") is not False
            or reconciliation.get("reconciliation_ref") != reconciliation_authority.get("reconciliation_ref")
            or reconciliation.get("reconciliation_hash") != reconciliation_authority.get("reconciliation_hash")
            or reconciliation.get("reconciliation_generation_id")
            != reconciliation_authority.get("reconciliation_generation_id")
            or not _hash(reconciliation.get("reconciliation_hash"))
        ):
            reasons.add("PREFLIGHT_RECONCILIATION_NOT_READY")

    dependency_items: list[Mapping[str, Any]] = []
    dependency_raw = payload["dependency_evidence"]
    dependency_valid = isinstance(dependency_raw, list)
    if dependency_valid:
        for item in dependency_raw:
            dependency = _exact_mapping(item, _DEPENDENCY_FIELDS)
            if dependency is None:
                dependency_valid = False
                break
            dependency_items.append(dependency)
        keys = [_dependency_key(item) for item in dependency_items]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            dependency_valid = False
    if not dependency_valid:
        reasons.add("PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY")
    else:
        for dependency in dependency_items:
            if (
                dependency.get("owner") not in DEPENDENCY_OWNERS
                or dependency.get("readiness_status") not in DEPENDENCY_READINESS_STATUSES
                or dependency.get("readiness_status") != "READY"
                or not _hash(dependency.get("evidence_hash"))
            ):
                reasons.add("PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY")
            observed_at = _utc(dependency.get("observed_at"))
            if evaluated_at is None or observed_at is None or observed_at > evaluated_at:
                reasons.add("PREFLIGHT_EVIDENCE_TIME_INVALID")
        if not _dependency_authority_matches(dependency_items, authority.required_dependencies):
            reasons.add("PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY")

    external_participation_authority_supplied = authority.external_consumer_authority is not None
    external_required = (
        role in EXTERNAL_CONSUMER_ALWAYS_REQUIRED_ROLES
        or supervisor_present
        or external_participation_authority_supplied
    )
    external = payload["external_consumer_evidence"]
    external_authority = _authority_mapping(authority.external_consumer_authority)
    if external is None:
        if external_required:
            reasons.add("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED")
    else:
        external_mapping = _exact_mapping(external, _EXTERNAL_CONSUMER_FIELDS)
        if (
            external_mapping is None
            or external_mapping.get("compatibility_status") not in EXTERNAL_COMPATIBILITY_STATUSES
            or external_mapping.get("compatibility_status") != "ACCEPTED"
            or external_mapping.get("external_consumer_id") != external_authority.get("external_consumer_id")
            or external_mapping.get("external_consumer_generation_id")
            != external_authority.get("external_consumer_generation_id")
            or external_mapping.get("external_consumer_config_hash")
            != external_authority.get("external_consumer_config_hash")
            or external_mapping.get("compatibility_profile_ref") != external_authority.get("compatibility_profile_ref")
            or external_mapping.get("compatibility_evidence_hash")
            != external_authority.get("compatibility_evidence_hash")
        ):
            reasons.add("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED")
        else:
            if not _hash(external_mapping.get("external_consumer_config_hash")) or not _hash(
                external_mapping.get("compatibility_evidence_hash")
            ):
                reasons.add("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED")
            compatibility_observed = _utc(external_mapping.get("compatibility_observed_at"))
            if evaluated_at is None or compatibility_observed is None or compatibility_observed > evaluated_at:
                reasons.add("PREFLIGHT_EVIDENCE_TIME_INVALID")

    authorization = _exact_mapping(payload["authorization_evidence"], _AUTHORIZATION_FIELDS)
    authorization_authority = _authority_mapping(authority.authorization_authority)
    if authorization is None:
        reasons.add("PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN")
    else:
        status = authorization.get("authorization_status")
        if status == "CONSUMED":
            reasons.add("PREFLIGHT_RUNTIME_AUTHORITY_CONSUMED")
        elif status not in AUTHORIZATION_STATUSES or status != "VALID":
            reasons.add("PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN")
        expected_class = ROLE_AUTHORIZATION_CLASS.get(role)
        capability_hash = capability.get("capability_snapshot_hash") if capability is not None else None
        if (
            expected_class is None
            or authorization.get("authorization_class") != expected_class
            or authorization.get("authorized_runtime_role") != role
            or authorization.get("authorized_project_revision") != payload["project_revision"]
            or authorization.get("authorized_capability_set_hash") != capability_hash
            or not _hash(authorization.get("authorized_capability_set_hash"))
            or any(authorization.get(field) != authorization_authority.get(field) for field in _AUTHORIZATION_FIELDS)
        ):
            reasons.add("PREFLIGHT_ROLE_AUTHORITY_EXCEEDED")

    ordered = _ordered_reasons(reasons)
    if ordered:
        status = FAIL_CLOSED
        reason_codes = ordered
    else:
        status = ELIGIBLE
        reason_codes = ["RUNTIME_PREFLIGHT_ELIGIBLE"]

    evidence = dict(payload)
    evidence["preflight_status"] = status
    evidence["reason_codes"] = reason_codes
    evidence["runtime_preflight_id"] = stable_runtime_preflight_id(evidence)
    validate_runtime_preflight_evidence(evidence)
    return evidence


def validate_runtime_preflight_evidence(evidence: Mapping[str, Any]) -> None:
    if not isinstance(evidence, Mapping) or set(evidence) != _TOP_LEVEL_FIELDS:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "RuntimePreflightEvidence fields do not match runtime-preflight-v0.1",
        )
    if evidence.get("schema_version") != SCHEMA_VERSION or evidence.get(
        "runtime_preflight_profile_version"
    ) != RUNTIME_PREFLIGHT_PROFILE_VERSION:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "unsupported runtime-preflight schema/profile",
        )
    evidence_id = evidence.get("runtime_preflight_id")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "runtime_preflight_id is invalid",
        )
    if evidence_id != stable_runtime_preflight_id(evidence):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "runtime_preflight_id does not match the immutable payload",
        )
    if evidence.get("runtime_role") not in RUNTIME_ROLES or evidence.get("launch_intent") not in LAUNCH_INTENTS:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "runtime role or launch intent is outside the accepted profile",
        )
    if not isinstance(evidence.get("project_revision"), str) or _REVISION_RE.fullmatch(evidence["project_revision"]) is None:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "project_revision must be a full lowercase Git SHA",
        )
    for field in (
        "revision_authority_hash",
        "operational_mode_payload_hash",
        "runtime_config_hash",
    ):
        if not _hash(evidence.get(field)):
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                f"{field} must be sha256:<lowercase hex>",
            )
    for field in ("evaluated_at", "process_started_at"):
        if _utc(evidence.get(field)) is None:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_TIME_INVALID",
                f"{field} must be canonical RFC3339 UTC Z",
            )
    if evidence.get("worktree_classification") not in WORKTREE_CLASSIFICATIONS:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "worktree_classification is unsupported",
        )
    if type(evidence.get("operational_mode_revision")) is not int or evidence["operational_mode_revision"] < 0:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "operational_mode_revision must be a non-negative integer",
        )
    if evidence.get("single_instance_status") not in SINGLE_INSTANCE_STATUSES:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "single_instance_status is unsupported",
        )

    heartbeat = _exact_mapping(evidence.get("heartbeat_evidence"), _HEARTBEAT_FIELDS)
    supervisor = _exact_mapping(evidence.get("supervisor_evidence"), _SUPERVISOR_FIELDS)
    capability = _exact_mapping(evidence.get("capability_evidence"), _CAPABILITY_FIELDS)
    reconciliation = _exact_mapping(evidence.get("reconciliation_evidence"), _RECONCILIATION_FIELDS)
    authorization = _exact_mapping(evidence.get("authorization_evidence"), _AUTHORIZATION_FIELDS)
    if heartbeat is None or supervisor is None or capability is None or reconciliation is None or authorization is None:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "nested runtime-preflight evidence fields mismatch",
        )
    if heartbeat.get("heartbeat_freshness_status") not in HEARTBEAT_FRESHNESS_STATUSES or not _hash(
        heartbeat.get("heartbeat_policy_hash")
    ):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "heartbeat evidence is noncanonical",
        )
    if supervisor.get("supervisor_compatibility_status") not in SUPERVISOR_COMPATIBILITY_STATUSES or supervisor.get(
        "restart_permission_status"
    ) not in RESTART_PERMISSION_STATUSES:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "supervisor evidence is noncanonical",
        )
    for field in ("required_action_ids", "registered_action_ids", "allowlisted_action_ids"):
        if _sorted_unique_texts(capability.get(field)) is None:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                f"capability {field} must be sorted and unique",
            )
    if capability.get("capability_status") not in CAPABILITY_STATUSES or not _hash(
        capability.get("capability_snapshot_hash")
    ):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "capability evidence is noncanonical",
        )
    if reconciliation.get("reconciliation_status") not in RECONCILIATION_STATUSES or type(
        reconciliation.get("fresh_reconciliation_required")
    ) is not bool or not _hash(reconciliation.get("reconciliation_hash")):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "reconciliation evidence is noncanonical",
        )
    if _utc(reconciliation.get("reconciliation_observed_at")) is None:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_TIME_INVALID",
            "reconciliation_observed_at must be canonical UTC",
        )

    dependencies = evidence.get("dependency_evidence")
    if not isinstance(dependencies, list):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "dependency_evidence must be a deterministic array",
        )
    dependency_keys: list[tuple[str, str, str]] = []
    for item in dependencies:
        dependency = _exact_mapping(item, _DEPENDENCY_FIELDS)
        if dependency is None or dependency.get("owner") not in DEPENDENCY_OWNERS or dependency.get(
            "readiness_status"
        ) not in DEPENDENCY_READINESS_STATUSES or not _hash(dependency.get("evidence_hash")):
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "dependency evidence is noncanonical",
            )
        if _utc(dependency.get("observed_at")) is None:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_TIME_INVALID",
                "dependency observed_at must be canonical UTC",
            )
        dependency_keys.append(_dependency_key(dependency))
    if dependency_keys != sorted(dependency_keys) or len(dependency_keys) != len(set(dependency_keys)):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "dependency evidence must be sorted and unique",
        )

    external = evidence.get("external_consumer_evidence")
    if external is not None:
        external_mapping = _exact_mapping(external, _EXTERNAL_CONSUMER_FIELDS)
        if external_mapping is None or external_mapping.get("compatibility_status") not in EXTERNAL_COMPATIBILITY_STATUSES:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "external consumer evidence is noncanonical",
            )
        if not _hash(external_mapping.get("external_consumer_config_hash")) or not _hash(
            external_mapping.get("compatibility_evidence_hash")
        ):
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "external consumer hashes are invalid",
            )
        if _utc(external_mapping.get("compatibility_observed_at")) is None:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_TIME_INVALID",
                "external consumer observation must be canonical UTC",
            )

    if authorization.get("authorization_status") not in AUTHORIZATION_STATUSES or not _hash(
        authorization.get("authorized_capability_set_hash")
    ):
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "authorization evidence is noncanonical",
        )

    status = evidence.get("preflight_status")
    reasons = evidence.get("reason_codes")
    if not isinstance(reasons, list) or not reasons:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "reason_codes must be a non-empty deterministic array",
        )
    if status == ELIGIBLE:
        if reasons != ["RUNTIME_PREFLIGHT_ELIGIBLE"]:
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "ELIGIBLE evidence must carry only RUNTIME_PREFLIGHT_ELIGIBLE",
            )
    elif status == FAIL_CLOSED:
        if any(reason not in _FAILURE_REASONS for reason in reasons):
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "FAIL_CLOSED reason is outside the accepted vocabulary",
            )
        if reasons != sorted(set(reasons), key=_REASON_INDEX.__getitem__):
            raise RuntimePreflightValidationError(
                "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
                "FAIL_CLOSED reasons must be unique and in contract order",
            )
    else:
        raise RuntimePreflightValidationError(
            "PREFLIGHT_EVIDENCE_IDENTITY_INVALID",
            "preflight_status must be ELIGIBLE or FAIL_CLOSED",
        )


def runtime_preflight_evidence_is_current(
    evidence: Mapping[str, Any],
    current_input: RuntimePreflightInput,
    current_authority: RuntimePreflightAuthority,
) -> bool:
    """Return whether evidence exactly matches a fresh pure interpretation of current facts."""

    try:
        validate_runtime_preflight_evidence(evidence)
        current = evaluate_runtime_preflight(current_input, current_authority)
    except RuntimePreflightValidationError:
        return False
    return dict(evidence) == current


__all__ = [
    "ELIGIBLE",
    "FAIL_CLOSED",
    "PREFLIGHT_REASON_ORDER",
    "RUNTIME_PREFLIGHT_PROFILE_VERSION",
    "RuntimePreflightAuthority",
    "RuntimePreflightInput",
    "RuntimePreflightValidationError",
    "canonical_runtime_preflight_json",
    "evaluate_runtime_preflight",
    "runtime_preflight_evidence_is_current",
    "stable_runtime_preflight_id",
    "validate_runtime_preflight_evidence",
]
