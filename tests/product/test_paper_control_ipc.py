import unittest
from tests.product import test_paper_runtime_v02 as fixtures
from storage.paper_process import open_paper_process_journal
from storage.runtime_models import RuntimeConflictError


class PaperControlIPCTests(unittest.TestCase):
    def setUp(self):
        helper = fixtures.PaperRuntimeV02Tests(); helper.setUp(); self.addCleanup(helper.doCleanups)
        self.h = helper
        self.assertTrue(hasattr(helper.process, 'request_entry_pause'),
                        'Read-only control connection must request pause without stealing runtime generation')

    def request(self, runtime, command='pause-control', actor='local-owner'):
        with open_paper_process_journal(self.h.root/'runtime.sqlite') as control:
            return control.request_entry_pause(runtime.run_id, command, actor=actor,
                expected_revision=control.control_revision(runtime.run_id), now=self.h.clock[0])

    def test_pause_request_blocks_entry_before_worker_consumption_without_new_generation(self):
        runtime = self.h.start(); before = self.h.process.recover(runtime.run_id).process_generation
        receipt = self.request(runtime)
        self.assertEqual(receipt['status'], 'PAUSED')
        self.assertEqual(self.h.process.recover(runtime.run_id).process_generation, before)
        outcome = runtime.on_market_event(self.h.event(0, bars=True))
        self.assertEqual(outcome.status, 'BLOCKED')
        self.assertIn('PAPER_ENTRIES_PAUSED', outcome.reason_codes)
        self.assertEqual(self.h.process.recover(runtime.run_id).state['broker']['payload']['submissions'], [])

    def test_pause_request_prevents_pending_entry_fill_while_retaining_original_order_facts(self):
        runtime = self.h.start(); runtime.on_market_event(self.h.event(0, bars=True))
        self.request(runtime)
        outcome = runtime.on_market_event(self.h.event(1))
        self.assertEqual(outcome.status, 'BLOCKED')
        state = self.h.process.recover(runtime.run_id).state
        self.assertIsNone(state['runtime']['position'])
        self.assertEqual(sum(len(item['order']['fills']) for item in state['broker']['payload']['submissions']), 0)
        self.assertEqual(len(state['broker']['payload']['submissions']), 1)

    def test_scheduler_consumes_pause_on_own_generation_and_preserves_verified_protection(self):
        from application.paper.scheduler import PaperScheduler
        runtime = self.h.start(); runtime.on_market_event(self.h.event(0, bars=True)); runtime.on_market_event(self.h.event(1))
        position = self.h.process.recover(runtime.run_id).state['runtime']['position']
        generation = self.h.process.recover(runtime.run_id).process_generation
        self.request(runtime)
        self.h.clock[0] += __import__('datetime').timedelta(seconds=1)
        outcomes = PaperScheduler(runtime).tick()
        after = self.h.process.recover(runtime.run_id)
        self.assertEqual(after.process_generation, generation)
        self.assertFalse(after.state['runtime']['paper_entries_allowed'])
        self.assertEqual(after.state['runtime']['position']['actual_quantity'], position['actual_quantity'])
        self.assertEqual(after.state['runtime']['position']['lifecycle_state'], 'OPEN_PROTECTED')
        self.assertEqual(self.h.process.pending_entry_pauses(runtime.run_id), ())
        self.assertTrue(any(item.operation_id == 'pause:pause-control' for item in outcomes))

    def test_pause_revision_cas_and_command_identity_are_atomic_immutable(self):
        runtime = self.h.start()
        with open_paper_process_journal(self.h.root/'runtime.sqlite') as control:
            with self.assertRaises(RuntimeConflictError):
                control.request_entry_pause(runtime.run_id, 'stale-pause', actor='local-owner', expected_revision=1, now=self.h.clock[0])
            self.assertFalse(control.entry_pause_requested(runtime.run_id))
            one = control.request_entry_pause(runtime.run_id, 'pause-one', actor='local-owner', expected_revision=0, now=self.h.clock[0])
            self.assertEqual(one, control.request_entry_pause(runtime.run_id, 'pause-one', actor='local-owner', expected_revision=0, now=self.h.clock[0]))
            with self.assertRaises(RuntimeConflictError):
                control.request_entry_pause(runtime.run_id, 'pause-one', actor='another-owner', expected_revision=0, now=self.h.clock[0])
            self.assertEqual(control.control_revision(runtime.run_id), 1)


if __name__ == '__main__': unittest.main()
