from pathlib import Path
from unittest.mock import patch
import unittest,uuid
import finish_bffc558_evidence as helper
BASE=Path(__file__).resolve().parent
class FinisherReadbackTests(unittest.TestCase):
 def test_nested_readback_uses_target_relative_protected_reader(self):
  directory=BASE/'finisher-readback-probe'/uuid.uuid4().hex
  directory.mkdir(parents=True,exist_ok=False)
  path=directory/'proof.json';raw=b'{"public":true}\n'
  with patch.object(helper,'TARGET',directory),patch.object(helper,'artifact_bytes',return_value=raw) as reader:
   helper.write_new(path,raw)
   reader.assert_called_once_with(directory,'proof.json')
 def test_over_limit_refuses_before_creation(self):
  directory=BASE/'finisher-readback-probe'/uuid.uuid4().hex
  directory.mkdir(parents=True,exist_ok=False);path=directory/'oversized.json'
  with patch.object(helper,'LIMIT',1):
   with self.assertRaises(AssertionError):helper.write_new(path,b'xx')
  self.assertFalse(path.exists())
if __name__=='__main__':unittest.main(verbosity=2)
