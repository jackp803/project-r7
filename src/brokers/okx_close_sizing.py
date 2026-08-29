from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from enum import Enum
from typing import Any, Mapping

from src.brokers.okx_sizing import (
    OKXInstrumentMetadata,
    OKXMetadataValidationError,
    OKXUnsupportedConversionError,
    validate_okx_instrument_metadata,
)
from src.execution.close import (
    CLOSE_PROFILE_VERSION,
    EMERGENCY_EXIT,
    EMERGENCY_EXIT_ROLE,
    EXIT,
    POSITION_EXIT_ROLE,
    CloseAuthorityError,
    validate_close_authority,
)
from src.execution.external_close_evidence import (
    CURRENT,
    CURRENT_KNOWN_OWNED,
    KNOWN_OWNED_CURRENT_GENERATION,
    NO_ACTION_CURRENT_KNOWN_OWNED,
    ExternalCloseEvidenceError,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    canonical_evidence_hash,
    external_provider_ownership_evidence_is_current,
)

CLOSE_RESIDUAL_SIZING_PROFILE_VERSION = "okx-swap-close-residual-sizing-v0.1"
FP02_CAPABILITY_PROFILE_VERSION = "okx-swap-action-role-capability-v0.1"

OKX_PROVIDER = "OKX"
CANONICAL_SYMBOL = "BTC_USDT_PERP"
OKX_INSTRUMENT_ID = "BTC-USDT-SWAP"
OKX_INST_TYPE = "SWAP"
ACCOUNT_LEVEL = "2"
MARGIN_MODE = "isolated"
QUANTITY_PROFILE_VERSION = "base-asset-v0.1"
QUANTITY_UNIT = "BASE_ASSET"
QUANTITY_ASSET = "BTC"
PROVIDER_QUANTITY_UNIT = "CONTRACT"

PRE_ACTION = "PRE_ACTION"
POST_ACTION_RESIDUAL = "POST_ACTION_RESIDUAL"
PRIOR_OUTCOME_CLEAR = "CLEAR"
PRIOR_OUTCOME_AMBIGUOUS = "AMBIGUOUS"

REPO_EVIDENCED = "REPO_EVIDENCED"
UNRESOLVED_FAIL_CLOSED = "UNRESOLVED_FAIL_CLOSED"
FORBIDDEN = "FORBIDDEN"
NOT_APPLICABLE = "NOT_APPLICABLE"

REQUIRED_FOR_CLOSE = "REQUIRED_FOR_CLOSE"
APPLICABLE_CONSTRAINT = "APPLICABLE_CONSTRAINT"
NOT_APPLICABLE_TO_CLOSE = "NOT_APPLICABLE_TO_CLOSE"
CLOSE_ROLE_SCOPE = "CLOSE_ROLE"

FULLY_REDUCIBLE = "FULLY_REDUCIBLE"
PARTIALLY_REDUCIBLE = "PARTIALLY_REDUCIBLE"
RESIDUAL_NONZERO_REPRESENTABLE = "RESIDUAL_NONZERO_REPRESENTABLE"
RESIDUAL_NONZERO_UNREPRESENTABLE = "RESIDUAL_NONZERO_UNREPRESENTABLE"
EXPOSURE_ALREADY_FLAT = "EXPOSURE_ALREADY_FLAT"
REDUCIBLE_EXPOSURE_UNKNOWN = "REDUCIBLE_EXPOSURE_UNKNOWN"
METADATA_STALE_OR_UNKNOWN = "METADATA_STALE_OR_UNKNOWN"
RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
CLOSE_CAPABILITY_UNPROVEN = "CLOSE_CAPABILITY_UNPROVEN"

_STATES = frozenset(
    {
        FULLY_REDUCIBLE,
        PARTIALLY_REDUCIBLE,
        RESIDUAL_NONZERO_REPRESENTABLE,
        RESIDUAL_NONZERO_UNREPRESENTABLE,
        EXPOSURE_ALREADY_FLAT,
        REDUCIBLE_EXPOSURE_UNKNOWN,
        METADATA_STALE_OR_UNKNOWN,
        RECONCILIATION_REQUIRED,
        CLOSE_CAPABILITY_UNPROVEN,
    }
)
_PHASES = frozenset({PRE_ACTION, POST_ACTION_RESIDUAL})
_PRIOR_OUTCOMES = frozenset({PRIOR_OUTCOME_CLEAR, PRIOR_OUTCOME_AMBIGUOUS})
_CAPABILITY_STATES = frozenset({REPO_EVIDENCED, UNRESOLVED_FAIL_CLOSED, FORBIDDEN, NOT_APPLICABLE})
_APPLICABILITY_STATES = frozenset(
    {REQUIRED_FOR_CLOSE, APPLICABLE_CONSTRAINT, NOT_APPLICABLE_TO_CLOSE, UNRESOLVED_FAIL_CLOSED}
)
_CURRENTNESS = frozenset({CURRENT, "STALE", "CONFLICT", "UNKNOWN"})

