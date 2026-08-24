from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

from .lifecycle_projection import (
    build_position_lifecycle_genesis,
    build_position_lifecycle_reattestation,
    build_position_lifecycle_transition,
    validate_position_lifecycle_projection,
)

SCHEMA_VERSION = "contracts-v0.1"
LIFECYCLE_EXECUTION_BINDING_PROFILE_VERSION = "position-lifecycle-execution-binding-v0.1"
EXECUTION_SCOPE = "POSITION_LINKED_REDUCTION_ORDERS_V0_1"
POSITION_ACTION_AUTHORIZATION = "POSITION_ACTION"
IN_SCOPE_ORDER_ROLES = frozenset({"PROTECTION_STOP", "POSITION_EXIT", "EMERGENCY_EXIT"})

_ORDER_STATUSES = frozenset(
    {
        "PENDING",
        "OPEN",
        "PARTIALLY_FILLED",
        "FILLED",
        "CANCELED",
        "REJECTED",
        "EXPIRED",
        "UNKNOWN",
        "RECONCILIATION_REQUIRED",
    }
)
_EXECUTION_HEALTH_STATUSES = frozenset({"HEALTHY", "DEGRADED", "UNKNOWN"})
_SIDES = frozenset({"BUY", "SELL"})
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BINDING_ID_RE = re.compile(r"^posexecbind_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_ORDER_REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "order_request_id",
        "trade_plan_id",
        "client_order_id",
        "symbol",
        "side",
        "order_type",
        "quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "created_at",
        "authorization_type",
        "position_action_id",
        "position_id",
        "risk_decision_id",
        "order_role",
        "limit_price",
        "stop_price",
        "reduce_only",
        "time_in_force",
    }
)
_ORDER_REQUEST_REQUIRED = frozenset(
    {
        "schema_version",
        "order_request_id",
        "trade_plan_id",
        "client_order_id",
        "symbol",
        "side",
        "order_type",
        "quantity",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
        "created_at",
    }
)
_POSITION_ACTION_REQUEST_REQUIRED = frozenset(
    {
        "authorization_type",
        "position_action_id",
        "position_id",
        "risk_decision_id",
        "order_role",
    }
)
_ORDER_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "order_request_id",
        "client_order_id",
        "broker_order_id",
        "order_status",
        "observed_at",
        "execution_health_status",
        "requested_quantity",
        "filled_quantity",
        "average_fill_price",
        "reject_reason",
    }
)
_ORDER_RESULT_REQUIRED = frozenset(
    {
        "schema_version",
        "order_request_id",
        "client_order_id",
        "order_status",
        "observed_at",
        "execution_health_status",
        "requested_quantity",
        "filled_quantity",
    }
)
_FILL_FIELDS = frozenset(
    {
        "schema_version",
        "fill_id",
        "broker_order_id",
        "client_order_id",
        "trade_plan_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "filled_at",
        "fee",
        "fee_currency",
        "liquidity_role",
        "position_action_id",
        "position_id",
        "order_role",
    }
)
_FILL_REQUIRED = frozenset(
    {
        "schema_version",
        "fill_id",
        "broker_order_id",
        "client_order_id",
        "trade_plan_id",
        "symbol",
        "side",
        "quantity",
        "price",
        "filled_at",
    }
)
_IN_SCOPE_FILL_REQUIRED = frozenset({"position_action_id", "position_id", "order_role"})
_BINDING_FIELDS = frozenset(
    {
        "schema_version",
        "lifecycle_execution_binding_profile_version",
        "lifecycle_execution_binding_id",
        "position_id",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "execution_interpreted_at",
        "execution_scope",
        "order_evidence",
        "execution_snapshot_hash",
    }
)
_ORDER_EVIDENCE_FIELDS = frozenset(
    {
        "order_request_id",
        "order_role",
        "order_request_payload_hash",
        "order_result_observation_count",
        "order_result_observation_set_hash",
        "latest_order_result_observed_at",
        "fill_count",
        "fill_set_hash",
        "latest_fill_at",
    }
)


