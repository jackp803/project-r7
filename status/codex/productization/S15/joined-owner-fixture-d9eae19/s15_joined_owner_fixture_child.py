"""Fixed suite; false-ACK sensitivity mutation exists in this child only."""
from dataclasses import replace
import sys,unittest
from unittest.mock import patch
from s15_joined_owner_acceptance_cases import JoinedOwnerAcceptanceTests
mode=sys.argv[1]
assert mode in ('NORMAL','MUTATION_CONTROL')
suite=unittest.defaultTestLoader.loadTestsFromTestCase(JoinedOwnerAcceptanceTests);assert suite.countTestCases()==3
if mode=='MUTATION_CONTROL':
    from application.cloud.bridge_transport import RcloneCloudTransport
    def false_ack(self,bundle,operation_id):
        return replace(self.bridge.stage.publish(bundle,operation_id),status='CLOUD_ACKNOWLEDGED')
    with patch.object(RcloneCloudTransport,'publish',false_ack):result=unittest.TextTestRunner(verbosity=2).run(suite)
else:result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
