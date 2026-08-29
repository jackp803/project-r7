from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .external_close_reinterpretation import (
    CURRENT,
    DECISION_RECONCILE,
    CurrentExternalCloseAuthority,
    ExternalCloseReinterpretationDecision,
    ExternalCloseReinterpretationError,
    external_close_convergence_evidence_is_current as _base_evidence_is_current,
    interpret_external_close_convergence as _base_interpret,
    validate_external_provider_ownership_evidence,
)
from .lifecycle_projection import LifecycleProjectionError, validate_position_lifecycle_projection
from .state_machine import PositionEvent, PositionLifecycleState, UnsafeTransitionError, transition


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
    """Fail closed on stale/unknown FP-10 provider truth before using the base exact-binding check."""

    if evidence.get("provider_position_currentness_status") != CURRENT:
        return False
    try:
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
    """Safe E5 FP-04/FP-10 consumer used by the package public surface.

    A stale/unknown currentness axis is reconciled before the base policy may
    consider closure. Positive authoritative exposure can never preserve or
    produce a CLOSED lifecycle state, including when a stale local projection
    already says CLOSED.
    """

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
    """A newer FP-10 object invalidates a prior E5 decision even if only its immutable evidence ID changed."""

    if not external_close_convergence_evidence_is_current(latest_evidence, authority):
        return False
    try:
        latest = interpret_external_close_convergence(latest_evidence, authority)
    except ExternalCloseReinterpretationError:
        return False
    return decision.decision_id == latest.decision_id
