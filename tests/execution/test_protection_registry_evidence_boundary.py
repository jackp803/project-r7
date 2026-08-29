import unittest
from dataclasses import replace
from datetime import timedelta

from src.execution.protection_registry_evidence import (
    OWNERSHIP_MANUAL_REVIEW_REQUIRED,
    PROTECTION_SET_UNKNOWN,
    ProtectionRegistryEvidenceError,
)
from src.execution.protection_registry_evidence_boundary import (
    build_protection_registry_multiplicity_evidence,
    protection_registry_multiplicity_evidence_is_current,
)
from tests.execution.test_protection_registry_evidence import (
    ProtectionRegistryMultiplicityEvidenceTests as FP11Fixtures,
)


class ProtectionRegistryMultiplicityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FP11Fixtures(
            methodName="test_exact_one_current_owned_exact_lineage_is_only_converged_success"
        )
        self.fixture.setUp()

    def test_unknown_exact_lineage_binding_routes_explicit_manual_review(self):
        dependency = self.fixture.fp04_dependency("protection-ambiguous")
        value = self.fixture.input_for(
            [self.fixture.entry(dependency, binding="UNKNOWN")],
            [dependency],
        )
        evidence = build_protection_registry_multiplicity_evidence(value)
        self.assertEqual(PROTECTION_SET_UNKNOWN, evidence["multiplicity_state"])
        self.assertIn(
            OWNERSHIP_MANUAL_REVIEW_REQUIRED,
            evidence["required_dispositions"],
        )
        self.assertIn(
            "PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED",
            evidence["reason_codes"],
        )

    def test_unknown_fp04_ownership_routes_explicit_manual_review(self):
        dependency = self.fixture.fp04_dependency("protection-unknown", kind="unknown")
        value = self.fixture.input_for(
            [self.fixture.entry(dependency, binding="UNKNOWN")],
            [dependency],
        )
        evidence = build_protection_registry_multiplicity_evidence(value)
        self.assertEqual(PROTECTION_SET_UNKNOWN, evidence["multiplicity_state"])
        self.assertIn(
            OWNERSHIP_MANUAL_REVIEW_REQUIRED,
            evidence["required_dispositions"],
        )
        self.assertIn(
            "PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED",
            evidence["reason_codes"],
        )

    def test_strict_timestamp_only_supersession_remains_forbidden(self):
        dependency = self.fixture.fp04_dependency("protection-ambiguous")
        original_input = self.fixture.input_for(
            [self.fixture.entry(dependency, binding="UNKNOWN")],
            [dependency],
        )
        original = build_protection_registry_multiplicity_evidence(original_input)
        later_input = replace(
            original_input,
            evaluated_at=self.fixture.evaluated_at + timedelta(minutes=5),
        )
        self.assertTrue(
            protection_registry_multiplicity_evidence_is_current(original, later_input)
        )
        with self.assertRaises(ProtectionRegistryEvidenceError) as caught:
            build_protection_registry_multiplicity_evidence(
                later_input,
                supersedes_evidence=original,
            )
        self.assertEqual("SUPERSESSION_REQUIRES_MATERIAL_CHANGE", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
