import inspect
import unittest
from dataclasses import replace
from pathlib import Path

from src.brokers.okx_close_sizing import (
    CLOSE_CAPABILITY_UNPROVEN,
    UNRESOLVED_FAIL_CLOSED,
    evaluate_okx_close_residual_sizing,
)
from src.brokers.okx_demo import OKXDemoAdapter
from src.execution.external_close_evidence import (
    build_external_manual_close_convergence_evidence,
)
from src.position import interpret_protection_registry_evidence
import tests.brokers.test_okx_close_sizing as fp05_fixture_module
import tests.execution.test_external_close_evidence as fp10_fixture_module
import tests.position.test_protection_registry_policy as fp11_policy_fixture_module


class P0IntegratedFailClosedSafetyTests(unittest.TestCase):
    """Safety definitions for gaps that must remain non-authorizing at LF-2."""

    @staticmethod
    def _fp05_fixture():
        fixture = fp05_fixture_module.OKXCloseResidualSizingTests(
            methodName="test_exact_current_facts_are_fully_reducible"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp10_fixture():
        fixture = fp10_fixture_module.ExternalCloseEvidenceProducerTests(
            methodName="test_fp10_exact_flat_current_compatible_chain_emits_consumable_close_eligible_evidence"
        )
        fixture.setUp()
        return fixture

    @staticmethod
    def _fp11_fixture():
        fixture = fp11_policy_fixture_module.ProtectionRegistryPolicyTests(
            methodName="test_converged_exact_current_registry_preserves_existing_protected_state_only"
        )
        fixture.setUp()
        return fixture

    def test_fp02_unresolved_close_capability_is_evidence_only_and_produces_no_provider_size(self):
        fixture = self._fp05_fixture()
        unresolved = replace(
            fixture.capability(),
            capability_state=UNRESOLVED_FAIL_CLOSED,
            provider_fieldset_status=UNRESOLVED_FAIL_CLOSED,
        )
        evidence = evaluate_okx_close_residual_sizing(
            fixture.sizing_input(capability=unresolved)
        )
        self.assertEqual(CLOSE_CAPABILITY_UNPROVEN, evidence["sizing_state"])
        self.assertIn("OKX_CLOSE_CAPABILITY_UNPROVEN", evidence["reason_codes"])
        self.assertIsNone(evidence["raw_provider_close_size"])
        self.assertIsNone(evidence["quantized_provider_close_size"])
        self.assertIsNone(evidence["effective_canonical_close_quantity"])

    def test_current_okx_adapter_has_no_provider_native_protection_or_close_mutation_surface(self):
        public_callables = {
            name
            for name, member in inspect.getmembers(OKXDemoAdapter, predicate=callable)
            if not name.startswith("_")
        }
        self.assertIn("submit_entry", public_callables)
        self.assertNotIn("submit_protection", public_callables)
        self.assertNotIn("replace_protection", public_callables)
        self.assertNotIn("cancel_protection", public_callables)
        self.assertNotIn("submit_exit", public_callables)
        self.assertNotIn("submit_emergency_exit", public_callables)

    def test_fp10_close_eligible_evidence_is_not_a_lifecycle_transition_or_trade_result(self):
        fixture = self._fp10_fixture()
        evidence = build_external_manual_close_convergence_evidence(fixture.assembly())
        self.assertEqual("LIFECYCLE_CLOSE_ELIGIBLE", evidence["convergence_state"])
        self.assertEqual(["NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE"], evidence["required_dispositions"])
        self.assertNotIn("lifecycle_event", evidence)
        self.assertNotIn("trade_result_id", evidence)
        self.assertNotIn("entry_fill_ids", evidence)
        self.assertNotIn("exit_fill_ids", evidence)

    def test_fp11_missing_multiple_external_and_conflict_never_supply_cleanup_target_or_mutation_authority(self):
        fixture = self._fp11_fixture()
        for kind in ("missing", "multiple", "intended-plus-external", "conflict", "unknown"):
            with self.subTest(kind=kind):
                evidence, authority, _ = fixture._build(kind)
                decision = interpret_protection_registry_evidence(evidence, authority)
                self.assertFalse(decision.provider_mutation_authorized)
                self.assertIsNone(decision.cleanup_target_ref)

    def test_runtime_preflight_is_contract_only_and_role_scoped_not_transferable(self):
        repo_root = Path(__file__).resolve().parents[2]
        contract_path = repo_root / "contracts" / "RUNTIME_PREFLIGHT_PROFILE_V0_1.md"
        implementation_path = repo_root / "src" / "integration" / "runtime_preflight.py"
        self.assertTrue(contract_path.is_file())
        self.assertFalse(implementation_path.exists())

        contract = contract_path.read_text(encoding="utf-8").lower()
        self.assertIn("runtime-preflight-v0.1", contract)
        self.assertIn("for one role is never transferable to another role", contract)
        self.assertIn("heartbeat", contract)
        self.assertIn("supervisor", contract)
        self.assertIn("allowlist", contract)
        self.assertIn("external consumer", contract)

    def test_contract_only_runtime_preflight_cannot_be_mistaken_for_provider_authority(self):
        repo_root = Path(__file__).resolve().parents[2]
        contract = (repo_root / "contracts" / "RUNTIME_PREFLIGHT_PROFILE_V0_1.md").read_text(
            encoding="utf-8"
        ).lower()
        self.assertIn("is not provider authority", contract)
        self.assertIn("order authority", contract)
        self.assertIn("bounded-live-fire authority", contract)
        self.assertIn("live authorization", contract)
        self.assertIn("capital", contract)


if __name__ == "__main__":
    unittest.main()
