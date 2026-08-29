import unittest
from dataclasses import replace

import tests.brokers.test_okx_close_sizing as fixture_module
from src.brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from src.brokers.okx_close_sizing_binding import (
    OKXCloseMetadataBindingEvidence,
    evaluate_okx_close_residual_sizing,
)
from src.brokers.okx_close_sizing import OKXCloseSizingError, FULLY_REDUCIBLE


class OKXCloseSizingMetadataBindingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.OKXCloseResidualSizingTests(methodName="runTest")
        self.fixture.setUp()
        self.value = self.fixture.sizing_input()

    def binding(self, value=None, **changes):
        value = self.value if value is None else value
        applicability = value.metadata_applicability
        metadata = value.instrument_metadata
        evidence = OKXCloseMetadataBindingEvidence(
            binding_ref="fixture:fp05:metadata-binding:001",
            instrument_metadata_ref=metadata.metadata_ref,
            instrument_metadata_hash=canonical_okx_close_sizing_hash(metadata),
            instrument_metadata_generation=applicability.instrument_metadata_generation,
            metadata_applicability_proof_ref=applicability.applicability_proof_ref,
            metadata_applicability_hash=canonical_okx_close_sizing_hash(applicability),
            metadata_applicability_generation_id=applicability.applicability_generation_id,
        )
        return replace(evidence, **changes)

    def test_exact_metadata_and_applicability_binding_allows_deterministic_evaluation(self):
        evidence = evaluate_okx_close_residual_sizing(self.value, self.binding())
        self.assertEqual(FULLY_REDUCIBLE, evidence["sizing_state"])

    def test_mixed_metadata_snapshot_or_applicability_proof_fails_before_sizing(self):
        cases = (
            self.binding(instrument_metadata_ref="fixture:other-metadata"),
            self.binding(instrument_metadata_hash="sha256:" + "0" * 64),
            self.binding(instrument_metadata_generation="other-generation"),
            self.binding(metadata_applicability_proof_ref="fixture:other-proof"),
            self.binding(metadata_applicability_hash="sha256:" + "1" * 64),
            self.binding(metadata_applicability_generation_id="other-proof-generation"),
        )
        for binding in cases:
            with self.subTest(binding=binding):
                with self.assertRaises(OKXCloseSizingError) as caught:
                    evaluate_okx_close_residual_sizing(self.value, binding)
                self.assertEqual("OKX_CLOSE_METADATA_BINDING_MISMATCH", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
