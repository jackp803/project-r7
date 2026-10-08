"""Actual Windows reader-sharing behavior of isolated fixture heartbeats."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from unittest.mock import patch

from tests.product.paper_worker_fixture import publish


class PaperWorkerFixturePublishTests(unittest.TestCase):
    def test_heartbeat_replaces_atomically_after_an_existing_reader_releases(self):
        with TemporaryDirectory(prefix='R7 fixture publish ') as temporary:
            path=Path(temporary)/'heartbeat.json'
            publish(path,dict(counter=1)); failures=[]; finished=threading.Event()
            def writer():
                try: publish(path,dict(counter=2))
                except BaseException as exc: failures.append(exc)
                finally: finished.set()
            with path.open('r',encoding='utf-8') as reader:
                thread=threading.Thread(target=writer);thread.start()
                try:
                    if os.name=='nt':
                        self.assertFalse(finished.wait(.1),'The writer must survive a transient Windows reader lock')
                    else:
                        self.assertTrue(finished.wait(2))
                    self.assertEqual(json.loads(reader.read()),dict(counter=1))
                finally:
                    reader.close();thread.join(7)
            self.assertFalse(thread.is_alive());self.assertEqual(failures,[])
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),dict(counter=2))
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_unrelated_replace_permission_error_propagates_without_retry(self):
        with TemporaryDirectory(prefix='R7 fixture publish denial ') as temporary:
            path=Path(temporary)/'heartbeat.json';publish(path,dict(counter=1))
            denied=PermissionError('explicit unrelated fixture denial')
            with patch.object(Path,'replace',side_effect=denied) as replace:
                with self.assertRaises(PermissionError) as raised:publish(path,dict(counter=2))
            self.assertIs(raised.exception,denied);self.assertEqual(replace.call_count,1)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),dict(counter=1))

    if os.name=='nt':
        def test_permanent_windows_reader_lock_fails_within_finite_publish_deadline(self):
            with TemporaryDirectory(prefix='R7 fixture publish bound ') as temporary:
                path=Path(temporary)/'heartbeat.json';publish(path,dict(counter=1))
                with path.open('r',encoding='utf-8') as reader:
                    started=time.monotonic()
                    with self.assertRaises(PermissionError):publish(path,dict(counter=2))
                    elapsed=time.monotonic()-started
                    self.assertGreaterEqual(elapsed,5)
                    self.assertLess(elapsed,7)
                    self.assertEqual(json.loads(reader.read()),dict(counter=1))
                self.assertEqual(json.loads(path.read_text(encoding='utf-8')),dict(counter=1))


if __name__=='__main__':unittest.main()
