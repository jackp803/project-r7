from __future__ import annotations

import hashlib
import json
import unittest

import test_external_close_currentness as fixtures


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _fp10_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("close_convergence_evidence_id", None)
    return "extcloseconv_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


class ExternalCloseCurrentnessSupersessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = fixtures.ExternalCloseCurrentnessPersistenceTests(
            "test_insert_read_exact_immutable_fp04_and_changed_same_id_rejected"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def test_newer_fp04_for_same_provider_object_invalidates_older_fp10_reference(self) -> None:
        old_fp04 = self.fixture.fp04()
        self.fixture.store.persist_fp04(old_fp04)
        old_fp10 = self.fixture.fp10(old_fp04)
        self.fixture.store.persist_fp10(old_fp10)
        self.fixture.persist_decision(self.fixture.decision(old_fp10), old_fp10)

        newer_fp04 = self.fixture.fp04(
            snapshot="provider-position-snapshot-002",
            generation="provider-generation-002",
            supersedes=old_fp04["ownership_evidence_id"],
        )
        self.fixture.store.persist_fp04(newer_fp04)

        recovery = self.fixture.store.recover_position(self.fixture.position_id)
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
        self.assertIn("FP10_REFERENCES_SUPERSEDED_FP04", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_newer_lifecycle_projection_pointer_invalidates_older_fp10_and_decision(self) -> None:
        fp04 = self.fixture.fp04()
        self.fixture.store.persist_fp04(fp04)
        old_fp10 = self.fixture.fp10(fp04)
        self.fixture.store.persist_fp10(old_fp10)
        self.fixture.persist_decision(self.fixture.decision(old_fp10), old_fp10)

        connection = self.fixture.store._connection
        old_row = connection.execute(
            "SELECT * FROM paper_position_lifecycle_projections WHERE position_id = ? AND lifecycle_revision = 0",
            (self.fixture.position_id,),
        ).fetchone()
        old_binding = connection.execute(
            "SELECT * FROM paper_position_lifecycle_execution_bindings WHERE position_id = ? AND lifecycle_revision = 0",
            (self.fixture.position_id,),
        ).fetchone()
        assert old_row is not None and old_binding is not None
        projection = json.loads(old_row["payload_json"])
        projection["lifecycle_revision"] = 1
        projection["previous_lifecycle_projection_id"] = old_row["lifecycle_projection_id"]
        projection["lifecycle_projection_kind"] = "REATTESTATION"
        projection["lifecycle_event"] = None
        projection["lifecycle_interpreted_at"] = "2026-08-29T08:10:07Z"
        projection.pop("lifecycle_projection_id", None)
        projection["lifecycle_projection_id"] = "posproj_" + hashlib.sha256(
            _json(projection).encode("utf-8")
        ).hexdigest()
        projection_json = _json(projection)
        projection_hash = _sha(projection)
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
                self.fixture.position_id,
                1,
                old_row["lifecycle_projection_id"],
                "REATTESTATION",
                None,
                projection["lifecycle_state"],
                projection["broker_state_observed_at"],
                projection["lifecycle_source_broker_state_observed_at"],
                projection["lifecycle_interpreted_at"],
                old_row["broker_fact_hash"],
                projection_json,
                projection_hash,
            ),
        )
        binding = json.loads(old_binding["payload_json"])
        binding["lifecycle_projection_id"] = projection["lifecycle_projection_id"]
        binding["lifecycle_revision"] = 1
        binding["execution_interpreted_at"] = projection["lifecycle_interpreted_at"]
        binding.pop("lifecycle_execution_binding_id", None)
        binding["lifecycle_execution_binding_id"] = "posexecbind_" + hashlib.sha256(
            _json(binding).encode("utf-8")
        ).hexdigest()
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
                self.fixture.position_id,
                1,
                binding["execution_interpreted_at"],
                binding["execution_scope"],
                binding["execution_snapshot_hash"],
                _json(binding),
                _sha(binding),
            ),
        )
        connection.execute(
            """
            UPDATE paper_position_current_projection
            SET lifecycle_projection_id = ?, lifecycle_revision = ?, payload_hash = ?
            WHERE position_id = ?
            """,
            (
                projection["lifecycle_projection_id"],
                1,
                projection_hash,
                self.fixture.position_id,
            ),
        )
        connection.commit()

        recovery = self.fixture.store.recover_position(self.fixture.position_id)
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
        self.assertIn("FP10_LIFECYCLE_PROJECTION_SUPERSEDED", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)

    def test_newer_fp10_owner_reference_generation_supersedes_old_decision_without_arrival_heuristic(self) -> None:
        fp04 = self.fixture.fp04()
        self.fixture.store.persist_fp04(fp04)
        old_fp10 = self.fixture.fp10(fp04)
        self.fixture.store.persist_fp10(old_fp10)
        self.fixture.persist_decision(self.fixture.decision(old_fp10), old_fp10)

        newer = dict(old_fp10)
        newer["normalized_position_ref"] = "normalized-position-e6-fp10-002"
        newer["normalized_position_hash"] = _sha({"position": "newer-owner-truth"})
        newer["fp05_close_residual_sizing_ref"] = "fp05-residual-evidence-002"
        newer["fp05_close_residual_sizing_hash"] = _sha({"fp05": "newer"})
        newer["fp11_prior_registry_evidence_ref"] = "fp11-registry-evidence-002"
        newer["fp11_prior_registry_evidence_hash"] = _sha({"fp11": "newer"})
        newer["terminal_protection_observation_ref"] = "terminal-protection-set-e6-fp10-002"
        newer["terminal_protection_observation_hash"] = _sha({"terminal": "newer-clear"})
        newer["runtime_config_generation_id"] = "runtime-config-generation-002"
        newer["supersedes_close_convergence_evidence_id"] = old_fp10["close_convergence_evidence_id"]
        newer["evaluated_at"] = "2026-08-29T08:10:08Z"
        newer.pop("close_convergence_evidence_id", None)
        newer["close_convergence_evidence_id"] = _fp10_id(newer)
        self.fixture.store.persist_fp10(newer)

        recovery = self.fixture.store.recover_position(self.fixture.position_id)
        self.assertEqual(newer["close_convergence_evidence_id"], recovery.current_fp10.canonical_id)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("CURRENT_E5_REINTERPRETATION_DECISION_MISSING", recovery.reason_codes)
        self.assertFalse(recovery.closed_presentation_allowed)


if __name__ == "__main__":
    unittest.main()
