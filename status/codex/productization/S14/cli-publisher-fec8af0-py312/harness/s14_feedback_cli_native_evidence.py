"""Exact current native historical publication evidence, without runtime claims."""
import hashlib,json
from application.datasets.catalog import read_local
from s14_feedback_cli_acceptance_core import require_artifact,require_sequence

COMMANDS=('historical-paper-publish','historical-paper-idempotent')
SCENARIOS=('native-historical-paper-exact-byte-ack-through-compiled-local-fake',
           'native-durable-paper-ack-is-not-republished',
           'native-publication-preserves-historical-runtime-generation-and-checkpoint')

def validate_native_paper(folder,report,identity,*,inputs,bound,project):
    clean=dict(revision=identity['executable_revision'],worktree='CLEAN')
    if (report.get('passed') is not True or report.get('fixture_cleanup_complete') is not True
        or report.get('identity')!=identity or report.get('source_before')!=clean or report.get('source_after')!=clean
        or report.get('implementation_hash_after')!=identity['implementation_hash']
        or report.get('harness_binding')!='BEFORE_AND_AFTER_EVERY_NATIVE_COMMAND'
        or report.get('fixture_origin')!='SOURCE_CREATED_ACTUAL_E2_E5_E6_ACCELERATED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION'
        or report.get('transport')!='OFFLINE_COMPILED_FAKE_ONLY'
        or any(report.get(key)!='NOT_RUN' for key in ('normal_runtime','real_cloud','real_forward','ubuntu'))
        or report.get('provider_requests')!=0 or report.get('credentials')!='NONE'
        or report.get('capital')!='NONE' or report.get('github_compute')!='NOT_USED'
        or report.get('financial_authority')!='NONE' or report.get('native_path')!='EMPTY'
        or report.get('native_pythonpath')!='UNSET' or report.get('native_node')!='UNAVAILABLE_ON_PATH'):
        raise ValueError('Exact bounded historical native subject and cleanup required')
    for key,count in (('command_count',2),('scenario_count',3)):
        if type(report.get(key)) is not int or report[key]!=count:raise ValueError('Exact native coverage count required')
    require_sequence(report['commands'],COMMANDS);require_sequence(report['scenarios'],SCENARIOS)
    if not all(row.get('passed') is True for row in report['scenarios']):raise ValueError('Named native scenario did not pass')
    before,after=report.get('input_sha256_before'),report.get('input_sha256_after')
    if not inputs or len(inputs)!=7 or before!=after or not isinstance(before,dict) or set(before)!=set(inputs):
        raise ValueError('Complete native fixture/executable input closure required')
    for reference,path in inputs.items():
        require_artifact(path.parent,path.name,before[reference]);bound[reference]=before[reference]
    for number,row in enumerate(report['commands'],1):
        expected_name=f'{number:02d}-{COMMANDS[number-1]}.log'
        if row.get('passed') is not True or row.get('tree_reaped') is not True or row.get('exit_code')!=0 or row.get('log')!=expected_name:
            raise ValueError('Exact owned native command required')
        raw=read_local(folder,expected_name,16*1024)
        expected='sha256:'+hashlib.sha256(raw).hexdigest()
        if expected!=row.get('log_sha256'):raise ValueError('Native stdout commitment differs')
        observed=json.loads(raw)
        counters=dict(attempted=1 if number==1 else 0,local_staged=0,cloud_acknowledged=1 if number==1 else 0,unavailable=0,conflicts=0)
        if observed!=dict(status='COMPLETE',**counters) or observed!=row.get('result') or any(type(observed[key]) is not int for key in counters):
            raise ValueError('Actual native historical publication counters differ')
        path=require_artifact(folder,expected_name,expected);bound[path.relative_to(project).as_posix()]=expected
