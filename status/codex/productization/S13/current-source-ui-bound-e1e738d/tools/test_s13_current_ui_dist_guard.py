from pathlib import Path
import os,tempfile,unittest
import s13_current_ui_bound_qualification_e1e738d as driver

class DistSubjectGuards(unittest.TestCase):
    def methods(self):
        capture=getattr(driver,'capture_dist',None);require=getattr(driver,'require_dist',None)
        self.assertTrue(callable(capture) and callable(require),'Built UI asset subject guards are missing')
        return capture,require

    def fixture(self,root):
        self.assertTrue(root.resolve().is_relative_to(driver.BASE.resolve()))
        (root/'assets').mkdir();(root/'index.html').write_bytes(b'<html>fixture</html>')
        (root/'assets/app.js').write_bytes(b'fixture original;')

    def test_changed_actual_asset_cannot_keep_original_subject(self):
        capture,require=self.methods()
        with tempfile.TemporaryDirectory(prefix='r7-ui-dist-change-',dir=driver.BASE) as temporary:
            root=Path(temporary);self.fixture(root);expected=capture(root)
            (root/'assets/app.js').write_bytes(b'fixture changed;')
            with self.assertRaises(AssertionError):require(root,expected)

    def test_added_or_deleted_actual_asset_cannot_keep_original_subject(self):
        capture,require=self.methods()
        for operation in ('add','delete'):
            with self.subTest(operation=operation),tempfile.TemporaryDirectory(prefix='r7-ui-dist-inventory-',dir=driver.BASE) as temporary:
                root=Path(temporary);self.fixture(root);expected=capture(root)
                if operation=='add':(root/'assets/extra.js').write_bytes(b'fixture extra;')
                else:(root/'assets/app.js').unlink()
                with self.assertRaises((AssertionError,ValueError,OSError)):require(root,expected)

    def test_actual_hardlinked_asset_is_rejected(self):
        capture,_=self.methods()
        with tempfile.TemporaryDirectory(prefix='r7-ui-dist-link-',dir=driver.BASE) as temporary:
            root=Path(temporary);self.fixture(root);os.link(root/'assets/app.js',root/'assets/alias.js')
            with self.assertRaises((ValueError,OSError)):capture(root)

if __name__=='__main__':unittest.main(verbosity=2)
