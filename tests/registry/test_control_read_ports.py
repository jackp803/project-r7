from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from storage.platform import open_sqlite_platform
from tests.validation.robustness_fixtures import subject


class ControlReadPortTests(unittest.TestCase):
    def test_bounded_e6_inventory_and_counts_use_actual_immutable_subjects(self):
        with TemporaryDirectory() as root, open_sqlite_platform(Path(root)/'registry.sqlite', research_namespace='FIXTURE') as e6:
            self.assertTrue(hasattr(e6, 'list_strategies'), 'Missing read-only bounded E6 inventory port')
            self.assertEqual(e6.list_strategies(limit=50, offset=0), ())
            self.assertEqual(e6.lifecycle_counts(), {})
            outcome = e6.intake(subject(), source_actor='fixture-local-intake', operation_id='fixture-control-intake')
            self.assertEqual(e6.list_strategies(limit=1, offset=0), (outcome.strategy,))
            self.assertEqual(e6.list_strategies(limit=1, offset=1), ())
            self.assertEqual(e6.lifecycle_counts(), {'DRAFT': 1})
            self.assertFalse(hasattr(e6, 'connection'))
            for limit, offset in ((0, 0), (201, 0), (True, 0), (1, -1)):
                with self.subTest(limit=limit, offset=offset), self.assertRaises(ValueError): e6.list_strategies(limit=limit, offset=offset)


if __name__ == '__main__': unittest.main()
