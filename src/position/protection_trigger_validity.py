from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping

from .lifecycle_projection import (
    POSITION_LIFECYCLE_PROJECTION_PROFILE_VERSION,
    LifecycleProjectionError,
    validate_position_lifecycle_projection,
)
from .protection import ProtectionActionError, validate_protection_action

SCHEMA_VERSION = "contracts-v0.1"
PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION = "protection-trigger-validity-v0.1"
PROTECTION_PROFILE_VERSION = "protection-v0.1"
PROTECTION_ACTION = "PROTECT"
PROTECTION_OPERATION_CREATE = "CREATE"
PROTECTION_OPERATION_REPLACE = "REPLACE"
PROTECTION_STOP_ORDER_ROLE = "PROTECTION_STOP"
TRIGGER_REFERENCE_LAST_PRICE = "LAST_PRICE"

BROKER_POSITION_OBSERVATION = "BROKER_POSITION_OBSERVATION"
LIFECYCLE_PROJECTION = "LIFECYCLE_PROJECTION"

FRESH = "FRESH"
STALE = "STALE"
UNKNOWN = "UNKNOWN"
ACTIONABLE = "ACTIONABLE"
FAIL_CLOSED = "FAIL_CLOSED"

HANDOFF_NONE = "NONE"
HANDOFF_REFRESH_MARKET = "REFRESH_MARKET_EVIDENCE_REQUIRED"
HANDOFF_POSITION_RECONCILIATION = "POSITION_RECONCILIATION_REQUIRED"
HANDOFF_POLICY_REEVALUATION = "E5_PROTECTION_POLICY_REEVALUATION_REQUIRED"

PROTECTION_TRIGGER_ACTIONABLE = "PROTECTION_TRIGGER_ACTIONABLE"
TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED = "TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED"
TRIGGER_REFERENCE_PRICE_UNKNOWN = "TRIGGER_REFERENCE_PRICE_UNKNOWN"
MARKET_EVIDENCE_UNKNOWN = "MARKET_EVIDENCE_UNKNOWN"
MARKET_EVIDENCE_STALE = "MARKET_EVIDENCE_STALE"
POSITION_AUTHORITY_MISMATCH = "POSITION_AUTHORITY_MISMATCH"
POSITION_AUTHORITY_STALE = "POSITION_AUTHORITY_STALE"
TEMPORAL_ORDER_INVALID = "TEMPORAL_ORDER_INVALID"
TRIGGER_SIDE_OR_GEOMETRY_INVALID = "TRIGGER_SIDE_OR_GEOMETRY_INVALID"
TRIGGER_ALREADY_BREACHED = "TRIGGER_ALREADY_BREACHED"

_FAILURE_REASON_ORDER = (
    TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED,
    TRIGGER_REFERENCE_PRICE_UNKNOWN,
    MARKET_EVIDENCE_UNKNOWN,
    MARKET_EVIDENCE_STALE,
    POSITION_AUTHORITY_MISMATCH,
    POSITION_AUTHORITY_STALE,
    TEMPORAL_ORDER_INVALID,
    TRIGGER_SIDE_OR_GEOMETRY_INVALID,
    TRIGGER_ALREADY_BREACHED,
)
_REASON_ORDER_INDEX = {code: index for index, code in enumerate(_FAILURE_REASON_ORDER)}

_REQUIRED_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "protection_trigger_validity_profile_version",
        "protection_trigger_validity_id",
        "position_action_id",
        "position_id",
        "position_side",
        "position_authority_type",
        "position_authority_ref",
        "position_observed_at",
        "position_reconciliation_status",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "protection_operation",
        "order_role",
        "stop_level",
        "market_snapshot_ref",
        "market_symbol",
        "market_source",
        "market_observed_at",
        "market_received_at",
        "market_health_status",
        "market_freshness_classification",
        "market_freshness_ms",
        "trigger_reference_semantic",
        "trigger_reference_price",
        "evaluated_at",
        "validity_status",
        "reason_codes",
        "handoff_category",
    }
)

