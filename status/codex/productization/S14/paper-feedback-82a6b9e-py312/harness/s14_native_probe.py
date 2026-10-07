"""Actual native CLI + local compiled fake transport; no real cloud/provider."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,os,sys
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.private_files import create_private_directory,write_private_new,require_private
from application.cloud.manifest import byte_hash,canonical_bytes
from application.research.holdout import ResearchTrialLedger
from tests.strategy.test_slice1_runtime import make_definition
from tests.strategy.v02_fixtures import definition_v02,field,operator
from tests.application.dataset_fixtures import dataset

package,selected,fake,output=map(lambda value:Path(value).absolute(),sys.argv[1:5])
assert output.is_relative_to(project/'artifacts') and not output.exists()
output.mkdir();identity=verify_distribution(package)
exe=package/json.loads((package/'distribution.json').read_bytes())['entrypoint']
selected_report=json.loads((selected/'native-selected-research.json').read_bytes())
assert selected_report['passed'] and selected_report['identity']==identity
product=selected/'研究 設定.json';settings=json.loads(product.read_bytes())
data,stage=Path(settings['local_data_root']),Path(settings['cloud_root'])
root_id=json.loads((stage/'.r7-root.json').read_bytes())['root_id']
private=data/'S14-bridge-private';create_private_directory(private)
remote=output/'模擬 遠端';remote.mkdir();(remote/'.r7-root.json').write_bytes(canonical_bytes(dict(root_id=root_id)))
reference=private/'synthetic-local-transport.conf'
write_private_new(reference,('SYNTHETIC_LOCAL_FAKE_TRANSPORT\n'+str(remote)+'\n').encode('utf-8'))
profile=private/'bridge-profile.json'
write_private_new(profile,canonical_bytes(dict(schema_version='r7-rclone-bridge-config-v0.2',executable=str(fake),executable_sha256=byte_hash(fake.read_bytes()),
    rclone_config_ref=str(reference),remote_alias='fixture-r7',drive_root_folder_id='synthetic_drive_root_0001',root_id=root_id,
    private_work_root=str(private),timeout_seconds=60,max_listing_bytes=1024*1024,max_transfer_bytes=16*1024*1024)))
env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ};env.update(PATH='',PYTHONUTF8='1')
cwd=output/'空白 工作 目錄';cwd.mkdir()
report=dict(profile='r7-native-S14-offline-copy-feedback-v0.2',identity=identity,passed=False,commands=[],scenarios=[],
    transport='OFFLINE_TRANSPORT_SIMULATION',real_rclone='NOT_RUN',real_cloud='NOT_RUN',ubuntu='NOT_RUN',
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',trading_runtime='NOT_STARTED',
    shadow='NOT_STARTED',paper='NOT_STARTED',live='NOT_STARTED',product_path='EMPTY',pythonpath='UNSET',node='UNAVAILABLE_ON_PATH',
    fake_transport_sha256=byte_hash(fake.read_bytes()),fake_transport_source_sha256=byte_hash((project/'artifacts/S14LocalFakeRclone.cs').read_bytes()))
def stamp():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def persist():
    (output/'native-S14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def command(name,args,expected=0):
    log=output/(str(len(report['commands'])+1).zfill(2)+'-'+name+'.log');owned=None;started=stamp()
    try:
        with log.open('xb') as stream:
            owned=spawn_owned([str(exe),*args],cwd=cwd,limits=ResourceLimits(120),stdout=stream,stderr=stream,env=env)
            code=owned.wait()
        raw=log.read_bytes();result=json.loads(raw)
        fact=dict(name=name,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,expected_exit_code=expected,
            tree_reaped=owned.termination_report.reaped,log=log.name,log_sha256=byte_hash(raw),passed=code==expected and owned.termination_report.reaped,result=result)
        report['commands'].append(fact);persist()
        assert fact['passed'],name
        return result
    finally:
        if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
def scenario(name):report['scenarios'].append(dict(name=name,passed=True));persist()
common=['--config',str(product),'--bridge-profile',str(profile)]
try:
    cap=output/'capabilities.json';cap_result=command('capabilities',['export-capabilities','--destination',str(cap)])
    capability=json.loads(cap.read_bytes());assert cap_result['snapshot_hash']==byte_hash(cap.read_bytes())
    assert capability['implementation_revision']==identity['implementation_hash']
    assert all(value=='NOT_RUN' for value in capability['platform_verification'].values())
    scenario('actual-native-current-capability-availability-without-platform-authority')
    inbox=remote/'inbox/strategies';inbox.mkdir(parents=True)
    for name in ('legacy','four-hour','multitimeframe','tactical'):
        definition=make_definition() if name=='legacy' else definition_v02();definition['strategy_id']='native-author-'+name
        if name=='multitimeframe':
            definition['required_timeframes']=['1h','4h'];definition['rules']['long']=operator('GT',field(timeframe='1h'),field(timeframe='4h'))
        source=output/(name+'-definition.json');source.write_bytes(canonical_bytes(definition))
        args=['author-package','--definition',str(source),'--destination',str(inbox/name),'--submission-id',name,
            '--package-version','0.1' if name=='legacy' else '0.2']
        if name=='tactical':args+=['--valid-from','2026-10-05T00:00:00Z','--valid-until','2026-10-05T04:00:00Z']
        result=command('author-'+name,args);assert result['execution_evidence']=='NOT_RUN' and result['financial_authority']=='NONE'
        scenario('actual-native-authoring-'+name)
    dataset(remote/'datasets/fixture-dataset/1')
    pulled=command('pull',['cloud-pull',*common]);assert pulled['files_staged']==11
    for file in (remote/'inbox').rglob('*'):
        if file.is_file():assert (stage/file.relative_to(remote)).read_bytes()==file.read_bytes()
    scenario('actual-native-owned-copy-download-and-author-staging')
    imported=command('import-dataset',['cloud-import-dataset',*common,'--dataset-id','fixture-dataset','--revision','1'])
    assert imported['logical_verification']=='NOT_RUN' and imported['namespace']=='FIXTURE'
    for name in ('dataset.json','candles.parquet','funding.parquet'):
        path=data/'datasets/fixture-dataset/1'/name;require_private(path)
        assert path.read_bytes()==(remote/'datasets/fixture-dataset/1'/name).read_bytes()
    scenario('actual-native-private-dataset-seal-without-oos-decoding-or-namespace-relabel')
    run_id=selected_report['actual_job']['outcome']['run_id']
    queued=command('queue-feedback',['queue-research-feedback','--config',str(product),'--run-id',run_id])
    assert queued['cloud']=='NOT_CONTACTED'
    with ResearchTrialLedger(data/'research.sqlite') as ledger:
        observations=ledger.holdout_observations()
    assert any(row['kind']=='CHAT_OBSERVATION' for row in observations)
    scenario('actual-native-owner-feedback-with-default-opt-out-and-chat-holdout-observation')
    ack=command('publish',['cloud-publish-outbox',*common,'--limit','10'])
    assert ack['cloud_acknowledged']==2 and ack['unavailable']==ack['conflicts']==0
    feedback_paths=list(remote.glob('reports/feedback/**/feedback.json'));assert len(feedback_paths)==1
    feedback=json.loads(feedback_paths[0].read_bytes());assert feedback['performance_policy']=='OPT_OUT'
    assert feedback['sealed_oos']['status']=='PASS' and feedback['sealed_oos']['performance'] is None
    assert feedback['paper']['status']==feedback['live']['status']=='NOT_RUN'
    assert 'net_pnl' not in feedback_paths[0].read_text(encoding='utf-8')
    html=feedback_paths[0].with_name('report.html').read_text(encoding='utf-8');assert '<script' not in html.lower() and 'https://' not in html
    scenario('actual-native-receipt-and-feedback-remote-byte-ack-through-local-compiled-fake')
    again=command('publish-idempotent',['cloud-publish-outbox',*common,'--limit','10']);assert again['attempted']==0
    scenario('actual-native-durable-ack-does-not-republish-completed-outboxes')
    from application.intake.ledger import IntakeLedger
    synthetic_private=canonical_bytes({'provider_account_id':'SYNTHETIC_PRIVATE_PRESTAGE'})
    with IntakeLedger(data/'intake.sqlite',instance_id=settings['product_instance_id']) as ledger:
        now=datetime.now(timezone.utc)
        claim=ledger.claim('synthetic-private-prestage','sha256:'+'e'*64,'fixture-prestage-owner',now)
        ledger.commit_effect(claim,'synthetic-private-prestage-effect',synthetic_private,now=now)
        private_path=ledger.pending_outbox(10)[0].logical_path
    denied=command('private-prestage-denied',['cloud-publish-outbox',*common,'--limit','10'],expected=2)
    assert denied['attempted']==denied['unavailable']==1 and denied['cloud_acknowledged']==denied['local_staged']==0
    assert not (stage/private_path).exists() and not (remote/private_path).exists()
    with IntakeLedger(data/'intake.sqlite',instance_id=settings['product_instance_id']) as ledger:
        pending=ledger.pending_outbox(10)
        assert len(pending)==1 and pending[0].payload==synthetic_private and pending[0].state=='UNAVAILABLE'
    scenario('actual-native-private-outbox-rejected-before-any-synchronized-stage-write-and-not-acknowledged')
    marker=remote/'.r7-root.json';before=marker.read_bytes();marker.unlink()
    lost=command('root-loss',['cloud-pull',*common],expected=2);assert lost['status']=='CLOUD_NOT_CONNECTED'
    assert not marker.exists();marker.write_bytes(before)
    scenario('actual-native-root-loss-denied-without-empty-root-initialization')
    report.update(passed=True,scenario_count=len(report['scenarios']),command_count=len(report['commands']))
except BaseException as error:
    report.update(passed=False,failure_class=type(error).__name__)
    raise
finally:persist()
print(json.dumps(dict(passed=report['passed'],scenarios=report['scenario_count'],commands=report['command_count'],transport=report['transport'])))
