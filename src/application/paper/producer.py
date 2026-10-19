"""Owning fixed PQR execution in the existing E6 software-only receipt store.

No imported results, request-selected test inventory, arbitrary program, or
per-signal qualification. The development tool uses this composition after the
fixed inventory and exact source have been committed.
"""
from contextlib import ExitStack
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from application.cloud.manifest import safe_relative
from application.config import load_config,product_namespace
from application.datasets.catalog import read_local
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import PROCESS_ROLES
from application.qualification import revision_fact,parse_result,_sanitize,discover_suites,FOCUSED
from registry.product_assessment import canonical,digest
from storage import open_sqlite_platform
from storage.qualification import QualificationSubject,QualificationCheck,_open_qualification_receipt_owner
from strategy.v02.capabilities import _source_revision,build_capability_snapshot
from .inventory import fixed_profile,current_target
from .qualification import validate_qualified_receipt,artifact_bytes


def executed_cases(text):
    # TextTestResult places a method's short docstring on a second line.
    # Both forms retain the exact test ID and require its actual success row.
    return re.findall(r'^test[^\r\n]* \(([^()\r\n]+)\)(?: \.\.\.|\r?\n[^\r\n]* \.\.\.) ok[ \t]*$',text,re.MULTILINE)


def require_executed_cases(text,expected):
    observed=executed_cases(text)
    if observed!=expected or not observed or len(observed)!=len(set(observed)):
        raise ValueError('Actual executed case inventory differs from committed profile')
    return observed


def native_artifacts(report,root):
    artifacts=report.get('artifacts') if isinstance(report,dict) else None
    from .qualification import MAX_EXECUTION_ARTIFACTS
    if not isinstance(artifacts,list) or not 1<=len(artifacts)<=MAX_EXECUTION_ARTIFACTS-1:
        raise ValueError('Complete bounded retained native artifact inventory required')
    bindings={}
    for artifact in artifacts:
        if not isinstance(artifact,dict) or set(artifact)!={'ref','hash'}:
            raise ValueError('Exact native artifact binding required')
        ref=safe_relative(artifact['ref'])
        if ref in bindings or 'sha256:'+hashlib.sha256(artifact_bytes(root,ref)).hexdigest()!=artifact['hash']:
            raise ValueError('Retained native artifact changed or duplicated')
        bindings[ref]=artifact['hash']
    return bindings


def native_assertions(report,member,root):
    rows=report.get('assertions') if isinstance(report,dict) else None
    if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows) or [row.get('assertion_id') for row in rows]!=member['assertions']:
        raise ValueError('Required actual native observations missing')
    bindings=native_artifacts(report,root)
    for row in rows:
        if set(row)!={'assertion_id','status','evidence_ref','evidence_hash'} or row['status']!='PASS':
            raise ValueError('Native observation did not pass')
        ref=safe_relative(row['evidence_ref'])
        if bindings.get(ref)!=row['evidence_hash']:raise ValueError('Actual native observation artifact missing or changed')
    return rows


def _retain_execution_failure(output,checks,results,error,tree_reaped):
    # Exception text may contain uncontrolled input or paths. Retain only its
    # bounded type and actual cleanup, never an invented successful member.
    ref='execution-failure.log'
    raw=(canonical(dict(status='FAILED',error_type=type(error).__name__[:96],
        tree_reaped=tree_reaped,scope='OWNING_FIXED_SOFTWARE_EXECUTION_ONLY'))+'\n').encode('utf-8')
    write_private_new(output/ref,raw)
    label='PQR-EXECUTION-FAILURE';commitment='sha256:'+hashlib.sha256(raw).hexdigest()
    checks.append(QualificationCheck(check_id=label,command_ref='owning-fixed-execution',log_ref=ref,
        log_hash=commitment,returncode=2,tree_reaped=tree_reaped,duration_ms=0,
        tests_run=0,failures=0,errors=1,skipped=0,expected_failures=0,unexpected_successes=0))
    results.append(dict(member_id=label,group_id='PQR-ERROR',test_cases=[],assertions=[],
        artifacts=[dict(ref=ref,hash=commitment)]))


