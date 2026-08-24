from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class RuntimePersistenceError(RuntimeError):
    """Base fail-closed persistence/recovery error for the E6 Paper journal."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class RuntimeValidationError(RuntimePersistenceError):
    pass


class RuntimeConflictError(RuntimePersistenceError):
    pass


@dataclass(frozen=True)
class StoredCanonicalObject:
    object_kind: str
    canonical_id: str
    payload_json: str
    payload_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise RuntimeValidationError(
                "STORED_PAYLOAD_NOT_OBJECT",
                f"stored {self.object_kind} payload is not a JSON object",
            )
        return value


@dataclass(frozen=True)
class PaperRuntimeRecovery:
    """E6-local recovery view; not a shared domain contract."""

    status: str
    reason_codes: tuple[str, ...]
    position_id: str | None
    trade_plan_id: str | None
    strategy_id: str | None
    strategy_version: str | None
    risk_decision: StoredCanonicalObject | None
    approved_trade_plan: StoredCanonicalObject | None
    current_position_projection: StoredCanonicalObject | None
    lifecycle_history: tuple[StoredCanonicalObject, ...]
    raw_position_observations: tuple[StoredCanonicalObject, ...]
    position_actions: tuple[StoredCanonicalObject, ...]
    order_requests: tuple[StoredCanonicalObject, ...]
    order_result_observations: tuple[StoredCanonicalObject, ...]
    current_order_results: tuple[StoredCanonicalObject, ...]
    fills: tuple[StoredCanonicalObject, ...]
    funding_evidence: tuple[StoredCanonicalObject, ...]
    trade_result: StoredCanonicalObject | None

    @property
    def restart_authoritative(self) -> bool:
        return self.status == "READY"
