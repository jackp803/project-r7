"""Bind actual execution support; keep unreviewed whole requirements NOT_RUN."""
from collections import defaultdict
import hashlib,json,re,sys,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from application.paper.qualification import artifact_bytes
from application.paper.qualification import validate_qualified_receipt
from application.platform.distribution import verify_distribution
from application.platform.supervision import config_hash
from application.config import load_config
from storage.qualification import open_qualification_receipts
from strategy.v02.capabilities import build_capability_snapshot
from index_current_qualification import run as rebuild_index

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(artifact_bytes(PROJECT,Path(path).relative_to(PROJECT).as_posix()))

def named_ids(value):
    if isinstance(value,str):
        if re.fullmatch(r'tests\.[A-Za-z0-9_.]+\.test[A-Za-z0-9_]+',value):yield value
    elif isinstance(value,list):
        for item in value:yield from named_ids(item)
    elif isinstance(value,dict):
        for item in value.values():yield from named_ids(item)

def bind_names(names,index):
    by_id=defaultdict(list)
    for row in index:by_id[row['test_id']].append(row)
    return [row for name in sorted(set(names)) for row in by_id.get(name,[])],sorted(set(names)-set(by_id))

def require_exact_rows(rows,canonical,id_key,text_key):
    if (len(rows)!=len(canonical) or len({r[id_key] for r in rows})!=len(canonical)
            or {r[id_key]:r[text_key] for r in rows}!=canonical):raise ValueError('Canonical requirement IDs/text differ')

