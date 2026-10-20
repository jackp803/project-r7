"""Original finalization refusal scenario; genuine owner flow."""
from dataclasses import replace
from datetime import timedelta
import unittest
from tests.product.trading_finalization_fixtures import FinalizationFixture


class TradingFinalizationIssuerV02Tests(FinalizationFixture,unittest.TestCase):
    def test_copied_or_expired_issued_reads_cannot_finalize(self):
        self.settled()
        reads = self.final_reads()
        target, native, inventory, metadata, proof = reads
        for candidate in ((replace(target),native,inventory,metadata,proof),
                          (target,replace(native),inventory,metadata,proof),
                          (target,native,replace(inventory),metadata,proof)):
            with self.subTest(copied=type(candidate[0]).__name__):
                self.assert_denied_without_final_effect(candidate)
        self.fixture.clock[0] += timedelta(seconds=6)
        self.assert_denied_without_final_effect(reads)
