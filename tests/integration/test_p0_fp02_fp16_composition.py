import unittest
from dataclasses import replace

from src.brokers.okx_action_capability import (
    CURRENT,
    EMERGENCY_EXIT,
    ENTRY,
    NET_MODE,
    OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED,
    OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN,
    OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN,
    OKX_SWAP_TRIGGER_BASIS_UNPROVEN,
    POSITION_EXIT,
    PROTECTION_STOP,
    READ_ONLY_RECONCILIATION,
    REPO_EVIDENCED,
    UNRESOLVED_FAIL_CLOSED,
    expected_repo_fieldset,
    expected_repo_fieldset_identity,
    okx_swap_action_capability_evidence_is_current,
    resolve_okx_swap_action_capability,
)
from src.brokers.okx_close_sizing import FULLY_REDUCIBLE, evaluate_okx_close_residual_sizing
from src.integration.runtime_preflight import ELIGIBLE, FAIL_CLOSED, evaluate_runtime_preflight
import tests.brokers.test_okx_action_capability as fp02_fixture_module
import tests.brokers.test_okx_close_sizing as fp05_fixture_module
import tests.integration.test_runtime_preflight as fp16_fixture_module
import tests.position.test_protection_registry_policy as fp11_fixture_module
import tests.position.test_protection_trigger_validity as fp03_fixture_module


