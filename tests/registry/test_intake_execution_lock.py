from pathlib import Path
from contextlib import closing
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from registry.service_base import DeferredCompatibilityBoundary
from storage.platform import open_sqlite_platform
from tests.strategy.v02_fixtures import definition_v02

class IntakeExecutionLockTests(unittest.TestCase):
    def test_fixture_registry_cannot_be_reopened_as_real_research_namespace(self):
        from registry import EvidenceGateError
        import inspect
        self.assertIn('research_namespace',inspect.signature(open_sqlite_platform).parameters)
        with TemporaryDirectory() as root:
            path=Path(root)/'registry.sqlite'
            with open_sqlite_platform(path,research_namespace='FIXTURE') as e6:
                e6.intake(definition_v02(),source_actor='FIXTURE')
            with self.assertRaises(EvidenceGateError): open_sqlite_platform(path,research_namespace='LOCAL_RESEARCH')

    def test_atomic_intake_does_not_hold_sqlite_writer_lock_during_compatibility(self):
        with TemporaryDirectory() as root:
            path=Path(root)/'registry.sqlite'
            class LocalExecutionProbe:
                def check(self,definition):
                    # A second real writer must remain admissible while E2 work
                    # runs outside the short canonical registration transaction.
                    with closing(sqlite3.connect(path,timeout=0.01)) as writer:
                        writer.execute('BEGIN IMMEDIATE')
                        writer.execute('CREATE TABLE IF NOT EXISTS unrelated_job_progress(n INTEGER)')
                        writer.execute('INSERT INTO unrelated_job_progress VALUES(1)')
                        writer.commit()
                    return DeferredCompatibilityBoundary().check(definition)
            with open_sqlite_platform(path,compatibility_boundary=LocalExecutionProbe()) as e6:
                try: result=e6.intake(definition_v02(),source_actor='FIXTURE',operation_id='fixture-op')
                except sqlite3.OperationalError: self.fail('Compatibility execution held the canonical SQLite writer lock')
                self.assertEqual('DRAFT',result.strategy.current_lifecycle_state)
                self.assertEqual('NOT_RUN',result.compatibility.status)
