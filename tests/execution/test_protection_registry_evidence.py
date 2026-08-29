import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.execution.external_close_evidence import (
    CONFLICT,
    CURRENT,
    LINEAGE_CONFLICT,
    LINEAGE_CURRENT_GENERATION,
    LINEAGE_EXTERNAL,
    LINEAGE_PRIOR_GENERATION,
    LINEAGE_UNKNOWN,
    MULTIPLICITY_SINGLE,
    PROVIDER_BINDING_EXACT,
    STALE,
    UNKNOWN,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    build_external_provider_ownership_evidence,
    canonical_evidence_hash,
)
from src.execution.protection_registry_evidence import (
    BLOCK_PROTECTION_CREATE_REPLACE,
    BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL,
    COMPLETE,
    CONVERGED_EXACTLY_ONE_INTENDED,
    EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION,
    EXACT_MATCH,
    FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED,
    INCOMPLETE,
    LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED,
    MULTIPLE_ACTIVE_PROTECTIONS,
    NO_ACTION_REGISTRY_CONVERGED,
    NO_ACTIVE_PROTECTION_OBSERVED,
    NOT_MATCH,
    ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT,
    OWNERSHIP_CONFLICT_PRESENT,
    PROTECTION_SET_STALE,
    PROTECTION_SET_UNKNOWN,
    ProtectionRegistryEvidenceError,
    ProtectionRegistryMultiplicityInput,
    FP04ActiveProtectionDependency,
    active_protection_set_hash,
    build_protection_registry_multiplicity_evidence,
    canonical_protection_registry_hash,
    protection_registry_multiplicity_evidence_is_current,
    validate_protection_registry_multiplicity_evidence,
)


class ProtectionRegistryMultiplicityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.revision = "74bafe9bd52f95a2fe1b5d26ba0f3b0c7fffe7a0"
        self.provider_observed_at = datetime(2026, 8, 29, 10, 10, 10, tzinfo=timezone.utc)
        self.provider_received_at = self.provider_observed_at + timedelta(seconds=1)
        self.evaluated_at = self.provider_received_at + timedelta(seconds=10)
        self.position_observed_at = self.provider_observed_at - timedelta(seconds=5)
        self.provider_identity = {
            "provider": "SANITIZED_FIXTURE",
            "environment": "deterministic",
            "account_scope": "non-secret",
        }
        self.provider_identity_ref = "provider-identity:fixture:fp11"
        self.provider_instrument_ref = "provider-instrument:BTC_USDT_PERP"
        self.provider_generation = "provider-protection-generation-001"

    def position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp11-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T10:00:00Z",
            "broker_state_observed_at": self.position_observed_at.isoformat().replace("+00:00", "Z"),
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def position_ref(self, position):
        return f"position:{position['position_id']}@{position['broker_state_observed_at']}"

    def intended_lineage(self, position=None, **changes):
        position = self.position() if position is None else position
        values = {
            "position_ref": self.position_ref(position),
            "position_hash": canonical_protection_registry_hash(position),
            "position_id": position["position_id"],
            "position_observed_at": position["broker_state_observed_at"],
            "position_side": position["side"],
            "position_quantity_ref": "position-quantity:fp11-001",
            "position_action_ref": "position-action:protect:fp11-001",
            "position_action_hash": canonical_protection_registry_hash(
                {"position_action_id": "posact-protect-fp11-001", "action": "PROTECT"}
            ),
            "position_action_id": "posact-protect-fp11-001",
            "approved_trade_plan_ref": "approved-trade-plan:fp11-001",
            "approved_trade_plan_hash": canonical_protection_registry_hash(
                {"trade_plan_id": "plan-fp11-001", "risk_decision_id": "risk-fp11-001"}
            ),
            "risk_decision_ref": "risk-decision:fp11-001",
            "protection_order_request_ref": "order-request:protection-stop:fp11-001",
            "protection_order_request_hash": canonical_protection_registry_hash(
                {"order_request_id": "ordreq-protection-fp11-001", "order_role": "PROTECTION_STOP"}
            ),
            "client_order_identity_ref": "client-order-identity:protection-fp11-001",
            "lifecycle_projection_ref": "lifecycle-projection:fp11-001",
            "lifecycle_execution_binding_ref": "lifecycle-execution-binding:fp11-001",
            "trigger_validity_ref": None,
            "runtime_preflight_ref": None,
            "runtime_process_instance_id": None,
            "runtime_process_start_generation_id": None,
            "runtime_config_generation_id": None,
            "ownership_reconciliation_generation_ref": "ownership-generation:fp11-001",
        }
        values.update(changes)
        return values

    def _lineage_item(self, object_ref, *, claim="CLAIMS_OWNERSHIP"):
        return {
            "owner": "E4",
            "evidence_class": "PROTECTION_ORDER_BINDING",
            "evidence_ref": f"lineage:{object_ref}",
            "evidence_hash": canonical_evidence_hash({"provider_object_ref": object_ref}),
            "evidence_generation_id": self.provider_generation,
            "observed_or_created_at": self.provider_observed_at.isoformat().replace("+00:00", "Z"),
            "lineage_role": "ORDER_REQUEST",
            "claim_status": claim,
        }

    def _registry_item(self, object_ref, *, currentness=CURRENT):
        return {
            "owner": "E6",
            "evidence_class": "PROTECTION_EXECUTION_REGISTRY",
            "evidence_ref": f"registry:{object_ref}",
            "evidence_hash": canonical_evidence_hash({"provider_object_ref": object_ref, "generation": self.provider_generation}),
            "evidence_generation_id": self.provider_generation,
            "observed_at": self.provider_received_at.isoformat().replace("+00:00", "Z"),
            "currentness_status": currentness,
        }

    def fp04_dependency(self, object_ref, *, kind="current", snapshot=None, snapshot_ref=None):
        snapshot = (
            {
                "provider_object_ref": object_ref,
                "status": "ACTIVE",
                "purpose": "PROTECTIVE_STOP",
                "generation": self.provider_generation,
            }
            if snapshot is None
            else snapshot
        )
        snapshot_ref = snapshot_ref or f"provider-snapshot:{object_ref}:{self.provider_generation}"
        observation = ProviderObjectObservation(
            provider_object_class="ACTIVE_PROTECTION",
            provider_identity_ref=self.provider_identity_ref,
            provider_identity=self.provider_identity,
            canonical_symbol="BTC_USDT_PERP",
            provider_instrument_ref=self.provider_instrument_ref,
            provider_object_ref=object_ref,
            provider_snapshot_ref=snapshot_ref,
            provider_snapshot=snapshot,
            provider_observation_generation_id=self.provider_generation,
            provider_observed_at=self.provider_observed_at,
            provider_received_at=self.provider_received_at,
        )

        if kind == "current":
            lineage_status = LINEAGE_CURRENT_GENERATION
            lineage = [self._lineage_item(object_ref)]
            registry = [self._registry_item(object_ref)]
        elif kind == "external":
            lineage_status = LINEAGE_EXTERNAL
            lineage = []
            registry = [self._registry_item(object_ref)]
        elif kind == "prior":
            lineage_status = LINEAGE_PRIOR_GENERATION
            lineage = [self._lineage_item(object_ref, claim="SUPPORTS_LINEAGE")]
            registry = [self._registry_item(object_ref)]
        elif kind == "conflict":
            lineage_status = LINEAGE_CONFLICT
            lineage = [self._lineage_item(object_ref, claim="CONTRADICTS_LINEAGE")]
            registry = [self._registry_item(object_ref, currentness=CONFLICT)]
        elif kind == "unknown":
            lineage_status = LINEAGE_UNKNOWN
            lineage = [self._lineage_item(object_ref, claim="UNKNOWN")]
            registry = [self._registry_item(object_ref, currentness=UNKNOWN)]
        else:
            raise AssertionError(kind)

        context = OwnershipEvaluationContext(
            current_project_revision=self.revision,
            local_lineage_evidence=lineage,
            local_registry_evidence=registry,
            lineage_generation_status=lineage_status,
            provider_binding_status=PROVIDER_BINDING_EXACT,
            multiplicity_status=MULTIPLICITY_SINGLE,
            evaluated_at=self.provider_received_at + timedelta(seconds=1),
        )
        evidence = build_external_provider_ownership_evidence(observation, context)
        return FP04ActiveProtectionDependency(observation=observation, context=context, evidence=evidence)

    def entry(self, dependency, *, binding=EXACT_MATCH, binding_material=None):
        evidence = dependency.evidence
        if binding == UNKNOWN:
            binding_ref = None
            binding_hash = None
        else:
            binding_material = binding_material or {
                "provider_object_ref": evidence["provider_object_ref"],
                "position_action_id": "posact-protect-fp11-001",
                "order_request_id": "ordreq-protection-fp11-001",
                "binding": binding,
            }
            binding_ref = f"lineage-binding:{evidence['provider_object_ref']}:{binding}"
            binding_hash = canonical_protection_registry_hash(binding_material)
        return {
            "provider_object_ref": evidence["provider_object_ref"],
            "provider_snapshot_ref": evidence["provider_snapshot_ref"],
            "provider_snapshot_hash": evidence["provider_snapshot_hash"],
            "provider_object_observed_at": evidence["provider_observed_at"],
            "ownership_evidence_ref": evidence["ownership_evidence_id"],
            "ownership_evidence_hash": canonical_evidence_hash(evidence),
            "ownership_classification": evidence["ownership_classification"],
            "ownership_reconciliation_status": evidence["reconciliation_status"],
            "intended_lineage_binding_status": binding,
            "intended_lineage_binding_ref": binding_ref,
            "intended_lineage_binding_hash": binding_hash,
        }

    def observed_set(self, entries, *, coverage=COMPLETE, currentness=CURRENT, generation=None):
        generation = self.provider_generation if generation is None else generation
        value = {
            "provider_identity_ref": self.provider_identity_ref,
            "provider_identity_hash": canonical_evidence_hash(self.provider_identity),
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_ref": self.provider_instrument_ref,
            "provider_observation_generation_id": generation,
            "provider_observed_at": self.provider_observed_at.isoformat().replace("+00:00", "Z"),
            "provider_received_at": self.provider_received_at.isoformat().replace("+00:00", "Z"),
            "observation_coverage_status": coverage,
            "set_currentness_status": currentness,
            "objects": list(entries),
            "observed_set_hash": "sha256:" + "0" * 64,
        }
        value["observed_set_hash"] = active_protection_set_hash(value)
        return value

    def input_for(
        self,
        entries=(),
        dependencies=(),
        *,
        position=None,
        lineage=None,
        observed_set=None,
        lifecycle_projection_ref="lifecycle-projection:fp11-001",
        lifecycle_execution_binding_ref="lifecycle-execution-binding:fp11-001",
        lifecycle_currentness=CURRENT,
        runtime_refs=None,
        runtime_currentness=CURRENT,
        evaluated_at=None,
    ):
        position = self.position() if position is None else position
        lineage = self.intended_lineage(position) if lineage is None else lineage
        observed_set = self.observed_set(entries) if observed_set is None else observed_set
        runtime_refs = (None, None, None, None) if runtime_refs is None else runtime_refs
        return ProtectionRegistryMultiplicityInput(
            position_ref=self.position_ref(position),
            position=position,
            intended_protection_lineage=lineage,
            observed_active_protection_set=observed_set,
            fp04_dependencies=tuple(dependencies),
            evaluated_at=self.evaluated_at if evaluated_at is None else evaluated_at,
            lifecycle_projection_ref=lifecycle_projection_ref,
            lifecycle_execution_binding_ref=lifecycle_execution_binding_ref,
            lifecycle_currentness_status=lifecycle_currentness,
            runtime_preflight_ref=runtime_refs[0],
            runtime_process_instance_id=runtime_refs[1],
            runtime_process_start_generation_id=runtime_refs[2],
            runtime_config_generation_id=runtime_refs[3],
            runtime_currentness_status=runtime_currentness,
        )

    def test_complete_current_empty_set_is_missing_not_converged(self):
        evidence = build_protection_registry_multiplicity_evidence(self.input_for())
        self.assertEqual(NO_ACTIVE_PROTECTION_OBSERVED, evidence["multiplicity_state"])
        self.assertNotEqual(CONVERGED_EXACTLY_ONE_INTENDED, evidence["registry_status"])
        self.assertIn(BLOCK_PROTECTION_CREATE_REPLACE, evidence["required_dispositions"])
        self.assertIn("E5_PROTECTION_REINTERPRETATION_REQUIRED", evidence["reason_codes"])
        self.assertNotIn(NO_ACTION_REGISTRY_CONVERGED, evidence["required_dispositions"])

    def test_exact_one_current_owned_exact_lineage_is_only_converged_success(self):
        dependency = self.fp04_dependency("protection-001")
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(dependency)], [dependency])
        )
        self.assertEqual(EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION, evidence["multiplicity_state"])
        self.assertEqual(CONVERGED_EXACTLY_ONE_INTENDED, evidence["registry_status"])
        self.assertEqual([NO_ACTION_REGISTRY_CONVERGED], evidence["required_dispositions"])
        self.assertEqual(["EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED"], evidence["reason_codes"])
        validate_protection_registry_multiplicity_evidence(evidence)

    def test_exact_one_current_owned_but_not_matching_lineage_is_orphan(self):
        dependency = self.fp04_dependency("protection-001")
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(dependency, binding=NOT_MATCH)], [dependency])
        )
        self.assertEqual(ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT, evidence["multiplicity_state"])
        self.assertIn("INTENDED_PROTECTION_OBJECT_IDENTITY_MISMATCH", evidence["reason_codes"])
        self.assertIn(BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL, evidence["required_dispositions"])

    def test_stale_unknown_and_conflicting_fp04_never_converge(self):
        current = self.fp04_dependency("protection-stale")
        stale_context = replace(
            current.context,
            local_registry_evidence=[self._registry_item("protection-stale", currentness=STALE)],
            evaluated_at=self.provider_received_at + timedelta(seconds=2),
        )
        stale_dep = replace(current, context=stale_context)
        stale = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(stale_dep)], [stale_dep])
        )
        self.assertEqual(PROTECTION_SET_STALE, stale["multiplicity_state"])

        unknown_dep = self.fp04_dependency("protection-unknown", kind="unknown")
        unknown_evidence = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(unknown_dep, binding=UNKNOWN)], [unknown_dep])
        )
        self.assertEqual(PROTECTION_SET_UNKNOWN, unknown_evidence["multiplicity_state"])

        conflict_dep = self.fp04_dependency("protection-conflict", kind="conflict")
        conflict = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(conflict_dep)], [conflict_dep])
        )
        self.assertEqual(OWNERSHIP_CONFLICT_PRESENT, conflict["multiplicity_state"])
        self.assertIn("PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED", conflict["reason_codes"])

    def test_two_exact_intended_objects_are_multiple_and_no_winner_is_selected(self):
        first = self.fp04_dependency("protection-001")
        second = self.fp04_dependency("protection-002")
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(second), self.entry(first)], [second, first])
        )
        self.assertEqual(MULTIPLE_ACTIVE_PROTECTIONS, evidence["multiplicity_state"])
        self.assertEqual(2, evidence["active_protection_count"])
        self.assertIn("MULTIPLE_ACTIVE_PROTECTIONS_OBSERVED", evidence["reason_codes"])
        self.assertIn(BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL, evidence["required_dispositions"])
        self.assertNotIn(NO_ACTION_REGISTRY_CONVERGED, evidence["required_dispositions"])

    def test_intended_plus_external_or_prior_object_remains_multiple_nonconverged(self):
        intended = self.fp04_dependency("protection-intended")
        external = self.fp04_dependency("protection-external", kind="external")
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for(
                [self.entry(intended), self.entry(external, binding=NOT_MATCH)],
                [intended, external],
            )
        )
        self.assertEqual(MULTIPLE_ACTIVE_PROTECTIONS, evidence["multiplicity_state"])
        self.assertIn("EXTERNAL_OR_ORPHAN_PROTECTION_PRESENT", evidence["reason_codes"])

        prior = self.fp04_dependency("protection-prior", kind="prior")
        prior_evidence = build_protection_registry_multiplicity_evidence(
            self.input_for(
                [self.entry(intended), self.entry(prior, binding=NOT_MATCH)],
                [intended, prior],
            )
        )
        self.assertEqual(MULTIPLE_ACTIVE_PROTECTIONS, prior_evidence["multiplicity_state"])
        self.assertIn("PRIOR_GENERATION_PROTECTION_PRESENT", prior_evidence["reason_codes"])

    def test_incomplete_provider_set_cannot_become_zero_or_exactly_one(self):
        dep = self.fp04_dependency("protection-001")
        for entries, dependencies in (([], []), ([self.entry(dep)], [dep])):
            with self.subTest(count=len(entries)):
                observed = self.observed_set(entries, coverage=INCOMPLETE)
                evidence = build_protection_registry_multiplicity_evidence(
                    self.input_for(entries, dependencies, observed_set=observed)
                )
                self.assertEqual(PROTECTION_SET_UNKNOWN, evidence["multiplicity_state"])
                self.assertNotIn(
                    evidence["multiplicity_state"],
                    {NO_ACTIVE_PROTECTION_OBSERVED, EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION},
                )

    def test_stale_and_unknown_provider_set_fail_closed(self):
        dep = self.fp04_dependency("protection-001")
        stale_set = self.observed_set([self.entry(dep)], currentness=STALE)
        stale = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(dep)], [dep], observed_set=stale_set)
        )
        self.assertEqual(PROTECTION_SET_STALE, stale["multiplicity_state"])

        unknown_set = self.observed_set([self.entry(dep)], currentness=UNKNOWN)
        unknown = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(dep)], [dep], observed_set=unknown_set)
        )
        self.assertEqual(PROTECTION_SET_UNKNOWN, unknown["multiplicity_state"])

    def test_terminal_flat_position_with_active_protection_routes_fp10_convergence(self):
        dep = self.fp04_dependency("protection-001")
        position = self.position(actual_quantity="0", lifecycle_state="CLOSED")
        lineage = self.intended_lineage(position)
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for(
                [self.entry(dep)],
                [dep],
                position=position,
                lineage=lineage,
            )
        )
        self.assertEqual(EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION, evidence["multiplicity_state"])
        self.assertEqual(LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED, evidence["registry_status"])
        self.assertIn(
            FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED,
            evidence["required_dispositions"],
        )
        self.assertNotIn(NO_ACTION_REGISTRY_CONVERGED, evidence["required_dispositions"])

    def test_set_hash_and_evidence_identity_are_order_independent(self):
        first = self.fp04_dependency("protection-001")
        second = self.fp04_dependency("protection-002")
        input_a = self.input_for([self.entry(first), self.entry(second)], [first, second])
        input_b = self.input_for([self.entry(second), self.entry(first)], [second, first])
        evidence_a = build_protection_registry_multiplicity_evidence(input_a)
        evidence_b = build_protection_registry_multiplicity_evidence(input_b)
        self.assertEqual(
            evidence_a["observed_active_protection_set_hash"],
            evidence_b["observed_active_protection_set_hash"],
        )
        self.assertEqual(
            evidence_a["protection_registry_evidence_id"],
            evidence_b["protection_registry_evidence_id"],
        )
        self.assertEqual(
            [item["provider_object_ref"] for item in evidence_a["observed_active_protection_objects"]],
            ["protection-001", "protection-002"],
        )

    def test_material_provider_snapshot_change_invalidates_and_supersedes(self):
        old_dep = self.fp04_dependency("protection-001")
        old_input = self.input_for([self.entry(old_dep)], [old_dep])
        old = build_protection_registry_multiplicity_evidence(old_input)

        new_snapshot = {
            "provider_object_ref": "protection-001",
            "status": "ACTIVE",
            "purpose": "PROTECTIVE_STOP",
            "generation": self.provider_generation,
            "revision": "new-snapshot",
        }
        new_dep = self.fp04_dependency(
            "protection-001",
            snapshot=new_snapshot,
            snapshot_ref="provider-snapshot:protection-001:new",
        )
        new_input = self.input_for([self.entry(new_dep)], [new_dep])
        self.assertFalse(protection_registry_multiplicity_evidence_is_current(old, new_input))
        new = build_protection_registry_multiplicity_evidence(new_input, supersedes_evidence=old)
        self.assertNotEqual(old["protection_registry_evidence_id"], new["protection_registry_evidence_id"])
        self.assertEqual(old["protection_registry_evidence_id"], new["supersedes_registry_evidence_id"])

    def test_position_lifecycle_runtime_and_fp04_changes_invalidate_currentness(self):
        dep = self.fp04_dependency("protection-001")
        base_input = self.input_for([self.entry(dep)], [dep])
        evidence = build_protection_registry_multiplicity_evidence(base_input)

        newer_position = self.position(
            broker_state_observed_at=(self.position_observed_at + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
        )
        newer_lineage = self.intended_lineage(newer_position)
        position_input = self.input_for(
            [self.entry(dep)],
            [dep],
            position=newer_position,
            lineage=newer_lineage,
        )
        self.assertFalse(protection_registry_multiplicity_evidence_is_current(evidence, position_input))

        lifecycle_lineage = self.intended_lineage(
            lifecycle_projection_ref="lifecycle-projection:fp11-002",
            lifecycle_execution_binding_ref="lifecycle-execution-binding:fp11-002",
        )
        lifecycle_input = self.input_for(
            [self.entry(dep)],
            [dep],
            lineage=lifecycle_lineage,
            lifecycle_projection_ref="lifecycle-projection:fp11-002",
            lifecycle_execution_binding_ref="lifecycle-execution-binding:fp11-002",
        )
        self.assertFalse(protection_registry_multiplicity_evidence_is_current(evidence, lifecycle_input))

        runtime = (
            "runtime-preflight:fp11-002",
            "runtime-process:fp11-002",
            "runtime-start:fp11-002",
            "runtime-config:fp11-002",
        )
        runtime_lineage = self.intended_lineage(
            runtime_preflight_ref=runtime[0],
            runtime_process_instance_id=runtime[1],
            runtime_process_start_generation_id=runtime[2],
            runtime_config_generation_id=runtime[3],
        )
        runtime_input = self.input_for(
            [self.entry(dep)],
            [dep],
            lineage=runtime_lineage,
            runtime_refs=runtime,
        )
        self.assertFalse(protection_registry_multiplicity_evidence_is_current(evidence, runtime_input))

        stale_context = replace(
            dep.context,
            local_registry_evidence=[self._registry_item("protection-001", currentness=STALE)],
            evaluated_at=self.provider_received_at + timedelta(seconds=2),
        )
        stale_dep = replace(dep, context=stale_context)
        fp04_input = self.input_for([self.entry(stale_dep)], [stale_dep])
        self.assertFalse(protection_registry_multiplicity_evidence_is_current(evidence, fp04_input))

    def test_later_timestamp_alone_does_not_refresh_or_justify_supersession(self):
        dep = self.fp04_dependency("protection-001")
        original_input = self.input_for([self.entry(dep)], [dep])
        original = build_protection_registry_multiplicity_evidence(original_input)
        later_input = replace(original_input, evaluated_at=self.evaluated_at + timedelta(minutes=5))
        self.assertTrue(protection_registry_multiplicity_evidence_is_current(original, later_input))
        with self.assertRaises(ProtectionRegistryEvidenceError) as caught:
            build_protection_registry_multiplicity_evidence(
                later_input,
                supersedes_evidence=original,
            )
        self.assertEqual("SUPERSESSION_REQUIRES_MATERIAL_CHANGE", caught.exception.code)

    def test_evidence_contains_no_provider_network_credential_or_mutation_authority(self):
        dep = self.fp04_dependency("protection-001")
        evidence = build_protection_registry_multiplicity_evidence(
            self.input_for([self.entry(dep)], [dep])
        )
        forbidden = {
            "api_key",
            "api_secret",
            "passphrase",
            "credentials",
            "endpoint",
            "cancel_target",
            "create_request",
            "replace_request",
            "provider_order_payload",
            "authorization_to_mutate",
        }
        serialized_keys = set(evidence)
        serialized_keys.update(evidence["observed_active_protection_objects"][0])
        self.assertTrue(forbidden.isdisjoint(serialized_keys))


if __name__ == "__main__":
    unittest.main()