class P0FP02FP16CompositionTests(unittest.TestCase):
    """Credential-free E7 definitions for FP-02/03/05/11/16 authority composition.

    These tests consume merged owner surfaces only. They define fail-closed
    cross-module expectations and intentionally perform no provider/network,
    credential, process-control, order mutation, runtime launch, or capital work.
    """

    @staticmethod
    def _fp02_fixture():
        fixture = fp02_fixture_module.OKXActionCapabilityTests(
            methodName="test_entry_net_mode_exact_owner_row_is_repo_evidenced"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp03_fixture():
        fixture = fp03_fixture_module.ProtectionTriggerValidityV01Tests(
            methodName="test_long_valid"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp05_fixture():
        fixture = fp05_fixture_module.OKXCloseResidualSizingTests(
            methodName="test_exact_current_facts_are_fully_reducible"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp11_fixture():
        fixture = fp11_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp16_fixture():
        fixture = fp16_fixture_module.RuntimePreflightV01Tests(
            methodName="test_coherent_credential_free_evidence_is_eligible_without_runtime_authority_side_effects"
        )
        fixture.setUp()
        return fixture

    def test_fp02_exact_entry_owner_row_is_repo_evidence_only(self):
        fixture = self._fp02_fixture()
        evidence = resolve_okx_swap_action_capability(fixture._facts(role=ENTRY, mode=NET_MODE))
        owner_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)

        self.assertEqual(REPO_EVIDENCED, evidence["capability_state"])
        self.assertEqual(owner_row["provider_fieldset_ref"], evidence["provider_fieldset_ref"])
        self.assertEqual(owner_row["provider_fieldset_generation_id"], evidence["provider_fieldset_generation_id"])
        for forbidden in (
            "provider_verified",
            "provider_dispatch_authorized",
            "runtime_authorized",
            "product_owner_authorized",
            "mutation_allowlisted",
            "capital_authorized",
        ):
            self.assertNotIn(forbidden, evidence)

    def test_fp02_copied_or_cross_role_owner_material_cannot_become_repo_evidenced(self):
        fixture = self._fp02_fixture()
        entry_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)

        forged_ref = fixture._facts(
            role=ENTRY,
            mode=NET_MODE,
            provider_fieldset=entry_row["provider_fieldset"],
            provider_fieldset_hash=entry_row["provider_fieldset_hash"],
            provider_fieldset_ref="forged:e7:p0:owner-row-ref",
            provider_fieldset_generation_id=entry_row["provider_fieldset_generation_id"],
        )
        forged_evidence = resolve_okx_swap_action_capability(forged_ref)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, forged_evidence["capability_state"])
        self.assertNotEqual(REPO_EVIDENCED, forged_evidence["capability_state"])

        cross_role = fixture._facts(
            role=READ_ONLY_RECONCILIATION,
            mode=NET_MODE,
            provider_fieldset=entry_row["provider_fieldset"],
            provider_fieldset_hash=entry_row["provider_fieldset_hash"],
            provider_fieldset_ref=entry_row["provider_fieldset_ref"],
            provider_fieldset_generation_id=entry_row["provider_fieldset_generation_id"],
        )
        cross_role_evidence = resolve_okx_swap_action_capability(cross_role)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, cross_role_evidence["capability_state"])

    def test_fp03_actionable_and_fp11_converged_still_leave_protection_provider_native_capability_unresolved(self):
        fp02 = self._fp02_fixture()
        fp03 = self._fp03_fixture()
        trigger = fp03._evidence(side="LONG", price="60000")
        self.assertEqual("ACTIONABLE", trigger["validity_status"])

        fp11 = self._fp11_fixture()
        registry, _, _ = fp11._build("success")
        self.assertEqual("CONVERGED_EXACTLY_ONE_INTENDED", registry["registry_status"])

        evidence = resolve_okx_swap_action_capability(
            fp02._facts(
                role=PROTECTION_STOP,
                mode=NET_MODE,
                fp03_trigger_validity_ref=trigger["protection_trigger_validity_id"],
                fp03_trigger_validity_status=trigger["validity_status"],
                fp03_trigger_validity_currentness=CURRENT,
                fp11_registry_ref=registry["protection_registry_evidence_id"],
                fp11_registry_status=registry["registry_status"],
                fp11_registry_currentness=CURRENT,
            )
        )
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertIn(OKX_SWAP_TRIGGER_BASIS_UNPROVEN, evidence["reason_codes"])
        self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])
        self.assertIsNone(evidence["provider_fieldset_ref"])

    def test_coherent_fp05_sizing_does_not_resolve_exit_or_emergency_provider_fieldset(self):
        fp05 = self._fp05_fixture()
        sizing = evaluate_okx_close_residual_sizing(fp05.sizing_input())
        self.assertEqual(FULLY_REDUCIBLE, sizing["sizing_state"])

        fp02 = self._fp02_fixture()
        for role in (POSITION_EXIT, EMERGENCY_EXIT):
            with self.subTest(role=role):
                evidence = resolve_okx_swap_action_capability(
                    fp02._facts(
                        role=role,
                        mode=NET_MODE,
                        fp05_close_sizing_ref=sizing["sizing_evidence_id"],
                        fp05_close_sizing_status=sizing["sizing_state"],
                        fp05_close_sizing_currentness=CURRENT,
                    )
                )
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
                self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])
                self.assertIsNone(evidence["provider_fieldset_ref"])

    def test_emergency_role_cannot_bypass_provider_capability_proof(self):
        fixture = self._fp02_fixture()
        evidence = resolve_okx_swap_action_capability(fixture._facts(role=EMERGENCY_EXIT, mode=NET_MODE))
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])

    def test_read_only_reconciliation_is_get_only_default_deny_and_never_mutation_authority(self):
        fixture = self._fp02_fixture()
        descriptor = expected_repo_fieldset(READ_ONLY_RECONCILIATION, NET_MODE)
        self.assertEqual("GET_ONLY", descriptor["method"])
        self.assertTrue(descriptor["default_deny"])
        self.assertEqual([], descriptor["mutation_methods"])

        positive = resolve_okx_swap_action_capability(
            fixture._facts(role=READ_ONLY_RECONCILIATION, mode=NET_MODE)
        )
        self.assertEqual(REPO_EVIDENCED, positive["capability_state"])

        mutation = resolve_okx_swap_action_capability(
            fixture._facts(
                role=READ_ONLY_RECONCILIATION,
                mode=NET_MODE,
                operation_class="MUTATION: ORDER_CANCEL",
            )
        )
        self.assertEqual("FORBIDDEN", mutation["capability_state"])
        self.assertEqual([OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN], mutation["reason_codes"])

    def test_runtime_preflight_eligible_and_allowlist_facts_cannot_upgrade_fp02_provider_capability(self):
        fp16 = self._fp16_fixture()
        preflight = fp16._evaluate()
        self.assertEqual(ELIGIBLE, preflight["preflight_status"])

        fp02 = self._fp02_fixture()
        evidence = resolve_okx_swap_action_capability(
            fp02._facts(
                role=PROTECTION_STOP,
                mode=NET_MODE,
                caller_capability_assertion=preflight,
            )
        )
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertIn(OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED, evidence["reason_codes"])
        self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])

    def test_fp02_repo_evidence_cannot_substitute_for_fp16_runtime_authorization(self):
        fp02 = self._fp02_fixture()
        repo_evidence = resolve_okx_swap_action_capability(fp02._facts(role=ENTRY, mode=NET_MODE))
        self.assertEqual(REPO_EVIDENCED, repo_evidence["capability_state"])

        fp16 = self._fp16_fixture()
        missing_authorization = fp16._authorization(status="MISSING")
        value = fp16._input(authorization=missing_authorization)
        authority = fp16._authority(value)
        preflight = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, preflight["preflight_status"])
        self.assertIn("PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN", preflight["reason_codes"])

    def test_fp16_external_participation_role_isolation_bounded_mode_and_revision_binding_remain_fail_closed(self):
        fixture = self._fp16_fixture()

        value = fixture._input()
        external = fixture._external_consumer()
        external_authority = {
            "external_consumer_id": external["external_consumer_id"],
            "external_consumer_generation_id": external["external_consumer_generation_id"],
            "external_consumer_config_hash": external["external_consumer_config_hash"],
            "compatibility_profile_ref": external["compatibility_profile_ref"],
            "compatibility_evidence_hash": external["compatibility_evidence_hash"],
        }
        authority = fixture._authority(value, external_consumer_authority=external_authority)
        missing_external = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, missing_external["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", missing_external["reason_codes"])

        shadow = replace(value, runtime_role="SHADOW_RUNTIME", requested_operational_mode="SHADOW")
        shadow_authority = fixture._authority(
            shadow,
            operational_mode_authority={
                "transition_id": "opmode-fixture-001",
                "mode_revision": 7,
                "mode": "SHADOW",
                "payload_hash": fixture.mode_hash,
            },
        )
        shadow_evidence = evaluate_runtime_preflight(shadow, shadow_authority)
        self.assertEqual(FAIL_CLOSED, shadow_evidence["preflight_status"])
        self.assertIn("PREFLIGHT_ROLE_AUTHORITY_EXCEEDED", shadow_evidence["reason_codes"])

        bounded = fixture._input(role="BOUNDED_LIVE_FIRE_RUNTIME")
        bounded_evidence = evaluate_runtime_preflight(bounded, fixture._authority(bounded))
        self.assertEqual(FAIL_CLOSED, bounded_evidence["preflight_status"])
        self.assertIn("PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED", bounded_evidence["reason_codes"])

        historical = fixture._input(project_revision="8fbf5fcae2eaf44accdf535121d8abf29ef5c93c")
        historical_evidence = evaluate_runtime_preflight(historical, fixture._authority(historical))
        self.assertEqual(FAIL_CLOSED, historical_evidence["preflight_status"])
        self.assertIn("PREFLIGHT_REVISION_MISMATCH", historical_evidence["reason_codes"])

    def test_material_owner_row_change_invalidates_prior_fp02_positive_evidence(self):
        fixture = self._fp02_fixture()
        facts = fixture._facts(role=ENTRY, mode=NET_MODE)
        first = resolve_okx_swap_action_capability(facts)
        self.assertEqual(REPO_EVIDENCED, first["capability_state"])

        changed = replace(
            facts,
            provider_fieldset_generation_id="changed:e7:p0:owner-row-generation",
        )
        second = resolve_okx_swap_action_capability(changed)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, second["capability_state"])
        self.assertFalse(okx_swap_action_capability_evidence_is_current(first, changed))
        self.assertNotEqual(first["capability_evidence_id"], second["capability_evidence_id"])

    def test_composition_evidence_contains_no_provider_runtime_or_capital_authority_upgrade(self):
        fp02 = self._fp02_fixture()
        repo_evidence = resolve_okx_swap_action_capability(fp02._facts(role=ENTRY, mode=NET_MODE))
        fp16 = self._fp16_fixture()
        preflight = fp16._evaluate()

        for evidence in (repo_evidence, preflight):
            for forbidden in (
                "provider_request",
                "credential",
                "provider_mutation_authorized",
                "order_authorized",
                "process_launch_authorized",
                "shadow_authorized",
                "paper_authorized",
                "bounded_live_fire_authorized",
                "live_authorized",
                "capital_authorized",
            ):
                self.assertNotIn(forbidden, evidence)


if __name__ == "__main__":
    unittest.main()