_REASON_ORDER = (
    "OKX_CLOSE_SIZING_PROFILE_UNSUPPORTED",
    "OKX_CLOSE_ROLE_UNSUPPORTED",
    "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED",
    "OKX_CLOSE_PRIOR_OUTCOME_AMBIGUOUS",
    "OKX_CLOSE_OWNERSHIP_RECONCILIATION_REQUIRED",
    "OKX_CLOSE_REDUCIBLE_EXPOSURE_UNKNOWN",
    "OKX_CLOSE_PROVIDER_FLAT_PROVEN",
    "OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH",
    "OKX_CLOSE_CAPABILITY_UNPROVEN",
    "OKX_CLOSE_PROVIDER_POSITION_UNIT_UNPROVEN",
    "OKX_CLOSE_METADATA_UNKNOWN_OR_STALE",
    "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN",
    "OKX_CLOSE_SIZE_ZERO_OR_NEGATIVE",
    "OKX_CLOSE_SIZE_EXCEEDS_REDUCIBLE_EXPOSURE",
    "OKX_CLOSE_SIZE_EXCEEDS_CANONICAL_AUTHORITY",
    "OKX_CLOSE_SIZE_NOT_REPRESENTABLE",
    "OKX_CLOSE_RESIDUAL_NONZERO_UNREPRESENTABLE",
    "OKX_CLOSE_NEWER_EVIDENCE_REQUIRED",
    "OKX_CLOSE_FULLY_REDUCIBLE",
    "OKX_CLOSE_PARTIALLY_REDUCIBLE",
    "OKX_CLOSE_RESIDUAL_NONZERO_REPRESENTABLE",
)
_REASON_INDEX = {value: index for index, value in enumerate(_REASON_ORDER)}

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^okxclosesz_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_EVIDENCE_FIELDS = frozenset(
    {
        "close_residual_sizing_profile_version",
        "sizing_evidence_id",
        "sizing_evidence_hash",
        "evaluation_phase",
        "action_role",
        "position_action_id",
        "parent_trade_plan_id",
        "parent_plan_hash",
        "source_position_ref",
        "source_position_hash",
        "current_position_ref",
        "current_position_hash",
        "position_id",
        "canonical_position_observed_at",
        "canonical_authorized_close_quantity",
        "current_canonical_quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "prior_close_outcome_status",
        "prior_close_outcome_ref",
        "fp02_capability_profile_version",
        "fp02_capability_row_ref",
        "fp02_capability_evidence_hash",
        "fp02_capability_state",
        "fp02_capability_generation_id",
        "fp02_capability_currentness_status",
        "provider_identity_ref",
        "provider_identity_hash",
        "provider_instrument_id",
        "account_level",
        "position_mode",
        "margin_mode",
        "provider_position_side_ref",
        "provider_position_snapshot_ref",
        "provider_position_snapshot_hash",
        "provider_position_observation_generation_id",
        "provider_position_observed_at",
        "provider_position_received_at",
        "provider_position_currentness_status",
        "provider_reducible_quantity",
        "provider_reducible_quantity_unit",
        "provider_normalized_canonical_quantity",
        "fp04_ownership_evidence_ref",
        "fp04_ownership_evidence_hash",
        "fp04_ownership_classification",
        "fp04_reconciliation_status",
        "fp04_required_dispositions",
        "instrument_metadata_ref",
        "instrument_metadata_hash",
        "instrument_metadata_generation",
        "instrument_metadata_observed_at",
        "instrument_metadata_freshness_policy_version",
        "metadata_applicability_proof_ref",
        "metadata_applicability_hash",
        "metadata_applicability_generation_id",
        "metadata_applicability_currentness_status",
        "conversion_profile",
        "provider_ct_val",
        "provider_ct_mult",
        "provider_ct_val_ccy",
        "provider_ct_type",
        "close_step",
        "close_min_size",
        "close_max_size",
        "raw_provider_close_size",
        "quantized_provider_close_size",
        "effective_canonical_close_quantity",
        "sizing_state",
        "reason_codes",
        "supersedes_sizing_evidence_id",
        "evaluated_at",
    }
)


