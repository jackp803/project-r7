"""One genuine candidate -> owner index -> local roundtrip.
No metric payload, caller PASS, fabricated financial row or remote ACK.
"""
import hashlib
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.cloud.feedback import build_research_feedback,feedback_bundle
from application.cloud.manifest import canonical_bytes,byte_hash
from application.cloud.safe_files import read_bounded
from application.cloud.synced_folder import SyncedFolderCloudTransport
from storage.platform import open_sqlite_platform
from tests.application import test_product_assessment_binding as fixtures
from tests.application.dataset_fixtures import encoded
from tests.application.test_research_robustness import selected


def _payload_hash(record):
    return 'sha256:'+hashlib.sha256(record.payload_json.encode('utf-8')).hexdigest()


class CandidateIndexRoundtripV02Tests(unittest.TestCase):
    def test_actual_candidate_index_publishes_exact_owner_refs_without_feedback_contract_or_oos_change(self):
        helper=fixtures.ProductAssessmentBindingTests()
        with TemporaryDirectory() as temporary,TemporaryDirectory() as cloud:
            root=Path(temporary);selected(root)
            (root/'risk.json').write_bytes(encoded(fixtures.risk_fixture()))
            with helper.service(root) as service:
                outcome=helper.execute(service)
                self.assertEqual('CANDIDATE',outcome.strategy_lifecycle)
                report=service.report(outcome.run_id)
                self.assertEqual('PASS',report['candidate_gate']['status'])
                with open_sqlite_platform(root/'registry.sqlite',research_namespace='FIXTURE') as e6:
                    assessment=e6.product_assessment(outcome.run_id)
                    strategy=e6.get_strategy(assessment.identity)
                    self.assertEqual(assessment,e6.candidate_product_assessment(assessment.identity))
                    development=e6._store.get_validation_evidence(report['backtest_e6_evidence_id'])
                    validation=e6._store.get_validation_evidence(assessment.validation_evidence_id)
                    sealed=e6._store.get_validation_evidence(validation.parent_evidence_id)
                self.assertEqual('PASS',assessment.status)
                before_report=service.report(outcome.run_id)
                existing_feedback=build_research_feedback(service,outcome.run_id)
                self.assertEqual([],existing_feedback['artifact_links'])
                self.assertEqual({'feedback.json','report.html'},set(feedback_bundle(existing_feedback).payloads))
                # Corrected draft: existing feedback already reserves its own
                # idempotent CHAT_OBSERVATION; snapshot AFTER that existing call.
                observed={row['observation_id']:dict(row) for row in service.ledger._db.execute(
                    'SELECT * FROM research_holdout_observations ORDER BY observation_id').fetchall()}
                # Missing new seam RED is deliberately AFTER real E2/E3/E6
                # candidate, independent final OOS, original feedback and IDs.
                module=importlib.import_module('application.cloud.candidate_index')
                operation=module.queue_candidate_index(service,outcome.run_id)
                rows=service.journal.pending_candidate_index_publications(2)
                self.assertEqual(1,len(rows));op,bundle,artifact_hash=rows[0]
                self.assertEqual(operation,op)
                self.assertTrue(bundle.logical_path.startswith('candidates/'+assessment.identity.strategy_id+'/'+assessment.identity.strategy_version+'/'))
                self.assertEqual({'candidate_manifest.json','evidence_index.json','report.html'},set(bundle.payloads))
                index=json.loads(bundle.payloads['evidence_index.json'])
                published={row['observation_id']:dict(row) for row in service.ledger._db.execute(
                    'SELECT * FROM research_holdout_observations ORDER BY observation_id').fetchall()}
                self.assertEqual(observed,{key:published[key] for key in observed})
                added=[row for key,row in published.items() if key not in observed]
                self.assertEqual(1,len(added))
                self.assertEqual('CHAT_OBSERVATION',added[0]['kind'])
                self.assertEqual(byte_hash(bundle.payloads['evidence_index.json']),added[0]['reference_hash'])
                self.assertEqual(report['frozen_finalist']['family_id'],added[0]['family_id'])
                period=report['frozen_finalist']['policies']['split']['sealed_oos']
                from application.cloud.manifest import utc
                self.assertEqual((utc(period['start']),utc(period['end'])),
                    (utc(added[0]['start_at']),utc(added[0]['end_at'])))
                self.assertEqual('r7-candidate-evidence-index-v0.2',index['schema_version'])
                self.assertEqual(outcome.run_id,index['run_id'])
                self.assertEqual(strategy.content_hash,index['strategy']['content_hash'])
                inputs,input_hash=service.ledger._run(outcome.run_id)
                self.assertEqual(input_hash,index['input_hash'])
                self.assertEqual(inputs['dataset_manifest_hash'],index['dataset']['manifest_hash'])
                self.assertEqual(inputs['split_policy_hash'],index['split_policy_hash'])
                self.assertEqual(inputs['cost_policy_hash'],index['policy_hashes']['cost'])
                self.assertEqual(assessment.implementation_hash,index['source']['implementation_hash'])
                self.assertEqual('NONE',index['financial_authority'])
                expected={
                    'development_backtest':(development.evidence_id,_payload_hash(development)),
                    'sealed_backtest':(sealed.evidence_id,_payload_hash(sealed)),
                    'oos_validation':(validation.evidence_id,_payload_hash(validation)),
                    'product_assessment':(assessment.assessment_id,assessment.payload_hash),
                }
                self.assertEqual(expected,{item['role']:(item['evidence_id'],item['payload_hash']) for item in index['evidence']})
                public=b''.join(bundle.payloads.values()).decode('utf-8')
                for private in (str(root),'net_pnl','gross_pnl','total_fees','funding_cost','raw_response'):
                    self.assertNotIn(private,public)
                stage=Path(cloud);(stage/'.r7-root.json').write_bytes(canonical_bytes({'root_id':'candidate-fixture-root'}))
                transport=SyncedFolderCloudTransport(stage,expected_root_id='candidate-fixture-root')
                summary=module.flush_candidate_indexes(service.journal,transport,limit=1)
                self.assertEqual((1,1,0),(summary.attempted,summary.local_staged,summary.cloud_acknowledged))
                for name,raw in bundle.payloads.items():
                    self.assertEqual(raw,read_bounded(stage,bundle.logical_path+'/'+name,256*1024))
                manifest=json.loads(read_bounded(stage,bundle.logical_path+'/manifest.json',65536))
                self.assertEqual(operation,manifest['operation_id'])
                self.assertEqual({name:byte_hash(raw) for name,raw in bundle.payloads.items()},manifest['payload_hashes'])
                self.assertEqual(artifact_hash,manifest['artifact_hash'])
                self.assertEqual(operation,module.queue_candidate_index(service,outcome.run_id))
                self.assertEqual(1,len(service.journal.pending_candidate_index_publications(2)))
                self.assertEqual(before_report,service.report(outcome.run_id))
                self.assertEqual(published,{row['observation_id']:dict(row) for row in service.ledger._db.execute(
                    'SELECT * FROM research_holdout_observations ORDER BY observation_id').fetchall()})
                with helper.service(root) as restarted:
                    self.assertEqual(operation,module.queue_candidate_index(restarted,outcome.run_id))
                    self.assertEqual(published,{row['observation_id']:dict(row) for row in restarted.ledger._db.execute(
                        'SELECT * FROM research_holdout_observations ORDER BY observation_id').fetchall()})
                self.assertEqual(existing_feedback,build_research_feedback(service,outcome.run_id))
                with open_sqlite_platform(root/'registry.sqlite',research_namespace='FIXTURE') as e6:
                    self.assertEqual(assessment,e6.product_assessment(outcome.run_id))
                    self.assertEqual(strategy,e6.get_strategy(assessment.identity))
