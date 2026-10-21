"""Actual local archive bytes/counters, controlled caps, no provider traffic."""
import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import uuid


class PublicCaptureArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary=TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)/'archive'

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.capture_archive'),
            'Cross-generation bounded immutable public capture archive is unavailable')
        return importlib.import_module('application.paper.capture_archive')

    def archive(self, **kwargs):
        return self.module().PublicCaptureArchive(self.root,**kwargs)

    def files(self):
        return {'request.json':b'{"owner":"actual-generation"}',
            'requests/001-attempt.json':b'{"method":"GET","authentication":"NONE"}',
            'requests/001-response.bin':b'{"settled":"0.0001"}',
            'requests/001-result.json':b'{"status":200}',
            'acquisition.json':b'{"requests":1,"responses":1}'}

    def record(self, archive, files=None, *, kind='funding', complete=True):
        token=str(uuid.uuid4()); files=self.files() if files is None else files
        archive.reserve(token,kind=kind,maximum_requests=16,maximum_bytes=1024*1024)
        return archive.commit(token,files,requests=1,responses=1,complete=complete)

    def test_exact_bytes_immutable_index_and_counters_survive_new_owner(self):
        archive=self.archive(); pointer=self.record(archive)
        self.assertEqual(archive.read_capture(pointer),self.files())
        successor=self.archive()
        self.assertEqual(successor.read_capture(pointer),self.files())
        self.assertEqual(successor.summary()['provider_requests'],1)
        self.assertEqual(successor.summary()['provider_responses'],1)
        self.assertEqual(successor.summary()['pending_reservations'],0)
        self.record(successor,kind='market')
        self.assertEqual(self.archive().summary()['provider_requests'],2)

    def test_identical_responses_reference_preserved_original_without_losing_attempts(self):
        archive=self.archive(); first=self.record(archive); second=self.record(archive)
        self.assertEqual(archive.read_capture(first),archive.read_capture(second))
        summary=archive.summary()
        self.assertEqual(summary['provider_requests'],2)
        self.assertGreater(summary['deduplicated_payload_bytes'],0)
        self.assertGreater(summary['physical_bytes'],0)

    def test_restart_verifies_exact_commit_file_index_during_linear_scan(self):
        from application.datasets.catalog import canonical
        archive=self.archive();token=str(uuid.uuid4())
        archive.reserve(token,kind='funding',maximum_requests=16,maximum_bytes=1024*1024)
        with archive._locked(),archive._writing():
            pointer=archive._append('FILE',token,'actual.json',b'PUBLIC_EXACT_FILE')
            archive._append('COMMIT',token,'',canonical(dict(files={'wrong.json':pointer},
                requests=1,responses=1,complete=True)).encode())
        with self.assertRaisesRegex(ValueError,'INDEX'):self.archive()

    def test_restart_dedup_verification_uses_only_preceding_verified_originals(self):
        archive=self.archive()
        for _ in range(5):self.record(archive)
        with patch.object(self.module().PublicCaptureArchive,'_read_pointer',
                side_effect=AssertionError('Full-volume verification must not reopen every dedup original')):
            successor=self.archive()
        self.assertEqual(successor.summary()['provider_requests'],5)

    def test_valid_seal_keeps_ordered_hash_chain_and_bounded_external_file_count(self):
        archive=self.archive()
        with patch.object(self.module(),'MAX_FRAMES',6):
            pointers=[self.record(archive) for _ in range(8)]
        successor=self.archive()
        for pointer in pointers: self.assertEqual(successor.read_capture(pointer),self.files())
        self.assertGreater(successor.summary()['sealed_segments'],0)
        self.assertLess(len(list(self.root.iterdir())),30)

    def test_reservation_refuses_before_dispatch_on_total_or_disk_pressure(self):
        module=self.module(); archive=self.archive()
        with patch.object(module,'MAX_TOTAL_BYTES',1024):
            with self.assertRaisesRegex(ValueError,'CAPACITY'):
                archive.reserve(str(uuid.uuid4()),kind='market',maximum_requests=165,maximum_bytes=2*1024*1024)
        with patch.object(module.shutil,'disk_usage',return_value=type('Disk',(),{'free':1})()):
            with self.assertRaisesRegex(ValueError,'DISK'):
                archive.reserve(str(uuid.uuid4()),kind='funding',maximum_requests=16,maximum_bytes=100)
        self.assertEqual(archive.summary()['provider_requests'],0)

    def test_shared_market_funding_preflight_reservations_not_reset_on_restart(self):
        archive=self.archive(); ids=[]
        for kind in ('market','funding','preflight'):
            token=str(uuid.uuid4()); ids.append(token)
            archive.reserve(token,kind=kind,maximum_requests=16,maximum_bytes=1024)
        successor=self.archive()
        self.assertEqual(successor.summary()['reserved_bytes'],3072)
        with self.assertRaisesRegex(ValueError,'PENDING'):
            successor.reserve(str(uuid.uuid4()),kind='market',maximum_requests=1,maximum_bytes=1024)
        self.assertEqual(successor.summary()['pending_reservations'],3)

    def test_unknown_counts_latch_incomplete_and_cannot_be_erased_by_restart(self):
        archive=self.archive(); self.record(archive,complete=False)
        successor=self.archive()
        self.assertEqual(successor.summary()['request_accounting'],'INCOMPLETE')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):
            self.record(successor)

    def test_torn_or_uncommitted_append_preserved_and_refused_without_truncation(self):
        archive=self.archive(); pointer=self.record(archive)
        pack=self.root/pointer['pack']; before=pack.read_bytes()
        with pack.open('ab') as stream: stream.write(b'controlled-torn-frame')
        damaged=pack.read_bytes()
        with self.assertRaisesRegex(ValueError,'RECOVERY'):
            self.archive()
        self.assertEqual(pack.read_bytes(),damaged); self.assertTrue(damaged.startswith(before))

    def test_corrupt_pack_head_or_missing_seal_never_starts_fresh_counters(self):
        for mode in ('pack','head','seal'):
            with self.subTest(mode=mode),TemporaryDirectory() as temp:
                self.root=Path(temp)/'archive'; archive=self.archive()
                with patch.object(self.module(),'MAX_FRAMES',6):
                    pointer=self.record(archive); self.record(archive)
                if mode=='pack':
                    path=self.root/pointer['pack']; raw=path.read_bytes(); path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
                elif mode=='head': (self.root/'head.json').unlink()
                else: next(self.root.glob('*.seal.json')).unlink()
                with self.assertRaises(ValueError): self.archive()

    def test_stale_writer_reloads_head_under_shared_scope_and_reservations_are_bounded(self):
        first=self.archive(); second=self.archive()
        self.record(first); self.record(second)
        self.assertEqual(first.summary()['provider_requests'],2)
        with self.assertRaises(ValueError):
            first.reserve(str(uuid.uuid4()),kind='private',maximum_requests=1,maximum_bytes=10)
        with self.assertRaises(ValueError):
            first.reserve(str(uuid.uuid4()),kind='funding',maximum_requests=166,maximum_bytes=10)

    def test_committed_capture_over_reservation_keeps_pending_and_original_bytes(self):
        archive=self.archive(); token=str(uuid.uuid4())
        archive.reserve(token,kind='funding',maximum_requests=1,maximum_bytes=10)
        with self.assertRaisesRegex(ValueError,'RESERVATION'):
            archive.commit(token,self.files(),requests=1,responses=1,complete=True)
        self.assertEqual(self.archive().summary()['pending_reservations'],1)

    def test_cache_eviction_replays_identically_after_bounded_cache_is_exceeded(self):
        archive=self.archive()
        with patch.object(self.module(),'MAX_CACHE',3):
            for value in (b'z',b'a',b'y',b'b',b'c',b'd'):
                files=self.files(); files['requests/001-response.bin']=value
                self.record(archive,files)
            self.assertEqual(self.archive().summary()['captures'],6)

    def test_pending_or_unknown_network_accounting_is_never_reported_as_zero_complete(self):
        archive=self.archive(); token=str(uuid.uuid4())
        archive.reserve(token,kind='funding',maximum_requests=16,maximum_bytes=1024*1024)
        summary=self.archive().summary()
        self.assertIsNone(summary['provider_requests'])
        self.assertEqual(summary['request_accounting'],'PENDING')
        archive.commit(token,self.files(),requests=1,responses=0,complete=False)
        summary=archive.summary()
        self.assertIsNone(summary['provider_requests'])
        self.assertEqual(summary['completed_capture_requests'],1)
        self.assertEqual(summary['request_accounting'],'INCOMPLETE')

    def test_file_capacity_is_reserved_before_io_and_emergency_has_file_headroom(self):
        module=self.module(); archive=self.archive()
        with patch.object(module,'MAX_FRAMES',6), patch.object(module,'MAX_SEGMENTS',4), \
                patch.object(module,'EMERGENCY_SEGMENTS',1,create=True):
            for _ in range(2):
                token=str(uuid.uuid4())
                archive.reserve(token,kind='market',maximum_requests=1,maximum_bytes=1024*1024,maximum_files=5)
                archive.commit(token,self.files(),requests=1,responses=1,complete=True)
            with self.assertRaisesRegex(ValueError,'FILE_CAPACITY'):
                archive.reserve(str(uuid.uuid4()),kind='market',maximum_requests=1,maximum_bytes=1024*1024,maximum_files=5)
            token=str(uuid.uuid4())
            archive.reserve(token,kind='market',maximum_requests=1,maximum_bytes=1024*1024,maximum_files=5,emergency=True)
            pointer=archive.commit(token,self.files(),requests=1,responses=1,complete=True)
            self.assertEqual(archive.read_capture(pointer),self.files())

    def test_loose_release_requires_verified_archive_and_exact_staging_boundary(self):
        from application.platform.private_files import create_private_directory,write_private_new
        archive=self.archive()
        self.assertTrue(callable(getattr(archive,'release_directory',None)),
            'Loose capture release has no verified-archive boundary')
        staging=self.root.parent/'staging'; create_private_directory(staging)
        folder=staging/str(uuid.uuid4()); create_private_directory(folder)
        for name,raw in self.files().items():
            path=folder/name
            if not path.parent.exists(): create_private_directory(path.parent)
            write_private_new(path,raw)
        pointer=self.record(archive)
        with self.assertRaises(ValueError):
            archive.release_directory(pointer,folder,staging_root=self.root.parent/'other')
        changed=folder/'request.json'; changed.write_bytes(b'changed')
        with self.assertRaises(ValueError): archive.release_directory(pointer,folder,staging_root=staging)
        self.assertTrue((folder/'acquisition.json').exists())  # Validate all before the first deletion.
        changed.write_bytes(self.files()['request.json'])
        archive.release_directory(pointer,folder,staging_root=staging)
        self.assertFalse(folder.exists()); self.assertEqual(archive.read_capture(pointer),self.files())

    def test_directory_archive_and_release_stream_with_bounded_parent_memory(self):
        import os,tracemalloc
        from application.platform.private_files import create_private_directory,write_private_new
        archive=self.archive()
        self.assertTrue(callable(getattr(archive,'commit_directory',None)),
            'Large capture archive still requires all raw pages in the runtime heap')
        staging=self.root.parent/'staging'; create_private_directory(staging)
        folder=staging/str(uuid.uuid4()); create_private_directory(folder)
        raw=os.urandom(4*1024**2)
        for index in range(5):write_private_new(folder/f'{index:03d}-response.bin',raw)
        token=str(uuid.uuid4()); archive.reserve(token,kind='market',maximum_requests=5,
            maximum_bytes=32*1024**2,maximum_files=5)
        tracemalloc.start()
        try:
            pointer=archive.commit_directory(token,folder,requests=5,responses=5,complete=True)
            archive.release_directory(pointer,folder,staging_root=staging)
            peak=tracemalloc.get_traced_memory()[1]
        finally:tracemalloc.stop()
        self.assertLess(peak,30*1024**2)
        self.assertEqual(archive.summary()['provider_requests'],5)
        self.assertFalse(folder.exists())

    def test_fragmented_large_frames_reserve_segments_before_normal_or_emergency_io(self):
        module=self.module(); base=self.root.parent
        for emergency,segments in ((False,3),(True,2)):
            self.root=base/('archive-emergency' if emergency else 'archive-normal'); archive=self.archive()
            with self.subTest(emergency=emergency),patch.object(module,'MAX_PACK_BYTES',1024**2), \
                    patch.object(module,'MAX_RAW',768*1024),patch.object(module,'MAX_SEGMENTS',segments), \
                    patch.object(module,'EMERGENCY_SEGMENTS',1):
                # Three >half-pack incompressible responses need three packs;
                # their aggregate bytes fit two. Both admissions must refuse.
                with self.assertRaisesRegex(ValueError,'FILE_CAPACITY'):
                    archive.reserve(str(uuid.uuid4()),kind='market',maximum_requests=3,
                        maximum_bytes=1600*1024,maximum_files=3,emergency=emergency)

    def test_active_request_upper_budget_seals_without_resetting_global_accounting(self):
        archive=self.archive(); module=self.module()
        with patch.object(module,'MAX_ACTIVE_REQUESTS',3,create=True):
            for _ in range(3):
                token=str(uuid.uuid4())
                archive.reserve(token,kind='market',maximum_requests=2,maximum_bytes=1024*1024)
                archive.commit(token,self.files(),requests=1,responses=1,complete=True)
            summary=self.archive().summary()
            self.assertGreaterEqual(summary['sealed_segments'],2)
            self.assertEqual(summary['provider_requests'],3)
            self.assertEqual(summary['request_budget_upper'],6)
            self.assertEqual(summary['active_request_budget_upper'],2)


if __name__=='__main__': unittest.main()
