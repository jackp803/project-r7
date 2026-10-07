import importlib,json,unittest
from pathlib import Path
from application.cloud.manifest import canonical_bytes
from application.cloud.protocol import ArtifactBundle,CloudError
from application.cloud.bridge_transport import RcloneCloudTransport
from tests.application import test_cloud_bridge as bridge_fixtures
from tests.product import test_paper_runtime_v02 as fixtures

class PaperFeedbackBridgeTests(unittest.TestCase):
    def setUp(self):
        self.owner=fixtures.PaperRuntimeV02Tests();self.owner.setUp();self.addCleanup(self.owner.doCleanups)
        self.cloud=bridge_fixtures.CloudBridgeTests();self.cloud.setUp();self.addCleanup(self.cloud.doCleanups)
        from storage._sqlite_registry import _apply_migrations
        _apply_migrations(self.owner.process._db)
        from storage.paper_feedback import PaperFeedbackOutbox
        self.outbox=PaperFeedbackOutbox(self.owner.process);self.runtime=self.owner.start()
        self.operation=self.outbox.queue(self.runtime);self.bridge=self.cloud.bridge();self.transport=RcloneCloudTransport(self.bridge)
    def test_actual_owner_paper_outbox_reaches_exact_remote_byte_ack_through_local_fake_only(self):
        result=self.outbox.flush(self.transport,limit=10)
        self.assertEqual(result.cloud_acknowledged,1);self.assertEqual(result.local_staged,0)
        self.assertEqual(self.outbox.publications()[0]['state'],'CLOUD_ACKNOWLEDGED')
        self.assertEqual(self.outbox.flush(self.transport,limit=10).attempted,0)
        self.assertTrue(any(path.name=='feedback.json' for path in self.cloud.remote.rglob('*')))
    def test_offline_copy_failure_preserves_unacknowledged_outbox_then_retries_same_content(self):
        self.cloud.fake.outage=True
        self.assertEqual(self.outbox.flush(self.transport,limit=10).unavailable,1)
        self.assertEqual(self.outbox.publications()[0]['state'],'UNAVAILABLE')
        self.cloud.fake.outage=False
        self.assertEqual(self.outbox.flush(self.transport,limit=10).cloud_acknowledged,1)
        self.assertEqual([row['operation_id'] for row in self.outbox.publications()],[self.operation])
    def test_private_or_changed_paper_media_is_refused_before_any_stage_write(self):
        operation,bundle,commitment=self.outbox.pending(1)[0]
        before={path.relative_to(self.cloud.stage).as_posix():path.read_bytes() for path in self.cloud.stage.rglob('*') if path.is_file()}
        raw=json.loads(bundle.payloads['feedback.json']);raw['provider_order_id']='SYNTHETIC_FORBIDDEN'
        payloads=dict(bundle.payloads);payloads['feedback.json']=canonical_bytes(raw)
        with self.assertRaises(CloudError):self.transport.publish(ArtifactBundle(bundle.logical_path,payloads),operation)
        payloads=dict(bundle.payloads);payloads['report.html']+=b'<script>forbidden()</script>'
        with self.assertRaises(CloudError):self.transport.publish(ArtifactBundle(bundle.logical_path,payloads),operation)
        after={path.relative_to(self.cloud.stage).as_posix():path.read_bytes() for path in self.cloud.stage.rglob('*') if path.is_file()}
        self.assertEqual(after,before)

if __name__=='__main__':unittest.main()
