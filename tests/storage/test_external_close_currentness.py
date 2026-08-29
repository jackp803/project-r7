from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage.external_close_currentness import (
    ExternalCloseConflictError,
    open_external_close_currentness_store,
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _fp04_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("ownership_evidence_id", None)
    return "extownrec_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _fp10_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("close_convergence_evidence_id", None)
    return "extcloseconv_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _decision_id(material: dict) -> str:
    return "e5extclose_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


class ExternalCloseCurrentnessPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "external-currentness.sqlite3"
        self.store = open_external_close_currentness_store(self.db_path)
        self.position_id = "position-e6-fp10-001"
        self.provider_identity_ref = "provider-identity-e6-fp10-001"
        self.project_revision = "db20f61cfbd54a1467aba28f30ee33ec23ab7727"
        self._seed_lifecycle(state="EXIT_REQUESTED")

    def tearDown(self) -> None:
        try:
            self.store.close()
        except sqlite3.Error:
            pass
        self.temp.cleanup()

    def _seed_lifecycle(self, *, state: str) -> tuple[dict, dict]:
        projection = {
            "schema_version": "contracts-v0.1",
            "position_id": self.position_id,
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0",
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T08:00:00Z",
            "broker_state_observed_at": "2026-08-29T08:10:00Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": state,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "position_lifecycle_projection_profile_version": "position-lifecycle-projection-v0.1",
            "lifecycle_revision": 0,
            "previous_lifecycle_projection_id": None,
            "lifecycle_projection_kind": "GENESIS",
            "lifecycle_event": None,
            "lifecycle_interpreted_at": "2026-08-29T08:10:01Z",
            "lifecycle_source_broker_state_observed_at": "2026-08-29T08:10:00Z",
        }
        projection["lifecycle_projection_id"] = "posproj_" + hashlib.sha256(
            _json(projection).encode("utf-8")
        ).hexdigest()
        projection_json = _json(projection)
        projection_hash = _sha(projection)
        broker_fact_hash = _sha(
            {
                key: projection[key]
                for key in (
                    "schema_version",
                    "position_id",
                    "symbol",
                    "side",
                    "actual_quantity",
                    "average_entry_price",
                    "opened_at",
                    "broker_state_observed_at",
                    "reconciliation_status",
                    "quantity_profile_version",
                    "quantity_unit",
                    "quantity_asset",
                )
            }
        )
        connection = self.store._connection
        connection.execute(
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
                projection["lifecycle_projection_id"],
                self.position_id,
                0,
                None,
                "GENESIS",
                None,
                state,
                projection["broker_state_observed_at"],
                projection["lifecycle_source_broker_state_observed_at"],
                projection["lifecycle_interpreted_at"],
                broker_fact_hash,
                projection_json,
                projection_hash,
            ),
        )
        connection.execute(
            """
            INSERT INTO paper_position_current_projection (
                position_id, lifecycle_projection_id, lifecycle_revision,
                broker_state_observed_at, payload_hash
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                self.position_id,
                projection["lifecycle_projection_id"],
                0,
                projection["broker_state_observed_at"],
                projection_hash,
            ),
        )
        binding = {
            "schema_version": "contracts-v0.1",
            "lifecycle_execution_binding_profile_version": "position-lifecycle-execution-binding-v0.1",
            "position_id": self.position_id,
            "lifecycle_projection_id": projection["lifecycle_projection_id"],
            "lifecycle_revision": 0,
            "execution_interpreted_at": projection["lifecycle_interpreted_at"],
            "execution_scope": "POSITION_LINKED_REDUCTION_ORDERS_V0_1",
            "order_evidence": [],
            "execution_snapshot_hash": _sha([]),
        }
        binding["lifecycle_execution_binding_id"] = "posexecbind_" + hashlib.sha256(
            _json(binding).encode("utf-8")
        ).hexdigest()
        binding_json = _json(binding)
        binding_hash = _sha(binding)
        connection.execute(
            """
            INSERT INTO paper_position_lifecycle_execution_bindings (
                lifecycle_execution_binding_id, lifecycle_projection_id,
                position_id, lifecycle_revision, execution_interpreted_at,
                execution_scope, execution_snapshot_hash, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                binding["lifecycle_execution_binding_id"],
                projection["lifecycle_projection_id"],
                self.position_id,
                0,
                binding["execution_interpreted_at"],
                binding["execution_scope"],
                binding["execution_snapshot_hash"],
                binding_json,
                binding_hash,
            ),
        )
        connection.commit()
        return projection, binding

    def fp04(
        self,
        *,
        snapshot: str = "provider-position-snapshot-001",
        generation: str = "provider-generation-001",
        supersedes: str | None = None,
    ) -> dict:
        payload = {
            "schema_version": "contracts-v0.1",
            "external_provider_ownership_profile_version": "external-provider-object-ownership-reconciliation-v0.1",
            "provider_object_class": "POSITION_EXPOSURE",
            "provider_identity_ref": self.provider_identity_ref,
            "provider_identity_hash": _sha({"provider": "sanitized-fixture"}),
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_object_ref": "provider-position-object-001",
            "provider_snapshot_ref": snapshot,
            "provider_snapshot_hash": _sha({"snapshot": snapshot}),
            "provider_observation_generation_id": generation,
            "provider_observed_at": "2026-08-29T08:10:00Z",
            "provider_received_at": "2026-08-29T08:10:01Z",
            "current_project_revision": self.project_revision,
            "runtime_preflight_ref": None,
            "runtime_process_instance_id": None,
            "runtime_process_start_generation_id": None,
            "runtime_config_generation_id": None,
            "local_lineage_evidence": [],
            "local_registry_evidence": [],
            "ownership_classification": "KNOWN_OWNED_CURRENT_GENERATION",
            "reconciliation_status": "CURRENT_KNOWN_OWNED",
            "required_dispositions": ["NO_ACTION_CURRENT_KNOWN_OWNED"],
            "reason_codes": ["CURRENT_GENERATION_OWNERSHIP_PROVEN"],
            "adoption_decision_ref": None,
            "supersedes_ownership_evidence_id": supersedes,
            "evaluated_at": "2026-08-29T08:10:04Z" if supersedes is None else "2026-08-29T08:10:05Z",
        }
        payload["ownership_evidence_id"] = _fp04_id(payload)
        return payload

    def fp10(
        self,
        fp04: dict,
        *,
        supersedes: str | None = None,
        generation: str = "provider-generation-001",
        snapshot: str = "provider-position-snapshot-001",
        state: str = "LIFECYCLE_CLOSE_ELIGIBLE",
        ownership_hash_override: str | None = None,
        trade_result_incomplete: bool = False,
    ) -> dict:
        projection_row = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_projections WHERE position_id = ?",
            (self.position_id,),
        ).fetchone()
        binding_row = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE position_id = ?",
            (self.position_id,),
        ).fetchone()
        assert projection_row is not None and binding_row is not None
        projection = json.loads(projection_row["payload_json"])
        fp04_row = {
            "provider_object_class": fp04["provider_object_class"],
            "provider_object_ref": fp04["provider_object_ref"],
            "provider_snapshot_hash": fp04["provider_snapshot_hash"],
            "ownership_evidence_ref": fp04["ownership_evidence_id"],
            "ownership_evidence_hash": ownership_hash_override or _sha(fp04),
            "ownership_classification": fp04["ownership_classification"],
            "ownership_reconciliation_status": fp04["reconciliation_status"],
            "ownership_currentness_status": "CURRENT",
        }
        rows = [fp04_row]
        if state == "LIFECYCLE_CLOSE_ELIGIBLE":
            dispositions = ["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"]
            reasons = ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]
        else:
            dispositions = ["TRADE_RESULT_EVIDENCE_INCOMPLETE"] if trade_result_incomplete else ["BLOCK_NEW_EXPOSURE"]
            reasons = (
                ["TRADE_RESULT_EVIDENCE_INCOMPLETE", "TERMINAL_PROTECTION_CLEAR"]
                if trade_result_incomplete
                else ["TERMINAL_PROTECTION_CLEAR"]
            )
        payload = {
            "schema_version": "contracts-v0.1",
            "external_manual_close_convergence_profile_version": "external-manual-close-lifecycle-convergence-v0.1",
            "position_id": self.position_id,
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_identity_ref": self.provider_identity_ref,
            "provider_identity_hash": fp04["provider_identity_hash"],
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_position_snapshot_ref": snapshot,
            "provider_position_snapshot_hash": _sha({"snapshot": snapshot}),
            "provider_position_observation_generation_id": generation,
            "provider_position_observed_at": "2026-08-29T08:10:00Z",
            "provider_position_received_at": "2026-08-29T08:10:01Z",
            "provider_position_currentness_status": "CURRENT",
            "normalized_position_ref": "normalized-position-e6-fp10-001",
            "normalized_position_hash": _sha({"position": "sanitized-fixture"}),
            "normalized_position_broker_state_observed_at": "2026-08-29T08:10:00Z",
            "normalized_position_reconciliation_status": "CONSISTENT",
            "normalized_actual_quantity": "0",
            "normalized_quantity_profile_version": "base-asset-v0.1",
            "normalized_quantity_unit": "BASE_ASSET",
            "normalized_quantity_asset": "BTC",
            "execution_evidence": [],
            "execution_evidence_set_hash": _sha([]),
            "fp04_ownership_evidence": rows,
            "fp04_evidence_set_hash": _sha(rows),
            "fp05_close_residual_sizing_ref": None,
            "fp05_close_residual_sizing_hash": None,
            "fp05_residual_state": "NOT_APPLICABLE",
            "fp11_prior_registry_evidence_ref": None,
            "fp11_prior_registry_evidence_hash": None,
            "terminal_protection_observation_ref": "terminal-protection-set-e6-fp10-001",
            "terminal_protection_observation_hash": _sha({"terminal": "clear"}),
            "terminal_protection_observed_at": "2026-08-29T08:10:02Z",
            "terminal_protection_received_at": "2026-08-29T08:10:03Z",
            "terminal_protection_status": "TERMINAL_PROTECTION_CLEAR",
            "lifecycle_projection_ref": projection["lifecycle_projection_id"],
            "lifecycle_projection_hash": projection_row["payload_hash"],
            "lifecycle_projection_id": projection["lifecycle_projection_id"],
            "lifecycle_revision": projection["lifecycle_revision"],
            "lifecycle_state": projection["lifecycle_state"],
            "lifecycle_execution_binding_ref": binding_row["lifecycle_execution_binding_id"],
            "lifecycle_execution_binding_hash": binding_row["payload_hash"],
            "lifecycle_execution_snapshot_hash": binding_row["execution_snapshot_hash"],
            "current_project_revision": self.project_revision,
            "runtime_preflight_ref": None,
            "runtime_process_instance_id": None,
            "runtime_process_start_generation_id": None,
            "runtime_config_generation_id": None,
            "exposure_change_origin_classification": "CURRENT_GENERATION_PROJECT",
            "convergence_state": state,
            "required_dispositions": dispositions,
            "reason_codes": reasons,
            "supersedes_close_convergence_evidence_id": supersedes,
            "evaluated_at": "2026-08-29T08:10:04Z" if supersedes is None else "2026-08-29T08:10:06Z",
        }
        payload["close_convergence_evidence_id"] = _fp10_id(payload)
        return payload

    def decision(
        self,
        fp10: dict,
        *,
        next_state: str = "CLOSED",
        close_eligible: bool = True,
        trade_result_incomplete: bool = False,
        evidence_current: bool = True,
    ) -> dict:
        binding_row = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE position_id = ?",
            (self.position_id,),
        ).fetchone()
        assert binding_row is not None
        material = {
            "close_convergence_evidence_id": fp10["close_convergence_evidence_id"],
            "position_id": self.position_id,
            "lifecycle_projection_id": fp10["lifecycle_projection_id"],
            "lifecycle_revision": fp10["lifecycle_revision"],
            "lifecycle_execution_binding_id": binding_row["lifecycle_execution_binding_id"],
            "evidence_current": evidence_current,
            "decision": "CLOSE" if close_eligible else "RECONCILE",
            "event": "POSITION_CLOSED" if close_eligible else "STATE_UNKNOWN",
            "next_state": next_state,
            "reason_codes": ["E5_POSITION_CLOSED_FROM_CURRENT_FP10"] if close_eligible else ["E5_CLOSE_CONVERGENCE_NOT_CURRENT"],
            "close_eligible": close_eligible,
            "trade_result_evidence_incomplete": trade_result_incomplete,
        }
        result = dict(material)
        result["decision_id"] = _decision_id(material)
        return result

    def persist_decision(self, decision: dict, fp10: dict) -> None:
        binding_row = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE position_id = ?",
            (self.position_id,),
        ).fetchone()
        assert binding_row is not None
        self.store.persist_e5_reinterpretation_decision(
            decision,
            position_id=self.position_id,
            close_convergence_evidence_id=fp10["close_convergence_evidence_id"],
            close_convergence_evidence_hash=_sha(fp10),
            lifecycle_projection_ref=fp10["lifecycle_projection_ref"],
            lifecycle_projection_id=fp10["lifecycle_projection_id"],
            lifecycle_revision=fp10["lifecycle_revision"],
            lifecycle_execution_binding_ref=fp10["lifecycle_execution_binding_ref"],
            lifecycle_execution_binding_id=binding_row["lifecycle_execution_binding_id"],
        )

    def test_insert_read_exact_immutable_fp04_and_changed_same_id_rejected(self) -> None:
        evidence = self.fp04()
        first = self.store.persist_fp04(evidence)
        replay = self.store.persist_fp04(evidence)
        self.assertEqual(evidence, first.payload)
        self.assertEqual(first.payload_json, replay.payload_json)
        self.assertEqual((first,), self.store.fp04_history("POSITION_EXPOSURE", self.provider_identity_ref, "provider-position-object-001"))

        changed = dict(evidence)
        changed["provider_snapshot_hash"] = _sha({"snapshot": "forged"})
        with self.assertRaises(ExternalCloseConflictError):
            self.store.persist_fp04(changed)
        self.assertEqual(1, len(self.store.fp04_history("POSITION_EXPOSURE", self.provider_identity_ref, "provider-position-object-001")))

    def test_insert_read_exact_immutable_fp10_and_changed_same_id_rejected(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        evidence = self.fp10(fp04)
        first = self.store.persist_fp10(evidence)
        replay = self.store.persist_fp10(evidence)
        self.assertEqual(evidence, first.payload)
        self.assertEqual(first.payload_json, replay.payload_json)

        changed = dict(evidence)
        changed["terminal_protection_observation_hash"] = _sha({"terminal": "forged"})
        with self.assertRaises(ExternalCloseConflictError):
            self.store.persist_fp10(changed)
        self.assertEqual(1, len(self.store.fp10_history(self.position_id)))

    def test_e5_decision_binds_exact_fp10_and_lifecycle_without_applying_transition(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        fp10 = self.fp10(fp04)
        self.store.persist_fp10(fp10)
        decision = self.decision(fp10)
        self.persist_decision(decision, fp10)

        recovery = self.store.recover_position(self.position_id)
        self.assertEqual("CURRENT", recovery.status)
        self.assertEqual(fp10["close_convergence_evidence_id"], recovery.current_fp10.canonical_id)
        self.assertEqual(decision["decision_id"], recovery.current_decision.canonical_id)
        self.assertEqual("EXIT_REQUESTED", recovery.current_lifecycle_state)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_missing_fp04_dependency_fails_closed(self) -> None:
        fp04 = self.fp04()
        fp10 = self.fp10(fp04)
        self.store.persist_fp10(fp10)
        recovery = self.store.recover_position(self.position_id)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("FP04_DEPENDENCY_MISSING", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_decision_without_persisted_fp10_dependency_fails_closed(self) -> None:
        fp04 = self.fp04()
        fp10 = self.fp10(fp04)
        decision = self.decision(fp10)
        self.persist_decision(decision, fp10)
        recovery = self.store.recover_position(self.position_id)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("FP10_EVIDENCE_MISSING", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_fp10_reference_hash_mismatch_is_conflict(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        fp10 = self.fp10(fp04, ownership_hash_override=_sha({"wrong": "fp04"}))
        self.store.persist_fp10(fp10)
        recovery = self.store.recover_position(self.position_id)
        self.assertEqual("CONFLICT", recovery.status)
        self.assertIn("FP10_FP04_PAYLOAD_HASH_MISMATCH", recovery.reason_codes)

    def test_superseded_fp10_is_historical_and_not_selected_current(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        old = self.fp10(fp04)
        new = self.fp10(
            fp04,
            supersedes=old["close_convergence_evidence_id"],
            generation="provider-generation-002",
            snapshot="provider-position-snapshot-002",
        )
        self.store.persist_fp10(old)
        self.store.persist_fp10(new)
        self.persist_decision(self.decision(new), new)

        recovery = self.store.recover_position(self.position_id)
        self.assertEqual(new["close_convergence_evidence_id"], recovery.current_fp10.canonical_id)
        self.assertEqual(2, len(self.store.fp10_history(self.position_id)))
        self.assertNotEqual(old["close_convergence_evidence_id"], recovery.current_fp10.canonical_id)

    def test_competing_unsuperseded_fp10_heads_fail_closed_independent_of_insert_order(self) -> None:
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "competing.sqlite3"
                    store = open_external_close_currentness_store(path)
                    try:
                        # Reuse exact accepted lifecycle rows from this fixture database.
                        source = self.store._connection
                        for table in (
                            "paper_position_lifecycle_projections",
                            "paper_position_current_projection",
                            "paper_position_lifecycle_execution_bindings",
                        ):
                            rows = source.execute(f"SELECT * FROM {table}").fetchall()
                            columns = [item[1] for item in source.execute(f"PRAGMA table_info({table})").fetchall()]
                            for row in rows:
                                values = [row[column] for column in columns]
                                placeholders = ",".join("?" for _ in columns)
                                store._connection.execute(
                                    f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
                                    values,
                                )
                        store._connection.commit()
                        fp04 = self.fp04()
                        store.persist_fp04(fp04)
                        one = self.fp10(fp04, generation="provider-generation-A", snapshot="provider-position-snapshot-A")
                        two = self.fp10(fp04, generation="provider-generation-B", snapshot="provider-position-snapshot-B")
                        pair = [one, two]
                        if reverse:
                            pair.reverse()
                        for evidence in pair:
                            store.persist_fp10(evidence)
                        recovery = store.recover_position(self.position_id)
                        self.assertEqual("CONFLICT", recovery.status)
                        self.assertIn("FP10_COMPETING_UNSUPERSEDED_HEADS", recovery.reason_codes)
                        self.assertIsNone(recovery.current_fp10)
                    finally:
                        store.close()

    def test_restart_preserves_history_and_reconstructs_same_current_projection(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        fp10 = self.fp10(fp04)
        self.store.persist_fp10(fp10)
        decision = self.decision(fp10)
        self.persist_decision(decision, fp10)
        before = self.store.recover_position(self.position_id)
        history_before = self.store.fp10_history(self.position_id)
        self.store.close()

        self.store = open_external_close_currentness_store(self.db_path)
        after = self.store.recover_position(self.position_id)
        self.assertEqual(before.status, after.status)
        self.assertEqual(before.reason_codes, after.reason_codes)
        self.assertEqual(before.current_fp10.payload_json, after.current_fp10.payload_json)
        self.assertEqual(before.current_decision.payload_json, after.current_decision.payload_json)
        self.assertEqual(history_before, self.store.fp10_history(self.position_id))

    def test_historical_close_eligible_row_alone_never_implies_current_closed(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        fp10 = self.fp10(fp04)
        self.store.persist_fp10(fp10)
        recovery = self.store.recover_position(self.position_id)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertEqual("EXIT_REQUESTED", recovery.current_lifecycle_state)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_old_decision_for_superseded_fp10_does_not_display_false_green(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        old = self.fp10(fp04)
        self.store.persist_fp10(old)
        self.persist_decision(self.decision(old), old)
        newer = self.fp10(
            fp04,
            supersedes=old["close_convergence_evidence_id"],
            generation="provider-generation-newer",
            snapshot="provider-position-snapshot-newer",
        )
        self.store.persist_fp10(newer)

        recovery = self.store.recover_position(self.position_id)
        self.assertEqual(newer["close_convergence_evidence_id"], recovery.current_fp10.canonical_id)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("CURRENT_E5_REINTERPRETATION_DECISION_MISSING", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_trade_result_evidence_incomplete_flag_remains_auditable(self) -> None:
        fp04 = self.fp04()
        self.store.persist_fp04(fp04)
        fp10 = self.fp10(
            fp04,
            state="FLAT_PROVIDER_TRUTH_PROVEN",
            trade_result_incomplete=True,
        )
        self.store.persist_fp10(fp10)
        decision = self.decision(
            fp10,
            next_state="RECONCILIATION_REQUIRED",
            close_eligible=False,
            trade_result_incomplete=True,
        )
        self.persist_decision(decision, fp10)
        recovery = self.store.recover_position(self.position_id)
        self.assertTrue(recovery.trade_result_evidence_incomplete)
        self.assertFalse(recovery.closed_presentation_allowed)
        self.assertEqual(True, recovery.current_decision.payload["trade_result_evidence_incomplete"])

    def test_migration_is_additive_and_idempotent_and_store_has_no_provider_runtime_surface(self) -> None:
        self.store.close()
        self.store = open_external_close_currentness_store(self.db_path)
        self.store.close()
        verify = sqlite3.connect(self.db_path)
        try:
            migrations = [
                row[0]
                for row in verify.execute(
                    "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
                ).fetchall()
            ]
            expected = sorted(path.name for path in Path("src/storage/migrations").glob("*.sql"))
            self.assertEqual(expected, migrations)
            self.assertIn("0005_external_close_currentness.sql", migrations)
        finally:
            verify.close()
        self.store = open_external_close_currentness_store(self.db_path)
        for forbidden in ("request", "send", "submit", "cancel", "amend", "close_position", "credentials"):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(hasattr(self.store, forbidden))


if __name__ == "__main__":
    unittest.main()
