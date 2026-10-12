"""Actual frozen long backup CLI, source-created synthetic stores only."""
from dataclasses import asdict
from pathlib import Path
import json,os,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,BASE,REPO,sha,stamp
sys.path.insert(0,str(REPO))
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact,_sanitize
from application.platform.distribution import verify_distribution
from application.platform.private_files import write_private_new,create_private_directory
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.supervision import _local_path
from tests.application.test_private_long_paths import PrivateLongPathTests
from tests.application.test_product_data_backup import ProductDataBackupTests

def main():
    package,output,revision=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
    revision_fact(REPO,revision,True);identity=verify_distribution(package)
    assert identity['executable_revision']==revision
    executable=package/json.loads(read_input(package/'distribution.json',8*1024**2))['entrypoint']
    _local_path(output);assert not os.path.lexists(output);output.mkdir()
    launcher=sha(read_input(Path(__file__),1024**2))
    environment={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    environment.update(PATH='',PYTHONUTF8='1')
    commands=[];scenarios=[];paths=PrivateLongPathTests();source=ProductDataBackupTests()
    def call(label,args,status):
        revision_fact(REPO,revision,True);assert verify_distribution(package)==identity
        owned=None;started=stamp()
        try:
            with OwnedProof(output/(label+'.log')) as proof:
                owned=spawn_owned([str(executable),*map(str,args)],cwd=output,limits=ResourceLimits(90),
                    stdout=proof.stream,stderr=subprocess.STDOUT,env=environment)
                code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
                proof.require_owned();proof.stream.seek(0);raw=proof.stream.read(4*1024**2+1)
                assert len(raw)<=4*1024**2
                sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
                proof.stream.seek(0);proof.stream.write(sanitized);proof.stream.truncate();proof.stream.flush();proof.require_owned()
                commands.append(dict(label=label,exit_code=code,tree_reaped=cleanup.reaped,started_at_utc=started,
                    finished_at_utc=stamp(),log=label+'.log',log_sha256=sha(sanitized),passed=code==0 and cleanup.reaped))
                assert code==0 and cleanup.reaped
                result=json.loads(raw);assert result['status']==status
                return result
        finally:
            if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
            revision_fact(REPO,revision,True);assert verify_distribution(package)==identity
    try:
        paths.setUp();source.setUp()
        profile_root=source.fixture.base/'native-profile-private';create_private_directory(profile_root)
        config=profile_root/'config.json'
        write_private_new(config,json.dumps({key:str(value) if isinstance(value,Path) else value
            for key,value in asdict(source.config).items()},ensure_ascii=False).encode())
        for number,kind,create,verify,status in [
            (1,'product','backup-product-data','verify-product-backup','PRODUCT_DATA_BACKUP_VERIFIED'),
            (3,'databases','backup-databases','verify-database-backup','DATABASE_BACKUP_VERIFIED')]:
            destination=paths.parent/('native-private-'+kind)
            assert len(str(destination))>280
            created=call(f'{number:02d}-{kind}-create',[create,'--config',config,'--destination',destination],status)
            verified=call(f'{number+1:02d}-{kind}-verify',[verify,'--config',config,'--destination',destination],status)
            assert created['backup_id']==verified['backup_id']
            if kind=='product':assert verified['coverage']=='COMPLETE_SUPPORTED_LOCAL_PROFILE'
            scenarios.append(dict(id='FROZEN_LONG_'+kind.upper()+'_BACKUP_AND_VERIFY',passed=True,path_length=len(str(destination))))
    finally:
        source_clean=source.doCleanups();paths_clean=paths.doCleanups()
        assert source_clean and paths_clean
    revision_fact(REPO,revision,True);assert verify_distribution(package)==identity
    assert sha(read_input(Path(__file__),1024**2))==launcher
    value=dict(passed=True,executable_revision=revision,native_build_identity=identity,commands=commands,scenarios=scenarios,
        launcher_sha256_before=launcher,launcher_sha256_after=launcher,private_fixture_removed=True,
        scope='ACTUAL_FROZEN_BACKUP_CLI_WITH_SOURCE_CREATED_SYNTHETIC_STORES;NO_NORMAL_RESEARCH_AUTH_PAPER_WORKFLOW',
        product_path='EMPTY',pythonpath='UNSET',paper='NOT_STARTED',research='NOT_STARTED',provider_requests=0,
        credentials='NONE',capital='NONE',github_compute='NOT_USED')
    with OwnedProof(output/'native-long-backup.json') as proof:proof.persist(value)
    print(json.dumps(dict(passed=True,scenarios=len(scenarios),commands=len(commands))),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
