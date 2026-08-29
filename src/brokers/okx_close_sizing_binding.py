from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from .okx_close_sizing import (
    OKXCloseSizingError,
    OKXCloseSizingInput,
    canonical_okx_close_sizing_hash,
    evaluate_okx_close_residual_sizing as _evaluate,
    okx_close_residual_sizing_evidence_is_current as _is_current,
)


@dataclass(frozen=True)
class OKXCloseMetadataBindingEvidence:
    """E4-local exact binding between one close applicability proof and one metadata snapshot."""

    binding_ref: str
    instrument_metadata_ref: str
    instrument_metadata_hash: str
    instrument_metadata_generation: str
    metadata_applicability_proof_ref: str
    metadata_applicability_hash: str
    metadata_applicability_generation_id: str


def validate_okx_close_metadata_binding(
    sizing_input: OKXCloseSizingInput,
    binding: OKXCloseMetadataBindingEvidence,
) -> None:
    """Reject mixed metadata/applicability generations before FP-05 evaluation."""

    if not isinstance(binding, OKXCloseMetadataBindingEvidence):
        raise OKXCloseSizingError(
            "OKX_CLOSE_METADATA_BINDING_REQUIRED",
            "FP-05 requires typed exact metadata/applicability binding evidence",
        )
    if not isinstance(binding.binding_ref, str) or not binding.binding_ref.strip():
        raise OKXCloseSizingError(
            "OKX_CLOSE_METADATA_BINDING_INVALID",
            "metadata binding_ref must be non-empty",
        )

    metadata = sizing_input.instrument_metadata
    applicability = sizing_input.metadata_applicability
    expected = {
        "instrument_metadata_ref": metadata.metadata_ref,
        "instrument_metadata_hash": canonical_okx_close_sizing_hash(metadata),
        "instrument_metadata_generation": applicability.instrument_metadata_generation,
        "metadata_applicability_proof_ref": applicability.applicability_proof_ref,
        "metadata_applicability_hash": canonical_okx_close_sizing_hash(applicability),
        "metadata_applicability_generation_id": applicability.applicability_generation_id,
    }
    for field, expected_value in expected.items():
        if getattr(binding, field) != expected_value:
            raise OKXCloseSizingError(
                "OKX_CLOSE_METADATA_BINDING_MISMATCH",
                f"{field} does not bind the exact metadata/applicability evidence used for sizing",
            )


def evaluate_okx_close_residual_sizing(
    sizing_input: OKXCloseSizingInput,
    metadata_binding: OKXCloseMetadataBindingEvidence,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Strict E4 FP-05 entry point; still provider-free and mutation-free."""

    validate_okx_close_metadata_binding(sizing_input, metadata_binding)
    return _evaluate(sizing_input, supersedes_evidence=supersedes_evidence)


def okx_close_residual_sizing_evidence_is_current(
    evidence: Mapping[str, Any],
    sizing_input: OKXCloseSizingInput,
    metadata_binding: OKXCloseMetadataBindingEvidence,
) -> bool:
    """Fail closed if current metadata/applicability binding no longer matches exactly."""

    try:
        validate_okx_close_metadata_binding(sizing_input, metadata_binding)
    except OKXCloseSizingError:
        return False
    return _is_current(evidence, sizing_input)
