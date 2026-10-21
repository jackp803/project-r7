"""Actual supported private backups; avoid redundant whole archive decoding."""
import unittest
from unittest.mock import patch
import uuid
import time

from application.paper import capture_archive
from application.platform import product_backup
from tests.application import test_public_acquisition_backup as fixture


class PublicArchiveBackupBudgetTests(unittest.TestCase):
    def setUp(self):
        helper=fixture.PublicAcquisitionBackupTests();helper.setUp();self.addCleanup(helper.doCleanups)
        self.config,self.base=helper.config,helper.base
        self.archive=capture_archive.PublicCaptureArchive(self.config.local_data_root/capture_archive.ROOT)
        token=str(uuid.uuid4());self.archive.reserve(token,kind='funding',maximum_requests=16,maximum_bytes=1024*1024)
        self.archive.commit(token,{'request.json':b'PUBLIC_CONTROLLED_STORAGE_ONLY'},requests=1,responses=1,complete=True)

    def test_each_backup_verify_and_restore_operation_verifies_full_archive_once(self):
        original=capture_archive.PublicCaptureArchive;calls=[]
        def verify(*args,**kwargs):
            calls.append(str(args[0]));return original(*args,**kwargs)
        with patch.object(capture_archive,'PublicCaptureArchive',side_effect=verify):
            product_backup.create_product_backup(self.config,self.base/'bounded-private-backup')
            self.assertEqual(len(calls),1,'A 30day archive cannot be decoded three times inside one bounded backup')
            product_backup.verify_product_backup(self.config,self.base/'bounded-private-backup')
            self.assertEqual(len(calls),2,'A separate verification must not inherit an old in-memory proof')
            product_backup.restore_product_backup(self.config,self.base/'bounded-private-backup',self.base/'bounded-private-restored')
            self.assertEqual(len(calls),3,'Restore must perform its own full verification, once')

    def test_changed_archive_bytes_between_copy_and_recheck_are_not_a_cached_pass(self):
        original=product_backup._copy_file;changed=[False]
        pack=self.archive.root/'000001.pack'
        def copy(source,target,row,end):
            original(source,target,row,end)
            if not changed[0] and row['relative_path'].endswith('.pack'):
                raw=pack.read_bytes();pack.write_bytes(raw[:-1]+bytes([raw[-1]^1]));changed[0]=True
        with patch.object(product_backup,'_copy_file',side_effect=copy),self.assertRaises(product_backup.ProductBackupError):
            product_backup.create_product_backup(self.config,self.base/'changed-source-backup')
        self.assertTrue(changed[0])

    def test_backup_refuses_boolean_commit_pointer_despite_coherent_frame_hashes(self):
        from tests.application.test_public_capture_archive import append_boolean_offset_commit
        append_boolean_offset_commit(self.archive)
        with self.assertRaisesRegex(product_backup.ProductBackupError,'PUBLIC_ARCHIVE_INVALID'):
            product_backup.create_product_backup(self.config,self.base/'invalid-index-backup')

    def test_final_inventory_rows_cannot_rebind_cached_semantic_proof_to_changed_bytes(self):
        proof=set();end=time.monotonic()+30
        arguments=dict(databases=('canonical.sqlite3',),_archive_verifications=proof)
        product_backup._data_inventory(self.config.local_data_root,end,**arguments)
        original=product_backup._file_facts;pack=self.archive.root/'000001.pack';calls=[0]
        def facts(path,deadline):
            if path==pack:
                calls[0]+=1
                if calls[0]==2:
                    raw=pack.read_bytes();pack.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
            return original(path,deadline)
        with patch.object(product_backup,'_file_facts',side_effect=facts),self.assertRaises(product_backup.ProductBackupError):
            product_backup._data_inventory(self.config.local_data_root,end,**arguments)
