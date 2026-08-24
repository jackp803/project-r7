from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storage.runtime import (
    PaperRuntimeJournal,
    RuntimeValidationError,
    open_paper_runtime_journal,
)


class PaperRuntimeStorageSurfaceDefinitions(unittest.TestCase):
    def test_safe_factory_returns_journal_without_public_sqlite_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            journal = open_paper_runtime_journal(Path(temp) / "runtime.sqlite3")
            try:
                self.assertIsInstance(journal, PaperRuntimeJournal)
                for raw_name in (
                    "connection",
                    "execute",
                    "cursor",
                    "apply_migrations",
                    "enable_paper",
                    "enable_live",
                    "go_live",
                    "submit_provider_order",
                ):
                    with self.subTest(raw_name=raw_name):
                        self.assertFalse(hasattr(journal, raw_name))
            finally:
                journal.close()

    def test_runtime_surface_is_separate_from_strategy_lifecycle_authority(self) -> None:
        methods = set(PaperRuntimeJournal.__dict__)
        self.assertIn("persist_position_projection", methods)
        self.assertIn("persist_lifecycle_execution_binding", methods)
        self.assertIn("persist_trade_result", methods)
        self.assertIn("recover", methods)
        self.assertNotIn("promote_strategy", methods)
        self.assertNotIn("approve_strategy", methods)
        self.assertNotIn("enable_paper", methods)
        self.assertNotIn("enable_live", methods)

    def test_provider_native_fields_are_outside_canonical_runtime_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            journal = open_paper_runtime_journal(Path(temp) / "runtime.sqlite3")
            try:
                payload = {
                    "schema_version": "contracts-v0.1",
                    "risk_decision_id": "risk-provider-private-forbidden",
                    "intent_id": "intent-provider-private-forbidden",
                    "strategy_id": "strategy-provider-private-forbidden",
                    "strategy_version": "1.0.0",
                    "decision": "REJECT",
                    "reason_codes": ["SYNTHETIC_TEST_ONLY"],
                    "risk_policy_version": "test-policy-v0.1",
                    "decided_at": "2026-08-24T07:00:00Z",
                    "market_health_status": "HEALTHY",
                    "account_state_status": "KNOWN",
                    "position_state_status": "FLAT",
                    "provider_instrument_id": "BTC-USDT-SWAP",
                }
                with self.assertRaises(RuntimeValidationError) as ctx:
                    journal.persist_risk_decision(payload)
                self.assertEqual("PROVIDER_NATIVE_FIELD_FORBIDDEN", ctx.exception.code)
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()
