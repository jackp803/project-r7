"""Produce a reversible case-selection draft; it cannot issue requirement PASS."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from strategy.v02.capabilities import _revision
from s14_feedback_cli_acceptance_core import require_artifact
revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
bound={}
def load(path):
    value=read_local(path.parent,path.name,8*1024*1024);expected='sha256:'+hashlib.sha256(value).hexdigest()
    require_artifact(path.parent,path.name,expected);bound[path.relative_to(project).as_posix()]=expected
    return json.loads(value)
policy=load(base/'S15-api-support-selection-fec8af0.json')
retained=load(repo/'status/codex/productization/S15/execution-index-fec8af0/retention-index.json')
index_record=[row for row in retained if row['original_ref']=='artifacts/S15-executed-case-index-fec8af0.json']
assert len(index_record)==1
index=load(base/'S15-executed-case-index-fec8af0.json')
assert bound['artifacts/S15-executed-case-index-fec8af0.json']==index_record[0]['original_sha256']
matrix=load(repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json')
assert policy['candidate_revision']==index['candidate_revision']==revision
assert index['indexed_execution_instances']==1953 and index['requirement_pass_claims']==0
assert index['source_before']==index['source_after']==dict(revision=revision,worktree='CLEAN')
assert _revision()==index['implementation_hash_after']
assert [row['id'] for row in policy['requirements']]==[f'API-{number:02d}' for number in range(1,4)]
by_requirement={row['id']:row for row in matrix['requirements']};commands={row['command_index']:row for row in index['commands']}
assert len(by_requirement)==66 and len(commands)==33
phase2=[row for row in index['cases'] if row['phase']=='phase_2']
assert len(phase2)==1706 and len({row['execution_instance_id'] for row in phase2})==1706
selected=[];definitions={};case_union={}
for row in policy['requirements']:
    cases=[];selectors=row['selectors'];assert len(selectors)==len({tuple(item) for item in selectors})
    for source,method in selectors:
        matches=[case for case in phase2 if case['source_definition']['source']==source and case['source_definition']['test_id'].rsplit('.',1)[-1]==method]
        assert len(matches)==1,(source,method,len(matches))
        case=matches[0];assert case['status']=='ok'
        definition=case['source_definition'];expected=index['input_sha256_before'][(repo/source).relative_to(project).as_posix()]
        raw=read_local(repo/source.rsplit('/',1)[0],source.rsplit('/',1)[1],1024*1024)
        assert 'sha256:'+hashlib.sha256(raw).hexdigest()==expected
        require_artifact((repo/source).parent,Path(source).name,expected)
        definitions[source]=expected;case_union[case['execution_instance_id']]=case
        command=commands[case['command_index']]
        cases.append(dict(test_id=definition['test_id'],execution_instance_id=case['execution_instance_id'],
            actual_outcome='PASS',source=source,line=definition['line'],source_sha256=expected,
            command_index=case['command_index'],command=command['command'],command_basis=command['command_basis'],
            duration_basis='COMPLETE_COMMAND_ONLY;NO_PER_CASE_DURATION',command_duration_seconds=command['duration_seconds'],
            execution_window=command['observed_execution_window'],log_ref=command['log_ref'],log_sha256=command['log_sha256']))
    selected.append(dict(requirement=by_requirement[row['id']],mapping_status='DRAFT_SCOPED_SOURCE_SUPPORT;INDEPENDENT_SEMANTIC_REVIEW_PENDING',
        requirement_status='NOT_RUN',requirement_pass_claim=False,supported_behavior=row['supported_behavior'],supporting_executed_cases=cases,remaining=row['remaining']))
body=dict(document_kind='SCOPED_SOURCE_SUPPORT_MAPPING_DRAFT;NOT_ACCEPTANCE_RESULT',task_id=index['task_id'],candidate_revision=revision,spec_revision=index['spec_revision'],
    implementation_hash=index['implementation_hash_after'],selection_input_hashes=bound,selected_test_source_hashes=definitions,
    source_qualification_tests=1953,source_qualification_commands=33,selected_requirement_drafts=3,unselected_v02_requirements=63,
    selected_distinct_execution_instances=len(case_union),requirement_pass_claims=0,legacy_applicability_or_mapping_pending=150,
    requirements=selected,common_limits=policy['common_limits'],created_at_utc=datetime.now(timezone.utc).isoformat())
target=base/'S15-api-support-draft-fec8af0.json';assert not target.exists()
target.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(selected_requirement_drafts=3,distinct_supporting_cases=len(case_union),requirement_pass_claims=0,semantic_review='PENDING')))
