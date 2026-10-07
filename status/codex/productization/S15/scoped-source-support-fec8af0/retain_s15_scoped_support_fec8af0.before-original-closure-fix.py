"""Retain 28 reviewed partial support rows without issuing acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import _sanitize
from strategy.v02.capabilities import _revision
from s14_feedback_cli_acceptance_core import require_artifact,publish_retention_manifest
from s12_runtime_supervision_review_integrity import validate_primary_proof

revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
reviewed={
 'S15-strategy-support-selection-fec8af0.json':'33ba44324803e705ac8edc542f15827920a18e9197ac8f899fee28fe399c7ae8',
 'build_s15_strategy_support_draft.py':'d8d1511f32643800226a03ae3d26dc683672b8d1c1e5f4e42c1ba419b9206730',
 'S15-strategy-support-draft-fec8af0.json':'f30165d818d29db9502ded785b3623a6d8bfb1ec5b50b0b43b8ef5537dbe0c4e',
 'S15-cloud-support-selection-fec8af0.json':'432f9c8657c1d2c37938df2ba23054b6dbd3435bf7c6c7c64adaaf396ad8970c',
 'build_s15_cloud_support_draft.py':'48f49f2147a1dc413402e0b38d770d3641604221771c33bc5eff89bd900eb71a',
 'S15-cloud-support-draft-fec8af0.json':'207a0f6469e70b9898b6b7a18857732e2feb47df697d3699e894f909643dd35a',
 'S15-data-research-support-selection-fec8af0.json':'6348688302ba4c7b73138ef08ed74f943cc433b2d1fb28aa4770d64ebd8ded68',
 'build_s15_data_research_support_draft.py':'6711cc837303907129fa0ba540351540061af0f240dd3729731cf7194d9383e9',
 'S15-data-research-support-draft-fec8af0.json':'06ea69703438d1c4a8d789044a82fdcddef544ab53a1e464606fa18038d50226'}
source_review={
 'tests/strategy/test_legacy_compatibility.py':'bdf129087cae8fc67adb6f5d878bed2a268937e2e4a6d3d9e3c56abfddbb009f',
 'tests/strategy/test_v02_parser.py':'c47a9cf863651a6ce3db075de974b42f5bcbf2523a3e48359237fc3e1c0d6764',
 'tests/strategy/test_v02_operators.py':'e6a051b08818c2988ac577e667519f60039beca3605a64ea0042b87d059e5b24',
 'tests/strategy/test_v02_multitimeframe.py':'79c5199afe061f250ec00fce1e158d9332b0af2eb9e6361a0b1cfb314f659d1b',
 'tests/indicators/test_v02_golden.py':'f70b5733dbd84245c5c8411db08dbbd1c91cd9c98f7009972c53fdb6ccddc8a3',
 'tests/indicators/test_v02_incremental.py':'82c4824df4439cbbb08c230564bee52fb4ea5a65544649a031e7ec4f48aee459',
 'tests/application/test_cloud_intake.py':'422ff5bd623ab2369e3d8a8f12d8ce0b879f2b6a273c57f4a1e67d68ef79dc5a',
 'tests/application/test_authoring_roundtrip.py':'6382db14665da62c20af34f8764d14366c8e53763db1c17a51cf7e9851de55b9',
 'tests/application/test_claim_recovery.py':'5cafab1582edf257fa5339c58c592406b652bbdaf23540df367744f2ea9bbb13',
 'tests/application/test_outbox.py':'f5703a6e01085dede51c2c44f75ea6a51ddbb0ba0a4bfec0ba0763c9e722b1ef',
 'tests/application/test_cloud_bridge.py':'84a9021e1d05bcd304c8c627715dd9396075a10cc65df02401b0ebbc4cd31c47',
 'tests/application/test_feedback_redaction.py':'eaecb20a7fcc1f9c6e4852d06e6b9a42cfe4ffd3c622c57039de96908d16a0c2',
 'tests/application/test_dataset_binding.py':'de5cfb030c1aa3c31486842796839357b037407af0fd0d0ed39f9874849bd79b',
 'tests/application/test_research_pipeline.py':'4f309ddb48f23e5b459c7fbd708f45f6b378078145e359deda9fc5041fa8b2d4',
 'tests/application/test_research_e6_recovery.py':'8482a2fce1350fbdd9a4583b82b478b6e34cc84626824d179f1f426cebf18801',
 'tests/application/test_research_robustness.py':'8e66f87b2f914e3e6c472a02d0358cbdb89c308f099839d53eba71372a406835',
 'tests/validation/test_robustness_v02.py':'e9161ef5124151a79f2e3e7fd0d0483c1ebce1312252b95d646f62ee3ddc3db1',
 'tests/validation/test_holdout_ledger.py':'09e6e018dad192667b0c991702d3ac4e273ffbee3100cf33b319e915e551957e',
 'tests/validation/test_monte_carlo.py':'38d96f6eb69351291388a4f2606d4f1446732a95a1bf28cd726e955ca085851b',
 'tests/validation/test_walk_forward.py':'9a79fb3ac94db3d6b09b685033c18c162d625e2ffea25a1c451f6e8c566a88ae'}
digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest()
def raw(path,expected=None):
    value=read_local(path.parent,path.name,8*1024*1024);actual=digest(value)
    if expected is not None and actual!=expected:raise ValueError('Support evidence changed')
    require_artifact(path.parent,path.name,actual);return value
snapshots={name:raw(base/name,'sha256:'+expected) for name,expected in reviewed.items()}
index_raw=raw(base/'S15-executed-case-index-fec8af0.json');index=json.loads(index_raw)
prior='status/codex/productization/S15/execution-index-fec8af0'
prior_manifest=json.loads(raw(repo/'status/codex/productization/S15/execution-index-artifact-hashes-fec8af0.json'))
for ref,expected in prior_manifest.items():
    if Path(ref).is_absolute() or '..' in Path(ref).parts or not ref.startswith(prior+'/'):raise ValueError('Prior manifest boundary')
    raw(repo/ref,expected)
retained=json.loads(raw(repo/prior/'retention-index.json'))
bindings=[row for row in retained if row['original_ref']=='artifacts/S15-executed-case-index-fec8af0.json']
assert len(bindings)==1 and bindings[0]['original_sha256']==digest(index_raw)
assert index['candidate_revision']==revision and index['indexed_execution_instances']==1953
assert index['source_before']==index['source_after']==dict(revision=revision,worktree='CLEAN')
assert index['requirement_pass_claims']==0 and index['requirements_unmapped']==66 and index['legacy_applicability_or_mapping_pending']==150
assert _revision()==index['implementation_hash_after']
canonical_cases={case['execution_instance_id']:case for case in index['cases']};commands={row['command_index']:row for row in index['commands']}
matrix=json.loads(raw(repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json'))
requirements={row['id']:row for row in matrix['requirements']}
assert len(requirements)==66 and len(commands)==33
for ref,expected in source_review.items():
    actual=raw(repo/ref,'sha256:'+expected)
    assert digest(actual)==index['input_sha256_before'][(repo/ref).relative_to(project).as_posix()]
sets=[('strategy',[f'STR-{n:02d}' for n in range(1,9)],37),
      ('cloud',[f'CLOUD-{n:02d}' for n in range(1,11)],29),
      ('data-research',['DATA-01','DATA-02']+[f'RES-{n:02d}' for n in range(1,9)],45)]
union=set();selected_ids=[];all_sources={}
for group,expected_ids,expected_count in sets:
    policy=json.loads(snapshots[f'S15-{group}-support-selection-fec8af0.json'])
    draft=json.loads(snapshots[f'S15-{group}-support-draft-fec8af0.json'])
    assert draft['candidate_revision']==revision and draft['implementation_hash']==index['implementation_hash_after']
    assert draft['requirement_pass_claims']==0 and draft['legacy_applicability_or_mapping_pending']==150
    assert [row['id'] for row in policy['requirements']]==expected_ids
    assert [row['requirement']['id'] for row in draft['requirements']]==expected_ids
    assert draft['selected_test_source_hashes']=={ref:'sha256:'+source_review[ref] for ref in draft['selected_test_source_hashes']}
    seen=set()
    for selection,row in zip(policy['requirements'],draft['requirements']):
        identifier=selection['id'];selected_ids.append(identifier)
        assert row['requirement']==requirements[identifier] and row['requirement_status']=='NOT_RUN' and row['requirement_pass_claim'] is False
        assert row['supported_behavior']==selection['supported_behavior'] and row['remaining']==selection['remaining']
        assert len(row['supporting_executed_cases'])==len(selection['selectors'])
        selectors=[]
        for case in row['supporting_executed_cases']:
            original=canonical_cases[case['execution_instance_id']];command=commands[case['command_index']]
            definition=original['source_definition'];source=definition['source'];all_sources[source]=draft['selected_test_source_hashes'][source]
            assert original['phase']=='phase_2' and original['status']=='ok' and original['command_index']==case['command_index']
            assert case['actual_outcome']=='PASS' and case['source']==source and case['test_id']==definition['test_id'] and case['line']==definition['line']
            assert case['source_sha256']==all_sources[source] and case['log_ref']==command['log_ref'] and case['log_sha256']==command['log_sha256']
            assert case['command']==command['command'] and case['command_basis']==command['command_basis']
            assert case['execution_window']==command['observed_execution_window'] and case['command_duration_seconds']==command['duration_seconds']
            selectors.append([source,definition['test_id'].rsplit('.',1)[-1]])
            seen.add(case['execution_instance_id'])
        assert selectors==selection['selectors']
    assert len(seen)==expected_count==draft['selected_distinct_execution_instances']
    assert not union.intersection(seen);union.update(seen)
assert len(selected_ids)==len(set(selected_ids))==28 and len(union)==111 and all_sources=={ref:'sha256:'+value for ref,value in source_review.items()}
stem='S15-scoped-source-support-publication-GREEN'
guard_names=['run_s15_scoped_support_retention_tests.py','test_s15_scoped_support_retention.py',Path(__file__).name,'s14_feedback_cli_acceptance_core.py']
guard=validate_primary_proof(base,stem,4,inputs={name:base/name for name in guard_names},
    input_fields=('input_sha256_before','input_sha256_after'),bound={},project=project)
assert guard['source_before']==guard['source_after'] and guard['source_before']['worktree']=='CLEAN'
assert guard['implementation_hash_before']==guard['implementation_hash_after']==index['implementation_hash_after']
tool_review=json.loads(raw(base/'S15-scoped-source-support-retention-review.json'))
assert tool_review['remaining_critical']==tool_review['remaining_important']==0 and tool_review['reviewer_execution']=='NONE'
assert set(tool_review['reviewed_original_files'])=={'artifacts/'+name for name in guard_names}
for original,expected in tool_review['reviewed_original_files'].items():raw(project/original,expected)
ref='status/codex/productization/S15/scoped-source-support-fec8af0'
target=repo/ref;manifest_path=repo/'status/codex/productization/S15/scoped-source-support-artifact-hashes-fec8af0.json'
assert not target.exists() and not manifest_path.exists();target.mkdir(parents=True)
history=['S15-strategy-support-selection-fec8af0.before-semantic-review.json','S15-strategy-support-draft-fec8af0.before-semantic-review.json',
    'S15-cloud-support-selection-fec8af0.before-cloud-wording-review.json','S15-cloud-support-draft-fec8af0.before-cloud-wording-review.json']
tools=['prepare_s15_cloud_support_draft.py','prepare_s15_data_research_support_draft.py','narrow_s15_cloud_support_wording.py',
    Path(__file__).name,'retain_s15_scoped_support_fec8af0.before-publication-fix.py',
    'run_s15_scoped_support_retention_tests.py','test_s15_scoped_support_retention.py','S15-scoped-source-support-retention-review.json']
reports=[label+suffix for label in ['S15-scoped-source-support-publication-RED','S15-scoped-source-support-publication-definitive-RED',stem] for suffix in ['.json','.log']]
paths=[base/name for name in list(reviewed)+history+tools+reports];retention=[];required={}
for path in paths:
    value=snapshots[path.name] if path.name in snapshots else raw(path)
    original=path.relative_to(project).as_posix();public=_sanitize(value.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8')
    (target/path.name).write_bytes(public);required[original]=digest(value)
    retention.append(dict(original_ref=original,original_sha256=digest(value),retained_file=path.name,retained_sha256=digest(public),
        role='REVIEWED_CURRENT_SCOPED_SUPPORT' if path.name in reviewed else 'HISTORY_OR_PROVENANCE_TOOL;NOT_EXECUTABLE_ACCEPTANCE',
        transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
receipt=dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_SEMANTIC_SUPPORT_REVIEW',reviewer='/root/qualification_review',reviewer_execution='NONE',
    remaining_critical=0,remaining_important=0,remaining_minor=0,
    reviewed_original_artifacts={'artifacts/'+name:'sha256:'+value for name,value in reviewed.items()},
    reviewed_test_sources={name:'sha256:'+value for name,value in source_review.items()},
    resolved_minor=['Added actual declared-feature AST-node budget assertion','Restricted ADX n1 description to asserted two-bar value',
      'Restricted link target assertion to file existence','Restricted opt-in exact-string claim to asserted owner net_pnl'],
    limits='NO_REVIEWER_EXECUTION;NO_REQUIREMENT_PLATFORM_OR_MASTER_ACCEPTANCE')
facts=dict(document_kind='REVIEWED_PARTIAL_SOURCE_SUPPORT;NOT_COMPLETE_REQUIREMENT_RESULTS',task_id=index['task_id'],state='IN_PROGRESS',
    candidate_revision=revision,spec_revision=index['spec_revision'],implementation_hash=index['implementation_hash_after'],
    selected_requirement_support_rows=28,unselected_v02_requirements=38,complete_requirement_results_pending=66,
    legacy_applicability_or_mapping_pending=150,requirement_pass_claims=0,distinct_supporting_execution_instances=111,
    source_qualification_tests=1953,source_qualification_commands=33,source_before=index['source_before'],source_after=index['source_after'],
    retention_guard_tests=4,retention_guard_ref=stem+'.json',retention_guard_source_before=guard['source_before'],retention_guard_source_after=guard['source_after'],
    prior_execution_index_ref=prior+'/S15-executed-case-index-fec8af0.json',prior_execution_index_original_sha256=digest(index_raw),
    selected_requirement_ids=selected_ids,reviewer_execution='NONE',real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    limitations=['Scoped supporting-case selections, not per-result21-field requirement acceptance.',
      'No new product execution; existing command timing only, no per-case timestamps/duration.',
      'Mandatory native Ubuntu/normal PAPER/whole-product/capacity/S16 and real commissioning gaps remain explicit.',
      'Four before-review drafts retained as HISTORY_ONLY; generators are provenance, not current acceptance.'])
def write(name,value):(target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
write('independent-semantic-review.json',receipt);write('disposition.json',facts)
write('required-inputs.json',required);write('retention-index.json',retention)
publish_retention_manifest(target,manifest_path,retention,required,repository_root=repo)
print(json.dumps(dict(retained_ref=ref,files=len(list(target.iterdir())),selected_support_rows=28,distinct_cases=111,requirement_pass_claims=0)))
