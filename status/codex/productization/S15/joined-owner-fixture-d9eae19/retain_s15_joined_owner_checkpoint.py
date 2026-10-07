"""Retain exact reviewed joined-owner fixtures and immutable execution proof."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,types
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest()
snapshots={}
def capture(name,expected=None):
    value=read_local(base,name,8*1024*1024)
    if expected is not None and digest(value)!=expected:raise ValueError('Reviewed commitment changed')
    snapshots[name]=value;return value
def main(review_sha):
    assert re.fullmatch(r'sha256:[0-9a-f]{64}',review_sha)
    review=json.loads(capture('S15-joined-owner-retention-review.json',review_sha))
    assert review['reviewer']=='/root/qualification_review' and review['reviewer_execution']=='NONE'
    assert all(review[k]==0 for k in ('remaining_critical','remaining_important','remaining_minor'))
    labels=('S15-joined-owner-owner-evidence-NORMAL','S15-joined-owner-owner-evidence-MUTATION')
    harness=('s15_joined_owner_acceptance_cases.py','s15_joined_owner_fixture_child.py','run_s15_joined_owner_fixture.py')
    names=set(harness)|{label+suffix for label in labels for suffix in ('.json','.log')}|{Path(__file__).name,'s14_feedback_cli_acceptance_core.py'}
    assert set(review['reviewed_original_artifacts'])=={'artifacts/'+name for name in names}
    for reference,sha in review['reviewed_original_artifacts'].items():capture(Path(reference).name,sha)
    assert digest(snapshots['s14_feedback_cli_acceptance_core.py'])=='sha256:a3bd7e32bb805cebfdb5a26994cd712bc47b1bb995dae0c51dd7a09522a9c7b0'
    core=types.ModuleType('s15_joined_fixed_core');core.__dict__['__file__']=str(base/'s14_feedback_cli_acceptance_core.py')
    exec(compile(snapshots['s14_feedback_cli_acceptance_core.py'],core.__dict__['__file__'],'exec'),core.__dict__)
    head='d9eae1948774b6ab97fb18c6545d79cda5395cf1';revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
    implementation='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
    assert revision_fact(repo,head,True)==dict(revision=head,worktree='CLEAN') and _revision()==implementation
    git=r'C:\Program Files\Git\cmd\git.exe'
    changed=subprocess.check_output([git,'diff','--name-only',revision,head],cwd=repo).decode().splitlines()
    assert all(name.startswith(('status/','coordination/')) for name in changed)
    test_names=subprocess.check_output([git,'ls-files','--','tests/**/*.py'],cwd=repo).decode().splitlines()
    expected_refs={(repo/name).relative_to(project).as_posix() for name in test_names}|{'artifacts/'+name for name in harness}
    assert len(expected_refs)==223
    positive='test_joined_cloud_intake_research_paper_ready_api_and_exact_feedback_ack'
    negatives=('test_joined_genuine_oos_loss_rejects_without_paper_run','test_joined_changed_sealed_input_denies_queue_and_research_evidence')
    for label,mode,failures,code in ((labels[0],'NORMAL',0,0),(labels[1],'MUTATION_CONTROL',1,1)):
        proof=json.loads(snapshots[label+'.json']);log=snapshots[label+'.log'].decode('utf-8')
        assert proof['mode']==mode and proof['exit_code']==code and proof['tests_run']==3 and proof['failures']==failures
        assert all(proof[k]==0 for k in ('errors','skipped','expected_failures','unexpected_successes'))
        parsed=parse_result(log,returncode=code)
        assert parsed.tests_run==3 and parsed.failures==failures and parsed.errors==parsed.skipped==parsed.expected_failures==parsed.unexpected_successes==0
        assert proof['log_sha256']==digest(snapshots[label+'.log']) and proof['tree_reaped'] and proof['fixture_scratch_empty']
        assert proof['fixture_scratch_cleanup']=='REMOVED_VERIFIED_EMPTY_ROOT'
        assert proof['source_before']==proof['source_after']==dict(revision=head,worktree='CLEAN')
        assert proof['implementation_hash_before']==proof['implementation_hash_after']==implementation
        assert proof['input_sha256_before']==proof['input_sha256_after'] and set(proof['input_sha256_before'])==expected_refs
        for reference,sha in proof['input_sha256_before'].items():
            path=project/reference;assert path.is_relative_to(project) and '..' not in Path(reference).parts
            assert digest(read_local(path.parent,path.name,1024*1024))==sha
        for name in negatives:
            assert re.search(r'^'+name+r' \(s15_joined_owner_acceptance_cases\.JoinedOwnerAcceptanceTests\.'+name+r'\) \.\.\. ok$',log,re.M)
        if mode=='NORMAL':
            assert proof['passed'] and parsed.passed and not proof['mutation_control_detected']
            assert re.search(r'^'+positive+r' \(s15_joined_owner_acceptance_cases\.JoinedOwnerAcceptanceTests\.'+positive+r'\) \.\.\. ok$',log,re.M)
        else:
            assert not proof['passed'] and proof['mutation_control_detected'] and proof['mutation_ack_failure_point_observed']
            assert re.findall(r'^FAIL: (test_\w+) \(',log,re.M)==[positive]
            assert re.search(r'^AssertionError: 0 != 1 : JOINED_CLOUD_OUTAGE_MUST_REMAIN_UNACKNOWLEDGED$',log,re.M)
        assert proof['real_provider_requests']==0 and proof['credentials']=='NONE' and proof['capital']=='NONE' and proof['real_forward']=='NOT_RUN'
        assert proof['github_compute']=='NOT_USED'
    history=['s15_joined_owner_acceptance_cases.before-thread-affinity-repair.py','s15_joined_owner_acceptance_cases.before-exit-evidence-repair.py',
        'S15-joined-owner-first-NORMAL.json','S15-joined-owner-first-NORMAL.log','S15-joined-owner-thread-owned-NORMAL.json','S15-joined-owner-thread-owned-NORMAL.log',
        'diagnose_s15_joined_paper_api.py','S15-joined-paper-api-diagnostic.json','S15-joined-paper-api-diagnostic.log',
        'S15-joined-paper-api-owner-diagnostic.json','S15-joined-paper-api-owner-diagnostic.log']
    for name in history:capture(name)
    ref='status/codex/productization/S15/joined-owner-fixture-d9eae19';target=repo/ref
    manifest=repo/'status/codex/productization/S15/joined-owner-fixture-artifact-hashes-d9eae19.json'
    assert not target.exists() and not manifest.exists();target.mkdir(parents=True)
    entries=[];required={}
    for name,value in snapshots.items():
        public=_sanitize(value.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8');(target/name).write_bytes(public)
        original='artifacts/'+name;required[original]=digest(value)
        entries.append(dict(original_ref=original,original_sha256=digest(value),retained_file=name,retained_sha256=digest(public),
            role='HISTORY_OR_DIAGNOSTIC;NOT_ACCEPTANCE' if name in history else 'CURRENT_REVIEWED_SCOPED_FIXTURE_EVIDENCE;NOT_MASTER_ACCEPTANCE',
            transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',state='IN_PROGRESS',execution_revision=head,
        qualified_executable_revision=revision,implementation_hash=implementation,status='THREE_JOINED_OWNER_SOURCE_FIXTURE_CASES_PASS',
        tests_run=3,failures=0,errors=0,skipped=0,expected_failures=0,unexpected_successes=0,false_ack_mutation_tests=3,
        false_ack_mutation_failures=1,false_ack_mutation_errors=0,exact_ack_failure_point=True,owned_tree_reaped=True,fixture_scratch_cleanup='PASS',
        input_commitments=223,original_1953_index_addition=0,requirement_pass_claims=0,
        fixture_origin='SOURCE_CREATED_ACTUAL_CLOUD_FAKE_TRANSPORT_E2_E3_E5_E6_API_PAPER_FEEDBACK_JOINED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION',
        exercised=['Fake-remote exact-byte author pull;actual sealed intake and research queue','Actual compatibility/research/robustness/frozen-finalist/sealedOOS candidate or genuine loss rejection',
            'Same canonical E6 database;thread-owned API and worker connections;idempotent API PAPER start','Actual ACK versus fill/protection/E5 target exit/canonical CLOSED graph/E3 metrics',
            'Explicit accelerated fixture READY;actual elapsed0;financial authority NONE','Actual API read projections;immutable PAPER feedback outbox;offline nonACK/retry/exact fake-remote byteACK'],
        limits=['Three new cases separate from1953 qualification and separate5tactical probes. No new full requirement PASS/native/browser/master acceptance.',
            'Fixture policy/release fingerprints are public synthetic inputs;no production qualification issuance/realforward/provider or capital authority.',
            'First run3failures included tuple-type assertions and main-to-ASGI SQLite connection reuse. Diagnostic confirmed thread-affinity error;minimal fixture factory repair.',
            'Intermediate3tests1failure read exit reason from transient PaperStep;final assertion reads actual durable E5 exit_action. Both failures retained as history.',
            'ASGI projections are not actual browser whole-flow. Normal native PAPER,Ubuntu,capacity,S16 and real commissioning remain pending.'],
        real_provider_requests=0,credentials='NONE',capital='NONE',runtime_llm_calls=0,github_compute='NOT_USED')
    def write(name,value):(target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    write('disposition.json',disposition);write('required-inputs.json',required);write('retention-index.json',entries)
    core.publish_retention_manifest(target,manifest,entries,required,repository_root=repo)
    assert _revision()==implementation
    print(json.dumps(dict(retained_files=len(list(target.iterdir())),new_joined_fixture_cases=3,detected_false_ack_failures=1,requirement_pass_claims=0)))
if __name__=='__main__':main(sys.argv[1])
