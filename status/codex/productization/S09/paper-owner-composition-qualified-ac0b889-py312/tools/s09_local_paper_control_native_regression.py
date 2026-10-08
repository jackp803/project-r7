"""Scoped native build, baseline smoke, historical publication and actual API reads."""
from pathlib import Path
import json,os,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,capture_qualification,sha,stamp,BASE,PROJECT,REPO
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read,_posix_read
from application.platform.supervision import _local_path
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.qualification import revision_fact,_sanitize

REVISION='41fa2fe0d74435fed5831ed728af8b87c28883f0'

def read_input(path,limit):
    # Exactly one fixed tracked native helper has a name outside cloud grammar.
    # Preserve opened-ancestor/reparse checks; never extend this to private paths.
    if path==REPO/'src/application/platform/_loopback_probe.py':
        _local_path(path)
        return (_windows_read if os.name=='nt' else _posix_read)(path,limit)
    return read_local(path.parent,path.name,limit)

def main():
    short=REVISION[:7];qualification=BASE/f'r7-productization-S09-owner-worker-qualified-{short}'
    report,context,qualification_hashes=capture_qualification(qualification,REVISION)
    assert report['tests_run']==1974 and len(context['source_input_hashes'])==610
    output=BASE/f'r7-native-windows-S09-local-control-{short}';package=output/'dist/R7'
    proof=BASE/f'S09-local-control-{short}-native-regression.json'
    assert not os.path.lexists(proof) and not os.path.lexists(output)
    paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_local_paper_control_native_http.py',
        BASE/'s13_native_access_integrity.py',REPO/'src/application/platform/_loopback_probe.py',
        REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',BASE/'s14_feedback_cli_native_paper.py',
        BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',qualification/'qualification.json',
        qualification/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py']
    def hashes():return {path.relative_to(PROJECT).as_posix():sha(read_input(path,64*1024**2)) for path in paths}
    captured={path.relative_to(PROJECT).as_posix():value for path,value in qualification_hashes.items()}
    for path in paths:
        if path not in qualification_hashes:captured[path.relative_to(PROJECT).as_posix()]=sha(read_input(path,64*1024**2))
    assert captured[(BASE/'s09_owner_worker_source_qualify.py').relative_to(PROJECT).as_posix()]==context['launcher_sha256']
    identity=None
    value=dict(passed=False,executable_revision=REVISION,source_qualification='PASS',input_hashes_before=captured,commands=[],
        native_worker_invoked=False,ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',
        scope='SOURCE_COMPONENT_AND_SCOPED_NATIVE_FIRST_RUN_HISTORICAL_PUBLICATION_AUTHENTICATED_EMPTY_READ_AND_START_DENIAL',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu='NOT_RUN')
    stages=[('build',[str(PROJECT/'toolchains/py312-native-build/Scripts/python.exe'),str(REPO/'tools/build_product.py'),
        '--output',str(output),'--expected-revision',REVISION],1000),
        ('smoke',[sys.executable,str(REPO/'tools/verify_native_product.py'),'--package-root',str(package),
            '--output',str(BASE/f'r7-native-S09-local-control-smoke-{short}')],600),
        ('historical-paper',[sys.executable,str(BASE/'s14_feedback_cli_native_paper.py'),str(package),
            str(BASE/'S14LocalFakeRclone.exe'),str(BASE/f'r7-native-S09-local-control-historical-{short}')],600),
        ('paper-reader',[sys.executable,str(BASE/'s09_local_paper_control_native_http.py'),str(package),
            str(BASE/f'r7-native-S09-local-control-reader-{short}')],180)]
    with OwnedProof(proof) as proof_owner:
        for label,argv,timeout in stages:
            revision_fact(REPO,REVISION,True);assert hashes()==captured
            if identity is not None:assert verify_distribution(package)==identity
            log=BASE/f'S09-local-control-{short}-native-{label}.log';owned=None;started=stamp()
            try:
                with OwnedProof(log) as log_owner:
                    owned=spawn_owned(argv,cwd=REPO,limits=ResourceLimits(timeout),stdout=log_owner.stream,stderr=subprocess.STDOUT)
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
        value.update(passed=True,input_hashes_after=hashes());proof_owner.persist(value)
    print(json.dumps(dict(passed=True,stages=4,ordinary_native_paper='NOT_RUN')),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
