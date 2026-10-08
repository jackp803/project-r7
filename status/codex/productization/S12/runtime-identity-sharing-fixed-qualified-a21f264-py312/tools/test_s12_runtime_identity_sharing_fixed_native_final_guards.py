"""Actual final native proof gate regressions on public isolated input bytes."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
import s12_runtime_identity_sharing_fixed_native_regression as driver
from application.qualification import QualificationError

class FinalNativeProofGuards(unittest.TestCase):
 def test_helper_change_cannot_be_published_as_pass(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-native-input-',dir=driver.BASE) as tmp:
   p=Path(tmp)/'helper.py';p.write_bytes(b'original\n')
   def hashes():return {'helper':driver.sha(p.read_bytes())}
   value={'passed':False,'input_hashes_before':hashes()};p.write_bytes(b'changed\n')
   with patch.object(driver,'revision_fact',return_value={}),patch.object(driver,'verify_distribution',return_value={'build':'fixture'}):
    with self.assertRaises(AssertionError):driver.finalize_pass(value,hashes,Path(tmp),{'build':'fixture'},'a'*40)
   self.assertFalse(value['passed'])
 def test_final_dirty_revision_is_rechecked_before_pass(self):
  value={'passed':False,'input_hashes_before':{'helper':'fixture'}}
  with patch.object(driver,'revision_fact',side_effect=QualificationError('fixture DIRTY')),patch.object(driver,'verify_distribution',return_value={'build':'fixture'}):
   with self.assertRaises(QualificationError):driver.finalize_pass(value,lambda:{'helper':'fixture'},driver.BASE,{'build':'fixture'},'a'*40)
  self.assertFalse(value['passed'])
 def test_final_changed_package_identity_is_rechecked_before_pass(self):
  value={'passed':False,'input_hashes_before':{'helper':'fixture'}}
  with patch.object(driver,'revision_fact',return_value={}),patch.object(driver,'verify_distribution',return_value={'build':'changed'}):
   with self.assertRaises(AssertionError):driver.finalize_pass(value,lambda:{'helper':'fixture'},driver.BASE,{'build':'fixture'},'a'*40)
  self.assertFalse(value['passed'])

if __name__=='__main__':unittest.main(verbosity=2)
