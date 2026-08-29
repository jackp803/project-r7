from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .external_close_reinterpretation import (
    CURRENT,
    DECISION_RECONCILE,
    LIFECYCLE_CLOSE_ELIGIBLE,
    NO_ACTION_CURRENT_KNOWN_OWNED,
    CurrentExternalCloseAuthority,
    ExternalCloseReinterpretationDecision,
    ExternalCloseReinterpretationError,
    external_close_convergence_evidence_is_current as _base_evidence_is_current,
    interpret_external_close_convergence as _base_interpret,
    validate_external_manual_close_convergence_evidence as _base_validate_fp10,
    validate_external_provider_ownership_evidence as _base_validate_fp04,
)
from .lifecycle_projection import LifecycleProjectionError, validate_position_lifecycle_projection
from .state_machine import PositionEvent, PositionLifecycleState, UnsafeTransitionError, transition

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


def _utc_text(value: Any, field: str):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalCloseReinterpretationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed


def validate_external_provider_ownership_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate FP-04 shape, vocabulary, deterministic ordering, and false-current claims."""

    _base_validate_fp04(evidence)
    reasons = evidence["reason_codes"]
    if any(code not in _FP04_REASON_INDEX for code in reasons):
        raise ExternalCloseReinterpretationError("FP04_REASON_UNKNOWN", "unknown FP-04 reason code")
    if reasons != sorted(set(reasons), key=_FP04_REASON_INDEX.__getitem__):
        raise ExternalCloseReinterpretationError("FP04_REASON_ORDER_INVALID", "FP-04 reasons are not deterministic")

    dispositions = evidence["required_dispositions"]
    if any(value not in _FP04_DISPOSITIONS for value in dispositions):
        raise ExternalCloseReinterpretationError("FP04_DISPOSITION_UNKNOWN", "unknown FP-04 disposition")
    if dispositions != sorted(set(dispositions)):
        raise ExternalCloseReinterpretationError("FP04_DISPOSITION_ORDER_INVALID", "FP-04 dispositions must be sorted and unique")
    if NO_ACTION_CURRENT_KNOWN_OWNED in dispositions and dispositions != [NO_ACTION_CURRENT_KNOWN_OWNED]:
        raise ExternalCloseReinterpretationError("FP04_FALSE_NO_ACTION", "NO_ACTION_CURRENT_KNOWN_OWNED is exclusive")

    lineage = evidence["local_lineage_evidence"]
    for item in lineage:
        if set(item) != _LINEAGE_FIELDS:
            raise ExternalCloseReinterpretationError("FP04_LINEAGE_FIELDS_INVALID", "FP-04 local lineage entry fields mismatch")
    registry = evidence["local_registry_evidence"]
    for item in registry:
        if set(item) != _REGISTRY_FIELDS:
            raise ExternalCloseReinterpretationError("FP04_REGISTRY_FIELDS_INVALID", "FP-04 registry entry fields mismatch")

    if evidence["reconciliation_status"] == "CURRENT_KNOWN_OWNED":
        if any(item.get("claim_status") in {"CONTRADICTS_LINEAGE", "UNKNOWN"} for item in lineage):
            raise ExternalCloseReinterpretationError("FP04_FALSE_CURRENT_OWNERSHIP", "current ownership cannot include contradictory/unknown lineage")
        if any(item.get("currentness_status") != CURRENT for item in registry):
            raise ExternalCloseReinterpretationError("FP04_FALSE_CURRENT_OWNERSHIP", "current ownership cannot depend on stale/conflicting registry evidence")


def validate_external_manual_close_convergence_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate FP-10 and enforce post-flat terminal-protection ordering before close eligibility."""

    _base_validate_fp10(evidence)
    if evidence.get("convergence_state") == LIFECYCLE_CLOSE_ELIGIBLE:
        provider_received = _utc_text(
            evidence.get("provider_position_received_at"),
            "provider_position_received_at",
        )
        terminal_received = _utc_text(
            evidence.get("terminal_protection_received_at"),
            "terminal_protection_received_at",
        )
        if terminal_received < provider_received:
            raise ExternalCloseReinterpretationError(
                "FP10_TERMINAL_PROTECTION_PRECEDES_FLAT_ACCEPTANCE",
                "close eligibility requires terminal protection observation after the flat Position acceptance boundary",
            )


def external_provider_ownership_evidence_is_current(
    evidence: Mapping[str, Any],
    *,
    provider_object_ref: str,
    provider_snapshot_ref: str,
    provider_snapshot_hash: str,
    provider_observation_generation_id: str,
    current_project_revision: str,
    runtime_preflight_ref: str | None = None,
    runtime_process_instance_id: str | None = None,
    runtime_process_start_generation_id: str | None = None,
    runtime_config_generation_id: str | None = None,
) -> bool:
    """Check FP-04 snapshot/generation currentness without upgrading ownership classification."""

    try:
        validate_external_provider_ownership_evidence(evidence)
    except ExternalCloseReinterpretationError:
        return False
    expected = {
        "provider_object_ref": provider_object_ref,
        "provider_snapshot_ref": provider_snapshot_ref,
        "provider_snapshot_hash": provider_snapshot_hash,
        "provider_observation_generation_id": provider_observation_generation_id,
        "current_project_revision": current_project_revision,
        "runtime_preflight_ref": runtime_preflight_ref,
        "runtime_process_instance_id": runtime_process_instance_id,
        "runtime_process_start_generation_id": runtime_process_start_generation_id,
        "runtime_config_generation_id": runtime_config_generation_id,
    }
    return all(evidence.get(field) == value for field, value in expected.items())


