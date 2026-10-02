"""Pure current-authority interpretation; no native/provider/LIVE authorization."""
import copy,importlib,unittest
from dataclasses import replace
from tests.integration import test_runtime_preflight as legacy_fixtures
from integration.runtime_preflight import evaluate_runtime_preflight,RuntimePreflightValidationError


class ProductRuntimePreflightV02Tests(unittest.TestCase):
    def setUp(self):self.base=legacy_fixtures.RuntimePreflightV01Tests();self.base.setUp()
    def api(self):
        try:return importlib.import_module('integration.product_runtime_preflight')
        except ModuleNotFoundError:self.fail('Missing pinned product v0.2 preflight; v0.1 authority must stay unchanged')
    def fixture(self):
        api=self.api();value=self.base._input(role='PAPER_RUNTIME')
        authorization=dict(value.authorization_evidence,authorization_class='PERSISTENT_LIVE_RUNTIME',authorized_runtime_role='LIVE_RUNTIME')
        value=replace(value,runtime_preflight_profile_version=api.PRODUCT_RUNTIME_PREFLIGHT_PROFILE_VERSION,runtime_role='LIVE_RUNTIME',requested_operational_mode='LIVE',authorization_evidence=authorization)
        return api,value,self.base._authority(value)

    def test_current_product_facts_are_eligible_but_legacy_profile_cannot_validate_or_accept_them(self):
        api,value,authority=self.fixture();result=api.evaluate_product_runtime_preflight(value,authority)
        self.assertEqual('ELIGIBLE',result['preflight_status']);api.validate_product_runtime_preflight_evidence(result)
        self.assertTrue(api.product_runtime_preflight_evidence_is_current(result,value,authority))
        with self.assertRaises(RuntimePreflightValidationError):evaluate_runtime_preflight(value,authority)
        legacy=replace(value,runtime_preflight_profile_version='runtime-preflight-v0.1')
        with self.assertRaises(RuntimePreflightValidationError):api.evaluate_product_runtime_preflight(legacy,authority)

    def test_bounded_permission_cannot_be_reused_for_persistent_role_or_clear_legacy_undefined_mode(self):
        api,value,authority=self.fixture()
        changed=replace(value,authorization_evidence=dict(value.authorization_evidence,authorization_class='BOUNDED_LIVE_FIRE_RUNTIME',authorized_runtime_role='BOUNDED_LIVE_FIRE_RUNTIME'))
        result=api.evaluate_product_runtime_preflight(changed,self.base._authority(changed))
        self.assertEqual('FAIL_CLOSED',result['preflight_status']);self.assertIn('PREFLIGHT_ROLE_AUTHORITY_EXCEEDED',result['reason_codes'])
        bounded=self.base._input(role='BOUNDED_LIVE_FIRE_RUNTIME');result=evaluate_runtime_preflight(bounded,self.base._authority(bounded))
        self.assertEqual('FAIL_CLOSED',result['preflight_status']);self.assertIn('PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED',result['reason_codes'])

    def test_wrong_revision_config_process_prior_boot_stale_heartbeat_or_single_instance_deny(self):
        api,value,authority=self.fixture()
        variants=[replace(value,project_revision='b'*40),replace(value,runtime_config_generation_id='other'),replace(value,process_start_generation_id='prior-boot'),
                  replace(value,single_instance_status='CONFLICT'),replace(value,heartbeat_evidence=dict(value.heartbeat_evidence,heartbeat_freshness_status='STALE')),
                  replace(value,requested_operational_mode='RESEARCH'),replace(value,worktree_classification='DIRTY')]
        for changed in variants:
            with self.subTest(value=changed):self.assertEqual('FAIL_CLOSED',api.evaluate_product_runtime_preflight(changed,authority)['preflight_status'])

    def test_missing_reconciliation_external_consumer_or_current_action_allowlist_deny(self):
        api,value,authority=self.fixture()
        for changed in [replace(value,reconciliation_evidence=dict(value.reconciliation_evidence,reconciliation_status='UNKNOWN')),
                        replace(value,external_consumer_evidence=None),replace(value,capability_evidence=dict(value.capability_evidence,allowlisted_action_ids=[])),
                        replace(value,authorization_evidence=dict(value.authorization_evidence,authorization_status='MISSING'))]:
            with self.subTest(value=changed):self.assertEqual('FAIL_CLOSED',api.evaluate_product_runtime_preflight(changed,authority)['preflight_status'])

    def test_old_evidence_cannot_refresh_itself_with_new_process_generation_or_mutated_hash(self):
        api,value,authority=self.fixture();result=api.evaluate_product_runtime_preflight(value,authority)
        newer=replace(value,process_start_generation_id='new-boot')
        self.assertFalse(api.product_runtime_preflight_evidence_is_current(result,newer,authority))
        mutated=copy.deepcopy(result);mutated['runtime_config_hash']='sha256:'+'f'*64
        self.assertFalse(api.product_runtime_preflight_evidence_is_current(mutated,value,authority))

    def test_untyped_input_and_missing_native_supervisor_fail_closed(self):
        api,value,authority=self.fixture()
        with self.assertRaises(RuntimePreflightValidationError):api.evaluate_product_runtime_preflight({'runtime_role':'LIVE_RUNTIME'},authority)
        changed=replace(value,supervisor_evidence=self.base._supervisor(present=False))
        self.assertEqual('FAIL_CLOSED',api.evaluate_product_runtime_preflight(changed,self.base._authority(changed))['preflight_status'])


if __name__=='__main__':unittest.main()