class OKXCloseSizingError(ValueError):
    """Fail-closed provider-local FP-05 evaluation error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class OKXProviderExposureObservation:
    provider_identity_ref: str
    provider_identity: Mapping[str, Any]
    provider_object_ref: str
    provider_position_side_ref: str
    provider_position_snapshot_ref: str
    provider_position_snapshot: Mapping[str, Any]
    provider_position_observation_generation_id: str
    provider_position_observed_at: datetime
    provider_position_received_at: datetime
    provider_position_currentness_status: str
    provider_reducible_quantity: Decimal | None
    provider_reducible_quantity_unit: str
    normalized_canonical_quantity: Decimal
    account_level: str
    position_mode: str
    margin_mode: str
    provider_instrument_id: str = OKX_INSTRUMENT_ID


@dataclass(frozen=True)
class OKXCloseRoleCapabilityEvidence:
    capability_profile_version: str
    capability_row_ref: str
    action_role: str
    capability_state: str
    capability_generation_id: str
    currentness_status: str
    provider: str
    canonical_symbol: str
    provider_instrument_id: str
    inst_type: str
    account_level: str
    position_mode: str
    margin_mode: str
    provider_position_quantity_unit: str
    provider_position_quantity_proof_ref: str
    provider_fieldset_status: str


@dataclass(frozen=True)
class OKXCloseMetadataApplicabilityEvidence:
    action_role: str
    applicability_scope: str
    applicability_proof_ref: str
    applicability_generation_id: str
    currentness_status: str
    instrument_metadata_generation: str
    conversion_profile: str
    conversion_status: str
    step_status: str
    min_status: str
    max_status: str
    close_step: Decimal | None
    close_min_size: Decimal | None
    close_max_size: Decimal | None


@dataclass(frozen=True)
class OKXCloseSizingInput:
    action: Mapping[str, Any]
    parent_plan: Mapping[str, Any]
    source_position: Mapping[str, Any]
    current_position: Mapping[str, Any]
    evaluation_phase: str
    prior_close_outcome_status: str
    prior_close_outcome_ref: str
    provider_exposure: OKXProviderExposureObservation
    fp04_ownership_evidence: Mapping[str, Any]
    fp04_currentness_context: OwnershipEvaluationContext
    capability: OKXCloseRoleCapabilityEvidence
    instrument_metadata: OKXInstrumentMetadata
    metadata_applicability: OKXCloseMetadataApplicabilityEvidence
    evaluated_at: datetime


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise OKXCloseSizingError("NONCANONICAL_DECIMAL", "Decimal must be finite")
        return format(value, "f")
    if isinstance(value, datetime):
        return _utc_text(value, "datetime")
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise OKXCloseSizingError("NONCANONICAL_KEY", "mapping keys must be strings")
            result[key] = _canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        raise OKXCloseSizingError("BINARY_FLOAT_FORBIDDEN", "binary floats are forbidden")
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise OKXCloseSizingError("NONCANONICAL_VALUE", f"unsupported canonical value: {type(value).__name__}")


def canonical_okx_close_sizing_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_okx_close_sizing_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_okx_close_sizing_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise OKXCloseSizingError("INVALID_TEXT", f"{field} must be non-empty canonical text")
    return value


def _hash(value: Any, field: str) -> str:
    text = _text(value, field)
    if _HASH_RE.fullmatch(text) is None:
        raise OKXCloseSizingError("INVALID_HASH", f"{field} must be sha256:<lowercase hex>")
    return text


def _utc_text(value: datetime | str, field: str) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise OKXCloseSizingError("INVALID_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OKXCloseSizingError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OKXCloseSizingError("INVALID_TIMESTAMP", f"{field} is invalid") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OKXCloseSizingError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_dt(value: datetime | str, field: str) -> datetime:
    text = _utc_text(value, field)
    return datetime.fromisoformat(text[:-1] + "+00:00").astimezone(timezone.utc)


def _decimal(value: Any, field: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str) and _DECIMAL_RE.fullmatch(value) is not None:
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise OKXCloseSizingError("INVALID_DECIMAL", f"{field} is invalid") from exc
    else:
        raise OKXCloseSizingError("INVALID_DECIMAL", f"{field} must be a canonical decimal")
    if not parsed.is_finite() or parsed < 0 or (positive and parsed <= 0):
        qualifier = "> 0" if positive else ">= 0"
        raise OKXCloseSizingError("INVALID_DECIMAL", f"{field} must be finite and {qualifier}")
    return parsed


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _position_ref(position: Mapping[str, Any]) -> str:
    return "position:" + _text(position.get("position_id"), "Position.position_id") + "@" + _utc_text(
        position.get("broker_state_observed_at"), "Position.broker_state_observed_at"
    )


def _action_role(action: Mapping[str, Any]) -> str:
    if action.get("close_profile_version") != CLOSE_PROFILE_VERSION:
        raise OKXCloseSizingError("OKX_CLOSE_SIZING_PROFILE_UNSUPPORTED", "close action must use close-v0.1")
    action_type = action.get("action")
    if action_type == EXIT:
        return POSITION_EXIT_ROLE
    if action_type == EMERGENCY_EXIT:
        return EMERGENCY_EXIT_ROLE
    raise OKXCloseSizingError("OKX_CLOSE_ROLE_UNSUPPORTED", "action must be EXIT or EMERGENCY_EXIT")


def _current_position_facts(position: Mapping[str, Any]) -> tuple[Decimal, str]:
    required = (
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "broker_state_observed_at",
        "reconciliation_status",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    )
    missing = [field for field in required if field not in position]
    if missing:
        raise OKXCloseSizingError("CURRENT_POSITION_INCOMPLETE", f"current Position missing fields: {missing}")
    if position.get("symbol") != CANONICAL_SYMBOL:
        raise OKXCloseSizingError("CURRENT_POSITION_SYMBOL_UNSUPPORTED", "current Position must be BTC_USDT_PERP")
    if position.get("side") not in {"LONG", "SHORT"}:
        raise OKXCloseSizingError("CURRENT_POSITION_SIDE_INVALID", "current Position side must be LONG or SHORT")
    if position.get("quantity_profile_version") != QUANTITY_PROFILE_VERSION:
        raise OKXCloseSizingError("CURRENT_POSITION_QUANTITY_PROFILE_INVALID", "quantity profile must be base-asset-v0.1")
    if position.get("quantity_unit") != QUANTITY_UNIT or position.get("quantity_asset") != QUANTITY_ASSET:
        raise OKXCloseSizingError("CURRENT_POSITION_QUANTITY_UNIT_INVALID", "current Position quantity must be BASE_ASSET/BTC")
    quantity = _decimal(position.get("actual_quantity"), "Position.actual_quantity")
    observed = _utc_text(position.get("broker_state_observed_at"), "Position.broker_state_observed_at")
    return quantity, observed


def _validate_phase_authority(value: OKXCloseSizingInput, action_role: str) -> tuple[bool, str | None]:
    if value.evaluation_phase not in _PHASES:
        raise OKXCloseSizingError("EVALUATION_PHASE_INVALID", "evaluation phase is unsupported")
    if value.prior_close_outcome_status not in _PRIOR_OUTCOMES:
        raise OKXCloseSizingError("PRIOR_OUTCOME_STATUS_INVALID", "prior close outcome status is unsupported")
    _text(value.prior_close_outcome_ref, "prior_close_outcome_ref")

    now = value.evaluated_at
    if value.evaluation_phase == POST_ACTION_RESIDUAL:
        created_at = value.action.get("created_at")
        try:
            now = _utc_dt(created_at, "PositionAction.created_at")
        except OKXCloseSizingError:
            return False, "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"
    try:
        validate_close_authority(value.action, value.parent_plan, value.source_position, now=now)
    except CloseAuthorityError:
        return False, "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"

    source_ref = _position_ref(value.source_position)
    current_ref = _position_ref(value.current_position)
    if value.evaluation_phase == PRE_ACTION and source_ref != current_ref:
        return False, "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"
    if value.evaluation_phase == POST_ACTION_RESIDUAL:
        if (
            value.source_position.get("position_id") != value.current_position.get("position_id")
            or value.source_position.get("symbol") != value.current_position.get("symbol")
            or value.source_position.get("side") != value.current_position.get("side")
            or value.source_position.get("quantity_profile_version")
            != value.current_position.get("quantity_profile_version")
            or value.source_position.get("quantity_unit") != value.current_position.get("quantity_unit")
            or value.source_position.get("quantity_asset") != value.current_position.get("quantity_asset")
        ):
            return False, "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"
        if _utc_dt(value.current_position["broker_state_observed_at"], "current Position observed_at") < _utc_dt(
            value.source_position["broker_state_observed_at"], "source Position observed_at"
        ):
            return False, "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"
    expected_role = POSITION_EXIT_ROLE if value.action.get("action") == EXIT else EMERGENCY_EXIT_ROLE
    return expected_role == action_role, None


def _provider_observation(value: OKXCloseSizingInput) -> ProviderObjectObservation:
    provider = value.provider_exposure
    return ProviderObjectObservation(
        provider_object_class="POSITION_EXPOSURE",
        provider_identity_ref=provider.provider_identity_ref,
        provider_identity=provider.provider_identity,
        canonical_symbol=CANONICAL_SYMBOL,
        provider_instrument_ref=provider.provider_instrument_id,
        provider_object_ref=provider.provider_object_ref,
        provider_snapshot_ref=provider.provider_position_snapshot_ref,
        provider_snapshot=provider.provider_position_snapshot,
        provider_observation_generation_id=provider.provider_position_observation_generation_id,
        provider_observed_at=provider.provider_position_observed_at,
        provider_received_at=provider.provider_position_received_at,
    )


def _fp04_status(value: OKXCloseSizingInput) -> tuple[bool, bool]:
    evidence = value.fp04_ownership_evidence
    try:
        exact_current = external_provider_ownership_evidence_is_current(
            evidence,
            _provider_observation(value),
            value.fp04_currentness_context,
        )
    except ExternalCloseEvidenceError:
        return False, False
    current_owned = (
        evidence.get("ownership_classification") == KNOWN_OWNED_CURRENT_GENERATION
        and evidence.get("reconciliation_status") == CURRENT_KNOWN_OWNED
        and evidence.get("required_dispositions") == [NO_ACTION_CURRENT_KNOWN_OWNED]
    )
    return exact_current, current_owned


def _capability_is_proven(value: OKXCloseSizingInput, action_role: str) -> bool:
    capability = value.capability
    if capability.capability_profile_version != FP02_CAPABILITY_PROFILE_VERSION:
        return False
    if capability.capability_state not in _CAPABILITY_STATES or capability.capability_state != REPO_EVIDENCED:
        return False
    if capability.provider_fieldset_status != REPO_EVIDENCED:
        return False
    if capability.currentness_status != CURRENT:
        return False
    if capability.action_role != action_role:
        return False
    if (
        capability.provider != OKX_PROVIDER
        or capability.canonical_symbol != CANONICAL_SYMBOL
        or capability.provider_instrument_id != OKX_INSTRUMENT_ID
        or capability.inst_type != OKX_INST_TYPE
        or capability.account_level != ACCOUNT_LEVEL
        or capability.margin_mode != MARGIN_MODE
    ):
        return False
    provider = value.provider_exposure
    if (
        capability.account_level != provider.account_level
        or capability.position_mode != provider.position_mode
        or capability.margin_mode != provider.margin_mode
        or capability.provider_instrument_id != provider.provider_instrument_id
    ):
        return False
    if capability.provider_position_quantity_unit != provider.provider_reducible_quantity_unit:
        return False
    if capability.provider_position_quantity_unit != PROVIDER_QUANTITY_UNIT:
        return False
    _text(capability.capability_row_ref, "capability_row_ref")
    _text(capability.capability_generation_id, "capability_generation_id")
    _text(capability.provider_position_quantity_proof_ref, "provider_position_quantity_proof_ref")
    return True


def _metadata_status(
    value: OKXCloseSizingInput,
    action_role: str,
) -> tuple[bool, str | None, OKXInstrumentMetadata | None]:
    proof = value.metadata_applicability
    if proof.currentness_status not in _CURRENTNESS or proof.currentness_status != CURRENT:
        return False, "OKX_CLOSE_METADATA_UNKNOWN_OR_STALE", None
    if proof.action_role != action_role or proof.applicability_scope != CLOSE_ROLE_SCOPE:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if (
        proof.conversion_status != REQUIRED_FOR_CLOSE
        or proof.step_status != APPLICABLE_CONSTRAINT
        or proof.min_status not in {APPLICABLE_CONSTRAINT, NOT_APPLICABLE_TO_CLOSE}
        or proof.max_status not in {APPLICABLE_CONSTRAINT, NOT_APPLICABLE_TO_CLOSE}
    ):
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if any(
        status not in _APPLICABILITY_STATES
        for status in (proof.conversion_status, proof.step_status, proof.min_status, proof.max_status)
    ):
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if proof.step_status == APPLICABLE_CONSTRAINT and proof.close_step is None:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if proof.min_status == APPLICABLE_CONSTRAINT and proof.close_min_size is None:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if proof.min_status == NOT_APPLICABLE_TO_CLOSE and proof.close_min_size is not None:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if proof.max_status == APPLICABLE_CONSTRAINT and proof.close_max_size is None:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    if proof.max_status == NOT_APPLICABLE_TO_CLOSE and proof.close_max_size is not None:
        return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    _text(proof.applicability_proof_ref, "applicability_proof_ref")
    _text(proof.applicability_generation_id, "applicability_generation_id")
    _text(proof.instrument_metadata_generation, "instrument_metadata_generation")
    try:
        checked = validate_okx_instrument_metadata(value.instrument_metadata, now=value.evaluated_at)
    except (OKXMetadataValidationError, OKXUnsupportedConversionError):
        return False, "OKX_CLOSE_METADATA_UNKNOWN_OR_STALE", None
    if checked.metadata_ref != value.instrument_metadata.metadata_ref:
        return False, "OKX_CLOSE_METADATA_UNKNOWN_OR_STALE", None
    for amount, field in (
        (proof.close_step, "close_step"),
        (proof.close_min_size, "close_min_size"),
        (proof.close_max_size, "close_max_size"),
    ):
        if amount is not None:
            _decimal(amount, field, positive=True)
    if proof.close_min_size is not None and proof.close_step is not None:
        ratio = proof.close_min_size / proof.close_step
        if ratio != ratio.to_integral_value():
            return False, "OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", None
    return True, None, checked


def _sort_reasons(values: list[str]) -> list[str]:
    unknown = [value for value in values if value not in _REASON_INDEX]
    if unknown:
        raise OKXCloseSizingError("REASON_UNKNOWN", f"unknown FP-05 reasons: {unknown}")
    return sorted(set(values), key=_REASON_INDEX.__getitem__)


def _material_without_identity(evidence: Mapping[str, Any], *, ignore_evaluated_at: bool = True) -> dict[str, Any]:
    material = dict(evidence)
    material.pop("sizing_evidence_id", None)
    material.pop("sizing_evidence_hash", None)
    if ignore_evaluated_at:
        material.pop("evaluated_at", None)
    return material


def _identity(evidence: Mapping[str, Any]) -> tuple[str, str]:
    material = _material_without_identity(evidence, ignore_evaluated_at=True)
    digest = hashlib.sha256(canonical_okx_close_sizing_json(material).encode("utf-8")).hexdigest()
    return "okxclosesz_" + digest, "sha256:" + digest


def _build_evidence(
    value: OKXCloseSizingInput,
    *,
    action_role: str,
    sizing_state: str,
    reason_codes: list[str],
    raw_provider_close_size: Decimal | None,
    quantized_provider_close_size: Decimal | None,
    effective_canonical_close_quantity: Decimal | None,
    checked_metadata: OKXInstrumentMetadata | None,
    supersedes_id: str | None,
) -> dict[str, Any]:
    provider = value.provider_exposure
    capability = value.capability
    proof = value.metadata_applicability
    current_quantity, current_observed = _current_position_facts(value.current_position)
    source_position_ref = _position_ref(value.source_position)
    current_position_ref = _position_ref(value.current_position)
    action_quantity = _decimal(value.action.get("quantity"), "PositionAction.quantity")
    fp04 = value.fp04_ownership_evidence
    metadata = value.instrument_metadata

    evidence: dict[str, Any] = {
        "close_residual_sizing_profile_version": CLOSE_RESIDUAL_SIZING_PROFILE_VERSION,
        "evaluation_phase": value.evaluation_phase,
        "action_role": action_role,
        "position_action_id": value.action.get("position_action_id"),
        "parent_trade_plan_id": value.action.get("trade_plan_id"),
        "parent_plan_hash": canonical_okx_close_sizing_hash(value.parent_plan),
        "source_position_ref": source_position_ref,
        "source_position_hash": canonical_okx_close_sizing_hash(value.source_position),
        "current_position_ref": current_position_ref,
        "current_position_hash": canonical_okx_close_sizing_hash(value.current_position),
        "position_id": value.current_position.get("position_id"),
        "canonical_position_observed_at": current_observed,
        "canonical_authorized_close_quantity": format(action_quantity, "f"),
        "current_canonical_quantity": format(current_quantity, "f"),
        "quantity_profile_version": value.current_position.get("quantity_profile_version"),
        "quantity_unit": value.current_position.get("quantity_unit"),
        "quantity_asset": value.current_position.get("quantity_asset"),
        "prior_close_outcome_status": value.prior_close_outcome_status,
        "prior_close_outcome_ref": value.prior_close_outcome_ref,
        "fp02_capability_profile_version": capability.capability_profile_version,
        "fp02_capability_row_ref": capability.capability_row_ref,
        "fp02_capability_evidence_hash": canonical_okx_close_sizing_hash(capability),
        "fp02_capability_state": capability.capability_state,
        "fp02_capability_generation_id": capability.capability_generation_id,
        "fp02_capability_currentness_status": capability.currentness_status,
        "provider_identity_ref": provider.provider_identity_ref,
        "provider_identity_hash": canonical_okx_close_sizing_hash(provider.provider_identity),
        "provider_instrument_id": provider.provider_instrument_id,
        "account_level": provider.account_level,
        "position_mode": provider.position_mode,
        "margin_mode": provider.margin_mode,
        "provider_position_side_ref": provider.provider_position_side_ref,
        "provider_position_snapshot_ref": provider.provider_position_snapshot_ref,
        "provider_position_snapshot_hash": canonical_okx_close_sizing_hash(provider.provider_position_snapshot),
        "provider_position_observation_generation_id": provider.provider_position_observation_generation_id,
        "provider_position_observed_at": _utc_text(provider.provider_position_observed_at, "provider_position_observed_at"),
        "provider_position_received_at": _utc_text(provider.provider_position_received_at, "provider_position_received_at"),
        "provider_position_currentness_status": provider.provider_position_currentness_status,
        "provider_reducible_quantity": _decimal_text(provider.provider_reducible_quantity),
        "provider_reducible_quantity_unit": provider.provider_reducible_quantity_unit,
        "provider_normalized_canonical_quantity": format(provider.normalized_canonical_quantity, "f"),
        "fp04_ownership_evidence_ref": fp04.get("ownership_evidence_id"),
        "fp04_ownership_evidence_hash": canonical_evidence_hash(fp04),
        "fp04_ownership_classification": fp04.get("ownership_classification"),
        "fp04_reconciliation_status": fp04.get("reconciliation_status"),
        "fp04_required_dispositions": fp04.get("required_dispositions"),
        "instrument_metadata_ref": metadata.metadata_ref,
        "instrument_metadata_hash": canonical_okx_close_sizing_hash(metadata),
        "instrument_metadata_generation": proof.instrument_metadata_generation,
        "instrument_metadata_observed_at": _utc_text(metadata.observed_at, "instrument_metadata_observed_at"),
        "instrument_metadata_freshness_policy_version": metadata.freshness_policy_version,
        "metadata_applicability_proof_ref": proof.applicability_proof_ref,
        "metadata_applicability_hash": canonical_okx_close_sizing_hash(proof),
        "metadata_applicability_generation_id": proof.applicability_generation_id,
        "metadata_applicability_currentness_status": proof.currentness_status,
        "conversion_profile": proof.conversion_profile,
        "provider_ct_val": format(metadata.ct_val, "f") if checked_metadata is not None else None,
        "provider_ct_mult": format(metadata.ct_mult, "f") if checked_metadata is not None else None,
        "provider_ct_val_ccy": metadata.ct_val_ccy if checked_metadata is not None else None,
        "provider_ct_type": metadata.ct_type if checked_metadata is not None else None,
        "close_step": _decimal_text(proof.close_step) if checked_metadata is not None else None,
        "close_min_size": _decimal_text(proof.close_min_size) if checked_metadata is not None else None,
        "close_max_size": _decimal_text(proof.close_max_size) if checked_metadata is not None else None,
        "raw_provider_close_size": _decimal_text(raw_provider_close_size),
        "quantized_provider_close_size": _decimal_text(quantized_provider_close_size),
        "effective_canonical_close_quantity": _decimal_text(effective_canonical_close_quantity),
        "sizing_state": sizing_state,
        "reason_codes": _sort_reasons(reason_codes),
        "supersedes_sizing_evidence_id": supersedes_id,
        "evaluated_at": _utc_text(value.evaluated_at, "evaluated_at"),
    }
    evidence_id, evidence_hash = _identity(evidence)
    evidence["sizing_evidence_id"] = evidence_id
    evidence["sizing_evidence_hash"] = evidence_hash
    validate_okx_close_residual_sizing_evidence(evidence)
    return evidence


def _outcome_without_sizing(
    value: OKXCloseSizingInput,
    *,
    action_role: str,
    state: str,
    reasons: list[str],
    checked_metadata: OKXInstrumentMetadata | None = None,
    supersedes_id: str | None = None,
) -> dict[str, Any]:
    return _build_evidence(
        value,
        action_role=action_role,
        sizing_state=state,
        reason_codes=reasons,
        raw_provider_close_size=None,
        quantized_provider_close_size=None,
        effective_canonical_close_quantity=None,
        checked_metadata=checked_metadata,
        supersedes_id=supersedes_id,
    )


def evaluate_okx_close_residual_sizing(
    value: OKXCloseSizingInput,
    *,
    supersedes_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate FP-05 from supplied facts only; never performs provider I/O or mutation."""

    if not isinstance(value, OKXCloseSizingInput):
        raise OKXCloseSizingError("INPUT_TYPE_INVALID", "FP-05 requires OKXCloseSizingInput")
    if not isinstance(value.evaluated_at, datetime):
        raise OKXCloseSizingError("INVALID_TIMESTAMP", "evaluated_at must be datetime")
    _utc_text(value.evaluated_at, "evaluated_at")
    action_role = _action_role(value.action)
    current_quantity, current_observed = _current_position_facts(value.current_position)
    _text(value.action.get("position_action_id"), "PositionAction.position_action_id")
    if value.action.get("position_id") != value.current_position.get("position_id"):
        raise OKXCloseSizingError("POSITION_ID_MISMATCH", "action and current Position must share one logical position_id")

    supersedes_id = None
    if supersedes_evidence is not None:
        validate_okx_close_residual_sizing_evidence(supersedes_evidence)
        if (
            supersedes_evidence.get("position_id") != value.current_position.get("position_id")
            or supersedes_evidence.get("action_role") != action_role
        ):
            raise OKXCloseSizingError("SUPERSESSION_LINEAGE_MISMATCH", "superseded evidence must share Position/role lineage")
        supersedes_id = supersedes_evidence["sizing_evidence_id"]

    phase_valid, phase_reason = _validate_phase_authority(value, action_role)
    if not phase_valid:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=[phase_reason or "OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    if value.current_position.get("reconciliation_status") != "CONSISTENT":
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_ACTION_STALE_OR_MISMATCHED"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    if value.prior_close_outcome_status == PRIOR_OUTCOME_AMBIGUOUS:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_PRIOR_OUTCOME_AMBIGUOUS"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    exact_fp04, current_owned = _fp04_status(value)
    if not exact_fp04:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_OWNERSHIP_RECONCILIATION_REQUIRED"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)
    if not current_owned:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=REDUCIBLE_EXPOSURE_UNKNOWN,
            reasons=["OKX_CLOSE_OWNERSHIP_RECONCILIATION_REQUIRED", "OKX_CLOSE_REDUCIBLE_EXPOSURE_UNKNOWN"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    provider = value.provider_exposure
    if provider.provider_position_currentness_status not in _CURRENTNESS or provider.provider_position_currentness_status != CURRENT:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=REDUCIBLE_EXPOSURE_UNKNOWN,
            reasons=["OKX_CLOSE_REDUCIBLE_EXPOSURE_UNKNOWN"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)
    if provider.provider_reducible_quantity is None:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=REDUCIBLE_EXPOSURE_UNKNOWN,
            reasons=["OKX_CLOSE_REDUCIBLE_EXPOSURE_UNKNOWN"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    provider_native_quantity = _decimal(provider.provider_reducible_quantity, "provider_reducible_quantity")
    provider_canonical_quantity = _decimal(provider.normalized_canonical_quantity, "provider_normalized_canonical_quantity")
    if provider_canonical_quantity != current_quantity:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)
    if current_quantity == 0:
        if provider_native_quantity != 0:
            candidate = _outcome_without_sizing(
                value,
                action_role=action_role,
                state=RECONCILIATION_REQUIRED,
                reasons=["OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH"],
                supersedes_id=supersedes_id,
            )
            return _finalize_supersession(candidate, supersedes_evidence)
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=EXPOSURE_ALREADY_FLAT,
            reasons=["OKX_CLOSE_PROVIDER_FLAT_PROVEN"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)
    if provider_native_quantity <= 0:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    if not _capability_is_proven(value, action_role):
        reasons = ["OKX_CLOSE_CAPABILITY_UNPROVEN"]
        if value.capability.provider_position_quantity_unit != provider.provider_reducible_quantity_unit:
            reasons.append("OKX_CLOSE_PROVIDER_POSITION_UNIT_UNPROVEN")
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=CLOSE_CAPABILITY_UNPROVEN,
            reasons=reasons,
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    metadata_ok, metadata_reason, checked = _metadata_status(value, action_role)
    if not metadata_ok or checked is None:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=METADATA_STALE_OR_UNKNOWN,
            reasons=[metadata_reason or "OKX_CLOSE_METADATA_UNKNOWN_OR_STALE"],
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    base_per_contract = checked.ct_val * checked.ct_mult
    if provider_native_quantity * base_per_contract != current_quantity:
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RECONCILIATION_REQUIRED,
            reasons=["OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH"],
            checked_metadata=checked,
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    proof = value.metadata_applicability
    close_step = _decimal(proof.close_step, "close_step", positive=True)
    native_bound_from_canonical = current_quantity / base_per_contract
    native_upper_bound = min(native_bound_from_canonical, provider_native_quantity)
    if proof.close_max_size is not None:
        native_upper_bound = min(native_upper_bound, _decimal(proof.close_max_size, "close_max_size", positive=True))
    raw_provider_close_size = native_upper_bound
    lot_units = (native_upper_bound / close_step).to_integral_value(rounding=ROUND_FLOOR)
    candidate_size = lot_units * close_step

    unrepresentable = candidate_size <= 0
    if proof.close_min_size is not None and candidate_size < proof.close_min_size:
        unrepresentable = True
    if unrepresentable:
        reasons = ["OKX_CLOSE_SIZE_NOT_REPRESENTABLE", "OKX_CLOSE_RESIDUAL_NONZERO_UNREPRESENTABLE"]
        if candidate_size <= 0:
            reasons.append("OKX_CLOSE_SIZE_ZERO_OR_NEGATIVE")
        if value.evaluation_phase == POST_ACTION_RESIDUAL:
            reasons.append("OKX_CLOSE_NEWER_EVIDENCE_REQUIRED")
        candidate = _outcome_without_sizing(
            value,
            action_role=action_role,
            state=RESIDUAL_NONZERO_UNREPRESENTABLE,
            reasons=reasons,
            checked_metadata=checked,
            supersedes_id=supersedes_id,
        )
        return _finalize_supersession(candidate, supersedes_evidence)

    if candidate_size > provider_native_quantity:
        raise OKXCloseSizingError("OKX_CLOSE_SIZE_EXCEEDS_REDUCIBLE_EXPOSURE", "quantized size exceeds provider reducible exposure")
    effective_canonical = candidate_size * base_per_contract
    action_quantity = _decimal(value.action.get("quantity"), "PositionAction.quantity")
    if effective_canonical > current_quantity or effective_canonical > action_quantity:
        raise OKXCloseSizingError("OKX_CLOSE_SIZE_EXCEEDS_CANONICAL_AUTHORITY", "quantized size exceeds canonical authority")
    if candidate_size / close_step != (candidate_size / close_step).to_integral_value():
        raise OKXCloseSizingError("OKX_CLOSE_SIZE_NOT_REPRESENTABLE", "quantized size violates close step")
    if proof.close_max_size is not None and candidate_size > proof.close_max_size:
        raise OKXCloseSizingError("OKX_CLOSE_SIZE_NOT_REPRESENTABLE", "quantized size violates close maximum")

    if value.evaluation_phase == POST_ACTION_RESIDUAL:
        state = RESIDUAL_NONZERO_REPRESENTABLE
        reasons = ["OKX_CLOSE_RESIDUAL_NONZERO_REPRESENTABLE"]
    elif candidate_size == provider_native_quantity and effective_canonical == current_quantity:
        state = FULLY_REDUCIBLE
        reasons = ["OKX_CLOSE_FULLY_REDUCIBLE"]
    else:
        state = PARTIALLY_REDUCIBLE
        reasons = ["OKX_CLOSE_PARTIALLY_REDUCIBLE"]

    candidate = _build_evidence(
        value,
        action_role=action_role,
        sizing_state=state,
        reason_codes=reasons,
        raw_provider_close_size=raw_provider_close_size,
        quantized_provider_close_size=candidate_size,
        effective_canonical_close_quantity=effective_canonical,
        checked_metadata=checked,
        supersedes_id=supersedes_id,
    )
    return _finalize_supersession(candidate, supersedes_evidence)


def _finalize_supersession(
    candidate: dict[str, Any],
    supersedes_evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if supersedes_evidence is None:
        return candidate
    old_material = _material_without_identity(supersedes_evidence, ignore_evaluated_at=True)
    new_material = _material_without_identity(candidate, ignore_evaluated_at=True)
    old_material.pop("supersedes_sizing_evidence_id", None)
    new_material.pop("supersedes_sizing_evidence_id", None)
    if old_material == new_material:
        raise OKXCloseSizingError(
            "SUPERSESSION_REQUIRES_MATERIAL_CHANGE",
            "evaluated_at alone cannot create a new immutable FP-05 evidence object",
        )
    return candidate


def validate_okx_close_residual_sizing_evidence(evidence: Mapping[str, Any]) -> None:
    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        raise OKXCloseSizingError("EVIDENCE_FIELDS_INVALID", "FP-05 evidence fields mismatch")
    if evidence.get("close_residual_sizing_profile_version") != CLOSE_RESIDUAL_SIZING_PROFILE_VERSION:
        raise OKXCloseSizingError("OKX_CLOSE_SIZING_PROFILE_UNSUPPORTED", "FP-05 profile unsupported")
    evidence_id = evidence.get("sizing_evidence_id")
    evidence_hash = evidence.get("sizing_evidence_hash")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None:
        raise OKXCloseSizingError("EVIDENCE_ID_INVALID", "sizing_evidence_id invalid")
    _hash(evidence_hash, "sizing_evidence_hash")
    expected_id, expected_hash = _identity(evidence)
    if evidence_id != expected_id or evidence_hash != expected_hash:
        raise OKXCloseSizingError("EVIDENCE_IDENTITY_MISMATCH", "FP-05 evidence identity/hash mismatch")
    if evidence.get("evaluation_phase") not in _PHASES:
        raise OKXCloseSizingError("EVALUATION_PHASE_INVALID", "evidence phase unsupported")
    if evidence.get("action_role") not in {POSITION_EXIT_ROLE, EMERGENCY_EXIT_ROLE}:
        raise OKXCloseSizingError("OKX_CLOSE_ROLE_UNSUPPORTED", "evidence role unsupported")
    if evidence.get("sizing_state") not in _STATES:
        raise OKXCloseSizingError("SIZING_STATE_INVALID", "evidence sizing state unsupported")
    if evidence.get("prior_close_outcome_status") not in _PRIOR_OUTCOMES:
        raise OKXCloseSizingError("PRIOR_OUTCOME_STATUS_INVALID", "evidence prior outcome unsupported")
    reasons = evidence.get("reason_codes")
    if not isinstance(reasons, list) or not reasons or reasons != _sort_reasons(reasons):
        raise OKXCloseSizingError("REASON_ORDER_INVALID", "reason codes must be deterministic and unique")
    _utc_text(evidence.get("canonical_position_observed_at"), "canonical_position_observed_at")
    _utc_text(evidence.get("provider_position_observed_at"), "provider_position_observed_at")
    _utc_text(evidence.get("provider_position_received_at"), "provider_position_received_at")
    _utc_text(evidence.get("instrument_metadata_observed_at"), "instrument_metadata_observed_at")
    _utc_text(evidence.get("evaluated_at"), "evaluated_at")
    if _utc_dt(evidence["provider_position_received_at"], "provider_position_received_at") < _utc_dt(
        evidence["provider_position_observed_at"], "provider_position_observed_at"
    ):
        raise OKXCloseSizingError("TEMPORAL_ORDER_INVALID", "provider receipt precedes observation")

    state = evidence["sizing_state"]
    raw = evidence.get("raw_provider_close_size")
    quantized = evidence.get("quantized_provider_close_size")
    effective = evidence.get("effective_canonical_close_quantity")
    sizing_states = {FULLY_REDUCIBLE, PARTIALLY_REDUCIBLE, RESIDUAL_NONZERO_REPRESENTABLE}
    if state in sizing_states:
        if raw is None or quantized is None or effective is None:
            raise OKXCloseSizingError("SIZING_VALUES_REQUIRED", "representable state requires sizing values")
        native = _decimal(quantized, "quantized_provider_close_size", positive=True)
        reducible = _decimal(evidence.get("provider_reducible_quantity"), "provider_reducible_quantity", positive=True)
        current = _decimal(evidence.get("current_canonical_quantity"), "current_canonical_quantity", positive=True)
        authorized = _decimal(evidence.get("canonical_authorized_close_quantity"), "canonical_authorized_close_quantity", positive=True)
        effective_decimal = _decimal(effective, "effective_canonical_close_quantity", positive=True)
        if native > reducible:
            raise OKXCloseSizingError("OKX_CLOSE_SIZE_EXCEEDS_REDUCIBLE_EXPOSURE", "evidence exceeds reducible exposure")
        if effective_decimal > current or effective_decimal > authorized:
            raise OKXCloseSizingError("OKX_CLOSE_SIZE_EXCEEDS_CANONICAL_AUTHORITY", "evidence exceeds canonical authority")
    else:
        if raw is not None or quantized is not None or effective is not None:
            raise OKXCloseSizingError("FALSE_SIZING_VALUES", "nonrepresentable/blocked state cannot carry request sizing")
    if state == EXPOSURE_ALREADY_FLAT:
        if _decimal(evidence.get("current_canonical_quantity"), "current_canonical_quantity") != 0:
            raise OKXCloseSizingError("FALSE_FLAT", "flat evidence requires exact zero canonical exposure")
        if _decimal(evidence.get("provider_reducible_quantity"), "provider_reducible_quantity") != 0:
            raise OKXCloseSizingError("FALSE_FLAT", "flat evidence requires exact zero provider exposure")
    if state == RESIDUAL_NONZERO_UNREPRESENTABLE:
        if _decimal(evidence.get("current_canonical_quantity"), "current_canonical_quantity", positive=True) <= 0:
            raise OKXCloseSizingError("FALSE_RESIDUAL", "unrepresentable residual requires positive exposure")


def okx_close_residual_sizing_evidence_is_current(
    evidence: Mapping[str, Any],
    current_input: OKXCloseSizingInput,
) -> bool:
    """Material currentness check; timestamp-only re-evaluation cannot refresh authority."""

    try:
        validate_okx_close_residual_sizing_evidence(evidence)
        fresh = evaluate_okx_close_residual_sizing(current_input)
    except (OKXCloseSizingError, CloseAuthorityError, ExternalCloseEvidenceError):
        return False
    ignored = {"sizing_evidence_id", "sizing_evidence_hash", "evaluated_at", "supersedes_sizing_evidence_id"}
    return all(evidence.get(field) == value for field, value in fresh.items() if field not in ignored)
