"""Actual owner-private creation/copy/read beyond Windows directory/file limits."""
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic
import unittest

from application.cloud.safe_files import read_bounded
from application.platform.private_files import create_private_directory, require_private, write_private_new
from application.platform.product_backup import _copy_file, _file_facts, _walk, ProductBackupError
from application.platform.supervision import SupervisionError


def fixture_path(path):
    return Path('\\\\?\\'+str(path)) if os.name=='nt' else path


class PrivateLongPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory(prefix='R7 private path 中文 ')
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).absolute()
        def cleanup():
            if self.root!=Path(self.temporary.name).absolute():
                raise AssertionError('Fresh private fixture cleanup containment failed')
            # Exactly the newly allocated named fixture; no other tree is touched.
            shutil.rmtree(fixture_path(self.root))
        self.addCleanup(cleanup)
        self.parent=self.root/'scoped-fixture'
        index=0
        while len(str(self.parent))<=280:
            self.parent=self.parent/(f'segment-{index}-'+('x'*70));index+=1
        fixture_path(self.parent).mkdir(parents=True)

    def private_directory(self,name):
        path=self.parent/name
        self.assertGreater(len(str(path)),260)
        create_private_directory(path)
        require_private(path,directory=True)
        return path

    def test_actual_long_private_directory_and_file_preserve_owner_acl_and_no_replace(self):
        directory=self.private_directory('中文 owner private')
        target=directory/'fixture.json';raw=b'{"synthetic":"PRIVATE_OWNER_BYTES"}'
        write_private_new(target,raw)
        require_private(target)
        self.assertEqual(read_bounded(directory,target.name,1024),raw)
        with self.assertRaises(FileExistsError):write_private_new(target,b'CHANGED')
        self.assertEqual(read_bounded(directory,target.name,1024),raw)
        alias=directory/'hardlink.json';os.link(fixture_path(target),fixture_path(alias))
        with self.assertRaises(ValueError):require_private(target)

    def test_actual_private_backup_copy_pins_long_source_and_preserves_single_link_boundary(self):
        source_root=self.private_directory('private source')
        target_root=self.private_directory('private target')
        source=source_root/'fixture.json';target=target_root/'fixture.json'
        raw=b'{"synthetic":"LONG_PRIVATE_BACKUP"}';write_private_new(source,raw)
        end=monotonic()+30;row=_file_facts(source,end)
        _copy_file(source,target,row,end)
        require_private(target)
        self.assertEqual(read_bounded(target_root,target.name,1024),raw)
        self.assertEqual(_file_facts(target,end),row)
        alias=source_root/'hardlink.json';os.link(fixture_path(source),fixture_path(alias))
        denied=target_root/'denied.json'
        with self.assertRaises(ProductBackupError):_copy_file(source,denied,row,end)
        self.assertEqual(read_bounded(target_root,denied.name,1024),b'')

    def test_actual_long_reparse_parent_is_rejected_before_private_write_or_backup_read(self):
        outside=self.root/'outside fixture';create_private_directory(outside)
        marker=outside/'marker.json';raw=b'{"synthetic":"KEEP_OUTSIDE_BYTES"}';write_private_new(marker,raw)
        alias=self.parent/'redirect'
        if os.name=='nt':
            subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(fixture_path(alias)),str(outside)],
                check=True,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=10)
        else:alias.symlink_to(outside,target_is_directory=True)
        with self.assertRaises((SupervisionError,ValueError)):
            write_private_new(alias/'forbidden.json',b'FORBIDDEN')
        self.assertFalse((outside/'forbidden.json').exists())
        with self.assertRaises((SupervisionError,ValueError)):
            _file_facts(alias/marker.name,monotonic()+30)
        self.assertEqual(read_bounded(outside,marker.name,1024),raw)

    def test_real_private_inventory_keeps_logical_names_at_actual_long_roots(self):
        root=self.private_directory('private inventory')
        records=root/'records';create_private_directory(records)
        target=records/'fixture.json';raw=b'{"synthetic":"REAL_LONG_INVENTORY"}';write_private_new(target,raw)
        paths,excluded=_walk(root,monotonic()+30,exclusions=False)
        self.assertEqual(set(paths),{'records/fixture.json'})
        self.assertEqual(excluded,[])
        self.assertEqual(paths['records/fixture.json'],target)
        self.assertEqual(_file_facts(paths['records/fixture.json'],monotonic()+30)['bytes'],len(raw))

    def test_actual_complete_product_backup_and_verification_at_long_destination(self):
        from tests.application.test_product_data_backup import ProductDataBackupTests
        from application.platform.product_backup import create_product_backup,verify_product_backup
        helper=ProductDataBackupTests()
        self.addCleanup(lambda:self.assertTrue(helper.doCleanups(),'Actual backup source fixture cleanup failed'))
        helper.setUp()
        destination=self.parent/'complete-private-backup'
        created=create_product_backup(helper.config,destination)
        self.assertEqual(created['status'],'PRODUCT_DATA_BACKUP_VERIFIED')
        verified=verify_product_backup(helper.config,destination)
        self.assertEqual(verified['coverage'],'COMPLETE_SUPPORTED_LOCAL_PROFILE')
        self.assertEqual(created['backup_id'],verified['backup_id'])

    def test_actual_database_backup_and_verification_at_long_destination(self):
        from tests.application.test_product_data_backup import ProductDataBackupTests
        from application.platform.backup import create_database_backup,verify_database_backup
        helper=ProductDataBackupTests()
        self.addCleanup(lambda:self.assertTrue(helper.doCleanups(),'Actual backup source fixture cleanup failed'))
        helper.setUp()
        destination=self.parent/'complete-private-databases'
        created=create_database_backup(helper.config,destination)
        verified=verify_database_backup(helper.config,destination)
        self.assertEqual(created['status'],'DATABASE_BACKUP_VERIFIED')
        self.assertEqual(created,verified)


if __name__=='__main__':unittest.main(verbosity=2)
