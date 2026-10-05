from dataclasses import asdict
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from application.cloud.command_runner import CommandResult
from application.cloud.manifest import byte_hash, canonical_bytes
from application.cloud.protocol import ArtifactBundle, CloudError
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.config import ProductConfig
from application.platform.private_files import create_private_directory, write_private_new
from tests.application.cloud_fixtures import package


class LocalFakeRclone:
    """Local bytes and filesystem effects, never cloud/private API access."""
    def __init__(self, root):
        self.root=root;self.extra_rows=[];self.outage=False;self.corrupt_readback=False
    def __call__(self, argv, **policy):
        operation=argv[1]
        if self.outage:
            return CommandResult('COMMAND_FAILED',3,True,b'',0,0)
        def remote(value):
            return self.root/value.split(':',1)[1]
        if operation=='lsjson':
            rows=[]
            for path in sorted(self.root.rglob('*')):
                if path.is_file():
                    raw=path.read_bytes();relative=path.relative_to(self.root).as_posix()
                    rows.append(dict(Path=relative,Name=path.name,Size=len(raw),IsDir=False,ID='synthetic-'+relative,
                        Hashes={'MD5':hashlib.md5(raw).hexdigest()}))
            raw=json.dumps(rows+self.extra_rows).encode()
        elif operation=='cat':
            path=remote(argv[2])
            if not path.exists():return CommandResult('COMMAND_FAILED',3,True,b'',0,0)
            raw=path.read_bytes()[:int(argv[argv.index('--head')+1])]
            if self.corrupt_readback and path.name!='.r7-root.json':raw=b'wrong synthetic readback'
        elif operation=='copyto':
            source,destination=argv[2:4]
            source=remote(source) if ':' in source and not Path(source).is_absolute() else Path(source)
            destination=remote(destination) if ':' in destination and not Path(destination).is_absolute() else Path(destination)
            raw=source.read_bytes()
            if destination.exists() and destination.read_bytes()!=raw:
                return CommandResult('COMMAND_FAILED',9,True,b'',0,0)
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw);raw=b''
        else:raise AssertionError('Unexpected bridge operation')
        if len(raw)>policy['stdout_limit']:return CommandResult('OUTPUT_LIMIT_EXCEEDED',0,True,b'',len(raw),0)
        return CommandResult('COMPLETE',0,True,raw,len(raw),0)


class CloudBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 橋接 模擬 ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.stage=self.root/'本機 雲端 暫存';self.stage.mkdir()
        self.data=self.root/'本機 私密';self.data.mkdir()
        self.remote=self.root/'模擬 遠端';self.remote.mkdir()
        self.marker=canonical_bytes(dict(root_id='bridge-fixture'))
        (self.stage/'.r7-root.json').write_bytes(self.marker);(self.remote/'.r7-root.json').write_bytes(self.marker)
        self.private=self.data/'bridge-private';create_private_directory(self.private)
        self.reference=self.private/'protected-rclone.conf';write_private_new(self.reference,b'SYNTHETIC_REFERENCE_NOT_READ_BY_R7')
        self.config=ProductConfig('r7-product-config-v0.2','bridge-fixture',self.data,self.stage,self.data/'canonical.sqlite3')
        self.settings=self.data/'bridge-profile.json'
        self.payload=dict(schema_version='r7-rclone-bridge-config-v0.2',executable=str(Path(sys.executable)),
            executable_sha256=byte_hash(Path(sys.executable).read_bytes()),rclone_config_ref=str(self.reference),
            remote_alias='fixture-r7',drive_root_folder_id='synthetic_drive_root_0001',root_id='bridge-fixture',
            private_work_root=str(self.private),timeout_seconds=30,max_listing_bytes=1024*1024,max_transfer_bytes=16*1024*1024)
        self.write_settings();self.fake=LocalFakeRclone(self.remote)

    def write_settings(self):
        self.settings.write_text(json.dumps(self.payload),encoding='utf-8')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.cloud.rclone_bridge'),
                             'The explicitly scoped copy bridge is not implemented')
        return importlib.import_module('application.cloud.rclone_bridge')

    def bridge(self):
        module=self.module()
        return module.RcloneBridge(module.load_bridge_profile(self.settings,self.config),runner=self.fake)

    def staged_bundle(self):
        bundle=ArtifactBundle('receipts/bridge-fixture/submission-1/generation-1',{'receipt.json':canonical_bytes(dict(status='INTAKE_ACCEPTED',strategy_id='example',revision=1))})
        receipt=SyncedFolderCloudTransport(self.stage,expected_root_id='bridge-fixture').publish(bundle,'operation-1')
        self.assertEqual(receipt.status,'LOCAL_STAGED')
        return bundle,receipt

    def test_configuration_reference_is_metadata_only_and_package_flags_are_rejected(self):
        from unittest.mock import patch
        module=self.module();original=Path.read_bytes
        def read(path):
            if path==self.reference:raise AssertionError('R7 Python must never open the protected OAuth reference')
            return original(path)
        with patch.object(Path,'read_bytes',read):
            profile=module.load_bridge_profile(self.settings,self.config)
        self.assertEqual(profile.remote_alias,'fixture-r7')
        from jsonschema import Draft202012Validator,ValidationError
        schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/rclone_bridge_profile_v0_2.schema.json').read_bytes())
        validator=Draft202012Validator(schema);validator.validate(self.payload)
        with self.assertRaises(ValidationError):validator.validate({**self.payload,'extra_flags':['sync']})
        self.payload['extra_flags']=['sync','--delete-before'];self.write_settings()
        with self.assertRaises(CloudError):module.load_bridge_profile(self.settings,self.config)

    def test_actual_local_bytes_reach_fake_remote_and_ack_requires_every_byte_readback(self):
        bundle,local=self.staged_bundle();bridge=self.bridge()
        result=bridge.push_bundle(bundle.logical_path)
        self.assertEqual(result.status,'CLOUD_ACKNOWLEDGED')
        self.assertEqual(result.operation_id,local.operation_id)
        self.assertEqual(result.artifact_hash,local.artifact_hash)
        for path in (self.stage/bundle.logical_path).iterdir():
            self.assertEqual((self.remote/bundle.logical_path/path.name).read_bytes(),path.read_bytes())
        before={path.relative_to(self.remote).as_posix():path.read_bytes() for path in self.remote.rglob('*') if path.is_file()}
        self.assertEqual(bridge.push_bundle(bundle.logical_path),result)
        self.assertEqual({path.relative_to(self.remote).as_posix():path.read_bytes() for path in self.remote.rglob('*') if path.is_file()},before)

    def test_duplicate_remote_names_conflict_before_any_runtime_payload_is_written(self):
        bundle,_=self.staged_bundle();bridge=self.bridge()
        self.fake.extra_rows=[dict(Path='.r7-root.json',Name='.r7-root.json',Size=len(self.marker),IsDir=False,ID='another-synthetic-object')]
        with self.assertRaises(CloudError) as caught:bridge.push_bundle(bundle.logical_path)
        self.assertEqual(caught.exception.code,'CONFLICT')
        self.assertFalse((self.remote/'receipts').exists())

    def test_remote_outage_and_wrong_readback_never_acknowledge_local_stage(self):
        bundle,local=self.staged_bundle();bridge=self.bridge();self.fake.outage=True
        with self.assertRaises(CloudError):bridge.push_bundle(bundle.logical_path)
        self.fake.outage=False;self.fake.corrupt_readback=True
        with self.assertRaises(CloudError):bridge.push_bundle(bundle.logical_path)
        self.assertEqual(local.status,'LOCAL_STAGED')

    def test_different_existing_remote_bytes_are_preserved_as_conflict(self):
        bundle,_=self.staged_bundle();bridge=self.bridge()
        target=self.remote/bundle.logical_path/'receipt.json';target.parent.mkdir(parents=True)
        target.write_bytes(b'{"status":"original remote evidence"}')
        with self.assertRaises(CloudError) as caught:bridge.push_bundle(bundle.logical_path)
        self.assertEqual(caught.exception.code,'CONFLICT')
        self.assertEqual(target.read_bytes(),b'{"status":"original remote evidence"}')

    def test_marker_loss_never_initializes_a_replacement_stage_root_or_remote(self):
        bundle,_=self.staged_bundle();bridge=self.bridge()
        (self.remote/'.r7-root.json').unlink()
        with self.assertRaises(CloudError) as caught:bridge.push_bundle(bundle.logical_path)
        self.assertEqual(caught.exception.code,'CLOUD_NOT_CONNECTED')
        self.assertFalse((self.remote/'.r7-root.json').exists())
        self.assertFalse((self.remote/'receipts').exists())

    def test_result_changed_after_validation_cannot_upload_unvalidated_private_bytes(self):
        bundle,_=self.staged_bundle();module=self.module()
        source=self.stage/bundle.logical_path/'receipt.json';original=source.read_bytes();changed=False
        def mutate_at_upload(argv, **policy):
            nonlocal changed
            if argv[1]=='copyto' and not changed:
                changed=True;source.write_bytes(b'{"provider_account_id":"synthetic-private-value"}')
            return self.fake(argv,**policy)
        bridge=module.RcloneBridge(module.load_bridge_profile(self.settings,self.config),runner=mutate_at_upload)
        with self.assertRaises(CloudError) as caught:
            bridge.push_bundle(bundle.logical_path)
        self.assertEqual(caught.exception.code,'CONFLICT')
        target=self.remote/bundle.logical_path/'receipt.json'
        self.assertEqual(target.read_bytes(),original,'Only the previously validated snapshot may reach the remote')

    def test_pull_stages_author_payload_before_manifest_and_ignores_runtime_results(self):
        folder,_,definition=package(self.remote)
        unrelated=self.remote/'reports/private.json';unrelated.parent.mkdir();unrelated.write_bytes(b'not an author input')
        result=self.bridge().pull_once()
        self.assertEqual(result['status'],'LOCAL_STAGED')
        self.assertEqual(result['files_staged'],2)
        for name in ('strategy.json','manifest.json'):
            self.assertEqual((self.stage/'inbox/strategies/submission-1'/name).read_bytes(),(folder/name).read_bytes())
        self.assertFalse((self.stage/'reports').exists())
        transport=SyncedFolderCloudTransport(self.stage,expected_root_id='bridge-fixture')
        descriptor=list(transport.discover())[0]
        snapshot=transport.snapshot(descriptor,self.data/'snapshots')
        from application.cloud.manifest import validate_package
        self.assertEqual(validate_package(snapshot).strategy.strategy_id,definition['strategy_id'])

    def test_missing_payload_is_retryable_and_unaccepted_manifest_can_evolve(self):
        folder,_,_=package(self.remote)
        definition=(folder/'strategy.json').read_bytes();(folder/'strategy.json').unlink()
        bridge=self.bridge();self.assertEqual(bridge.pull_once()['files_staged'],1)
        transport=SyncedFolderCloudTransport(self.stage,expected_root_id='bridge-fixture')
        descriptor=list(transport.discover())[0]
        with self.assertRaises(CloudError) as caught:transport.snapshot(descriptor,self.data/'snapshots')
        self.assertEqual(caught.exception.code,'INCOMPLETE_SYNC')
        (folder/'strategy.json').write_bytes(definition)
        manifest=json.loads((folder/'manifest.json').read_bytes());manifest['research_hypothesis']='updated before acceptance'
        (folder/'manifest.json').write_bytes(canonical_bytes(manifest))
        self.assertEqual(bridge.pull_once()['files_staged'],2)
        snapshot=transport.snapshot(descriptor,self.data/'snapshots')
        before={p.name:p.read_bytes() for p in snapshot.root.iterdir() if p.is_file()}
        manifest['research_hypothesis']='changed after acceptance';(folder/'manifest.json').write_bytes(canonical_bytes(manifest))
        bridge.pull_once()
        self.assertEqual({p.name:p.read_bytes() for p in snapshot.root.iterdir() if p.is_file()},before)

    def test_pull_duplicate_directory_or_malicious_path_fails_before_stage_mutation(self):
        package(self.remote);bridge=self.bridge()
        for extra in (dict(Path='inbox/strategies',Name='strategies',IsDir=True),
                      dict(Path='../outside',Name='outside',Size=1,IsDir=False),
                      dict(Path='inbox/strategies/submission-1/evil.py',Name='evil.py',Size=1,IsDir=False)):
            with self.subTest(path=extra['Path']):
                self.fake.extra_rows=[extra,extra] if extra['IsDir'] else [extra]
                with self.assertRaises(CloudError):bridge.pull_once()
                self.assertFalse((self.stage/'inbox').exists())

    def test_pull_transfer_budget_rejects_batch_before_download_or_stage(self):
        package(self.remote);self.payload['max_transfer_bytes']=4096;self.write_settings()
        self.fake.extra_rows=[dict(Path='datasets/example/v1/large.parquet',Name='large.parquet',Size=8192,IsDir=False)]
        with self.assertRaises(CloudError):self.bridge().pull_once()
        self.assertFalse((self.stage/'inbox').exists())

    def test_pull_actual_parquet_bytes_preserves_dataset_revision_identity(self):
        from tests.application.dataset_fixtures import dataset
        from application.datasets.catalog import DatasetCatalog
        folder=self.remote/'datasets/fixture-dataset/1';dataset(folder)
        bridge=self.bridge();result=bridge.pull_once()
        self.assertEqual(result['files_staged'],3)
        target=self.stage/'datasets/fixture-dataset/1'
        self.assertEqual(DatasetCatalog(target).load('dataset.json').as_dict()['namespace'],'FIXTURE')
        for path in folder.iterdir():self.assertEqual((target/path.name).read_bytes(),path.read_bytes())
        before=(target/'candles.parquet').read_bytes()
        (folder/'candles.parquet').write_bytes(before+b'changed')
        with self.assertRaises(CloudError) as caught:bridge.pull_once()
        self.assertEqual(caught.exception.code,'CONFLICT')
        self.assertEqual((target/'candles.parquet').read_bytes(),before)

    def test_changing_remote_download_never_mutates_stage(self):
        folder,_,_=package(self.remote);module=self.module();changed=False
        def mutate_at_download(argv,**policy):
            nonlocal changed
            if argv[1]=='copyto' and not changed:
                changed=True;(folder/'strategy.json').write_bytes(b'{"changed":true}')
            return self.fake(argv,**policy)
        bridge=module.RcloneBridge(module.load_bridge_profile(self.settings,self.config),runner=mutate_at_download)
        with self.assertRaises(CloudError) as caught:bridge.pull_once()
        self.assertEqual(caught.exception.code,'INCOMPLETE_SYNC')
        self.assertFalse((self.stage/'inbox').exists())

    def test_bridge_transport_never_acknowledges_an_outage_and_retries_same_bundle(self):
        self.assertIsNotNone(importlib.util.find_spec('application.cloud.bridge_transport'))
        module=importlib.import_module('application.cloud.bridge_transport')
        transport=module.RcloneCloudTransport(self.bridge())
        bundle=ArtifactBundle('receipts/bridge-fixture/submission-1/generation-1',{'receipt.json':canonical_bytes(dict(status='INTAKE_ACCEPTED'))})
        self.fake.outage=True
        with self.assertRaises(CloudError):transport.publish(bundle,'operation-1')
        self.assertTrue((self.stage/bundle.logical_path/'manifest.json').is_file())
        self.fake.outage=False
        self.assertEqual(transport.publish(bundle,'operation-1').status,'CLOUD_ACKNOWLEDGED')

    def test_cli_pull_emits_only_sanitized_status_with_exact_fixed_argv(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        from application.cli import main
        product=self.data/'product.json'
        product.write_bytes(canonical_bytes(dict(schema_version=self.config.schema_version,product_instance_id=self.config.product_instance_id,
            local_data_root=str(self.data),cloud_root=str(self.stage))))
        package(self.remote);output=StringIO();calls=[]
        def runner(argv,**policy):calls.append(argv);return self.fake(argv,**policy)
        with patch('application.cloud.rclone_bridge.run_bounded',runner),redirect_stdout(output):
            code=main(['cloud-pull','--config',str(product),'--bridge-profile',str(self.settings)])
        self.assertEqual(code,0)
        result=json.loads(output.getvalue());self.assertEqual(result['files_staged'],2)
        self.assertNotIn(str(self.data),output.getvalue());self.assertNotIn(str(self.reference),output.getvalue())
        self.assertTrue(calls)
        for argv in calls:
            self.assertIn(argv[1],('lsjson','cat','copyto'))
            self.assertEqual(argv[argv.index('--drive-root-folder-id')+1],self.payload['drive_root_folder_id'])
            self.assertEqual(argv[argv.index('--config')+1],str(self.reference))
            self.assertNotIn('sync',argv);self.assertNotIn('delete',argv)

    def test_actual_outbox_crash_after_remote_upload_recovers_same_identity(self):
        from datetime import datetime,timezone
        from application.intake.ledger import IntakeLedger
        from application.cloud.publisher import Publisher
        from application.cloud.bridge_transport import RcloneCloudTransport
        now=datetime(2026,10,5,tzinfo=timezone.utc);database=self.data/'intake.sqlite'
        transport=RcloneCloudTransport(self.bridge())
        with IntakeLedger(database,instance_id=self.config.product_instance_id) as ledger:
            claim=ledger.claim('submission-1','sha256:'+'a'*64,'worker-1',now)
            ledger.commit_effect(claim,'synthetic-intake-1',canonical_bytes(dict(status='INTAKE_ACCEPTED')),now=now)
            def crash(point):raise RuntimeError('synthetic crash after upload before ACK')
            with self.assertRaises(RuntimeError):Publisher(ledger,transport,fault_hook=crash).flush(10)
            self.assertEqual(ledger.pending_outbox(10)[0].state,'PENDING')
        before={p.relative_to(self.remote).as_posix():p.read_bytes() for p in self.remote.rglob('*') if p.is_file()}
        with IntakeLedger(database,instance_id=self.config.product_instance_id) as ledger:
            self.assertEqual(Publisher(ledger,transport).flush(10).cloud_acknowledged,1)
            self.assertEqual(ledger.pending_outbox(10),())
        self.assertEqual({p.relative_to(self.remote).as_posix():p.read_bytes() for p in self.remote.rglob('*') if p.is_file()},before)

    def test_native_stage_directory_link_is_rejected_without_outside_write(self):
        import os,subprocess
        package(self.remote);outside=self.root/'outside';outside.mkdir()
        link=self.stage/'inbox'
        if os.name=='nt':
            subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(outside)],shell=False,check=True,capture_output=True)
        else:link.symlink_to(outside,target_is_directory=True)
        with self.assertRaises(CloudError) as caught:self.bridge().pull_once()
        self.assertEqual(caught.exception.code,'BLOCKED')
        self.assertEqual(list(outside.iterdir()),[])

    def test_self_contained_owner_feedback_roundtrip_rejects_changed_html_before_upload(self):
        from application.cloud.feedback import build_research_feedback,feedback_bundle
        from application.cloud.bridge_transport import RcloneCloudTransport
        from application.research.service import ResearchService
        from tests.application.test_research_pipeline import configured
        from tests.validation.robustness_fixtures import subject
        research=self.data/'synthetic-research';research.mkdir();configured(research)
        with ResearchService(local_root=research,database_path=research/'research.sqlite',registry_path=research/'registry.sqlite',namespace='FIXTURE',owner_id='feedback-owner') as service:
            run=service.run(submission_id='fixture-submission',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json')
            bundle=feedback_bundle(build_research_feedback(service,run.run_id))
        bridge=self.bridge();receipt=RcloneCloudTransport(bridge).publish(bundle,'feedback-operation-1')
        self.assertEqual(receipt.status,'CLOUD_ACKNOWLEDGED')
        self.assertEqual((self.remote/bundle.logical_path/'report.html').read_bytes(),bundle.payloads['report.html'])
        unsafe=ArtifactBundle('reports/feedback/example/1/unsafe',{'feedback.json':bundle.payloads['feedback.json'],
            'report.html':b'<script src="https://invalid.example/secret.js"></script>'})
        with self.assertRaises(CloudError):RcloneCloudTransport(bridge).publish(unsafe,'feedback-operation-2')
        self.assertFalse((self.stage/unsafe.logical_path).exists())
        self.assertFalse((self.remote/unsafe.logical_path).exists())

    def test_feedback_outbox_survives_remote_ack_crash_and_reopens_without_recomputation(self):
        from application.cloud.feedback import build_research_feedback,queue_feedback,flush_feedback
        from application.cloud.bridge_transport import RcloneCloudTransport
        from application.research.service import ResearchService
        from tests.application.test_research_pipeline import configured
        from tests.validation.robustness_fixtures import subject
        research=self.data/'synthetic-research';research.mkdir();configured(research)
        transport=RcloneCloudTransport(self.bridge())
        def owner():return ResearchService(local_root=research,database_path=research/'research.sqlite',registry_path=research/'registry.sqlite',namespace='FIXTURE',owner_id='feedback-owner')
        with owner() as service:
            run=service.run(submission_id='fixture-submission',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json')
            operation=queue_feedback(service,run.run_id)
            self.assertEqual(queue_feedback(service,run.run_id),operation)
            self.fake.outage=True
            self.assertEqual(flush_feedback(service.journal,transport,limit=10).unavailable,1)
            self.fake.outage=False
            def crash(point):raise RuntimeError('synthetic after upload before ACK')
            with self.assertRaises(RuntimeError):flush_feedback(service.journal,transport,limit=10,fault_hook=crash)
            self.assertEqual(len(service.journal.pending_feedback_publications(10)),1)
        before={p.relative_to(self.remote).as_posix():p.read_bytes() for p in self.remote.rglob('*') if p.is_file()}
        with owner() as service:
            self.assertEqual(flush_feedback(service.journal,transport,limit=10).cloud_acknowledged,1)
            self.assertEqual(service.journal.pending_feedback_publications(10),())
        self.assertEqual({p.relative_to(self.remote).as_posix():p.read_bytes() for p in self.remote.rglob('*') if p.is_file()},before)

    def test_cloud_dataset_import_seals_private_bytes_without_decoding_oos_and_real_e1_resolves_nested_manifest(self):
        from tests.application.dataset_fixtures import dataset
        from application.datasets.catalog import DatasetCatalog
        from application.datasets.resolver import DatasetResolver
        from unittest.mock import patch
        from application.platform.private_files import require_private
        folder=self.remote/'datasets/fixture-dataset/1';dataset(folder)
        bridge=self.bridge();bridge.pull_once()
        with patch('application.datasets.resolver._parquet_rows',side_effect=AssertionError('Import must not decode sealed OOS prices')):
            result=bridge.import_dataset('fixture-dataset','1')
        self.assertEqual(result['status'],'LOCAL_DATASET_STAGED')
        self.assertEqual(result['logical_verification'],'NOT_RUN')
        local=self.data/'datasets/fixture-dataset/1';require_private(local,directory=True)
        for name in ('dataset.json','candles.parquet','funding.parquet'):
            require_private(local/name);self.assertEqual((local/name).read_bytes(),(folder/name).read_bytes())
        actual=DatasetResolver(DatasetCatalog(self.data)).resolve('datasets/fixture-dataset/1/dataset.json')
        self.assertEqual(actual.namespace,'FIXTURE');self.assertEqual(len(actual.candles_by_timeframe['1h']),12)
        self.assertEqual(bridge.import_dataset('fixture-dataset','1'),result)
        before=(local/'candles.parquet').read_bytes()
        (self.stage/'datasets/fixture-dataset/1/candles.parquet').write_bytes(before+b'corruption')
        with self.assertRaises(CloudError):bridge.import_dataset('fixture-dataset','1')
        self.assertEqual((local/'candles.parquet').read_bytes(),before)

    def test_private_field_aliases_and_secret_or_local_path_text_never_reach_remote(self):
        from application.cloud.bridge_transport import RcloneCloudTransport
        transport=RcloneCloudTransport(self.bridge())
        for index,value in enumerate(({' provider_account_id ':'SYNTHETIC'}, {'providerAccountId':'SYNTHETIC'},
            {'note':'password=SYNTHETIC'}, {'note':r'C:\Users\Synthetic\private.json'})):
            with self.subTest(index=index):
                path='reports/redaction/fixture/'+str(index)
                with self.assertRaises(CloudError):transport.publish(ArtifactBundle(path,{'summary.json':canonical_bytes(value)}),'operation-'+str(index))
                self.assertFalse((self.stage/path).exists(),'Rejected bytes must never enter a possibly synchronized folder')
                self.assertFalse((self.remote/path).exists())

    def test_publication_budget_and_invalid_payload_are_rejected_before_any_stage_write(self):
        from application.cloud.bridge_transport import RcloneCloudTransport
        self.payload['max_transfer_bytes']=4096;self.write_settings()
        transport=RcloneCloudTransport(self.bridge())
        for index,payloads in enumerate(({'summary.json':canonical_bytes({'note':'x'*4096})},
            {'summary.json':canonical_bytes({'status':'safe'}),'unimplemented.html':b'<p>unsupported</p>'},
            {'summary.json':canonical_bytes({'status':'safe'}),'SUMMARY.json':b'{}'},
            {'summary.json':canonical_bytes({'status':'safe'}),'manifest.json':b'{}'})):
            with self.subTest(index=index):
                path='reports/prestage/fixture/'+str(index)
                with self.assertRaises(CloudError):transport.publish(ArtifactBundle(path,payloads),'prestage-'+str(index))
                self.assertFalse((self.stage/path).exists())
                self.assertFalse((self.remote/path).exists())

    def test_private_snapshot_disk_failure_becomes_sanitized_operational_unavailable(self):
        from unittest.mock import patch
        bundle,_=self.staged_bundle();bridge=self.bridge()
        with patch('application.cloud.rclone_bridge.create_private_directory',side_effect=PermissionError('SYNTHETIC_LOCAL_PRIVATE_PATH')):
            with self.assertRaises(CloudError) as caught:bridge.push_bundle(bundle.logical_path)
        self.assertEqual(caught.exception.code,'UNAVAILABLE')
        self.assertNotIn('SYNTHETIC_LOCAL_PRIVATE_PATH',str(caught.exception))
        self.assertFalse((self.remote/'receipts').exists())

    def test_cli_flushes_actual_receipt_and_feedback_ledgers_with_one_total_batch_limit(self):
        from datetime import datetime,timezone
        from application.cli import main
        from application.intake.ledger import IntakeLedger
        from application.cloud.feedback import queue_feedback
        from application.research.service import ResearchService
        from tests.application.test_research_pipeline import configured
        from tests.validation.robustness_fixtures import subject
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        configured(self.data)
        with ResearchService(local_root=self.data,database_path=self.data/'research.sqlite',registry_path=self.config.database_path,namespace='FIXTURE',owner_id='feedback-owner') as service:
            run=service.run(submission_id='fixture-submission',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json')
            queue_feedback(service,run.run_id)
        now=datetime(2026,10,5,tzinfo=timezone.utc)
        with IntakeLedger(self.data/'intake.sqlite',instance_id=self.config.product_instance_id) as ledger:
            claim=ledger.claim('submission-1','sha256:'+'a'*64,'worker-1',now)
            ledger.commit_effect(claim,'synthetic-intake-1',canonical_bytes(dict(status='INTAKE_ACCEPTED')),now=now)
        product=self.data/'product.json';product.write_bytes(canonical_bytes(dict(schema_version=self.config.schema_version,
            product_instance_id=self.config.product_instance_id,local_data_root=str(self.data),cloud_root=str(self.stage))))
        for expected in (1,1,0):
            output=StringIO()
            with patch('application.cloud.rclone_bridge.run_bounded',self.fake),redirect_stdout(output):
                code=main(['cloud-publish-outbox','--config',str(product),'--bridge-profile',str(self.settings),'--limit','1'])
            self.assertEqual(code,0);result=json.loads(output.getvalue())
            self.assertEqual(result['attempted'],expected);self.assertEqual(result['cloud_acknowledged'],expected)
        self.assertEqual(len(list(self.remote.glob('reports/feedback/**/feedback.json'))),1)
        self.assertEqual(len(list(self.remote.glob('receipts/**/receipt.json'))),1)


if __name__=='__main__':
    unittest.main()
