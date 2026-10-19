"""Atomic cloud handoff keeps its guarantees beyond a Windows temporary MAX_PATH."""
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from application.cloud.protocol import CloudError
from application.cloud.safe_files import read_bounded, stage_author_input, write_immutable
from application.cloud.authoring import emit_package
from application.cloud.manifest import validate_package
from application.cloud.synced_folder import SyncedFolderCloudTransport
from tests.strategy.test_slice1_runtime import make_definition
import json


def fixture_path(path):
    return Path('\\\\?\\'+str(path)) if os.name=='nt' else path


class CloudLongPathTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='r7-path-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).absolute()
        # This cleanup owns exactly the freshly created fixture root, including
        # extended-path test inputs. Never enumerate/delete another directory.
        def cleanup():
            if self.root != Path(self.temp.name).absolute():
                raise AssertionError('Fresh fixture cleanup containment failed')
            shutil.rmtree(fixture_path(self.root))
        self.addCleanup(cleanup)
        count=max(20,150-len(str(self.root))-1)
        self.cloud=self.root/('中文 spaced '+('x'*(count-10)))
        fixture_path(self.cloud).mkdir()
    def test_immutable_publication_survives_a_temporary_path_longer_than_the_final_file(self):
        relative='receipts/'+('a'*64)+'/receipt.json'
        parent=self.cloud/Path(relative).parent
        self.assertGreater(len(str(parent))+47,260)
        self.assertLess(len(str(self.cloud/relative)),260)
        raw=b'{"synthetic":"PUBLIC_RECEIPT"}'
        write_immutable(self.cloud,relative,raw)
        self.assertEqual(read_bounded(self.cloud,relative,1024),raw)
        write_immutable(self.cloud,relative,raw)
        with self.assertRaises(CloudError) as caught:
            write_immutable(self.cloud,relative,b'{"synthetic":"CHANGED"}')
        self.assertEqual(caught.exception.code,'CONFLICT')
        self.assertEqual(read_bounded(self.cloud,relative,1024),raw)
    def test_opened_byte_reader_handles_actual_extended_length_parent_components(self):
        relative='reports/'+('b'*64)+'/'+('c'*64)+'/result.json'
        target=self.cloud/relative
        self.assertGreater(len(str(target)),260)
        fixture_path(target.parent).mkdir(parents=True)
        fixture_path(target).write_bytes(b'{"synthetic":"OPENED_BYTES"}')
        self.assertEqual(read_bounded(self.cloud,relative,1024),b'{"synthetic":"OPENED_BYTES"}')
    def test_author_handoff_keeps_bounded_atomic_replacement_with_a_long_temporary_path(self):
        relative='inbox/strategies/'+('d'*64)+'/strategy.json'
        self.assertGreater(len(str(self.cloud/Path(relative).parent))+47,260)
        stage_author_input(self.cloud,relative,b'{"synthetic":"FIRST"}')
        stage_author_input(self.cloud,relative,b'{"synthetic":"SECOND"}')
        self.assertEqual(read_bounded(self.cloud,relative,1024),b'{"synthetic":"SECOND"}')

    def authored(self,cloud,submission):
        fixture_path(cloud/'inbox/strategies').mkdir(parents=True,exist_ok=True)
        fixture_path(cloud/'.r7-root.json').write_bytes(b'{"root_id":"long-snapshot-fixture"}')
        return emit_package(json.dumps(make_definition()).encode(),cloud/'inbox/strategies'/submission,
            submission_id=submission,package_version='0.1')

    def test_verified_snapshot_sealing_and_idempotence_survive_full_extended_paths(self):
        authored=self.authored(self.cloud,'long-snapshot-fixture')
        transport=SyncedFolderCloudTransport(self.cloud,expected_root_id='long-snapshot-fixture')
        descriptor=tuple(transport.discover())[0]
        local=self.root/('本機 snapshots '+'l'*95)/('nested-'+'y'*64)
        expected=local/(descriptor.submission_id+'-'+authored['manifest_hash'][7:])
        self.assertGreater(len(str(expected/'manifest.json')),320)
        first=transport.snapshot(descriptor,local)
        self.assertEqual(first.root,expected)
        before={p.name:p.read_bytes() for p in fixture_path(expected).iterdir()}
        self.assertEqual(validate_package(first).strategy.content_hash,authored['strategy_content_hash'])
        again=transport.snapshot(descriptor,local)
        self.assertEqual(again.root,expected)
        self.assertEqual({p.name:p.read_bytes() for p in fixture_path(expected).iterdir()},before)
        self.assertFalse(str(first.root).startswith('\\\\?\\'))

    def test_long_cloud_discovery_and_executable_entry_scan_keep_rejection(self):
        cloud=self.cloud/('sync-layer-'+'x'*20);submission='submission-'+'s'*64
        self.authored(cloud,submission)
        folder=cloud/'inbox/strategies'/submission
        self.assertGreater(len(str(folder)),260)
        fixture_path(folder/'unapproved.py').write_bytes(b'raise RuntimeError("NEVER_EXECUTED")')
        transport=SyncedFolderCloudTransport(cloud,expected_root_id='long-snapshot-fixture')
        with self.assertRaises(CloudError) as caught:
            descriptor=tuple(transport.discover())[0]
            transport.snapshot(descriptor,self.root/'local-snapshots')
        self.assertEqual(caught.exception.code,'BLOCKED')
        self.assertEqual(caught.exception.reason,'EXECUTABLE_ARTIFACT_FORBIDDEN')
        self.assertFalse((self.root/'local-snapshots').exists())


if __name__=='__main__':
    unittest.main(verbosity=2)
