"""Bind actual exact-subject cases/assertions; never infer semantic acceptance."""
import ast,hashlib,json,re,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.paper.producer import _guard,require_executed_cases
from application.paper.inventory import current_target,fixed_profile
from application.paper.qualification import artifact_bytes,validate_qualified_receipt
from application.platform.distribution import verify_distribution
from application.platform.supervision import config_hash
from strategy.v02.capabilities import build_capability_snapshot
from storage.qualification import open_qualification_receipts
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
CASE=re.compile(r'^test[^\r\n]* \(([^()\r\n]+)\)(?: \.\.\.|\r?\n[^\r\n]* \.\.\.) ok[ \t]*$',re.MULTILINE)

def publish_index(destination,result,final_guard):
    final_guard()
    with destination.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')

def run(revision,qualification_attempt='first',*,emit=True):
    from run_current_checkpoint import qualification_output
    base=qualification_output(revision,qualification_attempt);checkpoint=json.loads((base/'checkpoint.json').read_bytes())
    if not checkpoint['passed']:raise ValueError('Actual complete qualification required')
    config=load_config(base/'product.json');package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package)
    profile=fixed_profile(current_target());_guard(ROOT,revision,package,facts,profile)
    with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:receipt=reader.get(checkpoint['result']['receipt_ref'])
    output=config.local_data_root/'qualification'/receipt.execution_id
    measured={**facts,'platform_id':current_target(),'capability_hash':build_capability_snapshot().snapshot_hash}
    validate_qualified_receipt(receipt,profile,artifact_root=output,measured=measured)
    index=[];native=[];definitions={};source_members=profile['groups'][0]['members']
    for member,check,outcome in zip([m for g in profile['groups'] for m in g['members']],receipt.checks,receipt.execution_evidence['members'],strict=True):
        raw=artifact_bytes(output,check.log_ref)
        if sha(raw)!=check.log_hash:raise ValueError('Actual committed command log changed')
        if member['kind']!='UNITTEST':
            native.extend(dict(group_id=outcome['group_id'],member_id=check.check_id,**row) for row in outcome['assertions']);continue
        text=raw.decode('utf-8');ids=require_executed_cases(text,member['test_cases']);matches=list(CASE.finditer(text))
        if len(ids)!=len(matches) or ids!=outcome['test_cases']:raise ValueError('Actual case identities differ')
        for ordinal,(reported,match) in enumerate(zip(ids,matches,strict=True),1):
            module,class_name,method=reported.rsplit('.',2)
            source=member['directory']+'/'+module.replace('.','/')+'.py';path=ROOT/source
            if source not in definitions:
                value={}
                if path.is_file():
                    for node in ast.parse(path.read_bytes()).body:
                        if isinstance(node,ast.ClassDef):
                            for item in node.body:
                                if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):value[(node.name,item.name)]=item.lineno
                definitions[source]=value
            static_line=definitions[source].get((class_name,method));normalized=member['directory'].replace('/','.')+'.'+reported
            index.append(dict(execution_instance_id=check.check_id+f':{ordinal:04d}',member_id=check.check_id,
                test_id=normalized,reported_test_id=reported,status='PASS',source_ref=source,definition_line=static_line,
                definition_resolution='EXACT_CURRENT_AST' if static_line else 'INHERITED_OR_DYNAMIC_UNRESOLVED',
                source_hash=sha(path.read_bytes()) if path.is_file() else None,log_ref=check.log_ref,log_hash=check.log_hash,
                log_start_line=text.count('\n',0,match.start())+1,log_completion_line=text.count('\n',0,match.end())+1))
    result=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',revision=revision,
        kind='ACTUAL_NAMED_EXECUTION_BINDINGS;NOT_SEMANTIC_REQUIREMENT_ACCEPTANCE',receipt_ref=receipt.receipt_id,execution_id=receipt.execution_id,
        identity=facts,profile_hash=receipt.profile_hash,source_commands=len(source_members),source_case_executions=len(index),
        distinct_test_ids=len({r['test_id'] for r in index}),definition_unresolved=sum(r['definition_line'] is None for r in index),
        actual_native_assertions=native,cases=index,config_hash=config_hash(config),started_at_utc=receipt.started_at,finished_at_utc=receipt.finished_at,
        timing_basis='ACTUAL_COMPLETE_OWNING_QUALIFICATION_WINDOW;NO_PER_TEST_TIMESTAMPS',requirement_pass_claims=0,
        public_provider_calls_in_this_offline_qualification=0,prior_separate_public_capture_requests=8,
        credentials='NONE',private_requests=0,provider_mutation=0,capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS')
    dest=BASE/('execution-index-'+revision[:7]+'.json')
    if emit:
        publish_index(dest,result,lambda:_guard(ROOT,revision,package,facts,profile))
        print(json.dumps({k:result[k] for k in ('revision','source_commands','source_case_executions','distinct_test_ids','definition_unresolved','requirement_pass_claims')}))
    else:_guard(ROOT,revision,package,facts,profile)
    return result
if __name__=='__main__':run(*sys.argv[1:])
