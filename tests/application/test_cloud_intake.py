import json
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
from unittest.mock import patch

from tests.application.test_platform import require
from tests.application.cloud_fixtures import package


class CloudIntakeTests(unittest.TestCase):
    def test_readonly_local_snapshot_root_is_operational_unavailable(self):
        protocol=require(self,"application.cloud.protocol")
        package(self.cloud)
        with patch.object(Path,"mkdir",side_effect=PermissionError("injected readonly snapshot root")):
            with self.assertRaises(protocol.CloudError) as caught:
                self.snapshot()
        self.assertEqual("UNAVAILABLE",caught.exception.code)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="R7 雲端 封包 ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cloud = self.root / "雲端 空格"
        self.cloud.mkdir()
        (self.cloud / ".r7-root.json").write_text('{"root_id":"offline-fixture"}', encoding="utf-8")

    def transport(self):
        return require(self, "application.cloud.synced_folder").SyncedFolderCloudTransport(
            self.cloud, expected_root_id="offline-fixture")

    def snapshot(self):
        transport = self.transport()
        descriptor = tuple(transport.discover())[0]
        return transport.snapshot(descriptor, self.root / "local/snapshots")

    def test_separate_manifest_versions_parse_sealed_bytes_through_real_e2(self):
        module = require(self, "application.cloud.manifest")
        for version in ("0.1", "0.2"):
            with self.subTest(version=version):
                folder, manifest, definition = package(self.cloud, "submission-" + version, version=version)
                descriptors = {item.submission_id:item for item in self.transport().discover()}
                snapshot = self.transport().snapshot(descriptors[manifest["submission_id"]], self.root / "snapshots")
                verified = module.validate_package(snapshot)
                self.assertEqual(definition["content_hash"], verified.strategy.content_hash)
                self.assertEqual(manifest["submission_id"], verified.manifest.submission_id)
                self.assertFalse(verified.compatibility_execution_pass)
                (folder / "strategy.json").write_text("changed cloud bytes", encoding="utf-8")
                self.assertEqual(definition["content_hash"], module.validate_package(snapshot).strategy.content_hash)

    def test_missing_and_mismatched_payload_are_incomplete_not_statistical_failure(self):
        module = require(self, "application.cloud.protocol")
        folder, _, _ = package(self.cloud)
        (folder / "strategy.json").unlink()
        with self.assertRaises(module.CloudError) as caught:
            self.snapshot()
        self.assertEqual("INCOMPLETE_SYNC", caught.exception.code)
        (folder / "strategy.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(module.CloudError) as caught:
            self.snapshot()
        self.assertEqual("INCOMPLETE_SYNC", caught.exception.code)

    def test_bad_paths_unknown_fields_duplicate_keys_and_secrets_block_without_echo(self):
        protocol = require(self, "application.cloud.protocol")
        folder, original, _ = package(self.cloud)
        for changes in ({"strategy_definition_file":"../private.json"}, {"strategy_definition_file":"C:/private.json"},
                        {"strategy_definition_file":"NUL.json"}, {"strategy_definition_file":"策略.json"},
                        {"api_secret":"SYNTHETIC_DO_NOT_ECHO"}, {"verification_status":"PASS"}):
            with self.subTest(changes=changes):
                (folder / "manifest.json").write_text(json.dumps({**original, **changes}), encoding="utf-8")
                with self.assertRaises(protocol.CloudError) as caught:
                    self.snapshot()
                self.assertEqual("BLOCKED", caught.exception.code)
                self.assertNotIn("SYNTHETIC_DO_NOT_ECHO", str(caught.exception))
        (folder / "manifest.json").write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaises(protocol.CloudError) as caught:
            self.snapshot()
        self.assertEqual("BLOCKED", caught.exception.code)

    def test_missing_root_marker_does_not_initialize_replacement_cloud(self):
        protocol = require(self, "application.cloud.protocol")
        (self.cloud / ".r7-root.json").unlink()
        with self.assertRaises(protocol.CloudError) as caught:
            tuple(self.transport().discover())
        self.assertEqual("CLOUD_NOT_CONNECTED", caught.exception.code)
        self.assertEqual([], list(self.cloud.iterdir()))

    def test_corrupt_snapshot_rejected_and_case_collision_payloads_blocked(self):
        protocol = require(self, "application.cloud.protocol")
        manifest_module = require(self, "application.cloud.manifest")
        folder, manifest, _ = package(self.cloud, version="0.2")
        snapshot = self.snapshot()
        snapshot.payload_paths["strategy_definition"].write_text("{}", encoding="utf-8")
        with self.assertRaises(protocol.CloudError) as caught:
            manifest_module.validate_package(snapshot)
        self.assertEqual("SNAPSHOT_CORRUPT", caught.exception.code)
        manifest["payloads"].append({**manifest["payloads"][0], "role":"research_notes", "relative_path":"STRATEGY.JSON", "media_type":"text/markdown"})
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(protocol.CloudError) as caught:
            self.snapshot()
        self.assertEqual("BLOCKED", caught.exception.code)

    def test_native_directory_link_escape_is_blocked_without_reading_target(self):
        protocol = require(self, "application.cloud.protocol")
        folder, manifest, _ = package(self.cloud)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "strategy.json").write_bytes((folder / "strategy.json").read_bytes())
        link = folder / "escape"
        if os.name == "nt":
            subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(outside)],
                           shell=False, check=True, capture_output=True)
        else:
            link.symlink_to(outside, target_is_directory=True)
        manifest["strategy_definition_file"] = "escape/strategy.json"
        (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(protocol.CloudError) as caught:
            self.snapshot()
        self.assertEqual("BLOCKED", caught.exception.code)
        self.assertTrue((outside / "strategy.json").exists())
