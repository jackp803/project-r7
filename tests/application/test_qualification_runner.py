import tempfile
import unittest
from pathlib import Path

from tests.application.test_platform import require


class QualificationRunnerTests(unittest.TestCase):
    def test_inventory_includes_registry_and_new_application_tests(self):
        module = require(self, "application.qualification")
        root = Path(__file__).resolve().parents[2]
        inventory = module.discover_suites(root)
        self.assertIn("registry", {suite.name for suite in inventory})
        self.assertIn("application", {suite.name for suite in inventory})
        self.assertEqual(sorted(root.glob("tests/**/test_*.py")),
                         sorted(path for suite in inventory for path in suite.test_files))

    def test_runner_fails_on_missing_requested_suite_and_empty_inventory(self):
        module = require(self, "application.qualification")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(module.QualificationError):
                module.discover_suites(root)
        root = Path(__file__).resolve().parents[2]
        with self.assertRaises(module.QualificationError):
            module.select_suites(module.discover_suites(root), ["nonexistent"])

    def test_summary_requires_nonzero_tests_and_rejects_skips_expected_failures(self):
        module = require(self, "application.qualification")
        for text in ("Ran 0 tests in 0.0s\n\nOK", "Ran 2 tests in 0.1s\n\nOK (skipped=1)",
                     "Ran 2 tests in 0.1s\n\nOK (expected failures=1)",
                     "Ran 2 tests in 0.1s\n\nFAILED (failures=1)", "no summary"):
            with self.subTest(text=text):
                self.assertFalse(module.parse_result(text, returncode=0).passed)
        result = module.parse_result("Ran 3 tests in 0.1s\n\nOK\n", returncode=0)
        self.assertTrue(result.passed)
        self.assertEqual(3, result.tests_run)

    def test_summary_counts_each_failure_class_separately(self):
        module = require(self, "application.qualification")
        result = module.parse_result("Ran 9 tests in 0.1s\n\nFAILED (failures=1, errors=2, skipped=3)\n", returncode=1)
        self.assertEqual((1, 2, 3, 3), (result.failures, result.errors, result.skipped, result.tests_passed))

    def test_runner_cannot_overwrite_source_tree_with_evidence(self):
        module = require(self, "application.qualification")
        root = Path(__file__).resolve().parents[2]
        with self.assertRaises(module.QualificationError):
            module.validate_output_root(root, root / "src" / "logs")

    def test_traceback_redaction_includes_repr_escaped_windows_paths(self):
        module = require(self, "application.qualification")
        root = Path(__file__).resolve().parents[2]
        text = str(root) + "\n" + repr(str(Path.home() / "private.sqlite3"))
        redacted = module._sanitize(text, root)
        self.assertNotIn(str(root), redacted)
        self.assertNotIn(str(Path.home()).replace("\\", "\\\\"), redacted)
