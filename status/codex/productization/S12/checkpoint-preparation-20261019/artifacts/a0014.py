"""Actual pinned private file checks only, never native qualification credit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import time,unittest
import verify_qualified_backup_checkpoint as helper
from application.platform.private_files import create_private_directory,write_private_new

class QualifiedBackupHelperFileChecks(unittest.TestCase):
    def test_valid_sealed_snapshot_copies_match_and_one_changed_seal_denies(self):
        with TemporaryDirectory(dir=helper.BASE,prefix='backup-helper-unit-') as temporary:
            roots=[Path(temporary)/name for name in ('original','captured','restored','recaptured')]
            relative='snapshots/'+'1'*64+'/.seal.json';raw=b'{"immutable_snapshot":"bounded_source_fixture"}\n'
            for root in roots:
                create_private_directory(root);create_private_directory(root/'snapshots');create_private_directory(root/'snapshots'/('1'*64))
                write_private_new(root/relative,raw)
            row=dict(relative_path=relative,bytes=len(raw),sha256=helper.sha(raw))
            helper.require_same_captured_file(roots,row,time.monotonic()+30)
            (roots[2]/relative).write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'four-way file equality'):helper.require_same_captured_file(roots,row,time.monotonic()+30)

if __name__=='__main__':unittest.main(verbosity=2)
