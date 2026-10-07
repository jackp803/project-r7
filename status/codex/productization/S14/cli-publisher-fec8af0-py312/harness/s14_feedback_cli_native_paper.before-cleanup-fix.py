"""Native historical PAPER publication with source-created fixture and fake exe."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,os,sqlite3,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from application.cloud.manifest import byte_hash,canonical_bytes
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.qualification import revision_fact
from strategy.v02.capabilities import _revision
from storage.paper_feedback import PaperFeedbackOutbox
from storage.paper_process import open_paper_process_journal
from tests.product import test_paper_runtime_v02 as fixtures

package,fake,output=map(lambda value:Path(value).absolute(),sys.argv[1:])
assert output.is_relative_to(base) and not output.exists()
identity=verify_distribution(package);revision=identity['executable_revision']
source_before=revision_fact(repo,revision,True)
assert _revision()==identity['implementation_hash']
fixture_names=('tests/product/test_paper_runtime_v02.py','tests/registry/test_operational_lifecycle_v02.py',
               'tests/application/test_product_assessment_binding.py','tests/validation/test_paper_promotion_policy.py')
input_paths=[Path(__file__),fake,base/'S14LocalFakeRclone.cs',*(repo/name for name in fixture_names)]
capture=lambda:{path.relative_to(project).as_posix():byte_hash(path.read_bytes()) for path in input_paths}
inputs_before=capture();output.mkdir()
data=output/'私密 歷史';create_private_directory(data)
stage=output/'本機 暫存';stage.mkdir();remote=output/'模擬 遠端';remote.mkdir()
root_id='native-paper-feedback-fixture'
marker=canonical_bytes(dict(root_id=root_id))
(stage/'.r7-root.json').write_bytes(marker);(remote/'.r7-root.json').write_bytes(marker)
private=data/'bridge-private';create_private_directory(private)
reference=private/'synthetic-transport.conf'
write_private_new(reference,('SYNTHETIC_LOCAL_FAKE_TRANSPORT\n'+str(remote)+'\n').encode('utf-8'))
product=data/'product.json';write_private_new(product,canonical_bytes(dict(
    schema_version='r7-product-config-v0.2',product_instance_id=root_id,
    local_data_root=str(data),cloud_root=str(stage))))
profile=private/'bridge-profile.json';write_private_new(profile,canonical_bytes(dict(
    schema_version='r7-rclone-bridge-config-v0.2',executable=str(fake),executable_sha256=byte_hash(fake.read_bytes()),
    rclone_config_ref=str(reference),remote_alias='fixture-r7',drive_root_folder_id='synthetic_drive_root_0001',
    root_id=root_id,private_work_root=str(private),timeout_seconds=60,max_listing_bytes=1024*1024,
    max_transfer_bytes=16*1024*1024)))
exe=package/json.loads((package/'distribution.json').read_bytes())['entrypoint']
cwd=output/'空白 工作';cwd.mkdir()
env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
env.update(PATH='',PYTHONUTF8='1')
report=dict(identity=identity,passed=False,commands=[],scenarios=[],source_before=source_before,
    harness_binding='BEFORE_AND_AFTER_EVERY_NATIVE_COMMAND',input_sha256_before=inputs_before,
    fixture_origin='SOURCE_CREATED_ACTUAL_E2_E5_E6_ACCELERATED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION',
    transport='OFFLINE_COMPILED_FAKE_ONLY',normal_runtime='NOT_RUN',real_cloud='NOT_RUN',real_forward='NOT_RUN',
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    native_path='EMPTY',native_pythonpath='UNSET',native_node='UNAVAILABLE_ON_PATH',
    financial_authority='NONE',ubuntu='NOT_RUN')
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def persist():
    (output/'native-paper-feedback.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def command(name):
    assert capture()==inputs_before and verify_distribution(package)==identity
    revision_fact(repo,revision,True)
    log=output/(f'{len(report["commands"])+1:02d}-'+name+'.log');owned=None;started=stamp()
    try:
        with log.open('xb') as stream:
            owned=spawn_owned([str(exe),'cloud-publish-outbox','--config',str(product),
                '--bridge-profile',str(profile),'--limit','1'],cwd=cwd,limits=ResourceLimits(120),
                stdout=stream,stderr=stream,env=env)
            code=owned.wait()
        result=json.loads(log.read_bytes())
        fact=dict(name=name,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
            tree_reaped=owned.termination_report.reaped,log=log.name,log_sha256=byte_hash(log.read_bytes()),
            result=result,passed=code==0 and owned.termination_report.reaped)
        report['commands'].append(fact);persist()
        assert fact['passed'] and capture()==inputs_before and verify_distribution(package)==identity
        revision_fact(repo,revision,True)
        return result
    finally:
        if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
owner=fixtures.PaperRuntimeV02Tests()
try:
    owner.setUp();runtime=owner.start();before=owner.process.recover(runtime.run_id)
    operation=PaperFeedbackOutbox(owner.process).queue(runtime)
    with sqlite3.connect(data/'canonical.sqlite3') as snapshot:owner.process._db.backup(snapshot)
    ack=command('historical-paper-publish')
    assert ack['status']=='COMPLETE' and ack['attempted']==ack['cloud_acknowledged']==1
    assert ack['local_staged']==ack['unavailable']==ack['conflicts']==0
    paths=list(remote.glob('reports/feedback/paper/**/feedback.json'));assert len(paths)==1
    feedback=json.loads(paths[0].read_bytes())
    assert feedback['source']['executable_revision']==revision and feedback['source']['worktree']=='CLEAN'
    assert feedback['source']['implementation_hash']==identity['implementation_hash']
    assert feedback['financial_authority']=='NONE' and feedback['performance_policy']=='OPT_OUT'
    assert feedback['observation']['mode']=='ACCELERATED_FIXTURE'
    assert feedback['observation']['actual_elapsed_seconds']==0 and feedback['live']['status']=='NOT_RUN'
    report['scenarios'].append(dict(name='native-historical-paper-exact-byte-ack-through-compiled-local-fake',passed=True))
    retry=command('historical-paper-idempotent');assert retry['attempted']==retry['cloud_acknowledged']==0
    report['scenarios'].append(dict(name='native-durable-paper-ack-is-not-republished',passed=True))
    with open_paper_process_journal(data/'canonical.sqlite3') as journal:
        assert journal.recover(runtime.run_id)==before
        rows=PaperFeedbackOutbox(journal).publications()
        assert len(rows)==1 and rows[0]['operation_id']==operation and rows[0]['state']=='CLOUD_ACKNOWLEDGED'
    assert owner.process.recover(runtime.run_id)==before
    report['scenarios'].append(dict(name='native-publication-preserves-historical-runtime-generation-and-checkpoint',passed=True))
    report.update(passed=True,scenario_count=len(report['scenarios']),command_count=len(report['commands']),
        source_after=revision_fact(repo,revision,True),input_sha256_after=capture(),
        implementation_hash_after=_revision())
    assert report['source_after']==source_before and report['input_sha256_after']==inputs_before
    assert report['implementation_hash_after']==identity['implementation_hash']
except BaseException as error:
    report.update(passed=False,failure_class=type(error).__name__)
    raise
finally:
    owner.doCleanups();persist()
print(json.dumps(dict(passed=report['passed'],scenarios=report['scenario_count'],commands=report['command_count'])))
