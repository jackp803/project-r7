"""Actual independent runtime owner mechanics; no real-forward qualification."""
from dataclasses import asdict, replace
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from application.platform.scope_lock import ScopeBusy
from application.platform.supervision import SupervisionError, process_health
from application.platform.shutdown import ManagedStop
from storage.runtime_models import RuntimeConflictError
from tests.application.paper_owner_fixtures import PaperOwnerFixture


class PaperOwnerWorkerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.worker'),
            'Independent PAPER owner worker must manage accepted runs')
        from application.paper.worker import PaperOwnerWorker, PaperWorkerError
        self.worker_type, self.error_type = PaperOwnerWorker, PaperWorkerError
        self.f = PaperOwnerFixture(self)

    def worker(self, **options):
        return self.worker_type(self.f.config, self.f.factory, namespace='FIXTURE', **options)

    def event_tick(self, worker, run_id, seconds, price='60000', bars=False):
        self.assertTrue(worker.submit_event(run_id, self.f.event(seconds, price, bars)))
        return worker.tick()[run_id][-1]

    def test_discovers_actual_api_prepared_start_after_empty_owner_without_stealing_generation(self):
        with self.worker() as worker:
            self.assertEqual(worker.tick(), {})
            self.assertEqual(worker.snapshot()['active_runs'], ())
            run_id = self.f.start()
            self.assertEqual(self.f.recover(run_id).process_generation, 0)
            worker.tick()
            generation = self.f.recover(run_id).process_generation
            self.assertEqual(generation, 1)
            self.f.reader.view(run_id)
            self.f.reader.list(self.f.h.registry_factory)
            self.assertEqual(self.f.recover(run_id).process_generation, generation)
            self.assertEqual(worker.snapshot()['active_runs'], (run_id,))
            self.assertEqual(worker.snapshot()['financial_authority'], 'NONE')
            self.assertEqual(worker.supervisor.identity['role'], 'runtime')
        self.assertEqual(process_health(self.f.config, 'runtime')['status'], 'STOPPED')

    def test_actual_scheduler_ack_fill_protection_target_close_and_canonical_result(self):
        run_id = self.f.start()
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(self.event_tick(worker, run_id, 0, bars=True).status, 'ACKNOWLEDGED')
            self.assertIsNone(self.f.recover(run_id).state['runtime']['position'])
            self.assertEqual(self.event_tick(worker, run_id, 1).status, 'PROTECTED')
            position = self.f.recover(run_id).state['runtime']['position']
            self.assertEqual(position['lifecycle_state'], 'OPEN_PROTECTED')
            self.assertEqual(self.event_tick(worker, run_id, 2, '60020').status, 'EXIT_REQUESTED')
            self.assertTrue(worker.submit_event(run_id, self.f.event(3, '60020')))
            self.assertTrue(any(item.status == 'CLOSED' for item in worker.tick()[run_id]))
            graph = worker.service.canonical.recover(position_id=position['position_id'])
            self.assertEqual(graph.status, 'READY')
            self.assertEqual(graph.current_position_projection.payload['lifecycle_state'], 'CLOSED')
            self.assertEqual(len(graph.fills), 2)
            self.assertEqual(graph.trade_result.payload, self.f.recover(run_id).state['runtime']['closed_trades'][0])

    def test_duplicate_owner_is_denied_before_factory_or_per_run_generation_changes(self):
        run_id = self.f.start()
        with self.worker() as first:
            first.tick()
            before = self.f.recover(run_id)
            calls = len(self.f.factory_calls)
            token = first.supervisor.identity['process_generation_id']
            with self.assertRaises(ScopeBusy):
                with self.worker():
                    self.fail('Duplicate runtime owner admitted')
            self.assertEqual(len(self.f.factory_calls), calls)
            self.assertEqual(self.f.recover(run_id), before)
            self.assertEqual(first.supervisor.health()['process_generation_id'], token)
            first.tick()

    def test_restart_recovers_same_protected_position_and_fences_old_owner(self):
        run_id = self.f.start()
        with self.worker() as first:
            first.tick()
            self.event_tick(first, run_id, 0, bars=True)
            self.event_tick(first, run_id, 1)
            original = self.f.recover(run_id)
            generation = first.supervisor.identity['generation']
        with self.worker() as second:
            second.tick()
            recovered = self.f.recover(run_id)
            self.assertEqual(recovered.process_generation, original.process_generation+1)
            self.assertEqual(second.supervisor.identity['generation'], generation+1)
            for name in ('opened_at', 'position_id', 'actual_quantity'):
                self.assertEqual(recovered.state['runtime']['position'][name], original.state['runtime']['position'][name])
            self.assertEqual(recovered.state['runtime']['protection_request'], original.state['runtime']['protection_request'])
            self.assertEqual(recovered.binding, original.binding)
            with self.assertRaises(self.error_type):
                first.tick()
            from application.paper.orchestrator import PaperCoordinator
            def cannot_produce(*_):
                self.fail('Fenced predecessor must not produce another owner effect')
            stale = PaperCoordinator(second.service.process, second.service.canonical, run_id,
                original.process_generation, cannot_produce, clock=lambda: self.f.h.clock[0])
            with self.assertRaises(RuntimeConflictError):
                stale.execute('stale-owner-attempt', dict(kind='DEADLINE'))
            self.assertEqual(self.event_tick(second, run_id, 2, '60020').status, 'EXIT_REQUESTED')
            self.assertTrue(second.submit_event(run_id, self.f.event(3, '60020')))
            self.assertTrue(any(item.status == 'CLOSED' for item in second.tick()[run_id]))
            self.assertEqual(len(self.f.recover(run_id).state['runtime']['closed_trades']), 1)

    def test_api_pause_preserves_existing_protection_and_owner_generation(self):
        run_id = self.f.start()
        with self.worker() as worker:
            worker.tick(); self.event_tick(worker, run_id, 0, bars=True); self.event_tick(worker, run_id, 1)
            before = self.f.recover(run_id)
            self.f.reader.pause(run_id, 'api-pause', 'fixture-owner', self.f.reader.revision(run_id))
            self.assertEqual(self.f.recover(run_id).process_generation, before.process_generation)
            worker.tick()
            after = self.f.recover(run_id)
            self.assertFalse(after.state['runtime']['paper_entries_allowed'])
            self.assertEqual(after.state['runtime']['protection_request'], before.state['runtime']['protection_request'])
            self.assertEqual(after.state['runtime']['position']['actual_quantity'], '0.001')
            self.assertEqual(worker.service.process.pending_entry_pauses(run_id), ())
            self.assertEqual(self.event_tick(worker, run_id, 2, '60020').status, 'EXIT_REQUESTED')

    def test_queue_full_cannot_starve_max_hold_deadline_without_entry_candle(self):
        run_id = self.f.start()
        with self.worker(maximum_pending_events=1) as worker:
            worker.tick(); self.event_tick(worker, run_id, 0, bars=True); self.event_tick(worker, run_id, 1)
            self.assertTrue(worker.submit_event(run_id, self.f.event(3601)))
            self.assertFalse(worker.submit_event(run_id, self.f.event(3601)))
            outcomes = worker.tick()[run_id]
            self.assertTrue(any(outcome.status == 'EXIT_REQUESTED' for outcome in outcomes))
            state = self.f.recover(run_id).state['runtime']
            self.assertIn('E5_MAX_HOLD_REACHED', state['exit_action']['reason_codes'])
            self.assertEqual(state['last_entry_boundary'], '2026-10-03T00:00:00Z')
            self.assertEqual(len(state['closed_trades']), 0, 'Exit ACK at the same clock is not a fill')
            self.assertTrue(worker.submit_event(run_id, self.f.event(3602)))
            self.assertTrue(any(item.status == 'CLOSED' for item in worker.tick()[run_id]))
            self.assertEqual(len(self.f.recover(run_id).state['runtime']['closed_trades']), 1)

    def test_factory_connections_are_opened_on_owner_thread_and_producer_only_queues(self):
        run_id = self.f.start(); errors = []; producer_result = []
        def own():
            try:
                with self.worker() as worker:
                    worker.tick()
                    self.assertEqual(self.f.factory_calls[-1], threading.get_ident())
                    event = self.f.event(0, bars=True)
                    def produce():
                        producer_result.append(worker.submit_event(run_id, event))
                        try: worker.tick()
                        except self.error_type as error: producer_result.append(str(error))
                    producer = threading.Thread(target=produce)
                    producer.start(); producer.join(5)
                    self.assertFalse(producer.is_alive())
                    self.assertEqual(worker.tick()[run_id][-1].status, 'ACKNOWLEDGED')
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=own)
        thread.start(); thread.join(15)
        self.assertFalse(thread.is_alive(), 'Owned test thread cleanup not confirmed')
        self.assertEqual(errors, [])
        self.assertEqual(producer_result, [True, 'PAPER_OWNER_THREAD_REQUIRED'])

    def test_configuration_drift_is_denied_before_new_order_or_owner_generation(self):
        profile = self.f.h.root/'worker-profile.json'
        values = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.f.config).items()}
        profile.write_text(json.dumps(values), encoding='utf-8')
        run_id = self.f.start()
        with self.worker(config_path=profile) as worker:
            worker.tick()
            self.assertTrue(worker.submit_event(run_id, self.f.event(0, bars=True)))
            before = self.f.recover(run_id)
            values['scan_interval'] = 31
            profile.write_text(json.dumps(values), encoding='utf-8')
            with self.assertRaises(SupervisionError): worker.tick()
            self.assertEqual(self.f.recover(run_id), before)

    def test_wrong_namespace_closes_factory_and_scope_without_attachment(self):
        run_id = self.f.start(); before = self.f.recover(run_id)
        closed = self.f.closed_factories
        with self.assertRaises(self.error_type):
            with self.worker_type(self.f.config, self.f.factory, namespace='LOCAL_RESEARCH'):
                self.fail('Wrong namespace owner admitted')
        self.assertEqual(self.f.closed_factories, closed+1)
        self.assertEqual(self.f.recover(run_id), before)
        with self.worker() as worker: worker.tick()

    def test_run_obeys_cooperative_stop_and_does_not_clear_position_or_pending_queue(self):
        run_id = self.f.start(); stop = ManagedStop()
        with self.worker() as worker:
            worker.tick(); self.event_tick(worker, run_id, 0, bars=True); self.event_tick(worker, run_id, 1)
            before = self.f.recover(run_id)
            stop.request(); worker.run(stop)
            self.assertEqual(self.f.recover(run_id), before)
        self.assertEqual(self.f.recover(run_id).state['runtime']['position']['lifecycle_state'], 'OPEN_PROTECTED')

    def test_terminal_flat_history_does_not_use_capacity_but_retired_exposure_stays_managed(self):
        run_id = self.f.start()
        with self.worker(maximum_active_runs=1) as worker:
            worker.tick(); self.event_tick(worker, run_id, 0, bars=True); self.event_tick(worker, run_id, 1)
            worker.service.registry.retire(self.f.identity, actor='fixture-owner', reason_codes=('USER_RETIRED',))
            worker.tick()
            self.assertIn(run_id, worker.snapshot()['active_runs'], 'Retired open exposure must remain managed')
            self.event_tick(worker, run_id, 2, '60020')
            self.assertTrue(worker.submit_event(run_id, self.f.event(3, '60020')))
            worker.tick(); worker.tick()
            second = self.f.second_candidate(); second_run = self.f.start('second-start', second)
            worker.tick()
            self.assertEqual(worker.snapshot()['active_runs'], (second_run,))
            self.assertEqual(self.f.recover(second_run).process_generation, 1)
            self.assertEqual(len(self.f.recover(run_id).state['runtime']['closed_trades']), 1)

    def test_capacity_failure_stays_visible_through_following_discovery_page(self):
        first_run = self.f.start()
        second = self.f.second_candidate(); second_run = self.f.start('second-start', second)
        with self.worker(maximum_active_runs=1) as worker:
            records = worker.service.registry.list_accepted_paper_starts(limit=50, offset=0)
            self.assertEqual(len(records), 2)
            # Controlled pagination of actual accepted E6 records; never forged
            # start/run evidence. The second page contains only the owned run.
            pages = [tuple([records[0]]*49+[records[1]]), tuple([records[0]]*50)]
            with patch.object(worker.service.registry, 'list_accepted_paper_starts', side_effect=pages):
                worker.tick()
                self.assertEqual(worker.snapshot()['status'], 'DEGRADED')
                worker.tick()
                self.assertEqual(worker.snapshot()['status'], 'DEGRADED')
                self.assertEqual(worker.snapshot()['discovery_status'], 'CAPACITY_EXCEEDED')
            self.assertEqual(worker.snapshot()['active_runs'], (first_run,))
            self.assertEqual(self.f.recover(second_run).process_generation, 0)

    def test_actual_private_restore_stays_inhibited_without_new_orders_across_worker_restarts(self):
        from application.platform.restoration import restoration_status
        run_id = self.f.start()
        self.f.restore_inhibited(self)
        self.assertEqual(restoration_status(self.f.config)['status'], 'RESTORED_INHIBITED')
        generation = None
        for attempt in range(2):
            with self.worker() as worker:
                worker.tick()
                if attempt == 0:
                    self.assertTrue(worker.submit_event(run_id, self.f.event(0, bars=True)))
                    outcomes = worker.tick()[run_id]
                    self.assertTrue(any('PAPER_ENTRIES_PAUSED' in item.reason_codes for item in outcomes))
                    generation = self.f.recover(run_id).process_generation
                else:
                    self.assertEqual(worker.snapshot()['active_runs'], ())
                    self.assertEqual(self.f.recover(run_id).process_generation, generation)
                    with self.assertRaisesRegex(self.error_type, 'PAPER_RUN_NOT_ATTACHED'):
                        worker.submit_event(run_id, self.f.event(0, bars=True))
                self.assertEqual(self.f.recover(run_id).state['broker']['payload']['submissions'], [])
                self.assertEqual(worker.snapshot()['restoration']['status'], 'RESTORED_INHIBITED')
                self.assertEqual(restoration_status(self.f.config)['runtime_new_exposure'], 'INHIBITED')
                self.assertTrue(worker.service.process.entry_pause_requested(run_id))

    def test_invalid_first_run_market_event_is_quarantined_while_second_run_keeps_protection_deadline(self):
        from application.paper.service import PaperMarketEvent
        first_run = self.f.start()
        second = self.f.second_candidate(); second_run = self.f.start('second-start', second)
        with self.worker() as worker:
            worker.tick()
            self.event_tick(worker, first_run, 0, bars=True)
            self.event_tick(worker, second_run, 0, bars=True)
            self.event_tick(worker, second_run, 1)
            valid = self.f.event(3601, bars=True)
            invalid = PaperMarketEvent(valid.snapshot, (replace(valid.candles[0], timeframe='4h',
                open_time=self.f.initial_now-timedelta(hours=4), close_time=self.f.initial_now),), 'FIXTURE')
            self.assertTrue(worker.submit_event(first_run, invalid))
            worker.tick()
            self.assertEqual(worker.snapshot()['run_failures'][first_run], 'MARKET_EVENT_REJECTED')
            self.assertEqual(worker.snapshot()['acquisition'][first_run]['pending_events'], 0)
            state = self.f.recover(second_run).state['runtime']
            self.assertEqual(state['position']['lifecycle_state'], 'EXIT_REQUESTED')
            self.assertIn('E5_MAX_HOLD_REACHED', state['exit_action']['reason_codes'])

    def test_restart_publishes_applied_owner_effect_without_recomputing_or_duplicate_order(self):
        run_id = self.f.start()
        with self.worker() as first:
            first.tick()
            self.assertTrue(first.submit_event(run_id, self.f.event(0, bars=True)))
            with patch.object(type(first.service.canonical), 'persist_order_result',
                    side_effect=OSError('FIXTURE_CANONICAL_PUBLICATION_INTERRUPTED')):
                with self.assertRaises(OSError): first.tick()
            before = self.f.recover(run_id)
            self.assertEqual(len(before.pending_operations), 1)
            operation_id = before.pending_operations[0]
            original = first.service.process.operation(run_id, operation_id)
            self.assertEqual(original.status, 'APPLIED')
            self.assertEqual(len(before.state['broker']['payload']['submissions']), 1)
        with self.worker() as second:
            second.tick()
            recovered = self.f.recover(run_id)
            self.assertEqual(recovered.pending_operations, ())
            publication = second.service.process.operation(run_id, operation_id)
            self.assertEqual(publication.status, 'PUBLISHED')
            self.assertEqual(publication.effect_hash, original.effect_hash)
            self.assertEqual(len(recovered.state['broker']['payload']['submissions']), 1)
            self.assertIsNone(recovered.state['runtime']['position'])
            self.assertEqual(self.event_tick(second, run_id, 1).status, 'PROTECTED')
            self.assertEqual(self.f.recover(run_id).state['runtime']['position']['actual_quantity'], '0.001')

    def test_prior_policy_binding_failure_is_visible_without_stopping_other_run_deadlines(self):
        first_run = self.f.start()
        with self.worker() as first:
            first.tick(); self.event_tick(first, first_run, 0, bars=True); self.event_tick(first, first_run, 1)
            original = self.f.recover(first_run)
        self.f.simulation = dict(self.f.simulation, generation=2)
        second = self.f.second_candidate(); second_run = self.f.start('second-start', second)
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(worker.snapshot()['run_failures'][first_run], 'RUN_ATTACHMENT_RECONCILIATION_REQUIRED')
            self.assertEqual(worker.snapshot()['active_runs'], (second_run,))
            self.event_tick(worker, second_run, 1, bars=True); self.event_tick(worker, second_run, 2)
            self.f.h.clock[0] = self.f.initial_now+timedelta(seconds=3602)
            worker.tick()
            self.assertIn('E5_MAX_HOLD_REACHED', self.f.recover(second_run).state['runtime']['exit_action']['reason_codes'])
            self.assertEqual(self.f.recover(first_run), original, 'Changed binding must not be silently rewritten')
            self.assertEqual(worker.snapshot()['status'], 'DEGRADED')

    def test_concurrent_actual_api_pause_during_restore_does_not_stop_other_protection(self):
        first_run = self.f.start()
        second = self.f.second_candidate(); second_run = self.f.start('second-start', second)
        with self.worker() as original:
            original.tick()
            for seconds in (0, 1):
                for run_id in (first_run, second_run):
                    self.assertTrue(original.submit_event(run_id, self.f.event(seconds, bars=seconds == 0)))
                original.tick()
        self.f.restore_inhibited(self)
        with self.worker() as worker:
            request = worker.service.process.request_entry_pause
            interleavings = []
            def race(run_id, command_id, **arguments):
                if run_id == first_run and not interleavings:
                    interleavings.append(self.f.reader.pause(run_id, 'api-concurrent-pause', 'fixture-owner',
                        self.f.reader.revision(run_id)))
                return request(run_id, command_id, **arguments)
            with patch.object(worker.service.process, 'request_entry_pause', side_effect=race):
                worker.tick()
            self.assertEqual(len(interleavings), 1)
            for run_id in (first_run, second_run):
                self.assertTrue(worker.service.process.entry_pause_requested(run_id))
                state = self.f.recover(run_id).state['runtime']
                self.assertEqual(state['position']['lifecycle_state'], 'EXIT_REQUESTED')
                self.assertIn('E5_MAX_HOLD_REACHED', state['exit_action']['reason_codes'])
                self.assertEqual(state['position']['actual_quantity'], '0.001')
            self.assertEqual(worker.snapshot()['run_failures'], {})


if __name__ == '__main__': unittest.main()
