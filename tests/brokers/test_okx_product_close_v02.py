import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import tests.brokers.test_okx_close_sizing as fixtures
import tests.brokers.test_okx_close_sizing_binding as bindings
from brokers.okx_close_sizing import (
    evaluate_okx_close_residual_sizing as legacy_evaluate,
    validate_okx_close_residual_sizing_evidence as legacy_validate,
    OKXCloseSizingError,
)
from brokers.okx_demo import OKXAccountConfigSnapshot


class OKXProductCloseV02Tests(unittest.TestCase):
    def setUp(self):
        from brokers.okx_product_capability import OKXProductCapabilityOwner
        self.owner = OKXProductCapabilityOwner()
        self.fixture = fixtures.OKXCloseResidualSizingTests(methodName='runTest')
        self.fixture.setUp()
        self.binding_fixture = bindings.OKXCloseSizingMetadataBindingTests(methodName='runTest')
        self.binding_fixture.setUp()
        self.account = OKXAccountConfigSnapshot('2', 'net_mode', '123', '123')

    def prepared(self, value=None, role='POSITION_EXIT', account=None):
        value = self.fixture.sizing_input() if value is None else value
        value = replace(value, instrument_metadata=replace(value.instrument_metadata, observed_at=value.evaluated_at))
        proof = self.owner.issue(role, self.account if account is None else account,
                                 value.instrument_metadata, observed_at=value.evaluated_at,
                                 now=value.evaluated_at)
        capability = self.owner.close_capability(proof, value.instrument_metadata, now=value.evaluated_at)
        return replace(value, capability=capability), proof

    def evaluate(self, value, proof, **kwargs):
        return self.owner.evaluate_close(value, self.binding_fixture.binding(value), proof,
                                         now=value.evaluated_at, **kwargs)

    def test_both_close_roles_use_shared_math_and_distinct_profile(self):
        for emergency in (False, True):
            position = self.fixture.position(lifecycle='EMERGENCY' if emergency else 'OPEN_PROTECTED')
            action = self.fixture.action(emergency=emergency)
            role = 'EMERGENCY_EXIT' if emergency else 'POSITION_EXIT'
            value, proof = self.prepared(self.fixture.sizing_input(source_position=position, action=action), role)
            result = self.evaluate(value, proof)
            self.assertEqual('FULLY_REDUCIBLE', result['sizing_state'])
            self.assertEqual('12', result['quantized_provider_close_size'])
            self.assertEqual('okx-product-close-residual-sizing-v0.2', result['close_residual_sizing_profile_version'])
            self.assertEqual('okx-product-action-role-capability-v0.2', result['fp02_capability_profile_version'])
            with self.assertRaises(OKXCloseSizingError):
                legacy_validate(result)
            self.assertEqual('CLOSE_CAPABILITY_UNPROVEN', legacy_evaluate(value)['sizing_state'])

    def test_partial_cap_and_dust_keep_existing_fail_closed_semantics(self):
        value, proof = self.prepared(self.fixture.sizing_input(applicability=self.fixture.applicability(close_max='10')))
        self.assertEqual('10', self.evaluate(value, proof)['quantized_provider_close_size'])
        value, proof = self.prepared(self.fixture.sizing_input(
            source_position=self.fixture.position(quantity='0.00005'),
            action=self.fixture.action(quantity='0.00005'),
            provider=self.fixture.provider(contracts='0.5', canonical='0.00005')))
        result = self.evaluate(value, proof)
        self.assertEqual('RESIDUAL_NONZERO_UNREPRESENTABLE', result['sizing_state'])
        self.assertIsNone(result['quantized_provider_close_size'])

    def test_ambiguous_and_external_truth_never_return_a_request_size(self):
        for options in ({'prior_status': 'AMBIGUOUS'}, {'external_fp04': True}, {'registry_status': 'STALE'}):
            value, proof = self.prepared(self.fixture.sizing_input(**options))
            result = self.evaluate(value, proof)
            self.assertIn(result['sizing_state'], ('RECONCILIATION_REQUIRED', 'REDUCIBLE_EXPOSURE_UNKNOWN'))
            self.assertIsNone(result['quantized_provider_close_size'])

    def test_caller_assertion_cross_owner_or_mutated_capability_is_rejected(self):
        from brokers.okx_product_capability import OKXProductCapabilityOwner, OKXProductCapabilityError
        value, proof = self.prepared()
        for bad in (True, {'state': 'PASS'}, replace(proof), OKXProductCapabilityOwner().issue(
                'POSITION_EXIT', self.account, value.instrument_metadata,
                observed_at=value.evaluated_at, now=value.evaluated_at)):
            with self.subTest(bad=type(bad).__name__), self.assertRaises(OKXProductCapabilityError):
                self.evaluate(value, bad)
        with self.assertRaises(OKXProductCapabilityError):
            self.evaluate(replace(value, capability=replace(value.capability, capability_generation_id='caller')), proof)

    def test_metadata_binding_and_stale_proof_do_not_refresh_authority(self):
        from brokers.okx_product_capability import OKXProductCapabilityError
        value, proof = self.prepared()
        with self.assertRaises(OKXProductCapabilityError):
            self.owner.close_capability(proof, value.instrument_metadata, now=value.evaluated_at + timedelta(seconds=31))
        with self.assertRaises(OKXProductCapabilityError):
            self.owner.close_capability(proof, replace(value.instrument_metadata, ct_val=Decimal('0.001')),
                                        now=value.evaluated_at)
        with self.assertRaises(OKXCloseSizingError):
            self.owner.evaluate_close(value, replace(self.binding_fixture.binding(value),
                                      instrument_metadata_generation='caller'), proof, now=value.evaluated_at)

    def test_unsupported_account_mode_or_role_cannot_be_proven(self):
        from brokers.okx_product_capability import OKXProductCapabilityError
        for role, account in (('UNKNOWN', self.account), ('POSITION_EXIT', replace(self.account, account_level='3')),
                              ('POSITION_EXIT', replace(self.account, position_mode='long_short_mode'))):
            with self.subTest(role=role, mode=account.position_mode), self.assertRaises(OKXProductCapabilityError):
                self.prepared(role=role, account=account)
        with self.assertRaises(ValueError):
            self.owner.issue([], self.account, self.fixture.metadata(), observed_at=self.fixture.now, now=self.fixture.now)

    def test_timestamp_only_supersession_does_not_renew_evidence(self):
        value, proof = self.prepared()
        previous = self.evaluate(value, proof)
        with self.assertRaises(OKXCloseSizingError):
            self.evaluate(value, proof, supersedes_evidence=previous)

    def test_mechanical_proof_does_not_bypass_five_second_submit_freshness(self):
        from brokers.okx_product_capability import OKXProductCapabilityError
        value = self.fixture.sizing_input()
        with self.assertRaises(OKXProductCapabilityError):
            self.owner.issue('POSITION_EXIT', self.account, value.instrument_metadata,
                             observed_at=value.evaluated_at, now=value.evaluated_at)

    def test_in_place_mutation_and_new_account_observation_invalidate_original_proof(self):
        from brokers.okx_product_capability import OKXProductCapabilityError
        value, proof = self.prepared()
        object.__setattr__(proof, 'role', 'EMERGENCY_EXIT')
        with self.assertRaises(OKXProductCapabilityError):
            self.owner.close_capability(proof, value.instrument_metadata, now=value.evaluated_at)
        value, proof = self.prepared()
        self.owner.issue('READ_ONLY_RECONCILIATION', replace(self.account, uid='456'),
                         value.instrument_metadata, observed_at=value.evaluated_at, now=value.evaluated_at)
        with self.assertRaises(OKXProductCapabilityError):
            self.owner.close_capability(proof, value.instrument_metadata, now=value.evaluated_at)


if __name__ == '__main__':
    unittest.main()
