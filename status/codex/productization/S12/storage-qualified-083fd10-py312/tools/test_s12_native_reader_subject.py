"""Native reader admission against the actual built package; no HTTP/auth/runtime start."""
import unittest
from pathlib import Path
import s12_storage_native_paper_reader as driver

CURRENT='083fd10e419e3eec903c3597093ea56e465f57cd'
OLD='41fa2fe0d74435fed5831ed728af8b87c28883f0'
PACKAGE=driver.BASE/'r7-native-windows-S12-storage-083fd10/dist/R7'
class NativeReaderSubjectTests(unittest.TestCase):
    def test_actual_current_native_subject_is_accepted_without_creating_fixture(self):
        output=driver.BASE/f'r7-native-S12-storage-reader-fixed-reader-{CURRENT[:7]}'
        self.assertFalse(output.exists())
        try:identity,before=driver._require_subject(PACKAGE,output,CURRENT)
        except Exception as error:self.fail('Actual current native subject wrongly denied: '+str(error))
        self.assertEqual(identity['executable_revision'],CURRENT)
        self.assertEqual(before,dict(revision=CURRENT,worktree='CLEAN'))
        self.assertFalse(output.exists())
    def test_other_revision_cannot_admit_the_actual_current_native_build(self):
        output=driver.BASE/f'r7-native-S12-storage-reader-fixed-reader-{OLD[:7]}'
        with self.assertRaises(ValueError):driver._require_subject(PACKAGE,output,OLD)
        self.assertFalse(output.exists())
    def test_other_output_cannot_create_an_unbound_native_reader_fixture(self):
        output=driver.BASE/'r7-native-S12-storage-reader-fixed-unbound'
        with self.assertRaises(ValueError):driver._require_subject(PACKAGE,output,CURRENT)
        self.assertFalse(output.exists())
if __name__=='__main__':unittest.main(verbosity=2)
