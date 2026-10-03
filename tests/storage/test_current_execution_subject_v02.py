import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from datetime import datetime, timedelta, timezone

import tests.storage.test_paper_runtime_durability as fixtures
from registry.models import StrategyIdentity
from storage.runtime import open_paper_runtime_journal
from position import build_position_lifecycle_genesis_with_execution_binding, build_position_lifecycle_reattestation_with_execution_binding


class CurrentExecutionSubjectV02Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'canonical.sqlite'
        self.journal = open_paper_runtime_journal(self.path)
        self.addCleanup(self.journal.close)
        self.risk, self.plan = fixtures.risk_decision(), fixtures.approved_plan()
        self.identity = StrategyIdentity(self.plan['strategy_id'], self.plan['strategy_version'])
        self.journal.persist_risk_decision(self.risk)
        self.journal.persist_approved_trade_plan(self.plan)

    def read(self, **kwargs):
        return self.journal.current_execution_subject(self.identity, self.plan['trade_plan_id'], **kwargs)

    def test_exact_durable_plan_and_risk_are_read_in_one_closed_snapshot(self):
        result = self.read()
        self.assertEqual(self.identity, result.identity)
        self.assertEqual(self.plan, result.approved_trade_plan.payload)
        self.assertEqual(self.risk, result.risk_decision.payload)
        self.assertIsNone(result.current_position_projection)
        self.journal.require_current_execution_subject(result)
        # A writer on another connection can commit after this read; no snapshot
        # or authoritative writer capability is leaked to application code.
        with closing(sqlite3.connect(self.path, timeout=1)) as db:
            db.execute('BEGIN IMMEDIATE')
            db.rollback()

    def test_wrong_subject_missing_plan_or_missing_position_action_is_rejected(self):
        from storage.runtime_models import RuntimeValidationError
        for call in (
            lambda: self.journal.current_execution_subject(StrategyIdentity('other', '1.0.0'), self.plan['trade_plan_id']),
            lambda: self.journal.current_execution_subject(self.identity, 'missing'),
            lambda: self.read(position_id='missing-position', position_action_id='missing-action'),
        ):
            with self.assertRaises(RuntimeValidationError):
                call()

    def test_raw_database_hash_corruption_is_not_a_valid_risk_snapshot(self):
        from storage.runtime_models import RuntimeValidationError
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('DROP TRIGGER paper_runtime_objects_immutable_update')
            db.execute("UPDATE paper_runtime_objects SET payload_hash=? WHERE object_kind='RISK_DECISION'", ('sha256:' + '0' * 64,))
            db.commit()
        with self.assertRaises(RuntimeValidationError):
            self.read()

    def test_actual_e5_genesis_binding_and_action_are_required_for_existing_position_read(self):
        position = fixtures.base_position()
        action = fixtures.protect_action()
        interpreted = datetime(2026, 8, 24, 7, 0, 21, tzinfo=timezone.utc)
        outcome = build_position_lifecycle_genesis_with_execution_binding(
            position, lifecycle_state='OPEN_UNPROTECTED', lifecycle_interpreted_at=interpreted,
            order_requests=[], order_results=[], fills=[])
        self.journal.persist_raw_position_observation(position)
        self.journal.persist_position_projection(outcome.lifecycle_projection)
        self.journal.persist_lifecycle_execution_binding(outcome.execution_binding)
        self.journal.persist_position_action(action)
        result = self.read(position_id=position['position_id'], position_action_id=action['position_action_id'])
        self.assertEqual(outcome.lifecycle_projection, result.current_position_projection.payload)
        self.assertEqual(outcome.execution_binding, result.current_lifecycle_execution_binding.payload)
        self.assertEqual(action, result.position_action.payload)
        self.journal.require_current_execution_subject(result)
        newer_position = fixtures.base_position(observed_at='2026-08-24T07:00:30Z')
        self.journal.persist_raw_position_observation(newer_position)
        from storage.runtime_models import RuntimeValidationError
        with self.assertRaises(RuntimeValidationError):
            self.journal.require_current_execution_subject(result)
        refreshed = build_position_lifecycle_reattestation_with_execution_binding(
            newer_position, outcome.lifecycle_projection, lifecycle_interpreted_at=interpreted + timedelta(seconds=10),
            order_requests=[], order_results=[], fills=[])
        self.journal.persist_position_projection(refreshed.lifecycle_projection)
        self.journal.persist_lifecycle_execution_binding(refreshed.execution_binding)
        with self.assertRaises(RuntimeValidationError):
            self.journal.require_current_execution_subject(result)

    def test_raw_malformed_json_is_rejected_by_the_supported_port(self):
        from storage.runtime_models import RuntimeValidationError
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('DROP TRIGGER paper_runtime_objects_immutable_update')
            db.execute("UPDATE paper_runtime_objects SET payload_json=? WHERE object_kind='RISK_DECISION'", ('[not-json]',))
            db.commit()
        with self.assertRaises(RuntimeValidationError):
            self.read()


if __name__ == '__main__':
    unittest.main()