class LifecycleExecutionBindingError(ValueError):
    """Fail-closed validation error for position-lifecycle-execution-binding-v0.1."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LifecycleProjectionExecutionBindingOutcome:
    """E5-internal composition outcome; the serialized objects remain separate."""

    lifecycle_projection: dict[str, Any]
    execution_binding: dict[str, Any]


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonicalize(value: Any, field: str = "value") -> Any:
    if isinstance(value, Enum):
        return _canonicalize(value.value, field)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must be finite")
        text = format(value, "f")
        if value == 0 and text.startswith("-"):
            raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must not encode negative zero")
        return text
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise LifecycleExecutionBindingError("NONCANONICAL_TIMESTAMP", f"{field} must be timezone-aware UTC")
        return _fmt_utc(value)
    if isinstance(value, float):
        raise LifecycleExecutionBindingError(
            "BINARY_FLOAT_FORBIDDEN",
            f"{field} cannot use binary floating-point in canonical execution evidence",
        )
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _canonicalize(getattr(value, item.name), f"{field}.{item.name}")
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise LifecycleExecutionBindingError("NONCANONICAL_KEY", f"{field} mapping keys must be strings")
            normalized[key] = _canonicalize(item, f"{field}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item, f"{field}[]") for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise LifecycleExecutionBindingError(
        "NONCANONICAL_VALUE",
        f"{field} contains unsupported canonical value type {type(value).__name__}",
    )


def _canonical_json(value: Any) -> str:
    normalized = _canonicalize(value)
    try:
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise LifecycleExecutionBindingError("NONCANONICAL_JSON", "evidence is not canonical JSON") from exc


def _sha256_json(value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return "sha256:" + digest


def _binding_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("lifecycle_execution_binding_id", None)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "posexecbind_" + digest


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise LifecycleExecutionBindingError("INVALID_TEXT_FIELD", f"{field} must be a canonical non-empty string")
    return value


def _canonical_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LifecycleExecutionBindingError("NONCANONICAL_TIMESTAMP", f"{field} must be RFC3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LifecycleExecutionBindingError("NONCANONICAL_TIMESTAMP", f"{field} is not valid RFC3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LifecycleExecutionBindingError("NONCANONICAL_TIMESTAMP", f"{field} must be UTC")
    parsed = parsed.astimezone(timezone.utc)
    if _fmt_utc(parsed) != value:
        raise LifecycleExecutionBindingError("NONCANONICAL_TIMESTAMP", f"{field} is not in canonical UTC Z form")
    return parsed


def _decimal_text(value: Any, field: str, *, allow_negative: bool = False) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must be a base-10 decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} is invalid") from exc
    if not parsed.is_finite():
        raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must be finite")
    if parsed == 0 and value.startswith("-"):
        raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must not encode negative zero")
    if not allow_negative and parsed < 0:
        raise LifecycleExecutionBindingError("NONCANONICAL_DECIMAL", f"{field} must be non-negative")
    return parsed


def _normalize_object(
    value: Any,
    *,
    kind: str,
    allowed_fields: frozenset[str],
    required_fields: frozenset[str],
) -> dict[str, Any]:
    normalized = _canonicalize(value, kind)
    if not isinstance(normalized, dict):
        raise LifecycleExecutionBindingError("INVALID_EVIDENCE_OBJECT", f"{kind} must serialize to an object")
    unknown = sorted(set(normalized) - allowed_fields)
    if unknown:
        raise LifecycleExecutionBindingError(
            "UNSUPPORTED_EVIDENCE_FIELDS",
            f"{kind} contains unsupported fields: {', '.join(unknown)}",
        )
    missing = sorted(required_fields - set(normalized))
    if missing:
        raise LifecycleExecutionBindingError(
            "INCOMPLETE_EVIDENCE_OBJECT",
            f"{kind} is missing required fields: {', '.join(missing)}",
        )
    if normalized.get("schema_version") != SCHEMA_VERSION:
        raise LifecycleExecutionBindingError("UNSUPPORTED_SCHEMA_VERSION", f"{kind} schema_version is unsupported")
    return normalized


def _normalize_request(value: Any) -> dict[str, Any]:
    request = _normalize_object(
        value,
        kind="OrderRequest",
        allowed_fields=_ORDER_REQUEST_FIELDS,
        required_fields=_ORDER_REQUEST_REQUIRED,
    )
    for field in ("order_request_id", "trade_plan_id", "client_order_id", "symbol", "order_type", "quantity_profile_version", "quantity_unit", "quantity_asset"):
        _text(request.get(field), f"OrderRequest.{field}")
    if request.get("side") not in _SIDES:
        raise LifecycleExecutionBindingError("INVALID_ORDER_REQUEST_SIDE", "OrderRequest.side is unsupported")
    _decimal_text(request.get("quantity"), "OrderRequest.quantity")
    _canonical_utc(request.get("created_at"), "OrderRequest.created_at")
    for field in ("limit_price", "stop_price"):
        if request.get(field) is not None:
            _decimal_text(request[field], f"OrderRequest.{field}")
    return request


def _request_scope(request: Mapping[str, Any], position_id: str) -> bool:
    role = request.get("order_role")
    authorization = request.get("authorization_type")
    request_position_id = request.get("position_id")
    action_id = request.get("position_action_id")

    clean_entry = authorization is None and request_position_id is None and role is None and action_id is None
    if clean_entry:
        return False

    if authorization != POSITION_ACTION_AUTHORIZATION:
        raise LifecycleExecutionBindingError(
            "ORDER_REQUEST_AUTHORIZATION_MISMATCH",
            "position-linked reduction evidence requires authorization_type=POSITION_ACTION",
        )
    if role not in IN_SCOPE_ORDER_ROLES:
        raise LifecycleExecutionBindingError(
            "ORDER_REQUEST_ROLE_OUT_OF_SCOPE",
            "PositionAction request role is not in the V0.1 reduction-order scope",
        )
    missing = sorted(_POSITION_ACTION_REQUEST_REQUIRED - set(request))
    if missing:
        raise LifecycleExecutionBindingError(
            "INCOMPLETE_POSITION_ACTION_REQUEST",
            "PositionAction OrderRequest missing fields: " + ", ".join(missing),
        )
    if request_position_id != position_id:
        raise LifecycleExecutionBindingError(
            "ORDER_REQUEST_POSITION_MISMATCH",
            "PositionAction OrderRequest.position_id does not match lifecycle projection",
        )
    _text(action_id, "OrderRequest.position_action_id")
    _text(request.get("risk_decision_id"), "OrderRequest.risk_decision_id")
    return True


def _normalize_result(value: Any) -> dict[str, Any]:
    result = _normalize_object(
        value,
        kind="OrderResult",
        allowed_fields=_ORDER_RESULT_FIELDS,
        required_fields=_ORDER_RESULT_REQUIRED,
    )
    _text(result.get("order_request_id"), "OrderResult.order_request_id")
    _text(result.get("client_order_id"), "OrderResult.client_order_id")
    if result.get("broker_order_id") is not None:
        _text(result.get("broker_order_id"), "OrderResult.broker_order_id")
    if result.get("order_status") not in _ORDER_STATUSES:
        raise LifecycleExecutionBindingError("INVALID_ORDER_STATUS", "OrderResult.order_status is unsupported")
    if result.get("execution_health_status") not in _EXECUTION_HEALTH_STATUSES:
        raise LifecycleExecutionBindingError("INVALID_EXECUTION_HEALTH", "OrderResult.execution_health_status is unsupported")
    _canonical_utc(result.get("observed_at"), "OrderResult.observed_at")
    requested = _decimal_text(result.get("requested_quantity"), "OrderResult.requested_quantity")
    filled = _decimal_text(result.get("filled_quantity"), "OrderResult.filled_quantity")
    if filled > requested:
        raise LifecycleExecutionBindingError("FILLED_QUANTITY_INVALID", "OrderResult.filled_quantity exceeds requested_quantity")
    if result.get("average_fill_price") is not None:
        _decimal_text(result.get("average_fill_price"), "OrderResult.average_fill_price")
    return result


def _normalize_fill(value: Any) -> dict[str, Any]:
    fill = _normalize_object(
        value,
        kind="Fill",
        allowed_fields=_FILL_FIELDS,
        required_fields=_FILL_REQUIRED,
    )
    for field in ("fill_id", "broker_order_id", "client_order_id", "trade_plan_id", "symbol"):
        _text(fill.get(field), f"Fill.{field}")
    if fill.get("side") not in _SIDES:
        raise LifecycleExecutionBindingError("INVALID_FILL_SIDE", "Fill.side is unsupported")
    if _decimal_text(fill.get("quantity"), "Fill.quantity") <= 0:
        raise LifecycleExecutionBindingError("INVALID_FILL_QUANTITY", "Fill.quantity must be positive")
    if _decimal_text(fill.get("price"), "Fill.price") <= 0:
        raise LifecycleExecutionBindingError("INVALID_FILL_PRICE", "Fill.price must be positive")
    _canonical_utc(fill.get("filled_at"), "Fill.filled_at")
    if fill.get("fee") is not None:
        _decimal_text(fill.get("fee"), "Fill.fee", allow_negative=True)
    return fill


def _build_request_registry(
    order_requests: Sequence[Any],
    *,
    position_id: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_client_id: dict[str, dict[str, Any]] = {}
    in_scope: set[str] = set()

    for raw in order_requests:
        request = _normalize_request(raw)
        request_id = request["order_request_id"]
        client_id = request["client_order_id"]
        existing = by_id.get(request_id)
        if existing is not None:
            if existing != request:
                raise LifecycleExecutionBindingError(
                    "ORDER_REQUEST_IDENTITY_CONFLICT",
                    "same order_request_id has changed canonical payload",
                )
            continue
        existing_client = by_client_id.get(client_id)
        if existing_client is not None and existing_client["order_request_id"] != request_id:
            raise LifecycleExecutionBindingError(
                "CLIENT_ORDER_IDENTITY_CONFLICT",
                "same client_order_id maps to different OrderRequest identities",
            )
        by_id[request_id] = request
        by_client_id[client_id] = request
        if _request_scope(request, position_id):
            in_scope.add(request_id)
    return by_id, by_client_id, in_scope


def _collect_result_pairs(
    order_results: Sequence[Any],
    *,
    requests_by_id: Mapping[str, Mapping[str, Any]],
    in_scope_request_ids: set[str],
) -> dict[str, list[list[str]]]:
    grouped: dict[str, dict[str, str]] = {request_id: {} for request_id in in_scope_request_ids}
    for raw in order_results:
        result = _normalize_result(raw)
        request_id = result["order_request_id"]
        request = requests_by_id.get(request_id)
        if request is None:
            raise LifecycleExecutionBindingError(
                "ORDER_RESULT_REQUEST_UNKNOWN",
                "OrderResult references an OrderRequest not supplied to the interpreted evidence set",
            )
        if result["client_order_id"] != request["client_order_id"]:
            raise LifecycleExecutionBindingError(
                "ORDER_RESULT_CLIENT_ID_MISMATCH",
                "OrderResult.client_order_id does not match its OrderRequest",
            )
        if request_id not in in_scope_request_ids:
            continue
        observed_at = result["observed_at"]
        payload_hash = _sha256_json(result)
        existing_hash = grouped[request_id].get(observed_at)
        if existing_hash is not None and existing_hash != payload_hash:
            raise LifecycleExecutionBindingError(
                "ORDER_RESULT_EQUAL_TIME_CONFLICT",
                "same order_request_id/observed_at has changed canonical OrderResult payload",
            )
        grouped[request_id][observed_at] = payload_hash

    return {
        request_id: [
            [observed_at, payload_hash]
            for observed_at, payload_hash in sorted(
                values.items(),
                key=lambda item: (_canonical_utc(item[0], "OrderResult.observed_at"), item[1]),
            )
        ]
        for request_id, values in grouped.items()
    }


def _fill_has_position_markers(fill: Mapping[str, Any]) -> bool:
    return any(fill.get(field) is not None for field in ("position_action_id", "position_id", "order_role"))


def _collect_fill_tuples(
    fills: Sequence[Any],
    *,
    requests_by_client_id: Mapping[str, Mapping[str, Any]],
    in_scope_request_ids: set[str],
) -> dict[str, list[list[str]]]:
    grouped: dict[str, dict[str, tuple[dict[str, Any], str]]] = {
        request_id: {} for request_id in in_scope_request_ids
    }
    global_fill_ids: dict[str, str] = {}

    for raw in fills:
        fill = _normalize_fill(raw)
        request = requests_by_client_id.get(fill["client_order_id"])
        if request is None:
            if _fill_has_position_markers(fill):
                raise LifecycleExecutionBindingError(
                    "FILL_REQUEST_UNKNOWN",
                    "position-linked Fill does not map to a supplied OrderRequest",
                )
            continue
        request_id = request["order_request_id"]
        if request_id not in in_scope_request_ids:
            continue

        missing = sorted(_IN_SCOPE_FILL_REQUIRED - set(fill))
        if missing:
            raise LifecycleExecutionBindingError(
                "INCOMPLETE_POSITION_FILL",
                "position-linked Fill missing fields: " + ", ".join(missing),
            )
        lineage_pairs = (
            ("position_id", "position_id"),
            ("position_action_id", "position_action_id"),
            ("order_role", "order_role"),
            ("trade_plan_id", "trade_plan_id"),
            ("symbol", "symbol"),
            ("side", "side"),
        )
        for fill_field, request_field in lineage_pairs:
            if fill.get(fill_field) != request.get(request_field):
                raise LifecycleExecutionBindingError(
                    "FILL_LINEAGE_MISMATCH",
                    f"Fill.{fill_field} does not match its in-scope OrderRequest",
                )

        payload_hash = _sha256_json(fill)
        fill_id = fill["fill_id"]
        previous_hash = global_fill_ids.get(fill_id)
        if previous_hash is not None and previous_hash != payload_hash:
            raise LifecycleExecutionBindingError(
                "FILL_IDENTITY_CONFLICT",
                "same fill_id has changed canonical payload",
            )
        global_fill_ids[fill_id] = payload_hash
        existing = grouped[request_id].get(fill_id)
        if existing is not None:
            if existing[1] != payload_hash:
                raise LifecycleExecutionBindingError(
                    "FILL_IDENTITY_CONFLICT",
                    "same fill_id has changed canonical payload",
                )
            continue
        grouped[request_id][fill_id] = (fill, payload_hash)

    result: dict[str, list[list[str]]] = {}
    for request_id, values in grouped.items():
        ordered = sorted(
            values.values(),
            key=lambda item: (
                _canonical_utc(item[0]["filled_at"], "Fill.filled_at"),
                item[0]["fill_id"],
            ),
        )
        result[request_id] = [
            [fill["fill_id"], fill["filled_at"], payload_hash]
            for fill, payload_hash in ordered
        ]
    return result


def build_position_lifecycle_execution_evidence_binding(
    lifecycle_projection: Mapping[str, Any],
    *,
    order_requests: Sequence[Any],
    order_results: Sequence[Any],
    fills: Sequence[Any],
) -> dict[str, Any]:
    """Emit one immutable canonical execution-evidence companion for one E5 projection."""

    projection_facts = validate_position_lifecycle_projection(lifecycle_projection)
    position_id = _text(lifecycle_projection.get("position_id"), "Position.position_id")
    requests_by_id, requests_by_client_id, in_scope_request_ids = _build_request_registry(
        order_requests,
        position_id=position_id,
    )
    result_pairs = _collect_result_pairs(
        order_results,
        requests_by_id=requests_by_id,
        in_scope_request_ids=in_scope_request_ids,
    )
    fill_tuples = _collect_fill_tuples(
        fills,
        requests_by_client_id=requests_by_client_id,
        in_scope_request_ids=in_scope_request_ids,
    )

    order_evidence: list[dict[str, Any]] = []
    for request_id in sorted(in_scope_request_ids):
        request = requests_by_id[request_id]
        observations = result_pairs[request_id]
        request_fills = fill_tuples[request_id]
        entry = {
            "order_request_id": request_id,
            "order_role": request["order_role"],
            "order_request_payload_hash": _sha256_json(request),
            "order_result_observation_count": len(observations),
            "order_result_observation_set_hash": _sha256_json(observations),
            "latest_order_result_observed_at": observations[-1][0] if observations else None,
            "fill_count": len(request_fills),
            "fill_set_hash": _sha256_json(request_fills),
            "latest_fill_at": request_fills[-1][1] if request_fills else None,
        }
        order_evidence.append(entry)

    snapshot_material = {
        "execution_scope": EXECUTION_SCOPE,
        "position_id": position_id,
        "order_evidence": order_evidence,
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "lifecycle_execution_binding_profile_version": LIFECYCLE_EXECUTION_BINDING_PROFILE_VERSION,
        "position_id": position_id,
        "lifecycle_projection_id": projection_facts["projection_id"],
        "lifecycle_revision": projection_facts["revision"],
        "execution_interpreted_at": lifecycle_projection["lifecycle_interpreted_at"],
        "execution_scope": EXECUTION_SCOPE,
        "order_evidence": order_evidence,
        "execution_snapshot_hash": _sha256_json(snapshot_material),
    }
    payload["lifecycle_execution_binding_id"] = _binding_id(payload)
    validate_position_lifecycle_execution_evidence_binding(payload, lifecycle_projection)
    return payload


def validate_position_lifecycle_execution_evidence_binding(
    binding: Mapping[str, Any],
    lifecycle_projection: Mapping[str, Any],
) -> None:
    """Validate the self-contained companion shape, projection binding and identities."""

    projection_facts = validate_position_lifecycle_projection(lifecycle_projection)
    normalized = _canonicalize(binding, "PositionLifecycleExecutionEvidenceBinding")
    if not isinstance(normalized, dict):
        raise LifecycleExecutionBindingError("INVALID_BINDING", "binding must serialize to an object")
    unknown = sorted(set(normalized) - _BINDING_FIELDS)
    missing = sorted(_BINDING_FIELDS - set(normalized))
    if unknown or missing:
        raise LifecycleExecutionBindingError(
            "INVALID_BINDING_FIELDS",
            f"binding fields mismatch; missing={missing}, unknown={unknown}",
        )
    if normalized["schema_version"] != SCHEMA_VERSION:
        raise LifecycleExecutionBindingError("UNSUPPORTED_SCHEMA_VERSION", "binding schema_version is unsupported")
    if normalized["lifecycle_execution_binding_profile_version"] != LIFECYCLE_EXECUTION_BINDING_PROFILE_VERSION:
        raise LifecycleExecutionBindingError("UNSUPPORTED_BINDING_PROFILE", "binding profile is unsupported")
    if normalized["execution_scope"] != EXECUTION_SCOPE:
        raise LifecycleExecutionBindingError("UNSUPPORTED_EXECUTION_SCOPE", "binding execution_scope is unsupported")
    if normalized["position_id"] != lifecycle_projection.get("position_id"):
        raise LifecycleExecutionBindingError("BINDING_POSITION_MISMATCH", "binding position_id does not match projection")
    if normalized["lifecycle_projection_id"] != projection_facts["projection_id"]:
        raise LifecycleExecutionBindingError("BINDING_PROJECTION_ID_MISMATCH", "binding lifecycle_projection_id mismatch")
    if normalized["lifecycle_revision"] != projection_facts["revision"]:
        raise LifecycleExecutionBindingError("BINDING_REVISION_MISMATCH", "binding lifecycle_revision mismatch")
    if normalized["execution_interpreted_at"] != lifecycle_projection.get("lifecycle_interpreted_at"):
        raise LifecycleExecutionBindingError("BINDING_INTERPRETATION_TIME_MISMATCH", "execution_interpreted_at must equal lifecycle_interpreted_at")
    _canonical_utc(normalized["execution_interpreted_at"], "binding.execution_interpreted_at")

    if not isinstance(normalized["order_evidence"], list):
        raise LifecycleExecutionBindingError("INVALID_ORDER_EVIDENCE", "order_evidence must be an array")
    previous_request_id: str | None = None
    for entry in normalized["order_evidence"]:
        if not isinstance(entry, dict) or set(entry) != _ORDER_EVIDENCE_FIELDS:
            raise LifecycleExecutionBindingError("INVALID_ORDER_EVIDENCE", "order_evidence entry fields are invalid")
        request_id = _text(entry["order_request_id"], "order_evidence.order_request_id")
        if previous_request_id is not None and request_id <= previous_request_id:
            raise LifecycleExecutionBindingError("ORDER_EVIDENCE_NOT_SORTED", "order_evidence must be strictly sorted by order_request_id")
        previous_request_id = request_id
        if entry["order_role"] not in IN_SCOPE_ORDER_ROLES:
            raise LifecycleExecutionBindingError("INVALID_ORDER_EVIDENCE_ROLE", "order_evidence.order_role is unsupported")
        for field in ("order_request_payload_hash", "order_result_observation_set_hash", "fill_set_hash"):
            if not isinstance(entry[field], str) or _HASH_RE.fullmatch(entry[field]) is None:
                raise LifecycleExecutionBindingError("INVALID_EVIDENCE_HASH", f"{field} must be sha256:<hex>")
        for count_field, latest_field in (
            ("order_result_observation_count", "latest_order_result_observed_at"),
            ("fill_count", "latest_fill_at"),
        ):
            count = entry[count_field]
            if type(count) is not int or count < 0:
                raise LifecycleExecutionBindingError("INVALID_EVIDENCE_COUNT", f"{count_field} must be a non-negative integer")
            latest = entry[latest_field]
            if count == 0:
                if latest is not None:
                    raise LifecycleExecutionBindingError("INVALID_EVIDENCE_LATEST_TIME", f"{latest_field} must be null when count is zero")
            else:
                _canonical_utc(latest, f"order_evidence.{latest_field}")

    snapshot_material = {
        "execution_scope": EXECUTION_SCOPE,
        "position_id": normalized["position_id"],
        "order_evidence": normalized["order_evidence"],
    }
    expected_snapshot_hash = _sha256_json(snapshot_material)
    if normalized["execution_snapshot_hash"] != expected_snapshot_hash:
        raise LifecycleExecutionBindingError("EXECUTION_SNAPSHOT_HASH_MISMATCH", "execution_snapshot_hash is invalid")
    binding_id = normalized["lifecycle_execution_binding_id"]
    if not isinstance(binding_id, str) or _BINDING_ID_RE.fullmatch(binding_id) is None:
        raise LifecycleExecutionBindingError("INVALID_BINDING_ID", "binding ID must be posexecbind_<sha256>")
    if binding_id != _binding_id(normalized):
        raise LifecycleExecutionBindingError("BINDING_ID_MISMATCH", "binding ID does not match complete binding payload")


def build_position_lifecycle_genesis_with_execution_binding(
    source_position: Mapping[str, Any],
    *,
    lifecycle_state: Any,
    lifecycle_interpreted_at: datetime,
    order_requests: Sequence[Any],
    order_results: Sequence[Any],
    fills: Sequence[Any],
) -> LifecycleProjectionExecutionBindingOutcome:
    projection = build_position_lifecycle_genesis(
        source_position,
        lifecycle_state=lifecycle_state,
        lifecycle_interpreted_at=lifecycle_interpreted_at,
    )
    binding = build_position_lifecycle_execution_evidence_binding(
        projection,
        order_requests=order_requests,
        order_results=order_results,
        fills=fills,
    )
    return LifecycleProjectionExecutionBindingOutcome(projection, binding)


def build_position_lifecycle_transition_with_execution_binding(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    lifecycle_event: Any,
    lifecycle_interpreted_at: datetime,
    order_requests: Sequence[Any],
    order_results: Sequence[Any],
    fills: Sequence[Any],
) -> LifecycleProjectionExecutionBindingOutcome:
    projection = build_position_lifecycle_transition(
        source_position,
        previous_projection,
        lifecycle_event=lifecycle_event,
        lifecycle_interpreted_at=lifecycle_interpreted_at,
    )
    binding = build_position_lifecycle_execution_evidence_binding(
        projection,
        order_requests=order_requests,
        order_results=order_results,
        fills=fills,
    )
    return LifecycleProjectionExecutionBindingOutcome(projection, binding)


def build_position_lifecycle_reattestation_with_execution_binding(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    lifecycle_interpreted_at: datetime,
    order_requests: Sequence[Any],
    order_results: Sequence[Any],
    fills: Sequence[Any],
) -> LifecycleProjectionExecutionBindingOutcome:
    projection = build_position_lifecycle_reattestation(
        source_position,
        previous_projection,
        lifecycle_interpreted_at=lifecycle_interpreted_at,
    )
    binding = build_position_lifecycle_execution_evidence_binding(
        projection,
        order_requests=order_requests,
        order_results=order_results,
        fills=fills,
    )
    return LifecycleProjectionExecutionBindingOutcome(projection, binding)
