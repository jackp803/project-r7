"""Bounded public metadata tracing for the failed synthetic restored backup."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
events=[]
selected={'product_backup.py','backup.py','private_files.py','safe_files.py'}
def trace(frame,event,arg):
    path=Path(frame.f_code.co_filename)
    if path.name not in selected:return None
    if event=='exception':
        error=arg[1]
        lengths={name:len(str(frame.f_locals[name])) for name in ('source','target','path','root','destination')
                 if isinstance(frame.f_locals.get(name),Path)}
        events.append(dict(module=path.name,function=frame.f_code.co_name,line=frame.f_lineno,
            exception_type=type(error).__name__,errno=getattr(error,'errno',None),winerror=getattr(error,'winerror',None),path_lengths=lengths))
        del events[:-60]
    return trace

name='tests.application.test_product_data_backup.ProductDataBackupTests.test_complete_restored_generation_can_be_backed_up_again_without_reusing_its_profile'
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for _ in range(3))
sys.settrace(trace)
try:result=unittest.TextTestRunner(verbosity=2).run(suite)
finally:sys.settrace(None)
print('R7_SYNTHETIC_BACKUP_DIAGNOSTIC '+json.dumps(dict(scope='EXCEPTION_TYPE_CODE_AND_PATH_LENGTH_ONLY;NO_PRIVATE_BYTES_OR_ERROR_MESSAGES',events=events)),flush=True)
raise SystemExit(0 if result.wasSuccessful() else 1)
