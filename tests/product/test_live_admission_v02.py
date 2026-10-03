"""Actual E6 owner graph plus explicitly synthetic E7 process facts; no provider."""
import importlib,json,unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from tests.registry import test_operational_lifecycle_v02 as lifecycle_fixtures
from tests.integration import test_runtime_preflight as preflight_fixtures
from registry import EvidenceGateError
from registry.operational_authority import stamp


class LiveAdmissionV02Tests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.helper=lifecycle_fixtures.OperationalLifecycleTests()
        self.owner,self.research,self.helper.run_id,self.identity,self.boundary,self.auth,self.clock,self.release,self.envelope=self.helper.fixture(self.root)
        self.addCleanup(self.research.close)
        self.e6=self.helper.platform(self.root,self.research,self.helper.run_id,self.boundary,'admission');self.addCleanup(self.e6.close)
        self.helper.build(self.e6,self.identity,'LIVE',self.auth)
        self.revision=self.e6.get_strategy(self.identity).registry_revision

    def factory(self):return self.helper.platform(self.root,self.research,self.helper.run_id,self.boundary,'admission')
    def api(self):
        try:return importlib.import_module('application.trading.admission')
        except ModuleNotFoundError:self.fail('Missing actual E6/E7 application admission composition')
    def permission(self,kind='NEW_EXPOSURE',revision=None):
        method=getattr(self.e6,'current_runtime_permission',None)
        self.assertTrue(callable(method),'Missing actual E6 current runtime permission read port')
        return method(self.identity,expected_revision=self.revision if revision is None else revision,permission=kind)

    def preflight(self):
        base=preflight_fixtures.RuntimePreflightV01Tests();base.setUp();release=self.release[0]
        base.revision=release.executable_revision;base.config_hash=release.config_hash;base.capability_hash=release.capability_hash
        base.authorization_capability_hash=release.capability_hash
        value=base._input(role='PAPER_RUNTIME');now=self.clock[0]
        authorization=dict(value.authorization_evidence,authorization_class='PERSISTENT_LIVE_RUNTIME',authorized_runtime_role='LIVE_RUNTIME')
        value=replace(value,runtime_preflight_profile_version='product-runtime-preflight-v0.2',runtime_role='LIVE_RUNTIME',requested_operational_mode='LIVE',
            evaluated_at=stamp(now),process_started_at=stamp(now-timedelta(seconds=3)),runtime_config_generation_id='config-generation:1',process_start_generation_id='runtime-generation:1',
            heartbeat_evidence=dict(value.heartbeat_evidence,heartbeat_process_start_generation_id='runtime-generation:1',heartbeat_observed_at=stamp(now-timedelta(seconds=2)),heartbeat_received_at=stamp(now-timedelta(seconds=1))),
            reconciliation_evidence=dict(value.reconciliation_evidence,reconciliation_observed_at=stamp(now-timedelta(seconds=1))),
            external_consumer_evidence=dict(value.external_consumer_evidence,compatibility_observed_at=stamp(now-timedelta(seconds=1))),authorization_evidence=authorization)
        authority=base._authority(value)
        authority=replace(authority,runtime_config_authority=dict(authority.runtime_config_authority,runtime_config_generation_id='config-generation:1'))
        return value,authority

    def test_public_permission_reads_actual_accepted_activation_and_exact_subject_without_minting_real_authority(self):
        proof=self.permission();self.assertEqual(self.identity,proof.identity);self.assertEqual(self.release[0],proof.release)
        self.assertEqual('SIMULATED_MECHANICS',proof.execution);self.assertEqual('NEW_EXPOSURE',proof.permission)
        self.assertEqual(self.revision,proof.registry_revision);self.assertTrue(proof.activation_evidence_id)
        self.assertTrue(proof.approval_record_id);self.assertEqual(self.envelope['strategy_content_hash'],proof.strategy_content_hash)
        from registry import ConcurrencyConflict
        with self.assertRaises(ConcurrencyConflict):self.permission(revision=self.revision-1)

    def test_exact_current_authority_snapshot_contains_original_envelope_and_selected_e5_policy(self):
        from registry.product_assessment import digest
        method = getattr(self.e6, 'current_runtime_authority', None)
        self.assertTrue(callable(method), 'Missing current envelope/policy owner read port')
        current = method(self.identity, expected_revision=self.revision, permission='NEW_EXPOSURE')
        self.assertEqual(self.permission(), current.permission)
        self.assertEqual(current.permission.approval_envelope_hash, digest(current.envelope_json))
        self.assertEqual(current.permission.release.risk_policy_hash, digest(current.risk_policy_json))
        self.assertEqual(self.envelope, json.loads(current.envelope_json))
        self.e6.revoke_approval(self.identity, authenticated_human=self.auth.authenticate('FIXTURE_AUTH_PROOF'),
                               reason='fixture', command_id='authority-revoke')
        with self.assertRaises(EvidenceGateError):
            method(self.identity, expected_revision=self.revision, permission='NEW_EXPOSURE')
        retained = method(self.identity, expected_revision=self.revision, permission='MANAGE_EXISTING')
        self.assertEqual(current.envelope_json, retained.envelope_json)

    def test_revocation_or_expiry_denies_new_exposure_but_retains_exact_existing_management_authority(self):
        self.permission()
        human=self.auth.authenticate('FIXTURE_AUTH_PROOF')
        self.e6.revoke_approval(self.identity,authenticated_human=human,reason='fixture-revoke',command_id='fixture-revoke')
        with self.assertRaises(EvidenceGateError):self.permission()
        management=self.permission('MANAGE_EXISTING');self.assertEqual('MANAGE_EXISTING',management.permission)
        self.clock[0]+=timedelta(hours=2)
        with self.assertRaises(EvidenceGateError):self.permission()
        self.assertEqual(management.approval_record_id,self.permission('MANAGE_EXISTING').approval_record_id)

    def test_fixture_permission_never_authorizes_production_and_opaque_verification_permit_rechecks_current_owners(self):
        api=self.api();admission=api.RuntimeAdmission(namespace='FIXTURE',registry_factory=self.factory,current_preflight=self.preflight,clock=lambda:self.clock[0],maximum_observation_age_seconds=5)
        denied=admission.evaluate(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='PRODUCTION')
        self.assertFalse(denied.allowed);self.assertIn('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',denied.reason_codes)
        permit=admission.issue(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        self.assertNotIn('nonce',repr(permit));admission.require(permit,identity=self.identity,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        with self.assertRaises(api.RuntimeAdmissionError):admission.require({'allowed':True},identity=self.identity,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        with self.assertRaises(api.RuntimeAdmissionError):admission.require(permit,identity=self.identity,permission='NEW_EXPOSURE',execution='PRODUCTION')
        self.e6.revoke_approval(self.identity,authenticated_human=self.auth.authenticate('FIXTURE_AUTH_PROOF'),reason='fixture',command_id='revoke-after-issue')
        with self.assertRaises(api.RuntimeAdmissionError):admission.require(permit,identity=self.identity,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')

    def test_current_release_and_process_generations_cannot_be_replaced_by_stored_audit_or_new_timestamp(self):
        api=self.api();admission=api.RuntimeAdmission(namespace='FIXTURE',registry_factory=self.factory,current_preflight=self.preflight,clock=lambda:self.clock[0],maximum_observation_age_seconds=5)
        self.assertTrue(admission.evaluate(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION').allowed)
        permit=admission.issue(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        value,authority=self.preflight()
        other_process=replace(value,process_instance_id='other-current-process',heartbeat_evidence=dict(value.heartbeat_evidence,heartbeat_process_instance_id='other-current-process'))
        admission.current_preflight=lambda:(other_process,authority)
        with self.assertRaises(api.RuntimeAdmissionError):admission.require(permit,identity=self.identity,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        admission.current_preflight=lambda:(replace(value,process_start_generation_id='prior-boot'),authority)
        self.assertFalse(admission.evaluate(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION').allowed)
        self.release[0]=replace(self.release[0],config_generation=2)
        with self.assertRaises(EvidenceGateError):self.permission()

    def test_permit_cannot_expire_during_actual_owner_read_and_still_be_returned(self):
        from unittest.mock import patch
        api=self.api()
        admission=api.RuntimeAdmission(namespace='FIXTURE',registry_factory=self.factory,current_preflight=self.preflight,
            clock=lambda:self.clock[0],maximum_observation_age_seconds=5)
        permit=admission.issue(self.identity,expected_revision=self.revision,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')
        original=admission.evaluate
        def slow(*args,**kwargs):
            result=original(*args,**kwargs);self.clock[0]+=timedelta(seconds=2);return result
        with patch.object(admission,'evaluate',side_effect=slow),self.assertRaises(api.RuntimeAdmissionError):
            admission.require(permit,identity=self.identity,permission='NEW_EXPOSURE',execution='FAKE_PROVIDER_VERIFICATION')


if __name__=='__main__':unittest.main()
