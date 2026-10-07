"""Execute the actual wrapper exit statement under controlled cleanup outcomes."""
import ast
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

class BoundInstallerExitTests(unittest.TestCase):
 def exit_for(self,code,reaped,filename='s12_runtime_supervision_bound_installer.py'):
  path=Path(__file__).with_name(filename)
  tree=ast.parse(path.read_bytes());statement=tree.body[-1]
  self.assertIsInstance(statement,ast.Raise)
  fragment=compile(ast.Module(body=[statement],type_ignores=[]),str(path),'exec')
  facts=dict(passed=code==0 and reaped,command=dict(exit_code=code,tree_reaped=reaped))
  with self.assertRaises(SystemExit) as raised:exec(fragment,dict(code=code,facts=facts))
  return raised.exception.code,facts
 def test_zero_child_exit_with_unreaped_tree_refuses_outer_success(self):
  code,facts=self.exit_for(0,False)
  self.assertFalse(facts['passed']);self.assertEqual(facts['command']['exit_code'],0)
  self.assertNotEqual(code,0)
 def test_successful_reaped_child_preserves_zero_wrapper_exit(self):
  code,facts=self.exit_for(0,True)
  self.assertTrue(facts['passed']);self.assertEqual(code,0)
 def test_failed_reaped_child_refuses_outer_success_and_retains_original_failure(self):
  code,facts=self.exit_for(7,True)
  self.assertFalse(facts['passed']);self.assertEqual(facts['command']['exit_code'],7)
  self.assertNotEqual(code,0)
 def test_integrity_runner_also_refuses_zero_child_exit_with_unreaped_tree(self):
  code,facts=self.exit_for(0,False,'run_s12_runtime_supervision_qualification_integrity.py')
  self.assertFalse(facts['passed']);self.assertNotEqual(code,0)

class PipelineDependencyBindingTests(unittest.TestCase):
 def inventory(self):
  base=Path(__file__).parent;tree=ast.parse((base/'s12_runtime_supervision_candidate_pipeline.py').read_bytes())
  names=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
   and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
  return base,tree,names
 def test_all_executed_external_python_imports_are_in_the_bound_inventory(self):
  base,tree,names=self.inventory();bound=set(names);required=set()
  for name in names:
   if not name.endswith('.py'):continue
   child=ast.parse((base/name).read_bytes())
   for node in ast.walk(child):
    if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith(('s12_','s13_','s14_')):
     required.add(node.module+'.py')
  self.assertIn('s13_native_access_integrity.py',required)
  self.assertFalse(required-bound,required-bound)
 def test_actual_pipeline_hash_guard_refuses_external_ssh_helper_replacement(self):
  base,tree,names=self.inventory()
  assignment=next(node for node in tree.body if isinstance(node,ast.Assign)
   and any(isinstance(target,ast.Name) and target.id=='hashes' for target in node.targets))
  guard=next(node for node in ast.walk(tree) if isinstance(node,ast.Assert) and ast.unparse(node.test)=='hashes() == before')
  with TemporaryDirectory(dir=base) as directory:
   folder=Path(directory)
   for name in names:(folder/name).write_bytes(b'CONTROLLED_HARNESS_BYTES')
   values=dict(base=folder,names=names,hashlib=hashlib)
   exec(compile(ast.Module(body=[assignment],type_ignores=[]),'<actual-pipeline-hash>','exec'),values)
   values['before']=values['hashes']();(folder/'s13_native_access_integrity.py').write_bytes(b'CONTROLLED_REPLACEMENT')
   with self.assertRaises(AssertionError):exec(compile(ast.Module(body=[guard],type_ignores=[]),'<actual-pipeline-guard>','exec'),values)

if __name__=='__main__':unittest.main(verbosity=2)
