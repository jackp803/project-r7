import unittest
from dataclasses import replace
from datetime import datetime, timedelta

from src.execution.external_close_binding import (
    build_external_manual_close_convergence_evidence,
    external_manual_close_convergence_evidence_is_current,
    validate_fp10_position_fp04_binding,
)
from src.execution.external_close_evidence import (
    CURRENT,
    FP04EvidenceDependency,
    LINEAGE_CURRENT_GENERATION,
    LINEAGE_EXTERNAL,
    MULTIPLICITY_SINGLE,
    NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE,
    PROVIDER_BINDING_EXACT,
    CloseConvergenceAssemblyInput,
    ExternalCloseEvidenceError,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    ProviderPositionObservation,
    TerminalProtectionObservation,
    build_external_provider_ownership_evidence,
    canonical_evidence_hash,
)
from src.position import (
    build_position_lifecycle_genesis_with_execution_binding,
    validate_external_manual_close_convergence_evidence,
)


class ExternalCloseExactPositionBindingTests(unittest.TestCase):
    def setUp(self):
        self.revision = "efcd3631ad069cd50afd22abbb9dd8028e23d9ac"
        self.observed = "2026-08-29T10:00:00Z"
        self.received = "2026-08-29T10:00:01Z"
        self.terminal_observed = "2026-08-29T10:00:02Z"
        self.terminal_received = "2026-08-29T10:00:03Z"
        self.evaluated = "2026-08-29T10:00:04Z"
        self.provider_generation = "provider-position-gen-exact-001"
        self.provider_ref = "provider-position-snapshot-exact-001"

    def position(self, *, quantity="0", state="EXIT_REQUESTED"):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp10-exact-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": quantity,
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T09:00:00Z",
            "broker_state_observed_at": self.observed,
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": state,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def identity(self):
        return {
            "provider": "OKX",
            "api_version": "V5",
            "environment": "sanitized-deterministic-fixture",
        }

    def provider_snapshot(self, quantity="0"):
        return {
            "instId": "BTC-USDT-SWAP",
            "posSide": "net",
            "normalized_quantity": quantity,
        }

    def lineage(self, *, claim="CLAIMS_OWNERSHIP"):
        return {
            "owner": "E4",
            "evidence_class": "POSITION_OBSERVATION_LINEAGE",
            "evidence_ref": "position-lineage-exact-001",
            "evidence_hash": canonical_evidence_hash({"position": "position-fp10-exact-001"}),
            "evidence_generation_id": self.provider_generation,
            "observed_or_created_at": self.received,
            "lineage_role": "POSITION",
            "claim_status": claim,
        }

    def registry(self):
        return {
            "owner": "E6",
            "evidence_class": "POSITION_REGISTRY",
            "evidence_ref": "position-registry-exact-001",
            "evidence_hash": canonical_evidence_hash({"position": "position-fp10-exact-001", "current": True}),
            "evidence_generation_id": self.provider_generation,
            "observed_at": self.received,
            "currentness_status": CURRENT,
        }

    def fp04(self, *, quantity="0", external=False, generation=None, snapshot_ref=None):
        generation = self.provider_generation if generation is None else generation
        snapshot_ref = self.provider_ref if snapshot_ref is None else snapshot_ref
        observation = ProviderObjectObservation(
            provider_object_class="POSITION_EXPOSURE",
            provider_identity_ref="provider-identity-exact-001",
            provider_identity=self.identity(),
            canonical_symbol="BTC_USDT_PERP",
            provider_instrument_ref="BTC-USDT-SWAP",
            provider_object_ref="provider-position-object-exact-001",
            provider_snapshot_ref=snapshot_ref,
            provider_snapshot=self.provider_snapshot(quantity),
            provider_observation_generation_id=generation,
            provider_observed_at=self.observed,
            provider_received_at=self.received,
        )
        context = OwnershipEvaluationContext(
            current_project_revision=self.revision,
            local_lineage_evidence=[] if external else [self.lineage()],
            local_registry_evidence=[] if external else [self.registry()],
            lineage_generation_status=LINEAGE_EXTERNAL if external else LINEAGE_CURRENT_GENERATION,
            provider_binding_status=PROVIDER_BINDING_EXACT,
            multiplicity_status=MULTIPLICITY_SINGLE,
            evaluated_at=self.evaluated,
        )
        return build_external_provider_ownership_evidence(observation, context)

    def assembly(self, *, position=None, fp04=None, state="LIFECYCLE_CLOSE_ELIGIBLE", origin="CURRENT_GENERATION_PROJECT"):
        position = self.position() if position is None else position
        projection_and_binding = build_position_lifecycle_genesis_with_execution_binding(
            position,
            lifecycle_state=position["lifecycle_state"],
            lifecycle_interpreted_at=datetime.fromisoformat(self.observed[:-1] + "+00:00") + timedelta(milliseconds=100),
            order_requests=[],
            order_results=[],
            fills=[],
        )
        fp04 = self.fp04(quantity=position["actual_quantity"]) if fp04 is None else fp04
        provider_position = ProviderPositionObservation(
            provider_identity_ref="provider-identity-exact-001",
            provider_identity=self.identity(),
            provider_instrument_ref="BTC-USDT-SWAP",
            provider_position_snapshot_ref=self.provider_ref,
            provider_position_snapshot=self.provider_snapshot(position["actual_quantity"]),
            provider_position_observation_generation_id=self.provider_generation,
            provider_position_observed_at=self.observed,
            provider_position_received_at=self.received,
            provider_position_currentness_status=CURRENT,
            position_id=position["position_id"],
            canonical_symbol=position["symbol"],
            position_side=position["side"],
            normalized_actual_quantity=position["actual_quantity"],
        )
        if state == "LIFECYCLE_CLOSE_ELIGIBLE":
            reasons = ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]
            dispositions = [NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE]
        elif state == "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED":
            reasons = [
                "EXTERNAL_MANUAL_EXECUTION_OBSERVED",
                "FP04_EXTERNAL_MANUAL_REINTERPRETATION_REQUIRED",
                "EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED",
            ]
            dispositions = ["BLOCK_NEW_EXPOSURE", "E5_LIFECYCLE_REINTERPRETATION_REQUIRED"]
        else:
            reasons = ["POSITIVE_EXPOSURE_REMAINS"]
            dispositions = ["BLOCK_NEW_EXPOSURE"]
        execution_origin = "EXTERNAL_MANUAL" if origin == "EXTERNAL_MANUAL" else "CURRENT_GENERATION_PROJECT"
        execution_class = "EXTERNAL_EXECUTION_OBSERVATION" if origin == "EXTERNAL_MANUAL" else "ORDER_RESULT_SET"
        execution = [
            {
                "owner": "E4",
                "evidence_class": execution_class,
                "evidence_ref": "execution-exact-001",
                "evidence_hash": canonical_evidence_hash({"execution": "exact", "origin": execution_origin}),
                "evidence_generation_id": "execution-exact-gen-001",
                "latest_observed_at": self.observed,
                "currentness_status": CURRENT,
                "position_compatibility_status": "COMPATIBLE",
                "lineage_origin": execution_origin,
            }
        ]
        return CloseConvergenceAssemblyInput(
            provider_position=provider_position,
            normalized_position_ref="normalized-position-exact-001",
            normalized_position=position,
            execution_evidence=execution,
            fp04_dependencies=[FP04EvidenceDependency(fp04, CURRENT)],
            terminal_protection=TerminalProtectionObservation(
                observation_ref="terminal-protection-exact-001",
                observation_payload={"coverage": "COMPLETE", "active_protection_count": 0},
                observed_at=self.terminal_observed,
                received_at=self.terminal_received,
                status="TERMINAL_PROTECTION_CLEAR",
            ),
            lifecycle_projection_ref=projection_and_binding.lifecycle_projection["lifecycle_projection_id"],
            lifecycle_projection=projection_and_binding.lifecycle_projection,
            lifecycle_execution_binding_ref=projection_and_binding.execution_binding["lifecycle_execution_binding_id"],
            lifecycle_execution_binding=projection_and_binding.execution_binding,
            current_project_revision=self.revision,
            exposure_change_origin_classification=origin,
            convergence_state=state,
            required_dispositions=dispositions,
            reason_codes=reasons,
            evaluated_at=self.evaluated,
        )

    def test_exact_fp04_position_snapshot_generation_is_required_and_consumable(self):
        assembly = self.assembly()
        bound = validate_fp10_position_fp04_binding(assembly)
        self.assertEqual("POSITION_EXPOSURE", bound["provider_object_class"])
        evidence = build_external_manual_close_convergence_evidence(assembly)
        validate_external_manual_close_convergence_evidence(evidence)
        self.assertEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])
        self.assertTrue(external_manual_close_convergence_evidence_is_current(evidence, assembly))

    def test_different_fp04_provider_snapshot_generation_is_rejected_before_fp10_assembly(self):
        mismatched = self.fp04(
            generation="provider-position-gen-other",
            snapshot_ref="provider-position-snapshot-other",
        )
        assembly = self.assembly(fp04=mismatched)
        with self.assertRaises(ExternalCloseEvidenceError) as caught:
            build_external_manual_close_convergence_evidence(assembly)
        self.assertEqual("FP10_POSITION_FP04_BINDING_MISSING", caught.exception.code)

    def test_missing_position_exposure_fp04_is_rejected_even_if_other_fp04_object_is_current(self):
        wrong = dict(self.fp04())
        wrong["provider_object_class"] = "TERMINAL_ORDER"
        # A changed shared evidence payload must have a new valid ID; the strict
        # binding check is intentionally earlier than generic FP-10 assembly.
        assembly = replace(
            self.assembly(),
            fp04_dependencies=[FP04EvidenceDependency(wrong, CURRENT)],
        )
        with self.assertRaises(ExternalCloseEvidenceError) as caught:
            validate_fp10_position_fp04_binding(assembly)
        self.assertEqual("FP10_POSITION_FP04_BINDING_MISSING", caught.exception.code)

    def test_external_manual_exact_position_binding_preserves_external_provenance(self):
        position = self.position(quantity="0", state="OPEN_PROTECTED")
        external_fp04 = self.fp04(quantity="0", external=True)
        assembly = self.assembly(
            position=position,
            fp04=external_fp04,
            state="EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED",
            origin="EXTERNAL_MANUAL",
        )
        evidence = build_external_manual_close_convergence_evidence(assembly)
        self.assertEqual("EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED", evidence["convergence_state"])
        self.assertEqual("EXTERNAL_UNTRACKED", evidence["fp04_ownership_evidence"][0]["ownership_classification"])
        self.assertNotEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])

    def test_newer_provider_position_generation_invalidates_prior_exact_binding_currentness(self):
        assembly = self.assembly()
        evidence = build_external_manual_close_convergence_evidence(assembly)
        newer_provider = replace(
            assembly.provider_position,
            provider_position_snapshot_ref="provider-position-snapshot-exact-002",
            provider_position_snapshot={
                "instId": "BTC-USDT-SWAP",
                "posSide": "net",
                "normalized_quantity": "0",
                "generation": 2,
            },
            provider_position_observation_generation_id="provider-position-gen-exact-002",
        )
        self.assertFalse(
            external_manual_close_convergence_evidence_is_current(
                evidence,
                replace(assembly, provider_position=newer_provider),
            )
        )


if __name__ == "__main__":
    unittest.main()
