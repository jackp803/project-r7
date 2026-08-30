from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from position import interpret_protection_registry_evidence
from storage._lifecycle_execution_binding import persist_lifecycle_execution_binding
from storage._paper_runtime import _open_paper_runtime_store
from storage.external_close_currentness import open_external_close_currentness_store
from storage.protection_registry_currentness import (
    HEALTHY_UNIQUE_PROTECTION,
    STATUS_STALE,
    STATUS_UNKNOWN,
    ProtectionRegistryCurrentAuthority,
    ProtectionRegistryValidationError,
    _canonical_storage_timestamp,
    open_protection_registry_currentness_store,
)
import tests.position.test_protection_registry_policy as policy_fixture_module


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


class ProtectionRegistryTimestampNormalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "fp11-timestamp-normalization.sqlite3"
        self.store = None
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

    def _build_healthy(self):
        evidence, owner_authority, value = self.fixture._build("success")

        fp04_store = open_external_close_currentness_store(self.db_path)
        try:
            for dependency in value.fp04_dependencies:
                fp04_store.persist_fp04(dependency.evidence)
        finally:
            fp04_store.close()

        runtime_store = _open_paper_runtime_store(self.db_path)
        try:
            stored_projection = runtime_store.persist_position_projection(
                dict(owner_authority.lifecycle_projection)
            )
            persist_lifecycle_execution_binding(
                runtime_store,
                dict(owner_authority.lifecycle_execution_binding),
            )
        finally:
            runtime_store.close()

        authority = ProtectionRegistryCurrentAuthority(
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

        self.store = open_protection_registry_currentness_store(self.db_path)
        self.store.persist_fp11(evidence)
        decision = interpret_protection_registry_evidence(evidence, owner_authority)
        self.store.persist_e5_interpretation(
            decision,
            evidence=evidence,
            authority=authority,
        )
        return evidence, owner_authority, authority, stored_projection

    def test_storage_timestamp_normalization_accepts_equivalent_fractional_forms(self):
        cases = {
            "2026-08-29T10:10:05Z": "2026-08-29T10:10:05.000000Z",
            "2026-08-29T10:10:05.1Z": "2026-08-29T10:10:05.100000Z",
            "2026-08-29T10:10:05.100000Z": "2026-08-29T10:10:05.100000Z",
            "2026-08-29T10:10:05.123Z": "2026-08-29T10:10:05.123000Z",
            "2026-08-29T10:10:05.123000Z": "2026-08-29T10:10:05.123000Z",
            "2026-08-29T10:10:05.123456Z": "2026-08-29T10:10:05.123456Z",
        }
        for supplied, expected in cases.items():
            with self.subTest(supplied=supplied):
                self.assertEqual(expected, _canonical_storage_timestamp(supplied))

    def test_malformed_storage_timestamp_is_rejected(self):
        for malformed in (
            "2026-08-29T10:10:05",
            "2026-08-29T10:10:99Z",
            "not-a-timestamp",
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ProtectionRegistryValidationError):
                    _canonical_storage_timestamp(malformed)

    def test_real_writer_restart_recovery_treats_semantically_equal_timestamp_as_current(self):
        evidence, owner_authority, authority, stored_projection = self._build_healthy()
        raw_timestamp = authority.position["broker_state_observed_at"]
        self.assertNotIn(".", raw_timestamp.split("T", 1)[1])

        current = self.store._connection.execute(
            "SELECT * FROM paper_position_current_projection WHERE position_id = ?",
            (evidence["position_id"],),
        ).fetchone()
        history = self.store._connection.execute(
            "SELECT * FROM paper_position_lifecycle_projections WHERE lifecycle_projection_id = ?",
            (authority.lifecycle_projection["lifecycle_projection_id"],),
        ).fetchone()
        self.assertEqual(_canonical_storage_timestamp(raw_timestamp), current["broker_state_observed_at"])
        self.assertEqual(_canonical_storage_timestamp(raw_timestamp), history["broker_state_observed_at"])
        self.assertEqual(_json(owner_authority.lifecycle_projection), stored_projection.payload_json)
        self.assertEqual(_sha(owner_authority.lifecycle_projection), stored_projection.payload_hash)
        self.assertEqual(stored_projection.payload_hash, current["payload_hash"])
        self.assertEqual(stored_projection.payload_hash, history["payload_hash"])

        self.store.close()
        self.store = open_protection_registry_currentness_store(self.db_path)
        result = self.store.recover(authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, result.status)
        self.assertTrue(result.healthy_protection)
        self.assertFalse(result.provider_mutation_authorized)
        self.assertIsNone(result.cleanup_target_ref)

    def test_truly_different_current_storage_anchor_still_fails_closed(self):
        _, _, authority, _ = self._build_healthy()
        self.store._connection.execute(
            "UPDATE paper_position_current_projection SET broker_state_observed_at = ? WHERE position_id = ?",
            ("2026-08-29T10:10:06.000000Z", authority.position["position_id"]),
        )
        self.store._connection.commit()
        result = self.store.recover(authority)
        self.assertEqual(STATUS_STALE, result.status)
        self.assertIn("CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_malformed_current_authority_timestamp_remains_rejected(self):
        _, _, authority, _ = self._build_healthy()
        malformed_position = dict(authority.position)
        malformed_position["broker_state_observed_at"] = "2026-08-29T10:10:05"
        malformed_projection = dict(authority.lifecycle_projection)
        malformed_projection["broker_state_observed_at"] = "2026-08-29T10:10:05"
        malformed_projection["lifecycle_source_broker_state_observed_at"] = "2026-08-29T10:10:05"
        malformed_authority = ProtectionRegistryCurrentAuthority(
            position_ref=authority.position_ref,
            position=malformed_position,
            intended_protection_lineage=authority.intended_protection_lineage,
            lifecycle_projection=malformed_projection,
            lifecycle_execution_binding=authority.lifecycle_execution_binding,
            provider_identity_ref=authority.provider_identity_ref,
            provider_instrument_ref=authority.provider_instrument_ref,
            provider_observation_generation_id=authority.provider_observation_generation_id,
            provider_observed_at=authority.provider_observed_at,
            provider_received_at=authority.provider_received_at,
            observed_active_protection_set_hash=authority.observed_active_protection_set_hash,
            runtime_preflight_ref=authority.runtime_preflight_ref,
            runtime_process_instance_id=authority.runtime_process_instance_id,
            runtime_process_start_generation_id=authority.runtime_process_start_generation_id,
            runtime_config_generation_id=authority.runtime_config_generation_id,
        )
        result = self.store.recover(malformed_authority)
        self.assertEqual(STATUS_UNKNOWN, result.status)
        self.assertIn("INVALID_TIMESTAMP", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_newer_storage_anchor_cannot_false_green_stale_evidence(self):
        _, _, authority, _ = self._build_healthy()
        self.store._connection.execute(
            "UPDATE paper_position_current_projection SET broker_state_observed_at = ? WHERE position_id = ?",
            ("2026-08-29T10:10:05.000001Z", authority.position["position_id"]),
        )
        self.store._connection.commit()
        self.store.close()
        self.store = open_protection_registry_currentness_store(self.db_path)
        result = self.store.recover(authority)
        self.assertEqual(STATUS_STALE, result.status)
        self.assertFalse(result.healthy_protection)
        self.assertFalse(result.provider_mutation_authorized)
        self.assertIsNone(result.cleanup_target_ref)


if __name__ == "__main__":
    unittest.main()
