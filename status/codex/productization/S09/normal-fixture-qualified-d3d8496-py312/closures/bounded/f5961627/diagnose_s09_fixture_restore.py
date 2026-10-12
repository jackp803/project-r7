"""Observe actual synthetic restore exceptions only; no product qualification."""
from pathlib import Path
import sys,unittest
repo=Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from tests.application.test_normal_fixture_worker import NormalFixtureWorkerTests
def observe(frame,event,arg):
    if event=='exception' and frame.f_code.co_filename.endswith('product_backup.py'):
        cls,value,_=arg
        print('ACTUAL_SYNTHETIC_RESTORE_EXCEPTION',frame.f_code.co_name,cls.__name__,str(value),flush=True)
    return observe
sys.settrace(observe)
try:
    suite=unittest.TestSuite([NormalFixtureWorkerTests('test_complete_normal_fixture_backup_preserves_protected_truth_and_restore_fences')])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
finally:
    sys.settrace(None)
raise SystemExit(0 if result.wasSuccessful() else 1)
