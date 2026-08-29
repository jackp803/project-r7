import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.external_close_evidence import (
    CONFLICT,
    CURRENT,
    EXTERNAL_MANUAL,
    FP04EvidenceDependency,
    LINEAGE_CONFLICT,
    LINEAGE_CURRENT_GENERATION,
    LINEAGE_EXTERNAL,
    LINEAGE_PRIOR_GENERATION,
    LINEAGE_UNKNOWN,
    MULTIPLICITY_SINGLE,
    NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE,
    OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED,
    PROVIDER_BINDING_EXACT,
    PROVIDER_BINDING_MISMATCH,
    RESIDUAL_NONZERO_REPRESENTABLE,
    RESIDUAL_NONZERO_UNREPRESENTABLE,
    RESIDUAL_UNREPRESENTABLE_NOT_FLAT,
    STALE,
    CloseConvergenceAssemblyInput,
    ExternalCloseEvidenceError,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    ProviderPositionObservation,
    TerminalProtectionObservation,
    build_external_manual_close_convergence_evidence,
    build_external_provider_ownership_evidence,
    canonical_evidence_hash,
    external_manual_close_convergence_evidence_is_current,
    external_provider_ownership_evidence_is_current,
)
from src.position import (
    build_position_lifecycle_genesis_with_execution_binding,
    validate_external_manual_close_convergence_evidence,
    validate_external_provider_ownership_evidence,
)


