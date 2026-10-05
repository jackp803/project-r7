"""Exercise only pure asset inventory guards, no browser/product launch."""
import ast, hashlib, os, stat, subprocess
from pathlib import Path
import tempfile, unittest
project=Path(__file__).resolve().parent.parent
source=project/'artifacts/s13_serial_browser_qualify.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
scope={'Path':Path,'hashlib':hashlib,'stat':stat}
functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ('build_inventory','require_build')]
assert len(functions)==2
exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),scope)

class BuildIdentityRegression(unittest.TestCase):
    def setUp(self):
        self.owner=tempfile.TemporaryDirectory(prefix='browser-build-guard-',dir=project/'artifacts')
        self.addCleanup(self.owner.cleanup)
        self.root=Path(self.owner.name)
        (self.root/'index.html').write_text('<script src="assets/app.js"></script>',encoding='utf-8')
        (self.root/'assets').mkdir()
        (self.root/'assets/app.js').write_bytes(b'original-build')
        self.expected=scope['build_inventory'](self.root)
    def test_exact_inventory_accepted(self):
        scope['require_build'](self.root,self.expected)
    def test_same_name_same_length_replacement_denied(self):
        (self.root/'assets/app.js').write_bytes(b'replaced-build')
        with self.assertRaisesRegex(ValueError,'BROWSER_BUILD_CHANGED'):
            scope['require_build'](self.root,self.expected)
    def test_missing_asset_denied(self):
        (self.root/'assets/app.js').unlink()
        with self.assertRaisesRegex(ValueError,'BROWSER_BUILD_CHANGED'):
            scope['require_build'](self.root,self.expected)
    def test_added_ignored_asset_denied(self):
        (self.root/'assets/extra.js').write_bytes(b'additional')
        with self.assertRaisesRegex(ValueError,'BROWSER_BUILD_CHANGED'):
            scope['require_build'](self.root,self.expected)
    def test_actual_root_junction_denied_before_traversal(self):
        self.assertEqual(os.name,'nt','This actual root-junction regression requires the approved native Windows host')
        target=self.root/'target'
        target.mkdir()
        (target/'index.html').write_bytes(b'valid-linked-build')
        alias=self.root/'alias'
        made=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(alias),str(target)],capture_output=True,check=False)
        self.assertEqual(made.returncode,0)
        self.assertTrue(alias.lstat().st_file_attributes & 0x400)
        with self.assertRaisesRegex(ValueError,'LINKED_BROWSER_BUILD_FORBIDDEN'):
            scope['build_inventory'](alias)
        self.assertEqual((target/'index.html').read_bytes(),b'valid-linked-build')

if __name__=='__main__':unittest.main(verbosity=2)
