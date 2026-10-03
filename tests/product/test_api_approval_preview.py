"""Readonly exact E6 proposal views through actual authenticated HTTP owners."""
from contextlib import contextmanager
import json
import unittest
from fastapi.testclient import TestClient
from application.control_api.app import create_app
from application.control_api.owner_services import OwnerControlServices
from application.control_api.approval_port import ApprovalControlPort
from registry.product_assessment import digest
import tests.product.test_api_authority as api_fixtures
import tests.registry.test_operational_lifecycle_v02 as owner_fixtures


class APIApprovalPreviewTests(api_fixtures.APIFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.helper=owner_fixtures.OperationalLifecycleTests(methodName='runTest')
        _,self.research,run_id,self.identity,self.boundary,old_auth,self.clock,self.release,self.envelope=self.helper.fixture(self.root)
        self.addCleanup(self.research.close);self.helper.run_id=run_id
        self.factory=lambda:self.helper.platform(self.root,self.research,run_id,self.boundary,'approval-view')
        with self.factory() as e6:
            self.helper.build(e6,self.identity,'READY_FOR_APPROVAL',old_auth)
            self.before=e6.get_strategy(self.identity)
        @contextmanager
        def approval_factory(issuer):
            self.boundary.authenticator=issuer
            with self.factory() as e6: yield e6
        self.port=ApprovalControlPort(namespace='FIXTURE',registry_factory=approval_factory)
        owners=OwnerControlServices(self.config,namespace='FIXTURE',clock=lambda:self.clock[0],
            registry_factory=self.factory,approval=self.port)
        self.client.close()
        self.app=create_app(self.config,auth=self.auth,commands=self.ledger,services=owners)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',42000),raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.path=f'/api/v1/strategies/{self.identity.strategy_id}/{self.identity.strategy_version}/approval-preview'

    def preview(self, **changes):
        arguments=dict(envelope_ref='fixture-envelope',expected_revision=self.before.registry_revision)
        arguments.update(changes)
        return self.client.get(self.path,params=arguments)

    def test_actual_registered_subject_limits_and_evidence_are_readonly_and_fixture_never_financial(self):
        self.assertEqual(401,self.preview().status_code)
        self.login()
        response=self.preview();self.assertEqual(200,response.status_code,response.text)
        view=response.json()['data']
        self.assertEqual(self.before.content_hash,view['strategy_content_hash'])
        self.assertEqual(self.before.registry_revision,view['registry_revision'])
        self.assertEqual(self.envelope,view['envelope'])
        self.assertEqual(self.release[0].as_dict(),view['release'])
        from registry.product_assessment import canonical
        self.assertEqual(digest(canonical(self.envelope)),view['envelope_hash'])
        self.assertEqual(self.release[0].risk_policy_hash,view['risk_policy_hash'])
        self.assertGreater(view['product_assessment']['sealed_backtest']['total_trades'],0)
        self.assertFalse(view['financial_confirmation_available'])
        self.assertIn('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',view['reason_codes'])
        self.assertNotIn(self.password,response.text)
        with self.factory() as e6: self.assertEqual(self.before,e6.get_strategy(self.identity))

    def test_stale_subject_or_wrong_envelope_or_release_drift_produces_typed_denial(self):
        self.login()
        self.assertEqual(409,self.preview(expected_revision=self.before.registry_revision-1).status_code)
        wrong=self.preview(envelope_ref='unregistered')
        self.assertEqual(409,wrong.status_code,wrong.text)
        from dataclasses import replace
        self.release[0]=replace(self.release[0],config_generation=2)
        changed=self.preview();self.assertEqual(409,changed.status_code,changed.text)
        self.assertNotIn('Traceback',changed.text)

    def test_query_rejects_untrusted_payload_unknown_keys_and_bad_bounds(self):
        self.login()
        for values in (dict(status='PASS'),dict(actor='ProductOwner'),dict(expected_revision=-1),
                       dict(expected_revision='true'),dict(envelope_ref='../../outside')):
            with self.subTest(values=values):self.assertEqual(422,self.preview(**values).status_code)

    def test_reading_or_reauthenticating_preview_never_allows_fixture_approval(self):
        self.login();self.assertEqual(200,self.preview().status_code)
        self.assertEqual(200,self.post('/api/v1/auth/reauthenticate',dict(command_id='reauth',expected_revision=1,password=self.password)).status_code)
        response=self.post('/api/v1/approvals',dict(command_id='never-financial',expected_revision=self.before.registry_revision,
            strategy_id=self.identity.strategy_id,strategy_version=self.identity.strategy_version,envelope_ref='fixture-envelope',
            decision='APPROVE',reason_code='USER_CONFIRMED',expected_strategy_hash=self.before.content_hash,
            expected_envelope_hash=digest(json.dumps(self.envelope))))
        self.assertEqual(403,response.status_code)
        with self.factory() as e6:self.assertEqual(self.before,e6.get_strategy(self.identity))


if __name__=='__main__':unittest.main()
