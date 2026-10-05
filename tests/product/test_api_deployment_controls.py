"""Actual E6 deployment stop/recovery mechanics; isolated FIXTURE only."""
from datetime import timedelta
import importlib
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from application.control_api.app import create_app
from application.control_api.owner_services import OwnerControlServices
from registry import EvidenceGateError, InvalidTransition
import tests.product.test_api_approval_preview as fixtures


class APIDeploymentControlTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.APIApprovalPreviewTests(methodName='runTest')
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        h=self.fixture;h.login()
        h.post('/api/v1/auth/reauthenticate',dict(command_id='reauth',expected_revision=1,password=h.password))
        self.human=h.app.state.authenticator.authenticate(h.auth.current_reauthentication(h.client.cookies.get('r7_session')))
        with h.port.factory(h.app.state.authenticator) as e6:
            e6.record_approval(h.identity,envelope_ref='fixture-envelope',authenticated_human=self.human,decision='APPROVE',
                reason='SIMULATED_OWNER_MECHANICS',command_id='fixture-owner-consent',expected_revision=h.before.registry_revision)
            current=e6.get_strategy(h.identity)
            self.before=e6.activate_deployment(h.identity,evidence_ref='fixture-admission',authenticated_human=self.human,
                command_id='fixture-owner-activation',expected_revision=current.registry_revision)

    def control(self):
        h=self.fixture
        try:module=importlib.import_module('application.control_api.deployment_port')
        except ModuleNotFoundError:self.fail('Actual deployment control port is missing')
        port=module.DeploymentControlPort(namespace='FIXTURE',registry_factory=h.port.factory)
        owners=OwnerControlServices(h.config,namespace='FIXTURE',clock=lambda:h.clock[0],registry_factory=h.factory,deployment=port)
        h.client.close();h.app=create_app(h.config,auth=h.auth,commands=h.ledger,services=owners)
        h.client=TestClient(h.app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000),raise_server_exceptions=False)
        h.addCleanup(h.client.close);h.login(command_id='login-control')
        h.post('/api/v1/auth/reauthenticate',dict(command_id='reauth-control',expected_revision=1,password=h.password))
        with port.factory(h.app.state.authenticator) as e6:subject=e6.deployment_control_subject(h.identity)
        return subject,port

    def body(self,command='pause-one'):
        h=self.fixture
        return dict(command_id=command,expected_revision=self.before.registry_revision,
            strategy_id=h.identity.strategy_id,strategy_version=h.identity.strategy_version)

    def test_authenticated_pause_disables_new_exposure_and_retains_original_management(self):
        subject,_=self.control();h=self.fixture
        view=h.client.get(f'/api/v1/strategies/{h.identity.strategy_id}/{h.identity.strategy_version}')
        self.assertEqual(200,view.status_code,view.text)
        self.assertEqual(subject.deployment_id,view.json()['data']['payload']['deployment']['deployment_id'])
        response=h.post('/api/v1/deployments/'+subject.deployment_id+'/pause',self.body())
        self.assertEqual(200,response.status_code,response.text);self.assertEqual('PAUSED',response.json()['status'])
        with h.factory() as e6:
            current=e6.get_strategy(h.identity);self.assertEqual('DEGRADED',current.current_lifecycle_state)
            retained=e6.current_runtime_permission(h.identity,expected_revision=current.registry_revision,permission='MANAGE_EXISTING')
            self.assertEqual(subject.approval_record_id,retained.approval_record_id)
            with self.assertRaises(InvalidTransition):e6.current_runtime_permission(h.identity,expected_revision=current.registry_revision,permission='NEW_EXPOSURE')
        self.assertEqual(response.json(),h.post('/api/v1/deployments/'+subject.deployment_id+'/pause',self.body()).json())

    def test_lost_api_receipt_reconciles_owner_pause_without_another_transition(self):
        subject,_=self.control();h=self.fixture;path='/api/v1/deployments/'+subject.deployment_id+'/pause'
        with patch.object(h.ledger,'complete',side_effect=OSError('fixture receipt loss')):
            self.assertEqual(500,h.post(path,self.body()).status_code)
        h.clock[0]+=timedelta(seconds=31)
        result=h.post(path,self.body());self.assertEqual(200,result.status_code,result.text)
        self.assertEqual(self.before.registry_revision+1,result.json()['resource_revision'])
        with h.factory() as e6:self.assertEqual(self.before.registry_revision+1,e6.get_strategy(h.identity).registry_revision)

    def test_wrong_deployment_identity_cannot_pause_and_fixture_activation_stays_denied(self):
        subject,_=self.control();h=self.fixture
        wrong=h.post('/api/v1/deployments/wrong/pause',self.body())
        self.assertEqual(409,wrong.status_code,wrong.text)
        h.post('/api/v1/auth/reauthenticate',dict(command_id='reauth-next',expected_revision=2,password=h.password))
        activate=h.post('/api/v1/deployments/'+subject.deployment_id+'/activate',dict(self.body('forbidden-activate'),evidence_ref='fixture-admission'))
        self.assertEqual(403,activate.status_code)
        with h.factory() as e6:self.assertEqual(self.before,e6.get_strategy(h.identity))

    def test_actual_owner_resume_retry_uses_original_operation_after_lifecycle_advances(self):
        self.control();h=self.fixture
        human=h.app.state.authenticator.authenticate(h.auth.current_reauthentication(h.client.cookies.get('r7_session')))
        with h.factory() as e6:
            paused=e6.degrade(h.identity,actor='local-owner',reason_codes=('USER_ENTRY_PAUSE',),command_id='owner-pause',expected_revision=self.before.registry_revision)
            result=e6.activate_selected_deployment(h.identity,evidence_ref='fixture-admission',authenticated_human=human,
                command_id='owner-resume',expected_revision=paused.registry_revision)
            self.assertEqual('LIVE',result.current_lifecycle_state)
            self.assertEqual(result,e6.activate_selected_deployment(h.identity,evidence_ref='fixture-admission',authenticated_human=human,
                command_id='owner-resume',expected_revision=paused.registry_revision))
            with self.assertRaises(EvidenceGateError):e6.activate_selected_deployment(h.identity,evidence_ref='other',authenticated_human=human,
                command_id='owner-resume',expected_revision=paused.registry_revision)


if __name__=='__main__':unittest.main()
