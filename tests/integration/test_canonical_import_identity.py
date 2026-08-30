from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path

import position
from position.protection_registry_policy import (
    CurrentProtectionRegistryAuthority,
    ProtectionRegistryPolicyError,
    interpret_protection_registry_evidence,
)

import tests.position.test_protection_registry_policy as fp11_policy_fixture_module
import tests.storage.test_protection_registry_currentness as fp11_storage_fixture_module


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"


class CanonicalImportIdentityTests(unittest.TestCase):
    """E7 regression definitions for one-source-module/one-class identity.

    These tests are credential-free and perform no provider/network/order/runtime
    activity. They intentionally keep the existing exact-type validation strict.
    """

    @staticmethod
    def _forbidden_src_position_imports(root: Path) -> list[str]:
        offenders: list[str] = []
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == "src.position" or module.startswith("src.position."):
                        offenders.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}:{module}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "src.position" or alias.name.startswith("src.position."):
                            offenders.append(
                                f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}:{alias.name}"
                            )
        return offenders

    def test_canonical_position_package_has_one_public_authority_class_identity(self):
        policy = importlib.import_module("position.protection_registry_policy")
        self.assertIs(
            position.CurrentProtectionRegistryAuthority,
            policy.CurrentProtectionRegistryAuthority,
        )
        self.assertIs(CurrentProtectionRegistryAuthority, policy.CurrentProtectionRegistryAuthority)
        self.assertEqual("position.protection_registry_policy", CurrentProtectionRegistryAuthority.__module__)

    def test_production_source_never_imports_src_position_namespace(self):
        self.assertEqual([], self._forbidden_src_position_imports(SOURCE_ROOT))

    def test_importing_cross_module_consumers_does_not_create_src_position_tree(self):
        importlib.import_module("execution.protection_trigger")
        importlib.import_module("execution.external_close_evidence")
        importlib.import_module("execution.protection_registry_evidence")
        duplicate_keys = sorted(
            key
            for key in sys.modules
            if key == "src.position" or key.startswith("src.position.")
        )
        self.assertEqual([], duplicate_keys)

    def test_valid_current_authority_uses_canonical_class_and_is_not_rejected_as_invalid(self):
        fixture = fp11_policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        fixture.setUp()
        evidence, authority, _ = fixture._build("success")
        self.assertIs(type(authority), CurrentProtectionRegistryAuthority)
        decision = interpret_protection_registry_evidence(evidence, authority)
        self.assertTrue(decision.evidence_current)
        self.assertNotIn("CURRENT_AUTHORITY_INVALID", decision.reason_codes)

    def test_truly_wrong_authority_type_remains_rejected(self):
        fixture = fp11_policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        fixture.setUp()
        evidence, _, _ = fixture._build("success")
        with self.assertRaises(ProtectionRegistryPolicyError) as caught:
            interpret_protection_registry_evidence(evidence, object())
        self.assertEqual("CURRENT_AUTHORITY_INVALID", caught.exception.code)

    def test_storage_restart_fixture_uses_same_canonical_authority_type(self):
        fixture = fp11_storage_fixture_module.ProtectionRegistryCurrentnessPersistenceTests(
            methodName="test_normal_paper_runtime_writer_projection_is_accepted_by_fp11_restart_currentness"
        )
        fixture.setUp()
        try:
            _, owner_authority, _, _ = fixture._setup_case()
            self.assertIs(type(owner_authority), CurrentProtectionRegistryAuthority)
            self.assertEqual(
                "position.protection_registry_policy",
                type(owner_authority).__module__,
            )
        finally:
            fixture.tearDown()

    def test_canonical_entrypoint_assumption_matches_pythonpath_src_layout(self):
        package_file = Path(position.__file__).resolve()
        self.assertEqual((SOURCE_ROOT / "position").resolve(), package_file.parent)
        self.assertFalse((SOURCE_ROOT / "__init__.py").exists())

    def test_import_rule_has_no_provider_network_runtime_dependency(self):
        source = Path(__file__).read_text(encoding="utf-8")
        for forbidden in (
            "requests.",
            "urllib.",
            "socket.",
            "subprocess.",
            "submit_order",
            "cancel_order",
            "amend_order",
            "start_runtime",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