class ExternalCloseEvidenceProducerTests(unittest.TestCase):
    def setUp(self):
        self.revision = "efcd3631ad069cd50afd22abbb9dd8028e23d9ac"
        self.observed = "2026-08-29T09:30:00Z"
        self.received = "2026-08-29T09:30:01Z"
        self.lineage_time = "2026-08-29T09:30:02Z"
        self.registry_time = "2026-08-29T09:30:03Z"
        self.terminal_observed = "2026-08-29T09:30:04Z"
        self.terminal_received = "2026-08-29T09:30:05Z"
        self.evaluated = "2026-08-29T09:30:06Z"

    def provider_object(self, **changes):
        values = {
            "provider_object_class": "POSITION_EXPOSURE",
            "provider_identity_ref": "provider-fixture:okx:prod-readonly",
            "provider_identity": {
                "provider": "OKX",
                "environment": "production_observation_fixture",
                "api_version": "V5",
            },
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_object_ref": "provider-position:BTC-USDT-SWAP:net",
            "provider_snapshot_ref": "provider-position-snapshot-001",
            "provider_snapshot": {
                "instId": "BTC-USDT-SWAP",
                "posSide": "net",
                "normalized_quantity": "0",
            },
            "provider_observation_generation_id": "provider-observation-gen-001",
            "provider_observed_at": self.observed,
            "provider_received_at": self.received,
        }
        values.update(changes)
        return ProviderObjectObservation(**values)

    def lineage(self, *, claim="CLAIMS_OWNERSHIP", ref="order-request-001", generation="exec-gen-001"):
        return {
            "owner": "E4",
            "evidence_class": "ORDER_REQUEST",
            "evidence_ref": ref,
            "evidence_hash": canonical_evidence_hash(
                {"order_request_id": ref, "provider_object_ref": "provider-position:BTC-USDT-SWAP:net"}
            ),
            "evidence_generation_id": generation,
            "observed_or_created_at": self.lineage_time,
            "lineage_role": "ORDER_REQUEST",
            "claim_status": claim,
        }

    def registry(self, *, currentness=CURRENT, ref="registry-001", generation="registry-gen-001"):
        return {
            "owner": "E6",
            "evidence_class": "EXECUTION_REGISTRY",
            "evidence_ref": ref,
            "evidence_hash": canonical_evidence_hash({"registry_ref": ref, "generation": generation}),
            "evidence_generation_id": generation,
            "observed_at": self.registry_time,
            "currentness_status": currentness,
        }

    def ownership_context(
        self,
        *,
        lineage_status=LINEAGE_CURRENT_GENERATION,
        provider_binding=PROVIDER_BINDING_EXACT,
        lineage=None,
        registry=None,
        evaluated=None,
        runtime_config=None,
    ):
        return OwnershipEvaluationContext(
            current_project_revision=self.revision,
            local_lineage_evidence=[self.lineage()] if lineage is None else lineage,
            local_registry_evidence=[self.registry()] if registry is None else registry,
            lineage_generation_status=lineage_status,
            provider_binding_status=provider_binding,
            multiplicity_status=MULTIPLICITY_SINGLE,
            evaluated_at=self.evaluated if evaluated is None else evaluated,
            runtime_preflight_ref=None if runtime_config is None else "runtime-preflight-001",
            runtime_process_instance_id=None if runtime_config is None else "runtime-process-001",
            runtime_process_start_generation_id=None if runtime_config is None else "runtime-start-001",
            runtime_config_generation_id=runtime_config,
        )

    def fp04(self, *, observation=None, context=None, supersedes=None):
        return build_external_provider_ownership_evidence(
            self.provider_object() if observation is None else observation,
            self.ownership_context() if context is None else context,
            supersedes_evidence=supersedes,
        )

    def position(self, *, quantity="0", state="EXIT_REQUESTED", observed=None):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp10-e4-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": quantity,
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T09:00:00Z",
            "broker_state_observed_at": self.observed if observed is None else observed,
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": state,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def lifecycle(self, position):
        interpreted = datetime.fromisoformat(position["broker_state_observed_at"][:-1] + "+00:00") + timedelta(
            milliseconds=100
        )
        outcome = build_position_lifecycle_genesis_with_execution_binding(
            position,
            lifecycle_state=position["lifecycle_state"],
            lifecycle_interpreted_at=interpreted,
            order_requests=[],
            order_results=[],
            fills=[],
        )
        return outcome.lifecycle_projection, outcome.execution_binding

    def provider_position(self, position=None, **changes):
        position = self.position() if position is None else position
        values = {
            "provider_identity_ref": "provider-fixture:okx:prod-readonly",
            "provider_identity": {
                "provider": "OKX",
                "environment": "production_observation_fixture",
                "api_version": "V5",
            },
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_position_snapshot_ref": "provider-position-snapshot-001",
            "provider_position_snapshot": {
                "instId": "BTC-USDT-SWAP",
                "posSide": "net",
                "normalized_quantity": position["actual_quantity"],
            },
            "provider_position_observation_generation_id": "provider-position-gen-001",
            "provider_position_observed_at": position["broker_state_observed_at"],
            "provider_position_received_at": self.received,
            "provider_position_currentness_status": CURRENT,
            "position_id": position["position_id"],
            "canonical_symbol": position["symbol"],
            "position_side": position["side"],
            "normalized_actual_quantity": position["actual_quantity"],
        }
        values.update(changes)
        return ProviderPositionObservation(**values)

    def execution(
        self,
        *,
        currentness=CURRENT,
        compatibility="COMPATIBLE",
        origin="CURRENT_GENERATION_PROJECT",
        evidence_class="ORDER_RESULT_SET",
        ref="close-result-set-001",
    ):
        return {
            "owner": "E4",
            "evidence_class": evidence_class,
            "evidence_ref": ref,
            "evidence_hash": canonical_evidence_hash(
                {"ref": ref, "terminal_status": "FILLED", "fixture_only": True}
            ),
            "evidence_generation_id": "execution-gen-001",
            "latest_observed_at": self.observed,
            "currentness_status": currentness,
            "position_compatibility_status": compatibility,
            "lineage_origin": origin,
        }

    def terminal_protection(self, *, status="TERMINAL_PROTECTION_CLEAR", payload=None):
        return TerminalProtectionObservation(
            observation_ref="terminal-protection-set-001",
            observation_payload={
                "coverage": "COMPLETE",
                "currentness": "CURRENT",
                "active_protection_count": 0,
            }
            if payload is None
            else payload,
            observed_at=self.terminal_observed,
            received_at=self.terminal_received,
            status=status,
        )

    def assembly(
        self,
        *,
        position=None,
        provider_position=None,
        fp04=None,
        fp04_currentness=CURRENT,
        execution=None,
        terminal=None,
        fp05_state="NOT_APPLICABLE",
        fp05_ref=None,
        fp05_hash=None,
        fp11_ref=None,
        fp11_hash=None,
        origin="CURRENT_GENERATION_PROJECT",
        state="LIFECYCLE_CLOSE_ELIGIBLE",
        reasons=None,
        dispositions=None,
        runtime_config=None,
        evaluated=None,
    ):
        position = self.position() if position is None else position
        projection, binding = self.lifecycle(position)
        provider_position = (
            self.provider_position(position) if provider_position is None else provider_position
        )
        fp04 = self.fp04() if fp04 is None else fp04
        execution = [self.execution()] if execution is None else execution
        terminal = self.terminal_protection() if terminal is None else terminal
        if reasons is None:
            reasons = {
                "LIFECYCLE_CLOSE_ELIGIBLE": ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"],
                "EXPOSURE_STILL_OPEN": ["POSITIVE_EXPOSURE_REMAINS"],
                "EXPOSURE_REDUCED_NOT_FLAT": ["POSITIVE_EXPOSURE_REMAINS"],
                "RESIDUAL_UNREPRESENTABLE_NOT_FLAT": [
                    "POSITIVE_EXPOSURE_REMAINS",
                    "RESIDUAL_NONZERO_UNREPRESENTABLE",
                ],
                "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED": [
                    "EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN"
                ],
                "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED": [
                    "TERMINAL_PROTECTION_OBJECT_PRESENT"
                ],
                "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED": [
                    "EXTERNAL_MANUAL_EXECUTION_OBSERVED",
                    "EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED",
                ],
                "OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED": ["FP04_OWNERSHIP_CONFLICT"],
            }.get(state, ["TERMINAL_PROTECTION_CLEAR"])
        if dispositions is None:
            dispositions = (
                [NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE]
                if state == "LIFECYCLE_CLOSE_ELIGIBLE"
                else ["BLOCK_NEW_EXPOSURE"]
            )
        return CloseConvergenceAssemblyInput(
            provider_position=provider_position,
            normalized_position_ref="normalized-position-001",
            normalized_position=position,
            execution_evidence=execution,
            fp04_dependencies=[FP04EvidenceDependency(fp04, fp04_currentness)],
            terminal_protection=terminal,
            lifecycle_projection_ref=projection["lifecycle_projection_id"],
            lifecycle_projection=projection,
            lifecycle_execution_binding_ref=binding["lifecycle_execution_binding_id"],
            lifecycle_execution_binding=binding,
            current_project_revision=self.revision,
            exposure_change_origin_classification=origin,
            convergence_state=state,
            required_dispositions=dispositions,
            reason_codes=reasons,
            evaluated_at=self.evaluated if evaluated is None else evaluated,
            fp05_close_residual_sizing_ref=fp05_ref,
            fp05_close_residual_sizing_hash=fp05_hash,
            fp05_residual_state=fp05_state,
            fp11_prior_registry_evidence_ref=fp11_ref,
            fp11_prior_registry_evidence_hash=fp11_hash,
            runtime_preflight_ref=None if runtime_config is None else "runtime-preflight-001",
            runtime_process_instance_id=None if runtime_config is None else "runtime-process-001",
            runtime_process_start_generation_id=None if runtime_config is None else "runtime-start-001",
            runtime_config_generation_id=runtime_config,
        )

    # FP-04

    def test_fp04_exact_current_known_owned_emits_only_accepted_success_tuple(self):
        evidence = self.fp04()
        validate_external_provider_ownership_evidence(evidence)
        self.assertEqual("KNOWN_OWNED_CURRENT_GENERATION", evidence["ownership_classification"])
        self.assertEqual("CURRENT_KNOWN_OWNED", evidence["reconciliation_status"])
        self.assertEqual(["NO_ACTION_CURRENT_KNOWN_OWNED"], evidence["required_dispositions"])
        self.assertEqual(["CURRENT_GENERATION_OWNERSHIP_PROVEN"], evidence["reason_codes"])
        self.assertTrue(
            external_provider_ownership_evidence_is_current(
                evidence,
                self.provider_object(),
                self.ownership_context(),
            )
        )

    def test_fp04_external_manual_preserves_external_classification_and_never_adopts(self):
        evidence = self.fp04(
            context=self.ownership_context(
                lineage_status=LINEAGE_EXTERNAL,
                lineage=[],
                registry=[],
            )
        )
        self.assertEqual("EXTERNAL_UNTRACKED", evidence["ownership_classification"])
        self.assertEqual("CONVERGENCE_REQUIRED", evidence["reconciliation_status"])
        self.assertIn("LIFECYCLE_REINTERPRETATION_REQUIRED", evidence["required_dispositions"])
        self.assertNotIn("NO_ACTION_CURRENT_KNOWN_OWNED", evidence["required_dispositions"])
        self.assertIsNone(evidence["adoption_decision_ref"])

    def test_fp04_prior_generation_cannot_become_current_generation_owned(self):
        evidence = self.fp04(
            context=self.ownership_context(
                lineage_status=LINEAGE_PRIOR_GENERATION,
                runtime_config="runtime-config-current",
            )
        )
        self.assertEqual("KNOWN_OWNED_PRIOR_GENERATION", evidence["ownership_classification"])
        self.assertEqual("RECONCILIATION_REQUIRED", evidence["reconciliation_status"])
        self.assertIn("FRESH_RECONCILIATION_REQUIRED", evidence["required_dispositions"])
        self.assertIn("PROVIDER_OBJECT_PRIOR_RUNTIME_GENERATION", evidence["reason_codes"])

    def test_fp04_contradictory_lineage_and_provider_binding_fail_closed(self):
        evidence = self.fp04(
            context=self.ownership_context(
                lineage_status=LINEAGE_CONFLICT,
                provider_binding=PROVIDER_BINDING_MISMATCH,
                lineage=[self.lineage(claim="CONTRADICTS_LINEAGE")],
            )
        )
        self.assertEqual("CONFLICTING_OWNERSHIP_EVIDENCE", evidence["ownership_classification"])
        self.assertEqual("RECONCILIATION_REQUIRED", evidence["reconciliation_status"])
        self.assertIn("LOCAL_LINEAGE_OWNERSHIP_CONFLICT", evidence["reason_codes"])
        self.assertIn("LINEAGE_PROVIDER_SNAPSHOT_MISMATCH", evidence["reason_codes"])

    def test_fp04_stale_registry_never_emits_current_known_owned(self):
        context = self.ownership_context(registry=[self.registry(currentness=STALE)])
        evidence = self.fp04(context=context)
        self.assertEqual("UNKNOWN", evidence["ownership_classification"])
        self.assertEqual("RECONCILIATION_REQUIRED", evidence["reconciliation_status"])
        self.assertIn("OWNERSHIP_EVIDENCE_STALE", evidence["reason_codes"])
        self.assertNotEqual(["NO_ACTION_CURRENT_KNOWN_OWNED"], evidence["required_dispositions"])

    def test_fp04_unknown_lineage_never_emits_current_known_owned(self):
        evidence = self.fp04(
            context=self.ownership_context(
                lineage_status=LINEAGE_UNKNOWN,
                lineage=[self.lineage(claim="UNKNOWN")],
            )
        )
        self.assertEqual("UNKNOWN", evidence["ownership_classification"])
        self.assertEqual("RECONCILIATION_REQUIRED", evidence["reconciliation_status"])

    def test_fp04_material_change_creates_new_id_supersession_and_invalidates_old_currentness(self):
        first_observation = self.provider_object()
        context = self.ownership_context()
        first = self.fp04(observation=first_observation, context=context)
        second_observation = self.provider_object(
            provider_snapshot_ref="provider-position-snapshot-002",
            provider_snapshot={
                "normalized_quantity": "0.001",
                "instId": "BTC-USDT-SWAP",
                "posSide": "net",
            },
            provider_observation_generation_id="provider-observation-gen-002",
        )
        second = self.fp04(
            observation=second_observation,
            context=context,
            supersedes=first,
        )
        self.assertNotEqual(first["ownership_evidence_id"], second["ownership_evidence_id"])
        self.assertEqual(first["ownership_evidence_id"], second["supersedes_ownership_evidence_id"])
        self.assertFalse(
            external_provider_ownership_evidence_is_current(first, second_observation, context)
        )

    def test_fp04_equivalent_mapping_order_is_deterministic(self):
        first = self.fp04()
        observation = self.provider_object(
            provider_identity={
                "api_version": "V5",
                "provider": "OKX",
                "environment": "production_observation_fixture",
            },
            provider_snapshot={
                "normalized_quantity": "0",
                "posSide": "net",
                "instId": "BTC-USDT-SWAP",
            },
        )
        lineage = dict(reversed(list(self.lineage().items())))
        registry = dict(reversed(list(self.registry().items())))
        second = self.fp04(
            observation=observation,
            context=self.ownership_context(lineage=[lineage], registry=[registry]),
        )
        self.assertEqual(first["ownership_evidence_id"], second["ownership_evidence_id"])
        self.assertEqual(first["provider_identity_hash"], second["provider_identity_hash"])
        self.assertEqual(first["provider_snapshot_hash"], second["provider_snapshot_hash"])

    def test_fp04_later_timestamp_alone_does_not_upgrade_stale_evidence(self):
        stale_context = self.ownership_context(registry=[self.registry(currentness=STALE)])
        first = self.fp04(context=stale_context)
        later = self.fp04(
            context=replace(stale_context, evaluated_at="2026-08-29T09:31:06Z"),
            supersedes=first,
        )
        self.assertEqual("UNKNOWN", first["ownership_classification"])
        self.assertEqual("UNKNOWN", later["ownership_classification"])
        self.assertEqual("RECONCILIATION_REQUIRED", later["reconciliation_status"])
        self.assertNotEqual(first["ownership_evidence_id"], later["ownership_evidence_id"])

    # FP-10

    def test_fp10_terminal_order_with_positive_position_cannot_be_close_eligible(self):
        position = self.position(quantity="0.001")
        with self.assertRaises(ExternalCloseEvidenceError):
            build_external_manual_close_convergence_evidence(
                self.assembly(position=position, state="LIFECYCLE_CLOSE_ELIGIBLE")
            )
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                position=position,
                state="EXPOSURE_REDUCED_NOT_FLAT",
                reasons=["POSITIVE_EXPOSURE_REMAINS", "TERMINAL_ORDER_WITHOUT_FLAT_POSITION_PROOF"],
            )
        )
        self.assertEqual("EXPOSURE_REDUCED_NOT_FLAT", evidence["convergence_state"])
        self.assertEqual("0.001", evidence["normalized_actual_quantity"])

    def test_fp10_manual_partial_reduction_remains_external_and_nonflat(self):
        position = self.position(quantity="0.0007", state="OPEN_PROTECTED")
        external_fp04 = self.fp04(
            context=self.ownership_context(
                lineage_status=LINEAGE_EXTERNAL,
                lineage=[],
                registry=[],
            )
        )
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                position=position,
                fp04=external_fp04,
                origin=EXTERNAL_MANUAL,
                state="EXPOSURE_REDUCED_NOT_FLAT",
                execution=[self.execution(origin="EXTERNAL_MANUAL", evidence_class="EXTERNAL_EXECUTION_OBSERVATION")],
                reasons=["POSITIVE_EXPOSURE_REMAINS", "EXTERNAL_MANUAL_EXECUTION_OBSERVED"],
            )
        )
        self.assertEqual("EXTERNAL_UNTRACKED", evidence["fp04_ownership_evidence"][0]["ownership_classification"])
        self.assertEqual(EXTERNAL_MANUAL, evidence["exposure_change_origin_classification"])
        self.assertNotEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])

    def test_fp10_positive_representable_residual_remains_nonflat(self):
        position = self.position(quantity="0.0003")
        fp05_ref = "fp05-sizing-001"
        fp05_hash = canonical_evidence_hash({"state": RESIDUAL_NONZERO_REPRESENTABLE})
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                position=position,
                fp05_state=RESIDUAL_NONZERO_REPRESENTABLE,
                fp05_ref=fp05_ref,
                fp05_hash=fp05_hash,
                state="EXPOSURE_REDUCED_NOT_FLAT",
                reasons=["POSITIVE_EXPOSURE_REMAINS", RESIDUAL_NONZERO_REPRESENTABLE],
            )
        )
        self.assertEqual("EXPOSURE_REDUCED_NOT_FLAT", evidence["convergence_state"])
        self.assertEqual(RESIDUAL_NONZERO_REPRESENTABLE, evidence["fp05_residual_state"])

    def test_fp10_positive_unrepresentable_residual_is_explicit_and_blocks_retry(self):
        position = self.position(quantity="0.0002")
        fp05_ref = "fp05-sizing-unrepresentable-001"
        fp05_hash = canonical_evidence_hash({"state": RESIDUAL_NONZERO_UNREPRESENTABLE})
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                position=position,
                fp05_state=RESIDUAL_NONZERO_UNREPRESENTABLE,
                fp05_ref=fp05_ref,
                fp05_hash=fp05_hash,
                state=RESIDUAL_UNREPRESENTABLE_NOT_FLAT,
                reasons=["POSITIVE_EXPOSURE_REMAINS", RESIDUAL_NONZERO_UNREPRESENTABLE],
                dispositions=["BLOCK_CLOSE_RETRY_MUTATION", "BLOCK_NEW_EXPOSURE", "FP05_RESIDUAL_REEVALUATION_REQUIRED"],
            )
        )
        self.assertEqual(RESIDUAL_UNREPRESENTABLE_NOT_FLAT, evidence["convergence_state"])
        self.assertIn("BLOCK_CLOSE_RETRY_MUTATION", evidence["required_dispositions"])

    def test_fp10_flat_position_with_execution_ambiguity_requires_reconciliation(self):
        execution = [
            self.execution(
                currentness="UNKNOWN",
                compatibility="UNKNOWN",
                evidence_class="AMBIGUOUS_OUTCOME_RECONCILIATION",
            )
        ]
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                execution=execution,
                state="FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
                reasons=["PRIOR_CLOSE_OUTCOME_RECONCILIATION_REQUIRED", "EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN"],
                dispositions=["BLOCK_CLOSE_RETRY_MUTATION", "EXECUTION_FILL_RECONCILIATION_REQUIRED"],
            )
        )
        self.assertEqual(
            "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
            evidence["convergence_state"],
        )
        self.assertIn("BLOCK_CLOSE_RETRY_MUTATION", evidence["required_dispositions"])

    def test_fp10_flat_position_with_nonconverged_terminal_protection_is_not_close_eligible(self):
        terminal = self.terminal_protection(
            status="TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED",
            payload={"coverage": "COMPLETE", "active_protection_count": 1},
        )
        evidence = build_external_manual_close_convergence_evidence(
            self.assembly(
                terminal=terminal,
                state="FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED",
                reasons=["TERMINAL_PROTECTION_OBJECT_PRESENT"],
                dispositions=["BLOCK_UNCERTAIN_PROTECTION_CLEANUP", "TERMINAL_PROTECTION_CONVERGENCE_REQUIRED"],
            )
        )
        self.assertEqual("FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED", evidence["convergence_state"])
        self.assertNotEqual([NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE], evidence["required_dispositions"])

    def test_fp10_exact_flat_current_compatible_chain_emits_consumable_close_eligible_evidence(self):
        assembly = self.assembly()
        evidence = build_external_manual_close_convergence_evidence(assembly)
        validate_external_manual_close_convergence_evidence(evidence)
        self.assertEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])
        self.assertEqual("0", evidence["normalized_actual_quantity"])
        self.assertEqual([NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE], evidence["required_dispositions"])
        self.assertEqual(["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"], evidence["reason_codes"])
        self.assertTrue(external_manual_close_convergence_evidence_is_current(evidence, assembly))

    def test_fp10_missing_or_mismatched_fp04_dependency_cannot_be_close_eligible(self):
        base = self.assembly()
        missing = replace(base, fp04_dependencies=[])
        with self.assertRaises(ExternalCloseEvidenceError):
            build_external_manual_close_convergence_evidence(missing)

        runtime_fp04 = self.fp04(
            context=self.ownership_context(runtime_config="runtime-config-001")
        )
        mismatched = replace(
            base,
            fp04_dependencies=[FP04EvidenceDependency(runtime_fp04, CURRENT)],
        )
        with self.assertRaises(ExternalCloseEvidenceError):
            build_external_manual_close_convergence_evidence(mismatched)

    def test_fp10_newer_provider_snapshot_generation_invalidates_old_evidence(self):
        assembly = self.assembly()
        evidence = build_external_manual_close_convergence_evidence(assembly)
        newer_provider = replace(
            assembly.provider_position,
            provider_position_snapshot_ref="provider-position-snapshot-002",
            provider_position_snapshot={
                "instId": "BTC-USDT-SWAP",
                "posSide": "net",
                "normalized_quantity": "0",
                "revision": 2,
            },
            provider_position_observation_generation_id="provider-position-gen-002",
        )
        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(assembly, provider_position=newer_provider),
            )
        )

    def test_fp10_newer_fp04_fp05_fp11_or_runtime_generation_invalidates_old_evidence(self):
        base = self.assembly()
        evidence = build_external_manual_close_convergence_evidence(base)

        newer_object = self.provider_object(
            provider_snapshot_ref="provider-position-snapshot-fp04-002",
            provider_snapshot={"instId": "BTC-USDT-SWAP", "normalized_quantity": "0", "revision": 2},
            provider_observation_generation_id="provider-observation-gen-fp04-002",
        )
        newer_fp04 = self.fp04(observation=newer_object, supersedes=self.fp04())
        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(base, fp04_dependencies=[FP04EvidenceDependency(newer_fp04, CURRENT)]),
            )
        )

        fp05_ref = "fp05-flat-002"
        fp05_hash = canonical_evidence_hash({"state": "EXPOSURE_ALREADY_FLAT", "generation": 2})
        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(
                    base,
                    fp05_close_residual_sizing_ref=fp05_ref,
                    fp05_close_residual_sizing_hash=fp05_hash,
                    fp05_residual_state="EXPOSURE_ALREADY_FLAT",
                ),
            )
        )

        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(
                    base,
                    fp11_prior_registry_evidence_ref="fp11-registry-002",
                    fp11_prior_registry_evidence_hash=canonical_evidence_hash({"generation": 2}),
                ),
            )
        )

        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(
                    base,
                    runtime_preflight_ref="runtime-preflight-002",
                    runtime_process_instance_id="runtime-process-002",
                    runtime_process_start_generation_id="runtime-start-002",
                    runtime_config_generation_id="runtime-config-002",
                ),
            )
        )

    def test_fp10_mapping_insertion_order_does_not_change_identity(self):
        first_assembly = self.assembly()
        first = build_external_manual_close_convergence_evidence(first_assembly)
        reordered_position = dict(reversed(list(first_assembly.normalized_position.items())))
        reordered_provider_identity = dict(
            reversed(list(first_assembly.provider_position.provider_identity.items()))
        )
        reordered_provider_snapshot = dict(
            reversed(list(first_assembly.provider_position.provider_position_snapshot.items()))
        )
        second_assembly = replace(
            first_assembly,
            normalized_position=reordered_position,
            provider_position=replace(
                first_assembly.provider_position,
                provider_identity=reordered_provider_identity,
                provider_position_snapshot=reordered_provider_snapshot,
            ),
        )
        second = build_external_manual_close_convergence_evidence(second_assembly)
        self.assertEqual(first["close_convergence_evidence_id"], second["close_convergence_evidence_id"])
        self.assertEqual(first["normalized_position_hash"], second["normalized_position_hash"])

    def test_fp10_supersession_is_explicit_and_immutable(self):
        first_assembly = self.assembly(
            state="FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
            execution=[self.execution(currentness="UNKNOWN", compatibility="UNKNOWN")],
            reasons=["EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN"],
            dispositions=["EXECUTION_FILL_RECONCILIATION_REQUIRED"],
        )
        first = build_external_manual_close_convergence_evidence(first_assembly)
        second = build_external_manual_close_convergence_evidence(
            self.assembly(),
            supersedes_evidence=first,
        )
        self.assertNotEqual(first["close_convergence_evidence_id"], second["close_convergence_evidence_id"])
        self.assertEqual(
            first["close_convergence_evidence_id"],
            second["supersedes_close_convergence_evidence_id"],
        )
        self.assertEqual(
            "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
            first["convergence_state"],
        )
        self.assertEqual("LIFECYCLE_CLOSE_ELIGIBLE", second["convergence_state"])

    def test_fp10_zero_provider_network_or_credentials_are_part_of_fixture_surface(self):
        evidence = build_external_manual_close_convergence_evidence(self.assembly())
        serialized = repr(evidence)
        for forbidden in (
            "api_key",
            "secret_key",
            "passphrase",
            "OK-ACCESS-SIGN",
            "x-simulated-trading",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
