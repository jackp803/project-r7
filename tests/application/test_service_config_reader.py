"""Actual local Unicode/pinned read regressions; no native Linux claim."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from application.platform import service_guard

class ServiceConfigReaderTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[4]
        self.temp=TemporaryDirectory(prefix='service-config-',dir=project/'artifacts')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def test_actual_unicode_spaced_config_bytes_are_read_through_pinned_handle(self):
        config=self.root/'產品 設定.json'
        raw='{"note":"中文實際測試"}'.encode('utf-8');config.write_bytes(raw)
        self.assertEqual(service_guard._read_local_config(config),raw)
    def test_oversized_local_configuration_is_refused_without_full_read(self):
        config=self.root/'bounded.json';config.write_bytes(b'a'*(65536+1))
        with self.assertRaises(ValueError):service_guard._read_local_config(config)

if __name__=='__main__':unittest.main()
