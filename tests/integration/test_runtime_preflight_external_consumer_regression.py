import unittest

from src.integration.runtime_preflight import ELIGIBLE, FAIL_CLOSED, evaluate_runtime_preflight
from tests.integration.test_runtime_preflight import RuntimePreflightV01Tests


class RuntimePreflightExternalConsumerParticipationRegressionTests(unittest.TestCase):
    """E7-113 regression definitions for conditional external-consumer participation."""

    def setUp(self):
        self.fixture = RuntimePreflightV01Tests(
            methodName="test_coherent_credential_free_evidence_is_eligible_without_runtime_authority_side_effects"
        )
        self.fixture.setUp()

    def _external_authority(self, **changes):
        external = self.fixture._external_consumer()
        value = {
            "external_consumer_id": external["external_consumer_id"],
            "external_consumer_generation_id": external["external_consumer_generation_id"],
            "external_consumer_config_hash": external["external_consumer_config_hash"],
            "compatibility_profile_ref": external["compatibility_profile_ref"],
            "compatibility_evidence_hash": external["compatibility_evidence_hash"],
        }
        value.update(changes)
        return value

    def test_credential_free_current_external_authority_without_evidence_fails_closed(self):
        value = self.fixture._input()
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_provider_read_only_current_external_authority_without_evidence_fails_closed(self):
        value = self.fixture._input(role="PROVIDER_READ_ONLY_OBSERVATION")
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_credential_free_no_external_participation_remains_eligible(self):
        value = self.fixture._input()
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(ELIGIBLE, evidence["preflight_status"])
        self.assertEqual(["RUNTIME_PREFLIGHT_ELIGIBLE"], evidence["reason_codes"])

    def test_exact_current_external_evidence_and_authority_remain_admissible(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(value)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(ELIGIBLE, evidence["preflight_status"])
        self.assertEqual(["RUNTIME_PREFLIGHT_ELIGIBLE"], evidence["reason_codes"])

    def test_external_evidence_without_current_authority_fails_closed(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_mismatched_or_incompatible_external_consumer_fails_closed(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(
                external_consumer_generation_id="agentbridge-gen-stale"
            ),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

        incompatible = self.fixture._external_consumer(compatibility_status="NOT_ACCEPTED")
        value = self.fixture._input(external_consumer=incompatible)
        authority = self.fixture._authority(value)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_shadow_external_consumer_requirement_remains_unconditional(self):
        value = self.fixture._input(role="SHADOW_RUNTIME")
        value = value.__class__(**{**value.__dict__, "external_consumer_evidence": None})
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_regression_path_creates_no_runtime_or_financial_authority_fields(self):
        value = self.fixture._input()
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        for forbidden in (
            "provider_request",
            "credential",
            "provider_mutation_authorized",
            "process_launch_authorized",
            "restart_executed",
            "order_authorized",
            "shadow_authorized",
            "paper_authorized",
            "live_authorized",
            "capital_authorized",
        ):
            self.assertNotIn(forbidden, evidence)


if __name__ == "__main__":
    unittest.main()
