from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class SourceResourceCommitmentTests(unittest.TestCase):
    def test_sql_authority_changes_invalidate_source_identity(self):
        from strategy.v02 import capabilities
        self.assertTrue(hasattr(capabilities, '_source_revision'), 'Missing resource-aware source commitment')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'owner.py').write_bytes(b'owner = 1\r\n')
            (root / 'migrations').mkdir()
            sql = root / 'migrations/0001.sql'
            sql.write_bytes(b'SELECT 1;\r\n')
            original = capabilities._source_revision(root)
            sql.write_bytes(b'SELECT 2;\n')
            self.assertNotEqual(original, capabilities._source_revision(root))
            sql.write_bytes(b'SELECT 1;\n')
            self.assertEqual(original, capabilities._source_revision(root))
            (root / 'runtime.sqlite').write_bytes(b'local mutable database')
            self.assertEqual(original, capabilities._source_revision(root))
