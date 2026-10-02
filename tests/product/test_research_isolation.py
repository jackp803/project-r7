"""Actual separate owned processes: controlled research fault vs PAPER management."""
import json
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits,process_alive


def wait_for(predicate,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=predicate()
        if value: return value
        time.sleep(.02)
    raise AssertionError('Expected local fixture observation did not arrive')


def read(path):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError: return None


class ResearchIsolationTests(unittest.TestCase):
    def test_memory_failure_and_owned_timeout_preserve_separate_actual_paper_management(self):
        with TemporaryDirectory(prefix='R7 bounded isolation ') as temporary:
            root=Path(temporary); log_path=root/'workers.log'
            with log_path.open('wb') as log:
                paper=spawn_owned([sys.executable,'-m','tests.product.paper_worker_fixture','paper',str(root)],
                    cwd=Path.cwd(),limits=ResourceLimits(timeout_seconds=60),stdout=log,stderr=log)
                self.addCleanup(lambda:terminate_owned(paper,deadline_seconds=5))
                first=wait_for(lambda:read(root/'heartbeat.json'))
                self.assertEqual(first['lifecycle'],'OPEN_PROTECTED')
                for kind in ('memory','timeout'):
                    target=root/kind
                    research=spawn_owned([sys.executable,'-m','tests.product.paper_worker_fixture',kind,str(target)],
                        cwd=Path.cwd(),limits=ResourceLimits(timeout_seconds=4 if kind=='timeout' else 30),stdout=log,stderr=log)
                    self.addCleanup(lambda handle=research:terminate_owned(handle,deadline_seconds=5))
                    wait_for(lambda:read(target/'fault-entered.json'))
                    if kind=='memory':
                        self.assertEqual(research.wait(timeout=10),3)
                        self.assertEqual(read(target/'fault-result.json')['status'],'MEMORY_ERROR_INJECTED')
                    else:
                        wait_for(lambda:research.termination_report)
                        self.assertEqual(research.termination_report.reason,'TIMEOUT')
                    self.assertTrue(research.termination_report.reaped)
                    self.assertIsNone(paper.process.poll())
                    self.assertTrue(process_alive(first['pid']))
                    previous=read(root/'heartbeat.json')['counter']
                    current=wait_for(lambda:(value if (value:=read(root/'heartbeat.json')) and value['counter']>previous else None))
                    self.assertEqual(current['lifecycle'],'OPEN_PROTECTED')
                (root/'close-request').write_text('explicit fixture close request',encoding='utf-8')
                result=wait_for(lambda:read(root/'paper-result.json'))
                self.assertEqual(result['status'],'CLOSED'); self.assertEqual(result['graph_status'],'READY')
                self.assertEqual(result['closed_trades'],1); self.assertEqual(Decimal(result['net_quantity']),0)
                self.assertEqual(paper.wait(timeout=10),0)
                self.assertTrue(paper.termination_report.reaped)
                self.assertFalse(process_alive(first['pid']))
                print('R7_RESOURCE_ISOLATION '+json.dumps(dict(memory_error='CONTROLLED_INJECTION',
                    actual_host_oom='NOT_RUN',research_timeout='REAPED',paper_final=result),sort_keys=True))
