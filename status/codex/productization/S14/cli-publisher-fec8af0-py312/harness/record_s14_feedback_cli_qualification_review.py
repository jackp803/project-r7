from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
files={
 's14_feedback_cli_candidate_pipeline.py':'0e59e29da6f7d15c46228215276ebd6a06dffb499306930474a86bfef94ec06a',
 's14_feedback_cli_ui_frontend.py':'d6e646aaafc0c7e957160eb7222c1e6b2d73259a3bb6c379afed9b3425ba6ad0',
 's14_feedback_cli_bound_installer.py':'939c22f97b93ff7272f1ffb5b8aa7fcd48f2c507c6865f2a1eec08d2bd66274d',
 's14_feedback_cli_source_qualify.py':'a9d16492d1056c2b4b49131487f25d350e0cfd412e067f539afb29a58d25132d',
 's14_feedback_cli_serial_browser_qualify.py':'729f6f5cb91107e9057ad4a05b5f6e458d811db6d8f0c24cdcc97fa171defa32',
 's14_feedback_cli_native_paper.py':'81aa2a6bbfd19a980095cbf168d7d3ea2c85a0f19ff012d720402d9dade218b5',
 'test_s14_feedback_cli_qualification_integrity.py':'379ca59311cd3aa7d00ec05e2708f6784049a680679b6c3ad73e5dd80515de7a',
 'run_s14_feedback_cli_qualification_integrity.py':'2910faa36cd8a87238974ceeae9fd3ddfb1446b2d45d10c31862561fa783a55f',
 'prepare_s14_feedback_cli_qualification.py':'07b98611dd7a161a5ac89058fdacdd9e0b4c67a328fafec8df57833cc09d84f8',
 'prepare_s14_feedback_cli_integrity.py':'ff2350b62ac9671d47f75f66f71bd925a480f246454103275faaef4c934ae24d'}
for name,expected in files.items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==expected
stem='S14-paper-feedback-cli-cleanup-integrity-GREEN'
proof=json.loads((base/(stem+'.json')).read_bytes())
assert proof['passed'] and proof['tests_run']==10 and proof['tree_reaped']
assert proof['input_sha256_before']==proof['input_sha256_after']
assert len(proof['input_sha256_before'])==18
for name,expected in proof['input_sha256_before'].items():assert 'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest()==expected
assert proof['log_sha256']=='sha256:'+hashlib.sha256((base/(stem+'.log')).read_bytes()).hexdigest()
target=base/'S14-paper-feedback-cli-independent-qualification-review.json';assert not target.exists()
target.write_text(json.dumps(dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_PREEXECUTION_QUALIFICATION_HARNESS_REVIEW',
    reviewer='/root/qualification_review',reviewer_execution='NONE',remaining_critical=0,remaining_important=0,
    reviewed_files={name:'sha256:'+value for name,value in files.items()},
    resolved_important=['Native fixture cleanup must succeed before retaining PASS or exiting successfully'],
    primary_regression=dict(report=stem+'.json',report_sha256='sha256:'+hashlib.sha256((base/(stem+'.json')).read_bytes()).hexdigest(),
        log=stem+'.log',log_sha256=proof['log_sha256'],tests=10),
    limits=['Read-only bounded review; reviewer did not execute tests',
            'No native runtime composition, whole-product or external commissioning acceptance']),indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded independently reviewed ten-file harness and fresh ten-test guard')
