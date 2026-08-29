from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from src.position.protection_trigger_validity import (
    ACTIONABLE,
    PROTECTION_OPERATION_CREATE,
    PROTECTION_STOP_ORDER_ROLE,
    PROTECTION_TRIGGER_ACTIONABLE,
    PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION,
    TRIGGER_REFERENCE_LAST_PRICE,
    ProtectionTriggerValidityError,
    protection_trigger_validity_evidence_is_current,
    validate_protection_trigger_validity_evidence,
)

from .models import OrderRequest
from .protection import (
    ProtectionAuthorityError,
    prepare_protection_order,
    validate_protection_authority,
)


class ProtectionTriggerConsumerError(ValueError):
    """Fail-closed E4 FP-03 consumer/binding error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ProviderTriggerBasisCompatibility:
    """E4-private proof that a separate provider capability boundary is compatible.

    This proof intentionally does not contain a provider-native trigger-price
    parameter or spelling. In particular, shared LAST_PRICE evidence does not
    select or imply OKX `triggerPxType` (or any equivalent provider field).
    """

    capability_boundary_ref: str
    canonical_symbol: str
    order_role: str
    protection_operation: str
    shared_trigger_reference_semantic: str
    compatible: bool


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_EVIDENCE_REQUIRED",
            f"{field} must be canonical protection-trigger-validity evidence",
        )
    return value


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                f"{field} is not a valid canonical decimal",
            ) from exc
    else:
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            f"{field} must be a decimal string or Decimal",
        )
    if not parsed.is_finite() or parsed <= 0:
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            f"{field} must be finite and > 0",
        )
    return parsed


def _utc_text(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed.astimezone(timezone.utc)


def _market_payload(snapshot: Any) -> Mapping[str, Any] | None:
    if isinstance(snapshot, Mapping):
        return snapshot
    to_interchange = getattr(snapshot, "to_interchange_dict", None)
    if callable(to_interchange):
        payload = to_interchange()
        return payload if isinstance(payload, Mapping) else None
    if is_dataclass(snapshot) and not isinstance(snapshot, type):
        return {item.name: getattr(snapshot, item.name) for item in fields(snapshot)}
    return None


def _newer_relevant_truth_is_known(
    evidence: Mapping[str, Any],
    current_position: Mapping[str, Any],
    current_market_snapshot: Any,
) -> bool:
    evidence_position_time = _utc_text(evidence.get("position_observed_at"))
    current_position_time = _utc_text(current_position.get("broker_state_observed_at"))
    if (
        evidence_position_time is not None
        and current_position_time is not None
        and current_position_time > evidence_position_time
    ):
        return True

    payload = _market_payload(current_market_snapshot)
    if payload is None:
        return False
    for current_field, evidence_field in (
        ("observed_at", "market_observed_at"),
        ("received_at", "market_received_at"),
    ):
        current_time = _utc_text(payload.get(current_field))
        evidence_time = _utc_text(evidence.get(evidence_field))
        if current_time is not None and evidence_time is not None and current_time > evidence_time:
            return True
    return False


def _require_exact_create_binding(
    evidence: Mapping[str, Any],
    action: Mapping[str, Any],
    current_position: Mapping[str, Any],
) -> None:
    expected_pairs = (
        ("position_action_id", action.get("position_action_id")),
        ("position_id", current_position.get("position_id")),
        ("position_side", current_position.get("side")),
        ("position_observed_at", current_position.get("broker_state_observed_at")),
        ("position_reconciliation_status", current_position.get("reconciliation_status")),
        ("market_symbol", action.get("symbol")),
    )
    for field, expected in expected_pairs:
        if evidence.get(field) != expected:
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                f"trigger-validity {field} does not match the current protection mutation",
            )

    if evidence.get("order_role") != PROTECTION_STOP_ORDER_ROLE:
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "trigger-validity order_role must match PROTECTION_STOP",
        )
    if evidence.get("protection_operation") != PROTECTION_OPERATION_CREATE:
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "current protection-v0.1 mutation baseline executes CREATE only; REPLACE is not executable",
        )

    if action.get("symbol") != current_position.get("symbol"):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "PositionAction symbol does not match current Position symbol",
        )
    if action.get("position_side") != current_position.get("side"):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "PositionAction side does not match current Position side",
        )

    instruction = action.get("protection_instruction")
    if not isinstance(instruction, Mapping):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "PositionAction.protection_instruction is required",
        )
    if _decimal(evidence.get("stop_level"), "evidence.stop_level") != _decimal(
        instruction.get("stop_level"),
        "PositionAction.protection_instruction.stop_level",
    ):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "trigger-validity stop_level does not match the current protection mutation",
        )

    lifecycle_profile = current_position.get("position_lifecycle_projection_profile_version")
    if lifecycle_profile is None:
        if evidence.get("position_authority_type") != "BROKER_POSITION_OBSERVATION":
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "trigger-validity Position authority type does not match current broker Position authority",
            )
        if evidence.get("lifecycle_projection_id") is not None or evidence.get("lifecycle_revision") is not None:
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "broker Position authority cannot be rebound to lifecycle projection identity",
            )
    else:
        if evidence.get("position_authority_type") != "LIFECYCLE_PROJECTION":
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "trigger-validity Position authority type does not match current lifecycle projection authority",
            )
        if evidence.get("lifecycle_projection_id") != current_position.get("lifecycle_projection_id"):
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "trigger-validity lifecycle projection ID does not match current Position authority",
            )
        if evidence.get("lifecycle_revision") != current_position.get("lifecycle_revision"):
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "trigger-validity lifecycle revision does not match current Position authority",
            )
        if evidence.get("position_authority_ref") != current_position.get("lifecycle_projection_id"):
            raise ProtectionTriggerConsumerError(
                "E4_BINDING_MISMATCH",
                "trigger-validity Position authority reference does not match current lifecycle projection",
            )


def validate_protection_trigger_create_evidence(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    trigger_validity_evidence: Mapping[str, Any] | None,
    current_market_snapshot: Any,
    *,
    market_freshness_classification: str,
    now: datetime,
) -> dict[str, Any]:
    """Validate FP-03 evidence immediately before protection CREATE mutation readiness.

    This is provider-neutral and performs no provider request or mutation. It
    consumes E5's accepted public evidence validator/currentness surface rather
    than duplicating the shared evidence schema or reason vocabulary.
    """

    evidence = _mapping(trigger_validity_evidence, "ProtectionTriggerValidityEvidence")
    if evidence.get("protection_trigger_validity_profile_version") != PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION:
        raise ProtectionTriggerConsumerError(
            "UNSUPPORTED_TRIGGER_VALIDITY_PROFILE",
            "protection mutation requires protection-trigger-validity-v0.1 evidence",
        )

    # Mutation-input binding is checked before semantic actionability so an
    # otherwise well-formed object for a different role/action/Position cannot
    # be confused with current authorization.
    _require_exact_create_binding(evidence, action, current_position)

    try:
        validate_protection_trigger_validity_evidence(evidence)
    except ProtectionTriggerValidityError as exc:
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_EVIDENCE_INVALID",
            "trigger-validity evidence failed the accepted shared validator",
        ) from exc

    if evidence.get("validity_status") != ACTIONABLE or evidence.get("reason_codes") != [
        PROTECTION_TRIGGER_ACTIONABLE
    ]:
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_FAIL_CLOSED",
            "FAIL_CLOSED protection-trigger evidence cannot authorize create or retry",
        )

    if _newer_relevant_truth_is_known(evidence, current_position, current_market_snapshot):
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_NOT_CURRENT",
            "newer relevant Position or market truth invalidates the bound trigger-validity evidence",
        )

    if not protection_trigger_validity_evidence_is_current(
        evidence,
        current_position,
        action,
        current_market_snapshot,
        market_freshness_classification=market_freshness_classification,
        trigger_reference_semantic=TRIGGER_REFERENCE_LAST_PRICE,
        protection_operation=PROTECTION_OPERATION_CREATE,
    ):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "trigger-validity evidence is not bound to the exact current mutation inputs",
        )

    # Existing protection-v0.1 authority/quantity/expiry/reconciliation rules
    # remain independently mandatory after FP-03 validity succeeds.
    authority_facts = validate_protection_authority(
        action,
        parent_plan,
        current_position,
        now=now,
    )
    return {
        "protection_trigger_validity_id": evidence["protection_trigger_validity_id"],
        "quantity": authority_facts["quantity"],
        "stop_level": authority_facts["stop_level"],
        "trigger_reference_semantic": evidence["trigger_reference_semantic"],
    }


def validate_provider_trigger_basis_compatibility(
    proof: ProviderTriggerBasisCompatibility | None,
    *,
    evidence: Mapping[str, Any],
) -> None:
    """Require a separate capability-bound compatibility proof without inferring native basis."""

    if proof is None:
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_NOT_PROVEN",
            "shared LAST_PRICE evidence alone cannot authorize a provider-native trigger basis",
        )
    if not isinstance(proof, ProviderTriggerBasisCompatibility):
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_NOT_PROVEN",
            "provider trigger-basis compatibility must come from the E4 capability boundary",
        )
    if not isinstance(proof.capability_boundary_ref, str) or not proof.capability_boundary_ref.strip():
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_NOT_PROVEN",
            "provider capability boundary reference is required",
        )
    expected = (
        proof.canonical_symbol == evidence.get("market_symbol"),
        proof.order_role == PROTECTION_STOP_ORDER_ROLE,
        proof.protection_operation == PROTECTION_OPERATION_CREATE,
        proof.shared_trigger_reference_semantic == TRIGGER_REFERENCE_LAST_PRICE,
    )
    if not all(expected):
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_INCOMPATIBLE",
            "provider capability proof does not match the current shared protection intent",
        )
    if proof.compatible is not True:
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_INCOMPATIBLE",
            "provider trigger-basis compatibility is not proven",
        )


def prepare_mutation_ready_protection_create_order(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    trigger_validity_evidence: Mapping[str, Any] | None,
    current_market_snapshot: Any,
    provider_trigger_basis_compatibility: ProviderTriggerBasisCompatibility | None,
    *,
    market_freshness_classification: str,
    now: datetime,
) -> OrderRequest:
    """Return a canonical protection request only after FP-03 and provider-basis gates pass.

    The returned request is still provider-neutral. This function performs no
    network call and does not select a provider-native trigger parameter.
    """

    validate_protection_trigger_create_evidence(
        action,
        parent_plan,
        current_position,
        trigger_validity_evidence,
        current_market_snapshot,
        market_freshness_classification=market_freshness_classification,
        now=now,
    )
    evidence = _mapping(trigger_validity_evidence, "ProtectionTriggerValidityEvidence")
    validate_provider_trigger_basis_compatibility(
        provider_trigger_basis_compatibility,
        evidence=evidence,
    )
    return prepare_protection_order(
        action,
        parent_plan,
        current_position,
        now=now,
    )