def _guard(root,revision,package,facts,profile):
    revision_fact(root,revision,True)
    # Qualification source tool only. Admission/protection never measures or
    # launches the external interpreter/Node/browser execution toolchain.
    from tools.paper_toolchain import measure,require_same
    require_same(measure(root),profile.get('execution_toolchains',{}).get(current_target()))
    actual={p.relative_to(root).as_posix() for p in (root/'tests').rglob('*.py')}
    frozen={ref for ref in profile['source_files'] if ref.startswith('tests/')}
    if actual!=frozen:raise ValueError('Complete current test file discovery differs from frozen inventory')
    commands=[(f'tests/{name}',pattern) for name,pattern in FOCUSED]
    commands.extend((f'tests/{suite.name}','test_*.py') for suite in discover_suites(root))
    if commands!=[(m['directory'],m['pattern']) for m in profile['groups'][0]['members']]:
        raise ValueError('Complete ordered source commands differ from committed inventory')
    for ref,expected in profile['source_files'].items():
        if 'sha256:'+hashlib.sha256(read_local(root,ref,4*1024*1024)).hexdigest()!=expected:
            raise ValueError('Frozen tool/test/decision inputs changed')
    if verify_distribution(package)!=facts or _source_revision(root/'src')!=facts['implementation_hash']:
        raise ValueError('Current exact native/source subject changed')


