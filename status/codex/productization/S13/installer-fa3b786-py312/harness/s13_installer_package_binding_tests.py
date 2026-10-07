"""Actual synthetic sealed inventories plus source ordering; no native Linux claim."""
import ast,importlib,json,tempfile,unittest
from pathlib import Path
base=Path(__file__).resolve().parent

class PackageBindingTests(unittest.TestCase):
    def test_old_actual_denial_loop_has_no_before_after_package_binding(self):
        tree=ast.parse((base/'s13_native_installer_denial.py').read_text(encoding='utf-8'))
        loop=next(n for n in tree.body if isinstance(n,ast.For))
        checks=[n for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='verify_distribution']
        self.assertEqual(len(checks),0)
    def test_actual_resealed_replacement_is_rejected_against_original_identity(self):
        module=importlib.import_module('s13_installer_package_binding')
        from application.platform.distribution import seal_distribution,verify_distribution
        with tempfile.TemporaryDirectory(prefix='installer-package-binding-',dir=base) as temporary:
            root=Path(temporary);source=root/'_internal/source';source.mkdir(parents=True)
            (source/'fixture.py').write_bytes(b'FIXTURE=True\n');(root/'R7.exe').write_bytes(b'SYNTHETIC_NATIVE_INVENTORY')
            seal_distribution(root,source_revision='a'*40,entrypoint='R7.exe',dependencies=[dict(name='fixture',version='0')])
            original=verify_distribution(root);module.require_package_identity(root,original)
            (root/'distribution.json').unlink()
            seal_distribution(root,source_revision='b'*40,entrypoint='R7.exe',dependencies=[dict(name='fixture',version='0')])
            self.assertNotEqual(verify_distribution(root),original)
            with self.assertRaises(ValueError):module.require_package_identity(root,original)
    def test_bound_native_loop_checks_before_spawn_after_wait_and_at_completion(self):
        tree=ast.parse((base/'s13_native_installer_denial_v2.py').read_text(encoding='utf-8'))
        loop=next(n for n in tree.body if isinstance(n,ast.For))
        checks=sorted(n.lineno for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='require_package_identity')
        spawn=next(n.lineno for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='spawn_owned')
        wait=next(n.lineno for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='wait')
        self.assertEqual(len(checks),2);self.assertLess(checks[0],spawn);self.assertGreater(checks[1],wait)
        final=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='require_package_identity' and n.lineno>loop.end_lineno]
        self.assertEqual(len(final),1)

if __name__=='__main__':unittest.main()
