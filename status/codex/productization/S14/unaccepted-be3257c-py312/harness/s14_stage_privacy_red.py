from pathlib import Path
import sys,unittest
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from tests.application.test_cloud_bridge import CloudBridgeTests
from application.cloud.bridge_transport import RcloneCloudTransport
from application.cloud.protocol import ArtifactBundle,CloudError
from application.cloud.manifest import canonical_bytes
class PrivacyBeforeStage(CloudBridgeTests):
    def test_private_fields_rejected_before_any_possible_synchronized_stage_write(self):
        path='reports/redaction/fixture/stage-guard'
        with self.assertRaises(CloudError):RcloneCloudTransport(self.bridge()).publish(
            ArtifactBundle(path,{'summary.json':canonical_bytes({'provider_account_id':'SYNTHETIC_PRIVATE'})}),'private-stage-probe')
        self.assertFalse((self.stage/path).exists(),'Rejected private bytes must never enter a possibly synchronized stage')
suite=unittest.TestSuite([PrivacyBeforeStage('test_private_fields_rejected_before_any_possible_synchronized_stage_write')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
