"""Normal owner/CLI/bridge integration; real local candidate, fake copy transport."""
from contextlib import contextmanager,redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application.cloud.manifest import canonical_bytes
from tests.application import test_product_assessment_binding as fixtures
from tests.application.dataset_fixtures import encoded
from tests.application.test_research_robustness import selected


@contextmanager
def actual_candidate():
    helper=fixtures.ProductAssessmentBindingTests()
    with TemporaryDirectory() as temporary:
        root=Path(temporary);selected(root)
        (root/'risk.json').write_bytes(encoded(fixtures.risk_fixture()))
        with helper.service(root) as service:
            result=helper.execute(service)
            if result.strategy_lifecycle!='CANDIDATE':raise AssertionError('Actual candidate prerequisite')
            yield root,service,result


class CandidateIndexIntegrationV02Tests(unittest.TestCase):
    def test_explicit_cli_queues_actual_owner_index_and_retry_keeps_original_operation(self):
        from application.cli import main
        from application.cloud.candidate_index import queue_candidate_index
        with actual_candidate() as (root,service,result):
            config=root/'product.json'
            config.write_bytes(canonical_bytes(dict(schema_version='r7-product-config-v0.2',
                product_instance_id='candidate-cli-fixture',local_data_root=str(root),
                cloud_root=None,database_path=str(root/'registry.sqlite'))))
            args=['queue-candidate-index','--config',str(config),'--run-id',result.run_id,'--namespace','FIXTURE']
            expected=queue_candidate_index(service,result.run_id)
            for _ in range(2):
                output=StringIO()
                with redirect_stdout(output):self.assertEqual(0,main(args))
                observed=json.loads(output.getvalue())
                self.assertEqual('CANDIDATE_INDEX_QUEUED',observed['status'])
                self.assertEqual(expected,observed['operation_id'])
                self.assertEqual('NOT_CONTACTED',observed['cloud'])
            self.assertEqual(1,len(service.journal.pending_candidate_index_publications(10)))

    def bridge_fixture(self):
        from tests.application.test_cloud_bridge import CloudBridgeTests
        fixture=CloudBridgeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        return fixture

    def test_actual_three_file_index_reaches_verified_fake_copy_and_tampered_html_never_stages(self):
        from application.cloud.bridge_transport import RcloneCloudTransport
        from application.cloud.candidate_index import queue_candidate_index,flush_candidate_indexes
        from application.cloud.protocol import ArtifactBundle,CloudError
        fixture=self.bridge_fixture()
        with actual_candidate() as (_,service,result):
            operation=queue_candidate_index(service,result.run_id)
            _,bundle,expected=service.journal.pending_candidate_index_publications(1)[0]
            transport=RcloneCloudTransport(fixture.bridge())
            result=flush_candidate_indexes(service.journal,transport,limit=1)
            self.assertEqual((1,0,1),(result.attempted,result.local_staged,result.cloud_acknowledged))
            for name,raw in bundle.payloads.items():
                self.assertEqual(raw,(fixture.remote/bundle.logical_path/name).read_bytes())
            receipt=json.loads((fixture.remote/bundle.logical_path/'manifest.json').read_bytes())
            self.assertEqual(operation,receipt['operation_id']);self.assertEqual(expected,receipt['artifact_hash'])
            self.assertEqual(0,flush_candidate_indexes(service.journal,transport,limit=1).attempted)
            before={p.relative_to(fixture.stage).as_posix():p.read_bytes() for p in fixture.stage.rglob('*') if p.is_file()}
            for payloads in ({**bundle.payloads,'report.html':b'<script>synthetic invalid html</script>'},
                             {**bundle.payloads,'extra.json':b'{}'}):
                with self.subTest(payloads=set(payloads)),self.assertRaises(CloudError):
                    transport.publish(ArtifactBundle(bundle.logical_path,payloads),operation)
                self.assertEqual(before,{p.relative_to(fixture.stage).as_posix():p.read_bytes() for p in fixture.stage.rglob('*') if p.is_file()})

    def test_normal_coordinator_queues_index_only_for_actual_completed_candidate(self):
        from application.coordinator import schedule_once
        from tests.application.test_product_coordinator import selection
        from tests.application.test_local_owner_composition import LocalOwnerCompositionTests
        for risk in (True,False):
            with self.subTest(risk=risk):
                fixture=LocalOwnerCompositionTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
                owners=fixture.configured()
                if not risk:
                    policy_path=fixture.root/'research.json'
                    policy=json.loads(policy_path.read_bytes())
                    policy['minimum_closed_trades']['sealed_oos']=100
                    policy_path.write_bytes(encoded(policy))
                with owners.inbox_factory() as inbox:self.assertEqual(1,inbox.scan_once(fixture.clock()).accepted)
                revision=owners.queue.selected_submission_revision('native-owner-fixture','selected-fixture')
                owners.queue.enqueue('native-owner-fixture','selected-fixture','candidate-auto-enqueue',revision,actor='fixture-owner')
                claim=owners.queue.claim_next();finished=owners.queue.step(claim.run_id,claim.generation)
                self.assertEqual('COMPLETE',finished['state'])
                self.assertEqual('CANDIDATE' if risk else 'BACKTESTING',finished['outcome']['strategy_lifecycle'])
                operations=selection(queue_reports=True)
                for _ in range(2):
                    scheduled=schedule_once(owners,owners.control_services(),operations)
                    self.assertEqual(1,scheduled['reports_queued'])
                    self.assertEqual(int(risk),scheduled['candidate_indexes_queued'])
                    self.assertEqual('NOT_COMMANDED',scheduled['paper'])
                with owners.queue.service_factory() as service:
                    self.assertEqual(1,len(service.journal.pending_feedback_publications(10)))
                    self.assertEqual(int(risk),len(service.journal.pending_candidate_index_publications(10)))

    def test_publish_cli_shares_one_requested_limit_across_feedback_and_candidate_outboxes(self):
        from application.cli import main
        from application.cloud.candidate_index import queue_candidate_index
        from application.cloud.feedback import queue_feedback
        fixture=self.bridge_fixture()
        with actual_candidate() as (root,service,result):
            from application.platform.private_files import create_private_directory
            work=root/'bridge-private';create_private_directory(work)
            fixture.payload['private_work_root']=str(work);fixture.write_settings()
            queue_feedback(service,result.run_id);queue_candidate_index(service,result.run_id)
            config=root/'product.json'
            config.write_bytes(canonical_bytes(dict(schema_version='r7-product-config-v0.2',
                product_instance_id='candidate-publish-cli-fixture',local_data_root=str(root),
                cloud_root=str(fixture.stage),database_path=str(root/'registry.sqlite'))))
            args=['cloud-publish-outbox','--config',str(config),'--bridge-profile',str(fixture.settings),'--limit','1']
            results=[]
            with patch('application.cloud.rclone_bridge.run_bounded',side_effect=fixture.fake):
                for _ in range(3):
                    output=StringIO()
                    with redirect_stdout(output):code=main(args)
                    self.assertEqual(0,code,output.getvalue())
                    results.append(json.loads(output.getvalue()))
            self.assertEqual([1,1,0],[item['attempted'] for item in results])
            self.assertEqual([1,1,0],[item['cloud_acknowledged'] for item in results])
            self.assertEqual((),service.journal.pending_feedback_publications(10))
            self.assertEqual((),service.journal.pending_candidate_index_publications(10))

    def test_one_index_refusal_does_not_pin_a_full_page_or_block_other_genuine_reports(self):
        from datetime import timedelta
        from application.coordinator import schedule_once
        from application.cloud import candidate_index
        from tests.application.test_product_coordinator import selection
        from tests.application.test_local_owner_composition import LocalOwnerCompositionTests
        from tests.application.cloud_fixtures import package
        from tests.validation.robustness_fixtures import subject
        from strategy import compute_content_hash
        from strategy.v02.capabilities import build_capability_snapshot
        fixture=LocalOwnerCompositionTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        tick=[fixture.clock()];fixture.clock=lambda:tick[0]
        fixture.configured()
        settings=json.loads(fixture.selection.read_bytes())
        settings['research_policies']['diagnostic-fixture']=dict(selection_mode='DIAGNOSTIC_DEVELOPMENT_ONLY',
            dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json',
            requested_dataset_profile='fixture-data',requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')
        fixture.selection.write_bytes(encoded(settings));owners=fixture.compose()
        capability=build_capability_snapshot().snapshot_hash
        submissions=['native-owner-fixture']
        for number in range(32):
            definition=subject();definition['strategy_id']='candidate-page-'+str(number)
            definition['content_hash']=compute_content_hash(definition)
            submission='candidate-page-'+str(number);submissions.append(submission)
            folder,manifest,_=package(fixture.cloud,submission=submission,version='0.2',definition=definition)
            manifest['capability_snapshot_hash']=capability;(folder/'manifest.json').write_bytes(encoded(manifest))
        with owners.inbox_factory() as inbox:self.assertEqual(33,inbox.scan_once(fixture.clock()).accepted)
        for number,submission in enumerate(submissions):
            policy='selected-fixture' if number==0 else 'diagnostic-fixture'
            revision=owners.queue.selected_submission_revision(submission,policy)
            owners.queue.enqueue(submission,policy,'page-enqueue-'+str(number),revision,actor='fixture-owner')
            claim=owners.queue.claim_next();finished=owners.queue.step(claim.run_id,claim.generation)
            self.assertEqual('COMPLETE',finished['state'])
            self.assertEqual('CANDIDATE' if number==0 else 'BACKTESTING',finished['outcome']['strategy_lifecycle'])
            tick[0]+=timedelta(seconds=1)
        jobs=owners.queue.list(limit=100);self.assertEqual(33,len(jobs))
        refused=jobs[0]['owner_run_id'];real_queue=candidate_index.queue_candidate_index
        def unavailable(service,run_id):
            if run_id==refused:raise candidate_index.CandidateIndexError('SYNTHETIC_INDEX_ONLY_REFUSAL')
            return real_queue(service,run_id)
        with patch.object(candidate_index,'queue_candidate_index',side_effect=unavailable):
            first=schedule_once(owners,owners.control_services(),selection(queue_reports=True))
            second=schedule_once(owners,owners.control_services(),selection(queue_reports=True),report_offset=first['next_report_offset'])
        self.assertEqual((32,32),(first['reports_queued'],first['next_report_offset']))
        self.assertEqual((1,0),(second['reports_queued'],second['next_report_offset']))
        self.assertEqual(0,first['candidate_indexes_queued'])
        self.assertEqual([dict(run_id=refused,operation='QUEUE_CANDIDATE_INDEX',reason_code='CandidateIndexError')],first['refusals'])
        with owners.queue.service_factory() as service:
            self.assertEqual(33,len(service.journal.pending_feedback_publications(100)))
            self.assertEqual((),service.journal.pending_candidate_index_publications(1))

    def test_actual_new_research_owner_backup_is_supported_without_losing_legacy_models(self):
        from tests.application.upgrade_preflight_complete_fixture import make_all_present_bundle
        from tests.application.upgrade_preflight_fixture import source_database_hashes,bundle_hashes
        from application.platform.upgrade_preflight import preflight_product_upgrade
        c=make_all_present_bundle(self)
        observed=preflight_product_upgrade(c.config,c.backup,config_path=c.config_path)
        self.assertEqual('COMPATIBLE_FOR_INHIBITED_CLONE',observed['status'])
        self.assertEqual('COMPATIBLE',observed['roles']['research']['status'])
        self.assertEqual(c.source_hashes,source_database_hashes(c.config))
        self.assertEqual(c.backup_hashes,bundle_hashes(c.backup))


if __name__=='__main__':unittest.main()
