"""Exercise the wrapper-to-reader path contract with no package/runtime creation."""
from pathlib import Path
import tempfile,unittest
import s09_paper_owner_composition_native_regression as driver
import s12_storage_native_paper_reader as reader

class NativeReaderHandoff(unittest.TestCase):
 def test_reader_receives_its_bound_output_and_full_revision_before_package_read(self):
  make=getattr(driver,'native_stages',None)
  self.assertTrue(callable(make),'Missing independently executable native stage constructor')
  with tempfile.TemporaryDirectory(prefix='r7-native-handoff-',dir=driver.BASE) as tmp:
   root=Path(tmp);package=root/'missing-package';revision='f'*40
   stages=make(revision,root/'build',package)
   argv=next(argv for label,argv,timeout in stages if label=='paper-reader')
   self.assertEqual(argv[-1],revision)
   self.assertEqual(Path(argv[2]),package)
   # The actual reader must pass its output-subject guard, then encounter the
   # deliberately absent package. A wrong prefix raises ValueError instead.
   with self.assertRaises(FileNotFoundError):
    reader._require_subject(package,Path(argv[3]),argv[4])
   self.assertFalse(package.exists())
   self.assertFalse(Path(argv[3]).exists())

if __name__=='__main__':unittest.main(verbosity=2)
