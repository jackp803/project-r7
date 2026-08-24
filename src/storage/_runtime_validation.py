from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .runtime_models import RuntimeValidationError

SCHEMA_VERSION = "contracts-v0.1"
POSITION_PROFILE = "position-lifecycle-projection-v0.1"
FUNDING_PROFILE = "funding-allocation-v0.1"
TRADE_RESULT_PROFILE = "trade-result-v0.1"

_SECRET_FRAGMENTS = (
    "api_key",
    "apikey",
    "api_secret",
    "secret_key",
    "password",
    "passphrase",
    "private_key",
    "access_token",
    "refresh_token",
    "session_token",
    "credential",
)

_PROFILE_FIELDS = frozenset(
    {
        "position_lifecycle_projection_profile_version",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "previous_lifecycle_projection_id",
        "lifecycle_projection_kind",
        "lifecycle_event",
        "lifecycle_interpreted_at",
        "lifecycle_source_broker_state_observed_at",
    }
)

_FUNDING_IDENTITY_FIELDS = (
    "schema_version",
    "funding_evidence_profile_version",
    "source_kind",
    "source",
    "source_version",
    "source_material_hash",
    "source_record_count",
    "source_complete_through",
    "trade_plan_id",
    "position_id",
    "symbol",
    "interval_start",
    "interval_end",
    "interval_semantics",
    "status",
    "funding_cost",
    "cost_currency",
)

_FUNDING_REQUIRED_FIELDS = frozenset((*_FUNDING_IDENTITY_FIELDS, "funding_evidence_id", "calculated_at"))


def _reject_noncanonical(value: Any, path: str = "payload") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise RuntimeValidationError(
            "BINARY_FLOAT_FORBIDDEN",
            f"{path} contains a binary floating-point value",
        )
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_noncanonical(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise RuntimeValidationError("NON_STRING_JSON_KEY", f"{path} contains a non-string key")
            lowered = key.lower()
            if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
                raise RuntimeValidationError(
                    "SECRET_LIKE_FIELD_FORBIDDEN",
                    f"secret-like field is forbidden at {path}.{key}",
                )
            _reject_noncanonical(item, f"{path}.{key}")
        return
    raise RuntimeValidationError(
        "NONCANONICAL_JSON_VALUE",
        f"{path} contains unsupported serialized value type {type(value).__name__}",
    )


def canonical_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], str, str]:
    if not isinstance(payload, Mapping):
        raise RuntimeValidationError("PAYLOAD_NOT_MAPPING", "canonical payload must be a mapping")
    material = dict(payload)
    _reject_noncanonical(material)
    try:
        payload_json = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeValidationError("PAYLOAD_NOT_CANONICAL_JSON", "payload is not canonical JSON") from exc
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return material, payload_json, "sha256:" + digest


def canonical_hash(material: Mapping[str, Any], *, prefix: str = "sha256:") -> str:
    _, payload_json, _ = canonical_payload(material)
    return prefix + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def nonempty_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise RuntimeValidationError("INVALID_TEXT_FIELD", f"{field} must be a non-empty canonical string")
    return value


