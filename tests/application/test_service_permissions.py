"""Linux permission-fact unit probes on Windows, not native service acceptance."""
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from application.platform import service_guard

def info(mode,uid=0,gid=1001,kind=stat.S_IFREG):
    return SimpleNamespace(st_mode=kind|mode,st_uid=uid,st_gid=gid)

def fake_path(leaf,parents):
    path=Mock();path.lstat.return_value=leaf
    path.parents=[]
    for value in parents:
        parent=Mock();parent.lstat.return_value=value;path.parents.append(parent)
    return path

class ServicePermissionTests(unittest.TestCase):
    def config(self,mode,gid=1001,parent=None):
        return fake_path(info(mode,gid=gid),[parent or info(0o750,kind=stat.S_IFDIR),info(0o755,gid=0,kind=stat.S_IFDIR)])
    def test_protected_group_readable_config_has_actual_service_access(self):
        with patch.object(service_guard,'_local_path'):
            service_guard._protected_config(self.config(0o640),1001)
    def test_root_only_config_is_refused_even_if_installer_can_read_it(self):
        with patch.object(service_guard,'_local_path'),self.assertRaises(ValueError):
            service_guard._protected_config(self.config(0o600),1001)
    def test_nontraversable_config_parent_is_refused_before_a_plan_claim(self):
        with patch.object(service_guard,'_local_path'),self.assertRaises(ValueError):
            service_guard._protected_config(self.config(0o640,parent=info(0o700,kind=stat.S_IFDIR)),1001)
    def test_wrong_group_world_readable_or_writable_config_is_refused(self):
        for mode,gid in ((0o640,1002),(0o644,1001),(0o660,1001)):
            with self.subTest(mode=mode,gid=gid),patch.object(service_guard,'_local_path'),self.assertRaises(ValueError):
                service_guard._protected_config(self.config(mode,gid),1001)
    def test_private_data_is_owned_by_exact_user_and_group(self):
        root=fake_path(info(0o700,uid=1001,kind=stat.S_IFDIR),[info(0o755,gid=0,kind=stat.S_IFDIR)])
        with patch.object(service_guard,'_local_path'):
            service_guard._private_service_root(root,1001,1001)
    def test_nontraversable_private_data_parent_is_refused(self):
        root=fake_path(info(0o700,uid=1001,kind=stat.S_IFDIR),[info(0o700,gid=0,kind=stat.S_IFDIR)])
        with patch.object(service_guard,'_local_path'),self.assertRaises(ValueError):
            service_guard._private_service_root(root,1001,1001)
    def test_service_owned_roots_without_owner_write_or_traversal_are_refused(self):
        for mode in (0o500,0o400,0o600):
            root=fake_path(info(mode,uid=1001,kind=stat.S_IFDIR),[info(0o755,gid=0,kind=stat.S_IFDIR)])
            with self.subTest(mode=mode),patch.object(service_guard,'_local_path'),self.assertRaises(ValueError):
                service_guard._private_service_root(root,1001,1001)

if __name__=='__main__':unittest.main()
