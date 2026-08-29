import unittest
from dataclasses import replace
from datetime import timedelta

from src.brokers.okx_close_sizing import (
    CLOSE_CAPABILITY_UNPROVEN,
    POST_ACTION_RESIDUAL,
    RESIDUAL_NONZERO_REPRESENTABLE,
    RESIDUAL_NONZERO_UNREPRESENTABLE,
    UNRESOLVED_FAIL_CLOSED,
    evaluate_okx_close_residual_sizing,
)
from src.execution.external_close_evidence import (
    EXTERNAL_MANUAL,
    LINEAGE_EXTERNAL,
    build_external_manual_close_convergence_evidence,
)
from src.execution.protection_trigger import (
    ProtectionTriggerConsumerError,
    validate_protection_trigger_create_evidence,
)
from src.position import (
    FAIL_CLOSED,
    FRESH,
    interpret_protection_registry_evidence,
)
import tests.brokers.test_okx_close_sizing as fp05_fixture_module
import tests.execution.test_external_close_evidence as fp10_fixture_module
import tests.position.test_protection_registry_policy as fp11_policy_fixture_module
import tests.position.test_protection_trigger_validity as fp03_fixture_module


class P0IntegratedFailurePreventionTests(unittest.TestCase):
    """Credential-free cross-module definitions for LF-2 P0 safety composition.

    These tests intentionally use the real owner-level public/internal composition
    surfaces already merged on main. They do not model provider-native mutation,
    credentials, network transport, runtime authorization, or capital authority.
    """

    @staticmethod
    def _fp03_fixture():
        fixture = fp03_fixture_module.ProtectionTriggerValidityV01Tests(
            methodName="test_long_equality_breached"
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
    def _fp10_fixture():
        fixture = fp10_fixture_module.ExternalCloseEvidenceProducerTests(
            methodName="test_fp10_exact_flat_current_compatible_chain_emits_consumable_close_eligible_evidence"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp11_fixture():
        fixture = fp11_policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        fixture.setUp()
        return fixture

    def test_fp03_breached_or_equal_trigger_stays_fail_closed_at_e4_boundary(self):
        fixture = self._fp03_fixture()
        cases = (("LONG", "59400.00"), ("SHORT", "60600.00"))
        for side, market_price in cases:
            with self.subTest(side=side):
                position = fixture._position(side=side)
                plan = fixture._plan(side=side)
                action = fixture._action(side=side, position=position, plan=plan)
                market = fixture._market(market_price)
                evidence = fixture._evidence(
                    side=side,
                    position=position,
                    plan=plan,
                    action=action,
                    market=market,
                )
                self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
                self.assertEqual(["TRIGGER_ALREADY_BREACHED"], evidence["reason_codes"])
                with self.assertRaises(ProtectionTriggerConsumerError) as caught:
                    validate_protection_trigger_create_evidence(
                        action,
                        plan,
                        position,
                        evidence,
                        market,
                        market_freshness_classification=FRESH,
                        now=fixture.evaluated_at,
                    )
                self.assertEqual("E4_TRIGGER_VALIDITY_FAIL_CLOSED", caught.exception.code)

    def test_fp03_newer_market_truth_invalidates_prior_actionable_evidence(self):
        fixture = self._fp03_fixture()
        position = fixture._position(side="LONG")
        plan = fixture._plan(side="LONG")
        action = fixture._action(side="LONG", position=position, plan=plan)
        market = fixture._market("60000")
        evidence = fixture._evidence(
            side="LONG",
            position=position,
            plan=plan,
            action=action,
            market=market,
        )
        self.assertEqual("ACTIONABLE", evidence["validity_status"])

        newer_market = fixture._market(
            "60000",
            observed_at=fixture.market_observed + timedelta(seconds=5),
            received_at=fixture.market_received + timedelta(seconds=5),
        )
        with self.assertRaises(ProtectionTriggerConsumerError) as caught:
            validate_protection_trigger_create_evidence(
                action,
                plan,
                position,
                evidence,
                newer_market,
                market_freshness_classification=FRESH,
                now=fixture.evaluated_at + timedelta(seconds=10),
            )
        self.assertEqual("E4_TRIGGER_VALIDITY_NOT_CURRENT", caught.exception.code)

    def test_fp04_external_manual_position_never_silently_adopts_and_routes_fp10(self):
        fixture = self._fp10_fixture()
        external_fp04 = fixture.fp04(
            context=fixture.ownership_context(
                lineage_status=LINEAGE_EXTERNAL,
                lineage=[],
                registry=[],
            )
        )
        self.assertEqual("EXTERNAL_UNTRACKED", external_fp04["ownership_classification"])
        self.assertIsNone(external_fp04["adoption_decision_ref"])
        self.assertIn("LIFECYCLE_REINTERPRETATION_REQUIRED", external_fp04["required_dispositions"])

        position = fixture.position(quantity="0.0007", state="OPEN_PROTECTED")
        evidence = build_external_manual_close_convergence_evidence(
            fixture.assembly(
                position=position,
                fp04=external_fp04,
                origin=EXTERNAL_MANUAL,
                state="EXPOSURE_REDUCED_NOT_FLAT",
                execution=[
                    fixture.execution(
                        origin="EXTERNAL_MANUAL",
                        evidence_class="EXTERNAL_EXECUTION_OBSERVATION",
                    )
                ],
                reasons=["POSITIVE_EXPOSURE_REMAINS", "EXTERNAL_MANUAL_EXECUTION_OBSERVED"],
            )
        )
        self.assertEqual(EXTERNAL_MANUAL, evidence["exposure_change_origin_classification"])
        self.assertEqual("EXPOSURE_REDUCED_NOT_FLAT", evidence["convergence_state"])
        self.assertNotEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])

    def test_fp05_fresh_positive_residual_remains_nonflat_when_consumed_by_fp10(self):
        fp05 = self._fp05_fixture()
        source = fp05.position()
        observed = fp05.position_observed + timedelta(seconds=20)
        current = fp05.position(
            quantity="0.0004",
            observed=observed,
            lifecycle="EXIT_REQUESTED",
        )
        provider = fp05.provider(
            contracts="4",
            canonical="0.0004",
            observed=observed,
            generation="provider-gen-p0-residual-001",
            snapshot_ref="provider-position-snapshot-p0-residual-001",
        )
        sizing = evaluate_okx_close_residual_sizing(
            fp05.sizing_input(
                source_position=source,
                current_position=current,
                provider=provider,
                phase=POST_ACTION_RESIDUAL,
                evaluated_at=observed + timedelta(seconds=10),
            )
        )
        self.assertEqual(RESIDUAL_NONZERO_REPRESENTABLE, sizing["sizing_state"])

        fp10 = self._fp10_fixture()
        position = fp10.position(quantity="0.0004")
        convergence = build_external_manual_close_convergence_evidence(
            fp10.assembly(
                position=position,
                fp05_state=sizing["sizing_state"],
                fp05_ref=sizing["sizing_evidence_id"],
                fp05_hash=sizing["sizing_evidence_hash"],
                state="EXPOSURE_REDUCED_NOT_FLAT",
                reasons=["POSITIVE_EXPOSURE_REMAINS", RESIDUAL_NONZERO_REPRESENTABLE],
            )
        )
        self.assertEqual("EXPOSURE_REDUCED_NOT_FLAT", convergence["convergence_state"])
        self.assertEqual(RESIDUAL_NONZERO_REPRESENTABLE, convergence["fp05_residual_state"])

    def test_fp05_unrepresentable_residual_and_unproven_capability_never_create_retry_authority(self):
        fixture = self._fp05_fixture()
        source = fixture.position()
        observed = fixture.position_observed + timedelta(seconds=20)
        current = fixture.position(
            quantity="0.00005",
            observed=observed,
            lifecycle="EXIT_REQUESTED",
        )
        provider = fixture.provider(
            contracts="0.5",
            canonical="0.00005",
            observed=observed,
            generation="provider-gen-p0-dust-001",
            snapshot_ref="provider-position-snapshot-p0-dust-001",
        )
        unrepresentable = evaluate_okx_close_residual_sizing(
            fixture.sizing_input(
                source_position=source,
                current_position=current,
                provider=provider,
                phase=POST_ACTION_RESIDUAL,
                evaluated_at=observed + timedelta(seconds=10),
            )
        )
        self.assertEqual(RESIDUAL_NONZERO_UNREPRESENTABLE, unrepresentable["sizing_state"])
        self.assertIn("OKX_CLOSE_NEWER_EVIDENCE_REQUIRED", unrepresentable["reason_codes"])
        self.assertIsNone(unrepresentable["quantized_provider_close_size"])

        unresolved = replace(
            fixture.capability(),
            capability_state=UNRESOLVED_FAIL_CLOSED,
            provider_fieldset_status=UNRESOLVED_FAIL_CLOSED,
        )
        capability_evidence = evaluate_okx_close_residual_sizing(
            fixture.sizing_input(capability=unresolved)
        )
        self.assertEqual(CLOSE_CAPABILITY_UNPROVEN, capability_evidence["sizing_state"])
        self.assertIsNone(capability_evidence["quantized_provider_close_size"])

    def test_fp11_only_exact_single_current_owned_lineage_is_healthy_and_never_mutation_authority(self):
        fixture = self._fp11_fixture()
        success, success_authority, _ = fixture._build("success")
        decision = interpret_protection_registry_evidence(success, success_authority)
        self.assertTrue(decision.healthy_protection)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

        for kind in ("missing", "multiple", "intended-plus-external", "conflict", "unknown"):
            with self.subTest(kind=kind):
                evidence, authority, _ = fixture._build(kind)
                rejected = interpret_protection_registry_evidence(evidence, authority)
                self.assertFalse(rejected.healthy_protection)
                self.assertFalse(rejected.provider_mutation_authorized)
                self.assertIsNone(rejected.cleanup_target_ref)

    def test_fp11_flat_closed_with_external_protection_reopens_false_green_lifecycle(self):
        fixture = self._fp11_fixture()
        evidence, authority, _ = fixture._build(
            "external-terminal",
            quantity="0",
            lifecycle="CLOSED",
        )
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertTrue(decision.terminal_close_dependency)
        self.assertEqual("RECONCILIATION_REQUIRED", decision.next_state.value)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)


if __name__ == "__main__":
    unittest.main()
