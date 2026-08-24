from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storage.runtime import PaperRuntimeJournal, open_paper_runtime_journal


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
        self.assertIn("persist_trade_result", methods)
        self.assertIn("recover", methods)
        self.assertNotIn("promote_strategy", methods)
        self.assertNotIn("approve_strategy", methods)
        self.assertNotIn("enable_paper", methods)
        self.assertNotIn("enable_live", methods)


if __name__ == "__main__":
    unittest.main()
