from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._runtime_validation import (
    broker_fact_hash,
    canonical_payload,
    decimal_text,
    immutable_object_metadata,
    validate_funding_evidence,
    validate_order_result,
    validate_position_projection,
    validate_raw_position,
    validate_trade_result,
)
from ._sqlite_registry import _apply_migrations, _connect
from .runtime_models import (
    PaperRuntimeRecovery,
    RuntimeConflictError,
    RuntimePersistenceError,
    RuntimeValidationError,
    StoredCanonicalObject,
)


class _PaperRuntimeStore:
    """E6-owned durable journal for already-canonical Paper runtime payloads.

    This store never calls E4/E5 domain transitions and never reconstructs a
    canonical runtime object from other rows. Current indexes are mechanical
    pointers into append-only canonical observation history.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def close(self) -> None:
        self._connection.close()

    def _record_conflict(
        self,
        reason_code: str,
        object_kind: str,
        *,
        canonical_id: str | None = None,
        trade_plan_id: str | None = None,
        position_id: str | None = None,
        existing_payload_hash: str | None = None,
        incoming_payload_hash: str | None = None,
    ) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO paper_runtime_conflicts (
                    reason_code, object_kind, canonical_id, trade_plan_id,
                    position_id, existing_payload_hash, incoming_payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reason_code,
                    object_kind,
                    canonical_id,
                    trade_plan_id,
                    position_id,
                    existing_payload_hash,
                    incoming_payload_hash,
                ),
            )
            self._connection.commit()
        except sqlite3.Error:
            self._connection.rollback()

    def _raise_conflict(
        self,
        code: str,
        message: str,
        object_kind: str,
        *,
        canonical_id: str | None = None,
        trade_plan_id: str | None = None,
        position_id: str | None = None,
        existing_payload_hash: str | None = None,
        incoming_payload_hash: str | None = None,
    ) -> None:
        self._connection.rollback()
        self._record_conflict(
            code,
            object_kind,
            canonical_id=canonical_id,
            trade_plan_id=trade_plan_id,
            position_id=position_id,
            existing_payload_hash=existing_payload_hash,
            incoming_payload_hash=incoming_payload_hash,
        )
        raise RuntimeConflictError(code, message)

    def _object_row(self, kind: str, canonical_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM paper_runtime_objects WHERE object_kind = ? AND canonical_id = ?",
            (kind, canonical_id),
        ).fetchone()

    def _object_by_client_order_id(self, client_order_id: str) -> sqlite3.Row | None:
        return self._connection.execute(
            """
            SELECT * FROM paper_runtime_objects
            WHERE object_kind = 'ORDER_REQUEST' AND client_order_id = ?
            """,
            (client_order_id,),
        ).fetchone()

    @staticmethod
    def _row_payload(row: sqlite3.Row) -> dict[str, Any]:
        value = json.loads(row["payload_json"])
        if not isinstance(value, dict):
            raise RuntimeValidationError("STORED_PAYLOAD_NOT_OBJECT", "stored canonical payload is not a JSON object")
        return value

    @staticmethod
    def _stored(kind: str, canonical_id: str, payload_json: str, payload_hash: str) -> StoredCanonicalObject:
        return StoredCanonicalObject(kind, canonical_id, payload_json, payload_hash)

    def _validate_parent_links(self, kind: str, payload: Mapping[str, Any], metadata: Mapping[str, Any]) -> None:
        if kind == "APPROVED_TRADE_PLAN":
            risk_id = payload.get("risk_decision_id")
            if not isinstance(risk_id, str) or not risk_id:
                raise RuntimeValidationError("RISK_DECISION_ID_REQUIRED", "ApprovedTradePlan requires risk_decision_id")
            risk_row = self._object_row("RISK_DECISION", risk_id)
            if risk_row is None:
                raise RuntimeValidationError("PARENT_RISK_DECISION_MISSING", "ApprovedTradePlan parent RiskDecision is not durable")
            risk = self._row_payload(risk_row)
            for field in ("strategy_id", "strategy_version"):
                if risk.get(field) != payload.get(field):
                    raise RuntimeValidationError("PLAN_RISK_LINEAGE_MISMATCH", f"ApprovedTradePlan {field} mismatches RiskDecision")
            if risk.get("decision") != "APPROVE":
                raise RuntimeValidationError("PLAN_RISK_NOT_APPROVED", "ApprovedTradePlan parent RiskDecision is not APPROVE")

        if kind == "POSITION_ACTION":
            trade_plan_id = metadata.get("trade_plan_id")
            if trade_plan_id is not None:
                plan_row = self._object_row("APPROVED_TRADE_PLAN", str(trade_plan_id))
                if plan_row is None:
                    raise RuntimeValidationError("PARENT_TRADE_PLAN_MISSING", "PositionAction parent ApprovedTradePlan is not durable")
                plan = self._row_payload(plan_row)
                for field in ("risk_decision_id", "strategy_id", "strategy_version"):
                    if field in payload and payload.get(field) != plan.get(field):
                        raise RuntimeValidationError("POSITION_ACTION_LINEAGE_MISMATCH", f"PositionAction {field} mismatches parent plan")

        if kind == "ORDER_REQUEST":
            plan_row = self._object_row("APPROVED_TRADE_PLAN", str(metadata["trade_plan_id"]))
            if plan_row is None:
                raise RuntimeValidationError("PARENT_TRADE_PLAN_MISSING", "OrderRequest parent ApprovedTradePlan is not durable")
            if payload.get("position_action_id") is not None:
                action_id = payload.get("position_action_id")
                if not isinstance(action_id, str) or not action_id:
                    raise RuntimeValidationError("POSITION_ACTION_ID_INVALID", "position_action_id must be a non-empty string")
                action_row = self._object_row("POSITION_ACTION", action_id)
                if action_row is None:
                    raise RuntimeValidationError("POSITION_ACTION_MISSING", "OrderRequest PositionAction authority is not durable")
                action = self._row_payload(action_row)
                for request_field, action_field in (
                    ("trade_plan_id", "trade_plan_id"),
                    ("position_id", "position_id"),
                    ("risk_decision_id", "risk_decision_id"),
                ):
                    if payload.get(request_field) != action.get(action_field):
                        raise RuntimeValidationError("ORDER_ACTION_LINEAGE_MISMATCH", f"OrderRequest {request_field} mismatches PositionAction")

        if kind == "FILL":
            request_row = self._object_by_client_order_id(str(metadata["client_order_id"]))
            if request_row is None:
                raise RuntimeValidationError("ORDER_REQUEST_MISSING", "Fill parent OrderRequest is not durable")
            request = self._row_payload(request_row)
            for field in ("trade_plan_id", "symbol", "side"):
                if payload.get(field) != request.get(field):
                    raise RuntimeValidationError("FILL_REQUEST_LINEAGE_MISMATCH", f"Fill {field} mismatches OrderRequest")
            for field in ("position_action_id", "position_id", "order_role"):
                if request.get(field) is not None and payload.get(field) != request.get(field):
                    raise RuntimeValidationError("FILL_REQUEST_LINEAGE_MISMATCH", f"Fill {field} mismatches OrderRequest")

    def persist_immutable(self, kind: str, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        metadata = immutable_object_metadata(kind, material)
        canonical_id = str(metadata["canonical_id"])
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            existing = self._object_row(kind, canonical_id)
            if existing is not None:
                if existing["payload_json"] == payload_json:
                    self._connection.rollback()
                    return self._stored(kind, canonical_id, existing["payload_json"], existing["payload_hash"])
                self._raise_conflict(
                    "IMMUTABLE_ID_PAYLOAD_CONFLICT",
                    f"{kind} canonical ID already exists with different payload",
                    kind,
                    canonical_id=canonical_id,
                    trade_plan_id=metadata.get("trade_plan_id"),
                    position_id=metadata.get("position_id"),
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            if kind == "ORDER_REQUEST":
                by_client = self._object_by_client_order_id(str(metadata["client_order_id"]))
                if by_client is not None and by_client["canonical_id"] != canonical_id:
                    self._raise_conflict(
                        "CLIENT_ORDER_ID_CONFLICT",
                        "client_order_id already belongs to a different OrderRequest",
                        kind,
                        canonical_id=canonical_id,
                        trade_plan_id=metadata.get("trade_plan_id"),
                        position_id=metadata.get("position_id"),
                        existing_payload_hash=by_client["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )

            self._validate_parent_links(kind, material, metadata)
            self._connection.execute(
                """
                INSERT INTO paper_runtime_objects (
                    object_kind, canonical_id, payload_json, payload_hash,
                    strategy_id, strategy_version, trade_plan_id, position_id,
                    order_request_id, client_order_id, broker_order_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kind,
                    canonical_id,
                    payload_json,
                    payload_hash,
                    metadata.get("strategy_id"),
                    metadata.get("strategy_version"),
                    metadata.get("trade_plan_id"),
                    metadata.get("position_id"),
                    metadata.get("order_request_id"),
                    metadata.get("client_order_id"),
                    metadata.get("broker_order_id"),
                ),
            )
            self._connection.commit()
            return self._stored(kind, canonical_id, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def persist_position_projection(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        facts = validate_position_projection(material)
        position_id = str(facts["position_id"])
        projection_id = str(facts["projection_id"])
        revision = int(facts["revision"])
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            existing_id = self._connection.execute(
                "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
                (projection_id,),
            ).fetchone()
            if existing_id is not None:
                if existing_id["payload_json"] == payload_json:
                    self._connection.rollback()
                    return self._stored("POSITION_LIFECYCLE_PROJECTION", projection_id, existing_id["payload_json"], existing_id["payload_hash"])
                self._raise_conflict(
                    "LIFECYCLE_PROJECTION_ID_CONFLICT",
                    "same lifecycle_projection_id has different canonical payload",
                    "POSITION_LIFECYCLE_PROJECTION",
                    canonical_id=projection_id,
                    position_id=position_id,
                    existing_payload_hash=existing_id["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            same_revision = self._connection.execute(
                """
                SELECT * FROM paper_position_lifecycle_projections
                WHERE position_id = ? AND lifecycle_revision = ?
                """,
                (position_id, revision),
            ).fetchone()
            if same_revision is not None:
                self._raise_conflict(
                    "LIFECYCLE_REVISION_CONFLICT",
                    "same position lifecycle revision already has a different projection",
                    "POSITION_LIFECYCLE_PROJECTION",
                    canonical_id=projection_id,
                    position_id=position_id,
                    existing_payload_hash=same_revision["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            current = self._connection.execute(
                "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
                (position_id,),
            ).fetchone()
            history_exists = self._connection.execute(
                "SELECT 1 FROM paper_position_lifecycle_projections WHERE position_id = ? LIMIT 1",
                (position_id,),
            ).fetchone()

            if current is None:
                if history_exists is not None:
                    self._raise_conflict(
                        "CURRENT_PROJECTION_INDEX_MISSING",
                        "Position lifecycle history exists without a current index",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        incoming_payload_hash=payload_hash,
                    )
                if revision != 0 or facts["kind"] != "GENESIS":
                    self._raise_conflict(
                        "LIFECYCLE_REVISION_GAP",
                        "first durable lifecycle projection must be GENESIS revision 0",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        incoming_payload_hash=payload_hash,
                    )
            else:
                current_revision = int(current["lifecycle_revision"])
                if revision <= current_revision:
                    self._raise_conflict(
                        "STALE_LIFECYCLE_BRANCH_CONFLICT",
                        "non-identical stale lifecycle revision cannot replace current projection",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=current["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                if revision != current_revision + 1:
                    self._raise_conflict(
                        "LIFECYCLE_REVISION_GAP",
                        "lifecycle projection cannot skip a revision",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=current["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                if facts["previous_id"] != current["lifecycle_projection_id"]:
                    self._raise_conflict(
                        "LIFECYCLE_PREDECESSOR_MISMATCH",
                        "lifecycle projection predecessor does not match current projection",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=current["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                previous = self._connection.execute(
                    "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
                    (current["lifecycle_projection_id"],),
                ).fetchone()
                if previous is None:
                    self._raise_conflict(
                        "LIFECYCLE_PREDECESSOR_MISSING",
                        "current lifecycle predecessor row is missing",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        incoming_payload_hash=payload_hash,
                    )
                if str(facts["broker_state_observed_at"]) < previous["broker_state_observed_at"]:
                    self._raise_conflict(
                        "BROKER_ANCHOR_REGRESSION",
                        "higher lifecycle revision cannot use an older broker observation",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=previous["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                if (
                    str(facts["broker_state_observed_at"]) == previous["broker_state_observed_at"]
                    and facts["broker_fact_hash"] != previous["broker_fact_hash"]
                ):
                    self._raise_conflict(
                        "EQUAL_TIME_BROKER_FACT_CONFLICT",
                        "equal broker anchor requires identical E4-owned broker facts",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=previous["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                previous_payload = self._row_payload(previous)
                if facts["kind"] == "REATTESTATION" and material.get("lifecycle_state") != previous_payload.get("lifecycle_state"):
                    self._raise_conflict(
                        "REATTESTATION_STATE_CHANGE",
                        "REATTESTATION must preserve previous lifecycle_state",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=previous["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                if facts["kind"] == "TRANSITION" and material.get("lifecycle_state") == previous_payload.get("lifecycle_state"):
                    self._raise_conflict(
                        "TRANSITION_STATE_UNCHANGED",
                        "TRANSITION must represent a lifecycle_state change",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        existing_payload_hash=previous["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )

            raw_same_time = self._connection.execute(
                """
                SELECT * FROM paper_position_broker_observations
                WHERE position_id = ? AND broker_state_observed_at = ?
                """,
                (position_id, facts["broker_state_observed_at"]),
            ).fetchone()
            if raw_same_time is not None and raw_same_time["broker_fact_hash"] != facts["broker_fact_hash"]:
                self._raise_conflict(
                    "PROFILE_RAW_BROKER_FACT_CONFLICT",
                    "profiled lifecycle projection conflicts with raw broker facts at same observation time",
                    "POSITION_LIFECYCLE_PROJECTION",
                    canonical_id=projection_id,
                    position_id=position_id,
                    existing_payload_hash=raw_same_time["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            self._connection.execute(
                """
                INSERT INTO paper_position_lifecycle_projections (
                    lifecycle_projection_id, position_id, lifecycle_revision,
                    previous_lifecycle_projection_id, lifecycle_projection_kind,
                    lifecycle_event, lifecycle_state, broker_state_observed_at,
                    lifecycle_source_broker_state_observed_at, lifecycle_interpreted_at,
                    broker_fact_hash, payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    projection_id,
                    position_id,
                    revision,
                    facts["previous_id"],
                    facts["kind"],
                    facts["event"],
                    facts["lifecycle_state"],
                    facts["broker_state_observed_at"],
                    material["lifecycle_source_broker_state_observed_at"],
                    material["lifecycle_interpreted_at"],
                    facts["broker_fact_hash"],
                    payload_json,
                    payload_hash,
                ),
            )
            if current is None:
                self._connection.execute(
                    """
                    INSERT INTO paper_position_current_projection (
                        position_id, lifecycle_projection_id, lifecycle_revision,
                        broker_state_observed_at, payload_hash
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (position_id, projection_id, revision, facts["broker_state_observed_at"], payload_hash),
                )
            else:
                cursor = self._connection.execute(
                    """
                    UPDATE paper_position_current_projection
                    SET lifecycle_projection_id = ?, lifecycle_revision = ?,
                        broker_state_observed_at = ?, payload_hash = ?
                    WHERE position_id = ? AND lifecycle_projection_id = ?
                      AND lifecycle_revision = ?
                    """,
                    (
                        projection_id,
                        revision,
                        facts["broker_state_observed_at"],
                        payload_hash,
                        position_id,
                        current["lifecycle_projection_id"],
                        current["lifecycle_revision"],
                    ),
                )
                if cursor.rowcount != 1:
                    self._raise_conflict(
                        "CURRENT_PROJECTION_CONCURRENCY_CONFLICT",
                        "current Position projection changed during atomic update",
                        "POSITION_LIFECYCLE_PROJECTION",
                        canonical_id=projection_id,
                        position_id=position_id,
                        incoming_payload_hash=payload_hash,
                    )
            self._connection.commit()
            return self._stored("POSITION_LIFECYCLE_PROJECTION", projection_id, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def persist_raw_position_observation(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        facts = validate_raw_position(material)
        position_id = str(facts["position_id"])
        observed_at = str(facts["observed_at"])
        storage_key = position_id + "@" + observed_at
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            existing = self._connection.execute(
                """
                SELECT * FROM paper_position_broker_observations
                WHERE position_id = ? AND broker_state_observed_at = ?
                """,
                (position_id, observed_at),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] == payload_json:
                    self._connection.rollback()
                    return self._stored("POSITION_BROKER_OBSERVATION", storage_key, existing["payload_json"], existing["payload_hash"])
                self._raise_conflict(
                    "EQUAL_TIME_RAW_POSITION_CONFLICT",
                    "same Position broker observation time has conflicting canonical payload",
                    "POSITION_BROKER_OBSERVATION",
                    canonical_id=storage_key,
                    position_id=position_id,
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )
            projection = self._connection.execute(
                """
                SELECT * FROM paper_position_lifecycle_projections
                WHERE position_id = ? AND broker_state_observed_at = ?
                ORDER BY lifecycle_revision DESC LIMIT 1
                """,
                (position_id, observed_at),
            ).fetchone()
            if projection is not None and projection["broker_fact_hash"] != facts["broker_fact_hash"]:
                self._raise_conflict(
                    "RAW_PROFILE_BROKER_FACT_CONFLICT",
                    "raw broker observation conflicts with profiled Position broker facts at same time",
                    "POSITION_BROKER_OBSERVATION",
                    canonical_id=storage_key,
                    position_id=position_id,
                    existing_payload_hash=projection["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )
            self._connection.execute(
                """
                INSERT INTO paper_position_broker_observations (
                    position_id, broker_state_observed_at, broker_fact_hash,
                    payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (position_id, observed_at, facts["broker_fact_hash"], payload_json, payload_hash),
            )
            self._connection.commit()
            return self._stored("POSITION_BROKER_OBSERVATION", storage_key, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def persist_order_result(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        facts = validate_order_result(material)
        request_id = str(facts["order_request_id"])
        observed_at = str(facts["observed_at"])
        observation_key = request_id + "@" + observed_at
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            request_row = self._object_row("ORDER_REQUEST", request_id)
            if request_row is None:
                raise RuntimeValidationError("ORDER_REQUEST_MISSING", "OrderResult parent OrderRequest is not durable")
            request = self._row_payload(request_row)
            if request.get("client_order_id") != facts["client_order_id"]:
                raise RuntimeValidationError("ORDER_RESULT_CLIENT_ID_MISMATCH", "OrderResult client_order_id mismatches OrderRequest")
            if request.get("quantity") != facts["requested_quantity"]:
                raise RuntimeValidationError("ORDER_RESULT_REQUESTED_QUANTITY_MISMATCH", "OrderResult requested_quantity mismatches OrderRequest.quantity")

            existing = self._connection.execute(
                """
                SELECT * FROM paper_order_result_observations
                WHERE order_request_id = ? AND observed_at = ?
                """,
                (request_id, observed_at),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] == payload_json:
                    self._connection.rollback()
                    return self._stored("ORDER_RESULT_OBSERVATION", observation_key, existing["payload_json"], existing["payload_hash"])
                self._raise_conflict(
                    "EQUAL_TIME_ORDER_RESULT_CONFLICT",
                    "same OrderResult observation time has conflicting canonical payload",
                    "ORDER_RESULT_OBSERVATION",
                    canonical_id=observation_key,
                    trade_plan_id=request_row["trade_plan_id"],
                    position_id=request_row["position_id"],
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            known_brokers = {
                row["broker_order_id"]
                for row in self._connection.execute(
                    """
                    SELECT broker_order_id FROM paper_order_result_observations
                    WHERE order_request_id = ? AND broker_order_id IS NOT NULL
                    """,
                    (request_id,),
                ).fetchall()
            }
            if facts["broker_order_id"] is not None and known_brokers and facts["broker_order_id"] not in known_brokers:
                self._raise_conflict(
                    "BROKER_ORDER_ID_CONFLICT",
                    "one OrderRequest cannot resolve to conflicting broker_order_id values",
                    "ORDER_RESULT_OBSERVATION",
                    canonical_id=observation_key,
                    trade_plan_id=request_row["trade_plan_id"],
                    position_id=request_row["position_id"],
                    incoming_payload_hash=payload_hash,
                )

            self._connection.execute(
                """
                INSERT INTO paper_order_result_observations (
                    order_request_id, client_order_id, broker_order_id,
                    observed_at, order_status, execution_health_status,
                    payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    facts["client_order_id"],
                    facts["broker_order_id"],
                    observed_at,
                    facts["order_status"],
                    facts["execution_health_status"],
                    payload_json,
                    payload_hash,
                ),
            )
            current = self._connection.execute(
                "SELECT * FROM paper_order_result_current WHERE order_request_id = ?",
                (request_id,),
            ).fetchone()
            if current is None:
                self._connection.execute(
                    "INSERT INTO paper_order_result_current(order_request_id, observed_at, payload_hash) VALUES (?, ?, ?)",
                    (request_id, observed_at, payload_hash),
                )
            elif observed_at > current["observed_at"]:
                self._connection.execute(
                    """
                    UPDATE paper_order_result_current
                    SET observed_at = ?, payload_hash = ?
                    WHERE order_request_id = ? AND observed_at = ?
                    """,
                    (observed_at, payload_hash, request_id, current["observed_at"]),
                )
            self._connection.commit()
            return self._stored("ORDER_RESULT_OBSERVATION", observation_key, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def persist_funding_evidence(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        facts = validate_funding_evidence(material)
        funding_id = str(facts["funding_evidence_id"])
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            existing = self._connection.execute(
                "SELECT * FROM paper_funding_evidence WHERE funding_evidence_id = ?",
                (funding_id,),
            ).fetchone()
            if existing is not None:
                if existing["identity_material_hash"] != facts["identity_material_hash"]:
                    self._raise_conflict(
                        "FUNDING_IDENTITY_CORRUPTION",
                        "same funding_evidence_id has different identity material",
                        "FUNDING_ALLOCATION_EVIDENCE",
                        canonical_id=funding_id,
                        trade_plan_id=facts["trade_plan_id"],
                        position_id=facts["position_id"],
                        existing_payload_hash=existing["payload_hash"],
                        incoming_payload_hash=payload_hash,
                    )
                self._connection.execute(
                    """
                    INSERT OR IGNORE INTO paper_funding_observations (
                        funding_evidence_id, calculated_at, payload_hash
                    ) VALUES (?, ?, ?)
                    """,
                    (funding_id, facts["calculated_at"], payload_hash),
                )
                self._connection.commit()
                return self._stored("FUNDING_ALLOCATION_EVIDENCE", funding_id, existing["payload_json"], existing["payload_hash"])

            lineage = self._connection.execute(
                "SELECT * FROM paper_funding_evidence WHERE lineage_key_hash = ?",
                (facts["lineage_key_hash"],),
            ).fetchone()
            if lineage is not None and lineage["funding_evidence_id"] != funding_id:
                self._raise_conflict(
                    "FUNDING_LINEAGE_CONFLICT",
                    "different funding evidence IDs claim the same exact allocation lineage",
                    "FUNDING_ALLOCATION_EVIDENCE",
                    canonical_id=funding_id,
                    trade_plan_id=facts["trade_plan_id"],
                    position_id=facts["position_id"],
                    existing_payload_hash=lineage["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            self._connection.execute(
                """
                INSERT INTO paper_funding_evidence (
                    funding_evidence_id, lineage_key_hash, trade_plan_id, position_id,
                    symbol, interval_start, interval_end, interval_semantics,
                    identity_material_hash, calculated_at, payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    funding_id,
                    facts["lineage_key_hash"],
                    facts["trade_plan_id"],
                    facts["position_id"],
                    facts["symbol"],
                    facts["interval_start"],
                    facts["interval_end"],
                    facts["interval_semantics"],
                    facts["identity_material_hash"],
                    facts["calculated_at"],
                    payload_json,
                    payload_hash,
                ),
            )
            self._connection.execute(
                "INSERT INTO paper_funding_observations(funding_evidence_id, calculated_at, payload_hash) VALUES (?, ?, ?)",
                (funding_id, facts["calculated_at"], payload_hash),
            )
            self._connection.commit()
            return self._stored("FUNDING_ALLOCATION_EVIDENCE", funding_id, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def persist_trade_result(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        material, payload_json, payload_hash = canonical_payload(payload)
        facts = validate_trade_result(material)
        trade_result_id = str(facts["trade_result_id"])
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            existing = self._connection.execute(
                "SELECT * FROM paper_trade_results WHERE trade_result_id = ?",
                (trade_result_id,),
            ).fetchone()
            if existing is not None:
                if existing["payload_json"] == payload_json:
                    self._connection.rollback()
                    return self._stored("TRADE_RESULT", trade_result_id, existing["payload_json"], existing["payload_hash"])
                self._raise_conflict(
                    "TRADE_RESULT_ID_CONFLICT",
                    "same trade_result_id has different canonical payload",
                    "TRADE_RESULT",
                    canonical_id=trade_result_id,
                    trade_plan_id=facts["trade_plan_id"],
                    position_id=facts["position_id"],
                    existing_payload_hash=existing["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            lineage = self._connection.execute(
                "SELECT * FROM paper_trade_results WHERE trade_plan_id = ? AND position_id = ?",
                (facts["trade_plan_id"], facts["position_id"]),
            ).fetchone()
            if lineage is not None:
                self._raise_conflict(
                    "TRADE_RESULT_LINEAGE_CONFLICT",
                    "closed position/trade lineage already has a different immutable TradeResult",
                    "TRADE_RESULT",
                    canonical_id=trade_result_id,
                    trade_plan_id=facts["trade_plan_id"],
                    position_id=facts["position_id"],
                    existing_payload_hash=lineage["payload_hash"],
                    incoming_payload_hash=payload_hash,
                )

            plan_row = self._object_row("APPROVED_TRADE_PLAN", str(facts["trade_plan_id"]))
            if plan_row is None:
                raise RuntimeValidationError("PARENT_TRADE_PLAN_MISSING", "TradeResult parent ApprovedTradePlan is not durable")
            plan = self._row_payload(plan_row)
            for field in ("strategy_id", "strategy_version"):
                if plan.get(field) != facts[field]:
                    raise RuntimeValidationError("TRADE_RESULT_PLAN_LINEAGE_MISMATCH", f"TradeResult {field} mismatches parent plan")

            funding_row = self._connection.execute(
                "SELECT * FROM paper_funding_evidence WHERE funding_evidence_id = ?",
                (facts["funding_evidence_id"],),
            ).fetchone()
            if funding_row is None:
                raise RuntimeValidationError("FUNDING_EVIDENCE_MISSING", "TradeResult funding evidence is not durable")
            funding = self._row_payload(funding_row)
            binding_pairs = (
                ("trade_plan_id", "trade_plan_id"),
                ("position_id", "position_id"),
                ("symbol", "symbol"),
                ("opened_at", "interval_start"),
                ("closed_at", "interval_end"),
            )
            for result_field, funding_field in binding_pairs:
                if material.get(result_field) != funding.get(funding_field):
                    raise RuntimeValidationError("TRADE_RESULT_FUNDING_BINDING_MISMATCH", f"TradeResult {result_field} mismatches funding {funding_field}")
            if material.get("funding_evidence_status") != funding.get("status"):
                raise RuntimeValidationError("TRADE_RESULT_FUNDING_STATUS_MISMATCH", "TradeResult funding status mismatches evidence")
            if funding.get("status") == "INCLUDED" and material.get("funding_cost") != funding.get("funding_cost"):
                raise RuntimeValidationError("TRADE_RESULT_FUNDING_COST_MISMATCH", "TradeResult funding cost mismatches evidence")
            if funding.get("status") == "ZERO_CONFIRMED" and material.get("funding_cost") not in (None, "0"):
                raise RuntimeValidationError("TRADE_RESULT_ZERO_FUNDING_MISMATCH", "ZERO_CONFIRMED TradeResult funding_cost must be omitted or zero")

            self._connection.execute(
                """
                INSERT INTO paper_trade_results (
                    trade_result_id, trade_plan_id, position_id,
                    strategy_id, strategy_version, funding_evidence_id,
                    payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_result_id,
                    facts["trade_plan_id"],
                    facts["position_id"],
                    facts["strategy_id"],
                    facts["strategy_version"],
                    facts["funding_evidence_id"],
                    payload_json,
                    payload_hash,
                ),
            )
            self._connection.commit()
            return self._stored("TRADE_RESULT", trade_result_id, payload_json, payload_hash)
        except RuntimePersistenceError:
            raise
        except Exception:
            self._connection.rollback()
            raise

    def _stored_rows(self, kind: str, rows: Sequence[sqlite3.Row], *, id_column: str = "canonical_id") -> tuple[StoredCanonicalObject, ...]:
        return tuple(
            self._stored(kind, str(row[id_column]), row["payload_json"], row["payload_hash"])
            for row in rows
        )

    def _projection_chain(self, position_id: str) -> tuple[tuple[StoredCanonicalObject, ...], list[str]]:
        rows = self._connection.execute(
            """
            SELECT * FROM paper_position_lifecycle_projections
            WHERE position_id = ? ORDER BY lifecycle_revision
            """,
            (position_id,),
        ).fetchall()
        reasons: list[str] = []
        previous: sqlite3.Row | None = None
        for expected_revision, row in enumerate(rows):
            try:
                payload = self._row_payload(row)
                validate_position_projection(payload)
            except RuntimePersistenceError:
                reasons.append("LIFECYCLE_PROJECTION_PAYLOAD_CORRUPT")
                continue
            if int(row["lifecycle_revision"]) != expected_revision:
                reasons.append("LIFECYCLE_REVISION_GAP")
            if previous is None:
                if row["lifecycle_revision"] != 0 or row["previous_lifecycle_projection_id"] is not None:
                    reasons.append("LIFECYCLE_GENESIS_INVALID")
            else:
                if row["previous_lifecycle_projection_id"] != previous["lifecycle_projection_id"]:
                    reasons.append("LIFECYCLE_PREDECESSOR_MISMATCH")
                if row["broker_state_observed_at"] < previous["broker_state_observed_at"]:
                    reasons.append("BROKER_ANCHOR_REGRESSION")
                if row["broker_state_observed_at"] == previous["broker_state_observed_at"] and row["broker_fact_hash"] != previous["broker_fact_hash"]:
                    reasons.append("EQUAL_TIME_BROKER_FACT_CONFLICT")
            previous = row

        current = self._connection.execute(
            "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
            (position_id,),
        ).fetchone()
        if rows:
            if current is None:
                reasons.append("CURRENT_PROJECTION_INDEX_MISSING")
            else:
                latest = rows[-1]
                if (
                    current["lifecycle_projection_id"] != latest["lifecycle_projection_id"]
                    or current["lifecycle_revision"] != latest["lifecycle_revision"]
                    or current["payload_hash"] != latest["payload_hash"]
                ):
                    reasons.append("CURRENT_PROJECTION_INDEX_MISMATCH")
        elif current is not None:
            reasons.append("CURRENT_PROJECTION_WITHOUT_HISTORY")

        stored = tuple(
            self._stored(
                "POSITION_LIFECYCLE_PROJECTION",
                row["lifecycle_projection_id"],
                row["payload_json"],
                row["payload_hash"],
            )
            for row in rows
        )
        return stored, reasons

    def recover(
        self,
        *,
        position_id: str | None = None,
        trade_plan_id: str | None = None,
    ) -> PaperRuntimeRecovery:
        if position_id is None and trade_plan_id is None:
            raise RuntimeValidationError("RECOVERY_LINEAGE_REQUIRED", "position_id or trade_plan_id is required")
        if position_id is not None and (not isinstance(position_id, str) or not position_id):
            raise RuntimeValidationError("POSITION_ID_INVALID", "position_id must be a non-empty string")
        if trade_plan_id is not None and (not isinstance(trade_plan_id, str) or not trade_plan_id):
            raise RuntimeValidationError("TRADE_PLAN_ID_INVALID", "trade_plan_id must be a non-empty string")

        reasons: list[str] = []
        position_candidates: set[str] = set()
        plan_candidates: set[str] = set()
        if position_id is not None:
            position_candidates.add(position_id)
            for row in self._connection.execute(
                "SELECT DISTINCT trade_plan_id FROM paper_runtime_objects WHERE position_id = ? AND trade_plan_id IS NOT NULL",
                (position_id,),
            ).fetchall():
                plan_candidates.add(row["trade_plan_id"])
            for table in ("paper_funding_evidence", "paper_trade_results"):
                for row in self._connection.execute(
                    f"SELECT DISTINCT trade_plan_id FROM {table} WHERE position_id = ?",
                    (position_id,),
                ).fetchall():
                    plan_candidates.add(row["trade_plan_id"])
        if trade_plan_id is not None:
            plan_candidates.add(trade_plan_id)
            for row in self._connection.execute(
                "SELECT DISTINCT position_id FROM paper_runtime_objects WHERE trade_plan_id = ? AND position_id IS NOT NULL",
                (trade_plan_id,),
            ).fetchall():
                position_candidates.add(row["position_id"])
            for table in ("paper_funding_evidence", "paper_trade_results"):
                for row in self._connection.execute(
                    f"SELECT DISTINCT position_id FROM {table} WHERE trade_plan_id = ?",
                    (trade_plan_id,),
                ).fetchall():
                    position_candidates.add(row["position_id"])

        if len(position_candidates) > 1:
            reasons.append("MULTIPLE_POSITION_LINEAGE_CONFLICT")
        if len(plan_candidates) > 1:
            reasons.append("MULTIPLE_TRADE_PLAN_LINEAGE_CONFLICT")
        resolved_position = position_id or (next(iter(position_candidates)) if len(position_candidates) == 1 else None)
        resolved_plan = trade_plan_id or (next(iter(plan_candidates)) if len(plan_candidates) == 1 else None)

        lifecycle_history: tuple[StoredCanonicalObject, ...] = ()
        current_projection: StoredCanonicalObject | None = None
        raw_positions: tuple[StoredCanonicalObject, ...] = ()
        if resolved_position is not None:
            lifecycle_history, chain_reasons = self._projection_chain(resolved_position)
            reasons.extend(chain_reasons)
            current_row = self._connection.execute(
                """
                SELECT p.* FROM paper_position_current_projection c
                JOIN paper_position_lifecycle_projections p
                  ON p.lifecycle_projection_id = c.lifecycle_projection_id
                WHERE c.position_id = ?
                """,
                (resolved_position,),
            ).fetchone()
            if current_row is None:
                reasons.append("RESTART_AUTHORITATIVE_POSITION_MISSING")
            else:
                current_projection = self._stored(
                    "POSITION_LIFECYCLE_PROJECTION",
                    current_row["lifecycle_projection_id"],
                    current_row["payload_json"],
                    current_row["payload_hash"],
                )
            raw_rows = self._connection.execute(
                """
                SELECT * FROM paper_position_broker_observations
                WHERE position_id = ? ORDER BY broker_state_observed_at
                """,
                (resolved_position,),
            ).fetchall()
            raw_positions = tuple(
                self._stored(
                    "POSITION_BROKER_OBSERVATION",
                    resolved_position + "@" + row["broker_state_observed_at"],
                    row["payload_json"],
                    row["payload_hash"],
                )
                for row in raw_rows
            )
            if current_row is not None and raw_rows and raw_rows[-1]["broker_state_observed_at"] > current_row["broker_state_observed_at"]:
                reasons.append("E5_REATTESTATION_REQUIRED")

        plan_object: StoredCanonicalObject | None = None
        risk_object: StoredCanonicalObject | None = None
        strategy_id: str | None = None
        strategy_version: str | None = None
        if resolved_plan is not None:
            plan_row = self._object_row("APPROVED_TRADE_PLAN", resolved_plan)
            if plan_row is None:
                reasons.append("APPROVED_TRADE_PLAN_MISSING")
            else:
                plan_object = self._stored("APPROVED_TRADE_PLAN", resolved_plan, plan_row["payload_json"], plan_row["payload_hash"])
                plan = self._row_payload(plan_row)
                strategy_id = plan.get("strategy_id") if isinstance(plan.get("strategy_id"), str) else None
                strategy_version = plan.get("strategy_version") if isinstance(plan.get("strategy_version"), str) else None
                risk_id = plan.get("risk_decision_id")
                if isinstance(risk_id, str):
                    risk_row = self._object_row("RISK_DECISION", risk_id)
                    if risk_row is None:
                        reasons.append("RISK_DECISION_MISSING")
                    else:
                        risk_object = self._stored("RISK_DECISION", risk_id, risk_row["payload_json"], risk_row["payload_hash"])
                else:
                    reasons.append("RISK_DECISION_ID_MISSING")
        else:
            reasons.append("TRADE_PLAN_LINEAGE_UNRESOLVED")

        where_parts: list[str] = []
        params: list[str] = []
        if resolved_plan is not None:
            where_parts.append("trade_plan_id = ?")
            params.append(resolved_plan)
        if resolved_position is not None:
            where_parts.append("position_id = ?")
            params.append(resolved_position)
        object_filter = " OR ".join(where_parts) if where_parts else "0"
        runtime_rows = self._connection.execute(
            f"SELECT * FROM paper_runtime_objects WHERE ({object_filter}) ORDER BY object_kind, canonical_id",
            tuple(params),
        ).fetchall()
        actions = self._stored_rows("POSITION_ACTION", [r for r in runtime_rows if r["object_kind"] == "POSITION_ACTION"])
        requests = self._stored_rows("ORDER_REQUEST", [r for r in runtime_rows if r["object_kind"] == "ORDER_REQUEST"])
        fills = self._stored_rows("FILL", [r for r in runtime_rows if r["object_kind"] == "FILL"])

        request_ids = [obj.canonical_id for obj in requests]
        order_observation_rows: list[sqlite3.Row] = []
        current_order_rows: list[sqlite3.Row] = []
        for request_id in request_ids:
            order_observation_rows.extend(
                self._connection.execute(
                    "SELECT * FROM paper_order_result_observations WHERE order_request_id = ? ORDER BY observed_at",
                    (request_id,),
                ).fetchall()
            )
            row = self._connection.execute(
                """
                SELECT o.* FROM paper_order_result_current c
                JOIN paper_order_result_observations o
                  ON o.order_request_id = c.order_request_id AND o.observed_at = c.observed_at
                WHERE c.order_request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if row is not None:
                current_order_rows.append(row)

        order_observations = tuple(
            self._stored(
                "ORDER_RESULT_OBSERVATION",
                row["order_request_id"] + "@" + row["observed_at"],
                row["payload_json"],
                row["payload_hash"],
            )
            for row in order_observation_rows
        )
        current_orders = tuple(
            self._stored(
                "ORDER_RESULT_OBSERVATION",
                row["order_request_id"] + "@" + row["observed_at"],
                row["payload_json"],
                row["payload_hash"],
            )
            for row in current_order_rows
        )
        for current_order in current_orders:
            payload = current_order.payload
            if payload.get("order_status") in {"UNKNOWN", "RECONCILIATION_REQUIRED"} or payload.get("execution_health_status") in {"UNKNOWN", "DEGRADED"}:
                reasons.append("ORDER_RECONCILIATION_REQUIRED")

        funding_rows: list[sqlite3.Row] = []
        trade_result_row: sqlite3.Row | None = None
        if resolved_plan is not None or resolved_position is not None:
            clauses: list[str] = []
            values: list[str] = []
            if resolved_plan is not None:
                clauses.append("trade_plan_id = ?")
                values.append(resolved_plan)
            if resolved_position is not None:
                clauses.append("position_id = ?")
                values.append(resolved_position)
            query = " OR ".join(clauses)
            funding_rows = self._connection.execute(
                f"SELECT * FROM paper_funding_evidence WHERE {query} ORDER BY interval_start, funding_evidence_id",
                tuple(values),
            ).fetchall()
            result_rows = self._connection.execute(
                f"SELECT * FROM paper_trade_results WHERE {query} ORDER BY trade_result_id",
                tuple(values),
            ).fetchall()
            if len(result_rows) > 1:
                reasons.append("MULTIPLE_TRADE_RESULTS_CONFLICT")
            elif result_rows:
                trade_result_row = result_rows[0]

        funding_objects = tuple(
            self._stored("FUNDING_ALLOCATION_EVIDENCE", row["funding_evidence_id"], row["payload_json"], row["payload_hash"])
            for row in funding_rows
        )
        trade_result_object = None
        if trade_result_row is not None:
            trade_result_object = self._stored(
                "TRADE_RESULT",
                trade_result_row["trade_result_id"],
                trade_result_row["payload_json"],
                trade_result_row["payload_hash"],
            )

        if current_projection is not None:
            current_payload = current_projection.payload
            if current_payload.get("reconciliation_status") != "CONSISTENT":
                reasons.append("POSITION_RECONCILIATION_REQUIRED")
            if current_payload.get("lifecycle_state") == "CLOSED":
                if trade_result_object is None:
                    reasons.append("CLOSED_POSITION_TRADE_RESULT_MISSING")
                if not funding_objects:
                    reasons.append("CLOSED_POSITION_FUNDING_EVIDENCE_MISSING")
                if trade_result_object is not None:
                    result_payload = trade_result_object.payload
                    if result_payload.get("position_id") != resolved_position:
                        reasons.append("TRADE_RESULT_POSITION_MISMATCH")
                    if current_payload.get("closed_at") is not None and result_payload.get("closed_at") != current_payload.get("closed_at"):
                        reasons.append("TRADE_RESULT_CLOSED_AT_MISMATCH")
            elif trade_result_object is not None:
                reasons.append("TRADE_RESULT_WITHOUT_CLOSED_PROJECTION")

        conflict_clauses: list[str] = []
        conflict_values: list[str] = []
        if resolved_position is not None:
            conflict_clauses.append("position_id = ?")
            conflict_values.append(resolved_position)
        if resolved_plan is not None:
            conflict_clauses.append("trade_plan_id = ?")
            conflict_values.append(resolved_plan)
        if conflict_clauses:
            conflict = self._connection.execute(
                f"SELECT 1 FROM paper_runtime_conflicts WHERE {' OR '.join(conflict_clauses)} LIMIT 1",
                tuple(conflict_values),
            ).fetchone()
            if conflict is not None:
                reasons.append("UNRESOLVED_DURABLE_CONFLICT")

        unique_reasons = tuple(dict.fromkeys(reasons))
        if any("CONFLICT" in reason or reason in {"UNRESOLVED_DURABLE_CONFLICT", "LIFECYCLE_PREDECESSOR_MISMATCH", "BROKER_ANCHOR_REGRESSION"} for reason in unique_reasons):
            status = "CONFLICT"
        elif any(reason in {"RESTART_AUTHORITATIVE_POSITION_MISSING", "APPROVED_TRADE_PLAN_MISSING", "RISK_DECISION_MISSING", "RISK_DECISION_ID_MISSING", "TRADE_PLAN_LINEAGE_UNRESOLVED", "CLOSED_POSITION_TRADE_RESULT_MISSING", "CLOSED_POSITION_FUNDING_EVIDENCE_MISSING", "TRADE_RESULT_WITHOUT_CLOSED_PROJECTION", "LIFECYCLE_REVISION_GAP", "CURRENT_PROJECTION_INDEX_MISSING", "CURRENT_PROJECTION_INDEX_MISMATCH", "CURRENT_PROJECTION_WITHOUT_HISTORY", "LIFECYCLE_PROJECTION_PAYLOAD_CORRUPT", "LIFECYCLE_GENESIS_INVALID"} for reason in unique_reasons):
            status = "INCOMPLETE"
        elif "E5_REATTESTATION_REQUIRED" in unique_reasons:
            status = "REATTESTATION_REQUIRED"
        elif "ORDER_RECONCILIATION_REQUIRED" in unique_reasons or "POSITION_RECONCILIATION_REQUIRED" in unique_reasons:
            status = "RECONCILIATION_REQUIRED"
        else:
            status = "READY"

        return PaperRuntimeRecovery(
            status=status,
            reason_codes=unique_reasons,
            position_id=resolved_position,
            trade_plan_id=resolved_plan,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            risk_decision=risk_object,
            approved_trade_plan=plan_object,
            current_position_projection=current_projection,
            lifecycle_history=lifecycle_history,
            raw_position_observations=raw_positions,
            position_actions=actions,
            order_requests=requests,
            order_result_observations=order_observations,
            current_order_results=current_orders,
            fills=fills,
            funding_evidence=funding_objects,
            trade_result=trade_result_object,
        )


def _open_paper_runtime_store(path: str | Path) -> _PaperRuntimeStore:
    connection = _connect(path)
    _apply_migrations(connection)
    return _PaperRuntimeStore(connection)