def run(revision,qualification_attempt='first'):
    from run_current_checkpoint import qualification_output
    qualifier=qualification_output(revision,qualification_attempt)
    package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package);profile=fixed_profile(current_target())
    _guard(ROOT,revision,package,facts,profile)
    actual=read(BASE/('execution-index-'+revision[:7]+'.json'));checkpoint=read(qualifier/'checkpoint.json')
    if (not checkpoint['passed'] or actual['revision']!=revision or actual['identity']!=facts
            or actual['receipt_ref']!=checkpoint['result']['receipt_ref']):raise ValueError('Complete actual current owning index required')
    if rebuild_index(revision,qualification_attempt,emit=False)!=actual:raise ValueError('Index differs from freshly verified actual named execution closure')
    config=load_config(qualifier/'product.json')
    with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:receipt=reader.get(actual['receipt_ref'])
    artifact_root=config.local_data_root/'qualification'/receipt.execution_id
    validate_qualified_receipt(receipt,profile,artifact_root=artifact_root,
        measured={**facts,'platform_id':current_target(),'capability_hash':build_capability_snapshot().snapshot_hash})
    if (actual['execution_id']!=receipt.execution_id or actual['profile_hash']!=receipt.profile_hash
            or actual['config_hash']!=config_hash(config) or actual['started_at_utc']!=receipt.started_at
            or actual['finished_at_utc']!=receipt.finished_at):raise ValueError('Actual receipt/index binding differs')
    expected=[]
    for member,check in zip(profile['groups'][0]['members'],receipt.checks):
        for ordinal,name in enumerate(member['test_cases'],1):
            expected.append((check.check_id+f':{ordinal:04d}',check.check_id,member['directory'].replace('/','.')+'.'+name,check.log_ref,check.log_hash))
    observed=[(r['execution_instance_id'],r['member_id'],r['test_id'],r['log_ref'],r['log_hash']) for r in actual['cases']]
    if observed!=expected or any(r['status']!='PASS' for r in actual['cases']):raise ValueError('Index cases differ from actual committed executed closure')
    specification=read(ROOT/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json');draft=read(BASE/'acceptance-v02-draft.json')
    spec_revision=read(ROOT/'coordination/CODEX/PROGRESS.json')['spec_revision']
    input_bindings={}
    for ref in ('docs/product/v0_2/07_ACCEPTANCE_MATRIX.json','docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'):
        raw=artifact_bytes(ROOT,ref)
        pinned=subprocess.run(['git','show',spec_revision+':'+ref],cwd=ROOT,check=True,capture_output=True).stdout
        if raw.replace(b'\r\n',b'\n')!=pinned.replace(b'\r\n',b'\n'):raise ValueError('Authoritative spec revision differs')
        input_bindings[ref]=sha(raw)
    if (len(specification['requirements'])!=66 or len(draft['requirements'])!=66
            or len({r['id'] for r in specification['requirements']})!=66
            or len({r['requirement_id'] for r in draft['requirements']})!=66
            or {r['id']:r['requirement'] for r in specification['requirements']}!={r['requirement_id']:r['requirement_text'] for r in draft['requirements']}):
        raise ValueError('Exact current66matrix required')
    require_exact_rows(draft['requirements'],{r['id']:r['requirement'] for r in specification['requirements']},'requirement_id','requirement_text')
    input_bindings['acceptance-v02-draft.json']=sha(artifact_bytes(BASE,'acceptance-v02-draft.json'))
    supplemental=defaultdict(list);references=defaultdict(list)
    for name in ('acceptance-str-expanded-map.json','acceptance-research-expanded-map.json','acceptance-cloud-trade-expanded-map.json'):
        raw=artifact_bytes(BASE,name);document=json.loads(raw);input_bindings[name]=sha(raw)
        for row in document['requirements']:
            rid=row['requirement_id'];supplemental[rid].append(row);references[rid].append(name)
            if name=='acceptance-str-expanded-map.json':
                supplemental[rid].extend(document['required_case_catalog'][key] for key in row['case_keys'])
    source_members={member['member_id']:member for member in profile['groups'][0]['members']}
    root_ref=checkpoint['owning_data_root_ref']+'/qualification/'+actual['execution_id']+'/'
    source_rows=actual['cases'];native_rows=actual['actual_native_assertions']
    build=read(BASE/('build-'+revision[:7])/'build-result.json')
    if build['identity']!=facts or build['target']!='windows' or current_target()!='windows-11-x86_64':raise ValueError('Same local Windows build target required')
    environment=dict(environment_class='SOURCE_ONLY_WINDOWS;ACTUAL_NAMED_SUPPORT_NOT_WHOLE_REQUIREMENT_ACCEPTANCE',
        os_version=build['os_version'],architecture=current_target().rsplit('-',1)[-1],
        runtime_versions=receipt.profile_manifest['execution_toolchains'][current_target()])
    def record(rid,text,mapping,names):
        bound,missing=bind_names(names,source_rows);logs={root_ref+r['log_ref']:r['log_hash'] for r in bound}
        commands=[dict(member_id=mid,command_ref=source_members[mid]['command_ref'],
            argv=['<PROFILE_HASH_BOUND_PYTHON>','-X','utf8','-m','unittest','discover','-s',source_members[mid]['directory'],'-p',source_members[mid]['pattern'],'-v'],
            basis='DETERMINISTIC_COMMAND_ASSEMBLED_BY_HASH_BOUND_OWNING_PRODUCER;NOT_OS_ARGV_TRACE',
            producer_ref='src/application/paper/producer.py',producer_hash=sha(artifact_bytes(ROOT,'src/application/paper/producer.py')))
            for mid in sorted({r['member_id'] for r in bound})]
        row=dict(requirement_id=rid,status='NOT_RUN',test_ids=sorted({r['test_id'] for r in bound}),command=commands,
            source_revision=revision,spec_revision=spec_revision,**environment,
            config_hash=actual['config_hash'],started_at_utc=actual['started_at_utc'],finished_at_utc=actual['finished_at_utc'],
            exit_code=None,passed=len(bound),failed=0,errors=0,skipped=0,artifact_refs=list(logs),artifact_hashes=logs,
            limitations=['Whole requirement acceptance remains NOT_RUN until each mandatory clause and environment is reviewed. Counts below are mapped supporting case occurrences, not requirement PASS.',
                'Times cover the actual owning run; no per-case timestamps. Focused/full repeated executions remain explicit.',
                'Windows/source/fake-provider evidence does not qualify Ubuntu, real cloud, private provider, elapsed forward or capital.'],
            requirement=text,mapped_supporting_executions=bound,unresolved_named_cases=missing,
            mapping_advisory=dict(kind='STATIC_MAPPING_INPUTS;NOT_CURRENT_EXECUTION_RESULTS',clauses_and_limits=mapping,
                primary_ref='acceptance-v02-draft.json' if '-' in rid else 'legacy-150-draft.json',expanded_refs=references.get(rid,[])),
            native_assertions_not_automatically_semantic_pass=[],acceptance_reviewer='PENDING',financial_authority='NONE')
        return row
    results=[]
    for row in draft['requirements']:
        rid=row['requirement_id'];mapping=[row,*supplemental[rid]];names=list(named_ids(mapping))
        result=record(rid,row['requirement_text'],mapping,names)
        wanted={(a['group'],a['assertion']) for a in row.get('native_assertion_refs',[])}
        result['native_assertions_not_automatically_semantic_pass']=[r for r in native_rows if (r['group_id'],r['assertion_id']) in wanted]
        if rid=='E2E-03':
            result=record(rid,row['requirement_text'],mapping,[r['test_id'] for r in source_rows])
            result.update(status='PASS',exit_code=0,acceptance_reviewer='EXACT_OWNING_FULL_SOURCE_WINDOWS_ONLY',
                limitations=['Scoped Windows full credential-free source execution only. No transitive code/environment acceptance or whole Master PASS.',
                    'Actual repeated focused/full occurrences retained; no per-test timestamps.'])
        results.append(result)
    legacy=read(BASE/'legacy-150-draft.json');legacy_results=[]
    canonical_legacy={m[0]:m[1] for m in re.findall(r'^\| ([A-M][0-9]{2}) \| ([^|]+?) \| [^|]+? \|$',
        artifact_bytes(ROOT,'docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md').decode('utf-8').replace('\r\n','\n'),re.MULTILINE)}
    if (len(canonical_legacy)!=150 or len(legacy['rows'])!=150 or len({r['id'] for r in legacy['rows']})!=150
            or {r['id']:r['requirement'] for r in legacy['rows']}!=canonical_legacy):raise ValueError('Exact150canonical legacy identities/text required')
    require_exact_rows(legacy['rows'],canonical_legacy,'id','requirement')
    input_bindings['legacy-150-draft.json']=sha(artifact_bytes(BASE,'legacy-150-draft.json'))
    for row in legacy['rows']:
        names=set(named_ids(row));resolved=[];unresolved=[]
        for definition in row['source_definition_refs']:
            source=definition['path'];symbol=definition['symbol']
            matches={r['test_id'] for r in source_rows if r['source_ref']==source and r['test_id'].endswith('.'+symbol)}
            if len(matches)==1:names.update(matches);resolved.append(dict(definition=definition,test_id=next(iter(matches)),resolution='EXACT_SOURCE_AND_UNIQUE_EXECUTED_SYMBOL'))
            else:unresolved.append(definition)
        result=record(row['id'],row['requirement'],row,names)
        result.update(applicability_proposal=row['proposed_applicability'],exact_symbol_bindings=resolved,unresolved_definition_refs=unresolved)
        legacy_results.append(result)
    required=set(specification['per_result_required_fields'])
    if any(not required<=set(row) for row in results+legacy_results):raise ValueError('Required21fields missing')
    report=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',kind='ACTUAL_SUPPORTING_EXECUTION_BINDINGS_WITH_EXPLICIT_UNACCEPTED_CLAUSES',
        revision=revision,identity=facts,receipt_ref=actual['receipt_ref'],master='IN_PROGRESS',mapping_input_hashes=input_bindings,
        environment_basis='Actual same-host build OS version; named target from typed receipt; execution toolchains verified by owning producer before every child. No independent OS argv trace.',
        current_matrix_results=results,inherited_legacy_results=legacy_results,
        scope='Only E2E03 scopedWindows fullsource PASS mechanically established; other requirements need semantic clause and required environment review.',
        credentials='NONE',private_requests=0,additional_public_requests=0,cumulative_actual_public_requests=8,capital='NONE',github_compute='NOT_USED')
    output=BASE/('acceptance-records-'+revision[:7]+'.json')
    _guard(ROOT,revision,package,facts,profile)
    with output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(revision=revision,current_rows=len(results),legacy_rows=len(legacy_results),scoped_windows_full_source='PASS',other_whole_requirement_acceptance='NOT_RUN')))

if __name__=='__main__':run(*sys.argv[1:])
