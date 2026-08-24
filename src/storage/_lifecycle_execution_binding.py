from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Mapping, TYPE_CHECKING

from ._runtime_validation import canonical_payload, validate_position_projection
from .runtime_models import (
    PaperRuntimeRecovery,
    RuntimeConflictError,
    RuntimePersistenceError,
    RuntimeValidationError,
    StoredCanonicalObject,
)

if TYPE_CHECKING:
    from ._paper_runtime import _PaperRuntimeStore

SCHEMA_VERSION = "contracts-v0.1"
BINDING_PROFILE = "position-lifecycle-execution-binding-v0.1"
EXECUTION_SCOPE = "POSITION_LINKED_REDUCTION_ORDERS_V0_1"
POSITION_ACTION_AUTHORIZATION = "POSITION_ACTION"
IN_SCOPE_ORDER_ROLES = frozenset({"PROTECTION_STOP", "POSITION_EXIT", "EMERGENCY_EXIT"})

_BINDING_ID_RE = re.compile(r"^posexecbind_[0-9a-f]{64}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
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
_AUTHORITY_REF_FIELDS = frozenset(
    {"position_action_id", "position_id", "action", "order_role"}
)
_ACTION_ROLE = {
    "EXIT": "POSITION_EXIT",
    "EMERGENCY_EXIT": "EMERGENCY_EXIT",
    "PROTECT": "PROTECTION_STOP",
}


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise RuntimeValidationError(
            "NONCANONICAL_EXECUTION_EVIDENCE",
            "execution evidence is not canonical JSON",
        ) from exc


def _sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _binding_id(payload: Mapping[str, Any]) -> str:
    material = dict(payload)
    material.pop("lifecycle_execution_binding_id", None)
    return "posexecbind_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be canonical RFC3339 UTC Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} is not valid RFC3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeValidationError("INVALID_TIMESTAMP", f"{field} must be UTC")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.isoformat().replace("+00:00", "Z") != value:
        raise RuntimeValidationError("NONCANONICAL_TIMESTAMP", f"{field} is not canonical UTC Z")
    return parsed


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RuntimeValidationError("INVALID_TEXT_FIELD", f"{field} must be a canonical non-empty string")
    return value


def _payload_from_row(row: Any) -> dict[str, Any]:
    value = json.loads(row["payload_json"])
    if not isinstance(value, dict):
        raise RuntimeValidationError("STORED_PAYLOAD_NOT_OBJECT", "stored canonical payload is not an object")
    return value


def _stored(kind: str, canonical_id: str, row: Any) -> StoredCanonicalObject:
    return StoredCanonicalObject(kind, canonical_id, row["payload_json"], row["payload_hash"])


def validate_lifecycle_execution_binding(
    payload: Mapping[str, Any],
    lifecycle_projection: Mapping[str, Any],
) -> dict[str, Any]:
    material, _, _ = canonical_payload(payload)
    missing = sorted(_BINDING_FIELDS - set(material))
    extra = sorted(set(material) - _BINDING_FIELDS)
    if missing or extra:
        raise RuntimeValidationError(
            "LIFECYCLE_EXECUTION_BINDING_FIELDS_INVALID",
            f"binding fields mismatch; missing={missing}, extra={extra}",
        )
    if material.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeValidationError("UNSUPPORTED_SCHEMA_VERSION", "binding schema_version is unsupported")
    if material.get("lifecycle_execution_binding_profile_version") != BINDING_PROFILE:
        raise RuntimeValidationError("UNSUPPORTED_BINDING_PROFILE", "binding profile is unsupported")
    if material.get("execution_scope") != EXECUTION_SCOPE:
        raise RuntimeValidationError("UNSUPPORTED_EXECUTION_SCOPE", "binding execution_scope is unsupported")

    projection_facts = validate_position_projection(lifecycle_projection)
    position_id = _text(material.get("position_id"), "binding.position_id")
    projection_id = _text(material.get("lifecycle_projection_id"), "binding.lifecycle_projection_id")
    revision = material.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise RuntimeValidationError("INVALID_BINDING_REVISION", "binding lifecycle_revision must be a non-negative integer")
    interpreted_at = _text(material.get("execution_interpreted_at"), "binding.execution_interpreted_at")
    _utc(interpreted_at, "binding.execution_interpreted_at")

    if position_id != lifecycle_projection.get("position_id"):
        raise RuntimeValidationError("BINDING_POSITION_MISMATCH", "binding position_id does not match lifecycle projection")
    if projection_id != projection_facts["projection_id"]:
        raise RuntimeValidationError("BINDING_PROJECTION_ID_MISMATCH", "binding lifecycle_projection_id does not match projection")
    if revision != projection_facts["revision"]:
        raise RuntimeValidationError("BINDING_REVISION_MISMATCH", "binding lifecycle_revision does not match projection")
    if interpreted_at != lifecycle_projection.get("lifecycle_interpreted_at"):
        raise RuntimeValidationError(
            "BINDING_INTERPRETATION_TIME_MISMATCH",
            "binding execution_interpreted_at must equal lifecycle_interpreted_at",
        )

    evidence = material.get("order_evidence")
    if not isinstance(evidence, list):
        raise RuntimeValidationError("INVALID_ORDER_EVIDENCE", "binding order_evidence must be an array")
    previous_request_id: str | None = None
    for entry in evidence:
        if not isinstance(entry, dict) or set(entry) != _ORDER_EVIDENCE_FIELDS:
            raise RuntimeValidationError("INVALID_ORDER_EVIDENCE", "binding order_evidence entry fields are invalid")
        request_id = _text(entry.get("order_request_id"), "order_evidence.order_request_id")
        if previous_request_id is not None and request_id <= previous_request_id:
            raise RuntimeValidationError("ORDER_EVIDENCE_NOT_SORTED", "order_evidence must be strictly sorted by order_request_id")
        previous_request_id = request_id
        if entry.get("order_role") not in IN_SCOPE_ORDER_ROLES:
            raise RuntimeValidationError("INVALID_ORDER_EVIDENCE_ROLE", "order_evidence.order_role is outside binding scope")
        for field in (
            "order_request_payload_hash",
            "order_result_observation_set_hash",
            "fill_set_hash",
        ):
            value = entry.get(field)
            if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
                raise RuntimeValidationError("INVALID_EVIDENCE_HASH", f"{field} must be sha256:<lowercase hex>")
        for count_field, latest_field in (
            ("order_result_observation_count", "latest_order_result_observed_at"),
            ("fill_count", "latest_fill_at"),
        ):
            count = entry.get(count_field)
            if type(count) is not int or count < 0:
                raise RuntimeValidationError("INVALID_EVIDENCE_COUNT", f"{count_field} must be a non-negative integer")
            latest = entry.get(latest_field)
            if count == 0:
                if latest is not None:
                    raise RuntimeValidationError("INVALID_EVIDENCE_LATEST_TIME", f"{latest_field} must be null when count is zero")
            else:
                _utc(latest, f"order_evidence.{latest_field}")

    snapshot_material = {
        "execution_scope": EXECUTION_SCOPE,
        "position_id": position_id,
        "order_evidence": evidence,
    }
    expected_snapshot_hash = _sha256_json(snapshot_material)
    snapshot_hash = material.get("execution_snapshot_hash")
    if snapshot_hash != expected_snapshot_hash:
        raise RuntimeValidationError("EXECUTION_SNAPSHOT_HASH_MISMATCH", "binding execution_snapshot_hash is invalid")

    binding_id = material.get("lifecycle_execution_binding_id")
    if not isinstance(binding_id, str) or _BINDING_ID_RE.fullmatch(binding_id) is None:
        raise RuntimeValidationError("INVALID_BINDING_ID", "binding ID must be posexecbind_<sha256>")
    if binding_id != _binding_id(material):
        raise RuntimeValidationError("BINDING_ID_MISMATCH", "binding ID does not match complete canonical payload")
    return {
        "binding_id": binding_id,
        "position_id": position_id,
        "projection_id": projection_id,
        "revision": revision,
        "execution_interpreted_at": interpreted_at,
        "execution_scope": EXECUTION_SCOPE,
        "execution_snapshot_hash": snapshot_hash,
        "order_evidence": evidence,
    }


def _in_scope_requests(store: "_PaperRuntimeStore", position_id: str) -> list[tuple[Any, dict[str, Any]]]:
    rows = store._connection.execute(
        """
        SELECT * FROM paper_runtime_objects
        WHERE object_kind = 'ORDER_REQUEST' AND position_id = ?
        ORDER BY canonical_id
        """,
        (position_id,),
    ).fetchall()
    selected: list[tuple[Any, dict[str, Any]]] = []
    for row in rows:
        payload = _payload_from_row(row)
        if payload.get("position_id") != position_id:
            raise RuntimeConflictError("ORDER_REQUEST_POSITION_INDEX_CONFLICT", "OrderRequest position index mismatches payload")
        authorization = payload.get("authorization_type")
        role = payload.get("order_role")
        if authorization != POSITION_ACTION_AUTHORIZATION or role not in IN_SCOPE_ORDER_ROLES:
            raise RuntimeConflictError(
                "POSITION_LINKED_REQUEST_SCOPE_UNSUPPORTED",
                "position-linked OrderRequest is outside the accepted execution binding scope",
            )
        _text(payload.get("position_action_id"), "OrderRequest.position_action_id")
        _text(payload.get("risk_decision_id"), "OrderRequest.risk_decision_id")
        selected.append((row, payload))
    return selected


def recompute_position_linked_execution_snapshot(
    store: "_PaperRuntimeStore",
    position_id: str,
) -> dict[str, Any]:
    order_evidence: list[dict[str, Any]] = []
    for request_row, request in _in_scope_requests(store, position_id):
        request_id = request["order_request_id"]
        client_order_id = request["client_order_id"]
        request_hash = _sha256_json(request)

        result_rows = store._connection.execute(
            """
            SELECT * FROM paper_order_result_observations
            WHERE order_request_id = ?
            ORDER BY observed_at, payload_hash
            """,
            (request_id,),
        ).fetchall()
        result_by_time: dict[str, str] = {}
        result_times: dict[str, datetime] = {}
        for result_row in result_rows:
            result = _payload_from_row(result_row)
            if result.get("order_request_id") != request_id or result.get("client_order_id") != client_order_id:
                raise RuntimeConflictError("ORDER_RESULT_LINEAGE_CONFLICT", "OrderResult lineage mismatches binding request")
            observed_at = _text(result.get("observed_at"), "OrderResult.observed_at")
            observed_dt = _utc(observed_at, "OrderResult.observed_at")
            payload_hash = _sha256_json(result)
            existing_hash = result_by_time.get(observed_at)
            if existing_hash is not None and existing_hash != payload_hash:
                raise RuntimeConflictError("EQUAL_TIME_ORDER_RESULT_CONFLICT", "equal-time OrderResult payloads conflict")
            result_by_time[observed_at] = payload_hash
            result_times[observed_at] = observed_dt
        observations = [
            [observed_at, result_by_time[observed_at]]
            for observed_at in sorted(result_by_time, key=lambda value: (result_times[value], result_by_time[value]))
        ]

        fill_rows = store._connection.execute(
            """
            SELECT * FROM paper_runtime_objects
            WHERE object_kind = 'FILL' AND client_order_id = ?
            ORDER BY canonical_id
            """,
            (client_order_id,),
        ).fetchall()
        fill_items: list[tuple[datetime, str, str, str]] = []
        seen_fill_ids: dict[str, str] = {}
        for fill_row in fill_rows:
            fill = _payload_from_row(fill_row)
            for fill_field, request_field in (
                ("position_id", "position_id"),
                ("position_action_id", "position_action_id"),
                ("order_role", "order_role"),
                ("trade_plan_id", "trade_plan_id"),
                ("symbol", "symbol"),
                ("side", "side"),
            ):
                if fill.get(fill_field) != request.get(request_field):
                    raise RuntimeConflictError("FILL_LINEAGE_CONFLICT", f"Fill.{fill_field} mismatches binding request")
            fill_id = _text(fill.get("fill_id"), "Fill.fill_id")
            filled_at = _text(fill.get("filled_at"), "Fill.filled_at")
            filled_dt = _utc(filled_at, "Fill.filled_at")
            payload_hash = _sha256_json(fill)
            prior = seen_fill_ids.get(fill_id)
            if prior is not None and prior != payload_hash:
                raise RuntimeConflictError("FILL_IDENTITY_CONFLICT", "same fill_id has changed payload")
            seen_fill_ids[fill_id] = payload_hash
            fill_items.append((filled_dt, fill_id, filled_at, payload_hash))
        fill_items.sort(key=lambda item: (item[0], item[1]))
        fills = [[fill_id, filled_at, payload_hash] for _, fill_id, filled_at, payload_hash in fill_items]

        order_evidence.append(
            {
                "order_request_id": request_id,
                "order_role": request["order_role"],
                "order_request_payload_hash": request_hash,
                "order_result_observation_count": len(observations),
                "order_result_observation_set_hash": _sha256_json(observations),
                "latest_order_result_observed_at": observations[-1][0] if observations else None,
                "fill_count": len(fills),
                "fill_set_hash": _sha256_json(fills),
                "latest_fill_at": fills[-1][1] if fills else None,
            }
        )

    order_evidence.sort(key=lambda entry: entry["order_request_id"])
    material = {
        "execution_scope": EXECUTION_SCOPE,
        "position_id": position_id,
        "order_evidence": order_evidence,
    }
    return {
        **material,
        "execution_snapshot_hash": _sha256_json(material),
    }


def persist_lifecycle_execution_binding(
    store: "_PaperRuntimeStore",
    payload: Mapping[str, Any],
) -> StoredCanonicalObject:
    material, payload_json, payload_hash = canonical_payload(payload)
    projection_id = material.get("lifecycle_projection_id")
    if not isinstance(projection_id, str) or not projection_id:
        raise RuntimeValidationError("BINDING_PROJECTION_ID_REQUIRED", "binding lifecycle_projection_id is required")
    projection_row = store._connection.execute(
        "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
        (projection_id,),
    ).fetchone()
    if projection_row is None:
        raise RuntimeValidationError("BINDING_PROJECTION_MISSING", "binding lifecycle projection is not durable")
    projection = _payload_from_row(projection_row)
    facts = validate_lifecycle_execution_binding(material, projection)
    binding_id = str(facts["binding_id"])

    try:
        store._connection.execute("BEGIN IMMEDIATE")
        existing_id = store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE lifecycle_execution_binding_id = ?",
            (binding_id,),
        ).fetchone()
        if existing_id is not None:
            if existing_id["payload_json"] == payload_json:
                store._connection.rollback()
                return _stored("POSITION_LIFECYCLE_EXECUTION_BINDING", binding_id, existing_id)
            store._raise_conflict(
                "LIFECYCLE_EXECUTION_BINDING_ID_CONFLICT",
                "same lifecycle execution binding ID has different canonical payload",
                "POSITION_LIFECYCLE_EXECUTION_BINDING",
                canonical_id=binding_id,
                position_id=facts["position_id"],
                existing_payload_hash=existing_id["payload_hash"],
                incoming_payload_hash=payload_hash,
            )

        existing_projection = store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE lifecycle_projection_id = ?",
            (projection_id,),
        ).fetchone()
        if existing_projection is not None:
            store._raise_conflict(
                "LIFECYCLE_EXECUTION_BINDING_PROJECTION_CONFLICT",
                "lifecycle projection already has a different immutable execution binding",
                "POSITION_LIFECYCLE_EXECUTION_BINDING",
                canonical_id=binding_id,
                position_id=facts["position_id"],
                existing_payload_hash=existing_projection["payload_hash"],
                incoming_payload_hash=payload_hash,
            )

        store._connection.execute(
            """
            INSERT INTO paper_position_lifecycle_execution_bindings (
                lifecycle_execution_binding_id, lifecycle_projection_id,
                position_id, lifecycle_revision, execution_interpreted_at,
                execution_scope, execution_snapshot_hash, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                binding_id,
                projection_id,
                facts["position_id"],
                facts["revision"],
                facts["execution_interpreted_at"],
                facts["execution_scope"],
                facts["execution_snapshot_hash"],
                payload_json,
                payload_hash,
            ),
        )
        store._connection.commit()
        return StoredCanonicalObject(
            "POSITION_LIFECYCLE_EXECUTION_BINDING",
            binding_id,
            payload_json,
            payload_hash,
        )
    except RuntimePersistenceError:
        raise
    except Exception:
        store._connection.rollback()
        raise


def _nonempty_unique_ids(payload: Mapping[str, Any], field: str) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise RuntimeValidationError("TRADE_RESULT_REFERENCE_LIST_INVALID", f"TradeResult.{field} must be a non-empty list")
    ids = [_text(item, f"TradeResult.{field}[]") for item in value]
    if len(ids) != len(set(ids)):
        raise RuntimeValidationError("TRADE_RESULT_REFERENCE_DUPLICATE", f"TradeResult.{field} contains duplicate IDs")
    return ids


def _object_payload(store: "_PaperRuntimeStore", kind: str, canonical_id: str, missing_code: str) -> dict[str, Any]:
    row = store._object_row(kind, canonical_id)
    if row is None:
        raise RuntimeValidationError(missing_code, f"TradeResult referenced {kind} {canonical_id} is not durable")
    return _payload_from_row(row)


def validate_trade_result_reference_graph(
    store: "_PaperRuntimeStore",
    payload: Mapping[str, Any],
) -> None:
    trade_plan_id = _text(payload.get("trade_plan_id"), "TradeResult.trade_plan_id")
    position_id = _text(payload.get("position_id"), "TradeResult.position_id")
    symbol = _text(payload.get("symbol"), "TradeResult.symbol")
    direction = payload.get("direction")
    if direction not in {"LONG", "SHORT"}:
        raise RuntimeValidationError("TRADE_RESULT_DIRECTION_INVALID", "TradeResult.direction is unsupported")
    entry_side = "BUY" if direction == "LONG" else "SELL"
    exit_side = "SELL" if direction == "LONG" else "BUY"

    plan = _object_payload(store, "APPROVED_TRADE_PLAN", trade_plan_id, "TRADE_RESULT_PLAN_MISSING")
    for field in (
        "strategy_id",
        "strategy_version",
        "risk_decision_id",
        "risk_policy_version",
        "symbol",
        "direction",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    ):
        if payload.get(field) != plan.get(field):
            raise RuntimeValidationError("TRADE_RESULT_PLAN_REFERENCE_MISMATCH", f"TradeResult.{field} mismatches ApprovedTradePlan")

    entry_request_ids = _nonempty_unique_ids(payload, "entry_order_request_ids")
    exit_request_ids = _nonempty_unique_ids(payload, "exit_order_request_ids")
    entry_fill_ids = _nonempty_unique_ids(payload, "entry_fill_ids")
    exit_fill_ids = _nonempty_unique_ids(payload, "exit_fill_ids")
    if set(entry_fill_ids) & set(exit_fill_ids):
        raise RuntimeValidationError("TRADE_RESULT_FILL_SET_CONFLICT", "entry and exit Fill references overlap")

    refs = payload.get("exit_authority_refs")
    if not isinstance(refs, list) or not refs:
        raise RuntimeValidationError("TRADE_RESULT_EXIT_AUTHORITY_REFS_INVALID", "TradeResult.exit_authority_refs must be non-empty")
    authority_refs: dict[tuple[str, str], dict[str, Any]] = {}
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != _AUTHORITY_REF_FIELDS:
            raise RuntimeValidationError("TRADE_RESULT_EXIT_AUTHORITY_REF_INVALID", "exit_authority_refs element fields are invalid")
        action_id = _text(ref.get("position_action_id"), "exit_authority_ref.position_action_id")
        if ref.get("position_id") != position_id:
            raise RuntimeValidationError("TRADE_RESULT_AUTHORITY_POSITION_MISMATCH", "exit authority position_id mismatches TradeResult")
        action = ref.get("action")
        role = ref.get("order_role")
        if _ACTION_ROLE.get(action) != role:
            raise RuntimeValidationError("TRADE_RESULT_AUTHORITY_ROLE_MISMATCH", "exit authority action/order_role pair is invalid")
        key = (action_id, role)
        if key in authority_refs:
            raise RuntimeValidationError("TRADE_RESULT_AUTHORITY_DUPLICATE", "duplicate exit authority reference")
        action_payload = _object_payload(store, "POSITION_ACTION", action_id, "TRADE_RESULT_POSITION_ACTION_MISSING")
        if action_payload.get("position_id") != position_id or action_payload.get("action") != action:
            raise RuntimeValidationError("TRADE_RESULT_POSITION_ACTION_MISMATCH", "referenced PositionAction does not match authority ref")
        for field in ("trade_plan_id", "risk_decision_id", "symbol"):
            if action_payload.get(field) is not None and action_payload.get(field) != payload.get(field):
                raise RuntimeValidationError("TRADE_RESULT_POSITION_ACTION_LINEAGE_MISMATCH", f"PositionAction.{field} mismatches TradeResult")
        authority_refs[key] = ref

    entry_requests: dict[str, dict[str, Any]] = {}
    entry_clients: dict[str, str] = {}
    for request_id in entry_request_ids:
        request = _object_payload(store, "ORDER_REQUEST", request_id, "TRADE_RESULT_ENTRY_ORDER_REQUEST_MISSING")
        if request.get("trade_plan_id") != trade_plan_id or request.get("symbol") != symbol or request.get("side") != entry_side:
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_ORDER_REQUEST_MISMATCH", "entry OrderRequest lineage mismatches TradeResult")
        if any(request.get(field) is not None for field in ("authorization_type", "position_action_id", "position_id", "order_role")):
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_ORDER_AUTHORITY_MISMATCH", "entry OrderRequest is not plan-authorized entry evidence")
        client_id = _text(request.get("client_order_id"), "entry OrderRequest.client_order_id")
        if client_id in entry_clients:
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_CLIENT_ID_CONFLICT", "referenced entry requests share client_order_id")
        entry_clients[client_id] = request_id
        entry_requests[request_id] = request

    exit_requests: dict[str, dict[str, Any]] = {}
    exit_clients: dict[str, str] = {}
    used_authorities: set[tuple[str, str]] = set()
    for request_id in exit_request_ids:
        request = _object_payload(store, "ORDER_REQUEST", request_id, "TRADE_RESULT_EXIT_ORDER_REQUEST_MISSING")
        if (
            request.get("trade_plan_id") != trade_plan_id
            or request.get("position_id") != position_id
            or request.get("symbol") != symbol
            or request.get("side") != exit_side
            or request.get("authorization_type") != POSITION_ACTION_AUTHORIZATION
            or request.get("risk_decision_id") != payload.get("risk_decision_id")
        ):
            raise RuntimeValidationError("TRADE_RESULT_EXIT_ORDER_REQUEST_MISMATCH", "exit OrderRequest lineage mismatches TradeResult")
        key = (request.get("position_action_id"), request.get("order_role"))
        if key not in authority_refs:
            raise RuntimeValidationError("TRADE_RESULT_EXIT_ORDER_AUTHORITY_MISMATCH", "exit OrderRequest is not covered by exit_authority_refs")
        used_authorities.add(key)
        client_id = _text(request.get("client_order_id"), "exit OrderRequest.client_order_id")
        if client_id in exit_clients:
            raise RuntimeValidationError("TRADE_RESULT_EXIT_CLIENT_ID_CONFLICT", "referenced exit requests share client_order_id")
        exit_clients[client_id] = request_id
        exit_requests[request_id] = request
    if used_authorities != set(authority_refs):
        raise RuntimeValidationError("TRADE_RESULT_UNUSED_EXIT_AUTHORITY", "each exit_authority_ref must bind a referenced exit OrderRequest")

    used_entry_requests: set[str] = set()
    for fill_id in entry_fill_ids:
        fill = _object_payload(store, "FILL", fill_id, "TRADE_RESULT_ENTRY_FILL_MISSING")
        if fill.get("trade_plan_id") != trade_plan_id or fill.get("symbol") != symbol or fill.get("side") != entry_side:
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_FILL_MISMATCH", "entry Fill lineage mismatches TradeResult")
        if any(fill.get(field) is not None for field in ("position_action_id", "position_id", "order_role")):
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_FILL_AUTHORITY_MISMATCH", "entry Fill carries position-linked authority")
        request_id = entry_clients.get(fill.get("client_order_id"))
        if request_id is None:
            raise RuntimeValidationError("TRADE_RESULT_ENTRY_FILL_REQUEST_MISMATCH", "entry Fill does not bind a referenced entry OrderRequest")
        used_entry_requests.add(request_id)
    if used_entry_requests != set(entry_request_ids):
        raise RuntimeValidationError("TRADE_RESULT_UNUSED_ENTRY_ORDER_REQUEST", "every referenced entry OrderRequest requires referenced Fill evidence")

    used_exit_requests: set[str] = set()
    for fill_id in exit_fill_ids:
        fill = _object_payload(store, "FILL", fill_id, "TRADE_RESULT_EXIT_FILL_MISSING")
        if (
            fill.get("trade_plan_id") != trade_plan_id
            or fill.get("position_id") != position_id
            or fill.get("symbol") != symbol
            or fill.get("side") != exit_side
        ):
            raise RuntimeValidationError("TRADE_RESULT_EXIT_FILL_MISMATCH", "exit Fill lineage mismatches TradeResult")
        request_id = exit_clients.get(fill.get("client_order_id"))
        if request_id is None:
            raise RuntimeValidationError("TRADE_RESULT_EXIT_FILL_REQUEST_MISMATCH", "exit Fill does not bind a referenced exit OrderRequest")
        request = exit_requests[request_id]
        if fill.get("position_action_id") != request.get("position_action_id") or fill.get("order_role") != request.get("order_role"):
            raise RuntimeValidationError("TRADE_RESULT_EXIT_FILL_AUTHORITY_MISMATCH", "exit Fill authority lineage mismatches OrderRequest")
        used_exit_requests.add(request_id)
    if used_exit_requests != set(exit_request_ids):
        raise RuntimeValidationError("TRADE_RESULT_UNUSED_EXIT_ORDER_REQUEST", "every referenced exit OrderRequest requires referenced Fill evidence")

    if payload.get("flat_position_observed_at") != payload.get("closed_at"):
        raise RuntimeValidationError("TRADE_RESULT_FLAT_POSITION_TIME_MISMATCH", "flat_position_observed_at must equal closed_at")


def _trade_result_reference_reason(store: "_PaperRuntimeStore", payload: Mapping[str, Any]) -> str | None:
    try:
        validate_trade_result_reference_graph(store, payload)
        return None
    except RuntimeValidationError as exc:
        if "MISSING" in exc.code:
            return exc.code
        return exc.code if "CONFLICT" in exc.code or "MISMATCH" in exc.code else "TRADE_RESULT_REFERENCED_GRAPH_INVALID"


def augment_recovery_with_binding_and_trade_result(
    store: "_PaperRuntimeStore",
    recovery: PaperRuntimeRecovery,
) -> PaperRuntimeRecovery:
    reasons = list(recovery.reason_codes)
    binding_objects: tuple[StoredCanonicalObject, ...] = ()
    current_binding: StoredCanonicalObject | None = None

    if recovery.position_id is not None:
        binding_rows = store._connection.execute(
            """
            SELECT * FROM paper_position_lifecycle_execution_bindings
            WHERE position_id = ? ORDER BY lifecycle_revision
            """,
            (recovery.position_id,),
        ).fetchall()
        binding_objects = tuple(
            _stored("POSITION_LIFECYCLE_EXECUTION_BINDING", row["lifecycle_execution_binding_id"], row)
            for row in binding_rows
        )

    if recovery.current_position_projection is not None:
        projection = recovery.current_position_projection.payload
        projection_id = recovery.current_position_projection.canonical_id
        rows = store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE lifecycle_projection_id = ?",
            (projection_id,),
        ).fetchall()
        if len(rows) == 0:
            reasons.append("LIFECYCLE_EXECUTION_BINDING_MISSING")
        elif len(rows) > 1:
            reasons.append("LIFECYCLE_EXECUTION_BINDING_CONFLICT")
        else:
            row = rows[0]
            current_binding = _stored("POSITION_LIFECYCLE_EXECUTION_BINDING", row["lifecycle_execution_binding_id"], row)
            try:
                binding = current_binding.payload
                validate_lifecycle_execution_binding(binding, projection)
                snapshot = recompute_position_linked_execution_snapshot(store, str(recovery.position_id))
                if (
                    binding.get("order_evidence") != snapshot["order_evidence"]
                    or binding.get("execution_snapshot_hash") != snapshot["execution_snapshot_hash"]
                ):
                    reasons.append("E5_EXECUTION_REINTERPRETATION_REQUIRED")
            except RuntimeConflictError:
                reasons.append("LIFECYCLE_EXECUTION_SNAPSHOT_CONFLICT")
            except RuntimeValidationError:
                reasons.append("LIFECYCLE_EXECUTION_BINDING_INVALID")

    if recovery.trade_result is not None:
        reason = _trade_result_reference_reason(store, recovery.trade_result.payload)
        if reason is not None:
            reasons.append(reason)

    unique_reasons = tuple(dict.fromkeys(reasons))
    status = recovery.status
    if any(
        reason in {
            "LIFECYCLE_EXECUTION_BINDING_CONFLICT",
            "LIFECYCLE_EXECUTION_SNAPSHOT_CONFLICT",
            "LIFECYCLE_EXECUTION_BINDING_INVALID",
        }
        or "MISMATCH" in reason
        or "CONFLICT" in reason
        for reason in unique_reasons
    ):
        status = "CONFLICT"
    elif any(
        reason == "LIFECYCLE_EXECUTION_BINDING_MISSING"
        or reason.startswith("TRADE_RESULT_") and "MISSING" in reason
        for reason in unique_reasons
    ):
        if status == "READY":
            status = "INCOMPLETE"
    elif "E5_EXECUTION_REINTERPRETATION_REQUIRED" in unique_reasons and status == "READY":
        status = "REINTERPRETATION_REQUIRED"

    return replace(
        recovery,
        status=status,
        reason_codes=unique_reasons,
        lifecycle_execution_bindings=binding_objects,
        current_lifecycle_execution_binding=current_binding,
    )
