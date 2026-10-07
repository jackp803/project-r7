from pathlib import Path
import py_compile

base=Path(__file__).resolve().parent
test=base/'test_s12_runtime_supervision_qualification_integrity.py'
runner=base/'run_s12_runtime_supervision_qualification_integrity.py'
assert not test.exists() and not runner.exists()
code=(base/'test_s14_feedback_harness_integrity.py').read_text(encoding='utf-8')
code=code.replace('run_s14_feedback_harness_integrity.py',runner.name).replace('s14_feedback_','s12_runtime_supervision_')
code=code.replace("('s13_','s14_')", "('s12_','s13_','s14_')")
test.write_text(code,encoding='utf-8',newline='\n')
py_compile.compile(str(test),doraise=True)
print('Prepared actual wrapper-exit and pipeline dependency/hash guard regressions')
