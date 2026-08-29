import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from src.brokers.okx_action_capability import (
    ACCOUNT_LEVEL,
    CAPABILITY_PROFILE_VERSION,
    CURRENT,
    EMERGENCY_EXIT,
    EMERGENCY_EXIT_OPERATION,
    ENTRY,
    ENTRY_OPERATION,
    FORBIDDEN,
    FP03_ACTIONABLE,
    FP11_CONVERGED,
    ISOLATED,
    LONG_SHORT_MODE,
    NET_MODE,
    OKX_API_VERSION,
    OKX_INSTRUMENT_ID,
    OKX_INST_TYPE,
    OKX_PROVIDER,
    OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED,
    OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED,
    OKX_SWAP_INSTRUMENT_UNSUPPORTED,
    OKX_SWAP_POSITION_MODE_UNSUPPORTED,
    OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT,
    OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN,
    OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN,
    OKX_SWAP_RECONCILIATION_REQUIRED,
    OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN,
    OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN,
    OKX_SWAP_TRIGGER_BASIS_UNPROVEN,
    POSITION_EXIT,
    POSITION_EXIT_OPERATION,
    PROTECTION_OPERATION,
    PROTECTION_STOP,
    READ_ONLY_OPERATION,
    READ_ONLY_RECONCILIATION,
    RECONCILIATION_REQUIRED,
    REPO_EVIDENCED,
    UNRESOLVED_FAIL_CLOSED,
    OKXActionCapabilityFacts,
    canonical_okx_action_capability_hash,
    expected_repo_fieldset,
    expected_repo_fieldset_identity,
    okx_swap_action_capability_evidence_is_current,
    resolve_okx_swap_action_capability,
    validate_okx_swap_action_capability_evidence,
)


class OKXActionCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 29, 12, 55, 0, tzinfo=timezone.utc)

    def _facts(self, role=ENTRY, mode=NET_MODE, **changes):
        if role == ENTRY:
            operation = ENTRY_OPERATION
        elif role == PROTECTION_STOP:
            operation = PROTECTION_OPERATION
        elif role == POSITION_EXIT:
            operation = POSITION_EXIT_OPERATION
        elif role == EMERGENCY_EXIT:
            operation = EMERGENCY_EXIT_OPERATION
        elif role == READ_ONLY_RECONCILIATION:
            operation = READ_ONLY_OPERATION
        else:
            operation = "UNKNOWN"

        owner_row = expected_repo_fieldset_identity(role, mode)
        values = dict(
            capability_profile_version=CAPABILITY_PROFILE_VERSION,
            action_role=role,
            provider=OKX_PROVIDER,
            api_version=OKX_API_VERSION,
            canonical_symbol="BTC_USDT_PERP",
            provider_instrument_id=OKX_INSTRUMENT_ID,
            inst_type=OKX_INST_TYPE,
            account_level=ACCOUNT_LEVEL,
            position_mode=mode,
            margin_mode=ISOLATED,
            operation_class=operation,
            evaluated_at=self.now,
            provider_fieldset_ref=(
                owner_row["provider_fieldset_ref"] if owner_row is not None else None
            ),
            provider_fieldset_hash=(
                owner_row["provider_fieldset_hash"] if owner_row is not None else None
            ),
            provider_fieldset_generation_id=(
                owner_row["provider_fieldset_generation_id"] if owner_row is not None else None
            ),
            provider_fieldset=(
                owner_row["provider_fieldset"] if owner_row is not None else None
            ),
            reconciliation_status=CURRENT,
        )
        values.update(changes)
        return OKXActionCapabilityFacts(**values)

    def _assert_fieldset_unproven(self, facts):
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertEqual([OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN], evidence["reason_codes"])
        return evidence

    def test_entry_net_mode_exact_owner_row_is_repo_evidenced(self):
        facts = self._facts()
        owner_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)
        self.assertEqual(owner_row["provider_fieldset_ref"], facts.provider_fieldset_ref)
        self.assertEqual(owner_row["provider_fieldset_generation_id"], facts.provider_fieldset_generation_id)
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(REPO_EVIDENCED, evidence["capability_state"])
        self.assertEqual([], evidence["reason_codes"])
        validate_okx_swap_action_capability_evidence(evidence)

    def test_entry_long_short_mode_exact_owner_row_is_repo_evidenced(self):
        facts = self._facts(mode=LONG_SHORT_MODE)
        descriptor = facts.provider_fieldset
        self.assertEqual("BUY=long|SELL=short", descriptor["pos_side_rule"])
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(REPO_EVIDENCED, evidence["capability_state"])

    def test_read_only_exact_owner_rows_are_repo_evidenced(self):
        for mode in (NET_MODE, LONG_SHORT_MODE):
            with self.subTest(mode=mode):
                evidence = resolve_okx_swap_action_capability(
                    self._facts(role=READ_ONLY_RECONCILIATION, mode=mode)
                )
                self.assertEqual(REPO_EVIDENCED, evidence["capability_state"])
                self.assertEqual([], evidence["reason_codes"])

    def test_copied_descriptor_and_hash_with_forged_ref_fails_closed(self):
        owner_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)
        self._assert_fieldset_unproven(
            self._facts(
                provider_fieldset=owner_row["provider_fieldset"],
                provider_fieldset_hash=owner_row["provider_fieldset_hash"],
                provider_fieldset_ref="caller-forged:fieldset-ref",
                provider_fieldset_generation_id=owner_row["provider_fieldset_generation_id"],
            )
        )

    def test_copied_descriptor_and_hash_with_forged_generation_fails_closed(self):
        owner_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)
        self._assert_fieldset_unproven(
            self._facts(
                provider_fieldset=owner_row["provider_fieldset"],
                provider_fieldset_hash=owner_row["provider_fieldset_hash"],
                provider_fieldset_ref=owner_row["provider_fieldset_ref"],
                provider_fieldset_generation_id="caller-forged:generation",
            )
        )

    def test_valid_owner_row_identity_cannot_cross_role_or_mode(self):
        entry_net = expected_repo_fieldset_identity(ENTRY, NET_MODE)
        self._assert_fieldset_unproven(
            self._facts(
                role=READ_ONLY_RECONCILIATION,
                mode=NET_MODE,
                provider_fieldset=entry_net["provider_fieldset"],
                provider_fieldset_hash=entry_net["provider_fieldset_hash"],
                provider_fieldset_ref=entry_net["provider_fieldset_ref"],
                provider_fieldset_generation_id=entry_net["provider_fieldset_generation_id"],
            )
        )
        self._assert_fieldset_unproven(
            self._facts(
                role=ENTRY,
                mode=LONG_SHORT_MODE,
                provider_fieldset=entry_net["provider_fieldset"],
                provider_fieldset_hash=entry_net["provider_fieldset_hash"],
                provider_fieldset_ref=entry_net["provider_fieldset_ref"],
                provider_fieldset_generation_id=entry_net["provider_fieldset_generation_id"],
            )
        )

    def test_descriptor_or_hash_mismatch_fails_closed(self):
        owner_row = expected_repo_fieldset_identity(ENTRY, NET_MODE)
        mutated = dict(owner_row["provider_fieldset"])
        mutated["fields"] = [*mutated["fields"], "reduceOnly"]
        self._assert_fieldset_unproven(
            self._facts(
                provider_fieldset=mutated,
                provider_fieldset_hash=owner_row["provider_fieldset_hash"],
            )
        )
        self._assert_fieldset_unproven(
            self._facts(provider_fieldset_hash="sha256:" + "0" * 64)
        )

    def test_missing_ref_or_generation_fails_closed(self):
        for changes in (
            {"provider_fieldset_ref": None},
            {"provider_fieldset_generation_id": None},
        ):
            with self.subTest(changes=changes):
                self._assert_fieldset_unproven(self._facts(**changes))

    def test_wrong_canonical_provider_instrument_or_non_swap_fails_closed(self):
        for changes in (
            {"canonical_symbol": "ETH_USDT_PERP"},
            {"provider_instrument_id": "ETH-USDT-SWAP"},
            {"inst_type": "SPOT"},
        ):
            with self.subTest(changes=changes):
                evidence = resolve_okx_swap_action_capability(self._facts(**changes))
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
                self.assertEqual([OKX_SWAP_INSTRUMENT_UNSUPPORTED], evidence["reason_codes"])

    def test_wrong_or_unknown_account_level_fails_closed(self):
        for level in ("1", "3", "4", "UNKNOWN"):
            with self.subTest(level=level):
                evidence = resolve_okx_swap_action_capability(self._facts(account_level=level))
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
                self.assertEqual([OKX_SWAP_ACCOUNT_LEVEL_UNSUPPORTED], evidence["reason_codes"])

    def test_wrong_or_unknown_position_mode_fails_closed(self):
        for mode in ("portfolio", "UNKNOWN"):
            with self.subTest(mode=mode):
                facts = self._facts(mode=NET_MODE, position_mode=mode)
                evidence = resolve_okx_swap_action_capability(facts)
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
                self.assertEqual([OKX_SWAP_POSITION_MODE_UNSUPPORTED], evidence["reason_codes"])

    def test_spot_cash_trade_mode_is_forbidden(self):
        evidence = resolve_okx_swap_action_capability(self._facts(margin_mode="cash"))
        self.assertEqual(FORBIDDEN, evidence["capability_state"])
        self.assertEqual([OKX_SWAP_SPOT_TRADE_MODE_FORBIDDEN], evidence["reason_codes"])

    def test_caller_capability_assertion_never_creates_authority(self):
        for assertion in (True, {"compatible": True}, {"provider_capable": True}):
            with self.subTest(assertion=assertion):
                evidence = resolve_okx_swap_action_capability(
                    self._facts(caller_capability_assertion=assertion)
                )
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
                self.assertEqual(
                    [OKX_SWAP_CALLER_CAPABILITY_ASSERTION_REJECTED],
                    evidence["reason_codes"],
                )

    def test_fp03_actionable_still_cannot_select_provider_trigger_basis(self):
        facts = self._facts(
            role=PROTECTION_STOP,
            fp03_trigger_validity_ref="protection-trigger-validity:fixture",
            fp03_trigger_validity_status=FP03_ACTIONABLE,
            fp03_trigger_validity_currentness=CURRENT,
            fp11_registry_ref="protection-registry:fixture",
            fp11_registry_status=FP11_CONVERGED,
            fp11_registry_currentness=CURRENT,
        )
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertIn(OKX_SWAP_TRIGGER_BASIS_UNPROVEN, evidence["reason_codes"])
        self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])
        self.assertNotIn(OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT, evidence["reason_codes"])

    def test_protection_stop_remains_unresolved_without_provider_materialization(self):
        evidence = resolve_okx_swap_action_capability(self._facts(role=PROTECTION_STOP))
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertIn(OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN, evidence["reason_codes"])
        self.assertIn(OKX_SWAP_TRIGGER_BASIS_UNPROVEN, evidence["reason_codes"])
        self.assertIn(OKX_SWAP_PROTECTION_REGISTRY_NOT_CURRENT, evidence["reason_codes"])
        self.assertIsNone(evidence["provider_fieldset_ref"])

    def test_position_exit_remains_unresolved_with_coherent_fp05_sizing(self):
        facts = self._facts(
            role=POSITION_EXIT,
            fp05_close_sizing_ref="okx-close-sizing:fixture",
            fp05_close_sizing_status="FULLY_REDUCIBLE",
            fp05_close_sizing_currentness=CURRENT,
        )
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertEqual([OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN], evidence["reason_codes"])
        self.assertNotIn(OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN, evidence["reason_codes"])

    def test_emergency_exit_has_no_provider_proof_bypass(self):
        facts = self._facts(
            role=EMERGENCY_EXIT,
            fp05_close_sizing_ref="okx-close-sizing:emergency-fixture",
            fp05_close_sizing_status="FULLY_REDUCIBLE",
            fp05_close_sizing_currentness=CURRENT,
        )
        evidence = resolve_okx_swap_action_capability(facts)
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, evidence["capability_state"])
        self.assertEqual([OKX_SWAP_PROVIDER_FIELDSET_UNPROVEN], evidence["reason_codes"])

    def test_stale_or_reconciliation_required_mutation_facts_do_not_authorize(self):
        reconciliation = resolve_okx_swap_action_capability(
            self._facts(reconciliation_status=RECONCILIATION_REQUIRED)
        )
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, reconciliation["capability_state"])
        self.assertEqual([OKX_SWAP_RECONCILIATION_REQUIRED], reconciliation["reason_codes"])

        stale_fp05 = resolve_okx_swap_action_capability(
            self._facts(
                role=POSITION_EXIT,
                fp05_close_sizing_ref="okx-close-sizing:stale",
                fp05_close_sizing_status="FULLY_REDUCIBLE",
                fp05_close_sizing_currentness="STALE",
            )
        )
        self.assertIn(OKX_SWAP_REDUCIBLE_SIZE_UNPROVEN, stale_fp05["reason_codes"])
        self.assertEqual(UNRESOLVED_FAIL_CLOSED, stale_fp05["capability_state"])

    def test_read_only_mutation_rejection_remains_intact(self):
        mutation = resolve_okx_swap_action_capability(
            self._facts(
                role=READ_ONLY_RECONCILIATION,
                operation_class="MUTATION: ORDER_CANCEL",
            )
        )
        self.assertEqual(FORBIDDEN, mutation["capability_state"])
        self.assertEqual(
            [OKX_SWAP_READ_ONLY_MUTATION_FORBIDDEN],
            mutation["reason_codes"],
        )

    def test_same_material_has_stable_identity_and_time_only_remains_current(self):
        facts = self._facts()
        first = resolve_okx_swap_action_capability(facts)
        later_facts = replace(facts, evaluated_at=self.now + timedelta(hours=2))
        later = resolve_okx_swap_action_capability(later_facts)
        self.assertEqual(first["capability_evidence_id"], later["capability_evidence_id"])
        self.assertTrue(okx_swap_action_capability_evidence_is_current(first, later_facts))

    def test_material_owner_row_ref_generation_or_hash_change_invalidates_currentness(self):
        facts = self._facts()
        first = resolve_okx_swap_action_capability(facts)
        changes = (
            {"provider_fieldset_ref": "forged:row-ref"},
            {"provider_fieldset_generation_id": "forged:generation"},
            {"provider_fieldset_hash": "sha256:" + "1" * 64},
        )
        for change in changes:
            with self.subTest(change=change):
                changed = replace(
                    facts,
                    evaluated_at=self.now + timedelta(seconds=1),
                    **change,
                )
                second = resolve_okx_swap_action_capability(changed)
                self.assertEqual(UNRESOLVED_FAIL_CLOSED, second["capability_state"])
                self.assertNotEqual(first["capability_evidence_id"], second["capability_evidence_id"])
                self.assertFalse(okx_swap_action_capability_evidence_is_current(first, changed))

    def test_expected_descriptor_is_copy_not_mutable_owner_authority(self):
        descriptor = expected_repo_fieldset(ENTRY, NET_MODE)
        descriptor["fields"].append("callerMutation")
        fresh = expected_repo_fieldset(ENTRY, NET_MODE)
        self.assertNotIn("callerMutation", fresh["fields"])
        self.assertNotEqual(
            canonical_okx_action_capability_hash(descriptor),
            canonical_okx_action_capability_hash(fresh),
        )

    def test_resolver_has_no_provider_or_runtime_dependency(self):
        evidence = resolve_okx_swap_action_capability(self._facts())
        self.assertEqual(REPO_EVIDENCED, evidence["capability_state"])
        for forbidden_name in (
            "credentials",
            "api_key",
            "secret_key",
            "passphrase",
            "account_balance",
            "provider_request",
            "process_id",
            "capital",
        ):
            self.assertNotIn(forbidden_name, evidence)


if __name__ == "__main__":
    unittest.main()
