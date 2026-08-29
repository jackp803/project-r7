from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from position import interpret_protection_registry_evidence
from src.execution.protection_registry_evidence_boundary import (
    build_protection_registry_multiplicity_evidence,
)
from storage._lifecycle_execution_binding import persist_lifecycle_execution_binding
from storage._paper_runtime import _open_paper_runtime_store
from storage.external_close_currentness import open_external_close_currentness_store
from storage.protection_registry_currentness import (
    HEALTHY_UNIQUE_PROTECTION,
    STATUS_CONFLICT,
    STATUS_INCOMPLETE,
    STATUS_RECONCILIATION_REQUIRED,
    STATUS_STALE,
    STATUS_UNKNOWN,
    ProtectionRegistryConflictError,
    ProtectionRegistryCurrentAuthority,
    open_protection_registry_currentness_store,
)
import tests.position.test_protection_registry_policy as policy_fixture_module


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _fp11_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("protection_registry_evidence_id", None)
    return "protregmul_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _lineage_hash(lineage: dict) -> str:
    return _sha(lineage)


class ProtectionRegistryCurrentnessPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "fp11-currentness.sqlite3"
        self.store = None
        self.persisted_projection_hash = None
        self.fixture = policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        if self.store is not None:
            try:
                self.store.close()
            except sqlite3.Error:
                pass
        self.temp.cleanup()

    def _owner_case(
        self,
        kind: str = "success",
        *,
        quantity: str = "0.0012",
        lifecycle: str = "OPEN_PROTECTED",
        coverage: str = "COMPLETE",
        currentness: str = "CURRENT",
        evaluated_at=None,
    ):
        return self.fixture._build(
            kind,
            quantity=quantity,
            lifecycle=lifecycle,
            coverage=coverage,
            currentness=currentness,
            evaluated_at=evaluated_at,
        )

    @staticmethod
    def _current_authority(evidence: dict, owner_authority) -> ProtectionRegistryCurrentAuthority:
        return ProtectionRegistryCurrentAuthority(
            position_ref=owner_authority.position_ref,
            position=owner_authority.position,
            intended_protection_lineage=evidence["intended_protection_lineage"],
            lifecycle_projection=owner_authority.lifecycle_projection,
            lifecycle_execution_binding=owner_authority.lifecycle_execution_binding,
            provider_identity_ref=owner_authority.provider_identity_ref,
            provider_instrument_ref=owner_authority.provider_instrument_ref,
            provider_observation_generation_id=owner_authority.provider_observation_generation_id,
            provider_observed_at=owner_authority.provider_observed_at,
            provider_received_at=owner_authority.provider_received_at,
            observed_active_protection_set_hash=owner_authority.observed_active_protection_set_hash,
            runtime_preflight_ref=owner_authority.runtime_preflight_ref,
            runtime_process_instance_id=owner_authority.runtime_process_instance_id,
            runtime_process_start_generation_id=owner_authority.runtime_process_start_generation_id,
            runtime_config_generation_id=owner_authority.runtime_config_generation_id,
        )

    def _persist_fp04_dependencies(self, value) -> None:
        bootstrap = open_external_close_currentness_store(self.db_path)
        try:
            for dependency in value.fp04_dependencies:
                bootstrap.persist_fp04(dependency.evidence)
        finally:
            bootstrap.close()

    def _seed_lifecycle(self, owner_authority) -> None:
        projection = dict(owner_authority.lifecycle_projection)
        binding = None if owner_authority.lifecycle_execution_binding is None else dict(owner_authority.lifecycle_execution_binding)
        runtime_store = _open_paper_runtime_store(self.db_path)
        try:
            stored_projection = runtime_store.persist_position_projection(projection)
            self.persisted_projection_hash = stored_projection.payload_hash
            if binding is not None:
                persist_lifecycle_execution_binding(runtime_store, binding)
        finally:
            runtime_store.close()

    def _setup_case(self, kind: str = "success", **kwargs):
        evidence, owner_authority, value = self._owner_case(kind, **kwargs)
        self._persist_fp04_dependencies(value)
        self._seed_lifecycle(owner_authority)
        self.store = open_protection_registry_currentness_store(self.db_path)
        authority = self._current_authority(evidence, owner_authority)
        return evidence, owner_authority, value, authority

    def _persist_decision(self, evidence: dict, owner_authority, authority):
        decision = interpret_protection_registry_evidence(evidence, owner_authority)
        return self.store.persist_e5_interpretation(decision, evidence=evidence, authority=authority)

    def _persist_healthy_chain(self):
        evidence, owner_authority, value, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        self._persist_decision(evidence, owner_authority, authority)
        return evidence, owner_authority, value, authority

    def test_normal_paper_runtime_writer_projection_is_accepted_by_fp11_restart_currentness(self):
        _, _, _, authority = self._persist_healthy_chain()
        current = self.store._connection.execute(
            "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
            (authority.position["position_id"],),
        ).fetchone()
        history = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
            (authority.lifecycle_projection["lifecycle_projection_id"],),
        ).fetchone()
        self.assertIsNotNone(current)
        self.assertIsNotNone(history)
        self.assertEqual(self.persisted_projection_hash, current["payload_hash"])
        self.assertEqual(self.persisted_projection_hash, history["payload_hash"])
        self.assertEqual(_json(authority.lifecycle_projection), history["payload_json"])
        result = self.store.recover(authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, result.status)
        self.assertTrue(result.healthy_protection)

    def test_lifecycle_projection_payload_hash_is_checked_in_its_own_storage_domain(self):
        evidence, owner_authority, _, authority = self._persist_healthy_chain()
        interpretation = self.store.interpretation_history(evidence["position_id"])[0]
        self.assertEqual(evidence["position_hash"], interpretation.payload["position_hash"])
        self.assertEqual(_sha(authority.position), evidence["position_hash"])
        current = self.store._connection.execute(
            "SELECT payload_hash FROM paper_position_current_projection WHERE position_id = ?",
            (evidence["position_id"],),
        ).fetchone()
        self.assertEqual(_sha(authority.lifecycle_projection), current["payload_hash"])
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, self.store.recover(authority).status)

    def test_corrupted_current_projection_payload_hash_fails_closed(self):
        _, _, _, authority = self._persist_healthy_chain()
        self.store._connection.execute(
            "UPDATE paper_position_current_projection SET payload_hash = ? WHERE position_id = ?",
            (_sha({"corrupt": "current-projection-hash"}), authority.position["position_id"]),
        )
        self.store._connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_STALE, result.status)
        self.assertIn("CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_corrupted_durable_projection_payload_hash_fails_closed(self):
        _, _, _, authority = self._persist_healthy_chain()
        self.store._connection.execute("DROP TRIGGER paper_position_projection_immutable_update")
        self.store._connection.execute(
            "UPDATE paper_position_lifecycle_projections SET payload_hash = ? WHERE lifecycle_projection_id = ?",
            (_sha({"corrupt": "history-projection-hash"}), authority.lifecycle_projection["lifecycle_projection_id"]),
        )
        self.store._connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_LIFECYCLE_PROJECTION_HASH_MISMATCH", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_corrupted_durable_projection_payload_json_fails_closed(self):
        _, _, _, authority = self._persist_healthy_chain()
        self.store._connection.execute("DROP TRIGGER paper_position_projection_immutable_update")
        self.store._connection.execute(
            "UPDATE paper_position_lifecycle_projections SET payload_json = ? WHERE lifecycle_projection_id = ?",
            (_json({"corrupt": "history-projection-json"}), authority.lifecycle_projection["lifecycle_projection_id"]),
        )
        self.store._connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_LIFECYCLE_PROJECTION_PAYLOAD_MISMATCH", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_current_projection_id_revision_or_broker_anchor_mismatch_fails_closed(self):
        mutations = (
            ("lifecycle_projection_id", "posproj_" + "0" * 64),
            ("lifecycle_revision", 999),
            ("broker_state_observed_at", "2026-08-29T23:59:59Z"),
        )
        for index, (column, bad_value) in enumerate(mutations):
            with self.subTest(column=column):
                if self.store is not None:
                    self.store.close()
                self.db_path = Path(self.temp.name) / f"fp11-current-index-{index}.sqlite3"
                self.store = None
                _, _, _, authority = self._persist_healthy_chain()
                if column == "lifecycle_projection_id":
                    self.store._connection.execute("PRAGMA foreign_keys = OFF")
                self.store._connection.execute(
                    f"UPDATE paper_position_current_projection SET {column} = ? WHERE position_id = ?",
                    (bad_value, authority.position["position_id"]),
                )
                self.store._connection.commit()
                result = self.store.recover(authority)
                self.assertEqual(STATUS_STALE, result.status)
                self.assertIn("CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED", result.reason_codes)
                self.assertFalse(result.healthy_protection)

    def test_canonical_position_hash_mismatch_independently_invalidates_fp11_currentness(self):
        evidence, _, _, authority = self._persist_healthy_chain()
        changed_position = dict(authority.position)
        changed_position["actual_quantity"] = "0.0011"
        result = self.store.recover(replace(authority, position=changed_position))
        self.assertEqual(STATUS_STALE, result.status)
        self.assertIn("FP11_CURRENT_AUTHORITY_MISMATCH", result.reason_codes)
        self.assertNotEqual(_sha(changed_position), evidence["position_hash"])
        self.assertFalse(result.healthy_protection)

    def test_immutable_insert_read_and_restart_reloads_exact_fp11_history(self):
        evidence, _, _, authority = self._setup_case()
        stored = self.store.persist_fp11(evidence)
        action_id = evidence["intended_protection_lineage"]["position_action_id"]
        before = self.store.fp11_history(evidence["position_id"], action_id)
        self.assertEqual(stored.payload_json, before[0].payload_json)
        self.store.close()
        self.store = open_protection_registry_currentness_store(self.db_path)
        after = self.store.fp11_history(evidence["position_id"], action_id)
        self.assertEqual(before, after)
        self.assertEqual(evidence, after[0].payload)
        self.assertEqual(STATUS_INCOMPLETE, self.store.recover(authority).status)

    def test_sql_update_and_delete_of_immutable_fp11_rows_are_rejected(self):
        evidence, _, _, _ = self._setup_case()
        self.store.persist_fp11(evidence)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "UPDATE protection_registry_multiplicity_evidence SET registry_status='UNKNOWN' WHERE protection_registry_evidence_id = ?",
                (evidence["protection_registry_evidence_id"],),
            )
        self.store._connection.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "DELETE FROM protection_registry_multiplicity_evidence WHERE protection_registry_evidence_id = ?",
                (evidence["protection_registry_evidence_id"],),
            )
        self.store._connection.rollback()

    def test_duplicate_fp11_id_with_changed_content_is_durable_conflict(self):
        evidence, _, _, _ = self._setup_case()
        self.store.persist_fp11(evidence)
        changed = dict(evidence)
        changed["evaluated_at"] = "2026-08-29T09:59:59Z"
        with self.assertRaises(ProtectionRegistryConflictError):
            self.store.persist_fp11(changed)

    def test_explicit_same_lineage_supersession_selects_only_declared_head(self):
        first, _, _, _ = self._setup_case()
        self.store.persist_fp11(first)
        _, second_owner, second_value = self._owner_case("multiple")
        self._persist_fp04_dependencies(second_value)
        second = build_protection_registry_multiplicity_evidence(
            second_value,
            supersedes_evidence=first,
        )
        self.store.persist_fp11(second)
        second_authority = self._current_authority(second, second_owner)
        projection = self.store.recover(second_authority)
        self.assertIsNotNone(projection.current_fp11)
        self.assertEqual(second["protection_registry_evidence_id"], projection.current_fp11.canonical_id)
        self.assertNotEqual(HEALTHY_UNIQUE_PROTECTION, projection.status)

    def test_timestamp_only_new_row_without_supersession_never_replaces_authority(self):
        first, _, value, authority = self._setup_case()
        self.store.persist_fp11(first)
        later_value = replace(value, evaluated_at=value.evaluated_at + timedelta(minutes=5))
        timestamp_only = build_protection_registry_multiplicity_evidence(later_value)
        self.store.persist_fp11(timestamp_only)
        result = self.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_COMPETING_UNSUPERSEDED_HEADS", result.reason_codes)

    def test_two_materially_different_unsuperseded_heads_fail_closed(self):
        first, _, _, authority = self._setup_case()
        self.store.persist_fp11(first)
        second, _, second_value = self._owner_case("multiple")
        self._persist_fp04_dependencies(second_value)
        self.store.persist_fp11(second)
        result = self.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertFalse(result.healthy_protection)

    def test_missing_predecessor_is_incomplete_not_current(self):
        first, _, _, _ = self._setup_case()
        _, second_owner, second_value = self._owner_case("multiple")
        self._persist_fp04_dependencies(second_value)
        second = build_protection_registry_multiplicity_evidence(
            second_value,
            supersedes_evidence=first,
        )
        self.store.persist_fp11(second)
        result = self.store.recover(self._current_authority(second, second_owner))
        self.assertEqual(STATUS_INCOMPLETE, result.status)
        self.assertIn("FP11_SUPERSESSION_PREDECESSOR_MISSING", result.reason_codes)

    def test_cross_lineage_supersession_is_conflict(self):
        first, _, _, _ = self._setup_case()
        self.store.persist_fp11(first)
        cross = json.loads(_json(first))
        lineage = dict(cross["intended_protection_lineage"])
        lineage["position_action_id"] = "position-action-different-lineage"
        lineage["position_action_ref"] = "position-action-ref-different-lineage"
        lineage["position_action_hash"] = _sha({"different": "position-action"})
        cross["intended_protection_lineage"] = lineage
        cross["intended_protection_lineage_hash"] = _lineage_hash(lineage)
        cross["supersedes_registry_evidence_id"] = first["protection_registry_evidence_id"]
        cross["evaluated_at"] = "2026-08-29T09:30:00Z"
        cross["protection_registry_evidence_id"] = _fp11_id(cross)
        self.store.persist_fp11(cross)
        cross_authority = replace(
            self._current_authority(first, self._owner_case()[1]),
            intended_protection_lineage=lineage,
        )
        result = self.store.recover(cross_authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_SUPERSESSION_LINEAGE_MISMATCH", result.reason_codes)

    def test_storage_cycle_or_supersession_reference_corruption_fails_closed(self):
        first, _, _, authority = self._setup_case()
        self.store.persist_fp11(first)
        _, _, second_value = self._owner_case("multiple")
        self._persist_fp04_dependencies(second_value)
        second = build_protection_registry_multiplicity_evidence(second_value, supersedes_evidence=first)
        self.store.persist_fp11(second)
        connection = self.store._connection
        connection.execute("DROP TRIGGER protection_registry_evidence_immutable_update")
        connection.execute(
            "UPDATE protection_registry_multiplicity_evidence SET supersedes_registry_evidence_id = ? WHERE protection_registry_evidence_id = ?",
            (second["protection_registry_evidence_id"], first["protection_registry_evidence_id"]),
        )
        connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertFalse(result.healthy_protection)

    def test_exact_current_fp11_and_matching_e5_interpretation_are_only_healthy_path(self):
        evidence, owner_authority, _, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        self._persist_decision(evidence, owner_authority, authority)
        result = self.store.recover(authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, result.status)
        self.assertTrue(result.healthy_protection)
        self.assertFalse(result.provider_mutation_authorized)
        self.assertIsNone(result.cleanup_target_ref)

    def test_missing_e5_interpretation_prevents_healthy_read_model(self):
        evidence, _, _, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        result = self.store.recover(authority)
        self.assertEqual(STATUS_INCOMPLETE, result.status)
        self.assertFalse(result.healthy_protection)
        self.assertIn("CURRENT_E5_FP11_INTERPRETATION_MISSING", result.reason_codes)

    def test_superseded_fp11_with_only_old_e5_interpretation_is_not_healthy(self):
        first, first_owner, _, first_authority = self._setup_case()
        self.store.persist_fp11(first)
        self._persist_decision(first, first_owner, first_authority)
        _, second_owner, second_value = self._owner_case("multiple")
        self._persist_fp04_dependencies(second_value)
        second = build_protection_registry_multiplicity_evidence(second_value, supersedes_evidence=first)
        self.store.persist_fp11(second)
        result = self.store.recover(self._current_authority(second, second_owner))
        self.assertEqual(STATUS_INCOMPLETE, result.status)
        self.assertFalse(result.healthy_protection)
        self.assertIn("CURRENT_E5_FP11_INTERPRETATION_MISSING", result.reason_codes)

    def test_nonconverged_registry_states_remain_non_green_after_restart(self):
        cases = (
            ("missing", "COMPLETE", "CURRENT"),
            ("multiple", "COMPLETE", "CURRENT"),
            ("intended-plus-external", "COMPLETE", "CURRENT"),
            ("conflict", "COMPLETE", "CURRENT"),
            ("unknown", "COMPLETE", "CURRENT"),
            ("missing", "INCOMPLETE", "CURRENT"),
            ("missing", "UNKNOWN", "CURRENT"),
            ("missing", "COMPLETE", "STALE"),
        )
        for index, (kind, coverage, currentness) in enumerate(cases):
            with self.subTest(kind=kind, coverage=coverage, currentness=currentness):
                if self.store is not None:
                    self.store.close()
                self.db_path = Path(self.temp.name) / f"fp11-nongreen-{index}.sqlite3"
                self.store = None
                evidence, owner_authority, _, authority = self._setup_case(
                    kind,
                    coverage=coverage,
                    currentness=currentness,
                )
                self.store.persist_fp11(evidence)
                self._persist_decision(evidence, owner_authority, authority)
                self.store.close()
                self.store = open_protection_registry_currentness_store(self.db_path)
                result = self.store.recover(authority)
                self.assertNotEqual(HEALTHY_UNIQUE_PROTECTION, result.status)
                self.assertFalse(result.healthy_protection)
                self.assertFalse(result.provider_mutation_authorized)
                self.assertIsNone(result.cleanup_target_ref)

    def test_changed_position_lifecycle_provider_or_runtime_authority_invalidates_old_health(self):
        evidence, owner_authority, _, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        self._persist_decision(evidence, owner_authority, authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, self.store.recover(authority).status)

        changed_position = dict(authority.position)
        changed_position["actual_quantity"] = "0.0011"
        self.assertEqual(STATUS_STALE, self.store.recover(replace(authority, position=changed_position)).status)
        self.assertEqual(
            STATUS_STALE,
            self.store.recover(replace(authority, provider_observation_generation_id="provider-generation-new")).status,
        )
        self.assertEqual(
            STATUS_STALE,
            self.store.recover(replace(authority, lifecycle_execution_binding=None)).status,
        )
        runtime_changed = replace(
            authority,
            runtime_preflight_ref="runtime-preflight-new",
            runtime_process_instance_id="runtime-process-new",
            runtime_process_start_generation_id="runtime-start-new",
            runtime_config_generation_id="runtime-config-new",
        )
        self.assertEqual(STATUS_STALE, self.store.recover(runtime_changed).status)

    def test_missing_or_superseded_fp04_dependency_invalidates_fp11_health(self):
        evidence, owner_authority, value, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        self._persist_decision(evidence, owner_authority, authority)
        dep = value.fp04_dependencies[0].evidence
        connection = self.store._connection
        connection.execute("DROP TRIGGER external_provider_ownership_immutable_delete")
        connection.execute(
            "DELETE FROM external_provider_ownership_evidence WHERE ownership_evidence_id = ?",
            (dep["ownership_evidence_id"],),
        )
        connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_INCOMPLETE, result.status)
        self.assertFalse(result.healthy_protection)

    def test_flat_closed_with_unresolved_active_protection_keeps_terminal_convergence_non_green_after_restart(self):
        evidence, owner_authority, _, authority = self._setup_case(
            "external-terminal",
            quantity="0",
            lifecycle="CLOSED",
        )
        self.store.persist_fp11(evidence)
        self._persist_decision(evidence, owner_authority, authority)
        self.store.close()
        self.store = open_protection_registry_currentness_store(self.db_path)
        result = self.store.recover(authority)
        self.assertEqual(STATUS_RECONCILIATION_REQUIRED, result.status)
        self.assertFalse(result.healthy_protection)
        self.assertTrue(result.terminal_close_dependency)
        self.assertIn("FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED", result.reason_codes)

    def test_unknown_or_unavailable_authority_is_explicit_non_green(self):
        evidence, _, _, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        result = self.store.recover(replace(authority, observed_active_protection_set_hash=None))
        self.assertEqual(STATUS_UNKNOWN, result.status)
        self.assertFalse(result.healthy_protection)

    def test_e5_healthy_flag_never_grants_provider_mutation_or_cleanup_authority(self):
        evidence, owner_authority, _, authority = self._setup_case()
        self.store.persist_fp11(evidence)
        interpretation = self._persist_decision(evidence, owner_authority, authority)
        self.assertTrue(interpretation.payload["healthy_protection"])
        result = self.store.recover(authority)
        self.assertTrue(result.healthy_protection)
        self.assertFalse(result.provider_mutation_authorized)
        self.assertIsNone(result.cleanup_target_ref)


if __name__ == "__main__":
    unittest.main()
