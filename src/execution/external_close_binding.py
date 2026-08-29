from __future__ import annotations

from typing import Any, Mapping

from .external_close_evidence import (
    CloseConvergenceAssemblyInput,
    ExternalCloseEvidenceError,
    build_external_manual_close_convergence_evidence as _build_fp10,
    canonical_evidence_hash,
    external_manual_close_convergence_evidence_is_current as _fp10_is_current,
)


def _matching_position_ownership_dependencies(
    assembly: CloseConvergenceAssemblyInput,
) -> list[Mapping[str, Any]]:
    provider = assembly.provider_position
    provider_identity_hash = canonical_evidence_hash(provider.provider_identity)
    provider_snapshot_hash = canonical_evidence_hash(provider.provider_position_snapshot)

    candidates: list[Mapping[str, Any]] = []
    for dependency in assembly.fp04_dependencies:
        evidence = dependency.evidence
        if evidence.get("provider_object_class") != "POSITION_EXPOSURE":
            continue
        if (
            evidence.get("provider_identity_ref") == provider.provider_identity_ref
            and evidence.get("provider_identity_hash") == provider_identity_hash
            and evidence.get("canonical_symbol") == provider.canonical_symbol
            and evidence.get("provider_instrument_ref") == provider.provider_instrument_ref
            and evidence.get("provider_snapshot_ref") == provider.provider_position_snapshot_ref
            and evidence.get("provider_snapshot_hash") == provider_snapshot_hash
            and evidence.get("provider_observation_generation_id")
            == provider.provider_position_observation_generation_id
            and evidence.get("provider_observed_at")
            == _canonical_utc(provider.provider_position_observed_at)
            and evidence.get("provider_received_at")
            == _canonical_utc(provider.provider_position_received_at)
        ):
            candidates.append(evidence)
    return candidates


def _canonical_utc(value: Any) -> str:
    # Reuse the canonical producer by comparing against a harmless timestamp
    # field already emitted by the supplied provider observation. Avoids
    # introducing a second temporal/profile interpretation surface here.
    from datetime import datetime, timezone

    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ExternalCloseEvidenceError(
                "FP10_POSITION_FP04_TIME_INVALID",
                "provider Position timestamp must be timezone-aware UTC",
            )
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExternalCloseEvidenceError(
            "FP10_POSITION_FP04_TIME_INVALID",
            "provider Position timestamp must be RFC3339 UTC Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExternalCloseEvidenceError(
            "FP10_POSITION_FP04_TIME_INVALID",
            "provider Position timestamp is invalid",
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ExternalCloseEvidenceError(
            "FP10_POSITION_FP04_TIME_INVALID",
            "provider Position timestamp must be UTC",
        )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_fp10_position_fp04_binding(
    assembly: CloseConvergenceAssemblyInput,
) -> Mapping[str, Any]:
    """Require exact FP-04 ownership evidence for the FP-10 provider Position snapshot.

    This validates evidence identity/current snapshot binding only. It does not
    upgrade ownership classification, choose an adoption policy, select a
    lifecycle transition, or authorize a provider mutation.
    """

    matches = _matching_position_ownership_dependencies(assembly)
    if not matches:
        raise ExternalCloseEvidenceError(
            "FP10_POSITION_FP04_BINDING_MISSING",
            "FP-10 requires FP-04 POSITION_EXPOSURE evidence for the exact provider Position snapshot/generation",
        )
    if len(matches) != 1:
        raise ExternalCloseEvidenceError(
            "FP10_POSITION_FP04_BINDING_AMBIGUOUS",
            "FP-10 provider Position must bind to exactly one matching FP-04 POSITION_EXPOSURE evidence object",
        )
    return matches[0]


def build_external_manual_close_convergence_evidence(
    assembly: CloseConvergenceAssemblyInput,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Strict E4 FP-10 assembly entry point with exact FP-04 Position binding."""

    validate_fp10_position_fp04_binding(assembly)
    return _build_fp10(assembly, supersedes_evidence=supersedes_evidence)


def external_manual_close_convergence_evidence_is_current(
    evidence: Mapping[str, Any],
    assembly: CloseConvergenceAssemblyInput,
) -> bool:
    """Return false when current FP-10 inputs no longer bind the exact FP-04 Position evidence."""

    try:
        validate_fp10_position_fp04_binding(assembly)
    except ExternalCloseEvidenceError:
        return False
    return _fp10_is_current(evidence, assembly)
