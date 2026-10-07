"""Two actual regressions for consumed-input binding and inherited package paths."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import s12_qualification_receipt_bound_regression as driver
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits

class BoundRegressionTests(unittest.TestCase):
 def test_other_executed_test_and_helper_mutations_change_commitment(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-input-guard-',dir=driver.BASE) as tmp:
   root=Path(tmp);repo=root/'repo';repo.mkdir()
   for name in driver.FILES:
    path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture\n',encoding='utf-8')
   other=repo/'tests/application/test_other_owner.py';other.parent.mkdir(parents=True);other.write_text('original\n')
   helper=root/'helper.py';helper.write_text('original helper\n');launcher=root/'launcher.py';launcher.write_text('launcher\n')
   subprocess.run(['git','init','-q',str(repo)],check=True,capture_output=True)
   subprocess.run(['git','add','.'],cwd=repo,check=True,capture_output=True)
   original=driver.capture_inputs(repo,helper,launcher)
   other.write_text('changed executed test\n')
   self.assertNotEqual(original,driver.capture_inputs(repo,helper,launcher),'An executed owner test changed without changing the commitment')
   original=driver.capture_inputs(repo,helper,launcher);helper.write_text('changed helper\n')
   self.assertNotEqual(original,driver.capture_inputs(repo,helper,launcher),'Imported proof helper changed without changing the commitment')
 def test_hostile_ambient_package_path_is_replaced_for_child_and_descendant(self):
  with tempfile.TemporaryDirectory(prefix='r7-s12-package-guard-',dir=driver.BASE) as tmp:
   fake=Path(tmp);package=fake/'storage';package.mkdir();(package/'__init__.py').write_text('marker=True\n')
   code="import json,pathlib,storage,subprocess,sys; print(json.dumps([str(pathlib.Path(storage.__file__).resolve()),subprocess.check_output([sys.executable,'-c','import pathlib,storage;print(pathlib.Path(storage.__file__).resolve())'],text=True).strip()]))"
   with patch.dict(os.environ,{'PYTHONPATH':str(fake)}):
    env=driver.child_environment()
    with tempfile.TemporaryFile() as output:
     owned=spawn_owned([sys.executable,'-c',code],cwd=driver.REPO,limits=ResourceLimits(20),stdout=output,stderr=subprocess.STDOUT,env=env)
     try:
      self.assertEqual(owned.wait(),0);self.assertTrue(terminate_owned(owned,deadline_seconds=5).reaped)
      output.seek(0);actual=json.loads(output.read().decode('utf-8'))
     finally:self.assertTrue(terminate_owned(owned,deadline_seconds=5).reaped)
   expected=str((driver.REPO/'src/storage/__init__.py').resolve())
   self.assertEqual(actual,[expected,expected])

if __name__=='__main__':unittest.main(verbosity=2)
