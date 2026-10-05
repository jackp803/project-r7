from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen

from application.config import ProductConfig
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.supervision import process_health


class ControlProcessSupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 控制 程序 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        self.config = ProductConfig('r7-product-config-v0.2', 'control-process-fixture', self.root / '資料',
                                    None, self.root / '資料' / 'canonical.sqlite3', control_api_port=port)
        self.profile = self.root / 'profile.json'
        self.write_profile()

    def write_profile(self, **changes):
        data = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        data.update(changes)
        self.profile.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

    def start(self, name):
        stream = (self.root / (name + '.log')).open('xb')
        self.addCleanup(stream.close)
        child = spawn_owned([sys.executable, '-m', 'application', 'serve', '--config', str(self.profile)],
            cwd=Path.cwd(), limits=ResourceLimits(15), stdout=stream, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: terminate_owned(child, deadline_seconds=5))
        return child

    def ready(self, child):
        deadline = time.monotonic() + 8
        while child.process.poll() is None and time.monotonic() < deadline:
            try:
                with urlopen('http://127.0.0.1:' + str(self.config.control_api_port) + '/api/v1/auth/status', timeout=0.3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertFalse(json.loads(response.read())['configured'])
                    return
            except (URLError, OSError):
                time.sleep(0.05)
        self.fail('Actual loopback control process did not become ready')

    def test_actual_control_restart_increments_generation_and_second_process_is_denied(self):
        first = self.start('first')
        self.ready(first)
        previous = process_health(self.config, 'control', now=datetime.now(timezone.utc))
        self.assertEqual(previous['status'], 'RECENT_HEARTBEAT')
        contender = self.start('contender')
        self.assertEqual(contender.wait(timeout=5), 2)
        self.assertEqual(process_health(self.config, 'control')['process_generation_id'], previous['process_generation_id'])
        self.assertTrue(terminate_owned(first, deadline_seconds=5).reaped)
        self.assertEqual(process_health(self.config, 'control')['status'], 'PROCESS_NOT_RUNNING')
        successor = self.start('successor')
        self.ready(successor)
        current = process_health(self.config, 'control')
        self.assertGreater(current['generation'], previous['generation'])
        self.assertNotEqual(current['process_generation_id'], previous['process_generation_id'])
        self.assertEqual(current['financial_authority'], 'NONE')

    def test_changed_actual_profile_stops_control_process_and_leaves_explicit_failure(self):
        first = self.start('config-change')
        self.ready(first)
        self.write_profile(scan_interval=31)
        self.assertEqual(first.wait(timeout=5), 2)
        self.assertTrue(first.termination_report.reaped)
        self.assertEqual(process_health(self.config, 'control')['status'], 'CONFIG_CHANGED')
