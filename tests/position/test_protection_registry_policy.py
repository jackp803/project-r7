import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from position import (
    DECISION_PRESERVE_PROTECTED,
    DECISION_PROTECTION_LOST,
    FP11_DECISION_HOLD_SAFE,
    FP11_DECISION_RECONCILE,
    CurrentProtectionRegistryAuthority,
    PositionEvent,
    PositionLifecycleState,
    build_position_lifecycle_genesis_with_execution_binding,
    canonical_protection_registry_hash,
    fp11_registry_evidence_is_current,
    interpret_protection_registry_evidence,
    protection_registry_interpretation_is_current,
    validate_fp11_registry_evidence,
)
from src.execution.protection_registry_evidence import (
    COMPLETE,
    INCOMPLETE,
    STALE,
    UNKNOWN,
)
from src.execution.protection_registry_evidence_boundary import (
    build_protection_registry_multiplicity_evidence,
)
import tests.execution.test_protection_registry_evidence as fp11_fixture_module


class ProtectionRegistryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fp11_fixture_module.ProtectionRegistryMultiplicityEvidenceTests(
            methodName="test_exact_one_current_owned_exact_lineage_is_only_converged_success"
        )
        self.fixture.setUp()

    def _lifecycle(self, *, quantity="0.0012", lifecycle="OPEN_PROTECTED"):
        source = self.fixture.position(actual_quantity=quantity, lifecycle_state=lifecycle)
        interpreted_at = self.fixture.position_observed_at + timedelta(seconds=1)
        outcome = build_position_lifecycle_genesis_with_execution_binding(
            source,
            lifecycle_state=lifecycle,
            lifecycle_interpreted_at=interpreted_at,
            order_requests=[],
            order_results=[],
            fills=[],
        )
        return outcome.lifecycle_projection, outcome.execution_binding

    def _build(
        self,
        kind="success",
        *,
        quantity="0.0012",
        lifecycle="OPEN_PROTECTED",
        coverage=COMPLETE,
        currentness="CURRENT",
        evaluated_at=None,
    ):
        projection, binding = self._lifecycle(quantity=quantity, lifecycle=lifecycle)
        lifecycle_ref = projection["lifecycle_projection_id"]
        binding_ref = binding["lifecycle_execution_binding_id"]
        lineage = self.fixture.intended_lineage(
            projection,
            lifecycle_projection_ref=lifecycle_ref,
            lifecycle_execution_binding_ref=binding_ref,
        )

        dependencies = []
        entries = []
        if kind == "success":
            dep = self.fixture.fp04_dependency("protection-fp11-current")
            dependencies = [dep]
            entries = [self.fixture.entry(dep)]
        elif kind == "missing":
            pass
        elif kind == "multiple":
            first = self.fixture.fp04_dependency("protection-fp11-first")
            second = self.fixture.fp04_dependency("protection-fp11-second")
            dependencies = [first, second]
            entries = [self.fixture.entry(first), self.fixture.entry(second)]
        elif kind == "intended-plus-external":
            intended = self.fixture.fp04_dependency("protection-fp11-intended")
            external = self.fixture.fp04_dependency("protection-fp11-external", kind="external")
            dependencies = [intended, external]
            entries = [self.fixture.entry(intended), self.fixture.entry(external, binding="NOT_MATCH")]
        elif kind == "conflict":
            conflict = self.fixture.fp04_dependency("protection-fp11-conflict", kind="conflict")
            dependencies = [conflict]
            entries = [self.fixture.entry(conflict)]
        elif kind == "unknown":
            unknown = self.fixture.fp04_dependency("protection-fp11-unknown", kind="unknown")
            dependencies = [unknown]
            entries = [self.fixture.entry(unknown, binding="UNKNOWN")]
        elif kind == "external-terminal":
            external = self.fixture.fp04_dependency("protection-fp11-terminal-external", kind="external")
            dependencies = [external]
            entries = [self.fixture.entry(external, binding="NOT_MATCH")]
        else:
            raise AssertionError(kind)

        observed_set = self.fixture.observed_set(
            entries,
            coverage=coverage,
            currentness=currentness,
        )
        value = self.fixture.input_for(
            entries,
            dependencies,
            position=projection,
            lineage=lineage,
            observed_set=observed_set,
            lifecycle_projection_ref=lifecycle_ref,
            lifecycle_execution_binding_ref=binding_ref,
            evaluated_at=self.fixture.evaluated_at if evaluated_at is None else evaluated_at,
        )
        evidence = build_protection_registry_multiplicity_evidence(value)
        authority = CurrentProtectionRegistryAuthority(
            position_ref=evidence["position_ref"],
            position_hash=evidence["position_hash"],
            position=projection,
            lifecycle_projection=projection,
            lifecycle_execution_binding=binding,
            provider_identity_ref=evidence["provider_identity_ref"],
            provider_instrument_ref=evidence["provider_instrument_ref"],
            provider_observation_generation_id=evidence["provider_observation_generation_id"],
            provider_observed_at=evidence["provider_observed_at"],
            provider_received_at=evidence["provider_received_at"],
            observed_active_protection_set_hash=evidence["observed_active_protection_set_hash"],
        )
        return evidence, authority, value

    def test_converged_exact_current_registry_preserves_existing_protected_state_only(self):
        evidence, authority, _ = self._build("success")
        validate_fp11_registry_evidence(evidence)
        self.assertTrue(fp11_registry_evidence_is_current(evidence, authority))
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(DECISION_PRESERVE_PROTECTED, decision.decision)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, decision.next_state)
        self.assertIsNone(decision.event)
        self.assertTrue(decision.healthy_protection)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_converged_registry_with_incompatible_lifecycle_does_not_fabricate_protection_verified(self):
        evidence, authority, _ = self._build("success", lifecycle="OPEN_UNPROTECTED")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionEvent.STATE_UNKNOWN, decision.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertFalse(decision.healthy_protection)
        self.assertNotEqual(PositionEvent.PROTECTION_VERIFIED, decision.event)

    def test_converged_registry_with_stale_lifecycle_binding_fails_closed(self):
        evidence, authority, _ = self._build("success")
        stale_authority = replace(authority, lifecycle_execution_binding=None)
        self.assertFalse(fp11_registry_evidence_is_current(evidence, stale_authority))
        decision = interpret_protection_registry_evidence(evidence, stale_authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.evidence_current)

    def test_complete_current_missing_protection_rejects_protected_claim_as_protection_lost(self):
        evidence, authority, _ = self._build("missing")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(DECISION_PROTECTION_LOST, decision.decision)
        self.assertEqual(PositionEvent.PROTECTION_LOST, decision.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, decision.next_state)
        self.assertFalse(decision.healthy_protection)
        self.assertFalse(decision.provider_mutation_authorized)

    def test_missing_protection_does_not_authorize_protect_mutation(self):
        evidence, authority, _ = self._build("missing", lifecycle="OPEN_UNPROTECTED")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_HOLD_SAFE, decision.decision)
        self.assertEqual(PositionLifecycleState.OPEN_UNPROTECTED, decision.next_state)
        self.assertIsNone(decision.event)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_multiple_protections_fail_closed_without_winner_or_cleanup_target(self):
        evidence, authority, _ = self._build("multiple")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_one_intended_plus_external_extra_fails_closed_without_adoption(self):
        evidence, authority, _ = self._build("intended-plus-external")
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertIn("ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED", decision.source_required_dispositions)
        self.assertFalse(decision.healthy_protection)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_ownership_conflict_and_unknown_route_reconciliation(self):
        for kind in ("conflict", "unknown"):
            evidence, authority, _ = self._build(kind)
            decision = interpret_protection_registry_evidence(evidence, authority)
            self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
            self.assertFalse(decision.healthy_protection)
            self.assertFalse(decision.provider_mutation_authorized)

    def test_stale_incomplete_and_unknown_provider_sets_do_not_become_healthy(self):
        stale, stale_authority, _ = self._build("missing", currentness=STALE)
        stale_decision = interpret_protection_registry_evidence(stale, stale_authority)
        self.assertEqual(FP11_DECISION_RECONCILE, stale_decision.decision)
        self.assertFalse(stale_decision.evidence_current)

        incomplete, incomplete_authority, _ = self._build("missing", coverage=INCOMPLETE)
        incomplete_decision = interpret_protection_registry_evidence(incomplete, incomplete_authority)
        self.assertEqual(FP11_DECISION_RECONCILE, incomplete_decision.decision)
        self.assertFalse(incomplete_decision.healthy_protection)

        unknown, unknown_authority, _ = self._build("missing", coverage=UNKNOWN)
        unknown_decision = interpret_protection_registry_evidence(unknown, unknown_authority)
        self.assertEqual(FP11_DECISION_RECONCILE, unknown_decision.decision)
        self.assertFalse(unknown_decision.healthy_protection)

    def test_newer_position_provider_or_lifecycle_truth_invalidates_old_interpretation(self):
        evidence, authority, _ = self._build("success")
        decision = interpret_protection_registry_evidence(evidence, authority)

        changed_position = dict(authority.position)
        changed_position["actual_quantity"] = "0.0011"
        changed_position_authority = replace(
            authority,
            position=changed_position,
            position_hash=canonical_protection_registry_hash(changed_position),
        )
        self.assertFalse(
            protection_registry_interpretation_is_current(
                decision,
                evidence,
                changed_position_authority,
            )
        )

        changed_provider = replace(
            authority,
            provider_observation_generation_id="provider-protection-generation-new",
        )
        self.assertFalse(
            protection_registry_interpretation_is_current(decision, evidence, changed_provider)
        )

        changed_lifecycle = replace(authority, lifecycle_execution_binding=None)
        self.assertFalse(
            protection_registry_interpretation_is_current(decision, evidence, changed_lifecycle)
        )

    def test_materially_changed_fp11_evidence_invalidates_prior_interpretation(self):
        evidence, authority, _ = self._build("success")
        decision = interpret_protection_registry_evidence(evidence, authority)
        newer_evidence, newer_authority, _ = self._build("multiple")
        self.assertFalse(
            protection_registry_interpretation_is_current(
                decision,
                newer_evidence,
                newer_authority,
            )
        )

    def test_timestamp_only_reevaluation_does_not_create_materially_new_decision(self):
        evidence, authority, value = self._build("success")
        decision = interpret_protection_registry_evidence(evidence, authority)
        later_value = replace(value, evaluated_at=self.fixture.evaluated_at + timedelta(minutes=5))
        later_evidence = build_protection_registry_multiplicity_evidence(later_value)
        self.assertNotEqual(
            evidence["protection_registry_evidence_id"],
            later_evidence["protection_registry_evidence_id"],
        )
        later_decision = interpret_protection_registry_evidence(later_evidence, authority)
        self.assertEqual(decision.decision_id, later_decision.decision_id)
        self.assertTrue(
            protection_registry_interpretation_is_current(decision, later_evidence, authority)
        )

    def test_terminal_flat_with_unresolved_active_protection_reopens_false_green_closed_claim(self):
        evidence, authority, _ = self._build(
            "external-terminal",
            quantity="0",
            lifecycle="CLOSED",
        )
        self.assertIn(
            "FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED",
            evidence["required_dispositions"],
        )
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(FP11_DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionEvent.STATE_UNKNOWN, decision.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertTrue(decision.terminal_close_dependency)
        self.assertFalse(decision.provider_mutation_authorized)
        self.assertIsNone(decision.cleanup_target_ref)

    def test_same_exact_inputs_are_deterministic(self):
        evidence, authority, _ = self._build("success")
        first = interpret_protection_registry_evidence(evidence, authority)
        second = interpret_protection_registry_evidence(evidence, authority)
        self.assertEqual(first, second)
        self.assertTrue(first.decision_id.startswith("e5protreg_"))


if __name__ == "__main__":
    unittest.main()
