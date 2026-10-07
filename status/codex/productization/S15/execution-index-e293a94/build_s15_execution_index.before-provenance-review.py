"""Bind actual named source-test execution; never infer requirement acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import FOCUSED,discover_suites,parse_result,revision_fact
from strategy.v02.capabilities import _revision
from s15_execution_index import read_command_cases

revision=sys.argv[1]
assert revision=='e293a947f886d9814c89983fd9e03151c1695788'
target=base/f'S15-executed-case-index-{revision[:7]}.json';assert not target.exists()
before=revision_fact(repo,revision,True);implementation_before=_revision();bound={}
def load(folder,name):
    raw=read_local(folder,name,8*1024*1024)
    bound[(Path(folder)/name).relative_to(project).as_posix()]='sha256:'+hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
def bind(path,expected=None):
    raw=path.read_bytes();actual='sha256:'+hashlib.sha256(raw).hexdigest()
    if expected is not None and actual!=expected:raise ValueError('Index input changed')
    bound[path.relative_to(project).as_posix()]=actual
    return actual
for name in ('build_s15_execution_index.py','s15_execution_index.py','test_s15_execution_index.py',
             'run_s15_execution_index_tests.py','prepare_s15_acceptance_coverage_inventory_v2.py'):
    bind(base/name)
inventory=load(base,f'S15-acceptance-coverage-inventory-{revision[:7]}.json')
assert inventory['candidate_revision']==revision and len(inventory['requirements'])==66 and len(inventory['legacy_requirements'])==150
assert all(row['acceptance_status']=='NOT_RUN' and row['mapping_status']=='UNMAPPED' for row in inventory['requirements'])
assert inventory['inventory_builder_sha256']==bind(base/'prepare_s15_acceptance_coverage_inventory_v2.py')
bind(repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json',inventory['matrix_sha256'])
bind(repo/'docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md',inventory['legacy_matrix_sha256'])
for ref,expected in inventory['test_source_hashes'].items():bind(repo/ref,expected)
stem='S15-executed-case-index-reviewed-GREEN'
guard=load(base,stem+'.json')
assert guard['passed'] is True and guard['tree_reaped'] is True and guard['tests_run']==8
assert guard['exit_code']==guard['failures']==guard['errors']==guard['skipped']==0
assert guard['harness_binding']=='BEFORE_AND_AFTER_EXECUTION' and guard['input_sha256_before']==guard['input_sha256_after']
assert set(guard['input_sha256_before'])=={'run_s15_execution_index_tests.py','test_s15_execution_index.py','s15_execution_index.py'}
for name,expected in guard['input_sha256_before'].items():bind(base/name,expected)
assert guard['implementation_hash_before']==guard['implementation_hash_after']==implementation_before
raw=read_local(base,stem+'.log',4*1024*1024);assert 'sha256:'+hashlib.sha256(raw).hexdigest()==guard['log_sha256']
parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=guard['exit_code'])
assert parsed.passed and parsed.tests_run==8;bind(base/(stem+'.log'),guard['log_sha256'])
folder=base/f'r7-productization-S12-runtime-supervision-qualified-{revision[:7]}'
full=load(folder,'qualification.json');context=load(folder,'qualification-context.json')
assert full['passed'] is True and type(full['tests_run']) is int and full['tests_run']==1942 and len(full['commands'])==33
assert full['source_before']==full['source_after']==before
assert full['execution']=='LOCAL' and full['github_compute']=='NOT_USED' and full['real_provider_calls']==0 and full['real_credentials']=='NONE' and full['capital']=='NONE'
assert context['configuration']==dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=revision)
bind(base/'s12_runtime_supervision_source_qualify.py',context['launcher_hash'])
assert context['spec_revision']==inventory['spec_revision']
expected=[('phase_1',suite,pattern) for suite,pattern in FOCUSED]
expected.extend(('phase_2',suite.name,'test_*.py') for suite in discover_suites(repo))
assert [(r['phase'],r['suite'],r['pattern']) for r in full['commands']]==expected
assert sum(r['tests_run'] for r in full['commands'])==full['tests_run']
for row in full['commands']:bind(folder/row['log'],'sha256:'+row['log_sha256'])
input_before=dict(bound)
definitions={r['test_id']:r for r in inventory['declared_tests']}
short={}
for row in inventory['declared_tests']:
    module,cls,method=row['test_id'].rsplit('.',2)
    short.setdefault((module.rsplit('.',1)[-1],cls,method),[]).append(row)
cases=[];commands=[]
for index,row in enumerate(full['commands'],1):
    observed=read_command_cases(folder,row,index)
    bind(folder/row['log'],'sha256:'+row['log_sha256'])
    assert row['source_after']==before
    argv=[sys.executable,'-m','unittest','discover','-s','tests/'+row['suite'],'-p',row['pattern'],'-v']
    commands.append(dict(command_index=index,phase=row['phase'],suite=row['suite'],pattern=row['pattern'],
        command=argv,command_basis='SEALED_EXECUTED_RUNNER_POLICY;NOT_RAW_ARGV_TRACE',
        tests=row['tests_run'],exit_code=row['returncode'],tree_reaped=row['tree_reaped'],duration_seconds=row['duration_seconds'],
        log_ref=(folder/row['log']).relative_to(project).as_posix(),log_sha256='sha256:'+row['log_sha256'],
        observed_execution_window=dict(scope='FULL_SOURCE_QUALIFICATION_WINDOW;NO_PER_TEST_TIMESTAMP_CLAIM',
            started_at_utc=context['started_at_utc'],finished_at_utc=context['finished_at_utc'])))
    for ordinal,case in enumerate(observed,1):
        identity=case['reported_test_id'];definition=definitions.get(identity)
        if definition is None:
            module,cls,method=identity.rsplit('.',2)
            choices=short.get((module.rsplit('.',1)[-1],cls,method),[])
            if len(choices)==1:definition=choices[0]
        cases.append(dict(**case,execution_instance_id=f'{index:03d}:{ordinal:04d}:{identity}',command_index=index,
            phase=row['phase'],suite=row['suite'],source_definition=definition,
            source_mapping='EXACT_STATIC_DECLARATION' if definition else 'UNRESOLVED_INHERITED_OR_DYNAMIC_CASE;NAMED_EXECUTION_PRESERVED',
            requirement_acceptance='NOT_INFERRED'))
assert len(cases)==1942 and len({r['execution_instance_id'] for r in cases})==1942
assert sum(r['tests_run'] for r in full['commands'] if r['phase']=='phase_1')==247
assert sum(r['tests_run'] for r in full['commands'] if r['phase']=='phase_2')==1695
after=revision_fact(repo,revision,True);implementation_after=_revision()
assert before==after and implementation_before==implementation_after
for ref,expected_hash in tuple(bound.items()):bind(project/ref,expected_hash)
assert input_before==bound
facts=dict(document_kind='ACTUAL_NAMED_SOURCE_EXECUTION_INDEX;NOT_REQUIREMENT_ACCEPTANCE',
    task_id=inventory['task_id'],candidate_revision=revision,spec_revision=inventory['spec_revision'],
    source_before=before,source_after=after,implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
    harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=input_before,input_sha256_after=dict(bound),
    indexed_execution_instances=len(cases),distinct_reported_test_ids=len({r['reported_test_id'] for r in cases}),
    unresolved_static_definitions=sum(r['source_definition'] is None for r in cases),
    source=dict(tests=1942,commands=33,phase_1=247,phase_2=1695,os=full['os'],os_version=full['os_version'],architecture=full['architecture'],python=full['python']),
    commands=commands,cases=cases,requirements_unmapped=66,legacy_applicability_or_mapping_pending=150,
    requirement_pass_claims=0,created_at_utc=datetime.now(timezone.utc).isoformat(),
    limits=['Each requirement still needs semantic named-test mapping and evidence review',
            'Imported/inherited/dynamic definitions stay explicit if static origin cannot resolve',
            'Source test cases do not establish native platform, browser, real cloud/forward/provider commissioning',
            'Command argv is reconstructed from the sealed executed runner policy; timing is the actual complete qualification window'])
target.write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:facts[k] for k in ('indexed_execution_instances','distinct_reported_test_ids','unresolved_static_definitions','requirement_pass_claims')}))