def external_close_convergence_evidence_is_current(
    evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
) -> bool:
    """Fail closed on stale/unknown FP-10 truth before using the base exact-binding check."""

    if evidence.get("provider_position_currentness_status") != CURRENT:
        return False
    try:
        validate_external_manual_close_convergence_evidence(evidence)
        return _base_evidence_is_current(evidence, authority)
    except (ExternalCloseReinterpretationError, InvalidOperation, ValueError, TypeError):
        return False


def _unknown_transition(current_state: PositionLifecycleState) -> tuple[PositionEvent | None, PositionLifecycleState]:
    if current_state == PositionLifecycleState.RECONCILIATION_REQUIRED:
        return None, current_state
    try:
        event = PositionEvent.STATE_UNKNOWN
        return event, transition(current_state, event)
    except UnsafeTransitionError:
        return None, current_state


def _decision_id(material: Mapping[str, Any]) -> str:
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "e5extclose_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reconcile_decision(
    evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
    *,
    reason: str,
    evidence_current: bool,
) -> ExternalCloseReinterpretationDecision:
    projection = authority.lifecycle_projection
    if projection is None:
        raise ExternalCloseReinterpretationError(
            "CURRENT_LIFECYCLE_MISSING",
            "current lifecycle projection is required for fail-closed reinterpretation",
        )
    try:
        facts = validate_position_lifecycle_projection(projection)
        current_state = PositionLifecycleState(projection["lifecycle_state"])
    except (LifecycleProjectionError, ValueError) as exc:
        raise ExternalCloseReinterpretationError(
            "CURRENT_LIFECYCLE_INVALID",
            "current lifecycle projection is invalid",
        ) from exc
    event, next_state = _unknown_transition(current_state)
    material = {
        "close_convergence_evidence_id": evidence.get("close_convergence_evidence_id"),
        "position_id": evidence.get("position_id"),
        "lifecycle_projection_id": facts["projection_id"],
        "lifecycle_revision": facts["revision"],
        "lifecycle_execution_binding_id": None
        if authority.lifecycle_execution_binding is None
        else authority.lifecycle_execution_binding.get("lifecycle_execution_binding_id"),
        "evidence_current": evidence_current,
        "decision": DECISION_RECONCILE,
        "event": None if event is None else event.value,
        "next_state": next_state.value,
        "reason_codes": [reason],
        "close_eligible": False,
        "trade_result_evidence_incomplete": "TRADE_RESULT_EVIDENCE_INCOMPLETE"
        in evidence.get("reason_codes", []),
    }
    return ExternalCloseReinterpretationDecision(
        decision_id=_decision_id(material),
        decision=DECISION_RECONCILE,
        event=event,
        next_state=next_state,
        reason_codes=(reason,),
        close_eligible=False,
        trade_result_evidence_incomplete=material["trade_result_evidence_incomplete"],
        evidence_current=evidence_current,
    )


def interpret_external_close_convergence(
    evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
) -> ExternalCloseReinterpretationDecision:
    """Safe E5 FP-04/FP-10 consumer used by the package public surface."""

    if not external_close_convergence_evidence_is_current(evidence, authority):
        return _reconcile_decision(
            evidence,
            authority,
            reason="E5_EXTERNAL_CLOSE_EVIDENCE_STALE_OR_MISMATCHED",
            evidence_current=False,
        )

    decision = _base_interpret(evidence, authority)
    position = authority.normalized_position
    if position is None:
        return _reconcile_decision(
            evidence,
            authority,
            reason="E5_CURRENT_POSITION_MISSING_NOT_FLAT",
            evidence_current=False,
        )
    try:
        quantity = Decimal(str(position.get("actual_quantity")))
    except (InvalidOperation, ValueError, TypeError):
        return _reconcile_decision(
            evidence,
            authority,
            reason="E5_CURRENT_POSITION_QUANTITY_UNKNOWN",
            evidence_current=False,
        )
    if not quantity.is_finite() or quantity < 0:
        return _reconcile_decision(
            evidence,
            authority,
            reason="E5_CURRENT_POSITION_QUANTITY_UNKNOWN",
            evidence_current=False,
        )
    if quantity > 0 and decision.next_state == PositionLifecycleState.CLOSED:
        return _reconcile_decision(
            evidence,
            authority,
            reason="E5_POSITIVE_EXPOSURE_FALSE_GREEN_CLOSED_BLOCKED",
            evidence_current=True,
        )
    return decision


def external_close_reinterpretation_decision_is_current(
    decision: ExternalCloseReinterpretationDecision,
    latest_evidence: Mapping[str, Any],
    authority: CurrentExternalCloseAuthority,
) -> bool:
    """A newer accepted FP-10 evidence object invalidates a decision bound to older evidence."""

    if not external_close_convergence_evidence_is_current(latest_evidence, authority):
        return False
    try:
        latest = interpret_external_close_convergence(latest_evidence, authority)
    except ExternalCloseReinterpretationError:
        return False
    return decision.decision_id == latest.decision_id
