"""Actual retained wrapper bytes and distribution sealing, not a Linux build."""
import importlib,os,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

class ServiceAdminPackagingTests(unittest.TestCase):
    def setUp(self):
        self.builder=importlib.import_module('tools.build_product')
        project=Path(__file__).resolve().parents[4]
        self.temp=TemporaryDirectory(prefix='service-package-',dir=project/'artifacts');self.addCleanup(self.temp.cleanup)
        self.package=Path(self.temp.name)/'native package 中文';self.package.mkdir()
    def test_linux_package_retains_exact_wrappers_and_complete_operator_guide(self):
        self.builder._retain_service_assets(self.package,'linux')
        documents={'NATIVE_UBUNTU_SERVICE_ADMIN.md','NATIVE_UBUNTU_SERVICE_PLAN.md','SSH_CONTROL_ACCESS.md'}
        self.assertEqual({p.name for p in self.package.iterdir()},{'install-service.sh','uninstall-service.sh'}|documents)
        for name in ('install-service.sh','uninstall-service.sh'):
            self.assertEqual((self.package/name).read_bytes(),(self.builder.ROOT/'packaging/linux'/name).read_bytes())
        for name in documents:
            self.assertEqual((self.package/name).read_bytes(),(self.builder.ROOT/'docs/product'/name).read_bytes())
    def test_windows_does_not_emit_ubuntu_administration_scripts(self):
        self.builder._retain_service_assets(self.package,'windows')
        self.assertEqual(list(self.package.iterdir()),[])
    def test_existing_dangling_asset_link_is_refused_without_creating_external_target(self):
        outside=Path(self.temp.name)/'external-owned-sentinel.sh'
        destination=self.package/'install-service.sh'
        if os.name!='nt':
            os.symlink(outside,destination)
            with self.assertRaises((OSError,ValueError)):self.builder._retain_service_assets(self.package,'linux')
            self.assertFalse(outside.exists());self.assertTrue(destination.is_symlink())
            return
        # Windows host lacks symlink privilege (actual WinError1314 retained).
        # Model an existing dangling directory entry at the exclusive-open seam;
        # the old copyfile path performs a real external fixture write.
        real_open=os.open;real_copy=self.builder.shutil.copyfile;attempts=[]
        def exclusive(name,flags,*args,**kwargs):
            if Path(name)==destination:
                attempts.append(flags);self.assertTrue(flags&os.O_EXCL)
                raise FileExistsError('Controlled dangling directory entry')
            return real_open(name,flags,*args,**kwargs)
        def following(source,target):
            return real_copy(source,outside if Path(target)==destination else target)
        with patch.object(os,'open',side_effect=exclusive),patch.object(self.builder.shutil,'copyfile',side_effect=following), \
                self.assertRaises((OSError,ValueError)):self.builder._retain_service_assets(self.package,'linux')
        self.assertFalse(outside.exists());self.assertEqual(len(attempts),1)
    def test_changed_retained_wrapper_invalidates_actual_distribution_provenance(self):
        self.builder._retain_service_assets(self.package,'linux')
        source=self.package/'_internal/source';source.mkdir(parents=True);(source/'fixture.py').write_bytes(b'FIXTURE=True\n')
        (self.package/'R7.exe').write_bytes(b'SYNTHETIC_NATIVE_INVENTORY')
        module=importlib.import_module('application.platform.distribution')
        module.seal_distribution(self.package,source_revision='a'*40,entrypoint='R7.exe',dependencies=[dict(name='fixture',version='0')])
        module.verify_distribution(self.package)
        wrapper=self.package/'install-service.sh';wrapper.write_bytes(wrapper.read_bytes()+b'# changed\n')
        with self.assertRaises(ValueError):module.verify_distribution(self.package)
