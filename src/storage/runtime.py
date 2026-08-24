from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from ._paper_runtime import _PaperRuntimeStore, _open_paper_runtime_store
from .runtime_models import (
    PaperRuntimeRecovery,
    RuntimeConflictError,
    RuntimePersistenceError,
    RuntimeValidationError,
    StoredCanonicalObject,
)


class PaperRuntimeJournal:
    """Supported E6 durability/restart surface for canonical Paper runtime truth.

    Inputs are already-serialized canonical mappings. This service persists and
    indexes them; it does not call E4/E5 producers, calculate PnL, infer order or
    Position truth, or grant PAPER/SHADOW/LIVE authority.
    """

    __slots__ = ("_store",)

    def __init__(self, store: _PaperRuntimeStore) -> None:
        self._store = store

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "PaperRuntimeJournal":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def persist_risk_decision(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_immutable("RISK_DECISION", payload)

    def persist_approved_trade_plan(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_immutable("APPROVED_TRADE_PLAN", payload)

    def persist_position_action(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_immutable("POSITION_ACTION", payload)

    def persist_order_request(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_immutable("ORDER_REQUEST", payload)

    def persist_fill(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_immutable("FILL", payload)

    def persist_position_projection(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_position_projection(payload)

    def persist_raw_position_observation(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_raw_position_observation(payload)

    def persist_order_result(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_order_result(payload)

    def persist_funding_evidence(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_funding_evidence(payload)

    def persist_trade_result(self, payload: Mapping[str, Any]) -> StoredCanonicalObject:
        return self._store.persist_trade_result(payload)

    def recover(
        self,
        *,
        position_id: str | None = None,
        trade_plan_id: str | None = None,
    ) -> PaperRuntimeRecovery:
        recovery = self._store.recover(position_id=position_id, trade_plan_id=trade_plan_id)
        if recovery.position_id is None:
            reasons = tuple(dict.fromkeys((*recovery.reason_codes, "POSITION_LINEAGE_UNRESOLVED")))
            return replace(recovery, status="INCOMPLETE", reason_codes=reasons)
        return recovery


def open_paper_runtime_journal(path: str | Path) -> PaperRuntimeJournal:
    """Open/migrate SQLite and return the safe E6 Paper durability service."""

    return PaperRuntimeJournal(_open_paper_runtime_store(path))


__all__ = [
    "PaperRuntimeJournal",
    "PaperRuntimeRecovery",
    "RuntimeConflictError",
    "RuntimePersistenceError",
    "RuntimeValidationError",
    "StoredCanonicalObject",
    "open_paper_runtime_journal",
]
