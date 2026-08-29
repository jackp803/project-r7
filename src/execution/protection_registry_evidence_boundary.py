from __future__ import annotations

from typing import Any, Mapping, Sequence

from .protection_registry_evidence import (
    CONVERGED_EXACTLY_ONE_INTENDED,
    OWNERSHIP_MANUAL_REVIEW_REQUIRED,
    ProtectionRegistryEvidenceError,
    ProtectionRegistryMultiplicityInput,
    _evidence_id,
    _sorted_dispositions,
    _sorted_reasons,
    build_protection_registry_multiplicity_evidence as _build_evidence,
    validate_protection_registry_multiplicity_evidence,
)

_UNKNOWN = "UNKNOWN"
_MANUAL_REVIEW_REASON = "PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED"


def _objects(value: ProtectionRegistryMultiplicityInput) -> Sequence[Mapping[str, Any]]:
    observed = value.observed_active_protection_set
    if not isinstance(observed, Mapping):
        return ()
    objects = observed.get("objects")
    if isinstance(objects, (str, bytes)) or not isinstance(objects, Sequence):
        return ()
    return tuple(item for item in objects if isinstance(item, Mapping))


def _has_ambiguous_ownership_or_lineage(value: ProtectionRegistryMultiplicityInput) -> bool:
    if any(item.get("intended_lineage_binding_status") == _UNKNOWN for item in _objects(value)):
        return True
    for dependency in value.fp04_dependencies:
        evidence = getattr(dependency, "evidence", None)
        if not isinstance(evidence, Mapping):
            return True
        if (
            evidence.get("ownership_classification") == _UNKNOWN
            or evidence.get("reconciliation_status") == _UNKNOWN
        ):
            return True
    return False


def _material_without_refresh_fields(evidence: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(evidence)
    for field in (
        "protection_registry_evidence_id",
        "supersedes_registry_evidence_id",
        "evaluated_at",
    ):
        material.pop(field, None)
    return material


def _enforce_strict_supersession_material_change(
    evidence: Mapping[str, Any],
    supersedes_evidence: Mapping[str, Any] | None,
) -> None:
    if supersedes_evidence is None:
        return
    if _material_without_refresh_fields(evidence) == _material_without_refresh_fields(
        supersedes_evidence
    ):
        raise ProtectionRegistryEvidenceError(
            "SUPERSESSION_REQUIRES_MATERIAL_CHANGE",
            "evaluated_at alone cannot justify strict FP-11 supersession",
        )


def build_protection_registry_multiplicity_evidence(
    value: ProtectionRegistryMultiplicityInput,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Strict FP-11 E4 entry point with explicit ambiguity/manual-review routing.

    The underlying producer owns normalization, state derivation, identity,
    currentness and supersession. This boundary only makes the task-required
    ambiguous exact-lineage/ownership path explicit using vocabulary already
    accepted by protection-registry-multiplicity-v0.1. It never selects a
    cleanup target and never creates provider mutation authority.
    """

    evidence = _build_evidence(value, supersedes_evidence=supersedes_evidence)
    if (
        evidence.get("registry_status") != CONVERGED_EXACTLY_ONE_INTENDED
        and _has_ambiguous_ownership_or_lineage(value)
    ):
        updated = dict(evidence)
        updated["required_dispositions"] = _sorted_dispositions(
            [*updated["required_dispositions"], OWNERSHIP_MANUAL_REVIEW_REQUIRED]
        )
        updated["reason_codes"] = _sorted_reasons(
            [*updated["reason_codes"], _MANUAL_REVIEW_REASON]
        )
        updated["protection_registry_evidence_id"] = _evidence_id(updated)
        validate_protection_registry_multiplicity_evidence(updated)
        _enforce_strict_supersession_material_change(updated, supersedes_evidence)
        return updated
    _enforce_strict_supersession_material_change(evidence, supersedes_evidence)
    return evidence


def protection_registry_multiplicity_evidence_is_current(
    evidence: Mapping[str, Any],
    current_input: ProtectionRegistryMultiplicityInput,
) -> bool:
    """Material-currentness check using the strict ambiguity boundary."""

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
    return all(
        evidence.get(field) == fresh.get(field)
        for field in evidence
        if field not in ignored
    )
