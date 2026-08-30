from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path


_TARGETS = (
    Path("src/execution/protection_trigger.py"),
    Path("src/execution/external_close_evidence.py"),
    Path("src/execution/protection_registry_evidence.py"),
)


class CanonicalPositionImportIdentityTests(unittest.TestCase):
    def test_e4_targets_do_not_import_src_position_namespace(self):
        for path in _TARGETS:
            with self.subTest(path=str(path)):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                imported_modules: list[str] = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module is not None:
                        imported_modules.append(node.module)
                    elif isinstance(node, ast.Import):
                        imported_modules.extend(alias.name for alias in node.names)
                self.assertFalse(
                    any(name == "src.position" or name.startswith("src.position.") for name in imported_modules),
                    f"{path} must not import duplicate src.position namespace",
                )

    def test_fp03_imports_are_exact_canonical_position_objects(self):
        e4 = importlib.import_module("execution.protection_trigger")
        canonical = importlib.import_module("position.protection_trigger_validity")
        self.assertIs(
            e4.ProtectionTriggerValidityError,
            canonical.ProtectionTriggerValidityError,
        )
        self.assertIs(
            e4.validate_protection_trigger_validity_evidence,
            canonical.validate_protection_trigger_validity_evidence,
        )
        self.assertIs(
            e4.protection_trigger_validity_evidence_is_current,
            canonical.protection_trigger_validity_evidence_is_current,
        )

    def test_fp04_fp10_imports_are_exact_canonical_position_objects(self):
        e4 = importlib.import_module("execution.external_close_evidence")
        canonical_policy = importlib.import_module("position.external_close_policy")
        canonical_reinterpretation = importlib.import_module("position.external_close_reinterpretation")
        canonical_binding = importlib.import_module("position.lifecycle_execution_binding")
        canonical_projection = importlib.import_module("position.lifecycle_projection")

        self.assertIs(
            e4.validate_external_provider_ownership_evidence,
            canonical_policy.validate_external_provider_ownership_evidence,
        )
        self.assertIs(
            e4.validate_external_manual_close_convergence_evidence,
            canonical_policy.validate_external_manual_close_convergence_evidence,
        )
        self.assertIs(
            e4.ExternalCloseReinterpretationError,
            canonical_reinterpretation.ExternalCloseReinterpretationError,
        )
        self.assertIs(
            e4.validate_position_lifecycle_execution_evidence_binding,
            canonical_binding.validate_position_lifecycle_execution_evidence_binding,
        )
        self.assertIs(
            e4.validate_position_lifecycle_projection,
            canonical_projection.validate_position_lifecycle_projection,
        )

    def test_fp11_imports_are_exact_canonical_position_objects(self):
        e4 = importlib.import_module("execution.protection_registry_evidence")
        canonical_policy = importlib.import_module("position.external_close_policy")
        canonical_reinterpretation = importlib.import_module("position.external_close_reinterpretation")

        self.assertIs(
            e4.validate_external_provider_ownership_evidence,
            canonical_policy.validate_external_provider_ownership_evidence,
        )
        self.assertIs(
            e4.ExternalCloseReinterpretationError,
            canonical_reinterpretation.ExternalCloseReinterpretationError,
        )

    def test_fp11_wrong_input_type_remains_fail_closed(self):
        e4 = importlib.import_module("execution.protection_registry_evidence")
        with self.assertRaises(e4.ProtectionRegistryEvidenceError) as caught:
            e4.build_protection_registry_multiplicity_evidence(object())
        self.assertEqual("INPUT_TYPE_INVALID", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
