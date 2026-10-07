"""Actual Windows junction / POSIX link denial before public UI mounting."""
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from application.control_api.assets import validate_control_center_assets

class ControlAssetLinkTests(unittest.TestCase):
    def setUp(self):
        artifacts=Path(__file__).resolve().parents[4]/'artifacts'
        self.owner=TemporaryDirectory(prefix='control-asset-links-',dir=artifacts)
        self.root=Path(self.owner.name)
        self.assertTrue(self.root.resolve().is_relative_to(artifacts.resolve()))
        self.addCleanup(self.owner.cleanup)
        self.assets=self.root/'ui';(self.assets/'assets').mkdir(parents=True)
        (self.assets/'index.html').write_bytes(b'<html>owned-fixture-only</html>')
        (self.assets/'assets/app.js').write_bytes(b'owned-fixture-only')
    def link(self,alias,target):
        self.assertTrue(alias.absolute().is_relative_to(self.root))
        self.assertTrue(target.resolve().is_relative_to(self.root.resolve()))
        if os.name=='nt':
            result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(target)],capture_output=True,check=False)
            self.assertEqual(result.returncode,0)
            self.assertTrue(alias.lstat().st_file_attributes & 0x400)
        else:
            alias.symlink_to(target,target_is_directory=True)
    def test_actual_build_root_link_denied_before_any_public_mount(self):
        alias=self.root/'linked-ui';self.link(alias,self.assets)
        with self.assertRaises(ValueError):validate_control_center_assets(alias)
        self.assertEqual((self.assets/'index.html').read_bytes(),b'<html>owned-fixture-only</html>')
    def test_actual_nested_asset_directory_link_denied(self):
        target=self.root/'nested-fixture';target.mkdir();(target/'fixture.js').write_bytes(b'isolated-fixture-only')
        self.link(self.assets/'assets/linked',target)
        with self.assertRaises(ValueError):validate_control_center_assets(self.assets)
        self.assertEqual((target/'fixture.js').read_bytes(),b'isolated-fixture-only')
    def test_regular_build_root_and_assets_are_accepted(self):
        self.assertEqual(validate_control_center_assets(self.assets),self.assets)

if __name__=='__main__':unittest.main()
