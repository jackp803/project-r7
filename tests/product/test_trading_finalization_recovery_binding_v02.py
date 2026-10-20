"""One bounded canonical interruption and fresh-process recovery case."""
import unittest
import tests.product.trading_finalization_recovery_fixtures as recovery_fixtures


class FinalizationRecoveryBindingTests(recovery_fixtures.FinalizationRecoveryFixture, unittest.TestCase):
    def test_actual_persist_lifecycle_execution_binding_commit_then_successor_replays_original_finalization(self):
        self.run_committed_writer_failure('persist_lifecycle_execution_binding', 2)
