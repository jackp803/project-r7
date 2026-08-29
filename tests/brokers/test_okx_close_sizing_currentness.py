import unittest
from dataclasses import replace
from datetime import timedelta

import tests.brokers.test_okx_close_sizing as fixture_module
from src.brokers.okx_close_sizing import (
    evaluate_okx_close_residual_sizing,
    okx_close_residual_sizing_evidence_is_current,
)


class OKXCloseSizingCurrentnessTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.OKXCloseResidualSizingTests(methodName="runTest")
        self.fixture.setUp()
        self.base_input = self.fixture.sizing_input()
        self.base_evidence = evaluate_okx_close_residual_sizing(self.base_input)

    def test_newer_position_observation_invalidates_old_evidence(self):
        newer_observed = self.fixture.position_observed + timedelta(seconds=1)
        newer_position = self.fixture.position(observed=newer_observed)
        changed = replace(self.base_input, current_position=newer_position)
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(self.base_evidence, changed))

    def test_newer_provider_snapshot_generation_invalidates_old_evidence(self):
        newer_provider = self.fixture.provider(
            generation="provider-gen-002",
            snapshot_ref="provider-position-snapshot-002",
        )
        changed = self.fixture.sizing_input(provider=newer_provider)
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(self.base_evidence, changed))

    def test_changed_fp04_ownership_interpretation_invalidates_old_evidence(self):
        changed = self.fixture.sizing_input(external_fp04=True)
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(self.base_evidence, changed))

    def test_changed_capability_generation_invalidates_old_evidence(self):
        changed = replace(
            self.base_input,
            capability=replace(
                self.base_input.capability,
                capability_generation_id="fp02-gen-002",
            ),
        )
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(self.base_evidence, changed))

    def test_changed_metadata_generation_invalidates_old_evidence(self):
        changed = replace(
            self.base_input,
            metadata_applicability=replace(
                self.base_input.metadata_applicability,
                instrument_metadata_generation="okx-metadata-gen-002",
                applicability_generation_id="fp05-metadata-proof-gen-002",
            ),
        )
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(self.base_evidence, changed))


if __name__ == "__main__":
    unittest.main()
