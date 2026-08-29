import unittest

from position import (
    FP11_DECISION_RECONCILE,
    PositionLifecycleState,
    interpret_protection_registry_evidence,
)
import tests.position.test_protection_registry_policy as policy_fixture_module


class FP11ProtectionRegistryFalseGreenSafetyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_terminal_flat_with_unresolved_active_protection_reopens_false_green_closed_claim"
        )
        self.fixture.setUp()

    def test_flat_position_with_unresolved_active_protection_cannot_remain_false_green_closed(self):
        evidence, authority, _ = self.fixture._build(
            "external-terminal",
            quantity="0",
            lifecycle="CLOSED",
        )
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertTrue(decision.terminal_close_dependency)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_multiple_protection_truth_cannot_select_cleanup_target_or_claim_healthy(self):
        evidence, authority, _ = self.fixture._build("multiple")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.healthy_protection)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)


if __name__ == "__main__":
    unittest.main()
