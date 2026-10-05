import importlib
import importlib.util
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from application.platform.processes import process_alive


class CloudCommandRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 雲端 命令 私密 ')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.cloud.command_runner'),
                             'The bounded cloud process runner is not implemented')
        return importlib.import_module('application.cloud.command_runner')

    def run_child(self, code, *, timeout=3, limit=4096):
        return self.module().run_bounded([sys.executable,'-c',code],private_root=self.root,
            timeout_seconds=timeout,stdout_limit=limit)

    def test_real_child_returns_exact_bounded_bytes_and_is_reaped(self):
        result=self.run_child("import sys;sys.stdout.buffer.write(b'{\"scope\":\"fixture\"}')")
        self.assertEqual(result.stdout,b'{"scope":"fixture"}')
        self.assertEqual(result.exit_code,0)
        self.assertTrue(result.tree_reaped)
        self.assertEqual(result.status,'COMPLETE')
        self.assertNotIn('fixture',repr(result), 'Raw remote bytes must not enter diagnostic repr')

    def test_nonzero_child_stderr_is_discarded_and_never_returned_as_remote_output(self):
        result=self.run_child("import sys;sys.stderr.write('synthetic-private-stderr');sys.exit(7)")
        self.assertEqual(result.exit_code,7)
        self.assertEqual(result.stdout,b'')
        self.assertTrue(result.tree_reaped)
        self.assertEqual(result.status,'COMMAND_FAILED')
        self.assertNotIn('synthetic-private-stderr',repr(result))
        self.assertFalse(any(b'synthetic-private-stderr' in path.read_bytes() for path in self.root.rglob('*') if path.is_file()))

    def test_oversize_stdout_has_no_partial_success_and_tree_is_reaped(self):
        result=self.run_child("import sys;sys.stdout.buffer.write(b'x'*(8*1024*1024));sys.stdout.flush()",limit=1024)
        self.assertEqual(result.status,'OUTPUT_LIMIT_EXCEEDED')
        self.assertEqual(result.stdout,b'')
        self.assertTrue(result.tree_reaped)

    def test_deadline_terminates_real_child_and_grandchild_without_killing_parent(self):
        pids=self.root/'owned-pids.txt'
        code="import os,pathlib,subprocess,sys,time;child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path(sys.argv[1]).write_text(str(os.getpid())+' '+str(child.pid));time.sleep(60)"
        started=time.monotonic()
        result=self.module().run_bounded([sys.executable,'-c',code,str(pids)],private_root=self.root,
            timeout_seconds=1,stdout_limit=4096)
        self.assertEqual(result.status,'TIMEOUT')
        self.assertTrue(result.tree_reaped)
        self.assertLess(time.monotonic()-started,5)
        self.assertTrue(pids.exists(),'The actual grandchild must have started')
        for pid in map(int,pids.read_text().split()):
            self.assertFalse(process_alive(pid),'Owned descendant must be terminated')
        self.assertTrue(process_alive(os.getpid()))

    def test_invalid_budgets_fail_before_starting_any_child(self):
        module=self.module()
        marker=self.root/'must-not-run.txt'
        for timeout,limit in ((True,1024),(0,1024),(301,1024),(1,True),(1,0),(1,64*1024*1024)):
            with self.subTest(timeout=timeout,limit=limit), self.assertRaises(ValueError):
                module.run_bounded([sys.executable,'-c',"import pathlib,sys;pathlib.Path(sys.argv[1]).touch()",str(marker)],
                    private_root=self.root,timeout_seconds=timeout,stdout_limit=limit)
        self.assertFalse(marker.exists())

    def test_overflow_reports_actual_observed_capture_size_instead_of_a_false_hard_cap(self):
        result=self.run_child("import sys;sys.stdout.buffer.write(b'x'*2048);sys.stdout.flush()",limit=1024)
        self.assertEqual(result.status,'OUTPUT_LIMIT_EXCEEDED')
        self.assertEqual(result.captured_bytes,2048)
        self.assertEqual(result.stdout,b'')


if __name__=='__main__':
    unittest.main()
