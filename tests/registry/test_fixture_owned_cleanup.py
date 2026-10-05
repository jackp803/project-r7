from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sqlite3,sys,unittest
from application.research.service import ResearchService,ResearchError
from application.platform.resources import inspect_hardware
from tests.registry import test_operational_lifecycle_v02
class FixtureCleanup(unittest.TestCase):
    def test_failure_before_fixture_return_closes_both_actual_research_databases(self):
        created=[];original=ResearchService.__init__
        def track(service,**kwargs):original(service,**kwargs);created.append(service)
        with TemporaryDirectory() as root:
            measured=replace(inspect_hardware(Path(root)),available_memory_bytes=0)
            try:
                with patch.object(ResearchService,'__init__',track),patch('application.research.service.inspect_hardware',return_value=measured):
                    with self.assertRaises(ResearchError) as caught:test_operational_lifecycle_v02.OperationalLifecycleTests().fixture(root)
                self.assertEqual(caught.exception.code,'RESEARCH_MEMORY_PRESSURE')
                self.assertEqual(len(created),1)
                for db in (created[0].journal._db,created[0].ledger._db):
                    with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            finally:
                # Only this new private synthetic fixture's owned handles.
                for service in created:service.close()
if __name__=='__main__':unittest.main(verbosity=2)
