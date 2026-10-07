"""Reuse the reviewed/tested validator for eleven additional partial mappings."""
from pathlib import Path
import hashlib,json,re,subprocess,sys,types
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import _sanitize
from strategy.v02.capabilities import _revision
digest=lambda value:'sha256:'+hashlib.sha256(value).hexdigest();snapshots={}
def raw(path,expected=None):
    value=read_local(path.parent,path.name,8*1024*1024)
    if expected is not None and digest(value)!=expected:raise ValueError('Reviewed evidence commitment changed')
    return value
def capture(name,expected=None):
    value=raw(base/name,expected);snapshots[name]=value;return value
def module(name,expected):
    value=capture(name,expected);loaded=types.ModuleType('s15_api_platform_bound_'+name.removesuffix('.py'))
    loaded.__dict__['__file__']=str(base/name)
    exec(compile(value,str(base/name),'exec'),loaded.__dict__)
    return loaded
def prior(folder,manifest_name,expected):
    prefix='status/codex/productization/S15/'+folder
    manifest=json.loads(raw(repo/'status/codex/productization/S15'/manifest_name,expected));values={}
    for reference,sha in manifest.items():
        assert reference.startswith(prefix+'/') and '..' not in Path(reference).parts
        values[Path(reference).name]=raw(repo/reference,sha)
    return values
