from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from position.protection_trigger_validity import (
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
from .protection import prepare_protection_order, validate_protection_authority


class ProtectionTriggerConsumerError(ValueError):
    """Fail-closed E4 FP-03 consumer/binding error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


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
    evidence_position_time = _utc_text(evidence.get("position_observed_at"))
    current_position_time = _utc_text(current_position.get("broker_state_observed_at"))
    if (
        evidence_position_time is not None
        and current_position_time is not None
        and current_position_time > evidence_position_time
    ):
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_NOT_CURRENT",
            "newer current Position truth invalidates the bound trigger-validity evidence",
        )

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

    if action.get("position_id") != current_position.get("position_id"):
        raise ProtectionTriggerConsumerError(
            "E4_BINDING_MISMATCH",
            "PositionAction position_id does not match current Position identity",
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
    """Validate FP-03 evidence immediately before protection CREATE translation.

    This function performs no provider request or mutation. It consumes E5's
    accepted public validator/currentness surface rather than duplicating the
    shared evidence schema or reason vocabulary.
    """

    evidence = _mapping(trigger_validity_evidence, "ProtectionTriggerValidityEvidence")
    if evidence.get("protection_trigger_validity_profile_version") != PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION:
        raise ProtectionTriggerConsumerError(
            "UNSUPPORTED_TRIGGER_VALIDITY_PROFILE",
            "protection mutation requires protection-trigger-validity-v0.1 evidence",
        )

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


def prepare_trigger_validated_protection_order(
    action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    current_position: Mapping[str, Any],
    trigger_validity_evidence: Mapping[str, Any] | None,
    current_market_snapshot: Any,
    *,
    market_freshness_classification: str,
    now: datetime,
) -> OrderRequest:
    """Prepare only the provider-neutral OrderRequest after the FP-03 gate passes.

    The result is not proof that any provider-native trigger basis is compatible
    and is not provider-mutation authority. Provider translation must still pass
    a separate applicable provider capability boundary.
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
    return prepare_protection_order(
        action,
        parent_plan,
        current_position,
        now=now,
    )


def require_provider_trigger_basis_compatibility(
    trigger_validity_evidence: Mapping[str, Any],
    provider_capability_evidence: Any = None,
) -> None:
    """Fail closed until an applicable provider capability boundary proves compatibility.

    FP-03 deliberately does not invent, accept, or infer provider-native trigger
    basis semantics. The current repository has no accepted provider capability
    proof object for this boundary, so neither an arbitrary caller value nor
    shared LAST_PRICE evidence can make a provider mutation ready. A later
    separately scoped E4 provider capability implementation must replace/extend
    this guard with its own accepted proof semantics rather than caller booleans.
    """

    evidence = _mapping(trigger_validity_evidence, "ProtectionTriggerValidityEvidence")
    try:
        validate_protection_trigger_validity_evidence(evidence)
    except ProtectionTriggerValidityError as exc:
        raise ProtectionTriggerConsumerError(
            "E4_TRIGGER_VALIDITY_EVIDENCE_INVALID",
            "provider capability guard received invalid trigger-validity evidence",
        ) from exc
    if evidence.get("trigger_reference_semantic") != TRIGGER_REFERENCE_LAST_PRICE:
        raise ProtectionTriggerConsumerError(
            "PROVIDER_TRIGGER_BASIS_INCOMPATIBLE",
            "unsupported shared trigger semantic cannot be mapped to provider mutation",
        )

    # Intentionally no positive path in FP-03: accepting an arbitrary Mapping,
    # bool, string, or callback as proof would create caller-assertable provider
    # authority and silently bundle the separate provider capability work.
    del provider_capability_evidence
    raise ProtectionTriggerConsumerError(
        "PROVIDER_TRIGGER_BASIS_NOT_PROVEN",
        "shared LAST_PRICE evidence alone does not prove a provider-native trigger basis",
    )
