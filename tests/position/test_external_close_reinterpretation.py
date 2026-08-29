import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

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
    external_close_reinterpretation_decision_is_current,
    external_provider_ownership_evidence_is_current,
    interpret_external_close_convergence,
    stable_external_close_convergence_evidence_id,
    stable_external_provider_ownership_evidence_id,
    validate_external_manual_close_convergence_evidence,
    validate_external_provider_ownership_evidence,
)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value):
    return "sha256:" + hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _dt(text):
    return datetime.fromisoformat(text[:-1] + "+00:00")


class ExternalCloseReinterpretationTests(unittest.TestCase):
    def setUp(self):
        self.revision = "0d4ac0aa4ffbac22a37c37ffdb404a7885fa445a"
        self.observed = "2026-08-29T08:00:00Z"
        self.received = "2026-08-29T08:00:01Z"
        self.terminal_observed = "2026-08-29T08:00:02Z"
        self.terminal_received = "2026-08-29T08:00:03Z"
        self.evaluated = "2026-08-29T08:00:04Z"

    def position(self, *, quantity="0", state="EXIT_REQUESTED", observed=None):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp10-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": quantity,
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T07:00:00Z",
            "broker_state_observed_at": observed or self.observed,
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": state,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def lifecycle(self, position):
        interpreted = _dt(position["broker_state_observed_at"]) + timedelta(seconds=1)
        outcome = build_position_lifecycle_genesis_with_execution_binding(
            position,
            lifecycle_state=position["lifecycle_state"],
            lifecycle_interpreted_at=interpreted,
            order_requests=[],
            order_results=[],
            fills=[],
        )
        return outcome.lifecycle_projection, outcome.execution_binding

    def fp04(self, *, external=False, snapshot="provider-position-snapshot-001", generation="provider-gen-001"):
        if external:
            ownership = "EXTERNAL_UNTRACKED"
            reconciliation = "CONVERGENCE_REQUIRED"
            dispositions = ["BLOCK_NEW_EXPOSURE", "LIFECYCLE_REINTERPRETATION_REQUIRED"]
            reasons = ["EXTERNAL_PROVIDER_OBJECT_UNTRACKED", "LIFECYCLE_REINTERPRETATION_REQUIRED"]
        else:
            ownership = "KNOWN_OWNED_CURRENT_GENERATION"
            reconciliation = "CURRENT_KNOWN_OWNED"
            dispositions = ["NO_ACTION_CURRENT_KNOWN_OWNED"]
            reasons = ["CURRENT_GENERATION_OWNERSHIP_PROVEN"]
        payload = {
            "schema_version": "contracts-v0.1",
            "external_provider_ownership_profile_version": "external-provider-object-ownership-reconciliation-v0.1",
            "provider_object_class": "POSITION_EXPOSURE",
            "provider_identity_ref": "provider-identity-001",
            "provider_identity_hash": _sha({"provider": "fixture"}),
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_ref": "BTC-USDT-SWAP",
            "provider_object_ref": "provider-position-001",
            "provider_snapshot_ref": snapshot,
            "provider_snapshot_hash": _sha({"snapshot": snapshot}),
            "provider_observation_generation_id": generation,
            "provider_observed_at": self.observed,
            "provider_received_at": self.received,
            "current_project_revision": self.revision,
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
            "evaluated_at": self.evaluated,
        }
        payload["ownership_evidence_id"] = stable_external_provider_ownership_evidence_id(payload)
        return payload

    def fp04_rows(self, evidence):
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
            for item in evidence
        ]
        return sorted(rows, key=lambda row: (row["provider_object_class"], row["provider_object_ref"], row["ownership_evidence_ref"]))

    def execution(self, *, currentness="CURRENT", compatibility="COMPATIBLE", origin="CURRENT_GENERATION_PROJECT"):
        return [
            {
                "owner": "E4",
                "evidence_class": "ORDER_RESULT_SET",
                "evidence_ref": "close-result-set-001",
                "evidence_hash": _sha({"terminal": "FILLED"}),
                "evidence_generation_id": "execution-gen-001",
                "latest_observed_at": self.observed,
                "currentness_status": currentness,
                "position_compatibility_status": compatibility,
                "lineage_origin": origin,
            }
        ]

    def authority(
        self,
        *,
        position=None,
        fp04=None,
        execution=None,
        fp05_state="NOT_APPLICABLE",
        terminal_status="TERMINAL_PROTECTION_CLEAR",
        runtime_config=None,
    ):
        position = self.position() if position is None else position
        projection, binding = self.lifecycle(position)
        fp04 = [self.fp04()] if fp04 is None else fp04
        execution = self.execution() if execution is None else execution
        return CurrentExternalCloseAuthority(
            normalized_position=position,
            normalized_position_ref="normalized-position-001",
            provider_identity_ref="provider-identity-001",
            provider_identity_hash=_sha({"provider": "fixture"}),
            provider_instrument_ref="BTC-USDT-SWAP",
            provider_position_snapshot_ref="provider-position-snapshot-001",
            provider_position_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-001"}),
            provider_position_observation_generation_id="provider-gen-001",
            provider_position_observed_at=self.observed,
            provider_position_received_at=self.received,
            execution_evidence_set_hash=_sha(execution),
            fp04_ownership_evidence=fp04,
            fp05_close_residual_sizing_ref=None,
            fp05_close_residual_sizing_hash=None,
            fp05_residual_state=fp05_state,
            terminal_protection_observation_ref="terminal-protection-set-001",
            terminal_protection_observation_hash=_sha({"terminal": "clear"}),
            terminal_protection_observed_at=self.terminal_observed,
            terminal_protection_received_at=self.terminal_received,
            terminal_protection_status=terminal_status,
            lifecycle_projection=projection,
            lifecycle_projection_ref=projection["lifecycle_projection_id"],
            lifecycle_execution_binding=binding,
            lifecycle_execution_binding_ref=binding["lifecycle_execution_binding_id"],
            current_project_revision=self.revision,
            runtime_preflight_ref=None,
            runtime_process_instance_id=None,
            runtime_process_start_generation_id=None,
            runtime_config_generation_id=runtime_config,
        )

    def evidence(
        self,
        authority,
        *,
        state="LIFECYCLE_CLOSE_ELIGIBLE",
        origin="CURRENT_GENERATION_PROJECT",
        execution=None,
        reasons=None,
        dispositions=None,
    ):
        p = authority.normalized_position
        projection = authority.lifecycle_projection
        binding = authority.lifecycle_execution_binding
        execution = self.execution() if execution is None else execution
        rows = self.fp04_rows(authority.fp04_ownership_evidence)
        if reasons is None:
            reasons = {
                "LIFECYCLE_CLOSE_ELIGIBLE": ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"],
                "EXPOSURE_STILL_OPEN": ["POSITIVE_EXPOSURE_REMAINS"],
                "EXPOSURE_REDUCED_NOT_FLAT": ["POSITIVE_EXPOSURE_REMAINS"],
                "RESIDUAL_UNREPRESENTABLE_NOT_FLAT": ["POSITIVE_EXPOSURE_REMAINS", "RESIDUAL_NONZERO_UNREPRESENTABLE"],
                "FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED": ["EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN"],
                "FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED": ["TERMINAL_PROTECTION_OBJECT_PRESENT"],
                "EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED": ["EXTERNAL_MANUAL_EXECUTION_OBSERVED", "EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED"],
                "FLAT_PROVIDER_TRUTH_PROVEN": ["TERMINAL_PROTECTION_CLEAR"],
            }.get(state, ["CONVERGENCE_EVIDENCE_SUPERSEDED"])
        if dispositions is None:
            dispositions = ["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"] if state == "LIFECYCLE_CLOSE_ELIGIBLE" else ["BLOCK_NEW_EXPOSURE"]
        payload = {
            "schema_version": "contracts-v0.1",
            "external_manual_close_convergence_profile_version": "external-manual-close-lifecycle-convergence-v0.1",
            "position_id": p["position_id"],
            "canonical_symbol": p["symbol"],
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
            "normalized_position_hash": _sha(p),
            "normalized_position_broker_state_observed_at": p["broker_state_observed_at"],
            "normalized_position_reconciliation_status": p["reconciliation_status"],
            "normalized_actual_quantity": p["actual_quantity"],
            "normalized_quantity_profile_version": p["quantity_profile_version"],
            "normalized_quantity_unit": p["quantity_unit"],
            "normalized_quantity_asset": p["quantity_asset"],
            "execution_evidence": execution,
            "execution_evidence_set_hash": _sha(execution),
            "fp04_ownership_evidence": rows,
            "fp04_evidence_set_hash": _sha(rows),
            "fp05_close_residual_sizing_ref": authority.fp05_close_residual_sizing_ref,
            "fp05_close_residual_sizing_hash": authority.fp05_close_residual_sizing_hash,
            "fp05_residual_state": authority.fp05_residual_state,
            "fp11_prior_registry_evidence_ref": None,
            "fp11_prior_registry_evidence_hash": None,
            "terminal_protection_observation_ref": authority.terminal_protection_observation_ref,
            "terminal_protection_observation_hash": authority.terminal_protection_observation_hash,
            "terminal_protection_observed_at": authority.terminal_protection_observed_at,
            "terminal_protection_received_at": authority.terminal_protection_received_at,
            "terminal_protection_status": authority.terminal_protection_status,
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
            "reason_codes": reasons,
            "supersedes_close_convergence_evidence_id": None,
            "evaluated_at": self.evaluated,
        }
        payload["close_convergence_evidence_id"] = stable_external_close_convergence_evidence_id(payload)
        return payload

    def test_fp04_identity_and_snapshot_currentness(self):
        fp04 = self.fp04()
        validate_external_provider_ownership_evidence(fp04)
        self.assertTrue(
            external_provider_ownership_evidence_is_current(
                fp04,
                provider_object_ref=fp04["provider_object_ref"],
                provider_snapshot_ref=fp04["provider_snapshot_ref"],
                provider_snapshot_hash=fp04["provider_snapshot_hash"],
                provider_observation_generation_id=fp04["provider_observation_generation_id"],
                current_project_revision=self.revision,
            )
        )
        self.assertFalse(
            external_provider_ownership_evidence_is_current(
                fp04,
                provider_object_ref=fp04["provider_object_ref"],
                provider_snapshot_ref="newer-snapshot",
                provider_snapshot_hash=_sha({"snapshot": "newer"}),
                provider_observation_generation_id="provider-gen-002",
                current_project_revision=self.revision,
            )
        )

    def test_terminal_close_order_but_position_positive_no_close(self):
        authority = self.authority(position=self.position(quantity="0.001", state="EXIT_REQUESTED"))
        ev = self.evidence(authority, state="EXPOSURE_REDUCED_NOT_FLAT")
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_RETAIN_OPEN, decision.decision)
        self.assertFalse(decision.close_eligible)
        self.assertNotEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_manual_partial_reduction_stays_open_and_does_not_adopt_lineage(self):
        authority = self.authority(
            position=self.position(quantity="0.0007", state="OPEN_PROTECTED"),
            fp04=[self.fp04(external=True)],
        )
        ev = self.evidence(authority, state="EXPOSURE_REDUCED_NOT_FLAT", origin="EXTERNAL_MANUAL")
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_REATTEST, decision.decision)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, decision.next_state)
        self.assertEqual("EXTERNAL_UNTRACKED", authority.fp04_ownership_evidence[0]["ownership_classification"])

    def test_representable_and_unrepresentable_positive_residuals_never_close(self):
        representable = self.authority(
            position=self.position(quantity="0.0003"),
            fp05_state="RESIDUAL_NONZERO_REPRESENTABLE",
        )
        ev = self.evidence(
            representable,
            state="EXPOSURE_REDUCED_NOT_FLAT",
            reasons=["POSITIVE_EXPOSURE_REMAINS", "RESIDUAL_NONZERO_REPRESENTABLE"],
        )
        self.assertFalse(interpret_external_close_convergence(ev, representable).close_eligible)

        unrepresentable = self.authority(
            position=self.position(quantity="0.00001"),
            fp05_state="RESIDUAL_NONZERO_UNREPRESENTABLE",
        )
        ev = self.evidence(unrepresentable, state="RESIDUAL_UNREPRESENTABLE_NOT_FLAT")
        decision = interpret_external_close_convergence(ev, unrepresentable)
        self.assertEqual(DECISION_HOLD_SAFE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_current_close_eligible_uses_existing_flat_close_transition(self):
        authority = self.authority(position=self.position(quantity="0", state="EXIT_REQUESTED"))
        ev = self.evidence(authority)
        validate_external_manual_close_convergence_evidence(ev)
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_CLOSE, decision.decision)
        self.assertEqual(PositionEvent.POSITION_CLOSED, decision.event)
        self.assertEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_reconciliation_required_close_eligible_uses_reconciled_flat(self):
        authority = self.authority(position=self.position(quantity="0", state="RECONCILIATION_REQUIRED"))
        ev = self.evidence(authority)
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(PositionEvent.RECONCILED_FLAT, decision.event)
        self.assertEqual(PositionLifecycleState.CLOSED, decision.next_state)

    def test_forged_close_eligible_with_positive_exposure_is_rejected(self):
        authority = self.authority(position=self.position(quantity="0.001"))
        ev = self.evidence(authority, state="EXPOSURE_STILL_OPEN")
        forged = dict(ev)
        forged["convergence_state"] = "LIFECYCLE_CLOSE_ELIGIBLE"
        forged["required_dispositions"] = ["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"]
        forged["reason_codes"] = ["LIFECYCLE_CLOSE_ELIGIBLE_PROVEN"]
        forged["close_convergence_evidence_id"] = stable_external_close_convergence_evidence_id(forged)
        with self.assertRaises(ExternalCloseReinterpretationError):
            validate_external_manual_close_convergence_evidence(forged)

    def test_positive_exposure_overrides_stale_local_closed_false_green(self):
        authority = self.authority(position=self.position(quantity="0.001", state="CLOSED"))
        ev = self.evidence(authority, state="EXPOSURE_STILL_OPEN")
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)
        self.assertFalse(decision.close_eligible)

    def test_flat_execution_fill_reconciliation_required_no_forced_close(self):
        execution = self.execution(currentness="UNKNOWN", compatibility="UNKNOWN")
        authority = self.authority(execution=execution)
        ev = self.evidence(
            authority,
            state="FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED",
            execution=execution,
        )
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_flat_nonconverged_terminal_protection_no_close(self):
        authority = self.authority(terminal_status="TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED")
        ev = self.evidence(authority, state="FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED")
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_external_manual_flat_requires_two_step_reinterpretation(self):
        authority = self.authority(fp04=[self.fp04(external=True)])
        ev = self.evidence(authority, state="EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED", origin="EXTERNAL_MANUAL")
        decision = interpret_external_close_convergence(ev, authority)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, decision.next_state)

    def test_newer_provider_fp04_lifecycle_and_runtime_truth_invalidate_old_fp10(self):
        authority = self.authority(runtime_config="cfg-001")
        ev = self.evidence(authority)

        newer_provider = replace(
            authority,
            provider_position_snapshot_ref="provider-position-snapshot-002",
            provider_position_snapshot_hash=_sha({"snapshot": "provider-position-snapshot-002"}),
            provider_position_observation_generation_id="provider-gen-002",
        )
        self.assertFalse(external_close_convergence_evidence_is_current(ev, newer_provider))

        newer_fp04 = replace(authority, fp04_ownership_evidence=[self.fp04(snapshot="provider-position-snapshot-002", generation="provider-gen-002")])
        self.assertFalse(external_close_convergence_evidence_is_current(ev, newer_fp04))

        newer_position = self.position(quantity="0", state="EXIT_REQUESTED", observed="2026-08-29T08:00:01Z")
        newer_projection, newer_binding = self.lifecycle(newer_position)
        newer_lifecycle = replace(
            authority,
            normalized_position=newer_position,
            lifecycle_projection=newer_projection,
            lifecycle_projection_ref=newer_projection["lifecycle_projection_id"],
            lifecycle_execution_binding=newer_binding,
            lifecycle_execution_binding_ref=newer_binding["lifecycle_execution_binding_id"],
        )
        self.assertFalse(external_close_convergence_evidence_is_current(ev, newer_lifecycle))
        self.assertFalse(external_close_convergence_evidence_is_current(ev, replace(authority, runtime_config_generation_id="cfg-002")))

    def test_newer_fp10_evidence_invalidates_prior_reinterpretation_decision(self):
        authority = self.authority()
        ev = self.evidence(authority)
        decision = interpret_external_close_convergence(ev, authority)
        newer = dict(ev)
        newer["evaluated_at"] = "2026-08-29T08:00:05Z"
        newer["supersedes_close_convergence_evidence_id"] = ev["close_convergence_evidence_id"]
        newer["close_convergence_evidence_id"] = stable_external_close_convergence_evidence_id(newer)
        self.assertFalse(external_close_reinterpretation_decision_is_current(decision, newer, authority))

    def test_missing_local_position_row_and_no_pending_order_are_not_flatness(self):
        authority = self.authority(position=self.position(quantity="0.001", state="OPEN_PROTECTED"), execution=[])
        ev = self.evidence(authority, state="EXPOSURE_STILL_OPEN", execution=[])
        self.assertEqual(DECISION_RETAIN_OPEN, interpret_external_close_convergence(ev, authority).decision)

        missing_position = replace(authority, normalized_position=None, normalized_position_ref=None)
        self.assertFalse(external_close_convergence_evidence_is_current(ev, missing_position))
        decision = interpret_external_close_convergence(ev, missing_position)
        self.assertEqual(DECISION_RECONCILE, decision.decision)
        self.assertFalse(decision.close_eligible)

    def test_trade_result_incomplete_never_fabricates_execution_lineage(self):
        authority = self.authority()
        ev = self.evidence(
            authority,
            state="FLAT_PROVIDER_TRUTH_PROVEN",
            reasons=["TRADE_RESULT_EVIDENCE_INCOMPLETE", "TERMINAL_PROTECTION_CLEAR"],
            dispositions=["TRADE_RESULT_EVIDENCE_INCOMPLETE"],
        )
        decision = interpret_external_close_convergence(ev, authority)
        self.assertTrue(decision.trade_result_evidence_incomplete)
        self.assertFalse(decision.close_eligible)
        self.assertEqual(DECISION_RECONCILE, decision.decision)

    def test_decision_identity_is_deterministic(self):
        authority = self.authority()
        ev = self.evidence(authority)
        one = interpret_external_close_convergence(ev, authority)
        two = interpret_external_close_convergence(ev, authority)
        self.assertEqual(one.decision_id, two.decision_id)


if __name__ == "__main__":
    unittest.main()
