from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack

from registry import EvidenceGateError, StrategyIdentity
from storage import open_sqlite_platform
from tests.application.test_platform import require
from tests.application.cloud_fixtures import package
import json
from concurrent.futures import ThreadPoolExecutor

NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


class ClaimRecoveryTests(unittest.TestCase):
    def test_two_local_workers_acquire_only_one_claim(self):
        module=require(self,"application.intake.ledger")
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"app.sqlite3"
            with module.IntakeLedger(path,instance_id="fixture"):
                pass
            def claim(owner):
                with module.IntakeLedger(path,instance_id="fixture") as ledger:
                    return ledger.claim("s1","sha256:"+"a"*64,owner,NOW)
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(claim,["worker1","worker2"]))
            self.assertEqual(1,sum(result.acquired for result in results))
            self.assertEqual(1,len({result.owner_id for result in results}))
    def test_crash_after_outbox_commit_repeated_scans_and_changed_submission(self):
        service_module = require(self, "application.intake.service")
        cloud_module = require(self, "application.cloud.synced_folder")
        ledger_module = require(self, "application.intake.ledger")
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root=Path(temp)
            cloud=root/"cloud"
            cloud.mkdir()
            (cloud/".r7-root.json").write_text('{"root_id":"fixture"}',encoding="utf-8")
            folder,manifest,_=package(cloud)
            e6=stack.enter_context(open_sqlite_platform(root/"e6.sqlite3"))
            ledger=stack.enter_context(ledger_module.IntakeLedger(root/"app.sqlite3",instance_id="fixture"))
            transport=cloud_module.SyncedFolderCloudTransport(cloud,expected_root_id="fixture")
            def crash(point):
                if point == "AFTER_OUTBOX_COMMIT": raise RuntimeError("injected local crash")
            inbox=service_module.StrategyInboxService(transport,ledger,e6,snapshot_root=root/"snapshots",owner_id="worker1",fault_hook=crash)
            with self.assertRaises(RuntimeError): inbox.scan_once(NOW)
            self.assertEqual(1,len(ledger.pending_outbox(10)))
            reopened=stack.enter_context(ledger_module.IntakeLedger(root/"app.sqlite3",instance_id="fixture"))
            resumed=service_module.StrategyInboxService(transport,reopened,e6,snapshot_root=root/"snapshots",owner_id="worker2")
            self.assertEqual(1,resumed.scan_once(NOW+timedelta(seconds=1)).idempotent)
            manifest["research_hypothesis"]="changed immutable author material"
            (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            self.assertEqual(1,resumed.scan_once(NOW+timedelta(seconds=2)).conflicts)
            self.assertEqual(1,len(reopened.pending_outbox(10)))

    def test_expired_lease_changes_generation_and_stale_worker_cannot_commit(self):
        module = require(self, "application.intake.ledger")
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            ledger = stack.enter_context(module.IntakeLedger(Path(temp) / "app.sqlite3", instance_id="fixture"))
            first = ledger.claim("s1", "sha256:" + "a"*64, "worker1", NOW)
            self.assertTrue(first.acquired)
            busy = ledger.claim("s1", first.manifest_hash, "worker2", NOW + timedelta(seconds=1))
            self.assertFalse(busy.acquired)
            second = ledger.claim("s1", first.manifest_hash, "worker2", NOW + timedelta(seconds=61))
            self.assertGreater(second.lease_generation, first.lease_generation)
            with self.assertRaises(module.LeaseConflict):
                ledger.commit_effect(first, "e6:receipt", b'{}', now=NOW + timedelta(seconds=62))
            result = ledger.commit_effect(second, "e6:receipt", b'{}', now=NOW + timedelta(seconds=62))
            self.assertEqual("INTAKE_ACCEPTED", result.state)
            with self.assertRaises(module.ManifestConflict):
                ledger.claim("s1", "sha256:" + "b"*64, "worker2", NOW + timedelta(seconds=63))

    def test_restart_after_real_e6_registration_reuses_one_canonical_effect_and_receipt(self):
        service_module = require(self, "application.intake.service")
        cloud_module = require(self, "application.cloud.synced_folder")
        ledger_module = require(self, "application.intake.ledger")
        with tempfile.TemporaryDirectory(prefix="R7 重啟 ") as temp, ExitStack() as stack:
            root = Path(temp)
            cloud = root / "cloud"
            cloud.mkdir()
            (cloud / ".r7-root.json").write_text('{"root_id":"fixture"}', encoding="utf-8")
            _, _, definition = package(cloud)
            e6 = stack.enter_context(open_sqlite_platform(root / "e6.sqlite3"))
            ledger = stack.enter_context(ledger_module.IntakeLedger(root / "app.sqlite3", instance_id="fixture"))
            transport = cloud_module.SyncedFolderCloudTransport(cloud, expected_root_id="fixture")
            def crash(point):
                if point == "AFTER_E6_INTAKE":
                    raise RuntimeError("injected local crash")
            inbox = service_module.StrategyInboxService(transport, ledger, e6, snapshot_root=root / "snapshots", owner_id="worker1", fault_hook=crash)
            with self.assertRaises(RuntimeError):
                inbox.scan_once(NOW)
            identity = StrategyIdentity(definition["strategy_id"], definition["strategy_version"])
            original = e6.intake(definition, source_actor="R7_INTAKE:fixture", operation_id=ledger.operation_key("submission-1"))
            self.assertEqual("DRAFT", original.strategy.current_lifecycle_state)
            with self.assertRaises(EvidenceGateError):
                e6.begin_backtesting(identity, actor="fixture")
            resumed = service_module.StrategyInboxService(transport, ledger, e6, snapshot_root=root / "snapshots", owner_id="worker2")
            result = resumed.scan_once(NOW + timedelta(seconds=61))
            self.assertEqual(1, result.accepted)
            self.assertEqual(original.receipt.intake_id, ledger.get_submission("submission-1").effect_ref)
            repeated = resumed.scan_once(NOW + timedelta(seconds=62))
            self.assertEqual(1, repeated.idempotent)
            self.assertEqual(1, len(ledger.pending_outbox(10)))

    def test_incomplete_sync_backoff_is_durable_bounded_and_stalls_after_one_day(self):
        module = require(self, "application.intake.ledger")
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            path = Path(temp) / "app.sqlite3"
            ledger = stack.enter_context(module.IntakeLedger(path, instance_id="fixture"))
            self.assertTrue(hasattr(ledger, "retry_allowed"), "Durable sync retry admission is missing")
            ledger.observe("s1", "INCOMPLETE_SYNC", "ARTIFACT_MISSING", NOW, "sha256:" + "a"*64)
            self.assertFalse(ledger.retry_allowed("s1", NOW + timedelta(seconds=1)))
            self.assertTrue(ledger.retry_allowed("s1", NOW + timedelta(seconds=5)))
            reopened = stack.enter_context(module.IntakeLedger(path, instance_id="fixture"))
            self.assertFalse(reopened.retry_allowed("s1", NOW + timedelta(seconds=4)))
            status = reopened.observe("s1", "INCOMPLETE_SYNC", "ARTIFACT_MISSING", NOW + timedelta(days=1), "sha256:" + "a"*64)
            self.assertEqual("SYNC_STALLED", status)
            self.assertFalse(reopened.retry_allowed("s1", NOW + timedelta(days=1, hours=1)))
