import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def require(test, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        test.fail(f"Required application component missing: {error.name}")


class ProductPlatformTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="R7 中文 空格 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = {
            "schema_version": "r7-product-config-v0.2",
            "product_instance_id": "test-instance",
            "local_data_root": str(self.root / "本機 資料"),
            "cloud_root": str(self.root / "雲端 暫存"),
        }

    def load(self, **changes):
        module = require(self, "application.config")
        path = self.root / "設定.json"
        path.write_text(json.dumps({**self.payload, **changes}, ensure_ascii=False), encoding="utf-8")
        return module.load_config(path)

    def test_chinese_paths_diagnostic_defaults_and_local_database(self):
        value = self.load()
        self.assertEqual(self.root / "本機 資料", value.local_data_root)
        self.assertEqual(self.root / "雲端 暫存", value.cloud_root)
        self.assertTrue(value.database_path.is_relative_to(value.local_data_root))
        self.assertEqual(1, value.research_worker_count)
        self.assertEqual("127.0.0.1", value.control_api_host)
        self.assertTrue(value.diagnostic_only)
        self.assertFalse(value.paper_runtime_enabled)

    def test_nested_roots_and_external_database_rejected_both_directions(self):
        module = require(self, "application.config")
        for changes in (
            {"cloud_root": self.payload["local_data_root"]},
            {"cloud_root": str(Path(self.payload["local_data_root"]) / "cloud")},
            {"local_data_root": str(Path(self.payload["cloud_root"]) / "db")},
            {"database_path": str(self.root / "elsewhere.sqlite3")},
        ):
            with self.subTest(changes=changes), self.assertRaises(module.ConfigError):
                self.load(**changes)

    def test_rejects_relative_paths_bad_resources_unknown_and_secret_fields(self):
        module = require(self, "application.config")
        for changes in (
            {"local_data_root": "relative"}, {"local_data_root": "C:relative"},
            {"research_worker_count": 0}, {"research_worker_count": True},
            {"scan_interval": 0}, {"control_api_port": 70000},
            {"control_api_host": "0.0.0.0"}, {"api_key": "synthetic-forbidden"},
        ):
            with self.subTest(changes=changes), self.assertRaises(module.ConfigError):
                self.load(**changes)

    def test_duplicate_json_keys_and_missing_config_do_not_initialize_data(self):
        module = require(self, "application.config")
        path = self.root / "duplicate.json"
        path.write_text('{"schema_version":"x","schema_version":"y"}', encoding="utf-8")
        with self.assertRaises(module.ConfigError):
            module.load_config(path)
        self.assertFalse(Path(self.payload["local_data_root"]).exists())

    def test_optional_cloud_is_not_silently_initialized(self):
        value = self.load(cloud_root=None)
        self.assertIsNone(value.cloud_root)
        self.assertFalse(Path(self.payload["local_data_root"]).exists())

    def test_network_database_volume_is_rejected_before_initialization(self):
        module = require(self, "application.config")
        for filesystem in ("nfs", "nfs4", "cifs", "fuse.rclone", "smbfs"):
            with self.subTest(filesystem=filesystem), patch("application.platform.resources._filesystem", return_value=filesystem):
                with self.assertRaises(module.ConfigError):
                    self.load()
        self.assertFalse(Path(self.payload["local_data_root"]).exists())

    def test_hardware_doctor_emits_measured_json_without_initializing_data(self):
        module = require(self, "application.cli")
        from contextlib import redirect_stdout
        from io import StringIO
        output = StringIO()
        with redirect_stdout(output):
            code = module.main(["doctor", "--hardware", "--data-root", str(self.root), "--json"])
        self.assertEqual(0, code)
        result = json.loads(output.getvalue())
        self.assertEqual("NOT_REQUIRED", result["gpu_status"])
        self.assertGreater(result["physical_memory_bytes"], 0)

    def test_measured_hardware_has_positive_memory_cpu_disk_and_no_gpu_requirement(self):
        module = require(self, "application.platform.resources")
        hardware = module.inspect_hardware(self.root)
        self.assertGreater(hardware.physical_memory_bytes, 0)
        self.assertGreater(hardware.available_memory_bytes, 0)
        self.assertGreater(hardware.logical_cores, 0)
        self.assertGreater(hardware.disk_free_bytes, 0)
        self.assertTrue(hardware.cpu_model)
        self.assertEqual("NOT_REQUIRED", hardware.gpu_status)

    def test_resource_pressure_blocks_research_with_measured_boundaries(self):
        module = require(self, "application.platform.resources")
        policy = module.ResourcePolicy.conservative(24 * 1024**3)
        self.assertEqual(8 * 1024**3, policy.memory_soft_budget_bytes)
        self.assertEqual(1, policy.worker_count)
        good = policy.admission(available_memory_bytes=8 * 1024**3, disk_free_bytes=4 * 1024**3, disk_total_bytes=40 * 1024**3)
        self.assertTrue(good.allowed)
        low_memory = policy.admission(available_memory_bytes=1 * 1024**3, disk_free_bytes=4 * 1024**3, disk_total_bytes=40 * 1024**3)
        self.assertFalse(low_memory.allowed)
        self.assertIn("RESEARCH_MEMORY_PRESSURE", low_memory.reason_codes)
        low_disk = policy.admission(available_memory_bytes=8 * 1024**3, disk_free_bytes=1 * 1024**3, disk_total_bytes=40 * 1024**3)
        self.assertFalse(low_disk.allowed)
        self.assertIn("RESEARCH_DISK_PRESSURE", low_disk.reason_codes)
