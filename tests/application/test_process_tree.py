import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests.application.test_platform import require


class OwnedProcessTreeTests(unittest.TestCase):
    def test_automatic_timeout_reaps_without_caller_cancellation(self):
        module = require(self, "application.platform.processes")
        handle = module.spawn_owned([sys.executable, "-c", "import time; time.sleep(120)"],
                                    cwd=Path.cwd(), limits=module.ResourceLimits(timeout_seconds=0.2))
        self.addCleanup(lambda: module.terminate_owned(handle, deadline_seconds=5))
        deadline = time.monotonic() + 5
        while handle.termination_report is None and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertIsNotNone(handle.termination_report)
        self.assertEqual("TIMEOUT", handle.termination_report.reason)
        self.assertTrue(handle.termination_report.reaped)
        self.assertIsNotNone(handle.process.returncode)

    def test_timeout_reaps_parent_child_grandchild_and_preserves_unrelated_process(self):
        module = require(self, "application.platform.processes")
        with tempfile.TemporaryDirectory(prefix="R7 程序 樹 ") as temp:
            root = Path(temp)
            target = root / "worker.py"
            target.write_text(
                "import subprocess,sys,time,os,json\n"
                "from pathlib import Path\n"
                "depth=int(sys.argv[1]); root=Path(sys.argv[2])\n"
                "(root/f'{depth}.json').write_text(json.dumps({'pid':os.getpid()}))\n"
                "if depth: subprocess.Popen([sys.executable,__file__,str(depth-1),str(root)])\n"
                "time.sleep(120)\n", encoding="utf-8")
            unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(120)"], cwd=root)
            self.addCleanup(lambda: unrelated.wait(timeout=5))
            self.addCleanup(lambda: unrelated.poll() is None and unrelated.kill())
            handle = module.spawn_owned([sys.executable, str(target), "2", str(root)], cwd=root, limits=module.ResourceLimits())
            self.addCleanup(lambda: module.terminate_owned(handle, deadline_seconds=5))
            deadline = time.monotonic() + 10
            while not all((root / f"{depth}.json").exists() for depth in (0, 1, 2)):
                if time.monotonic() > deadline:
                    self.fail("worker descendants did not start")
                time.sleep(0.05)
            pids = [json.loads((root / f"{depth}.json").read_text())["pid"] for depth in (0, 1, 2)]
            self.assertTrue(all(module.process_alive(pid) for pid in pids))
            report = module.terminate_owned(handle, deadline_seconds=5)
            self.assertTrue(report.terminated)
            self.assertTrue(report.reaped)
            self.assertTrue(all(not module.process_alive(pid) for pid in pids))
            self.assertIsNone(unrelated.poll())
            unrelated.kill()
            unrelated.wait(timeout=5)

    def test_rejects_shell_strings_and_invalid_limits_before_spawning(self):
        module = require(self, "application.platform.processes")
        with self.assertRaises(ValueError):
            module.spawn_owned("python -c bad", cwd=Path.cwd(), limits=module.ResourceLimits())
        with self.assertRaises(ValueError):
            module.ResourceLimits(timeout_seconds=0)
