"""Request validity through real package verification, ledger and E6 intake."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from unittest.mock import patch

from application.cloud.authoring import emit_package
from application.cloud.manifest import canonical_bytes
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.intake.ledger import IntakeLedger
from application.intake.service import StrategyInboxService
from storage import open_sqlite_platform
from strategy.v02.capabilities import build_capability_snapshot
from tests.strategy.v02_fixtures import definition_v02

NOW=datetime(2026,10,5,tzinfo=timezone.utc)
UNTIL=NOW+timedelta(hours=4)
def z(value):return value.isoformat().replace('+00:00','Z')

class SubmissionValidityIntakeTests(unittest.TestCase):
    @contextmanager
    def fixture(self,*,intent='TACTICAL_STRATEGY'):
        with TemporaryDirectory(prefix='R7 submission validity ') as temporary:
            root=Path(temporary);cloud=root/'cloud';cloud.mkdir()
            (cloud/'.r7-root.json').write_bytes(canonical_bytes(dict(root_id='fixture')))
            parent=cloud/'inbox/strategies';parent.mkdir(parents=True)
            emit_package(definition_v02(),parent/'tactical',submission_id='tactical',intent_class=intent,
                         validity={'from':z(NOW),'until':z(UNTIL)})
            with IntakeLedger(root/'app.sqlite',instance_id='fixture') as ledger,open_sqlite_platform(root/'e6.sqlite') as e6:
                inbox=StrategyInboxService(SyncedFolderCloudTransport(cloud,expected_root_id='fixture'),ledger,e6,
                    snapshot_root=root/'snapshots',owner_id='worker',capability_snapshot_hash=build_capability_snapshot().snapshot_hash)
                yield inbox,ledger,e6,parent/'tactical'

    def test_expired_submission_is_terminal_observation_without_e6_or_receipt(self):
        with self.fixture() as (inbox,ledger,e6,_):
            for instant in (UNTIL,UNTIL+timedelta(seconds=1)):
                summary=inbox.scan_once(instant)
                self.assertEqual(summary.results[0].state,'EXPIRED')
                self.assertEqual(summary.results[0].reason_codes,('SUBMISSION_EXPIRED',))
                self.assertEqual(summary.accepted,0)
            self.assertEqual(ledger.submission_view('tactical')['state'],'EXPIRED')
            self.assertIsNone(ledger.get_submission('tactical'))
            self.assertIsNone(ledger.accepted_receipt('tactical'))
            self.assertEqual(ledger.pending_outbox(10),())
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)

    def test_exclusive_upper_boundary_keeps_prior_immutable_receipt_and_draft(self):
        with self.fixture() as (inbox,ledger,e6,_):
            self.assertEqual(inbox.scan_once(UNTIL-timedelta(microseconds=1)).accepted,1)
            receipt=ledger.accepted_receipt('tactical')
            self.assertEqual(inbox.scan_once(UNTIL).results[0].state,'EXPIRED')
            view=ledger.submission_view('tactical')
            self.assertEqual(view['state'],'INTAKE_ACCEPTED')
            self.assertEqual(view['latest_observation']['state'],'EXPIRED')
            self.assertEqual(view['receipt'],receipt)
            self.assertEqual(e6.lifecycle_counts()['DRAFT'],1)
            self.assertEqual(len(ledger.pending_outbox(10)),1)

    def test_future_submission_is_blocked_until_actual_validity_boundary(self):
        with self.fixture() as (inbox,ledger,e6,_):
            outcome=inbox.scan_once(NOW-timedelta(microseconds=1)).results[0]
            self.assertEqual(outcome.state,'BLOCKED')
            self.assertEqual(outcome.reason_codes,('SUBMISSION_NOT_YET_VALID',))
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)
            self.assertEqual(inbox.scan_once(NOW).accepted,1)
            self.assertEqual(e6.lifecycle_counts()['DRAFT'],1)

    def test_partial_payload_recovered_after_expiry_cannot_create_intake_effect(self):
        with self.fixture() as (inbox,ledger,e6,folder):
            payload=(folder/'strategy.json').read_bytes()
            (folder/'strategy.json').write_bytes(payload[:17])
            self.assertEqual(inbox.scan_once(UNTIL-timedelta(seconds=1)).results[0].state,'INCOMPLETE_SYNC')
            (folder/'strategy.json').write_bytes(payload)
            self.assertEqual(inbox.scan_once(UNTIL+timedelta(seconds=5)).results[0].state,'EXPIRED')
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)
            self.assertEqual(ledger.pending_outbox(10),())

    def test_finite_evergreen_interval_also_stops_new_expired_submission(self):
        with self.fixture(intent='EVERGREEN_STRATEGY') as (inbox,ledger,e6,_):
            self.assertEqual(inbox.scan_once(UNTIL).results[0].state,'EXPIRED')
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)
            self.assertIsNone(ledger.get_submission('tactical'))

    def test_snapshot_manifest_replacement_cannot_use_old_validity(self):
        with self.fixture() as (inbox,ledger,e6,folder):
            snapshot=inbox.transport.snapshot
            def replace(descriptor,root):
                path=folder/'manifest.json';manifest=json.loads(path.read_bytes())
                manifest['validity']={'from':z(NOW-timedelta(hours=2)),'until':z(NOW-timedelta(hours=1))}
                path.write_text(json.dumps(manifest),encoding='utf-8')
                return snapshot(descriptor,root)
            with patch.object(inbox.transport,'snapshot',side_effect=replace):
                result=inbox.scan_once(NOW).results[0]
            self.assertEqual(result.state,'INCOMPLETE_SYNC')
            self.assertEqual(result.reason_codes,('MANIFEST_CHANGED_DURING_SNAPSHOT',))
            self.assertIsNone(ledger.get_submission('tactical'))
            self.assertIsNone(ledger.accepted_receipt('tactical'))
            self.assertEqual(sum(e6.lifecycle_counts().values()),0)
            self.assertEqual(ledger.pending_outbox(10),())
            self.assertEqual(inbox.scan_once(NOW+timedelta(seconds=6)).results[0].state,'EXPIRED')
