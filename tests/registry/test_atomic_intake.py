import tempfile
from pathlib import Path
import unittest
from contextlib import ExitStack

from registry import IdentityConflict
from storage import open_sqlite_platform
from tests.strategy.test_slice1_runtime import make_definition
import sqlite3


class AtomicIntakeTests(unittest.TestCase):
    def test_failure_after_registration_rolls_back_every_intake_table(self):
        class BrokenBoundary:
            def check(self, _):
                raise RuntimeError("injected after registration")
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            path = Path(temp) / "e6.sqlite3"
            service = stack.enter_context(open_sqlite_platform(path, compatibility_boundary=BrokenBoundary()))
            with self.assertRaises(RuntimeError):
                service.intake(make_definition(), source_actor="fixture", operation_id="atomic-failure")
            with sqlite3.connect(path) as connection:
                for table in ("strategy_versions", "compatibility_evidence", "strategy_intake_receipts", "strategy_intake_operations"):
                    self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
            connection.close()
            recovered = stack.enter_context(open_sqlite_platform(path))
            result = recovered.intake(make_definition(), source_actor="fixture", operation_id="atomic-failure")
            self.assertEqual("DRAFT", result.strategy.current_lifecycle_state)

    def test_operation_replay_has_same_receipt_and_retains_draft_without_compatibility_pass(self):
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            path = Path(temp) / "e6.sqlite3"
            first_service = stack.enter_context(open_sqlite_platform(path))
            first = first_service.intake(make_definition(), source_actor="fixture", operation_id="intake-1")
            restarted = stack.enter_context(open_sqlite_platform(path))
            second = restarted.intake(make_definition(), source_actor="fixture", operation_id="intake-1")
            self.assertEqual(first.receipt, second.receipt)
            self.assertEqual(first.compatibility, second.compatibility)
            self.assertEqual("DRAFT", second.strategy.current_lifecycle_state)
            self.assertEqual("NOT_RUN", second.compatibility.status)
            with self.assertRaises(IdentityConflict):
                restarted.intake(make_definition(), source_actor="different", operation_id="intake-1")
