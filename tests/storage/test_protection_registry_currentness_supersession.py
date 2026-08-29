from __future__ import annotations

import hashlib
import json
import unittest

from storage.protection_registry_currentness import STATUS_CONFLICT
from tests.storage.test_protection_registry_currentness import (
    ProtectionRegistryCurrentnessPersistenceTests,
)


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _fp11_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("protection_registry_evidence_id", None)
    return "protregmul_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


class ProtectionRegistryInvalidSupersessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ProtectionRegistryCurrentnessPersistenceTests(
            methodName="test_exact_current_fp11_and_matching_e5_interpretation_are_only_healthy_path"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def test_cross_lineage_child_poisoning_original_head_fails_closed(self):
        first, _, _, original_authority = self.fixture._setup_case()
        self.fixture.store.persist_fp11(first)

        cross = json.loads(_json(first))
        lineage = dict(cross["intended_protection_lineage"])
        lineage["position_action_id"] = "position-action-cross-lineage"
        lineage["position_action_ref"] = "position-action-ref-cross-lineage"
        lineage["position_action_hash"] = _sha({"position_action": "cross-lineage"})
        cross["intended_protection_lineage"] = lineage
        cross["intended_protection_lineage_hash"] = _sha(lineage)
        cross["supersedes_registry_evidence_id"] = first["protection_registry_evidence_id"]
        cross["evaluated_at"] = "2026-08-29T09:40:00Z"
        cross["protection_registry_evidence_id"] = _fp11_id(cross)
        self.fixture.store.persist_fp11(cross)

        result = self.fixture.store.recover(original_authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_CROSS_LINEAGE_SUPERSESSION_CHILD", result.reason_codes)
        self.assertFalse(result.healthy_protection)

    def test_refresh_only_explicit_supersession_does_not_advance_current_authority(self):
        first, _, _, authority = self.fixture._setup_case()
        self.fixture.store.persist_fp11(first)

        refresh_only = json.loads(_json(first))
        refresh_only["supersedes_registry_evidence_id"] = first["protection_registry_evidence_id"]
        refresh_only["evaluated_at"] = "2026-08-29T09:45:00Z"
        refresh_only["protection_registry_evidence_id"] = _fp11_id(refresh_only)
        self.fixture.store.persist_fp11(refresh_only)

        result = self.fixture.store.recover(authority)
        self.assertEqual(STATUS_CONFLICT, result.status)
        self.assertIn("FP11_SUPERSESSION_REQUIRES_MATERIAL_CHANGE", result.reason_codes)
        self.assertFalse(result.healthy_protection)


if __name__ == "__main__":
    unittest.main()
