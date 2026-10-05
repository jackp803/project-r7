import importlib
import signal
import threading
import time
import unittest
from pathlib import Path
import sys


class ManagedStopTests(unittest.TestCase):
    def api(self):
        return importlib.import_module('application.platform.shutdown')

    def test_actual_term_and_interrupt_request_stop_without_async_exception_and_restore_handlers(self):
        before={number:signal.getsignal(number) for number in (signal.SIGTERM,signal.SIGINT)}
        with self.api().ManagedStop() as stop:
            self.assertFalse(stop.requested)
            self.assertTrue(callable(signal.getsignal(signal.SIGTERM)))
            signal.raise_signal(signal.SIGTERM)
            self.assertTrue(stop.requested)
            self.assertEqual(stop.first_signal,signal.SIGTERM)
            signal.raise_signal(signal.SIGINT)
            self.assertEqual(stop.first_signal,signal.SIGTERM)
        self.assertEqual(before,{number:signal.getsignal(number) for number in before})

    def test_idle_wait_wakes_on_explicit_stop_request(self):
        with self.api().ManagedStop() as stop:
            timer=threading.Timer(0.02,stop.request)
            timer.start()
            try:
                started=time.monotonic()
                self.assertTrue(stop.wait(2))
                self.assertLess(time.monotonic()-started,1)
            finally:timer.join(2)

    def test_idle_wait_observes_an_actual_signal_without_waiting_for_the_full_delay(self):
        with self.api().ManagedStop() as stop:
            timer=threading.Timer(0.02,lambda:signal.raise_signal(signal.SIGTERM))
            timer.start()
            try:
                self.assertTrue(stop.wait(2))
                self.assertEqual(stop.first_signal,signal.SIGTERM)
            finally:timer.join(3)

    def test_nested_scope_restores_the_original_handlers_without_stopping_outer_scope(self):
        before=signal.getsignal(signal.SIGTERM)
        with self.api().ManagedStop() as outer:
            outer_handler=signal.getsignal(signal.SIGTERM)
            with self.api().ManagedStop() as inner:
                self.assertTrue(callable(signal.getsignal(signal.SIGTERM)))
                signal.raise_signal(signal.SIGTERM)
                self.assertTrue(inner.requested)
                self.assertFalse(outer.requested)
            self.assertIs(signal.getsignal(signal.SIGTERM),outer_handler)
            signal.raise_signal(signal.SIGTERM)
            self.assertTrue(outer.requested)
        self.assertIs(signal.getsignal(signal.SIGTERM),before)

    def test_signal_ownership_requires_main_thread_and_leaves_handlers_untouched(self):
        api=self.api();before=signal.getsignal(signal.SIGTERM);errors=[]
        def wrong_thread():
            try:
                with api.ManagedStop():pass
            except ValueError as error:errors.append(str(error))
        thread=threading.Thread(target=wrong_thread)
        thread.start();thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors,['MANAGED_STOP_MAIN_THREAD_REQUIRED'])
        self.assertIs(signal.getsignal(signal.SIGTERM),before)

    def test_actual_signal_cannot_deadlock_when_interrupted_manual_wait_holds_its_lock(self):
        from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
        program=('import signal\nfrom application.platform.shutdown import ManagedStop\n'
                 'with ManagedStop() as stop:\n'
                 ' with stop._event._cond:\n'
                 '  signal.raise_signal(signal.SIGTERM)\n'
                 ' assert stop.requested\n')
        owned=spawn_owned([sys.executable,'-c',program],cwd=Path.cwd(),limits=ResourceLimits(2))
        self.addCleanup(lambda:terminate_owned(owned,deadline_seconds=5))
        self.assertEqual(owned.wait(timeout=3),0,'Signal must not acquire the interrupted wait lock')
        self.assertTrue(owned.termination_report.reaped)
