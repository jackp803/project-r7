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
    EvidenceGateError,
    IntakeReceipt,
    IntakeOutcome,
    InvalidTransition,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
    is_canonical_lifecycle_transition_allowed,
)

_MIGRATIONS_DIR = Path(__file__).with_name("migrations")


class _WriterCapability:
    """Module-private construction capability for authoritative SQLite writers."""

    __slots__ = ()


_WRITER_CAPABILITY = _WriterCapability()


def _connect(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _apply_migrations(
    connection: sqlite3.Connection,
    migrations_dir: str | Path | None = None,
) -> None:
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
        rebuilding=script.startswith('-- r7-migration-transaction: foreign-key-rebuild')
        atomic=rebuilding or script.startswith('-- r7-migration-transaction: atomic')
        if atomic and connection.in_transaction: raise EvidenceGateError('Atomic schema migration requires an idle connection')
        try:
            if rebuilding:
                connection.execute('PRAGMA foreign_keys=OFF')
            if atomic: connection.executescript('BEGIN IMMEDIATE;\n'+script)
            else: connection.executescript(script)
            if rebuilding:
                if connection.execute('PRAGMA foreign_key_check').fetchone() is not None:
                    raise sqlite3.IntegrityError('Registry schema rebuild failed foreign-key verification')
            connection.execute("INSERT INTO schema_migrations(migration_name) VALUES (?)",(migration.name,))
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            if rebuilding: connection.execute('PRAGMA foreign_keys=ON')


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


class _SQLiteRegistryStore:
    """Internal authoritative SQLite Registry writer/read model.

    This is deliberately not exported from ``storage``. Construction requires the
    module-private writer capability owned by the E6 composition path. The capability
    is a trusted-process API boundary, not a hostile-code security sandbox.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        _writer_capability: object | None = None,
    ) -> None:
        if _writer_capability is not _WRITER_CAPABILITY:
            raise PermissionError(
                "authoritative SQLiteRegistryStore construction is internal to the E6 platform factory"
            )
        self._connection = connection
        self._writer_capability = _writer_capability
        self._atomic_intake_active = False
        self._atomic_lifecycle_active = False

    def close(self):
        self._connection.close()

    def get_research_namespace(self):
        exists=self._connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='registry_research_namespace'").fetchone()
        if not exists: return None
        row=self._connection.execute('SELECT namespace FROM registry_research_namespace WHERE singleton=1').fetchone()
        return None if row is None else row['namespace']

    def product_assessment_for_decision(self,decision_id):
        row=self._connection.execute('SELECT * FROM product_assessments WHERE validation_evidence_id=?',(decision_id,)).fetchone()
        return self._product_from_row(row)

    @staticmethod
    def _product_from_row(row):
        from registry.product_assessment import ProductAssessmentRecord
        if row is None: return None
        values=dict(row)
        values['identity']=StrategyIdentity(values.pop('strategy_id'),values.pop('strategy_version'))
        return ProductAssessmentRecord(**values)

    def get_product_assessment(self,run_id):
        return self._product_from_row(self._connection.execute('SELECT * FROM product_assessments WHERE run_id=?',(run_id,)).fetchone())

    def product_assessment_by_id(self,assessment_id):
        return self._product_from_row(self._connection.execute('SELECT * FROM product_assessments WHERE assessment_id=?',(assessment_id,)).fetchone())

    def _save_product_assessment(self,record,*,capability):
        from dataclasses import asdict
        from registry.product_assessment import _PRODUCT_EVIDENCE_CAPABILITY,ProductAssessmentRecord
        self._require_writer_capability()
        if capability is not _PRODUCT_EVIDENCE_CAPABILITY or not isinstance(record,ProductAssessmentRecord):
            raise EvidenceGateError('Trusted E6 product evidence writer required')
        with self._connection:
            self._connection.execute('BEGIN IMMEDIATE')
            existing=self.get_product_assessment(record.run_id)
            if existing is not None:
                if replace(record,recorded_at=existing.recorded_at)!=existing:
                    raise EvidenceGateError('Immutable product evidence conflict')
                return existing
            values=asdict(record); values.pop('identity')
            values.update(strategy_id=record.identity.strategy_id,strategy_version=record.identity.strategy_version)
            columns=tuple(values)
            self._connection.execute('INSERT INTO product_assessments('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',tuple(values.values()))
            return record

    def candidate_product_assessment(self,identity):
        row=self._connection.execute("SELECT primary_evidence_id FROM lifecycle_transitions WHERE strategy_id=? AND strategy_version=? AND new_state='CANDIDATE' ORDER BY resulting_registry_revision DESC LIMIT 1",
            (identity.strategy_id,identity.strategy_version)).fetchone()
        return None if row is None else self.product_assessment_for_decision(row['primary_evidence_id'])

    def ready_forward_evidence(self,identity):
        row=self._connection.execute("SELECT owner_evidence_id FROM lifecycle_transitions WHERE strategy_id=? AND strategy_version=? AND new_state='READY_FOR_APPROVAL' ORDER BY resulting_registry_revision DESC LIMIT 1",
            (identity.strategy_id,identity.strategy_version)).fetchone()
        return None if row is None else self.get_owner_evidence(row['owner_evidence_id'])

    def accepted_paper_start_evidence(self,identity):
        row=self._connection.execute("SELECT owner_evidence_id FROM lifecycle_transitions WHERE strategy_id=? AND strategy_version=? AND new_state='PAPER' ORDER BY resulting_registry_revision DESC LIMIT 1",
            (identity.strategy_id,identity.strategy_version)).fetchone()
        return None if row is None else self.get_owner_evidence(row['owner_evidence_id'])

    @staticmethod
    def _owner_from_row(row,record_type):
        if row is None: return None
        values=dict(row); values['identity']=StrategyIdentity(values.pop('strategy_id'),values.pop('strategy_version'))
        return record_type(**values)

    def get_owner_evidence(self,evidence_id):
        from registry.operational_authority import OwnerGateRecord
        return self._owner_from_row(self._connection.execute('SELECT * FROM lifecycle_owner_evidence WHERE evidence_id=?',(evidence_id,)).fetchone(),OwnerGateRecord)

    def get_human_approval(self,approval_id):
        from registry.operational_authority import HumanApprovalRecord
        return self._owner_from_row(self._connection.execute('SELECT * FROM human_approvals WHERE approval_record_id=?',(approval_id,)).fetchone(),HumanApprovalRecord)

    def human_approval_for_command(self,command_id):
        from registry.operational_authority import HumanApprovalRecord
        row=self._connection.execute('SELECT * FROM human_approvals WHERE command_id=?',(command_id,)).fetchone()
        return self._owner_from_row(row,HumanApprovalRecord)

    def latest_human_approval(self,identity):
        from registry.operational_authority import HumanApprovalRecord
        row=self._connection.execute('SELECT * FROM human_approvals WHERE strategy_id=? AND strategy_version=? ORDER BY rowid DESC LIMIT 1',
            (identity.strategy_id,identity.strategy_version)).fetchone()
        return self._owner_from_row(row,HumanApprovalRecord)

    def approval_is_revoked(self,approval_id):
        return self._connection.execute('SELECT 1 FROM approval_revocations WHERE approval_record_id=?',(approval_id,)).fetchone() is not None

    def _save_owner_record(self,record,*,capability):
        from dataclasses import asdict
        from registry.operational_authority import _OWNER_EVIDENCE_CAPABILITY,OwnerGateRecord,HumanApprovalRecord
        self._require_writer_capability()
        if capability is not _OWNER_EVIDENCE_CAPABILITY or not isinstance(record,(OwnerGateRecord,HumanApprovalRecord)):
            raise EvidenceGateError('Trusted E6 owner evidence writer required')
        table='lifecycle_owner_evidence' if isinstance(record,OwnerGateRecord) else 'human_approvals'
        owns_transaction=not self._atomic_lifecycle_active
        try:
            if owns_transaction: self._connection.execute('BEGIN IMMEDIATE')
            row=self._connection.execute('SELECT * FROM '+table+' WHERE command_id=?',(record.command_id,)).fetchone()
            if row is not None:
                existing=self._owner_from_row(row,type(record))
                if existing!=record: raise EvidenceGateError('Immutable owner command identity conflict')
                if owns_transaction: self._connection.commit()
                return existing
            values=asdict(record); values.pop('identity')
            values.update(strategy_id=record.identity.strategy_id,strategy_version=record.identity.strategy_version)
            self._connection.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
            if owns_transaction: self._connection.commit()
            return record
        except BaseException:
            self._connection.rollback(); raise

    def lookup_lifecycle_command(self,command_id,request_json):
        from registry.product_assessment import digest
        row=self._connection.execute('SELECT * FROM lifecycle_command_receipts WHERE command_id=?',(command_id,)).fetchone()
        if row is None: return None
        if row['request_json']!=request_json or digest(request_json)!=row['request_hash']:
            raise EvidenceGateError('Lifecycle command identity conflict')
        if digest(row['output_json'])!=row['output_hash']: raise EvidenceGateError('Lifecycle receipt commitment mismatch')
        values=json.loads(row['output_json']); values['identity']=StrategyIdentity(**values['identity'])
        return StrategyVersionRecord(**values)

    def run_lifecycle_once(self,command_id,request_json,perform):
        """Short E6 write-only closure; owner production must precede this lock."""
        from dataclasses import asdict
        from registry.product_assessment import canonical,digest
        self._require_writer_capability()
        if self._connection.in_transaction or self._atomic_lifecycle_active: raise ConcurrencyConflict('Lifecycle transaction already active')
        self._connection.execute('BEGIN IMMEDIATE'); self._atomic_lifecycle_active=True
        try:
            existing=self.lookup_lifecycle_command(command_id,request_json)
            if existing is not None:
                self._connection.commit(); return existing
            result=perform()
            row=self._connection.execute('SELECT transition_id,changed_at FROM lifecycle_transitions WHERE strategy_id=? AND strategy_version=? AND resulting_registry_revision=?',
                (result.identity.strategy_id,result.identity.strategy_version,result.registry_revision)).fetchone()
            if row is None: raise EvidenceGateError('Lifecycle command has no owner transition')
            raw=canonical(asdict(result))
            self._connection.execute('INSERT INTO lifecycle_command_receipts VALUES(?,?,?,?,?,?,?)',
                (command_id,request_json,digest(request_json),raw,digest(raw),row['transition_id'],row['changed_at']))
            self._connection.commit(); return result
        except BaseException:
            self._connection.rollback(); raise
        finally: self._atomic_lifecycle_active=False

    def _revoke_approval(self,approval_id,*,actor,reason,command_id,recorded_at,capability):
        from registry.operational_authority import _OWNER_EVIDENCE_CAPABILITY
        from registry.product_assessment import digest,canonical
        if capability is not _OWNER_EVIDENCE_CAPABILITY: raise EvidenceGateError('Authenticated revocation writer required')
        values=('revoke-'+digest(canonical([approval_id,actor,reason,command_id]))[7:],approval_id,actor,reason,command_id,recorded_at)
        with self._connection:
            self._connection.execute('BEGIN IMMEDIATE')
            existing=self._connection.execute('SELECT * FROM approval_revocations WHERE command_id=?',(command_id,)).fetchone()
            if existing is not None:
                if tuple(existing)[:-1]!=values[:-1]: raise EvidenceGateError('Revocation command identity conflict')
                return existing['revocation_id']
            self._connection.execute('INSERT INTO approval_revocations VALUES(?,?,?,?,?,?)',values)
        return values[0]

    def bind_research_namespace(self,namespace):
        self._require_writer_capability()
        if namespace not in ('FIXTURE','LOCAL_RESEARCH'): raise EvidenceGateError('Invalid research namespace')
        with self._connection:
            self._connection.execute('BEGIN IMMEDIATE')
            self._connection.execute('CREATE TABLE IF NOT EXISTS registry_research_namespace(singleton INTEGER PRIMARY KEY CHECK(singleton=1), namespace TEXT NOT NULL)')
            row=self._connection.execute('SELECT namespace FROM registry_research_namespace WHERE singleton=1').fetchone()
            if row is None:
                if self._connection.execute('SELECT COUNT(*) FROM strategy_versions').fetchone()[0]:
                    raise EvidenceGateError('Existing unclassified registry requires explicit namespace migration')
                self._connection.execute('INSERT INTO registry_research_namespace VALUES(1,?)',(namespace,))
                self._connection.execute("CREATE TRIGGER registry_research_namespace_immutable BEFORE UPDATE ON registry_research_namespace BEGIN SELECT RAISE(ABORT,'registry namespace is immutable'); END")
                self._connection.execute("CREATE TRIGGER registry_research_namespace_no_delete BEFORE DELETE ON registry_research_namespace BEGIN SELECT RAISE(ABORT,'registry namespace cannot be deleted'); END")
            elif row['namespace']!=namespace: raise EvidenceGateError('Fixture and real research registry namespaces cannot mix')

    def _commit_intake_write(self):
        if not self._atomic_intake_active:
            self._connection.commit()

    def run_intake_once(self, operation_id, payload_hash, actor, perform):
        self._require_writer_capability()
        if self._connection.in_transaction or self._atomic_intake_active:
            raise ConcurrencyConflict("Intake transaction already active")
        self._connection.execute("BEGIN IMMEDIATE")
        self._atomic_intake_active = True
        try:
            operation = self._connection.execute(
                "SELECT * FROM strategy_intake_operations WHERE operation_id = ?", (operation_id,)
            ).fetchone()
            if operation is not None:
                if operation["payload_hash"] != payload_hash or operation["source_actor"] != actor:
                    raise IdentityConflict("Intake operation has different immutable content or actor")
                row = self._connection.execute(
                    "SELECT * FROM strategy_intake_receipts WHERE intake_id = ?", (operation["intake_id"],)
                ).fetchone()
                receipt = IntakeReceipt(row["intake_id"], StrategyIdentity(row["strategy_id"], row["strategy_version"]),
                                        row["payload_hash"], row["received_at"], row["source_actor"],
                                        row["result_status"], row["compatibility_id"])
                compatibility = _compatibility_from_row(self._connection.execute(
                    "SELECT * FROM compatibility_evidence WHERE compatibility_id = ?", (receipt.compatibility_id,)
                ).fetchone())
                result = IntakeOutcome(self.get_strategy(receipt.identity), receipt, compatibility)
            else:
                result = perform()
                self._connection.execute(
                    "INSERT INTO strategy_intake_operations(operation_id,payload_hash,source_actor,intake_id) VALUES (?,?,?,?)",
                    (operation_id, payload_hash, actor, result.receipt.intake_id),
                )
            self._connection.commit()
            return result
        except BaseException:
            self._connection.rollback()
            raise
        finally:
            self._atomic_intake_active = False

    def _require_writer_capability(self) -> None:
        if self._writer_capability is not _WRITER_CAPABILITY:
            raise PermissionError("authoritative SQLite writer capability is not present")

    def register_strategy(self, record: StrategyVersionRecord) -> tuple[StrategyVersionRecord, bool]:
        self._require_writer_capability()
        if record.current_lifecycle_state != "DRAFT" or record.registry_revision != 0:
            raise InvalidTransition(
                "new strategy registration requires current_lifecycle_state=DRAFT and registry_revision=0"
            )

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
        self._commit_intake_write()
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

    def list_strategies(self, *, limit, offset):
        rows = self._connection.execute(
            'SELECT * FROM strategy_versions ORDER BY registered_at,strategy_id,strategy_version LIMIT ? OFFSET ?',
            (limit, offset),
        ).fetchall()
        return tuple(_strategy_from_row(row) for row in rows)

    def list_paper_identities(self, *, limit, offset):
        rows=self._connection.execute(
            "SELECT DISTINCT s.strategy_id,s.strategy_version,s.registered_at FROM strategy_versions s "
            "JOIN lifecycle_transitions t ON t.strategy_id=s.strategy_id AND t.strategy_version=s.strategy_version "
            "WHERE t.new_state='PAPER' ORDER BY s.registered_at,s.strategy_id,s.strategy_version LIMIT ? OFFSET ?",
            (limit,offset),
        ).fetchall()
        return tuple((row[0],row[1]) for row in rows)

    def lifecycle_counts(self):
        return dict(self._connection.execute(
            'SELECT current_lifecycle_state,COUNT(*) FROM strategy_versions GROUP BY current_lifecycle_state'
        ).fetchall())

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
        self._require_writer_capability()
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
        self._commit_intake_write()

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
        self._require_writer_capability()
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
        self._commit_intake_write()

    def save_validation_evidence(self, evidence: ValidationEvidenceRecord) -> ValidationEvidenceRecord:
        self._require_writer_capability()
        try:
            self._connection.execute('BEGIN IMMEDIATE')
            row=self._connection.execute('SELECT * FROM validation_evidence WHERE evidence_type=? AND upstream_object_id=?',
                                         (evidence.evidence_type,evidence.upstream_object_id)).fetchone()
            if row is not None:
                original=_validation_from_row(row)
                compared=replace(evidence,evidence_id=original.evidence_id,recorded_at=original.recorded_at)
                if compared!=original:
                    raise EvidenceGateError('Immutable upstream evidence content or verification binding changed')
                self._connection.commit()
                return original
            self._insert_validation_evidence(evidence)
            self._connection.commit()
            return evidence
        except BaseException:
            self._connection.rollback()
            raise

    def _insert_validation_evidence(self,evidence: ValidationEvidenceRecord) -> None:
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
        self._require_writer_capability()
        if not is_canonical_lifecycle_transition_allowed(
            transition.previous_state, transition.new_state
        ):
            raise InvalidTransition(
                "canonical persistence does not allow lifecycle transition "
                f"{transition.previous_state} -> {transition.new_state}"
            )

        identity = transition.identity
        try:
            if not self._atomic_lifecycle_active: self._connection.execute("BEGIN IMMEDIATE")
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
                    expected_registry_revision, resulting_registry_revision, owner_evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    transition.owner_evidence_id,
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
            if not self._atomic_lifecycle_active: self._connection.commit()
            return replace(
                current,
                current_lifecycle_state=transition.new_state,
                registry_revision=transition.resulting_registry_revision,
            )
        except Exception:
            self._connection.rollback()
            raise


def _open_authorized_store(path: str | Path) -> _SQLiteRegistryStore:
    """Factory-only production composition primitive; never return the raw connection."""

    connection = _connect(path)
    try:
        _apply_migrations(connection)
        return _SQLiteRegistryStore(connection, _writer_capability=_WRITER_CAPABILITY)
    except BaseException:
        connection.close()
        raise


def _internal_store_for_tests(connection: sqlite3.Connection) -> _SQLiteRegistryStore:
    """Explicit internal/test-only helper for storage-mechanics definitions."""

    return _SQLiteRegistryStore(connection, _writer_capability=_WRITER_CAPABILITY)
