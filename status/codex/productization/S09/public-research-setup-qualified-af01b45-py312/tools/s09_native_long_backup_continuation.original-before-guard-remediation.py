"""Fresh bounded repaired probe, preserving the five completed exact native stages."""
from pathlib import Path
import json,os,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,BASE,PROJECT,REPO,sha,stamp
from s09_owner_worker_source_qualify import inputs
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact,_sanitize
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from local_windows_qualification_awake import awake_request

def main():
    revision=sys.argv[1];short=revision[:7];revision_fact(REPO,revision,True)
    original_path=BASE/f'S09-public-research-setup-{short}-native-regression.json'
    original=json.loads(read_input(original_path,8*1024**2))
    assert original['passed'] is False and original['executable_revision']==revision
    assert [c['label'] for c in original['commands']]==['build','smoke','historical-paper','paper-reader','public-setup','long-backup']
    assert all(c['passed'] and c['tree_reaped'] for c in original['commands'][:5])
    assert original['commands'][-1]['exit_code']==1 and original['commands'][-1]['tree_reaped']
    old_probe=BASE/'s09_native_long_backup_probe.original-import-failure.py'
    for name,expected in original['input_hashes_before'].items():
        path=old_probe if name=='artifacts/s09_native_long_backup_probe.py' else PROJECT/name
        assert sha(read_input(path,64*1024**2))==expected
    source=BASE/f'r7-productization-S09-public-research-setup-qualified-{short}-long-path-fixed'
    context=json.loads(read_input(source/'qualification-context.json',8*1024**2))
    captured_source=inputs();assert captured_source==context['source_input_hashes']
    package=BASE/f'r7-native-windows-S09-public-research-setup-{short}/dist/R7'
    identity=verify_distribution(package);assert identity==original['native_build_identity']
    paths=[Path(__file__),BASE/'s09_native_long_backup_probe.py',old_probe,original_path,
        BASE/'s09_owner_worker_native_regression.py',BASE/'s09_owner_worker_source_qualify.py',
        BASE/'s09_local_paper_control_native_regression.py',BASE/'local_windows_qualification_awake.py']
    def capture():return {p.relative_to(PROJECT).as_posix():sha(read_input(p,64*1024**2)) for p in paths}
    before=capture();output=BASE/f'r7-native-S09-long-backup-private-fixed-probe-{short}'
    log=BASE/f'S09-public-research-setup-{short}-native-long-backup-private-fixed.log';owned=None
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
        TEMP=str(BASE/f'S09-public-research-setup-{short}-native-temp'),TMP=str(BASE/f'S09-public-research-setup-{short}-native-temp'))
    started=stamp()
    try:
        with awake_request() as awake,OwnedProof(log) as proof:
            owned=spawn_owned([sys.executable,str(BASE/'s09_native_long_backup_probe.py'),str(package),str(output),revision],
                cwd=REPO,limits=ResourceLimits(600),stdout=proof.stream,stderr=subprocess.STDOUT,env=environment)
            code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
            proof.require_owned();proof.stream.seek(0);raw=proof.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
            sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
            proof.stream.seek(0);proof.stream.write(sanitized);proof.stream.truncate();proof.stream.flush();proof.require_owned()
    finally:
        if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
    after=capture();assert before==after and inputs()==captured_source and verify_distribution(package)==identity
    revision_fact(REPO,revision,True);assert awake['restored'] is True
    value=dict(passed=code==0 and cleanup.reaped,executable_revision=revision,native_build_identity=identity,
        input_hashes_before=before,input_hashes_after=after,source_inputs_unchanged=True,awake_request=awake,
        started_at_utc=started,finished_at_utc=stamp(),exit_code=code,tree_reaped=cleanup.reaped,log=log.name,
        log_sha256=sha(sanitized),original_native_proof_sha256=sha(read_input(original_path,8*1024**2)),
        scope='REPAIRED_LONG_BACKUP_PROBE_ONLY;FIRST_FIVE_STAGES_KEEP_ORIGINAL_INPUT_BINDING;NO_OTHER_STAGES_REEXECUTED',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    with OwnedProof(BASE/f'S09-public-research-setup-{short}-native-long-backup-private-continuation.json') as proof:proof.persist(value)
    print(json.dumps(dict(passed=value['passed'],exit_code=code,tree_reaped=cleanup.reaped)),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
