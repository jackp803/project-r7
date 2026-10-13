"""Qualification binds the actual local execution toolchain before execution."""
import importlib.util
import unittest


class PaperToolchainTests(unittest.TestCase):
    def module(self):
        from pathlib import Path
        path=Path(__file__).resolve().parents[2]/'tools/paper_toolchain.py'
        self.assertTrue(path.is_file(),'Actual interpreter/browser execution identities must be frozen')
        spec=importlib.util.spec_from_file_location('paper_toolchain_under_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_actual_installed_tools_are_measured_without_user_paths_or_network(self):
        from pathlib import Path
        m=self.module();observed=m.measure(Path(__file__).resolve().parents[2])
        self.assertEqual(set(observed),{'python','node','browser','playwright'})
        for identity in observed.values():
            self.assertTrue(identity['version']);self.assertRegex(identity['hash'],r'^sha256:[0-9a-f]{64}$')
            self.assertEqual(identity['scope'],'LOCAL_EXECUTION_TOOL_ONLY')
        self.assertNotIn('C:\\Users',str(observed))

    def test_changed_tool_identity_is_denied_before_any_qualification_execution(self):
        from pathlib import Path
        m=self.module();actual=m.measure(Path(__file__).resolve().parents[2])
        m.require_same(actual,actual)
        changed={**actual,'browser':{**actual['browser'],'hash':'sha256:'+'0'*64}}
        with self.assertRaises(ValueError):m.require_same(changed,actual)


if __name__=='__main__':unittest.main()
