import hashlib
import json
import unittest
from dataclasses import replace
from datetime import timedelta

from src.execution.protection_registry_evidence_boundary import (
    build_protection_registry_multiplicity_evidence,
)
from storage.protection_registry_currentness import (
    HEALTHY_UNIQUE_PROTECTION,
    STATUS_CONFLICT,
    STATUS_RECONCILIATION_REQUIRED,
    STATUS_STALE,
    open_protection_registry_currentness_store,
)
import tests.storage.test_protection_registry_currentness as fp11_storage_fixture_module


def _sha(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class P0ReconciliationRestartE2ETests(unittest.TestCase):
    """Cross-module restart/currentness definitions for the P0 LF-2/LF-3 seam."""

    def setUp(self):
        self.fixture = fp11_storage_fixture_module.ProtectionRegistryCurrentnessPersistenceTests(
            methodName="test_normal_paper_runtime_writer_projection_is_accepted_by_fp11_restart_currentness"
        )
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def test_real_paper_lifecycle_writer_and_fp11_currentness_remain_healthy_after_restart_only_for_exact_chain(self):
        evidence, owner_authority, _, authority = self.fixture._persist_healthy_chain()
        before = self.fixture.store.recover(authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, before.status)
        self.assertTrue(before.healthy_protection)
        self.assertFalse(before.provider_mutation_authorized)
        self.assertIsNone(before.cleanup_target_ref)

        self.fixture.store.close()
        self.fixture.store = open_protection_registry_currentness_store(self.fixture.db_path)
        after = self.fixture.store.recover(authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, after.status)
        self.assertTrue(after.healthy_protection)
        self.assertEqual(evidence["protection_registry_evidence_id"], after.current_fp11.canonical_id)
        self.assertFalse(after.provider_mutation_authorized)
        self.assertIsNone(after.cleanup_target_ref)
        self.assertEqual(
            owner_authority.lifecycle_projection["lifecycle_projection_id"],
            authority.lifecycle_projection["lifecycle_projection_id"],
        )

    def test_timestamp_only_fp11_row_never_becomes_current_head_and_restart_fails_closed(self):
        first, _, value, authority = self.fixture._setup_case()
        self.fixture.store.persist_fp11(first)
        later_value = replace(value, evaluated_at=value.evaluated_at + timedelta(minutes=5))
        timestamp_only = build_protection_registry_multiplicity_evidence(later_value)
        self.fixture.store.persist_fp11(timestamp_only)

        before = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, before.status)
        self.assertFalse(before.healthy_protection)

        self.fixture.store.close()
        self.fixture.store = open_protection_registry_currentness_store(self.fixture.db_path)
        after = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, after.status)
        self.assertIn("FP11_COMPETING_UNSUPERSEDED_HEADS", after.reason_codes)
        self.assertFalse(after.healthy_protection)

    def test_corrupt_lifecycle_projection_hash_cannot_false_green_after_restart(self):
        _, _, _, authority = self.fixture._persist_healthy_chain()
        self.fixture.store._connection.execute(
            "UPDATE paper_position_current_projection SET payload_hash = ? WHERE position_id = ?",
            (_sha({"corrupt": "p0-current-projection-hash"}), authority.position["position_id"]),
        )
        self.fixture.store._connection.commit()

        before = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_STALE, before.status)
        self.assertFalse(before.healthy_protection)

        self.fixture.store.close()
        self.fixture.store = open_protection_registry_currentness_store(self.fixture.db_path)
        after = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_STALE, after.status)
        self.assertIn("CURRENT_LIFECYCLE_PROJECTION_SUPERSEDED_OR_MISMATCHED", after.reason_codes)
        self.assertFalse(after.healthy_protection)

    def test_newer_position_provider_lifecycle_or_runtime_authority_invalidates_prior_health(self):
        evidence, owner_authority, _, authority = self.fixture._setup_case()
        self.fixture.store.persist_fp11(evidence)
        self.fixture._persist_decision(evidence, owner_authority, authority)
        self.assertEqual(HEALTHY_UNIQUE_PROTECTION, self.fixture.store.recover(authority).status)

        changed_position = dict(authority.position)
        changed_position["actual_quantity"] = "0.0011"
        candidates = (
            replace(authority, position=changed_position),
            replace(authority, provider_observation_generation_id="provider-generation-p0-new"),
            replace(authority, lifecycle_execution_binding=None),
            replace(
                authority,
                runtime_preflight_ref="runtime-preflight-p0-new",
                runtime_process_instance_id="runtime-process-p0-new",
                runtime_process_start_generation_id="runtime-start-p0-new",
                runtime_config_generation_id="runtime-config-p0-new",
            ),
        )
        for candidate in candidates:
            with self.subTest(candidate=candidate):
                result = self.fixture.store.recover(candidate)
                self.assertEqual(STATUS_STALE, result.status)
                self.assertFalse(result.healthy_protection)
                self.assertFalse(result.provider_mutation_authorized)

    def test_flat_closed_with_unresolved_external_protection_remains_reconciliation_required_after_restart(self):
        evidence, owner_authority, _, authority = self.fixture._setup_case(
            "external-terminal",
            quantity="0",
            lifecycle="CLOSED",
        )
        self.fixture.store.persist_fp11(evidence)
        self.fixture._persist_decision(evidence, owner_authority, authority)
        self.fixture.store.close()
        self.fixture.store = open_protection_registry_currentness_store(self.fixture.db_path)

        result = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_RECONCILIATION_REQUIRED, result.status)
        self.assertFalse(result.healthy_protection)
        self.assertTrue(result.terminal_close_dependency)
        self.assertIn("FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED", result.reason_codes)
        self.assertFalse(result.provider_mutation_authorized)
        self.assertIsNone(result.cleanup_target_ref)


if __name__ == "__main__":
    unittest.main()
