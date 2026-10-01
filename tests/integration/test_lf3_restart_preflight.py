"""LF-3 restart faults using pure preflight evaluation; no runtime is launched."""
import unittest
from dataclasses import replace

from integration.runtime_preflight import ELIGIBLE, FAIL_CLOSED, evaluate_runtime_preflight
import tests.integration.test_runtime_preflight as preflight_fixtures


class LF3RestartPreflightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = preflight_fixtures.RuntimePreflightV01Tests()
        self.fixture.setUp()

    def test_restart_requires_current_identity_heartbeat_and_fresh_reconciliation(self):
        # PAPER_RUNTIME is a synthetic role input to the evaluator, not a launch.
        value = self.fixture._input(role="PAPER_RUNTIME", launch_intent="RESTART")
        authority = self.fixture._authority(value)
        eligible = evaluate_runtime_preflight(value, authority)
        self.assertEqual(ELIGIBLE, eligible["preflight_status"])
        cases = (
            (replace(value, project_revision="b" * 40), "PREFLIGHT_REVISION_MISMATCH"),
            (replace(value, requested_operational_mode="SHADOW"), "PREFLIGHT_OPERATIONAL_MODE_MISMATCH"),
            (replace(value, heartbeat_evidence=self.fixture._heartbeat(heartbeat_freshness_status="STALE")), "PREFLIGHT_HEARTBEAT_STALE"),
            (replace(value, heartbeat_evidence=self.fixture._heartbeat(heartbeat_process_start_generation_id="previous-boot")), "PREFLIGHT_HEARTBEAT_PRIOR_BOOT"),
            (replace(value, reconciliation_evidence=self.fixture._reconciliation(fresh_reconciliation_required=True)), "PREFLIGHT_RECONCILIATION_NOT_READY"),
            (replace(value, reconciliation_evidence=self.fixture._reconciliation(reconciliation_status="NOT_READY")), "PREFLIGHT_RECONCILIATION_NOT_READY"),
        )
        for fault, reason in cases:
            with self.subTest(reason=reason):
                first = evaluate_runtime_preflight(fault, authority)
                repeated = evaluate_runtime_preflight(fault, authority)
                self.assertEqual(FAIL_CLOSED, first["preflight_status"])
                self.assertIn(reason, first["reason_codes"])
                self.assertEqual(first, repeated)
                for forbidden in ("process_launch_authorized", "restart_executed", "provider_mutation_authorized", "paper_authorized"):
                    self.assertNotIn(forbidden, first)
        self.assertEqual(eligible, evaluate_runtime_preflight(value, authority))


if __name__ == "__main__":
    unittest.main()
