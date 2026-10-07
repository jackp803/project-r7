from pathlib import Path
import hashlib,json,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002';sys.path.insert(0,str(repo/'src'))
from application.qualification import parse_result
from strategy.v02.capabilities import _revision
prefix='workspaces/project-r7-productization-master-20261002/'
reviewed={
 prefix+'src/application/cli.py':'b748d3848e53a507aa12868b15c863d3be397a17360a229097af43b0ca5231d3',
 prefix+'tests/product/test_paper_feedback_cli.py':'81b739b5ac5e53ddb803531111e16f658c5d4e795fb26b7320680d809adde331',
 prefix+'docs/product/v0_2/PAPER_FEEDBACK_IMPLEMENTATION.md':'92c2c0bb801fba14212d22dd741a41080fd60e4ae7f5e20fac7ac90ab135b5cc',
 'artifacts/S14-paper-feedback-cli-increment-plan.md':'c872f91acf6ebec3291974577380ccf13ad591cca8a6fe40fbdb0e7fb471fe0d',
 'artifacts/run_s14_paper_feedback_cli_increment.py':'15f13d2bc62e9d85a2ecb36df129fe821585b90370190bbd48b437f483519e5f',
 prefix+'src/storage/_sqlite_registry.py':'cf43e089e9d75fca2cb73d89e5588fbe5224d0668b967b4abefb1c7d8953ae5d',
 prefix+'src/storage/paper_process.py':'17bc52dcafa49b809188aab863708b2b21cc324daee282159cebe2c1d3cf427c',
 prefix+'tests/storage/test_paper_process_existing.py':'59ea7cb0034f80266e47f2b1b5b0f4b089e9df7000fea37cd4db41e3d86cb31f'}
for ref,expected in reviewed.items():assert hashlib.sha256((project/ref).read_bytes()).hexdigest()==expected
implementation=_revision();assert implementation=='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
proofs={}
for stem,count in (('S14-paper-feedback-cli-existing-race-GREEN',11),('S14-paper-feedback-cli-existing-race-affected-GREEN',90)):
    facts=json.loads((base/(stem+'.json')).read_bytes());raw=(base/(stem+'.log')).read_bytes()
    assert 'sha256:'+hashlib.sha256(raw).hexdigest()==facts['log_sha256']
    parsed=parse_result(raw.decode('utf-8'),returncode=facts['exit_code'])
    assert parsed.passed and parsed.tests_run==facts['tests_run']==count and facts['passed'] and facts['tree_reaped']
    assert facts['input_sha256_before']==facts['input_sha256_after'] and facts['source_before']==facts['source_after']
    assert facts['implementation_hash_before']==facts['implementation_hash_after']==implementation
    for ref,expected in facts['input_sha256_before'].items():assert 'sha256:'+hashlib.sha256((project/ref).read_bytes()).hexdigest()==expected
    proofs[stem]=dict(tests=count,log_sha256=facts['log_sha256'])
target=base/'S14-paper-feedback-cli-independent-source-review.json';assert not target.exists()
target.write_text(json.dumps(dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_HISTORICAL_PAPER_PUBLICATION_SOURCE_REVIEW',
    reviewer='/root/qualification_review',reviewer_execution='NONE',remaining_critical=0,remaining_important=0,
    reviewed_files={ref:'sha256:'+value for ref,value in reviewed.items()},
    resolved_important=['Existing-only SQLite mode=rw closes the checked-store-disappearance race'],
    limits=['Read-only bounded review; reviewer did not execute tests',
            'Not whole-branch/native/normal runtime/real cloud/qualified-release acceptance']),indent=2)+'\n',encoding='utf-8',newline='\n')
path=repo/'coordination/CODEX/PROGRESS.json';progress=json.loads(path.read_bytes())
assert progress['qualified_executable_revision']=='e293a947f886d9814c89983fd9e03151c1695788'
progress['historical_paper_cli_source_checkpoint']=dict(status='SOURCE_FOCUSED_PASS;EXACT_CLEAN_QUALIFICATION_PENDING',
    implementation_hash=implementation,focused_tests=11,affected_tests=90,proofs=proofs,
    independent_review='BOUNDED_READ_ONLY;8_FILES;0_CRITICAL_0_IMPORTANT',
    initial_red=dict(tests=7,failures=4,errors=0),existing_store_red=dict(tests=11,failures=1,error_occurrences=6),
    normal_runtime='NOT_RUN',native_historical_publication='NOT_RUN_PENDING_NEW_BUILD',real_cloud='NOT_RUN')
progress['next_step']='Run exact-clean qualification for the historical PAPER CLI composition with original full source limits and a new Windows native build. Preserve initial failures and the existing-only race repair; then retain/push sanitized evidence and continue normal runtime/qualification plumbing and S15 acceptance mapping.'
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=('Historical PAPER cloud CLI source increment: actual focused11 and affected90 tests PASS with owned reaping and unchanged source/implementation/input bindings; '
    'initial RED7/4 failures and existing-only race RED11/1 failure/6 TypeError error occurrences retained. '
    'Three outboxes share one batch budget/cloud host lock. Existing-only SQLite mode=rw refuses a disappearing canonical DB; original creating owner behavior retained. '
    'Independent bounded eight-file source/test/runner review0 Critical/Important. Full source/native/browser qualification of this new executable remains pending; accepted qualified revision stays e293a947f886d9814c89983fd9e03151c1695788. '
    'No normal runtime start,real cloud/provider calls,credentials,capital or GitHub compute. Continue automatically.\n\n')
handoff=repo/'coordination/CODEX/HANDOFF.md';handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
report=repo/'status/codex/productization/S14/PAPER_FEEDBACK_CLI_SOURCE_CHECKPOINT.md';assert not report.exists()
report.write_text('# Historical PAPER publication source checkpoint\n\n'+note+
    'Implementation and limits: `docs/product/v0_2/PAPER_FEEDBACK_IMPLEMENTATION.md`. '
    'This source increment is not a qualified software release or normal native runtime composition.\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(focused=11,affected=90,implementation=implementation,qualified_executable_unchanged=True)))