def utc_text(payload: Mapping[str, Any], field: str) -> datetime:
    value = payload.get(field)
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be RFC3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be valid RFC3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def decimal_text(payload: Mapping[str, Any], field: str) -> Decimal:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeValidationError("INVALID_DECIMAL", f"{field} must be a base-10 decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise RuntimeValidationError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    if not parsed.is_finite():
        raise RuntimeValidationError("INVALID_DECIMAL", f"{field} must be finite")
    return parsed


def require_schema(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeValidationError("UNSUPPORTED_SCHEMA_VERSION", "schema_version must equal contracts-v0.1")


def immutable_object_metadata(kind: str, payload: Mapping[str, Any]) -> dict[str, str | None]:
    require_schema(payload)
    if kind == "RISK_DECISION":
        canonical_id = nonempty_text(payload, "risk_decision_id")
        strategy_id = nonempty_text(payload, "strategy_id")
        strategy_version = nonempty_text(payload, "strategy_version")
        return {
            "canonical_id": canonical_id,
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "trade_plan_id": None,
            "position_id": None,
            "order_request_id": None,
            "client_order_id": None,
            "broker_order_id": None,
        }
    if kind == "APPROVED_TRADE_PLAN":
        canonical_id = nonempty_text(payload, "trade_plan_id")
        return {
            "canonical_id": canonical_id,
            "strategy_id": nonempty_text(payload, "strategy_id"),
            "strategy_version": nonempty_text(payload, "strategy_version"),
            "trade_plan_id": canonical_id,
            "position_id": None,
            "order_request_id": None,
            "client_order_id": None,
            "broker_order_id": None,
        }
    if kind == "POSITION_ACTION":
        canonical_id = nonempty_text(payload, "position_action_id")
        return {
            "canonical_id": canonical_id,
            "strategy_id": payload.get("strategy_id") if isinstance(payload.get("strategy_id"), str) else None,
            "strategy_version": payload.get("strategy_version") if isinstance(payload.get("strategy_version"), str) else None,
            "trade_plan_id": payload.get("trade_plan_id") if isinstance(payload.get("trade_plan_id"), str) else None,
            "position_id": nonempty_text(payload, "position_id"),
            "order_request_id": None,
            "client_order_id": None,
            "broker_order_id": None,
        }
    if kind == "ORDER_REQUEST":
        canonical_id = nonempty_text(payload, "order_request_id")
        return {
            "canonical_id": canonical_id,
            "strategy_id": None,
            "strategy_version": None,
            "trade_plan_id": nonempty_text(payload, "trade_plan_id"),
            "position_id": payload.get("position_id") if isinstance(payload.get("position_id"), str) else None,
            "order_request_id": canonical_id,
            "client_order_id": nonempty_text(payload, "client_order_id"),
            "broker_order_id": None,
        }
    if kind == "FILL":
        canonical_id = nonempty_text(payload, "fill_id")
        return {
            "canonical_id": canonical_id,
            "strategy_id": None,
            "strategy_version": None,
            "trade_plan_id": nonempty_text(payload, "trade_plan_id"),
            "position_id": payload.get("position_id") if isinstance(payload.get("position_id"), str) else None,
            "order_request_id": None,
            "client_order_id": nonempty_text(payload, "client_order_id"),
            "broker_order_id": nonempty_text(payload, "broker_order_id"),
        }
    raise RuntimeValidationError("UNSUPPORTED_OBJECT_KIND", f"unsupported runtime object kind: {kind}")


def broker_fact_material(position: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in position.items()
        if key not in _PROFILE_FIELDS and key != "lifecycle_state"
    }


def broker_fact_hash(position: Mapping[str, Any]) -> str:
    _, payload_json, _ = canonical_payload(broker_fact_material(position))
    return "sha256:" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def validate_raw_position(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_schema(payload)
    if any(field in payload for field in _PROFILE_FIELDS):
        raise RuntimeValidationError(
            "PROFILED_POSITION_NOT_RAW_OBSERVATION",
            "raw broker Position observation must not contain lifecycle projection metadata",
        )
    position_id = nonempty_text(payload, "position_id")
    nonempty_text(payload, "symbol")
    nonempty_text(payload, "side")
    decimal_text(payload, "actual_quantity")
    decimal_text(payload, "average_entry_price")
    utc_text(payload, "opened_at")
    observed_at = utc_text(payload, "broker_state_observed_at")
    nonempty_text(payload, "reconciliation_status")
    nonempty_text(payload, "lifecycle_state")
    return {
        "position_id": position_id,
        "observed_at": payload["broker_state_observed_at"],
        "broker_fact_hash": broker_fact_hash(payload),
    }


def validate_position_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_schema(payload)
    if payload.get("position_lifecycle_projection_profile_version") != POSITION_PROFILE:
        raise RuntimeValidationError(
            "UNSUPPORTED_POSITION_PROJECTION_PROFILE",
            "restart-authoritative Position requires position-lifecycle-projection-v0.1",
        )
    position_id = nonempty_text(payload, "position_id")
    nonempty_text(payload, "lifecycle_projection_id")
    revision = payload.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise RuntimeValidationError("INVALID_LIFECYCLE_REVISION", "lifecycle_revision must be a non-negative integer")
    kind = payload.get("lifecycle_projection_kind")
    if kind not in {"GENESIS", "TRANSITION", "REATTESTATION"}:
        raise RuntimeValidationError("INVALID_LIFECYCLE_PROJECTION_KIND", "unsupported lifecycle projection kind")
    previous_id = payload.get("previous_lifecycle_projection_id")
    event = payload.get("lifecycle_event")
    if kind == "GENESIS":
        if revision != 0 or previous_id is not None or event is not None:
            raise RuntimeValidationError(
                "INVALID_GENESIS_PROJECTION",
                "GENESIS requires revision 0, null predecessor, and null lifecycle_event",
            )
    else:
        if revision == 0:
            raise RuntimeValidationError("INVALID_LIFECYCLE_REVISION", "non-GENESIS projection requires revision > 0")
        if not isinstance(previous_id, str) or not previous_id:
            raise RuntimeValidationError("PREDECESSOR_REQUIRED", "non-GENESIS projection requires predecessor ID")
        if kind == "TRANSITION":
            if not isinstance(event, str) or not event:
                raise RuntimeValidationError("LIFECYCLE_EVENT_REQUIRED", "TRANSITION requires lifecycle_event")
        elif event is not None:
            raise RuntimeValidationError("REATTESTATION_EVENT_FORBIDDEN", "REATTESTATION requires lifecycle_event=null")
    nonempty_text(payload, "lifecycle_state")
    anchor = utc_text(payload, "broker_state_observed_at")
    source_anchor = utc_text(payload, "lifecycle_source_broker_state_observed_at")
    if source_anchor != anchor or payload.get("lifecycle_source_broker_state_observed_at") != payload.get("broker_state_observed_at"):
        raise RuntimeValidationError("LIFECYCLE_SOURCE_ANCHOR_MISMATCH", "lifecycle source broker anchor must equal Position broker_state_observed_at")
    interpreted = utc_text(payload, "lifecycle_interpreted_at")
    if interpreted < anchor:
        raise RuntimeValidationError("INTERPRETATION_PREDATES_BROKER_OBSERVATION", "lifecycle_interpreted_at cannot predate broker observation")
    decimal_text(payload, "actual_quantity")
    decimal_text(payload, "average_entry_price")
    projection_id = payload["lifecycle_projection_id"]
    material = dict(payload)
    material.pop("lifecycle_projection_id", None)
    _, identity_json, _ = canonical_payload(material)
    expected_id = "posproj_" + hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
    if projection_id != expected_id:
        raise RuntimeValidationError("LIFECYCLE_PROJECTION_ID_MISMATCH", "lifecycle_projection_id does not match canonical payload")
    return {
        "position_id": position_id,
        "projection_id": projection_id,
        "revision": revision,
        "previous_id": previous_id,
        "kind": kind,
        "event": event,
        "lifecycle_state": payload["lifecycle_state"],
        "broker_state_observed_at": payload["broker_state_observed_at"],
        "broker_fact_hash": broker_fact_hash(payload),
    }


def validate_order_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_schema(payload)
    order_request_id = nonempty_text(payload, "order_request_id")
    client_order_id = nonempty_text(payload, "client_order_id")
    observed_at = utc_text(payload, "observed_at")
    nonempty_text(payload, "order_status")
    nonempty_text(payload, "execution_health_status")
    requested = decimal_text(payload, "requested_quantity")
    filled = decimal_text(payload, "filled_quantity")
    if requested < 0 or filled < 0 or filled > requested:
        raise RuntimeValidationError("ORDER_QUANTITY_INVALID", "OrderResult quantities must satisfy 0 <= filled <= requested")
    broker_order_id = payload.get("broker_order_id")
    if broker_order_id is not None and (not isinstance(broker_order_id, str) or not broker_order_id):
        raise RuntimeValidationError("INVALID_BROKER_ORDER_ID", "broker_order_id must be null or non-empty string")
    return {
        "order_request_id": order_request_id,
        "client_order_id": client_order_id,
        "broker_order_id": broker_order_id,
        "observed_at": payload["observed_at"],
        "observed_dt": observed_at,
        "order_status": payload["order_status"],
        "execution_health_status": payload["execution_health_status"],
        "requested_quantity": payload["requested_quantity"],
    }


def validate_funding_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    material, _, _ = canonical_payload(payload)
    missing = sorted(_FUNDING_REQUIRED_FIELDS - set(material))
    extra = sorted(set(material) - _FUNDING_REQUIRED_FIELDS)
    if missing or extra:
        raise RuntimeValidationError(
            "FUNDING_PAYLOAD_SHAPE_INVALID",
            f"FundingAllocationEvidence fields mismatch; missing={missing}, extra={extra}",
        )
    require_schema(material)
    if material.get("funding_evidence_profile_version") != FUNDING_PROFILE:
        raise RuntimeValidationError("UNSUPPORTED_FUNDING_PROFILE", "funding profile must be funding-allocation-v0.1")
    funding_id = nonempty_text(material, "funding_evidence_id")
    nonempty_text(material, "source_kind")
    nonempty_text(material, "source")
    nonempty_text(material, "source_version")
    nonempty_text(material, "source_material_hash")
    trade_plan_id = nonempty_text(material, "trade_plan_id")
    position_id = nonempty_text(material, "position_id")
    symbol = nonempty_text(material, "symbol")
    interval_start = utc_text(material, "interval_start")
    interval_end = utc_text(material, "interval_end")
    if interval_start >= interval_end:
        raise RuntimeValidationError("FUNDING_INTERVAL_INVALID", "funding interval_start must be before interval_end")
    if material.get("interval_semantics") != "START_INCLUSIVE_END_EXCLUSIVE":
        raise RuntimeValidationError("FUNDING_INTERVAL_SEMANTICS_INVALID", "unsupported funding interval semantics")
    complete = utc_text(material, "source_complete_through")
    calculated = utc_text(material, "calculated_at")
    if complete < interval_end or calculated < interval_end:
        raise RuntimeValidationError("FUNDING_EVIDENCE_INCOMPLETE", "funding completeness/calculation must cover interval_end")
    record_count = material.get("source_record_count")
    if type(record_count) is not int or record_count < 0:
        raise RuntimeValidationError("FUNDING_RECORD_COUNT_INVALID", "source_record_count must be a non-negative integer")
    cost = decimal_text(material, "funding_cost")
    if material.get("cost_currency") != "USDT":
        raise RuntimeValidationError("FUNDING_CURRENCY_UNSUPPORTED", "funding cost_currency must be USDT")
    status = material.get("status")
    if status == "ZERO_CONFIRMED":
        if record_count != 0 or cost != 0:
            raise RuntimeValidationError("ZERO_FUNDING_INVARIANT_INVALID", "ZERO_CONFIRMED requires zero records and zero cost")
    elif status == "INCLUDED":
        if record_count < 1:
            raise RuntimeValidationError("INCLUDED_FUNDING_INVARIANT_INVALID", "INCLUDED requires at least one source record")
    else:
        raise RuntimeValidationError("FUNDING_STATUS_INVALID", "funding status must be ZERO_CONFIRMED or INCLUDED")

    identity_material = {field: material[field] for field in _FUNDING_IDENTITY_FIELDS}
    _, identity_json, _ = canonical_payload(identity_material)
    expected_id = "fundev_" + hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
    if funding_id != expected_id:
        raise RuntimeValidationError("FUNDING_EVIDENCE_ID_MISMATCH", "funding_evidence_id does not match canonical identity material")
    identity_hash = "sha256:" + hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
    lineage_material = {
        "funding_evidence_profile_version": material["funding_evidence_profile_version"],
        "trade_plan_id": trade_plan_id,
        "position_id": position_id,
        "symbol": symbol,
        "interval_start": material["interval_start"],
        "interval_end": material["interval_end"],
        "interval_semantics": material["interval_semantics"],
    }
    _, lineage_json, _ = canonical_payload(lineage_material)
    lineage_hash = "sha256:" + hashlib.sha256(lineage_json.encode("utf-8")).hexdigest()
    return {
        "funding_evidence_id": funding_id,
        "trade_plan_id": trade_plan_id,
        "position_id": position_id,
        "symbol": symbol,
        "interval_start": material["interval_start"],
        "interval_end": material["interval_end"],
        "interval_semantics": material["interval_semantics"],
        "identity_material_hash": identity_hash,
        "lineage_key_hash": lineage_hash,
        "calculated_at": material["calculated_at"],
        "status": status,
        "funding_cost": material["funding_cost"],
    }


def validate_trade_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    require_schema(payload)
    if payload.get("trade_result_profile_version") != TRADE_RESULT_PROFILE:
        raise RuntimeValidationError("UNSUPPORTED_TRADE_RESULT_PROFILE", "TradeResult must declare trade-result-v0.1")
    trade_result_id = nonempty_text(payload, "trade_result_id")
    trade_plan_id = nonempty_text(payload, "trade_plan_id")
    position_id = nonempty_text(payload, "position_id")
    strategy_id = nonempty_text(payload, "strategy_id")
    strategy_version = nonempty_text(payload, "strategy_version")
    funding_id = nonempty_text(payload, "funding_evidence_id")
    if payload.get("funding_evidence_profile_version") != FUNDING_PROFILE:
        raise RuntimeValidationError("TRADE_RESULT_FUNDING_PROFILE_INVALID", "TradeResult funding profile reference is invalid")
    opened = utc_text(payload, "opened_at")
    closed = utc_text(payload, "closed_at")
    if opened >= closed:
        raise RuntimeValidationError("TRADE_RESULT_INTERVAL_INVALID", "TradeResult opened_at must be before closed_at")
    nonempty_text(payload, "symbol")
    decimal_text(payload, "entry_quantity")
    decimal_text(payload, "average_entry_price")
    decimal_text(payload, "average_exit_price")
    decimal_text(payload, "gross_pnl")
    decimal_text(payload, "net_pnl")
    decimal_text(payload, "total_fees")
    return {
        "trade_result_id": trade_result_id,
        "trade_plan_id": trade_plan_id,
        "position_id": position_id,
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "funding_evidence_id": funding_id,
        "symbol": payload["symbol"],
        "opened_at": payload["opened_at"],
        "closed_at": payload["closed_at"],
        "funding_evidence_status": payload.get("funding_evidence_status"),
        "funding_cost": payload.get("funding_cost"),
    }
