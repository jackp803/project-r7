import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.control_api.auth import LocalAuth
from registry.operational_authority import HumanAuthenticator
from registry import EvidenceGateError
from tests.registry import test_operational_lifecycle_v02 as fixtures


class APIApprovalBindingTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.control_api.approval_port'),
                             'Exact-subject authenticated approval adapter is missing')
        self.temp=TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.helper=fixtures.OperationalLifecycleTests()
        api,research,run_id,self.identity,self.boundary,old_auth,self.clock,self.release,self.envelope=self.helper.fixture(self.root)
        self.addCleanup(research.close); self.helper.run_id=run_id
        self.e6=self.helper.platform(self.root,research,run_id,self.boundary,'approval-api'); self.addCleanup(self.e6.close)
        self.helper.build(self.e6,self.identity,'READY_FOR_APPROVAL',old_auth)
        self.local=LocalAuth(self.root/'auth.sqlite',namespace='FIXTURE',clock=lambda:self.clock[0]); self.password='explicit-test-only-password-123'
        self.local.create_owner('local-owner',self.password)
        self.grant=self.local.login('local-owner',self.password,command_id='login-one',expected_revision=0)
        self.issuer=HumanAuthenticator(namespace='FIXTURE',verifier=self.local.verify_reauthentication,current_verifier=self.local.verify_reauthentication,
            reauth_seconds=300,clock=lambda:self.clock[0])
        self.boundary.authenticator=self.issuer
        self.human=self.issuer.authenticate(self.local.reauthenticate(self.grant.token,self.password,expected_revision=1))

    def test_actual_e6_approval_actor_is_verified_local_session_identity(self):
        before=self.e6.get_strategy(self.identity)
        after=self.e6.record_approval(self.identity,envelope_ref='fixture-envelope',authenticated_human=self.human,decision='APPROVE',
            reason='USER_CONFIRMED',command_id='local-approval',expected_revision=before.registry_revision)
        self.assertEqual(after.current_lifecycle_state,'APPROVED')
        stored=self.e6.human_approval_for_command('local-approval')
        self.assertEqual(stored.actor,'local-owner')
        self.assertEqual(stored.identity,self.identity)
        self.assertNotIn(self.password,stored.payload_json)
        self.assertEqual(stored.namespace,'FIXTURE')

    def test_logout_revokes_actual_e6_capability_before_any_owner_approval_effect(self):
        before=self.e6.get_strategy(self.identity)
        self.local.logout(self.grant.token,expected_revision=2)
        with self.assertRaises(EvidenceGateError):
            self.e6.record_approval(self.identity,envelope_ref='fixture-envelope',authenticated_human=self.human,decision='APPROVE',
                reason='USER_CONFIRMED',command_id='revoked-approval',expected_revision=before.registry_revision)
        self.assertEqual(self.e6.get_strategy(self.identity),before)

    def test_approval_adapter_also_denies_fixture_financial_authority(self):
        from application.control_api.approval_port import ApprovalControlPort
        from application.control_api.errors import APIError
        port=ApprovalControlPort(namespace='FIXTURE',registry_factory=lambda issuer:self.e6)
        port.install_authenticator(self.issuer)
        with self.assertRaises(APIError) as error:
            port.record({},actor='local-owner',human=self.human,command_id='forbidden',expected_revision=0)
        self.assertEqual(error.exception.reason,'FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN')


if __name__=='__main__': unittest.main()