def main(review_sha):
    assert re.fullmatch(r'sha256:[0-9a-f]{64}',review_sha)
    review=json.loads(capture('S15-api-platform-retention-review.json',review_sha))
    assert review['reviewer']=='/root/qualification_review' and review['reviewer_execution']=='NONE'
    assert all(review[k]==0 for k in ('remaining_critical','remaining_important','remaining_minor'))
    names={Path(__file__).name,'retain_s15_owner_temporal_support.py','s14_feedback_cli_acceptance_core.py'}
    assert set(review['reviewed_original_artifacts'])=={'artifacts/'+name for name in names}
    for reference,sha in review['reviewed_original_artifacts'].items():capture(Path(reference).name,sha)
    validator=module('retain_s15_owner_temporal_support.py','sha256:73d3afe6d87e6c2069f64c0346ab03b84190ffd59fc89865dddf3eec8bf06d46')
    substrate=module('s14_feedback_cli_acceptance_core.py','sha256:a3bd7e32bb805cebfdb5a26994cd712bc47b1bb995dae0c51dd7a09522a9c7b0')
    reviewed={
      'S15-api-support-selection-fec8af0.json':'4e03936d662456f1e3fc2cadec6318e8f71fad1f5c20855acf574baaf5552c29',
      'build_s15_api_support_draft.py':'d5178a17be420e867466e8942a397d760fc219eabfa30165adce698c6350a2ff',
      'S15-api-support-draft-fec8af0.json':'a0ad9d81905a34757a8e2a8f99a1878c2bddd79622a880d43dbdd940453b1f2b',
      'S15-platform-support-selection-fec8af0.json':'6f5763f0de3d792b81703c54e8004deb8c0c6a53fb5e3970773c4b340f1ba9c7',
      'build_s15_platform_support_draft.py':'1f3d04ec9f69a8c3aedf93980fbc923e84e6957088b395a29f43e6f43373f491',
      'S15-platform-support-draft-fec8af0.json':'aa83062404834343d281f4a9dfc0ca240f7d0cdf8715100adebe4450d35227b5'}
    for name,sha in reviewed.items():capture(name,'sha256:'+sha)
    index=json.loads(raw(base/'S15-executed-case-index-fec8af0.json','sha256:3ce754311d3210ac5827500999543d87c56d2f5bb4e7eb1ac67e4a9aa0c72209'))
    matrix=json.loads(raw(repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json','sha256:a205373601ac6c2b5994c964b23ebe562c8f0aa3898ef2f2b6412988c1f5968f'))
    revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
    assert index['candidate_revision']==revision and index['indexed_execution_instances']==1953 and index['requirement_pass_claims']==0
    assert index['source_before']==index['source_after']==dict(revision=revision,worktree='CLEAN')
    assert _revision()==index['implementation_hash_after']
    old=prior('scoped-source-support-fec8af0','scoped-source-support-artifact-hashes-fec8af0.json',
        'sha256:73060e2671e2038d6bc9ffd8d617a2b631a4f76136b7d88f59fd5ae0b0c8db61');assert len(old)==46
    previous=prior('owner-temporal-support-fec8af0','owner-temporal-support-artifact-hashes-fec8af0.json',
        'sha256:1d88228af17316a35fec8016aa3e366851267b35580093486f58f0b1ba937e5f');assert len(previous)==45
    old_ids,old_union=validator.validate_prior_support(index,matrix,old)
    public_index=json.loads(_sanitize(json.dumps(index,ensure_ascii=False),repo));sources={}
    for group in ('strategy','cloud','data-research'):
        sources.update(json.loads(old[f'S15-{group}-support-draft-fec8af0.json'])['selected_test_source_hashes'])
    for group in ('temporal','lifecycle-trading'):
        selection=json.loads(previous[f'S15-{group}-support-selection-fec8af0.json'])
        draft=json.loads(previous[f'S15-{group}-support-draft-fec8af0.json'])
        old_union.update(validator.validate_support(public_index,matrix,selection,draft));old_ids.extend(r['id'] for r in selection['requirements'])
        sources.update(draft['selected_test_source_hashes'])
    assert len(old_ids)==46 and len(old_union)==203
    new_ids=[];new_union=set();new_sources={}
    for group,ids,count in [('api',[f'API-{n:02d}' for n in range(1,4)],21),('platform',[f'PLAT-{n:02d}' for n in range(1,9)],37)]:
        selection=json.loads(snapshots[f'S15-{group}-support-selection-fec8af0.json'])
        draft=json.loads(snapshots[f'S15-{group}-support-draft-fec8af0.json'])
        assert [r['id'] for r in selection['requirements']]==ids
        assert draft['selected_distinct_execution_instances']==count and draft['selected_requirement_drafts']==len(ids)
        new_union.update(validator.validate_support(index,matrix,selection,draft));new_ids.extend(ids)
        sources.update(draft['selected_test_source_hashes']);new_sources.update(draft['selected_test_source_hashes'])
    assert len(new_ids)==11 and not set(old_ids).intersection(new_ids) and len(new_union)==58
    assert len(old_union|new_union)==261 and len(sources)==54
    for reference,sha in new_sources.items():
        assert reference.startswith('tests/') and '..' not in Path(reference).parts
        raw(repo/reference,sha)
    git=r'C:\Program Files\Git\cmd\git.exe'
    head=subprocess.check_output([git,'rev-parse','HEAD'],cwd=repo).decode().strip()
    assert head=='932c37da369c605c5cfc8045679fb3bc53f44ba1'
    assert not subprocess.check_output([git,'status','--porcelain'],cwd=repo).strip()
    changed=subprocess.check_output([git,'diff','--name-only',revision,'HEAD'],cwd=repo).decode().splitlines()
    assert all(name.startswith(('status/','coordination/')) for name in changed)
    history=['prepare_s15_api_support_draft.py','prepare_s15_platform_support_draft.py','resolve_s15_platform_review.py',
        'S15-platform-support-selection-fec8af0.before-semantic-review.json','S15-platform-support-draft-fec8af0.before-semantic-review.json']
    for name in history:capture(name)
    ref='status/codex/productization/S15/api-platform-support-fec8af0';target=repo/ref
    manifest_path=repo/'status/codex/productization/S15/api-platform-support-artifact-hashes-fec8af0.json'
    assert not target.exists() and not manifest_path.exists();target.mkdir(parents=True)
    retained=[];required={}
    for name,value in snapshots.items():
        public=_sanitize(value.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8')
        (target/name).write_bytes(public);original='artifacts/'+name;required[original]=digest(value)
        retained.append(dict(original_ref=original,original_sha256=digest(value),retained_file=name,retained_sha256=digest(public),
            role='HISTORY_OR_GENERATOR;NOT_ACCEPTANCE' if name in history else 'REVIEWED_CURRENT_PARTIAL_SUPPORT;NOT_REQUIREMENT_ACCEPTANCE',
            transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
    semantic=dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_API_PLATFORM_SUPPORT_REVIEW',reviewer='/root/qualification_review',reviewer_execution='NONE',
        remaining_critical=0,remaining_important=0,remaining_minor=0,
        reviewed_original_artifacts={'artifacts/'+name:'sha256:'+sha for name,sha in reviewed.items()},reviewed_test_sources=new_sources,
        resolved_minor=['Narrowed nested/external path rejection to selected assertions','Separated hardware doctor JSON from unasserted initialization invariant',
            'Labeled fixed24GiB renderer policy input'],limits='NO_REVIEWER_EXECUTION;NO_NATIVE_REQUIREMENT_OR_MASTER_ACCEPTANCE')
    disposition=dict(document_kind='57_REVIEWED_PARTIAL_SOURCE_SUPPORT_ROWS;NOT_COMPLETE_REQUIREMENT_RESULTS',state='IN_PROGRESS',task_id=index['task_id'],
        candidate_revision=revision,implementation_hash=index['implementation_hash_after'],cumulative_support_rows=57,
        cumulative_distinct_original_execution_instances=261,independently_reviewed_test_source_files=54,
        additional_support_rows=11,additional_distinct_source_cases=58,selected_requirement_ids=new_ids,
        unselected_support_rows=9,complete_requirement_results_pending=66,legacy_applicability_or_mapping_pending=150,requirement_pass_claims=0,
        source_qualification_tests=1953,source_qualification_commands=33,retention_source_before=dict(revision=head,worktree='CLEAN'),
        reused_validator='FIXED_REVIEWED_PROTECTED_RAW_73d3afe;SEVEN_REGRESSIONS_RETAINED_IN_PRIOR_CHECKPOINT;NO_NEW_REGRESSION_EXECUTION',
        real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        limits=['Partial source assertions only;actual Windows native/browser evidence is separate. Ubuntu/ordinary native PAPER/capacity/whole-flow/S16 remain pending.',
            'No real SSH,cloud,forward,provider/credential/financial commissioning or57 complete21-field requirement results claimed.',
            'Five new tactical fixture executions remain separate from original1953 index;203+58 original source cases deduplicate to261.'])
    def write(name,value):(target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    write('independent-semantic-review.json',semantic);write('disposition.json',disposition)
    write('required-inputs.json',required);write('retention-index.json',retained)
    substrate.publish_retention_manifest(target,manifest_path,retained,required,repository_root=repo)
    assert _revision()==index['implementation_hash_after']
    print(json.dumps(dict(retained_files=len(list(target.iterdir())),cumulative_partial_rows=57,cumulative_distinct_original_cases=261,requirement_pass_claims=0)))
if __name__=='__main__':main(sys.argv[1])
