"""Prepare an explicit current-candidate execution-index refresh without altering history."""
from pathlib import Path
base=Path(__file__).resolve().parent
def create(old,new,replacements):
    text=(base/old).read_text(encoding='utf-8')
    for before,after in replacements:
        assert before in text,(old,before)
        text=text.replace(before,after)
    target=base/new;assert not target.exists()
    target.write_text(text,encoding='utf-8',newline='\n')
create('test_s15_execution_index.py','test_s15_execution_index_fec8af0.py',[
 ('build_s15_execution_index.py','build_s15_execution_index_fec8af0.py')])
create('run_s15_execution_index_tests.py','run_s15_execution_index_fec8af0_tests.py',[
 ('test_s15_execution_index','test_s15_execution_index_fec8af0'),
 ('build_s15_execution_index.py','build_s15_execution_index_fec8af0.py')])
create('build_s15_execution_index.py','build_s15_execution_index_fec8af0.py',[
 ('e293a947f886d9814c89983fd9e03151c1695788','fec8af0f70d787deea720b1e7f952c4fca9487b5'),
 ('1942','1953'),('1695','1706'),
 ('build_s15_execution_index.py','build_s15_execution_index_fec8af0.py'),
 ('test_s15_execution_index.py','test_s15_execution_index_fec8af0.py'),
 ('run_s15_execution_index_tests.py','run_s15_execution_index_fec8af0_tests.py'),
 ('S15-executed-case-index-reference-order-GREEN','S15-executed-case-index-fec8af0-current-GREEN'),
 ('r7-productization-S12-runtime-supervision-qualified-','r7-productization-S14-feedback-cli-qualified-'),
 ('s12_runtime_supervision_source_qualify.py','s14_feedback_cli_source_qualify.py'),
 ("raw=path.read_bytes();actual=", "raw=read_local(path.parent,path.name,8*1024*1024);actual=")])
print('Prepared three new candidate-bound files; previous tools and proofs preserved')
