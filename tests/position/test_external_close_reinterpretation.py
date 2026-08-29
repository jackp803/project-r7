import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from position import (
    CurrentExternalCloseAuthority,
    DECISION_CLOSE,
    DECISION_HOLD_SAFE,
    DECISION_REATTEST,
    DECISION_RECONCILE,
    DECISION_RETAIN_OPEN,
    ExternalCloseReinterpretationError,
    PositionEvent,
    PositionLifecycleState,
    build_position_lifecycle_genesis_with_execution_binding,
    external_close_convergence_evidence_is_current,
    interpret_external_close_convergence,
    stable_external_close_convergence_evidence_id,
    stable_external_provider_ownership_evidence_id,
    validate_external_manual_close_convergence_evidence,
    validate_external_provider_ownership_evidence,
)


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value):
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class ExternalCloseReinterpretationTests(unittest.TestCase):
    def setUp(self):
        self.project_revision = "0d4ac0aa4ffbac22a37c37ffdb404a7885fa445a"
        self.observed_at = "2026-08-29T08:00:00Z"
        self.received_at = "2026-08-29T08:00:01Z"
        self.terminal_observed_at = "2026-08-29T08:00:02Z"
        self.terminal_received_at = "2026-08-29T08:00:03Z"
        self.evaluated_at = "2026-08-29T08:00:04Z"

    def _position(self, *, quantity="0", lifecycle_state="EXIT_REQUESTED", observed_at=None):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-extclose-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": quantity,
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T07:00:00Z",
            "broker_state_observed_at": observed_at or self.observed_at,
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle_state,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _lifecycle(self, position):
        outcome = build_position_lifecycle_genesis_with_execution_binding(
            position,
            lifecycle_state=position["lifecycle_state"],
            lifecycle_interpreted_at=datetime(2026, 8, 29, 8, 0, 2, tzinfo=timezone.utc),
            order_requests=[],
            order_results=[],
            fills=[],
        )
        return outcome.lifecycle_projection, outcome.execution_binding

    def _fp04(
        self,
        *,
        provider_object_class="POSITION_EXPOSURE",
        provider_object_ref="provider-position-001",
        provider_snapshot_ref="provider-position-snapshot-001",
        provider_snapshot_hash=None,
        observation_generation="provider-gen-001",
        ownership="KNOWN_OWNED_CURRENT_GENERATION",
        reconciliation="CURRENT_KNOWN_OWNED",
        external=False,
    ):
        if external:
            ownership = "EXTERNAL_UNTRACKED"
            reconciliation = "CONVERGENCE_REQUIRED"
            dispositions = ["BLOCK_NEW_EXPOSURE", "LIFECYCLE_REINTERPRETATION_REQUIRED"]
            reasons = ["EXTERNAL_PROVIDER_OBJECT_UNTRACKED", "LIFECYCLE_REINTERPRETATION_REQUIRED"]
        else:
            dispositions = ["NO_ACTION_CURRENT_KNOWN_OWNED"]
            reasons = ["CURRENT_GENERATION_OWNERSHIP_PROVEN"]
        payload = {
            "schema_version": "contracts-v0.1",
            "external_provider_ownership_profile_version": "external-provider-object-ownership-reconciliation-v0.1",
            "provider_object_class": provider_object_class,
            "provider_identity_ref": "provider-identity-001",
            "provider_identity_hash": _sha({"provider": "fixture"}),
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_object_ref": provider_object_ref,
            "provider_snapshot_ref": provider_snapshot_ref,
            "provider_snapshot_hash": provider_snapshot_hash or _sha({"snapshot": provider_snapshot_ref}),
            "provider_observation_generation_id": observation_generation,
            "provider_observed_at": self.observed_at,
            "provider_received_at": self.received_at,
            "current_project_revision": self.project_revision,
            "runtime_preflight_ref": None,
            "runtime_process_instance_id": None,
            "runtime_process_start_generation_id": None,
            "runtime_config_generation_id": None,
            "local_lineage_evidence": [],
            "local_registry_evidence": [],
            "ownership_classification": ownership,
            "reconciliation_status": reconciliation,
            "required_dispositions": dispositions,
            "reason_codes": reasons,
            "adoption_decision_ref": None,
            "supersedes_ownership_evidence_id": None,
            "evaluated_at": self.evaluated_at,
        }
        payload["ownership_evidence_id"] = stable_external_provider_ownership_evidence_id(payload)
        return payload

    def _fp04_rows(self, items):
        rows = [
            {
                "provider_object_class": item["provider_object_class"],
                "provider_object_ref": item["provider_object_ref"],
                "provider_snapshot_hash": item["provider_snapshot_hash"],
                "ownership_evidence_ref": item["ownership_evidence_id"],
                "ownership_evidence_hash": _sha(item),
                "ownership_classification": item["ownership_classification"],
                "ownership_reconciliation_status": item["reconciliation_status"],
                "ownership_currentness_status": "CURRENT",
            }
            for item in items
        ]
        return sorted(rows, key=lambda row: (row["provider_object_class"], row["provider_object_ref"], row["ownership_evidence_ref"]))

    def _execution(self, *, compatibility="COMPATIBLE", currentness="CURRENT", lineage_origin="CURRENT_GENERATION_PROJECT"):
        return [
            {
                "owner": "E4",
                "evidence_class": "ORDER_RESULT_SET",
                "evidence_ref": "close-results-001",
                "evidence_hash": _sha({"order_status": "FILLED"}),
                "evidence_generation_id": "execution-gen-001",
                "latest_observed_at": self.observed_at,
                "currentness_status": currentness,
                "position_compatibility_status": compatibility,
                "lineage_origin": lineage_origin,
            }
        ]

    def _authority(
        self,
        *,
        position=None,
        fp04=None,
        execution_evidence=None,
        fp05_state="NOT_APPLICABLE",
        terminal_status="TERMINAL_PROTECTION_CLEAR",
        project_revision=None,
        runtime_config_generation_id=None,
    ):
        position = self._position() if position is None else position
        projection = binding = None
        if position is not None:
            projection, binding = self._lifecycle(position)
        fp04 = [self._fp04()] if fp04 is None else fp04
        execution_evidence = self._execution() if execution_evidence is None else execution_evidence
        return CurrentExternalCloseAuthority(
            normalized_position=position,
            normalized_position_ref=None if position is None else "normalized-position-001",
            provider_identity_ref="provider-identity-001",
            provider_identity_hash=_sha({"provider": "fixture"}),
            provider_instrument_ref="BTC-USDT-SWAP",
            provider_position_snapshot_ref="provider-position-snapshot-001",
            provider_position_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-001"}),
            provider_position_observation_generation_id="provider-gen-001",
            provider_position_observed_at=self.observed_at,
            provider_position_received_at=self.received_at,
            execution_evidence_set_hash=_sha(execution_evidence),
            fp04_ownership_evidence=fp04,
            fp05_close_residual_sizing_ref=None,
            fp05_close_residual_sizing_hash=None,
            fp05_residual_state=fp05_state,
            terminal_protection_observation_ref="terminal-protection-set-001",
            terminal_protection_observation_hash=_sha({"terminal": "clear"}),
            terminal_protection_observed_at=self.terminal_observed_at,
            terminal_protection_received_at=self.terminal_received_at,
            terminal_protection_status=terminal_status,
            lifecycle_projection=projection,
            lifecycle_projection_ref=None if projection is None else projection["lifecycle_projection_id"],
            lifecycle_execution_binding=binding,
            lifecycle_execution_binding_ref=None if binding is None else binding["lifecycle_execution_binding_id"],
            current_project_revision=project_revision or self.project_revision,
            runtime_preflight_ref=None,
            runtime_process_instance_id=None,
            runtime_process_start_generation_id=None,
            runtime_config_generation_id=runtime_config_generation_id,
        )

    def _evidence(
        self,
        *,
        authority=None,
        state="LIFECYCLE_CLOSE_ELIGIBLE",
        origin="CURRENT_GENERATION_PROJECT",
        execution_evidence=None,
        reason_codes=None,
        dispositions=None,
        fp05_state=None,
    ):
        authority = self._authority() if authority is None else authority
        position = authority.normalized_position
        self.assertIsNotNone(position)
        projection = authority.lifecycle_projection
        binding = authority.lifecycle_execution_binding
        self.assertIsNotNone(projection)
        self.assertIsNotNone(binding)
        execution_evidence = self._execution() if execution_evidence is None else execution_evidence
        rows = self._fp04_rows(authority.fp04_ownership_evidence)
        if reason_codes is None:
            if state == "LIFECYCLE_CLOSE_ELIGIBLE":
                reason_codes = ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]
            elif state == "RESIDUAL_UNREPRESENTABLE_NOT_FLAT":
                reason_codes = ["POSITIVE_EXPOSURE_REMAINS", "RESIDUAL_NONZERO_UNREPRESENTABLE"]
            elif state in {"EXPOSURE_REDUCED_NOT_FLAT", "EXPOSURE_STILL_OPEN"}:
                reason_codes = ["POSITIVE_EXPOSURE_REMAINS"]
            elif state == "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED":
                reason_codes = ["EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN"]
            elif state == "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED":
                reason_codes = ["TERMINAL_PROTECTION_OBJECT_PRESENT"]
            elif state == "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED":
                reason_codes = ["EXTERNAL_MANUAL_EXECUTION_OBSERVED", "EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED"]
            elif state == "FLAT_PROVIDER_TRUTH_PROVEN":
                reason_codes = ["TERMINAL_PROTECTION_CLEAR"]
            else:
                reason_codes = ["CONVERGENCE_EVIDENCE_SUPERSEDED"]
        if dispositions is None:
            dispositions = (
                ["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"]
                if state == "LIFECYCLE_CLOSE_ELIGIBLE"
                else ["BLOCK_NEW_EXPOSURE"]
            )
        terminal_status = authority.terminal_protection_status
        payload = {
            "schema_version": "contracts-v0.1",
            "external_manual_close_convergence_profile_version": "external-manual-close-lifecycle-convergence-v0.1",
            "position_id": position["position_id"],
            "canonical_symbol": position["symbol"],
            "provider_identity_ref": authority.provider_identity_ref,
            "provider_identity_hash": authority.provider_identity_hash,
            "provider_instrument_ref": authority.provider_instrument_ref,
            "provider_position_snapshot_ref": authority.provider_position_snapshot_ref,
            "provider_position_snapshot_hash": authority.provider_position_snapshot_hash,
            "provider_position_observation_generation_id": authority.provider_position_observation_generation_id,
            "provider_position_observed_at": authority.provider_position_observed_at,
            "provider_position_received_at": authority.provider_position_received_at,
            "provider_position_currentness_status": "CURRENT",
            "normalized_position_ref": authority.normalized_position_ref,
            "normalized_position_hash": _sha(position),
            "normalized_position_broker_state_observed_at": position["broker_state_observed_at"],
            "normalized_position_reconciliation_status": position["reconciliation_status"],
            "normalized_actual_quantity": position["actual_quantity"],
            "normalized_quantity_profile_version": position["quantity_profile_version"],
            "normalized_quantity_unit": position["quantity_unit"],
            "normalized_quantity_asset": position["quantity_asset"],
            "execution_evidence": execution_evidence,
            "execution_evidence_set_hash": _sha(execution_evidence),
            "fp04_ownership_evidence": rows,
            "fp04_evidence_set_hash": _sha(rows),
            "fp05_close_residual_sizing_ref": authority.fp05_close_residual_sizing_ref,
            "fp05_close_residual_sizing_hash": authority.fp05_close_residual_sizing_hash,
            "fp05_residual_state": authority.fp05_residual_state if fp05_state is None else fp05_state,
            "fp11_prior_registry_evidence_ref": None,
            "fp11_prior_registry_evidence_hash": None,
            "terminal_protection_observation_ref": authority.terminal_protection_observation_ref,
            "terminal_protection_observation_hash": authority.terminal_protection_observation_hash,
            "terminal_protection_observed_at": authority.terminal_protection_observed_at,
            "terminal_protection_received_at": authority.terminal_protection_received_at,
            "terminal_protection_status": terminal_status,
            "lifecycle_projection_ref": authority.lifecycle_projection_ref,
            "lifecycle_projection_hash": _sha(projection),
            "lifecycle_projection_id": projection["lifecycle_projection_id"],
            "lifecycle_revision": projection["lifecycle_revision"],
            "lifecycle_state": projection["lifecycle_state"],
            "lifecycle_execution_binding_ref": authority.lifecycle_execution_binding_ref,
            "lifecycle_execution_binding_hash": _sha(binding),
            "lifecycle_execution_snapshot_hash": binding["execution_snapshot_hash"],
            "current_project_revision": authority.current_project_revision,
            "runtime_preflight_ref": authority.runtime_preflight_ref,
            "runtime_process_instance_id": authority.runtime_process_instance_id,
            "runtime_process_start_generation_id": authority.runtime_process_start_generation_id,
            "runtime_config_generation_id": authority.runtime_config_generation_id,
            "exposure_change_origin_classification": origin,
            "convergence_state": state,
            "required_dispositions": dispositions,
            "reason_codes": reason_codes,
            "supersedes_close_convergence_evidence_id": None,
            "evaluated_at": self.evaluated_at,
        }
        payload["close_convergence_evidence_id"] = stable_external_close_convergence_evidence_id(payload)
        return payload

    def test_fp04_current_known_owned_identity_is_valid(self):
        evidence = self._fp04()
        validate_external_provider_ownership_evidence(evidence)
        self.assertTrue(evidence["ownership_evidence_id"].startswith("extownrec_"))

    def test_terminal_close_order_but_position_positive_never_closes(self):
        position = self._position(quantity="0.0010", lifecycle_state="EXIT_REQUESTED")
        authority = self._authority(position=position)
        evidence = self._evidence(authority=authority, state="EXPOSURE_REDUCED_NOT_FLAT")
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_RETAIN_OPEN, decision.decision)
        self.assertNotEqual(PositionLifecycleState.CLOSED, decision.next_state)
        self.assertFalse(decision.close_eligible)

    def test_manual_partial_reduction_reinterprets_open_not_closed(self):
        position = self._position(quantity="0.0007", lifecycle_state="OPEN_PROTECTED")
        fp04 = [self._fp04(external=True)]
        authority = self._authority(position=position, fp04=fp04)
        evidence = self._evidence(
            authority=authority,
            state="EXPOSURE_REDUCED_NOT_FLAT",
            origin="EXTERNAL_MANUAL",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_REATTEST, decision.decision)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, decision.next_state)
        self.assertIsNone(decision.event)

    def test_positive_representable_residual_never_closes(self):
        position = self._position(quantity="0.0003", lifecycle_state="EXIT_REQUESTED")
        authority = self._authority(position=position, fp05_state="RESIDUAL_NONZERO_REPRESENTABLE")
        evidence = self._evidence(
            authority=authority,
            state="EXPOSURE_REDUCED_NOT_FLAT",
            fp05_state="RESIDUAL_NONZERO_REPRESENTABLE",
            reason_codes=["POSITIVE_EXPOSURE_REMAINS", "RESIDUAL_NONZERO_REPRESENTABLE"],
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertFalse(decision.close_eligible)
        self.assertNotEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_positive_unrepresentable_residual_is_explicit_fail_closed_nonflat(self):
        position = self._position(quantity="0.00001", lifecycle_state="EXIT_REQUESTED")
        authority = self._authority(position=position, fp05_state="RESIDUAL_NONZERO_UNREPRESENTABLE")
        evidence = self._evidence(
            authority=authority,
            state="RESIDUAL_UNREPRESENTABLE_NOT_FLAT",
            fp05_state="RESIDUAL_NONZERO_UNREPRESENTABLE",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_HOLD_SAFE, decision.decision)
        self.assertFalse(decision.close_eligible)
        self.assertIn("E5_POSITIVE_UNREPRESENTABLE_RESIDUAL_FAIL_CLOSED", decision.reason_codes)

    def test_current_close_eligible_exit_requested_uses_existing_position_closed_transition(self):
        authority = self._authority(position=self._position(quantity="0", lifecycle_state="EXIT_REQUESTED"))
        evidence = self._evidence(authority=authority)
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_CLOSE, decision.decision)
        self.assertEqual(PositionEvent.POSITION_CLOSED, decision.event)
        self.assertEqual(PositionLifecycleState.CLOSED, decision.next_state)
        self.assertTrue(decision.close_eligible)

    def test_current_close_eligible_reconciliation_uses_reconciled_flat_transition(self):
        authority = self._authority(position=self._position(quantity="0", lifecycle_state="RECONCILIATION_REQUIRED"))
        evidence = self._evidence(authority=authority)
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(PositionEvent.RECONCILED_FLAT, decision.event)
        self.assertEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_positive_quantity_forged_as_close_eligible_is_rejected_structurally(self):
        authority = self._authority(position=self._position(quantity="0.001", lifecycle_state="EXIT_REQUESTED"))
        evidence = self._evidence(
            authority=authority,
            state="EXPOSURE_REDUCED_NOT_FLAT",
        )
        forged = dict(evidence)
        forged["convergence_state"] = "LIFECYCLE_CLOSE_ELIGIBLE"
        forged["required_dispositions"] = ["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"]
        forged["reason_codes"] = ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]
        forged["close_convergence_evidence_id"] = stable_external_close_convergence_evidence_id(forged)
        with self.assertRaises(ExternalCloseReinterpretationError) as caught:
            validate_external_manual_close_convergence_evidence(forged)
        self.assertEqual("FP10_FALSE_FLAT", caught.exception.code)

    def test_flat_provider_truth_with_execution_reconciliation_does_not_force_close(self):
        execution = self._execution(compatibility="UNKNOWN", currentness="UNKNOWN")
        authority = self._authority(execution_evidence=execution)
        evidence = self._evidence(
            authority=authority,
            execution_evidence=execution,
            state="FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)
        self.assertNotEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_flat_with_nonconverged_terminal_protection_does_not_close(self):
        authority = self._authority(terminal_status="TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED")
        evidence = self._evidence(
            authority=authority,
            state="FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_external_manual_flat_uses_two_step_reinterpretation_not_silent_lineage_adoption(self):
        fp04 = [self._fp04(external=True)]
        authority = self._authority(fp04=fp04)
        evidence = self._evidence(
            authority=authority,
            state="EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED",
            origin="EXTERNAL_MANUAL",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertEqual("EXTERNAL_UNTRACKED", fp04[0]["ownership_classification"])

    def test_stale_or_mismatched_fp04_evidence_fails_currentness(self):
        authority = self._authority()
        evidence = self._evidence(authority=authority)
        newer_fp04 = [
            self._fp04(
                provider_snapshot_ref="provider-position-snapshot-002",
                provider_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-002"}),
                observation_generation="provider-gen-002",
            )
        ]
        newer_authority = replace(authority, fp04_ownership_evidence=newer_fp04)
        self.assertFalse(external_close_convergence_evidence_is_current(evidence, newer_authority))
        decision = interpret_external_close_convergence(evidence, newer_authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_newer_provider_position_truth_invalidates_prior_decision(self):
        authority = self._authority()
        evidence = self._evidence(authority=authority)
        newer = replace(
            authority,
            provider_position_snapshot_ref="provider-position-snapshot-002",
            provider_position_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-002"}),
            provider_position_observation_generation_id="provider-gen-002",
        )
        self.assertFalse(external_close_convergence_evidence_is_current(evidence, newer))

    def test_newer_lifecycle_truth_invalidates_prior_decision(self):
        authority = self._authority()
        evidence = self._evidence(authority=authority)
        new_position = dict(authority.normalized_position)
        new_position["broker_state_observed_at"] = "2026-08-29T08:00:05Z"
        newer_projection, newer_binding = self._lifecycle(new_position)
        newer = replace(
            authority,
            normalized_position=new_position,
            lifecycle_projection=newer_projection,
            lifecycle_projection_ref=newer_projection["lifecycle_projection_id"],
            lifecycle_execution_binding=newer_binding,
            lifecycle_execution_binding_ref=newer_binding["lifecycle_execution_binding_id"],
        )
        self.assertFalse(external_close_convergence_evidence_is_current(evidence, newer))

    def test_runtime_config_generation_change_invalidates_prior_decision(self):
        authority = self._authority(runtime_config_generation_id="cfg-001")
        evidence = self._evidence(authority=authority)
        newer = replace(authority, runtime_config_generation_id="cfg-002")
        self.assertFalse(external_close_convergence_evidence_is_current(evidence, newer))

    def test_missing_local_position_row_is_never_flat(self):
        full = self._authority()
        evidence = self._evidence(authority=full)
        missing = replace(
            full,
            normalized_position=None,
            normalized_position_ref=None,
            lifecycle_projection=None,
            lifecycle_projection_ref=None,
            lifecycle_execution_binding=None,
            lifecycle_execution_binding_ref=None,
        )
        self.assertFalse(external_close_convergence_evidence_is_current(evidence, missing))

    def test_no_pending_order_is_not_flatness_authority(self):
        position = self._position(quantity="0.001", lifecycle_state="OPEN_PROTECTED")
        authority = self._authority(position=position, execution_evidence=[])
        evidence = self._evidence(
            authority=authority,
            execution_evidence=[],
            state="EXPOSURE_STILL_OPEN",
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(DECISION_RETAIN_OPEN, decision.decision)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, decision.next_state)

    def test_trade_result_incomplete_does_not_fabricate_execution_lineage_or_force_close(self):
        authority = self._authority()
        evidence = self._evidence(
            authority=authority,
            state="FLAT_PROVIDER_TRUTH_PROVEN",
            reason_codes=["TRADE_RESULT_EVIDENCE_INCOMPLETE", "TERMINAL_PROTECTION_CLEAR"],
            dispositions=["TRADE_RESULT_EVIDENCE_INCOMPLETE"],
        )
        decision = interpret_external_close_convergence(evidence, authority)
        self.assertTrue(decision.trade_result_evidence_incomplete)
        self.assertFalse(decision.close_eligible)
        self.assertEqual(DECISION_RECONCILE, decision.decision)

    def test_same_exact_input_has_stable_decision_identity_and_material_change_changes_it(self):
        authority = self._authority()
        evidence = self._evidence(authority=authority)
        first = interpret_external_close_convergence(evidence, authority)
        second = interpret_external_close_convergence(evidence, authority)
        self.assertEqual(first.decision_id, second.decision_id)

        newer = replace(
            authority,
            provider_position_snapshot_ref="provider-position-snapshot-002",
            provider_position_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-002"}),
            provider_position_observation_generation_id="provider-gen-002",
        )
        changed = interpret_external_close_convergence(evidence, newer)
        self.assertNotEqual(first.decision_id, changed.decision_id)


if __name__ == "__main__":
    unittest.main()
