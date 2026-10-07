"""Retain reviewed partial mappings and separately executed tactical FIXTUREs."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,re,subprocess,sys,types
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import _sanitize,parse_result
from strategy.v02.capabilities import _revision
digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest()
snapshots={}
def capture(path,expected=None):
    value=read_local(path.parent,path.name,8*1024*1024)
    if expected is not None and digest(value)!=expected:raise ValueError('Reviewed input commitment changed')
    return value
def artifact(name,expected=None):
    value=capture(base/name,expected);snapshots[name]=value;return value
def decode(value):return json.loads(value)
def core():
    value=artifact('s14_feedback_cli_acceptance_core.py','sha256:a3bd7e32bb805cebfdb5a26994cd712bc47b1bb995dae0c51dd7a09522a9c7b0')
    module=types.ModuleType('s15_owner_temporal_bound_core')
    exec(compile(value,str(base/'s14_feedback_cli_acceptance_core.py'),'exec'),module.__dict__)
    return module
def validate_support(index,matrix,selection,draft):
    requirements={row['id']:row for row in matrix['requirements']}
    cases={row['execution_instance_id']:row for row in index['cases']}
    commands={row['command_index']:row for row in index['commands']}
    assert draft['candidate_revision']==index['candidate_revision']
    assert draft['implementation_hash']==index['implementation_hash_after']
    assert draft['requirement_pass_claims']==0 and draft['legacy_applicability_or_mapping_pending']==150
    assert [r['id'] for r in selection['requirements']]==[r['requirement']['id'] for r in draft['requirements']]
    seen=set()
    for chosen,row in zip(selection['requirements'],draft['requirements']):
        assert row['requirement']==requirements[chosen['id']]
        assert row['requirement_status']=='NOT_RUN' and row['requirement_pass_claim'] is False
        assert row['supported_behavior']==chosen['supported_behavior'] and row['remaining']==chosen['remaining']
        assert len(row['supporting_executed_cases'])==len(chosen['selectors'])
        selected=[]
        for case in row['supporting_executed_cases']:
            original=cases[case['execution_instance_id']];command=commands[original['command_index']]
            definition=original['source_definition'];source=definition['source']
            assert original['phase']=='phase_2' and original['status']=='ok' and case['actual_outcome']=='PASS'
            assert case['command_index']==original['command_index'] and case['source']==source
            assert case['test_id']==definition['test_id'] and case['line']==definition['line']
            assert case['source_sha256']==draft['selected_test_source_hashes'][source]
            assert case['source_sha256']==index['input_sha256_before'][(repo/source).relative_to(project).as_posix()]
            for key,original_key in [('command','command'),('command_basis','command_basis'),('log_ref','log_ref'),
                  ('log_sha256','log_sha256'),('execution_window','observed_execution_window'),('command_duration_seconds','duration_seconds')]:
                assert case[key]==command[original_key]
            assert case['duration_basis']=='COMPLETE_COMMAND_ONLY;NO_PER_CASE_DURATION'
            selected.append([source,definition['test_id'].rsplit('.',1)[-1]]);seen.add(case['execution_instance_id'])
        assert selected==chosen['selectors']
    assert len(seen)==draft['selected_distinct_execution_instances']
    return seen
def validate_prior_support(index,matrix,old_snapshots):
    union=set();identifiers=[]
    for group in ('strategy','cloud','data-research'):
        policy=decode(old_snapshots[f'S15-{group}-support-selection-fec8af0.json'])
        draft=decode(old_snapshots[f'S15-{group}-support-draft-fec8af0.json'])
        union.update(validate_support(index,matrix,policy,draft));identifiers.extend(row['id'] for row in policy['requirements'])
    assert len(identifiers)==28 and len(union)==111
    return identifiers,union
def validate_tactical(proof,log,mode,names):
    assert proof['mode']==mode and proof['tests_run']==5 and proof['tree_reaped'] is True
    assert all(proof[key]==0 for key in ('errors','skipped','expected_failures','unexpected_successes'))
    assert proof['input_sha256_before']==proof['input_sha256_after']
    assert proof['source_before']==proof['source_after']==dict(revision='ad4565b8d7ec420540d45d02dfad81573eb08370',worktree='CLEAN')
    assert proof['implementation_hash_before']==proof['implementation_hash_after']=='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
    assert proof['harness_binding']=='BEFORE_AND_AFTER_EXECUTION'
    assert proof['fixture_origin']=='SOURCE_CREATED_ACTUAL_E2_E3_E5_E6_ACCELERATED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION'
    assert proof['real_provider_requests']==0 and proof['credentials']=='NONE' and proof['capital']=='NONE'
    assert proof['github_compute']=='NOT_USED' and proof['real_forward']=='NOT_RUN'
    assert digest(log)==proof['log_sha256']
    started=datetime.fromisoformat(proof['started_at_utc']);finished=datetime.fromisoformat(proof['finished_at_utc'])
    assert started.utcoffset()==finished.utcoffset()==timezone.utc.utcoffset(started) and finished>=started
    result=parse_result(log.decode('utf-8'),returncode=proof['exit_code'])
    for key in ('tests_run','failures','errors','skipped','expected_failures','unexpected_successes','returncode'):
        assert getattr(result,key)==proof[key]
    pattern=r'^(test_[A-Za-z0-9_]+) \(s15_tactical_owner_acceptance_cases\.TacticalOwnerAcceptanceTests\.\1\) \.\.\. (ok|FAIL)$'
    outcomes=dict(re.findall(pattern,log.decode('utf-8'),re.MULTILINE))
    assert set(outcomes)==set(names) and len(outcomes)==5
    if mode=='NORMAL':
        assert proof['passed'] is True and proof['exit_code']==0 and proof['failures']==0 and result.passed
        assert set(outcomes.values())=={'ok'}
    else:
        failed={'test_ack_is_cancelled_at_tactical_expiry_without_fill_or_plan_renewal',
            'test_expiry_boundary_denies_entry_after_actual_research_candidate_and_paper_gate',
            'test_original_not_yet_valid_interval_can_enter_only_when_valid_then_manage_after_expiry'}
        assert proof['passed'] is False and proof['exit_code']==1 and proof['failures']==3 and proof['mutation_control_detected'] is True
        assert {name for name,status in outcomes.items() if status=='FAIL'}==failed
    return outcomes
def main(review_sha):
    assert re.fullmatch(r'sha256:[0-9a-f]{64}',review_sha)
    substrate=core()
    review=decode(artifact('S15-owner-temporal-retention-review.json',review_sha))
    assert review['reviewer']=='/root/qualification_review' and review['reviewer_execution']=='NONE'
    assert all(review[key]==0 for key in ('remaining_critical','remaining_important','remaining_minor'))
    tool_names={Path(__file__).name,'s14_feedback_cli_acceptance_core.py'}
    assert set(review['reviewed_original_artifacts'])=={'artifacts/'+name for name in tool_names}
    for reference,expected in review['reviewed_original_artifacts'].items():artifact(Path(reference).name,expected)
    semantic=decode(artifact('S15-owner-temporal-semantic-review.json',review['semantic_review_sha256']))
    assert all(semantic[key]==0 for key in ('remaining_critical','remaining_important','remaining_minor'))
    assert semantic['reviewer_execution']=='NONE'
    for reference,expected in semantic['reviewed_original_artifacts'].items():
        assert Path(reference).parts[0]=='artifacts' and len(Path(reference).parts)==2
        artifact(Path(reference).name,expected)
    revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
    index=decode(capture(base/'S15-executed-case-index-fec8af0.json','sha256:3ce754311d3210ac5827500999543d87c56d2f5bb4e7eb1ac67e4a9aa0c72209'))
    matrix=decode(capture(repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json','sha256:a205373601ac6c2b5994c964b23ebe562c8f0aa3898ef2f2b6412988c1f5968f'))
    assert index['candidate_revision']==revision and index['indexed_execution_instances']==1953 and index['requirement_pass_claims']==0
    assert index['source_before']==index['source_after']==dict(revision=revision,worktree='CLEAN')
    assert _revision()==index['implementation_hash_after']
    prior='status/codex/productization/S15/scoped-source-support-fec8af0'
    manifest=decode(capture(repo/'status/codex/productization/S15/scoped-source-support-artifact-hashes-fec8af0.json',
        'sha256:73060e2671e2038d6bc9ffd8d617a2b631a4f76136b7d88f59fd5ae0b0c8db61'))
    assert len(manifest)==46
    old_snapshots={}
    for reference,expected in manifest.items():
        assert reference.startswith(prior+'/') and '..' not in Path(reference).parts
        old_snapshots[Path(reference).name]=capture(repo/reference,expected)
    old_ids,old_union=validate_prior_support(index,matrix,old_snapshots)
    new_union=set();new_ids=[];selected_sources={}
    for group,count,case_count in [('temporal',6,28),('lifecycle-trading',12,69)]:
        policy=decode(snapshots[f'S15-{group}-support-selection-fec8af0.json'])
        draft=decode(snapshots[f'S15-{group}-support-draft-fec8af0.json'])
        assert draft['selected_requirement_drafts']==len(policy['requirements'])==count
        assert draft['selected_distinct_execution_instances']==case_count
        new_union.update(validate_support(index,matrix,policy,draft));new_ids.extend(row['id'] for row in policy['requirements'])
        selected_sources.update(draft['selected_test_source_hashes'])
    assert len(new_ids)==len(set(new_ids))==18 and not set(old_ids).intersection(new_ids)
    assert len(new_union)==94 and len(old_union|new_union)==203
    for reference,expected in selected_sources.items():
        assert reference.startswith('tests/') and '..' not in Path(reference).parts
        capture(repo/reference,expected)
    tools=['s15_tactical_owner_acceptance_cases.py','s15_tactical_owner_fixture_child.py','run_s15_tactical_owner_fixture.py']
    tree=ast.parse(snapshots[tools[0]])
    names=[method.name for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='TacticalOwnerAcceptanceTests'
        for method in node.body if isinstance(method,ast.FunctionDef) and method.name.startswith('test_')]
    assert len(names)==len(set(names))==5
    reports=[]
    for mode in ('NORMAL','MUTATION_CONTROL'):
        stem='S15-tactical-owner-target-reason-'+mode
        proof=decode(artifact(stem+'.json',semantic['observed_execution_artifacts']['artifacts/'+stem+'.json']))
        log=artifact(stem+'.log',semantic['observed_execution_artifacts']['artifacts/'+stem+'.log'])
        validate_tactical(proof,log,mode,names);reports.append(proof)
    assert reports[0]['input_sha256_before']==reports[1]['input_sha256_before']
    git=r'C:\Program Files\Git\cmd\git.exe'
    tracked=subprocess.check_output([git,'ls-files','--','tests/**/*.py'],cwd=repo).decode('utf-8').splitlines()
    expected_refs={(repo/name).relative_to(project).as_posix() for name in tracked}|{'artifacts/'+name for name in tools}
    assert set(reports[0]['input_sha256_before'])==expected_refs
    for reference,expected in reports[0]['input_sha256_before'].items():
        if reference.startswith('artifacts/'):
            assert digest(snapshots[Path(reference).name])==expected
        else:capture(project/reference,expected)
    assert subprocess.check_output([git,'rev-parse','HEAD'],cwd=repo).decode().strip()=='ad4565b8d7ec420540d45d02dfad81573eb08370'
    assert not subprocess.check_output([git,'status','--porcelain'],cwd=repo).strip()
    changed=subprocess.check_output([git,'diff','--name-only',revision,'HEAD'],cwd=repo).decode().splitlines()
    assert all(name.startswith(('status/','coordination/')) for name in changed)
    history=['s15_tactical_owner_acceptance_cases.before-utc-fixture-fix.py',
        's15_tactical_owner_acceptance_cases.before-target-reason-review.py']
    history.extend(stem+suffix for stem in ['S15-tactical-owner-first-NORMAL','S15-tactical-owner-utc-fixed-NORMAL',
        'S15-tactical-owner-MUTATION_CONTROL'] for suffix in ('.json','.log'))
    for group in ('temporal','lifecycle-trading'):
        history.extend(f'S15-{group}-support-{stem}-fec8af0.before-semantic-review.json' for stem in ('selection','draft'))
        history.extend('prepare_s15_'+group.replace('-','_')+'_support_draft.py' for _ in range(1))
        history.append('resolve_s15_'+group.replace('-','_')+'_review.py')
    for name in history:artifact(name)
    ref='status/codex/productization/S15/owner-temporal-support-fec8af0'
    target=repo/ref;manifest_path=repo/'status/codex/productization/S15/owner-temporal-support-artifact-hashes-fec8af0.json'
    assert not target.exists() and not manifest_path.exists();target.mkdir(parents=True)
    retained=[];required={}
    for name,value in snapshots.items():
        public=_sanitize(value.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8')
        (target/name).write_bytes(public);original='artifacts/'+name;required[original]=digest(value)
        retained.append(dict(original_ref=original,original_sha256=digest(value),retained_file=name,retained_sha256=digest(public),
            role='HISTORY_OR_GENERATOR;NOT_CURRENT_ACCEPTANCE' if name in history else 'REVIEWED_CURRENT_SCOPED_EVIDENCE;NOT_REQUIREMENT_ACCEPTANCE',
            transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
    disposition=dict(document_kind='REVIEWED_PARTIAL_SOURCE_SUPPORT_AND_SEPARATE_TACTICAL_FIXTURE;NOT_COMPLETE_REQUIREMENT_RESULTS',
        task_id=index['task_id'],state='IN_PROGRESS',candidate_revision=revision,implementation_hash=index['implementation_hash_after'],
        selected_additional_support_rows=18,selected_additional_distinct_cases=94,cumulative_support_rows=46,
        cumulative_distinct_original_execution_instances=203,unselected_support_rows=20,complete_requirement_results_pending=66,
        legacy_applicability_or_mapping_pending=150,requirement_pass_claims=0,new_requirement_ids=new_ids,
        tactical_fixture_tests=5,tactical_fixture_source_revision=reports[0]['source_before'],tactical_fixture_result='PASS',
        tactical_temporal_mutation_tests=5,tactical_temporal_mutation_failures=3,tactical_temporal_mutation_errors=0,
        tactical_fixture_timing={key:reports[0][key] for key in ('started_at_utc','finished_at_utc')},
        source_qualification_tests=1953,source_qualification_commands=33,source_qualification_revision=revision,
        compatibility_basis='Git differences from fec8af0 to ad4565 are status/coordination only; full implementation hash and223 tactical inputs unchanged',
        reviewer_execution='NONE',retention_tool_regressions='NOT_NEWLY_EXECUTED;BOUNDED_REVIEW_AND_ACTUAL_RETENTION_VALIDATION',
        real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        limits=['203 is deduplicated across46 partial support rows; new5 tactical tests are separate and do not increase the1953 original qualification index.',
          'FIXTURE simulated approval/lifecycle labels and synthetic E7 facts are not financial/current native authority.',
          'No normal native PAPER, Ubuntu parity, real forward/cloud/provider,24GB capacity or master acceptance claimed.',
          'Full21-field requirement results and150 inherited applicability/mapping decisions remain pending.'])
    def write(name,value):(target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    write('disposition.json',disposition);write('required-inputs.json',required);write('retention-index.json',retained)
    substrate.publish_retention_manifest(target,manifest_path,retained,required,repository_root=repo)
    assert _revision()==index['implementation_hash_after']
    print(json.dumps(dict(retained_files=len(list(target.iterdir())),additional_support_rows=18,cumulative_rows=46,
        cumulative_original_cases=203,separate_tactical_cases=5,requirement_pass_claims=0)))
if __name__=='__main__':main(sys.argv[1])
