"""Versioned publication dispatch; schema-only legacy fixture has no executed-stage claim."""
import copy,importlib,json,unittest
from tests.product import test_paper_runtime_v02 as fixtures

class PublicFeedbackDispatchTests(unittest.TestCase):
    def setUp(self):self.module=importlib.import_module('application.cloud.public_feedback')
    def legacy(self):
        from application.cloud.feedback import feedback_bundle
        stage=dict(status='NOT_RUN',sample_count=None,trial_count=None,reason_codes=[],performance=None)
        value=dict(schema_version='r7-chat-feedback-v0.2',run_id='fixture-schema-only',namespace='FIXTURE',
            strategy=dict(strategy_id='paper',strategy_version='0.2.0',content_hash='sha256:'+'a'*64,runtime_family='DSL',runtime_version='0.2.0'),
            source=dict(executable_revision=None,implementation_hash='sha256:'+'b'*64,execution='LOCAL',worktree='UNAVAILABLE'),
            dataset=dict(dataset_id='fixture-data',dataset_version='1',manifest_hash='sha256:'+'c'*64),
            split=dict(policy_hash='sha256:'+'d'*64,training={'start':'2026-01-01T00:00:00Z','end':'2026-02-01T00:00:00Z'},
                development={'start':'2026-02-01T00:00:00Z','end':'2026-03-01T00:00:00Z'},sealed_oos={'start':'2026-03-01T00:00:00Z','end':'2026-04-01T00:00:00Z'}),
            created_at='2026-04-01T00:00:00Z',reason_codes=[],training=copy.deepcopy(stage),development=copy.deepcopy(stage),
            robustness=copy.deepcopy(stage),sealed_oos=copy.deepcopy(stage),paper={'status':'NOT_RUN','observation_seconds':None,'sample_count':None},
            live={'status':'NOT_RUN','performance':None},performance_policy='OPT_OUT',holdout_observed=False,artifact_links=[],
            uncertainty=['Historical research does not establish forward performance or financial authority.',
                'Trial counts and closed-trade counts are not independent observations.'])
        return feedback_bundle(value)
    def test_legacy_strategy_named_paper_remains_valid_research_feedback(self):
        bundle=self.legacy();self.module.validate_public_feedback_publication(bundle.logical_path,dict(bundle.payloads))
    def test_actual_owner_paper_bundle_uses_its_strict_schema(self):
        from application.cloud.paper_feedback import build_paper_feedback,paper_feedback_bundle
        case=fixtures.PaperRuntimeV02Tests();case.setUp();self.addCleanup(case.doCleanups)
        bundle=paper_feedback_bundle(build_paper_feedback(case.start()))
        self.module.validate_public_feedback_publication(bundle.logical_path,dict(bundle.payloads))
        with self.assertRaises(ValueError):self.module.validate_public_feedback_publication(bundle.logical_path+'-changed',dict(bundle.payloads))
    def test_changed_media_private_fields_and_unknown_schema_never_reach_public_staging(self):
        bundle=self.legacy()
        for field,value in (('provider_order_id','SYNTHETIC_FORBIDDEN'),('schema_version','UNSUPPORTED')):
            payloads=dict(bundle.payloads);document=json.loads(payloads['feedback.json']);document[field]=value
            from application.cloud.manifest import canonical_bytes
            payloads['feedback.json']=canonical_bytes(document)
            with self.assertRaises(ValueError):self.module.validate_public_feedback_publication(bundle.logical_path,payloads)
        media=dict(bundle.payloads);media['report.html']+=b'<script>untrusted()</script>'
        with self.assertRaises(ValueError):self.module.validate_public_feedback_publication(bundle.logical_path,media)

if __name__=='__main__':unittest.main()
