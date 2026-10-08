"""Scoped sleep request cleanup; no real sleep or persistent power-policy changes."""
import importlib,importlib.util,unittest

class AwakeRequestTests(unittest.TestCase):
 def guard(self):
  self.assertIsNotNone(importlib.util.find_spec('local_windows_qualification_awake'),'Scoped Windows awake guard is absent')
  return importlib.import_module('local_windows_qualification_awake').awake_request
 def test_request_is_released_after_success(self):
  calls=[]
  def api(flags):calls.append(flags);return 0x80000000
  with self.guard()(set_state=api) as evidence:self.assertEqual(calls,[0x80000001])
  self.assertEqual(calls,[0x80000001,0x80000000]);self.assertTrue(evidence['restored'])
 def test_previous_thread_requirements_are_restored_on_exception(self):
  calls=[]
  def api(flags):calls.append(flags);return 0x80000002
  with self.assertRaisesRegex(ValueError,'fixture failure'):
   with self.guard()(set_state=api):raise ValueError('fixture failure')
  self.assertEqual(calls,[0x80000001,0x80000002])
 def test_request_failure_denies_execution(self):
  calls=[]
  def api(flags):calls.append(flags);return 0
  with self.assertRaises(OSError):
   with self.guard()(set_state=api):self.fail('Unheld request allowed operation')
  self.assertEqual(calls,[0x80000001])
 def test_release_failure_cannot_claim_restoration(self):
  calls=[]
  def api(flags):calls.append(flags);return 0x80000000 if len(calls)==1 else 0
  with self.assertRaises(OSError):
   with self.guard()(set_state=api) as evidence:pass
  self.assertFalse(evidence['restored'])

if __name__=='__main__':unittest.main(verbosity=2)
