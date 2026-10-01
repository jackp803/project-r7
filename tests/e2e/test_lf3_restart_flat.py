"""Compose durable flat recovery, fresh fake observations, E5 and FP16.

All provider messages and authorizations are synthetic fixtures. No process or
network transport is launched; the composition exports hypothetical evidence.
"""
import unittest
from dataclasses import replace
from datetime import timedelta

from integration import ShadowComposition
from integration.runtime_preflight import ELIGIBLE, FAIL_CLOSED, evaluate_runtime_preflight
from storage import open_operational_mode_store
from storage.runtime import open_paper_runtime_journal
import tests.integration.test_gate_c_shadow_composition as observation_fixtures
import tests.integration.test_runtime_preflight as preflight_fixtures
import tests.storage.test_paper_runtime_durability as durable_fixtures


def _utc(value):
    return value.isoformat().replace("+00:00", "Z")


class LF3RestartFlatCompositionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = durable_fixtures.PaperRuntimeDurabilityDefinitions()
        self.fixture.setUp()
        self.preflight = preflight_fixtures.RuntimePreflightV01Tests()
        self.preflight.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def _evaluate_restored_preflight(self, store):
        restored = store.recover()
        mode = restored.current_mode
        checkpoint = restored.last_shadow_checkpoint
        now = observation_fixtures.NOW
        reconciliation = self.preflight._reconciliation(
            reconciliation_ref="lf3-no-fresh-flat" if checkpoint is None else checkpoint.checkpoint_id,
            reconciliation_hash=self.preflight.reconciliation_hash if checkpoint is None else checkpoint.payload_hash,
            reconciliation_generation_id="lf3-unreconciled" if checkpoint is None else checkpoint.checkpoint_id,
            reconciliation_observed_at=_utc(now) if checkpoint is None else checkpoint.observed_at,
            reconciliation_status="READY" if restored.shadow_planning_safe else "NOT_READY",
            fresh_reconciliation_required=restored.fresh_reconciliation_required,
        )
        value = self.preflight._input(
            role="SHADOW_RUNTIME", launch_intent="RESTART", mode=mode.mode,
            evaluated_at=_utc(now + timedelta(seconds=1)),
            process_started_at=_utc(now - timedelta(seconds=1)),
            operational_mode_transition_id=mode.transition_id,
            operational_mode_revision=mode.mode_revision,
            operational_mode_payload_hash=mode.payload_hash,
            heartbeat_evidence=self.preflight._heartbeat(heartbeat_observed_at=_utc(now), heartbeat_received_at=_utc(now)),
            reconciliation_evidence=reconciliation,
            dependencies=[self.preflight._dependency(observed_at=_utc(now), readiness_status="READY" if restored.shadow_planning_safe else "NOT_READY")],
            external_consumer=self.preflight._external_consumer(compatibility_observed_at=_utc(now)),
        )
        authority = replace(self.preflight._authority(value),
            operational_mode_authority={"transition_id": mode.transition_id, "mode_revision": mode.mode_revision, "mode": mode.mode, "payload_hash": mode.payload_hash},
            reconciliation_authority={key: reconciliation[key] for key in ("reconciliation_ref", "reconciliation_hash", "reconciliation_generation_id")},
        )
        return evaluate_runtime_preflight(value, authority)

    def test_restored_flat_requires_fresh_reconciliation_and_new_positive_exposure_invalidates_it(self):
        graph = self.fixture._persist_closed_graph()
        store = open_operational_mode_store(self.fixture.db_path)
        observation_fixtures._enter_shadow(store)
        store.close()
        self.fixture.journal.close()
        self.fixture.journal = open_paper_runtime_journal(self.fixture.db_path)
        recovered = self.fixture.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("READY", recovered.status)
        self.assertEqual(graph["closed"], recovered.current_position_projection.payload)
        self.assertEqual("0", recovered.current_position_projection.payload["actual_quantity"])
        self.assertEqual(graph["binding"], recovered.current_lifecycle_execution_binding.payload)

        store = open_operational_mode_store(self.fixture.db_path)
        try:
            self.assertTrue(store.recover().fresh_reconciliation_required)
            before = self._evaluate_restored_preflight(store)
            self.assertEqual(FAIL_CLOSED, before["preflight_status"])
            self.assertIn("PREFLIGHT_RECONCILIATION_NOT_READY", before["reason_codes"])
            transport = observation_fixtures._Transport(observation_fixtures._responses())
            composition = ShadowComposition(mode_store=store, provider_reader=observation_fixtures._reader(transport))
            snapshot, candles = observation_fixtures._market_inputs()
            fresh = observation_fixtures._run(composition, snapshot, candles)
            self.assertTrue(fresh.ready_for_hypothetical_new_exposure)
            self.assertEqual("APPROVE", fresh.planning_evidence.risk_decision)
            self.assertFalse(fresh.planning_evidence.provider_submit_reachable)
            self.assertFalse(fresh.planning_evidence.provider_mutation_reachable)
            checkpoint = store.recover().last_shadow_checkpoint
            self.assertEqual(fresh.shadow_checkpoint_id, checkpoint.checkpoint_id)
            self.assertEqual(fresh.provider_observation_ref, checkpoint.provider_observation_ref)
            self.assertTrue(checkpoint.payload["position_truth_known"])
            self.assertFalse(checkpoint.payload["unexpected_exposure"])
            self.assertEqual(ELIGIBLE, self._evaluate_restored_preflight(store)["preflight_status"])
            self.assertTrue(all(request.method == "GET" for request in transport.requests))
        finally:
            store.close()

        # Another restart retains the old flat graph/checkpoint, but fresh
        # authoritative positive exposure must prevent any new-exposure claim.
        store = open_operational_mode_store(self.fixture.db_path)
        try:
            self.assertTrue(store.recover().fresh_reconciliation_required)
            responses = observation_fixtures._responses()
            responses[observation_fixtures.POSITIONS] = {"code": "0", "data": [{
                "instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "posSide": "net", "pos": "0.001",
            }]}
            transport = observation_fixtures._Transport(responses)
            composition = ShadowComposition(mode_store=store, provider_reader=observation_fixtures._reader(transport))
            rejected = observation_fixtures._run(composition, snapshot, candles)
            self.assertFalse(rejected.ready_for_hypothetical_new_exposure)
            self.assertFalse(rejected.provider_read_healthy)
            self.assertIsNone(rejected.shadow_checkpoint_id)
            self.assertIn("GATE_C_SHADOW_POSITION_UNSAFE", rejected.reason_codes)
            self.assertIn("NEW_EXPOSURE_DISABLED", rejected.reason_codes)
            self.assertEqual("REJECT", rejected.planning_evidence.risk_decision)
            self.assertFalse(store.recover().shadow_planning_safe)
            self.assertEqual(FAIL_CLOSED, self._evaluate_restored_preflight(store)["preflight_status"])
            self.assertEqual(graph["closed"], self.fixture.journal.recover(position_id="position-e6-paper-001").current_position_projection.payload)
            self.assertTrue(all(request.method == "GET" for request in transport.requests))
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
