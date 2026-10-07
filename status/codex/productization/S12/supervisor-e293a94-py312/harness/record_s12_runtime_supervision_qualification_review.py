"""Bind the independently reviewed pre-execution qualification harnesses."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
names={
    's12_runtime_supervision_candidate_pipeline.py':'2d519be7b0ea3b7ebe50f6b31d3f42dc766132f5383047f99e8b32b2aeac78c8',
    's12_runtime_supervision_ui_frontend.py':'9ced0fba9210adb8b5a32eca0fe4eeeaf807e84712865b18de2358ca5de51120',
    's12_runtime_supervision_bound_installer.py':'d5a8b888779c513ca8066e169bbb08028aa3538fd25a6032ad0dbcccfe9931bb',
    's12_runtime_supervision_source_qualify.py':'5cf7d295abbfb3ca6c09c6cae9ba67c30776eb0b5f4d45b13389d2ef983d8133',
    's12_runtime_supervision_serial_browser_qualify.py':'0eb8aaf2aa76a2fcc06f23bab9cbde9acc52b8d828d88a718d71b1b2fd9b4ead',
    'test_s12_runtime_supervision_qualification_integrity.py':'749cfc5f13c760633299607a7cddfd8e038652d98b149b54a6e5c5b74e8c4aa6',
    'run_s12_runtime_supervision_qualification_integrity.py':'dc6bf7b381a8f18baac3c8f9af1ddf4d1a9c6a6adae3584ad38e1b28dd2e9786',
    'run_s12_runtime_supervision_integrated.py':'0c108a3948ce08ff8dc3830dccbb888b87a0f455905098e0bfd340c9133f7878',
}
for name,sha in names.items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==sha
proof=json.loads((base/'S12-runtime-supervision-qualification-reviewed-integrity-GREEN.json').read_bytes())
assert proof['passed'] and proof['tests_run']==6 and proof['failures']==proof['errors']==proof['skipped']==0
assert proof['input_sha256_before']==proof['input_sha256_after'] and proof['tree_reaped']
assert proof['log_sha256']=='sha256:'+hashlib.sha256((base/'S12-runtime-supervision-qualification-reviewed-integrity-GREEN.log').read_bytes()).hexdigest()
for name,sha in names.items():
    if name in proof['input_sha256_before']:assert proof['input_sha256_before'][name]=='sha256:'+sha
doc=base.parent/'workspaces/project-r7-productization-master-20261002/docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md'
assert hashlib.sha256(doc.read_bytes()).hexdigest()=='6f39fbb685c254c8123483b2c3f903c421ec9b98410d62cc6ef56f9187aedca9'
report=dict(reviewer='/root/qualification_review',kind='INDEPENDENT_BOUNDED_READ_ONLY_PREEXECUTION_QUALIFICATION_HARNESS_REVIEW',
    remaining_critical=0,remaining_important=0,reviewer_execution='NONE',reviewed_files={name:'sha256:'+sha for name,sha in names.items()},
    reviewed_document=dict(ref='docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md',sha256='sha256:6f39fbb685c254c8123483b2c3f903c421ec9b98410d62cc6ef56f9187aedca9'),
    primary_regression=dict(report='S12-runtime-supervision-qualification-reviewed-integrity-GREEN.json',
        report_sha256='sha256:'+hashlib.sha256((base/'S12-runtime-supervision-qualification-reviewed-integrity-GREEN.json').read_bytes()).hexdigest(),
        log='S12-runtime-supervision-qualification-reviewed-integrity-GREEN.log',log_sha256=proof['log_sha256'],tests=6),
    resolved_important=['Qualification wording describes commitment-bound receipt, not an unproved immutable receipt'],
    pipeline_dependencies=14,guard_execution_bound_inputs=16,actual_tests='SEPARATE_CODEX_LOCAL_GUARD_FRAGMENT_RUN6PASS',
    normal_paper_worker='NOT_RUN',native='NOT_YET_EXECUTED_FOR_CANDIDATE',ubuntu='NOT_RUN',whole_branch='NOT_REVIEWED')
target=base/'S12-runtime-supervision-independent-qualification-harness-review.json'
assert not target.exists()
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded exact pre-execution harness review;0 remaining Critical/Important')
