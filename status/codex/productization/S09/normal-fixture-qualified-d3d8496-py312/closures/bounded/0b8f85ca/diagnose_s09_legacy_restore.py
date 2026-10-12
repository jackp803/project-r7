"""Observe existing minimal E6 fixture restore failure; no qualification credit."""
from pathlib import Path
import sys,unittest
repo=Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from tests.application.test_database_restore import DatabaseRestoreTests
def observe(frame,event,arg):
    if event=='exception' and frame.f_code.co_filename.endswith('database_restore.py'):
        cls,value,_=arg
        print('ACTUAL_SYNTHETIC_RESTORE_EXCEPTION',frame.f_code.co_name,cls.__name__,str(value),file=sys.stderr,flush=True)
    return observe
sys.settrace(observe)
try:
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([DatabaseRestoreTests('test_actual_e6_dispatch_and_paper_generations_advance_without_replaying_effects')]))
finally:
    sys.settrace(None)
raise SystemExit(0 if result.wasSuccessful() else 1)
