"""Real local owner/lease fences for archive recovery; no provider traffic."""
import importlib
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import uuid

from application.platform.supervision import ProcessSupervisor
from tests.application import test_public_paper_feed as fixture


class PublicCaptureRecoveryTests(unittest.TestCase):
    def setUp(self):
        helper=fixture.PublicPaperFeedTests();self.path,self.config=helper.configured();self.addCleanup(helper.doCleanups)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.capture_activity'),
            'Archive recovery has no actual capture/runtime ownership fence')
        return importlib.import_module('application.paper.capture_activity')

    def test_actual_owner_fence_excludes_live_capture_and_every_kind_of_child_writer(self):
        module=self.module()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            with module.capture_activity(self.config.local_data_root):
                with self.assertRaises(ValueError):
                    with module.fenced_recovery(self.config,owner):self.fail('live capture treated as orphan')
            with module.fenced_recovery(self.config,owner):
                for kind in ('market','funding','preflight'):
                    with self.subTest(kind=kind),self.assertRaises(RuntimeError):
                        with module.capture_lease(self.config,kind):self.fail('writer entered recovery')
                with self.assertRaises(ValueError):
                    with module.capture_activity(self.config.local_data_root):self.fail('dispatch entered recovery')
            with module.capture_lease(self.config,'funding'):pass

    def test_missing_closed_foreign_role_or_nonowner_thread_cannot_recover(self):
        module=self.module()
        for owner in (None,True,object()):
            with self.subTest(owner=type(owner).__name__),self.assertRaises(ValueError):
                with module.fenced_recovery(self.config,owner):self.fail('no actual owner')
        with ProcessSupervisor(self.config,'control',config_path=self.path) as owner:
            with self.assertRaises(ValueError):
                with module.fenced_recovery(self.config,owner):self.fail('wrong role')
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            errors=[]
            def wrong_thread():
                try:
                    with module.fenced_recovery(self.config,owner):pass
                except ValueError:errors.append('REFUSED')
            worker=threading.Thread(target=wrong_thread);worker.start();worker.join(3)
            self.assertFalse(worker.is_alive());self.assertEqual(errors,['REFUSED'])
        with self.assertRaises(ValueError):
            with module.fenced_recovery(self.config,owner):self.fail('closed owner')

    def test_live_child_lease_and_unreaped_owned_handle_refuse_recovery(self):
        module=self.module()
        from application.paper import public_feed
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            with module.capture_lease(self.config,'market'):
                with self.assertRaises(RuntimeError):
                    with module.fenced_recovery(self.config,owner):self.fail('live writer ignored')
            with patch.object(public_feed,'_unreaped',[object()]),self.assertRaises(ValueError):
                with module.fenced_recovery(self.config,owner):self.fail('unreaped child ignored')

    def recovery(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.capture_recovery'),
            'There is no bounded owner-fenced prefix/rotation/orphan recovery')
        return importlib.import_module('application.paper.capture_recovery')

    def archive(self):
        from application.paper.capture_archive import PublicCaptureArchive,ROOT
        return PublicCaptureArchive(self.config.local_data_root/ROOT)

    def files(self):
        return {'request.json':b'PUBLIC_CONTROLLED_REQUEST','response.bin':b'PUBLIC_CONTROLLED_RESPONSE'}

    def reserve(self,archive):
        token=str(uuid.uuid4());archive.reserve(token,kind='funding',maximum_requests=16,
            maximum_bytes=1024*1024,maximum_files=16)
        return token

    def test_complete_commit_before_head_is_replayed_once_with_exact_counters(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        with patch.object(archive,'_save',side_effect=OSError('controlled head crash')),self.assertRaises(OSError):
            archive.commit(token,self.files(),requests=1,responses=1,complete=True)
        old_pack=archive.root/'000001.pack';old_bytes=old_pack.read_bytes()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,disposition=module.recover_public_archive(self.config,owner)
            self.assertEqual(recovered.summary()['provider_requests'],1)
            self.assertEqual(recovered.summary()['request_budget_upper'],16)
            self.assertEqual(recovered.summary()['request_accounting'],'COMPLETE')
            self.assertEqual(len(disposition['replayed_capture_indexes']),1)
            pointer=disposition['replayed_capture_indexes'][0]
            self.assertEqual(recovered.read_capture(pointer),self.files())
            repeated,again=module.recover_public_archive(self.config,owner)
            self.assertEqual(repeated.summary()['provider_requests'],1)
            self.assertEqual(again['replayed_capture_indexes'],[])
        self.assertEqual(old_pack.read_bytes(),old_bytes)

    def test_torn_suffix_stays_immutable_and_orphan_unknown_is_not_reset(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        pack=archive.root/'000001.pack'
        with pack.open('ab') as output:output.write(b'CONTROLLED_TORN_FRAME')
        damaged=pack.read_bytes()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,disposition=module.recover_public_archive(self.config,owner)
            summary=recovered.summary()
            self.assertEqual(summary['pending_reservations'],0)
            self.assertEqual(summary['request_accounting'],'INCOMPLETE')
            self.assertIsNone(summary['provider_requests'])
            self.assertEqual(summary['request_budget_upper'],16)
            self.assertIn(token,disposition['retired_orphan_reservations'])
            before={p.name:p.read_bytes() for p in archive.root.iterdir()}
            repeated,_=module.recover_public_archive(self.config,owner)
            self.assertEqual(before,{p.name:p.read_bytes() for p in archive.root.iterdir()})
            with self.assertRaisesRegex(ValueError,'INCOMPLETE'):self.reserve(repeated)
            emergency=str(uuid.uuid4())
            repeated.reserve(emergency,kind='funding',maximum_requests=1,maximum_bytes=1024*1024,
                maximum_files=16,emergency=True)
            pointer=repeated.commit(emergency,self.files(),requests=1,responses=1,complete=True)
            self.assertEqual(repeated.read_capture(pointer),self.files())
            self.assertEqual(repeated.summary()['request_accounting'],'INCOMPLETE')
        self.assertEqual(pack.read_bytes(),damaged)

    def test_interrupted_rotation_matches_original_seal_without_duplicate_bytes(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        archive.commit(token,self.files(),requests=1,responses=1,complete=True)
        with patch.object(archive,'_save',side_effect=OSError('rotation head crash')),self.assertRaises(OSError):
            with archive._locked():archive._seal()
        original=(archive.root/'000001.seal.json').read_bytes()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,_=module.recover_public_archive(self.config,owner)
            self.assertEqual(recovered.summary()['provider_requests'],1)
            self.assertEqual(recovered.summary()['sealed_segments'],1)
            self.assertEqual(recovered.summary()['request_accounting'],'COMPLETE')
        self.assertEqual((archive.root/'000001.seal.json').read_bytes(),original)

    def test_corruption_inside_committed_prefix_is_never_reclassified_as_a_crash_tail(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        archive.commit(token,self.files(),requests=1,responses=1,complete=True)
        pack=archive.root/'000001.pack';raw=pack.read_bytes();pack.write_bytes(raw[:20]+bytes([raw[20]^1])+raw[21:])
        before={p.name:p.read_bytes() for p in archive.root.iterdir()}
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner,self.assertRaises(ValueError):
            module.recover_public_archive(self.config,owner)
        self.assertEqual(before,{p.name:p.read_bytes() for p in archive.root.iterdir()})

    def test_recovery_head_write_crash_is_resumable_without_discarding_prior_tail(self):
        module=self.recovery();archive=self.archive();self.reserve(archive)
        pack=archive.root/'000001.pack'
        with pack.open('ab') as output:output.write(b'TORN')
        damaged=pack.read_bytes()
        import application.paper.capture_archive as storage
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            with patch.object(storage,'write_private_atomic',side_effect=OSError('recovery head crash')),self.assertRaises(OSError):
                module.recover_public_archive(self.config,owner)
            recovered,_=module.recover_public_archive(self.config,owner)
            self.assertEqual(recovered.summary()['request_budget_upper'],16)
            self.assertEqual(recovered.summary()['request_accounting'],'INCOMPLETE')
        self.assertEqual(pack.read_bytes(),damaged)

    def test_orphan_staging_bytes_are_archived_before_verified_loose_release(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        from application.platform.private_files import create_private_directory,write_private_new
        base=self.config.local_data_root/'public-funding-observations';create_private_directory(base)
        previous=base/str(uuid.uuid4());create_private_directory(previous)
        path=previous/token;create_private_directory(path)
        for name,raw in self.files().items():write_private_new(path/name,raw)
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,disposition=module.recover_public_archive(self.config,owner)
            pointer=disposition['archived_orphan_indexes'][token]
            self.assertEqual(recovered.read_capture(pointer),self.files())
            self.assertFalse(path.exists())
            self.assertEqual(recovered.summary()['request_budget_upper'],16)
            self.assertEqual(recovered.summary()['request_accounting'],'INCOMPLETE')

    def test_empty_orphan_directory_is_retired_without_an_invalid_empty_capture(self):
        module=self.recovery();archive=self.archive();token=self.reserve(archive)
        from application.platform.private_files import create_private_directory
        base=self.config.local_data_root/'public-funding-observations';create_private_directory(base)
        previous=base/str(uuid.uuid4());create_private_directory(previous)
        path=previous/token;create_private_directory(path)
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,disposition=module.recover_public_archive(self.config,owner)
            self.assertEqual(recovered.summary()['captures'],0)
            self.assertEqual(recovered.summary()['pending_reservations'],0)
            self.assertIn(token,disposition['retired_orphan_reservations'])

    def test_recovered_tail_and_unknown_accounting_roundtrip_private_backup_inhibited(self):
        module=self.recovery();archive=self.archive();self.reserve(archive)
        pack=archive.root/'000001.pack'
        with pack.open('ab') as output:output.write(b'PUBLIC_TORN_TAIL_RETAIN')
        from application.local_owners import LocalOwners
        with LocalOwners(self.config,namespace='LOCAL_RESEARCH').registry_factory() as registry:registry.lifecycle_counts()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,_=module.recover_public_archive(self.config,owner)
        before={p.name:p.read_bytes() for p in archive.root.iterdir()}
        from application.platform.product_backup import create_product_backup,restore_product_backup
        from application.paper.capture_archive import PublicCaptureArchive,ROOT
        from application.platform.restoration import require_valid_restoration
        from application.config import load_config
        base=self.config.local_data_root.parent
        create_product_backup(self.config,base/'backup-recovered-source')
        restore_product_backup(self.config,base/'backup-recovered-source',base/'restored-source')
        restored=PublicCaptureArchive(base/'restored-source'/ROOT)
        self.assertEqual(before,{p.name:p.read_bytes() for p in restored.root.iterdir()})
        self.assertEqual(restored.summary()['request_budget_upper'],16)
        self.assertEqual(restored.summary()['request_accounting'],'INCOMPLETE')
        self.assertEqual(require_valid_restoration(load_config(base/'restored-source/restored-product.json'))['status'],'RESTORED_INHIBITED')

    def test_short_archive_write_never_advances_committed_head_or_discards_tail(self):
        from contextlib import contextmanager
        import application.platform.product_backup as private_io
        archive=self.archive();token=self.reserve(archive);head=(archive.root/'head.json').read_bytes()
        original=private_io._opened_source
        class ShortWriter:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def write(self,raw):return self.stream.write(raw[:max(1,len(raw)//2)])
        @contextmanager
        def short(path,*,_archive_writer=False):
            with original(path,_archive_writer=_archive_writer) as stream:
                yield ShortWriter(stream) if _archive_writer else stream
        with patch.object(private_io,'_opened_source',short),self.assertRaisesRegex(OSError,'PARTIAL'):
            archive.commit(token,self.files(),requests=1,responses=1,complete=True)
        self.assertEqual((archive.root/'head.json').read_bytes(),head)
        damaged=(archive.root/'000001.pack').read_bytes()
        with ProcessSupervisor(self.config,'runtime',config_path=self.path) as owner:
            recovered,_=self.recovery().recover_public_archive(self.config,owner)
            self.assertEqual(recovered.summary()['request_accounting'],'INCOMPLETE')
        self.assertEqual((archive.root/'000001.pack').read_bytes(),damaged)

    def test_malformed_uncommitted_header_is_sealed_without_losing_management_recovery(self):
        import struct
        import zlib
        from application.datasets.catalog import canonical,digest
        cases=({'path':None},{'path':[]},{'path':'../escape'},
            {'kind':[]},{'reference':[]},{'raw_hash':[]},{'previous':None})
        for changes in cases:
            with self.subTest(changes=changes):
                # Each independent root has a genuine durable RESERVE prefix.
                helper=fixture.PublicPaperFeedTests();path,config=helper.configured()
                self.addCleanup(helper.doCleanups)
                from application.paper.capture_archive import PublicCaptureArchive,ROOT
                archive=PublicCaptureArchive(config.local_data_root/ROOT);token=self.reserve(archive)
                payload=b'PUBLIC_UNCOMMITTED_RESPONSE'
                header=dict(sequence=archive.state['sequence']+1,previous=archive.state['tip'],
                    kind='FILE',capture_id=token,path='0001-response.bin',bytes=len(payload),
                    raw_hash=digest(payload),reference=None)
                header.update(changes);encoded=canonical(header).encode();body=zlib.compress(payload)
                frame=struct.pack('!II',len(encoded),len(body))+encoded+body
                pack=archive.root/'000001.pack'
                with pack.open('ab') as output:output.write(frame)
                original=pack.read_bytes()
                with ProcessSupervisor(config,'runtime',config_path=path) as owner:
                    recovered,_=self.recovery().recover_public_archive(config,owner)
                    self.assertEqual(recovered.summary()['request_accounting'],'INCOMPLETE')
                    self.assertEqual(recovered.summary()['request_budget_upper'],16)
                    self.assertTrue((archive.root/'000001.seal.json').exists())
                    before={p.name:p.read_bytes() for p in archive.root.iterdir()}
                    repeated,_=self.recovery().recover_public_archive(config,owner)
                    self.assertEqual(before,{p.name:p.read_bytes() for p in archive.root.iterdir()})
                    emergency=str(uuid.uuid4())
                    repeated.reserve(emergency,kind='funding',maximum_requests=1,
                        maximum_bytes=1024*1024,maximum_files=16,emergency=True)
                    pointer=repeated.commit(emergency,self.files(),requests=1,responses=1,complete=True)
                    self.assertEqual(repeated.read_capture(pointer),self.files())
                self.assertEqual(pack.read_bytes(),original)


if __name__=='__main__':unittest.main()
