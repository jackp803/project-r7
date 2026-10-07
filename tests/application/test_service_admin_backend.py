"""Controlled OS metadata/manager seams; not actual Ubuntu administration."""
import importlib,io,os,stat,unittest
from types import SimpleNamespace
from unittest.mock import patch

class ServiceAdminBackendTests(unittest.TestCase):
    def setUp(self):self.module=importlib.import_module('application.platform.service_admin_files')
    def bare(self):return self.module.LinuxServiceBackend.__new__(self.module.LinuxServiceBackend)
    def test_source_or_unsupported_platform_is_refused_before_any_filesystem_open(self):
        with patch.object(self.module,'_native_ubuntu',side_effect=ValueError('Native required')),patch('os.open') as opened,self.assertRaises(ValueError):
            self.module.LinuxServiceBackend()
        opened.assert_not_called()
    def test_native_operator_requires_exact_root_user_and_group_before_filesystem(self):
        for uid,gid in ((1000,1000),(0,1000)):
            with self.subTest(uid=uid,gid=gid),patch.object(self.module,'_native_ubuntu'), \
                    patch('os.geteuid',return_value=uid,create=True),patch('os.getegid',return_value=gid,create=True), \
                    patch('os.open') as opened,self.assertRaises(ValueError):self.module.LinuxServiceBackend()
            opened.assert_not_called()
    def test_only_fixed_targets_and_exact_operation_audit_names_are_allowed(self):
        for target in self.module.FILES:self.assertEqual(str(self.module._allowed(target)),target)
        self.module._allowed('/var/lib/r7-service-admin/uninstalled-'+'a'*64+'.json')
        for path in ('/tmp/foreign','/etc/systemd/system/other.service','/var/lib/r7-service-admin/../data',
                     '/var/lib/r7-service-admin/uninstalled-arbitrary.json'):
            with self.subTest(path=path),self.assertRaises(ValueError):self.module._allowed(path)
    def test_controlled_link_wrong_owner_group_or_writable_metadata_is_rejected(self):
        self.module._protected(SimpleNamespace(st_uid=0,st_gid=0,st_mode=stat.S_IFDIR|0o755),directory=True)
        for uid,gid,mode in ((1000,0,stat.S_IFDIR|0o755),(0,1000,stat.S_IFDIR|0o755),
                             (0,0,stat.S_IFDIR|0o775),(0,0,stat.S_IFLNK|0o777),(0,0,stat.S_IFIFO|0o600)):
            with self.subTest(uid=uid,gid=gid,mode=mode),self.assertRaises(ValueError):
                self.module._protected(SimpleNamespace(st_uid=uid,st_gid=gid,st_mode=mode),directory=True)
    def test_manager_uses_fixed_direct_show_argv_and_requires_all_unique_properties(self):
        backend=self.bare();text='\n'.join(name+'=' for name in self.module.PROPERTIES)+'\n'
        with patch.object(backend,'_manager_command',return_value=text) as command:
            self.assertEqual(set(backend.manager_state('r7-control.service')),set(self.module.PROPERTIES))
        command.assert_called_once_with(['/usr/bin/systemctl','show','r7-control.service','--all','--no-pager',
            '--property='+','.join(self.module.PROPERTIES)])
        for invalid in ('LoadState=not-found\n',text+'Job=0\n',text+'Foreign=value\n'):
            with self.subTest(case=len(invalid)),patch.object(backend,'_manager_command',return_value=invalid),self.assertRaises(ValueError):
                backend.manager_state('r7-control.service')
    def test_manager_reload_only_uses_fixed_reload_argv(self):
        backend=self.bare()
        with patch.object(backend,'_manager_command',return_value='') as command:self.assertTrue(backend.reload())
        command.assert_called_once_with(['/usr/bin/systemctl','daemon-reload'])
    def test_arbitrary_failed_manager_exit_cannot_be_interpreted_as_inactive(self):
        owned=SimpleNamespace(wait=lambda:3,termination_report=SimpleNamespace(reaped=True,reason='COMPLETED'),
            process=SimpleNamespace(stdout=io.BytesIO(b'LoadState=not-found\n')))
        with patch.object(self.module,'spawn_owned',return_value=owned),self.assertRaises(ValueError):
            self.bare()._manager_command(['/usr/bin/systemctl','show','r7-control.service'])
        self.assertTrue(owned.process.stdout.closed)
    def test_failed_cleanup_and_timeout_return_before_reading_stdout(self):
        for reaped,reason in ((False,'CLEANUP_FAILED'),(True,'TIMEOUT')):
            stream=SimpleNamespace(read=lambda *args:(_ for _ in ()).throw(AssertionError('Unreaped/timed-out pipe must not be read')),close=lambda:None)
            owned=SimpleNamespace(wait=lambda:124,termination_report=SimpleNamespace(reaped=reaped,reason=reason),process=SimpleNamespace(stdout=stream))
            with self.subTest(reaped=reaped,reason=reason),patch.object(self.module,'spawn_owned',return_value=owned),self.assertRaises(ValueError):
                self.bare()._manager_command(['/usr/bin/systemctl','daemon-reload'])

    def test_missing_receipt_parent_has_actionable_creation_only_prerequisite(self):
        def pin(backend,path):
            if str(path)==self.module.PARENTS[2]:raise FileNotFoundError('Controlled missing admin directory')
        with patch.object(self.module,'_native_ubuntu'),patch('os.geteuid',return_value=0,create=True), \
                patch('os.getegid',return_value=0,create=True),patch.object(self.module.LinuxServiceBackend,'_pin',pin), \
                self.assertRaises(self.module.ServiceAdminPrerequisiteError) as error:self.module.LinuxServiceBackend()
        self.assertEqual(error.exception.required_directory,self.module.PARENTS[2])

    def test_hardlinked_owned_metadata_is_rejected_before_reading_bytes(self):
        with self.assertRaises(ValueError):self.module._protected(SimpleNamespace(st_uid=0,st_gid=0,st_mode=stat.S_IFREG|0o600,st_nlink=2),directory=False)

    def test_rename_adapter_uses_exact_fd_relative_noreplace_without_fallback(self):
        from unittest.mock import Mock
        rename=Mock(return_value=0);library=SimpleNamespace(renameat2=rename)
        with patch.object(self.module.ctypes,'CDLL',return_value=library):self.module._rename_noreplace(11,'r7-control.service',12,'item')
        rename.assert_called_once_with(11,b'r7-control.service',12,b'item',1)
        for library in (SimpleNamespace(),SimpleNamespace(renameat2=Mock(return_value=-1))):
            with self.subTest(supported=hasattr(library,'renameat2')),patch.object(self.module.ctypes,'CDLL',return_value=library), \
                    patch.object(self.module.ctypes,'get_errno',return_value=17),self.assertRaises((OSError,ValueError)):
                self.module._rename_noreplace(11,'r7-control.service',12,'item')

    def test_link_added_between_name_inspection_and_open_is_rejected_before_read(self):
        before=SimpleNamespace(st_uid=0,st_gid=0,st_mode=stat.S_IFREG|0o644,st_nlink=1,st_dev=1,st_ino=2,st_size=4,st_mtime_ns=5)
        opened=SimpleNamespace(**dict(vars(before),st_nlink=2))
        with patch('os.stat',return_value=before),patch('os.open',return_value=71),patch('os.fstat',return_value=opened), \
                patch('os.O_NOFOLLOW',0x20000,create=True),patch('os.O_NONBLOCK',0x800,create=True), \
                patch('os.read') as read,patch('os.close') as close,self.assertRaises(ValueError):
            self.bare()._snapshot_leaf(70,'r7-control.service',False)
        read.assert_not_called();close.assert_called_once_with(71)

if __name__=='__main__':unittest.main()
