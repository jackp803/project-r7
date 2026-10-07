from pathlib import Path
import ast
base=Path(__file__).resolve().parent
for source_name,target_name in (
    ('test_s12_runtime_supervision_qualification_integrity.py','test_s14_feedback_cli_qualification_integrity.py'),
    ('run_s12_runtime_supervision_qualification_integrity.py','run_s14_feedback_cli_qualification_integrity.py')):
    target=base/target_name;assert not target.exists()
    code=(base/source_name).read_text(encoding='utf-8').replace('s12_runtime_supervision_', 's14_feedback_cli_')
    if source_name.startswith('test_'):
        code=code.replace('import ast\n','import ast\nimport sys\n')
        code=code.replace('class PipelineDependencyBindingTests', '''class NativeHistoricalBindingTests(unittest.TestCase):
 def finalize(self,*,cleanup_ok,earlier_failure=False):
  tree=ast.parse(Path(__file__).with_name('s14_feedback_cli_native_paper.py').read_bytes())
  final=next(node.finalbody for node in tree.body if isinstance(node,ast.Try))
  owner=unittest.TestCase()
  if not cleanup_ok:
   def fail():raise RuntimeError('CONTROLLED_FIXTURE_CLEANUP_FAILURE')
   owner.addCleanup(fail)
  report=dict(passed=not earlier_failure)
  if earlier_failure:report['failure_class']='ValueError'
  observed=[]
  body=[ast.Raise(exc=ast.Call(func=ast.Name(id='ValueError',ctx=ast.Load()),args=[],keywords=[]))] if earlier_failure else [ast.Pass()]
  module=ast.fix_missing_locations(ast.Module(body=[ast.Try(body=body,handlers=[],orelse=[],finalbody=final)],type_ignores=[]))
  error=None
  try:exec(compile(module,'<actual-native-finalization>','exec'),dict(owner=owner,report=report,persist=lambda:observed.append(dict(report)),sys=sys))
  except BaseException as caught:error=caught
  return report,observed,error
 def test_failed_actual_fixture_cleanup_refuses_retained_pass_and_successful_exit(self):
  report,observed,error=self.finalize(cleanup_ok=False)
  self.assertIsInstance(error,RuntimeError)
  self.assertFalse(report['passed']);self.assertFalse(report['fixture_cleanup_complete'])
  self.assertEqual(observed,[report])
 def test_successful_actual_fixture_cleanup_preserves_retained_pass(self):
  report,observed,error=self.finalize(cleanup_ok=True)
  self.assertIsNone(error);self.assertTrue(report['passed']);self.assertTrue(report['fixture_cleanup_complete'])
  self.assertEqual(observed,[report])
 def test_cleanup_failure_preserves_earlier_native_exception_and_failed_receipt(self):
  report,observed,error=self.finalize(cleanup_ok=False,earlier_failure=True)
  self.assertIsInstance(error,ValueError);self.assertEqual(report['failure_class'],'ValueError')
  self.assertFalse(report['passed']);self.assertFalse(report['fixture_cleanup_complete']);self.assertEqual(observed,[report])
 def test_native_paper_script_and_compiled_fake_source_are_in_bound_pipeline(self):
  tree=ast.parse(Path(__file__).with_name('s14_feedback_cli_candidate_pipeline.py').read_bytes())
  names=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
   and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
  self.assertIn('s14_feedback_cli_native_paper.py',names)
  self.assertIn('S14LocalFakeRclone.cs',names)

class PipelineDependencyBindingTests''')
    else:
        code=code.replace('result.tests_run==6','result.tests_run==10')
    ast.parse(code);target.write_text(code,encoding='utf-8',newline='\n')
print('Prepared ten actual wrapper/pipeline/fixture cleanup guard tests')
