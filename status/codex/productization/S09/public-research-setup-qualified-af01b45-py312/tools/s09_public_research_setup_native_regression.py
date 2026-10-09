"""Fresh exact-clean candidate, actual frozen public setup and scoped native regressions."""
from pathlib import Path
import json,os,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,capture_qualification,sha,stamp,BASE,PROJECT,REPO
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read,_posix_read
from application.platform.supervision import _local_path
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.qualification import revision_fact,_sanitize

from s09_owner_worker_source_qualify import inputs
from local_windows_qualification_awake import awake_request
from s09_local_paper_control_native_regression import read_input

def finalize_pass(value,hashes,package,identity,revision):
    after=hashes()
    assert after==value['input_hashes_before']
    revision_fact(REPO,revision,True)
    assert verify_distribution(package)==identity
    value.update(passed=True,input_hashes_after=after)

def native_stages(revision,output,package):
    short=revision[:7]
    return [('build',[str(PROJECT/'toolchains/py312-native-build/Scripts/python.exe'),str(REPO/'tools/build_product.py'),
        '--output',str(output),'--expected-revision',revision],1000),
        ('smoke',[sys.executable,str(REPO/'tools/verify_native_product.py'),'--package-root',str(package),
            '--output',str(BASE/f'r7-native-S09-public-research-setup-reader-fixed-smoke-{short}')],600),
        ('historical-paper',[sys.executable,str(BASE/'s14_feedback_cli_native_paper.py'),str(package),
            str(BASE/'S14LocalFakeRclone.exe'),str(BASE/f'r7-native-S09-public-research-setup-reader-fixed-historical-{short}')],600),
        ('paper-reader',[sys.executable,str(BASE/'s12_storage_native_paper_reader.py'),str(package),
            str(BASE/f'r7-native-S12-storage-reader-fixed-reader-{short}'),revision],180),
        ('public-setup',[sys.executable,str(BASE/'s09_native_public_research_setup_probe.py'),str(package),
            str(BASE/f'r7-native-S09-public-setup-probe-{short}'),revision],600),
        ('long-backup',[sys.executable,str(BASE/'s09_native_long_backup_probe.py'),str(package),
            str(BASE/f'r7-native-S09-long-backup-probe-{short}'),revision],600)]

def main():
    REVISION=sys.argv[1]
    revision_fact(REPO,REVISION,True)
    short=REVISION[:7];qualification=BASE/f'r7-productization-S09-public-research-setup-qualified-{short}-long-path-fixed'
    report,context,qualification_hashes=capture_qualification(qualification,REVISION)
    assert inputs()==context['source_input_hashes']
    assert report['tests_run']==2052 and len(context['source_input_hashes'])==625
    for name in ['src/application/research/setup.py','tests/application/test_research_setup_flow.py','docs/product/v0_2/PUBLIC_RESEARCH_SETUP_FLOW.md']:
        assert name in context['source_input_hashes']
    output=BASE/f'r7-native-windows-S09-public-research-setup-{short}';package=output/'dist/R7'
    proof=BASE/f'S09-public-research-setup-{short}-native-regression.json'
    assert not os.path.lexists(proof) and not os.path.lexists(output)
    paths=[Path(__file__),BASE/'s09_local_paper_control_native_regression.py',BASE/'s09_owner_worker_native_regression.py',BASE/'s12_storage_native_paper_reader.py',
        BASE/'s13_native_access_integrity.py',REPO/'src/application/platform/_loopback_probe.py',
        REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',BASE/'s14_feedback_cli_native_paper.py',
        BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',qualification/'qualification.json',
        qualification/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py',
        BASE/'s09_public_research_setup_source_qualify.py',BASE/'local_windows_qualification_awake.py',
        BASE/'s09_native_public_research_setup_probe.py',BASE/'s09_native_long_backup_probe.py']
    def hashes():
        assert inputs()==context['source_input_hashes']
        return {path.relative_to(PROJECT).as_posix():sha(read_input(path,64*1024**2)) for path in paths}
    captured={path.relative_to(PROJECT).as_posix():value for path,value in qualification_hashes.items()}
    for path in paths:
        if path not in qualification_hashes:captured[path.relative_to(PROJECT).as_posix()]=sha(read_input(path,64*1024**2))
    assert captured[(BASE/'s09_public_research_setup_source_qualify.py').relative_to(PROJECT).as_posix()]==context['launcher_sha256']
    assert context['awake_request']['restored'] is True and context['awake_helper_sha256_before']==context['awake_helper_sha256_after']
    assert captured[(BASE/'local_windows_qualification_awake.py').relative_to(PROJECT).as_posix()]==context['awake_helper_sha256_after']
    identity=None
    value=dict(passed=False,executable_revision=REVISION,source_qualification='PASS',input_hashes_before=captured,commands=[],
        native_worker_invoked=False,ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',
        scope='PUBLIC_RESEARCH_SETUP_SOURCE_INCREMENT_BUILD_EXISTING_SCOPED_NATIVE_REGRESSIONS_AND_ACTUAL_FROZEN_SETUP;NO_NATIVE_RESEARCH_AUTH_OR_ORDINARY_PAPER_ACCEPTANCE',
        source_tests=report['tests_run'],source_commands=len(report['commands']),source_input_files=len(context['source_input_hashes']),child_source_package='EXACT_REPO_SRC_PINNED',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu='NOT_RUN')
    stages=native_stages(REVISION,output,package)
    temporary=BASE/f'S09-public-research-setup-{short}-native-temp'
    _local_path(temporary);assert not os.path.lexists(temporary);temporary.mkdir()
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temporary),TMP=str(temporary))
    with OwnedProof(proof) as proof_owner:
        with awake_request() as awake:
            for label,argv,timeout in stages:
                revision_fact(REPO,REVISION,True);assert hashes()==captured
                if identity is not None:assert verify_distribution(package)==identity
                log=BASE/f'S09-public-research-setup-{short}-native-{label}.log';owned=None;started=stamp()
                try:
                    with OwnedProof(log) as log_owner:
                        owned=spawn_owned(argv,cwd=REPO,limits=ResourceLimits(timeout),stdout=log_owner.stream,stderr=subprocess.STDOUT,env=environment)
                        code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
                        log_owner.require_owned();log_owner.stream.seek(0);raw=log_owner.stream.read(8*1024**2+1)
                        assert len(raw)<=8*1024**2
                        sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
                        log_owner.stream.seek(0);log_owner.stream.write(sanitized);log_owner.stream.truncate()
                        log_owner.stream.flush();log_owner.require_owned()
                        result=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
                            tree_reaped=cleanup.reaped,log=log.name,log_sha256=sha(sanitized),passed=code==0 and cleanup.reaped)
                    value['commands'].append(result);proof_owner.persist(value);print(json.dumps(result),flush=True)
                    revision_fact(REPO,REVISION,True);assert hashes()==captured
                    if not result['passed']:return 1
                    if label=='build':
                        identity=verify_distribution(package)
                        assert identity['executable_revision']==REVISION and identity['implementation_hash']==context['implementation_hash']
                        value['native_build_identity']=identity
                    assert verify_distribution(package)==identity
                finally:
                    if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
        assert awake['restored'] is True
        value['awake_request']=awake
        finalize_pass(value,hashes,package,identity,REVISION);proof_owner.persist(value)
    print(json.dumps(dict(passed=True,stages=len(stages),ordinary_native_paper='NOT_RUN')),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
