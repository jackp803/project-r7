"""Actual canonical commit failure and fresh-process replay helpers.

Non-TestCase mixin. Apply as tests/product/trading_finalization_recovery_fixtures.py
Actual owner writes commit before scoped injected I/O
failure; no SQL financial mutation, mocked risk result or old-read replay.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

import tests.product.trading_finalization_fixtures as finalization_fixtures
import tests.integration.test_runtime_preflight as preflight_fixtures
from application.trading.admission import RuntimeAdmission
from application.trading.service import TradingService
from application.trading.provider import FakeProductProvider
from brokers.okx_product_capability import OKXProductCapabilityOwner
from brokers.okx_product import OKXProductTranslator
from registry.operational_authority import stamp
from storage.product_dispatch import open_product_dispatch_journal
from storage.runtime import PaperRuntimeJournal, open_paper_runtime_journal
from storage.product_finalization import claim_snapshot


class FinalizationRecoveryFixture(finalization_fixtures.FinalizationFixture):
    # No unittest.TestCase ancestry here; modules expose exactly one own case.
    def successor(self, label):
        self.fixture.clock[0] += timedelta(seconds=1)
        started = self.fixture.clock[0]
        instance = 'process-fixture-finalization-successor-' + label

        def current_preflight():
            base = preflight_fixtures.RuntimePreflightV01Tests(); base.setUp()
            release = self.fixture.release[0]
            base.revision = release.executable_revision
            base.config_hash = release.config_hash
            base.capability_hash = release.capability_hash
            base.authorization_capability_hash = release.capability_hash
            value = base._input(role='PAPER_RUNTIME')
            now = self.fixture.clock[0]
            runtime_generation = 'runtime-generation:' + str(release.runtime_generation)
            config_generation = 'config-generation:' + str(release.config_generation)
            value = replace(value,
                runtime_preflight_profile_version='product-runtime-preflight-v0.2',
                runtime_role='LIVE_RUNTIME', requested_operational_mode='LIVE',
                evaluated_at=stamp(now), process_instance_id=instance,
                process_start_generation_id=runtime_generation, process_started_at=stamp(started),
                runtime_config_generation_id=config_generation,
                heartbeat_evidence=dict(value.heartbeat_evidence,
                    heartbeat_process_instance_id=instance,
                    heartbeat_process_start_generation_id=runtime_generation,
                    heartbeat_observed_at=stamp(now), heartbeat_received_at=stamp(now)),
                reconciliation_evidence=dict(value.reconciliation_evidence,
                    reconciliation_observed_at=stamp(now)),
                external_consumer_evidence=dict(value.external_consumer_evidence,
                    compatibility_observed_at=stamp(now)),
                authorization_evidence=dict(value.authorization_evidence,
                    authorization_class='PERSISTENT_LIVE_RUNTIME', authorized_runtime_role='LIVE_RUNTIME'))
            authority = base._authority(value)
            return value, replace(authority,
                runtime_config_authority=dict(authority.runtime_config_authority,
                    runtime_config_generation_id=config_generation))

        admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=self.fixture.factory,
            current_preflight=current_preflight, clock=lambda:self.fixture.clock[0],
            maximum_observation_age_seconds=5)
        capabilities = OKXProductCapabilityOwner()
        translator = OKXProductTranslator(capabilities)
        dispatch = open_product_dispatch_journal(self.fixture.root/'dispatch.sqlite')
        canonical = open_paper_runtime_journal(self.fixture.root/'canonical.sqlite')
        self.addCleanup(dispatch.close); self.addCleanup(canonical.close)
        provider = FakeProductProvider([])
        service = TradingService(admission=admission, translator=translator,
            dispatch=dispatch, canonical=canonical, provider=provider,
            identity=self.fixture.identity, run_id=self.service.run_id,
            clock=lambda:self.fixture.clock[0])
        lease = service.bind_process(expected_revision=self.fixture.revision, expected_generation=1)
        self.assertEqual(2, lease.generation)
        self.assertEqual(instance, lease.instance_id)
        self.assertIsNot(service.admission, self.service.admission)
        self.assertIsNot(service.translator, self.service.translator)
        self.assertIsNot(service.provider, self.service.provider)
        return service

    def assert_prefix(self, recovered, batch, baseline, prefix):
        effects = batch.effects
        states = {
            1: ('INCOMPLETE', {'CLOSED_POSITION_TRADE_RESULT_MISSING', 'LIFECYCLE_EXECUTION_BINDING_MISSING'}),
            2: ('INCOMPLETE', {'CLOSED_POSITION_TRADE_RESULT_MISSING'}),
            3: ('READY', set()),
        }
        status, reasons = states[prefix]
        self.assertEqual(status, recovered.status)
        self.assertEqual(reasons, set(recovered.reason_codes))
        self.assertEqual(effects[0]['payload'], recovered.current_position_projection.payload)
        self.assertEqual(baseline.lifecycle_history, recovered.lifecycle_history[:-1])
        self.assertEqual(len(baseline.lifecycle_history)+1, len(recovered.lifecycle_history))
        if prefix == 1:
            self.assertIsNone(recovered.current_lifecycle_execution_binding)
            self.assertEqual(baseline.lifecycle_execution_bindings, recovered.lifecycle_execution_bindings)
        else:
            self.assertEqual(effects[1]['payload'], recovered.current_lifecycle_execution_binding.payload)
            self.assertEqual(len(baseline.lifecycle_execution_bindings)+1, len(recovered.lifecycle_execution_bindings))
            self.assertEqual(baseline.lifecycle_execution_bindings, recovered.lifecycle_execution_bindings[:-1])
        if prefix < 3:
            self.assertIsNone(recovered.trade_result)
        else:
            self.assertEqual(effects[2]['payload'], recovered.trade_result.payload)
        for field in ('position_id','trade_plan_id','strategy_id','strategy_version','risk_decision',
                      'approved_trade_plan','raw_position_observations','position_actions','order_requests',
                      'order_result_observations','current_order_results','fills','funding_evidence'):
            self.assertEqual(getattr(baseline, field), getattr(recovered, field), field)

    def run_committed_writer_failure(self, method_name, prefix):
        self.settled()
        reads = self.final_reads()
        baseline = self.flow.recover()
        self.assertEqual('REINTERPRETATION_REQUIRED', baseline.status)
        self.assertEqual(('E5_EXECUTION_REINTERPRETATION_REQUIRED',), baseline.reason_codes)
        old_calls = deepcopy(self.provider.calls)
        old_lease = self.service.lease
        original_descriptor = getattr(PaperRuntimeJournal, method_name)
        written = []

        def actual_commit_then_interrupt(journal, payload):
            stored = original_descriptor(journal, payload)
            written.append(stored)
            # Class descriptor is real and commits through canonical owner.
            # Exception occurs AFTER actual durable writer, not instead of it.
            raise OSError('fixture-finalization-post-commit-interruption')

        with patch.object(PaperRuntimeJournal, method_name, autospec=True,
                          side_effect=actual_commit_then_interrupt):
            with self.assertRaises(OSError):
                self.finalize(reads)
        self.assertEqual(1, len(written))
        batch = self.service.dispatch.finalization_batch(self.service.run_id, self.close_id)
        self.assertIsNotNone(batch, 'Stage must commit before any canonical writer')
        self.assertIsNone(self.service.dispatch.finalization_receipt(batch))
        self.assertEqual((batch,), self.service.dispatch.pending_finalizations(self.service.run_id))
        self.assertEqual(['POSITION_PROJECTION','LIFECYCLE_EXECUTION_BINDING','TRADE_RESULT'],
                         [item['kind'] for item in batch.effects])
        self.assertEqual(batch.effects[prefix-1]['payload'], written[0].payload)
        self.assert_prefix(self.flow.recover(), batch, baseline, prefix)
        self.assertEqual(old_calls, self.provider.calls)
        original_bundle = (batch.source_json, batch.source_hash, batch.effects_json, batch.effects_hash, batch.staged_at)
        successor = self.successor(str(prefix))
        self.assertEqual(batch, successor.dispatch.finalization_batch(successor.run_id, self.close_id))
        # This is the stable semantic history commitment, never a persisted
        # comparison of connection-local PRAGMA data_version/total_changes.
        self.assertEqual(batch.source['claim_snapshot'], claim_snapshot(successor.dispatch, successor.run_id))
        with self.assertRaises(ValueError):
            self.service.dispatch.require_process(old_lease, now=self.fixture.clock[0])
        successor.recover_publications()  # No old issued read/preparation objects.
        recovered = successor.canonical.recover(trade_plan_id=baseline.trade_plan_id,
                                               position_id=baseline.position_id)
        self.assert_prefix(recovered, batch, baseline, 3)
        self.assertTrue(recovered.restart_authoritative, recovered.reason_codes)
        saved = successor.dispatch.finalization_batch(successor.run_id, self.close_id)
        self.assertEqual(original_bundle, (saved.source_json,saved.source_hash,saved.effects_json,
                                          saved.effects_hash,saved.staged_at))
        receipt = successor.dispatch.finalization_receipt(saved)
        self.assertIsNotNone(receipt)
        self.assertEqual(batch.source_hash, receipt.source_hash)
        self.assertEqual(batch.effects_hash, receipt.effects_hash)
        self.assertEqual(batch.source['interpreted_at'], receipt.interpreted_at)
        self.assertEqual(self.flat['broker_state_observed_at'], receipt.closed_at)
        self.assertEqual(self.flat['broker_state_observed_at'], recovered.trade_result.payload['closed_at'])
        self.assertEqual(self.flat['broker_state_observed_at'],
                         recovered.current_position_projection.payload['broker_state_observed_at'])
        self.assertEqual(self.flat['lifecycle_revision']+1,
                         recovered.current_position_projection.payload['lifecycle_revision'])
        self.assertEqual(self.flat['lifecycle_projection_id'],
                         recovered.current_position_projection.payload['previous_lifecycle_projection_id'])
        # Assertion-only SQL in the future applied test. No SQL state mutation.
        count = successor.dispatch._db.execute(
            'SELECT COUNT(*) FROM product_dispatch_finalization_publications WHERE run_id=? AND operation_id=?',
            (successor.run_id,self.close_id)).fetchone()[0]
        self.assertEqual(1, count)
        self.assertEqual((), successor.dispatch.pending_finalizations(successor.run_id))
        self.assertEqual([], successor.provider.calls)
        self.assertFalse(successor.provider._responses)
        self.assertEqual(old_calls, self.provider.calls)
        successor.recover_publications()
        self.assertEqual(recovered, successor.canonical.recover(trade_plan_id=baseline.trade_plan_id,
                                                              position_id=baseline.position_id))
        self.assertEqual(receipt, successor.dispatch.finalization_receipt(saved))
        self.assertEqual([], successor.provider.calls)
        self.assertEqual(1, successor.dispatch._db.execute(
            'SELECT COUNT(*) FROM product_dispatch_finalization_publications WHERE run_id=? AND operation_id=?',
            (successor.run_id,self.close_id)).fetchone()[0])