_ID_RE = re.compile(r"^prottrigval_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


class ProtectionTriggerValidityError(ValueError):
    """Structural failure at the E5 FP-03 producer boundary."""

    def __init__(self, code: str, message: str, *, handoff_category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.handoff_category = handoff_category


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProtectionTriggerValidityError(
            TEMPORAL_ORDER_INVALID,
            f"{field} must be an explicit timezone-aware UTC datetime",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ProtectionTriggerValidityError(
            TEMPORAL_ORDER_INVALID,
            f"{field} must be UTC",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    return value.astimezone(timezone.utc)


def _timestamp_text(value: Any, field: str, *, failure_code: str, handoff: str) -> tuple[str, datetime]:
    if isinstance(value, datetime):
        parsed = _utc_datetime(value, field)
        return _fmt_utc(parsed), parsed
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be RFC3339 UTC ending in Z",
            handoff_category=handoff,
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be valid RFC3339 UTC",
            handoff_category=handoff,
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be UTC",
            handoff_category=handoff,
        )
    return value, parsed.astimezone(timezone.utc)


def _text(value: Any, field: str, *, failure_code: str, handoff: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be a canonical non-empty string",
            handoff_category=handoff,
        )
    return value


def _positive_decimal_text(value: Any, field: str, *, failure_code: str, handoff: str) -> tuple[str, Decimal]:
    if isinstance(value, Decimal):
        parsed = value
        text = format(value, "f")
    elif isinstance(value, str) and _DECIMAL_RE.fullmatch(value) is not None:
        text = value
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ProtectionTriggerValidityError(
                failure_code,
                f"{field} is not a valid decimal",
                handoff_category=handoff,
            ) from exc
    else:
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be a canonical base-10 decimal string or Decimal",
            handoff_category=handoff,
        )
    if not parsed.is_finite() or parsed <= 0:
        raise ProtectionTriggerValidityError(
            failure_code,
            f"{field} must be finite and > 0",
            handoff_category=handoff,
        )
    return text, parsed


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not canonical")
        return format(value, "f")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("non-UTC datetime is not canonical")
        return _fmt_utc(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _canonicalize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("canonical mapping keys must be strings")
            normalized[key] = _canonicalize(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise ValueError(f"unsupported canonical value type: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonicalize(value), sort_keys=True, separators=(",", ":"))


def _sha256_ref(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def stable_protection_trigger_validity_id(evidence: Mapping[str, Any]) -> str:
    """Return the contract-defined prottrigval_ identity over the payload except its ID."""

    if not isinstance(evidence, Mapping):
        raise TypeError("evidence must be a mapping")
    material = dict(evidence)
    material.pop("protection_trigger_validity_id", None)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "prottrigval_" + digest


def _position_binding(position: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(position, Mapping):
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "Position authority must be a canonical mapping",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    position_id = _text(
        position.get("position_id"),
        "Position.position_id",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    symbol = _text(
        position.get("symbol"),
        "Position.symbol",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    side = position.get("side")
    if side not in {"LONG", "SHORT"}:
        raise ProtectionTriggerValidityError(
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
            "Position.side must be LONG or SHORT",
            handoff_category=HANDOFF_POLICY_REEVALUATION,
        )
    observed_text, observed_at = _timestamp_text(
        position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    reconciliation_status = _text(
        position.get("reconciliation_status"),
        "Position.reconciliation_status",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )

    profile = position.get("position_lifecycle_projection_profile_version")
    if profile is None:
        authority_type = BROKER_POSITION_OBSERVATION
        authority_ref = _sha256_ref(position)
        lifecycle_projection_id = None
        lifecycle_revision = None
    else:
        if profile != POSITION_LIFECYCLE_PROJECTION_PROFILE_VERSION:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "unsupported Position lifecycle projection profile",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        try:
            projection_facts = validate_position_lifecycle_projection(position)
        except LifecycleProjectionError as exc:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "Position lifecycle authority is invalid",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            ) from exc
        authority_type = LIFECYCLE_PROJECTION
        authority_ref = projection_facts["projection_id"]
        lifecycle_projection_id = projection_facts["projection_id"]
        lifecycle_revision = projection_facts["revision"]

    return {
        "position_id": position_id,
        "symbol": symbol,
        "side": side,
        "observed_text": observed_text,
        "observed_at": observed_at,
        "reconciliation_status": reconciliation_status,
        "authority_type": authority_type,
        "authority_ref": authority_ref,
        "lifecycle_projection_id": lifecycle_projection_id,
        "lifecycle_revision": lifecycle_revision,
    }


def _market_payload(snapshot: Any) -> dict[str, Any]:
    to_interchange = getattr(snapshot, "to_interchange_dict", None)
    if callable(to_interchange):
        payload = to_interchange()
    elif isinstance(snapshot, Mapping):
        payload = dict(snapshot)
    elif is_dataclass(snapshot) and not isinstance(snapshot, type):
        payload = {item.name: getattr(snapshot, item.name) for item in fields(snapshot)}
    else:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot must expose canonical normalized facts",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    try:
        normalized = _canonicalize(payload)
    except (TypeError, ValueError) as exc:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot contains non-canonical values",
            handoff_category=HANDOFF_REFRESH_MARKET,
        ) from exc
    if not isinstance(normalized, dict):
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot canonical payload must be an object",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    return normalized


def _market_binding(snapshot: Any, freshness_classification: Any) -> tuple[dict[str, Any], set[str]]:
    payload = _market_payload(snapshot)
    reasons: set[str] = set()

    schema_version = payload.get("schema_version")
    symbol = payload.get("symbol")
    source = payload.get("source")
    health_status = payload.get("health_status")
    if schema_version != SCHEMA_VERSION:
        reasons.add(MARKET_EVIDENCE_UNKNOWN)
    if not isinstance(symbol, str) or not symbol:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot.symbol must be present",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    if not isinstance(source, str) or not source:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot.source must be present",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    if not isinstance(health_status, str) or not health_status:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "MarketSnapshot.health_status must be present",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )

    observed_text, observed_at = _timestamp_text(
        payload.get("observed_at"),
        "MarketSnapshot.observed_at",
        failure_code=MARKET_EVIDENCE_UNKNOWN,
        handoff=HANDOFF_REFRESH_MARKET,
    )
    received_text, received_at = _timestamp_text(
        payload.get("received_at"),
        "MarketSnapshot.received_at",
        failure_code=MARKET_EVIDENCE_UNKNOWN,
        handoff=HANDOFF_REFRESH_MARKET,
    )

    classification = freshness_classification
    if classification not in {FRESH, STALE, UNKNOWN}:
        classification = UNKNOWN
        reasons.add(MARKET_EVIDENCE_UNKNOWN)
    if health_status != "HEALTHY":
        reasons.add(MARKET_EVIDENCE_UNKNOWN)
    if classification == STALE:
        reasons.add(MARKET_EVIDENCE_STALE)
    elif classification == UNKNOWN:
        reasons.add(MARKET_EVIDENCE_UNKNOWN)

    freshness_ms = payload.get("freshness_ms")
    if freshness_ms is not None and (type(freshness_ms) is not int or freshness_ms < 0):
        freshness_ms = None
        reasons.add(MARKET_EVIDENCE_UNKNOWN)

    trigger_price_text: str | None
    trigger_price: Decimal | None
    try:
        trigger_price_text, trigger_price = _positive_decimal_text(
            payload.get("last_price"),
            "MarketSnapshot.last_price",
            failure_code=TRIGGER_REFERENCE_PRICE_UNKNOWN,
            handoff=HANDOFF_REFRESH_MARKET,
        )
    except ProtectionTriggerValidityError:
        trigger_price_text = None
        trigger_price = None
        reasons.add(TRIGGER_REFERENCE_PRICE_UNKNOWN)

    return (
        {
            "snapshot_ref": _sha256_ref(payload),
            "symbol": symbol,
            "source": source,
            "observed_text": observed_text,
            "observed_at": observed_at,
            "received_text": received_text,
            "received_at": received_at,
            "health_status": health_status,
            "freshness_classification": classification,
            "freshness_ms": freshness_ms,
            "trigger_price_text": trigger_price_text,
            "trigger_price": trigger_price,
        },
        reasons,
    )


def _action_facts(action: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(action, Mapping):
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "PositionAction must be a canonical mapping",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    action_id = _text(
        action.get("position_action_id"),
        "PositionAction.position_action_id",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    position_id = _text(
        action.get("position_id"),
        "PositionAction.position_id",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    symbol = _text(
        action.get("symbol"),
        "PositionAction.symbol",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    side = action.get("position_side")
    observed_text, observed_at = _timestamp_text(
        action.get("position_observed_at"),
        "PositionAction.position_observed_at",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    created_text, created_at = _timestamp_text(
        action.get("created_at"),
        "PositionAction.created_at",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    expires_text, expires_at = _timestamp_text(
        action.get("expires_at"),
        "PositionAction.expires_at",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    reconciliation_status = action.get("position_reconciliation_status")
    instruction = action.get("protection_instruction")
    if not isinstance(instruction, Mapping):
        raise ProtectionTriggerValidityError(
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
            "PositionAction.protection_instruction is required",
            handoff_category=HANDOFF_POLICY_REEVALUATION,
        )
    stop_text, stop_level = _positive_decimal_text(
        instruction.get("stop_level"),
        "PositionAction.protection_instruction.stop_level",
        failure_code=TRIGGER_SIDE_OR_GEOMETRY_INVALID,
        handoff=HANDOFF_POLICY_REEVALUATION,
    )
    return {
        "action_id": action_id,
        "position_id": position_id,
        "symbol": symbol,
        "side": side,
        "observed_text": observed_text,
        "observed_at": observed_at,
        "created_text": created_text,
        "created_at": created_at,
        "expires_text": expires_text,
        "expires_at": expires_at,
        "reconciliation_status": reconciliation_status,
        "stop_text": stop_text,
        "stop_level": stop_level,
        "profile": action.get("protection_profile_version"),
        "action": action.get("action"),
    }


def _handoff_for_reasons(reasons: list[str]) -> str:
    reason_set = set(reasons)
    if reason_set & {POSITION_AUTHORITY_MISMATCH, POSITION_AUTHORITY_STALE}:
        return HANDOFF_POSITION_RECONCILIATION
    if reason_set & {
        TRIGGER_REFERENCE_PRICE_UNKNOWN,
        MARKET_EVIDENCE_UNKNOWN,
        MARKET_EVIDENCE_STALE,
        TEMPORAL_ORDER_INVALID,
    }:
        return HANDOFF_REFRESH_MARKET
    return HANDOFF_POLICY_REEVALUATION


def _ordered_failure_reasons(reasons: set[str]) -> list[str]:
    return [code for code in _FAILURE_REASON_ORDER if code in reasons]


def build_protection_trigger_validity_evidence(
    position_authority: Mapping[str, Any],
    protection_action: Mapping[str, Any],
    parent_plan: Mapping[str, Any],
    market_snapshot: Any,
    *,
    market_freshness_classification: str,
    evaluated_at: datetime,
    trigger_reference_semantic: str = TRIGGER_REFERENCE_LAST_PRICE,
    protection_operation: str = PROTECTION_OPERATION_CREATE,
) -> dict[str, Any]:
    """Build canonical E5 protection-trigger-validity-v0.1 evidence.

    This function is pure and provider-neutral. It does not submit, replace,
    cancel or verify a protective order and it does not select a lifecycle
    transition. E1 remains authoritative for market freshness classification.
    """

    evaluated = _utc_datetime(evaluated_at, "evaluated_at")
    position = _position_binding(position_authority)
    action = _action_facts(protection_action)
    market, reasons = _market_binding(market_snapshot, market_freshness_classification)
    reasons = set(reasons)

    if trigger_reference_semantic != TRIGGER_REFERENCE_LAST_PRICE:
        reasons.add(TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED)

    if protection_operation not in {PROTECTION_OPERATION_CREATE, PROTECTION_OPERATION_REPLACE}:
        raise ProtectionTriggerValidityError(
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
            "protection_operation must be CREATE or REPLACE",
            handoff_category=HANDOFF_POLICY_REEVALUATION,
        )
    if protection_operation == PROTECTION_OPERATION_REPLACE:
        # Baseline MODIFY_PROTECTION is deliberately not executable. The
        # shared validity profile can carry REPLACE only for a future approved
        # executable modification profile, which is outside this task.
        reasons.add(TRIGGER_SIDE_OR_GEOMETRY_INVALID)

    if action["profile"] != PROTECTION_PROFILE_VERSION or action["action"] != PROTECTION_ACTION:
        reasons.add(POSITION_AUTHORITY_MISMATCH)

    side_exact = action["side"] in {"LONG", "SHORT"} and position["side"] == action["side"]
    symbol_exact = position["symbol"] == action["symbol"] == market["symbol"]
    if not side_exact or not symbol_exact:
        reasons.add(TRIGGER_SIDE_OR_GEOMETRY_INVALID)
    if action["position_id"] != position["position_id"]:
        reasons.add(POSITION_AUTHORITY_MISMATCH)
    if action["side"] != position["side"] or action["symbol"] != position["symbol"]:
        reasons.add(POSITION_AUTHORITY_MISMATCH)
    if (
        action["reconciliation_status"] != position["reconciliation_status"]
        or position["reconciliation_status"] != "CONSISTENT"
    ):
        reasons.add(POSITION_AUTHORITY_MISMATCH)

    if action["observed_text"] != position["observed_text"]:
        if position["observed_at"] > action["observed_at"]:
            reasons.add(POSITION_AUTHORITY_STALE)
        else:
            reasons.add(POSITION_AUTHORITY_MISMATCH)
    if action["created_at"] < position["observed_at"]:
        reasons.add(POSITION_AUTHORITY_MISMATCH)
    if action["expires_at"] <= action["created_at"]:
        reasons.add(POSITION_AUTHORITY_MISMATCH)
    if evaluated >= action["expires_at"]:
        reasons.add(POSITION_AUTHORITY_STALE)

    if not reasons.intersection({POSITION_AUTHORITY_MISMATCH, POSITION_AUTHORITY_STALE}):
        try:
            validate_protection_action(
                protection_action,
                position_authority,
                parent_plan,
                now=evaluated,
            )
        except ProtectionActionError as exc:
            if exc.code == "POSITION_ACTION_EXPIRED":
                reasons.add(POSITION_AUTHORITY_STALE)
            else:
                reasons.add(POSITION_AUTHORITY_MISMATCH)

    if (
        evaluated < market["received_at"]
        or evaluated < position["observed_at"]
        or evaluated < action["created_at"]
    ):
        reasons.add(TEMPORAL_ORDER_INVALID)

    market_exact = not reasons.intersection(
        {
            TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED,
            TRIGGER_REFERENCE_PRICE_UNKNOWN,
            MARKET_EVIDENCE_UNKNOWN,
            MARKET_EVIDENCE_STALE,
            POSITION_AUTHORITY_MISMATCH,
            POSITION_AUTHORITY_STALE,
            TEMPORAL_ORDER_INVALID,
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
        }
    )
    if market_exact and market["trigger_price"] is not None:
        if position["side"] == "LONG":
            if action["stop_level"] >= market["trigger_price"]:
                reasons.add(TRIGGER_ALREADY_BREACHED)
        elif position["side"] == "SHORT":
            if action["stop_level"] <= market["trigger_price"]:
                reasons.add(TRIGGER_ALREADY_BREACHED)
        else:
            reasons.add(TRIGGER_SIDE_OR_GEOMETRY_INVALID)

    failure_reasons = _ordered_failure_reasons(reasons)
    validity_status = ACTIONABLE if not failure_reasons else FAIL_CLOSED
    reason_codes = [PROTECTION_TRIGGER_ACTIONABLE] if validity_status == ACTIONABLE else failure_reasons
    handoff_category = HANDOFF_NONE if validity_status == ACTIONABLE else _handoff_for_reasons(failure_reasons)

    evidence: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "protection_trigger_validity_profile_version": PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION,
        "position_action_id": action["action_id"],
        "position_id": position["position_id"],
        "position_side": position["side"],
        "position_authority_type": position["authority_type"],
        "position_authority_ref": position["authority_ref"],
        "position_observed_at": position["observed_text"],
        "position_reconciliation_status": position["reconciliation_status"],
        "lifecycle_projection_id": position["lifecycle_projection_id"],
        "lifecycle_revision": position["lifecycle_revision"],
        "protection_operation": protection_operation,
        "order_role": PROTECTION_STOP_ORDER_ROLE,
        "stop_level": action["stop_text"],
        "market_snapshot_ref": market["snapshot_ref"],
        "market_symbol": market["symbol"],
        "market_source": market["source"],
        "market_observed_at": market["observed_text"],
        "market_received_at": market["received_text"],
        "market_health_status": market["health_status"],
        "market_freshness_classification": market["freshness_classification"],
        "market_freshness_ms": market["freshness_ms"],
        "trigger_reference_semantic": trigger_reference_semantic,
        "trigger_reference_price": market["trigger_price_text"],
        "evaluated_at": _fmt_utc(evaluated),
        "validity_status": validity_status,
        "reason_codes": reason_codes,
        "handoff_category": handoff_category,
    }
    evidence["protection_trigger_validity_id"] = stable_protection_trigger_validity_id(evidence)
    validate_protection_trigger_validity_evidence(evidence)
    return evidence


def validate_protection_trigger_validity_evidence(evidence: Mapping[str, Any]) -> None:
    """Validate the immutable shared evidence shape and deterministic identity."""

    if not isinstance(evidence, Mapping):
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "ProtectionTriggerValidityEvidence must be a mapping",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    if set(evidence.keys()) != _REQUIRED_EVIDENCE_FIELDS:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "ProtectionTriggerValidityEvidence fields do not match the accepted profile",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "unsupported evidence schema_version",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    if evidence.get("protection_trigger_validity_profile_version") != PROTECTION_TRIGGER_VALIDITY_PROFILE_VERSION:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "unsupported trigger-validity profile",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    evidence_id = evidence.get("protection_trigger_validity_id")
    if not isinstance(evidence_id, str) or _ID_RE.fullmatch(evidence_id) is None:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "invalid protection_trigger_validity_id",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    if evidence_id != stable_protection_trigger_validity_id(evidence):
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "protection_trigger_validity_id does not match the immutable payload",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    for field in (
        "position_action_id",
        "position_id",
        "position_authority_ref",
        "market_snapshot_ref",
        "market_symbol",
        "market_source",
        "market_health_status",
    ):
        _text(
            evidence.get(field),
            field,
            failure_code=POSITION_AUTHORITY_MISMATCH,
            handoff=HANDOFF_POSITION_RECONCILIATION,
        )
    if evidence.get("position_side") not in {"LONG", "SHORT"}:
        raise ProtectionTriggerValidityError(
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
            "position_side must be LONG or SHORT",
            handoff_category=HANDOFF_POLICY_REEVALUATION,
        )
    if evidence.get("position_authority_type") not in {BROKER_POSITION_OBSERVATION, LIFECYCLE_PROJECTION}:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "position_authority_type is unsupported",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )
    if evidence.get("position_authority_type") == LIFECYCLE_PROJECTION:
        if evidence.get("lifecycle_projection_id") != evidence.get("position_authority_ref"):
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "lifecycle projection reference mismatch",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        revision = evidence.get("lifecycle_revision")
        if type(revision) is not int or revision < 0:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "lifecycle_revision must be a non-negative integer",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
    elif evidence.get("lifecycle_projection_id") is not None or evidence.get("lifecycle_revision") is not None:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "broker Position authority cannot carry lifecycle projection identity",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    if evidence.get("protection_operation") not in {PROTECTION_OPERATION_CREATE, PROTECTION_OPERATION_REPLACE}:
        raise ProtectionTriggerValidityError(
            TRIGGER_SIDE_OR_GEOMETRY_INVALID,
            "unsupported protection_operation",
            handoff_category=HANDOFF_POLICY_REEVALUATION,
        )
    if evidence.get("order_role") != PROTECTION_STOP_ORDER_ROLE:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "order_role must be PROTECTION_STOP",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    _, stop_level = _positive_decimal_text(
        evidence.get("stop_level"),
        "stop_level",
        failure_code=TRIGGER_SIDE_OR_GEOMETRY_INVALID,
        handoff=HANDOFF_POLICY_REEVALUATION,
    )
    _, position_observed_at = _timestamp_text(
        evidence.get("position_observed_at"),
        "position_observed_at",
        failure_code=POSITION_AUTHORITY_MISMATCH,
        handoff=HANDOFF_POSITION_RECONCILIATION,
    )
    _, market_observed_at = _timestamp_text(
        evidence.get("market_observed_at"),
        "market_observed_at",
        failure_code=MARKET_EVIDENCE_UNKNOWN,
        handoff=HANDOFF_REFRESH_MARKET,
    )
    _, market_received_at = _timestamp_text(
        evidence.get("market_received_at"),
        "market_received_at",
        failure_code=MARKET_EVIDENCE_UNKNOWN,
        handoff=HANDOFF_REFRESH_MARKET,
    )
    _, evaluated_at = _timestamp_text(
        evidence.get("evaluated_at"),
        "evaluated_at",
        failure_code=TEMPORAL_ORDER_INVALID,
        handoff=HANDOFF_REFRESH_MARKET,
    )
    if market_observed_at.tzinfo is None:
        raise AssertionError("unreachable")

    classification = evidence.get("market_freshness_classification")
    if classification not in {FRESH, STALE, UNKNOWN}:
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "market_freshness_classification is unsupported",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )
    freshness_ms = evidence.get("market_freshness_ms")
    if freshness_ms is not None and (type(freshness_ms) is not int or freshness_ms < 0):
        raise ProtectionTriggerValidityError(
            MARKET_EVIDENCE_UNKNOWN,
            "market_freshness_ms must be null or a non-negative integer",
            handoff_category=HANDOFF_REFRESH_MARKET,
        )

    reference_price: Decimal | None = None
    if evidence.get("trigger_reference_price") is not None:
        _, reference_price = _positive_decimal_text(
            evidence.get("trigger_reference_price"),
            "trigger_reference_price",
            failure_code=TRIGGER_REFERENCE_PRICE_UNKNOWN,
            handoff=HANDOFF_REFRESH_MARKET,
        )

    validity_status = evidence.get("validity_status")
    reason_codes = evidence.get("reason_codes")
    if not isinstance(reason_codes, list) or not reason_codes:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "reason_codes must be a non-empty deterministic array",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )

    if validity_status == ACTIONABLE:
        if reason_codes != [PROTECTION_TRIGGER_ACTIONABLE] or evidence.get("handoff_category") != HANDOFF_NONE:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "ACTIONABLE evidence must carry only PROTECTION_TRIGGER_ACTIONABLE/NONE",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        if evidence.get("trigger_reference_semantic") != TRIGGER_REFERENCE_LAST_PRICE:
            raise ProtectionTriggerValidityError(
                TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED,
                "ACTIONABLE evidence requires LAST_PRICE",
                handoff_category=HANDOFF_POLICY_REEVALUATION,
            )
        if reference_price is None:
            raise ProtectionTriggerValidityError(
                TRIGGER_REFERENCE_PRICE_UNKNOWN,
                "ACTIONABLE evidence requires trigger_reference_price",
                handoff_category=HANDOFF_REFRESH_MARKET,
            )
        if evidence.get("market_health_status") != "HEALTHY" or classification != FRESH:
            raise ProtectionTriggerValidityError(
                MARKET_EVIDENCE_UNKNOWN,
                "ACTIONABLE evidence requires healthy/fresh market truth",
                handoff_category=HANDOFF_REFRESH_MARKET,
            )
        if evidence.get("position_reconciliation_status") != "CONSISTENT":
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "ACTIONABLE evidence requires CONSISTENT Position truth",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        if evaluated_at < market_received_at or evaluated_at < position_observed_at:
            raise ProtectionTriggerValidityError(
                TEMPORAL_ORDER_INVALID,
                "ACTIONABLE evidence cannot predate required evidence boundaries",
                handoff_category=HANDOFF_REFRESH_MARKET,
            )
        if evidence.get("position_side") == "LONG" and not stop_level < reference_price:
            raise ProtectionTriggerValidityError(
                TRIGGER_ALREADY_BREACHED,
                "ACTIONABLE LONG evidence requires stop < LAST_PRICE",
                handoff_category=HANDOFF_POLICY_REEVALUATION,
            )
        if evidence.get("position_side") == "SHORT" and not stop_level > reference_price:
            raise ProtectionTriggerValidityError(
                TRIGGER_ALREADY_BREACHED,
                "ACTIONABLE SHORT evidence requires stop > LAST_PRICE",
                handoff_category=HANDOFF_POLICY_REEVALUATION,
            )
    elif validity_status == FAIL_CLOSED:
        if PROTECTION_TRIGGER_ACTIONABLE in reason_codes:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "FAIL_CLOSED evidence cannot carry PROTECTION_TRIGGER_ACTIONABLE",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        if any(code not in _REASON_ORDER_INDEX for code in reason_codes):
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "FAIL_CLOSED reason code is outside the accepted profile vocabulary",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        expected_order = sorted(set(reason_codes), key=_REASON_ORDER_INDEX.__getitem__)
        if reason_codes != expected_order:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "FAIL_CLOSED reason_codes are not in deterministic profile order",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        expected_handoff = _handoff_for_reasons(reason_codes)
        if evidence.get("handoff_category") != expected_handoff:
            raise ProtectionTriggerValidityError(
                POSITION_AUTHORITY_MISMATCH,
                "FAIL_CLOSED handoff category does not match deterministic precedence",
                handoff_category=HANDOFF_POSITION_RECONCILIATION,
            )
        if TRIGGER_REFERENCE_PRICE_UNKNOWN in reason_codes and reference_price is not None:
            raise ProtectionTriggerValidityError(
                TRIGGER_REFERENCE_PRICE_UNKNOWN,
                "TRIGGER_REFERENCE_PRICE_UNKNOWN conflicts with a usable reference price",
                handoff_category=HANDOFF_REFRESH_MARKET,
            )
    else:
        raise ProtectionTriggerValidityError(
            POSITION_AUTHORITY_MISMATCH,
            "validity_status must be ACTIONABLE or FAIL_CLOSED",
            handoff_category=HANDOFF_POSITION_RECONCILIATION,
        )


def protection_trigger_validity_is_actionable(evidence: Mapping[str, Any]) -> bool:
    """Return true only for structurally valid ACTIONABLE evidence."""

    validate_protection_trigger_validity_evidence(evidence)
    return evidence["validity_status"] == ACTIONABLE


def protection_trigger_validity_evidence_is_current(
    evidence: Mapping[str, Any],
    position_authority: Mapping[str, Any],
    protection_action: Mapping[str, Any],
    market_snapshot: Any,
    *,
    market_freshness_classification: str,
    trigger_reference_semantic: str = TRIGGER_REFERENCE_LAST_PRICE,
    protection_operation: str = PROTECTION_OPERATION_CREATE,
) -> bool:
    """Compare immutable evidence with the materially current authority inputs.

    `evaluated_at` is deliberately not part of this currentness comparison: a
    later clock value alone is not new market/Position/action evidence and must
    not make unchanged breached evidence retryable.
    """

    try:
        validate_protection_trigger_validity_evidence(evidence)
        position = _position_binding(position_authority)
        action = _action_facts(protection_action)
        market, _ = _market_binding(market_snapshot, market_freshness_classification)
    except (ProtectionTriggerValidityError, TypeError, ValueError):
        return False

    material = {
        "position_action_id": action["action_id"],
        "position_id": position["position_id"],
        "position_side": position["side"],
        "position_authority_type": position["authority_type"],
        "position_authority_ref": position["authority_ref"],
        "position_observed_at": position["observed_text"],
        "position_reconciliation_status": position["reconciliation_status"],
        "lifecycle_projection_id": position["lifecycle_projection_id"],
        "lifecycle_revision": position["lifecycle_revision"],
        "protection_operation": protection_operation,
        "order_role": PROTECTION_STOP_ORDER_ROLE,
        "stop_level": action["stop_text"],
        "market_snapshot_ref": market["snapshot_ref"],
        "market_symbol": market["symbol"],
        "market_source": market["source"],
        "market_observed_at": market["observed_text"],
        "market_received_at": market["received_text"],
        "market_health_status": market["health_status"],
        "market_freshness_classification": market["freshness_classification"],
        "market_freshness_ms": market["freshness_ms"],
        "trigger_reference_semantic": trigger_reference_semantic,
        "trigger_reference_price": market["trigger_price_text"],
    }
    return all(evidence.get(key) == value for key, value in material.items())
