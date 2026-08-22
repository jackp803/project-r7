from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from registry.lifecycle_authority import require_transition_authority
from registry.models import (
    CompatibilityEvidence,
    ConcurrencyConflict,
    IdentityConflict,
    IntakeReceipt,
    InvalidTransition,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
    is_early_lifecycle_transition_allowed,
)

_MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def apply_migrations(connection: sqlite3.Connection, migrations_dir: str | Path | None = None) -> None:
    directory = Path(migrations_dir) if migrations_dir is not None else _MIGRATIONS_DIR
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        )
        """
    )
    applied = {
        row["migration_name"]
        for row in connection.execute("SELECT migration_name FROM schema_migrations")
    }
    for migration in sorted(directory.glob("*.sql")):
        if migration.name in applied:
            continue
        script = migration.read_text(encoding="utf-8")
        connection.executescript(script)
        connection.execute(
            "INSERT INTO schema_migrations(migration_name) VALUES (?)",
            (migration.name,),
        )
        connection.commit()


def _strategy_from_row(row: sqlite3.Row) -> StrategyVersionRecord:
    return StrategyVersionRecord(
        identity=StrategyIdentity(row["strategy_id"], row["strategy_version"]),
        strategy_schema_version=row["strategy_schema_version"],
        content_hash=row["content_hash"],
        name=row["name"],
        symbol=row["symbol"],
        declared_runtime_family=row["declared_runtime_family"],
        declared_runtime_version=row["declared_runtime_version"],
        definition_json=row["definition_json"],
        upstream_created_at=row["upstream_created_at"],
        registered_at=row["registered_at"],
        current_lifecycle_state=row["current_lifecycle_state"],
        registry_revision=row["registry_revision"],
    )


def _compatibility_from_row(row: sqlite3.Row) -> CompatibilityEvidence:
    return CompatibilityEvidence(
        compatibility_id=row["compatibility_id"],
        identity=StrategyIdentity(row["strategy_id"], row["strategy_version"]),
        status=row["status"],
        verification_kind=row["verification_kind"],
        checker=row["checker"],
        checked_at=row["checked_at"],
        reason_codes=tuple(json.loads(row["reason_codes_json"])),
        details=json.loads(row["details_json"]),
        source_revision=row["source_revision"],
        environment=row["environment"],
        command=row["command"],
        result_ref=row["result_ref"],
    )


def _validation_from_row(row: sqlite3.Row) -> ValidationEvidenceRecord:
    return ValidationEvidenceRecord(
        evidence_id=row["evidence_id"],
        evidence_type=row["evidence_type"],
        upstream_object_id=row["upstream_object_id"],
        identity=StrategyIdentity(row["strategy_id"], row["strategy_version"]),
        strategy_content_hash=row["strategy_content_hash"],
        upstream_schema_version=row["upstream_schema_version"],
        producer=row["producer"],
        payload_json=row["payload_json"],
        recorded_at=row["recorded_at"],
        verification_status=row["verification_status"],
        verification_kind=row["verification_kind"],
        decision=row["decision"],
        parent_evidence_id=row["parent_evidence_id"],
        source_revision=row["source_revision"],
        environment=row["environment"],
        command=row["command"],
        result_ref=row["result_ref"],
    )


class SQLiteRegistryStore:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def register_strategy(self, record: StrategyVersionRecord) -> tuple[StrategyVersionRecord, bool]:
        existing = self.get_strategy(record.identity)
        if existing is not None:
            if existing.content_hash != record.content_hash or existing.definition_json != record.definition_json:
                raise IdentityConflict(
                    "same (strategy_id, strategy_version) already exists with different immutable content"
                )
            return existing, False

        self._connection.execute(
            """
            INSERT INTO strategy_versions (
                strategy_id, strategy_version, strategy_schema_version, content_hash,
                name, symbol, declared_runtime_family, declared_runtime_version,
                definition_json, upstream_created_at, registered_at,
                current_lifecycle_state, registry_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.identity.strategy_id,
                record.identity.strategy_version,
                record.strategy_schema_version,
                record.content_hash,
                record.name,
                record.symbol,
                record.declared_runtime_family,
                record.declared_runtime_version,
                record.definition_json,
                record.upstream_created_at,
                record.registered_at,
                record.current_lifecycle_state,
                record.registry_revision,
            ),
        )
        self._connection.commit()
        return record, True

    def get_strategy(self, identity: StrategyIdentity) -> StrategyVersionRecord | None:
        row = self._connection.execute(
            """
            SELECT * FROM strategy_versions
            WHERE strategy_id = ? AND strategy_version = ?
            """,
            (identity.strategy_id, identity.strategy_version),
        ).fetchone()
        return _strategy_from_row(row) if row is not None else None

    def list_versions(self, strategy_id: str) -> Sequence[StrategyVersionRecord]:
        rows = self._connection.execute(
            """
            SELECT * FROM strategy_versions
            WHERE strategy_id = ?
            ORDER BY registered_at, strategy_version
            """,
            (strategy_id,),
        ).fetchall()
        return tuple(_strategy_from_row(row) for row in rows)

    def save_compatibility(self, evidence: CompatibilityEvidence) -> None:
        self._connection.execute(
            """
            INSERT INTO compatibility_evidence (
                compatibility_id, strategy_id, strategy_version, status,
                verification_kind, checker, checked_at, reason_codes_json,
                details_json, source_revision, environment, command, result_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.compatibility_id,
                evidence.identity.strategy_id,
                evidence.identity.strategy_version,
                evidence.status,
                evidence.verification_kind,
                evidence.checker,
                evidence.checked_at,
                json.dumps(list(evidence.reason_codes), separators=(",", ":")),
                json.dumps(dict(evidence.details), sort_keys=True, separators=(",", ":")),
                evidence.source_revision,
                evidence.environment,
                evidence.command,
                evidence.result_ref,
            ),
        )
        self._connection.commit()

    def latest_compatibility(self, identity: StrategyIdentity) -> CompatibilityEvidence | None:
        row = self._connection.execute(
            """
            SELECT * FROM compatibility_evidence
            WHERE strategy_id = ? AND strategy_version = ?
            ORDER BY checked_at DESC, compatibility_id DESC
            LIMIT 1
            """,
            (identity.strategy_id, identity.strategy_version),
        ).fetchone()
        return _compatibility_from_row(row) if row is not None else None

    def save_intake_receipt(self, receipt: IntakeReceipt) -> None:
        self._connection.execute(
            """
            INSERT INTO strategy_intake_receipts (
                intake_id, strategy_id, strategy_version, payload_hash,
                received_at, source_actor, result_status, compatibility_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.intake_id,
                receipt.identity.strategy_id,
                receipt.identity.strategy_version,
                receipt.payload_hash,
                receipt.received_at,
                receipt.source_actor,
                receipt.result_status,
                receipt.compatibility_id,
            ),
        )
        self._connection.commit()

    def save_validation_evidence(self, evidence: ValidationEvidenceRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO validation_evidence (
                evidence_id, evidence_type, upstream_object_id,
                strategy_id, strategy_version, strategy_content_hash,
                upstream_schema_version, producer, decision, parent_evidence_id,
                payload_json, recorded_at, verification_status, verification_kind,
                source_revision, environment, command, result_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.evidence_id,
                evidence.evidence_type,
                evidence.upstream_object_id,
                evidence.identity.strategy_id,
                evidence.identity.strategy_version,
                evidence.strategy_content_hash,
                evidence.upstream_schema_version,
                evidence.producer,
                evidence.decision,
                evidence.parent_evidence_id,
                evidence.payload_json,
                evidence.recorded_at,
                evidence.verification_status,
                evidence.verification_kind,
                evidence.source_revision,
                evidence.environment,
                evidence.command,
                evidence.result_ref,
            ),
        )
        self._connection.commit()

    def get_validation_evidence(self, evidence_id: str) -> ValidationEvidenceRecord | None:
        row = self._connection.execute(
            "SELECT * FROM validation_evidence WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
        return _validation_from_row(row) if row is not None else None

    def find_validation_decisions(self, identity: StrategyIdentity) -> Sequence[ValidationEvidenceRecord]:
        rows = self._connection.execute(
            """
            SELECT * FROM validation_evidence
            WHERE strategy_id = ? AND strategy_version = ?
              AND evidence_type = 'VALIDATION_DECISION'
            ORDER BY recorded_at DESC, evidence_id DESC
            """,
            (identity.strategy_id, identity.strategy_version),
        ).fetchall()
        return tuple(_validation_from_row(row) for row in rows)

    def append_transition(self, transition: LifecycleTransitionRecord) -> StrategyVersionRecord:
        if not is_early_lifecycle_transition_allowed(
            transition.previous_state, transition.new_state
        ):
            raise InvalidTransition(
                "early Slice 2 persistence does not allow lifecycle transition "
                f"{transition.previous_state} -> {transition.new_state}"
            )

        identity = transition.identity
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            row = self._connection.execute(
                """
                SELECT * FROM strategy_versions
                WHERE strategy_id = ? AND strategy_version = ?
                """,
                (identity.strategy_id, identity.strategy_version),
            ).fetchone()
            if row is None:
                raise ConcurrencyConflict("strategy version disappeared during transition")
            current = _strategy_from_row(row)
            if current.current_lifecycle_state != transition.previous_state:
                raise ConcurrencyConflict("authoritative lifecycle state changed")
            if current.registry_revision != transition.expected_registry_revision:
                raise ConcurrencyConflict("registry revision changed")
            expected_resulting_revision = current.registry_revision + 1
            if transition.resulting_registry_revision != expected_resulting_revision:
                raise ConcurrencyConflict("invalid resulting registry revision")

            require_transition_authority(self, current, transition)

            self._connection.execute(
                """
                INSERT INTO lifecycle_transitions (
                    transition_id, strategy_id, strategy_version,
                    previous_state, new_state, changed_at, changed_by,
                    reason_codes_json, primary_evidence_id,
                    expected_registry_revision, resulting_registry_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transition.transition_id,
                    identity.strategy_id,
                    identity.strategy_version,
                    transition.previous_state,
                    transition.new_state,
                    transition.changed_at,
                    transition.changed_by,
                    json.dumps(list(transition.reason_codes), separators=(",", ":")),
                    transition.primary_evidence_id,
                    transition.expected_registry_revision,
                    transition.resulting_registry_revision,
                ),
            )
            cursor = self._connection.execute(
                """
                UPDATE strategy_versions
                SET current_lifecycle_state = ?, registry_revision = ?
                WHERE strategy_id = ? AND strategy_version = ?
                  AND current_lifecycle_state = ? AND registry_revision = ?
                """,
                (
                    transition.new_state,
                    transition.resulting_registry_revision,
                    identity.strategy_id,
                    identity.strategy_version,
                    transition.previous_state,
                    transition.expected_registry_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflict("lifecycle projection update lost concurrency race")
            self._connection.commit()
            return replace(
                current,
                current_lifecycle_state=transition.new_state,
                registry_revision=transition.resulting_registry_revision,
            )
        except Exception:
            self._connection.rollback()
            raise