def qualify(config_path,source_root,package_root):
    """Development/native qualification tool only; performs every fixed check."""
    if getattr(sys,'frozen',False) or sys.version_info[:2]!=(3,12):
        raise ValueError('Explicit local native CPython3.12 qualification tool required')
    config=load_config(config_path);root=Path(source_root).resolve();package=Path(package_root).resolve()
    if product_namespace(config)!='LOCAL_RESEARCH' or require_valid_restoration(config)['status']!='NOT_RESTORED':
        raise ValueError('Non-restored ordinary owning software store required')
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    if config.local_data_root.is_relative_to(package) or config.local_data_root.is_relative_to(root):
        raise ValueError('Private qualification data outside executable installation/source required')
    facts=verify_distribution(package);revision=facts['executable_revision'];target=current_target()
    profile=fixed_profile(target);_guard(root,revision,package,facts,profile)
    measured={**facts,'platform_id':target,'capability_hash':build_capability_snapshot().snapshot_hash}
    execution='pqr-'+uuid.uuid4().hex
    checks=[];results=[];started=datetime.now(timezone.utc);complete=False
    with ExitStack() as stack:
        for role in PROCESS_ROLES:
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config:raise ValueError('Qualification configuration changed')
        if not config.local_data_root.exists():create_private_directory(config.local_data_root)
        # Initialize through E6 namespace binding, never raw database mutation.
        with open_sqlite_platform(config.database_path,research_namespace='LOCAL_RESEARCH'):pass
        base=config.local_data_root/'qualification'
        if not base.exists():create_private_directory(base)
        require_private(base,directory=True)
        output=base/execution;create_private_directory(output)
        write_private_new(output/'preflight.json',(canonical(dict(profile=profile,measured=measured,
            execution_id=execution,source_revision=revision,source_worktree='CLEAN'))+'\n').encode('utf-8'))
        env=os.environ.copy();env.update(PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
        tree_reaped=True
        try:
            for group in profile['groups']:
                for member in group['members']:
                    _guard(root,revision,package,facts,profile)
                    label=member['member_id'];log_ref=label+'.log';raw=output/(label+'.raw')
                    command=[sys.executable,'-X','utf8']
                    native_output=output/(label+'-artifacts')
                    if member['kind']=='UNITTEST':
                        command+=['-m','unittest','discover','-s',member['directory'],'-p',member['pattern'],'-v']
                    else:
                        command+=[str(root/member['tool_ref']),'--package-root',str(package),'--output',str(native_output)]
                        if group['check_id']!='PQR-02':command+=['--group',group['check_id']]
                    before=time.monotonic()
                    tree_reaped=False
                    with raw.open('xb') as stream:
                        owned=None
                        try:
                            owned=spawn_owned(command,cwd=root,limits=ResourceLimits(member['timeout_seconds']),stdout=stream,stderr=subprocess.STDOUT,env=env)
                            code=owned.wait()
                        finally:
                            if owned is not None:
                                tree_reaped=False
                                cleanup=terminate_owned(owned,deadline_seconds=5)
                                tree_reaped=cleanup.reaped
                    text=_sanitize(artifact_bytes(output,raw.name).decode('utf-8',errors='replace').replace('\r\n','\n'),root).replace(str(config.local_data_root),'<LOCAL_DATA_ROOT>')
                    log_bytes=text.encode('utf-8');write_private_new(output/log_ref,log_bytes)
                    raw.unlink() # Only after sanitized retention has succeeded.
                    artifacts=[dict(ref=log_ref,hash='sha256:'+hashlib.sha256(log_bytes).hexdigest())]
                    assertions=[];cases=[]
                    parsed=parse_result(text,returncode=code)
                    if member['kind']=='UNITTEST':
                        try:cases=require_executed_cases(text,member['test_cases'])
                        except ValueError:code=code or 2
                        if not parsed.passed:code=code or 2
                        counts={key:getattr(parsed,key) for key in ('tests_run','failures','errors','skipped','expected_failures','unexpected_successes')}
                    else:
                        counts=dict(tests_run=0,failures=0,errors=0,skipped=0,expected_failures=0,unexpected_successes=0)
                        try:
                            report=json.loads(artifact_bytes(native_output,'pqr-result.json',262144))
                            for ref,commitment in native_artifacts(report,native_output).items():
                                artifacts.append(dict(ref=f'{native_output.name}/{ref}',hash=commitment))
                            rows=native_assertions(report,member,native_output)
                            for row in rows:
                                prefixed=f'{native_output.name}/{row["evidence_ref"]}'
                                assertions.append({**row,'evidence_ref':prefixed})
                        except (ValueError,OSError,KeyError,TypeError):code=code or 2
                    check=QualificationCheck(check_id=label,command_ref=member['command_ref'],log_ref=log_ref,
                        log_hash=artifacts[0]['hash'],returncode=code,tree_reaped=owned.termination_report.reaped,
                        duration_ms=int((time.monotonic()-before)*1000),**counts)
                    checks.append(check);results.append(dict(member_id=label,group_id=group['check_id'],test_cases=cases,
                        artifacts=artifacts,assertions=assertions))
                    print(json.dumps(dict(member=label,passed=check.passed,tests=check.tests_run,tree_reaped=check.tree_reaped)),flush=True)
                    _guard(root,revision,package,facts,profile)
                    # Keep actual failed outcomes. A repaired candidate must use a
                    # distinct execution with its separately committed inventory.
                    if not check.passed:break
                if checks and not checks[-1].passed:break
        except Exception as error:
            _retain_execution_failure(output,checks,results,error,tree_reaped)
        evidence=dict(schema_version='r7-qualified-paper-execution-evidence-v0.2',provenance='FIXTURE_SOFTWARE_CHECKS_ONLY',members=results)
        with _open_qualification_receipt_owner(config.database_path,namespace='LOCAL_RESEARCH') as owner:
            receipt=owner._append(execution_id=execution,subject=QualificationSubject(namespace='LOCAL_RESEARCH',
                **{key:measured[key] for key in ('executable_revision','implementation_hash','build_hash','platform_id')}),
                profile_id=profile['profile_id'],profile_hash=digest(canonical(profile)),checks=tuple(checks),
                started_at=started,finished_at=datetime.now(timezone.utc),profile_manifest=profile,execution_evidence=evidence)
        try:validate_qualified_receipt(receipt,profile,artifact_root=output,measured=measured);complete=True
        except ValueError:pass
        result=dict(status='NATIVE_PAPER_SOFTWARE_QUALIFIED' if complete else 'NATIVE_PAPER_SOFTWARE_NOT_QUALIFIED',
            receipt_ref=receipt.receipt_id,execution_id=execution,profile_hash=receipt.profile_hash,
            platform_id=target,executable_revision=revision,build_hash=facts['build_hash'],
            groups_completed=sum(all(any(c.check_id==m['member_id'] and c.passed for c in checks)
                for m in group['members']) for group in profile['groups']),groups_required=7,
            provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',financial_authority='NONE')
        write_private_new(output/'result.json',(canonical(result)+'\n').encode('utf-8'))
    return result
