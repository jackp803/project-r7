from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from contextlib import ExitStack
import errno

from tests.application.test_platform import require


class OutboxTests(unittest.TestCase):
    def test_outbox_capacity_blocks_new_effect_and_keeps_existing_evidence(self):
        module=require(self,"application.intake.ledger")
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            ledger=stack.enter_context(module.IntakeLedger(Path(temp)/"app.sqlite3",instance_id="fixture",outbox_max_items=1))
            now=datetime(2026,10,2,tzinfo=timezone.utc)
            first=ledger.claim("s1","sha256:"+"a"*64,"worker1",now)
            ledger.commit_effect(first,"first",b'{}',now=now)
            second=ledger.claim("s2","sha256:"+"b"*64,"worker1",now)
            with self.assertRaises(module.OutboxCapacityError):
                ledger.commit_effect(second,"second",b'{}',now=now)
            self.assertEqual("CLAIMED",ledger.get_submission("s2").state)
            self.assertEqual(["s1"],[item.submission_id for item in ledger.pending_outbox(10)])

    def test_crash_after_upload_before_ack_restarts_with_same_artifact(self):
        ledger_module = require(self,"application.intake.ledger")
        publisher_module = require(self,"application.cloud.publisher")
        transport_module = require(self,"application.cloud.synced_folder")
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            root=Path(temp)
            cloud=root/"cloud"
            cloud.mkdir()
            (cloud/".r7-root.json").write_text('{"root_id":"fixture"}',encoding="utf-8")
            ledger=stack.enter_context(ledger_module.IntakeLedger(root/"app.sqlite3",instance_id="fixture"))
            now=datetime(2026,10,2,tzinfo=timezone.utc)
            claim=ledger.claim("s1","sha256:"+"a"*64,"worker1",now)
            ledger.commit_effect(claim,"intake-local-id",b'{}',now=now)
            transport=transport_module.SyncedFolderCloudTransport(cloud,expected_root_id="fixture")
            def crash(point):
                if point == "AFTER_UPLOAD_BEFORE_ACK": raise RuntimeError("injected local crash")
            with self.assertRaises(RuntimeError): publisher_module.Publisher(ledger,transport,fault_hook=crash).flush(10)
            self.assertEqual("PENDING",ledger.pending_outbox(10)[0].state)
            reopened=stack.enter_context(ledger_module.IntakeLedger(root/"app.sqlite3",instance_id="fixture"))
            result=publisher_module.Publisher(reopened,transport).flush(10)
            self.assertEqual(1,result.local_staged)
            self.assertEqual(0,result.cloud_acknowledged)
            self.assertEqual(1,len(list(cloud.glob("receipts/**/receipt.json"))))

    def test_partial_payload_write_is_not_finalized_and_can_be_retried(self):
        protocol = require(self, "application.cloud.protocol")
        transport_module = require(self, "application.cloud.synced_folder")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".r7-root.json").write_text('{"root_id":"fixture"}', encoding="utf-8")
            def disk_full(point):
                if point == "AFTER_PARTIAL_STAGE_WRITE":
                    raise OSError(errno.ENOSPC, "injected local disk full")
            transport = transport_module.SyncedFolderCloudTransport(root, expected_root_id="fixture", fault_hook=disk_full)
            bundle = protocol.ArtifactBundle("receipts/fixture/s1/g1", {"receipt.json":b'{"status":"DRAFT"}'})
            with self.assertRaises(protocol.CloudError) as caught:
                transport.publish(bundle, "op1")
            self.assertEqual("UNAVAILABLE", caught.exception.code)
            self.assertFalse((root / bundle.logical_path / "receipt.json").exists())
            retried = transport_module.SyncedFolderCloudTransport(root, expected_root_id="fixture")
            self.assertEqual("LOCAL_STAGED", retried.publish(bundle, "op1").status)
            self.assertEqual(bundle.payloads["receipt.json"], (root / bundle.logical_path / "receipt.json").read_bytes())
    def test_local_copy_never_claims_remote_ack_and_retries_are_content_idempotent(self):
        ledger_module = require(self, "application.intake.ledger")
        publisher_module = require(self, "application.cloud.publisher")
        transport_module = require(self, "application.cloud.synced_folder")
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            root = Path(temp)
            cloud = root / "cloud"
            cloud.mkdir()
            (cloud / ".r7-root.json").write_text('{"root_id":"fixture"}', encoding="utf-8")
            ledger = stack.enter_context(ledger_module.IntakeLedger(root / "app.sqlite3", instance_id="fixture"))
            now = datetime(2026, 10, 2, tzinfo=timezone.utc)
            claim = ledger.claim("s1", "sha256:" + "a"*64, "worker1", now)
            ledger.commit_effect(claim, "intake-local-id", b'{"status":"DRAFT"}', now=now)
            publisher = publisher_module.Publisher(ledger, transport_module.SyncedFolderCloudTransport(cloud, expected_root_id="fixture"))
            first = publisher.flush(10)
            self.assertEqual(1, first.local_staged)
            self.assertEqual(0, first.cloud_acknowledged)
            second = publisher.flush(10)
            self.assertEqual(1, second.local_staged)
            self.assertEqual(0, second.cloud_acknowledged)
            self.assertEqual(1, len(list((cloud / "receipts").glob("**/receipt.json"))))

    def test_publication_content_conflict_does_not_overwrite(self):
        protocol = require(self, "application.cloud.protocol")
        transport_module = require(self, "application.cloud.synced_folder")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".r7-root.json").write_text('{"root_id":"fixture"}', encoding="utf-8")
            transport = transport_module.SyncedFolderCloudTransport(root, expected_root_id="fixture")
            bundle = protocol.ArtifactBundle("receipts/fixture/s1/g1", {"receipt.json":b'{}'})
            self.assertEqual("LOCAL_STAGED", transport.publish(bundle, "op1").status)
            with self.assertRaises(protocol.CloudError) as caught:
                transport.publish(protocol.ArtifactBundle(bundle.logical_path, {"receipt.json":b'{"different":true}'}), "op1")
            self.assertEqual("CONFLICT", caught.exception.code)
            self.assertEqual(b'{}', (root / bundle.logical_path / "receipt.json").read_bytes())

    def test_wrong_transport_ack_hash_is_not_accepted(self):
        protocol = require(self, "application.cloud.protocol")
        ledger_module = require(self, "application.intake.ledger")
        publisher_module = require(self, "application.cloud.publisher")
        class WrongTransport:
            def publish(self, bundle, operation_id):
                return protocol.PublishReceipt(operation_id, "CLOUD_ACKNOWLEDGED", "sha256:" + "b"*64)
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            ledger = stack.enter_context(ledger_module.IntakeLedger(Path(temp) / "app.sqlite3", instance_id="fixture"))
            now = datetime(2026, 10, 2, tzinfo=timezone.utc)
            claim = ledger.claim("s1", "sha256:" + "a"*64, "worker1", now)
            ledger.commit_effect(claim, "intake-local-id", b'{}', now=now)
            result = publisher_module.Publisher(ledger, WrongTransport()).flush(10)
            self.assertEqual(0, result.cloud_acknowledged)
            self.assertEqual(1, result.unavailable)
