import unittest
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.okx_close_sizing import (
    APPLICABLE_CONSTRAINT,
    CLOSE_CAPABILITY_UNPROVEN,
    CLOSE_ROLE_SCOPE,
    EXPOSURE_ALREADY_FLAT,
    FULLY_REDUCIBLE,
    METADATA_STALE_OR_UNKNOWN,
    NOT_APPLICABLE_TO_CLOSE,
    PARTIALLY_REDUCIBLE,
    POST_ACTION_RESIDUAL,
    PRE_ACTION,
    PRIOR_OUTCOME_AMBIGUOUS,
    PRIOR_OUTCOME_CLEAR,
    RECONCILIATION_REQUIRED,
    REDUCIBLE_EXPOSURE_UNKNOWN,
    REPO_EVIDENCED,
    REQUIRED_FOR_CLOSE,
    RESIDUAL_NONZERO_REPRESENTABLE,
    RESIDUAL_NONZERO_UNREPRESENTABLE,
    UNRESOLVED_FAIL_CLOSED,
    OKXCloseMetadataApplicabilityEvidence,
    OKXCloseRoleCapabilityEvidence,
    OKXCloseSizingError,
    OKXCloseSizingInput,
    OKXProviderExposureObservation,
    evaluate_okx_close_residual_sizing,
    okx_close_residual_sizing_evidence_is_current,
    validate_okx_close_residual_sizing_evidence,
)
from src.brokers.okx_sizing import OKXInstrumentMetadata
from src.execution.external_close_evidence import (
    CURRENT,
    LINEAGE_CURRENT_GENERATION,
    LINEAGE_EXTERNAL,
    MULTIPLICITY_SINGLE,
    PROVIDER_BINDING_EXACT,
    OwnershipEvaluationContext,
    ProviderObjectObservation,
    build_external_provider_ownership_evidence,
    canonical_evidence_hash,
)


class OKXCloseResidualSizingTests(unittest.TestCase):
    def setUp(self):
        self.revision = "e9e8aa6674bc5696a194e61e2e0dc1b4b75ef86c"
        self.position_observed = datetime(2026, 8, 29, 9, 50, 20, tzinfo=timezone.utc)
        self.provider_received = self.position_observed + timedelta(seconds=1)
        self.now = self.position_observed + timedelta(seconds=10)

    def plan(self, **changes):
        value = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-fp05-001",
            "risk_decision_id": "risk-fp05-001",
            "intent_id": "intent-fp05-001",
            "strategy_id": "strategy-fp05",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
            "quantity": "0.003",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "leverage": "20",
            "margin_mode": "ISOLATED",
            "entry_instruction": {"profile_version": "entry-v0.1", "order_type": "MARKET"},
            "protection_instruction": {"stop_level": "59400", "target_level": "61200", "max_hold_seconds": 1800},
            "created_at": "2026-08-29T09:40:00Z",
            "expires_at": "2026-08-29T09:40:30Z",
            "risk_policy_version": "e5-fp05-policy-v0.1",
        }
        value.update(changes)
        return value

    def position(self, *, quantity="0.0012", observed=None, lifecycle="OPEN_PROTECTED", reconciliation="CONSISTENT", **changes):
        observed = self.position_observed if observed is None else observed
        value = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp05-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": quantity,
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T09:45:00Z",
            "broker_state_observed_at": observed.isoformat().replace("+00:00", "Z"),
            "reconciliation_status": reconciliation,
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        value.update(changes)
        return value

    def action(self, *, quantity="0.0012", observed=None, emergency=False, **changes):
        observed = self.position_observed if observed is None else observed
        value = {
            "schema_version": "contracts-v0.1",
            "close_profile_version": "close-v0.1",
            "position_action_id": "posact-fp05-001" if not emergency else "posact-fp05-emergency-001",
            "position_id": "position-fp05-001",
            "action": "EMERGENCY_EXIT" if emergency else "EXIT",
            "reason_codes": ["E5_EMERGENCY_EXIT_REQUIRED"] if emergency else ["E5_EXIT_REQUESTED"],
            "risk_policy_version": "e5-fp05-policy-v0.1",
            "trade_plan_id": "plan-fp05-001",
            "risk_decision_id": "risk-fp05-001",
            "strategy_id": "strategy-fp05",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "source_lifecycle_state": "EMERGENCY" if emergency else "OPEN_PROTECTED",
            "position_observed_at": observed.isoformat().replace("+00:00", "Z"),
            "position_reconciliation_status": "CONSISTENT",
            "quantity": quantity,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "close_order_type": "MARKET",
            "created_at": self.now.isoformat().replace("+00:00", "Z"),
            "expires_at": (self.now + timedelta(seconds=60)).isoformat().replace("+00:00", "Z"),
        }
        value.update(changes)
        return value

    def metadata(self, *, observed_at=None, **changes):
        observed_at = self.position_observed if observed_at is None else observed_at
        value = OKXInstrumentMetadata(
            provider="OKX",
            canonical_symbol="BTC_USDT_PERP",
            instrument_id="BTC-USDT-SWAP",
            inst_type="SWAP",
            ct_val=Decimal("0.0001"),
            ct_mult=Decimal("1"),
            ct_val_ccy="BTC",
            ct_type="linear",
            lot_sz=Decimal("1"),
            min_sz=Decimal("1"),
            tick_sz=Decimal("0.1"),
            state="live",
            observed_at=observed_at,
            metadata_ref="fixture:fp05:metadata:001",
        )
        return replace(value, **changes)

    def capability(self, *, role="POSITION_EXIT", **changes):
        value = OKXCloseRoleCapabilityEvidence(
            capability_profile_version="okx-swap-action-role-capability-v0.1",
            capability_row_ref="fixture:fp02:position-exit:accepted",
            action_role=role,
            capability_state=REPO_EVIDENCED,
            capability_generation_id="fp02-gen-001",
            currentness_status=CURRENT,
            provider="OKX",
            canonical_symbol="BTC_USDT_PERP",
            provider_instrument_id="BTC-USDT-SWAP",
            inst_type="SWAP",
            account_level="2",
            position_mode="net_mode",
            margin_mode="isolated",
            provider_position_quantity_unit="CONTRACT",
            provider_position_quantity_proof_ref="fixture:fp02:provider-position-contract-unit",
            provider_fieldset_status=REPO_EVIDENCED,
        )
        return replace(value, **changes)

    def applicability(self, *, role="POSITION_EXIT", close_step="1", close_min="1", close_max=None, **changes):
        value = OKXCloseMetadataApplicabilityEvidence(
            action_role=role,
            applicability_scope=CLOSE_ROLE_SCOPE,
            applicability_proof_ref="fixture:fp05:close-metadata-applicability",
            applicability_generation_id="fp05-metadata-proof-gen-001",
            currentness_status=CURRENT,
            instrument_metadata_generation="okx-metadata-gen-001",
            conversion_profile="LINEAR_DIRECT_BASE_ASSET",
            conversion_status=REQUIRED_FOR_CLOSE,
            step_status=APPLICABLE_CONSTRAINT,
            min_status=APPLICABLE_CONSTRAINT if close_min is not None else NOT_APPLICABLE_TO_CLOSE,
            max_status=APPLICABLE_CONSTRAINT if close_max is not None else NOT_APPLICABLE_TO_CLOSE,
            close_step=None if close_step is None else Decimal(close_step),
            close_min_size=None if close_min is None else Decimal(close_min),
            close_max_size=None if close_max is None else Decimal(close_max),
        )
        return replace(value, **changes)

    def provider(self, *, contracts="12", canonical="0.0012", observed=None, received=None, currentness=CURRENT, snapshot_ref="provider-position-snapshot-001", generation="provider-gen-001", **changes):
        observed = self.position_observed if observed is None else observed
        received = observed + timedelta(seconds=1) if received is None else received
        snapshot = {
            "provider": "OKX",
            "instrument": "BTC-USDT-SWAP",
            "position_side": "net",
            "contracts": contracts,
            "normalized_btc": canonical,
            "observation_generation": generation,
        }
        value = OKXProviderExposureObservation(
            provider_identity_ref="provider-identity:okx-fixture",
            provider_identity={"provider": "OKX", "environment": "fixture", "account_scope": "sanitized"},
            provider_object_ref="provider-position:btc-usdt-swap:net",
            provider_position_side_ref="net",
            provider_position_snapshot_ref=snapshot_ref,
            provider_position_snapshot=snapshot,
            provider_position_observation_generation_id=generation,
            provider_position_observed_at=observed,
            provider_position_received_at=received,
            provider_position_currentness_status=currentness,
            provider_reducible_quantity=None if contracts is None else Decimal(contracts),
            provider_reducible_quantity_unit="CONTRACT",
            normalized_canonical_quantity=Decimal(canonical),
            account_level="2",
            position_mode="net_mode",
            margin_mode="isolated",
        )
        return replace(value, **changes)

    def fp04(self, provider, *, external=False, registry_status=CURRENT):
        observation = ProviderObjectObservation(
            provider_object_class="POSITION_EXPOSURE",
            provider_identity_ref=provider.provider_identity_ref,
            provider_identity=provider.provider_identity,
            canonical_symbol="BTC_USDT_PERP",
            provider_instrument_ref=provider.provider_instrument_id,
            provider_object_ref=provider.provider_object_ref,
            provider_snapshot_ref=provider.provider_position_snapshot_ref,
            provider_snapshot=provider.provider_position_snapshot,
            provider_observation_generation_id=provider.provider_position_observation_generation_id,
            provider_observed_at=provider.provider_position_observed_at,
            provider_received_at=provider.provider_position_received_at,
        )
        lineage = [] if external else [
            {
                "owner": "E4",
                "evidence_class": "PROVIDER_POSITION_BINDING",
                "evidence_ref": "fixture:e4:position-binding",
                "evidence_hash": canonical_evidence_hash({"position_id": "position-fp05-001", "provider_object_ref": provider.provider_object_ref}),
                "evidence_generation_id": provider.provider_position_observation_generation_id,
                "observed_or_created_at": provider.provider_position_observed_at.isoformat().replace("+00:00", "Z"),
                "lineage_role": "POSITION",
                "claim_status": "CLAIMS_OWNERSHIP",
            }
        ]
        registry = [
            {
                "owner": "E6",
                "evidence_class": "POSITION_EXECUTION_REGISTRY",
                "evidence_ref": "fixture:e6:position-registry",
                "evidence_hash": canonical_evidence_hash({"position_id": "position-fp05-001", "generation": provider.provider_position_observation_generation_id}),
                "evidence_generation_id": provider.provider_position_observation_generation_id,
                "observed_at": provider.provider_position_received_at.isoformat().replace("+00:00", "Z"),
                "currentness_status": registry_status,
            }
        ]
        context = OwnershipEvaluationContext(
            current_project_revision=self.revision,
            local_lineage_evidence=lineage,
            local_registry_evidence=registry,
            lineage_generation_status=LINEAGE_EXTERNAL if external else LINEAGE_CURRENT_GENERATION,
            provider_binding_status=PROVIDER_BINDING_EXACT,
            multiplicity_status=MULTIPLICITY_SINGLE,
            evaluated_at=provider.provider_position_received_at + timedelta(seconds=1),
        )
        evidence = build_external_provider_ownership_evidence(observation, context)
        return evidence, context

    def sizing_input(
        self,
        *,
        source_position=None,
        current_position=None,
        action=None,
        parent_plan=None,
        provider=None,
        external_fp04=False,
        registry_status=CURRENT,
        capability=None,
        metadata=None,
        applicability=None,
        phase=PRE_ACTION,
        prior_status=PRIOR_OUTCOME_CLEAR,
        evaluated_at=None,
    ):
        source_position = self.position() if source_position is None else source_position
        current_position = source_position if current_position is None else current_position
        action = self.action(quantity=source_position["actual_quantity"], observed=datetime.fromisoformat(source_position["broker_state_observed_at"][:-1] + "+00:00")) if action is None else action
        parent_plan = self.plan() if parent_plan is None else parent_plan
        provider = self.provider(canonical=current_position["actual_quantity"]) if provider is None else provider
        fp04, context = self.fp04(provider, external=external_fp04, registry_status=registry_status)
        role = "EMERGENCY_EXIT" if action["action"] == "EMERGENCY_EXIT" else "POSITION_EXIT"
        capability = self.capability(role=role) if capability is None else capability
        metadata = self.metadata() if metadata is None else metadata
        applicability = self.applicability(role=role) if applicability is None else applicability
        return OKXCloseSizingInput(
            action=action,
            parent_plan=parent_plan,
            source_position=source_position,
            current_position=current_position,
            evaluation_phase=phase,
            prior_close_outcome_status=prior_status,
            prior_close_outcome_ref="fixture:prior-close-outcome:clear" if prior_status == PRIOR_OUTCOME_CLEAR else "fixture:prior-close-outcome:ambiguous",
            provider_exposure=provider,
            fp04_ownership_evidence=fp04,
            fp04_currentness_context=context,
            capability=capability,
            instrument_metadata=metadata,
            metadata_applicability=applicability,
            evaluated_at=self.now if evaluated_at is None else evaluated_at,
        )

    def test_exact_current_facts_are_fully_reducible(self):
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input())
        self.assertEqual(FULLY_REDUCIBLE, evidence["sizing_state"])
        self.assertEqual("12", evidence["quantized_provider_close_size"])
        self.assertEqual("0.0012", evidence["effective_canonical_close_quantity"])
        validate_okx_close_residual_sizing_evidence(evidence)

    def test_valid_strict_subset_is_partially_reducible(self):
        value = self.sizing_input(applicability=self.applicability(close_max="10"))
        evidence = evaluate_okx_close_residual_sizing(value)
        self.assertEqual(PARTIALLY_REDUCIBLE, evidence["sizing_state"])
        self.assertEqual("10", evidence["quantized_provider_close_size"])
        self.assertEqual("0.0010", evidence["effective_canonical_close_quantity"])

    def test_fresh_post_action_positive_residual_is_representable(self):
        source = self.position()
        observed = self.position_observed + timedelta(seconds=20)
        current = self.position(quantity="0.0004", observed=observed, lifecycle="EXIT_REQUESTED")
        provider = self.provider(contracts="4", canonical="0.0004", observed=observed, generation="provider-gen-002", snapshot_ref="provider-position-snapshot-002")
        value = self.sizing_input(source_position=source, current_position=current, provider=provider, phase=POST_ACTION_RESIDUAL, evaluated_at=observed + timedelta(seconds=10))
        evidence = evaluate_okx_close_residual_sizing(value)
        self.assertEqual(RESIDUAL_NONZERO_REPRESENTABLE, evidence["sizing_state"])
        self.assertEqual("4", evidence["quantized_provider_close_size"])
        self.assertEqual(source["broker_state_observed_at"], evidence["source_position_ref"].split("@", 1)[1])

    def test_positive_dust_residual_is_explicit_unrepresentable(self):
        source = self.position(quantity="0.00005")
        action = self.action(quantity="0.00005")
        provider = self.provider(contracts="0.5", canonical="0.00005")
        value = self.sizing_input(source_position=source, action=action, provider=provider)
        evidence = evaluate_okx_close_residual_sizing(value)
        self.assertEqual(RESIDUAL_NONZERO_UNREPRESENTABLE, evidence["sizing_state"])
        self.assertIsNone(evidence["quantized_provider_close_size"])
        self.assertIn("OKX_CLOSE_SIZE_NOT_REPRESENTABLE", evidence["reason_codes"])

    def test_post_action_unrepresentable_residual_has_no_unchanged_retry_authority(self):
        source = self.position()
        observed = self.position_observed + timedelta(seconds=20)
        current = self.position(quantity="0.00005", observed=observed, lifecycle="EXIT_REQUESTED")
        provider = self.provider(contracts="0.5", canonical="0.00005", observed=observed, generation="provider-gen-002", snapshot_ref="provider-position-snapshot-002")
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(source_position=source, current_position=current, provider=provider, phase=POST_ACTION_RESIDUAL, evaluated_at=observed + timedelta(seconds=10)))
        self.assertEqual(RESIDUAL_NONZERO_UNREPRESENTABLE, evidence["sizing_state"])
        self.assertIn("OKX_CLOSE_NEWER_EVIDENCE_REQUIRED", evidence["reason_codes"])
        self.assertIsNone(evidence["quantized_provider_close_size"])

    def test_fresh_exact_zero_provider_and_canonical_exposure_is_flat_evidence_only(self):
        source = self.position()
        observed = self.position_observed + timedelta(seconds=20)
        current = self.position(quantity="0", observed=observed, lifecycle="EXIT_REQUESTED")
        provider = self.provider(contracts="0", canonical="0", observed=observed, generation="provider-gen-flat", snapshot_ref="provider-position-snapshot-flat")
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(source_position=source, current_position=current, provider=provider, phase=POST_ACTION_RESIDUAL, evaluated_at=observed + timedelta(seconds=10)))
        self.assertEqual(EXPOSURE_ALREADY_FLAT, evidence["sizing_state"])
        self.assertIsNone(evidence["quantized_provider_close_size"])
        self.assertNotIn("CLOSED", evidence)
        self.assertNotIn("order_request", evidence)

    def test_unknown_provider_reducible_exposure_fails_closed(self):
        provider = self.provider(contracts=None, canonical="0.0012")
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(provider=provider))
        self.assertEqual(REDUCIBLE_EXPOSURE_UNKNOWN, evidence["sizing_state"])
        self.assertIsNone(evidence["quantized_provider_close_size"])

    def test_stale_position_provider_or_fp04_fails_closed(self):
        stale_position = self.position(reconciliation="RECONCILIATION_REQUIRED")
        position_evidence = evaluate_okx_close_residual_sizing(self.sizing_input(source_position=stale_position, current_position=stale_position, action=self.action()))
        self.assertEqual(RECONCILIATION_REQUIRED, position_evidence["sizing_state"])

        stale_provider = self.provider(currentness="STALE")
        provider_evidence = evaluate_okx_close_residual_sizing(self.sizing_input(provider=stale_provider))
        self.assertEqual(REDUCIBLE_EXPOSURE_UNKNOWN, provider_evidence["sizing_state"])

        fp04_evidence = evaluate_okx_close_residual_sizing(self.sizing_input(registry_status="STALE"))
        self.assertEqual(REDUCIBLE_EXPOSURE_UNKNOWN, fp04_evidence["sizing_state"])

    def test_external_manual_fp04_is_not_silently_adopted(self):
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(external_fp04=True))
        self.assertEqual(REDUCIBLE_EXPOSURE_UNKNOWN, evidence["sizing_state"])
        self.assertEqual("EXTERNAL_UNTRACKED", evidence["fp04_ownership_classification"])
        self.assertIsNone(evidence["quantized_provider_close_size"])

    def test_unproven_close_capability_blocks_both_close_roles(self):
        ordinary = evaluate_okx_close_residual_sizing(
            self.sizing_input(capability=self.capability(capability_state=UNRESOLVED_FAIL_CLOSED, provider_fieldset_status=UNRESOLVED_FAIL_CLOSED))
        )
        self.assertEqual(CLOSE_CAPABILITY_UNPROVEN, ordinary["sizing_state"])

        source = self.position(lifecycle="EMERGENCY")
        action = self.action(emergency=True)
        emergency = evaluate_okx_close_residual_sizing(
            self.sizing_input(
                source_position=source,
                current_position=source,
                action=action,
                capability=self.capability(role="EMERGENCY_EXIT", capability_state=UNRESOLVED_FAIL_CLOSED, provider_fieldset_status=UNRESOLVED_FAIL_CLOSED),
                applicability=self.applicability(role="EMERGENCY_EXIT"),
            )
        )
        self.assertEqual(CLOSE_CAPABILITY_UNPROVEN, emergency["sizing_state"])

    def test_entry_only_constraint_evidence_cannot_satisfy_close_applicability(self):
        entry_only = self.applicability(role="ENTRY")
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(applicability=entry_only))
        self.assertEqual(METADATA_STALE_OR_UNKNOWN, evidence["sizing_state"])
        self.assertIn("OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN", evidence["reason_codes"])

    def test_stale_metadata_fails_closed(self):
        stale = self.metadata(observed_at=self.now - timedelta(seconds=301))
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(metadata=stale))
        self.assertEqual(METADATA_STALE_OR_UNKNOWN, evidence["sizing_state"])
        self.assertIsNone(evidence["quantized_provider_close_size"])

    def test_unresolved_prior_outcome_precedes_new_sizing(self):
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(prior_status=PRIOR_OUTCOME_AMBIGUOUS))
        self.assertEqual(RECONCILIATION_REQUIRED, evidence["sizing_state"])
        self.assertIn("OKX_CLOSE_PRIOR_OUTCOME_AMBIGUOUS", evidence["reason_codes"])
        self.assertIsNone(evidence["quantized_provider_close_size"])

    def test_quantization_never_exceeds_provider_or_canonical_authority(self):
        source = self.position(quantity="0.00125")
        action = self.action(quantity="0.00125")
        provider = self.provider(contracts="12.5", canonical="0.00125")
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input(source_position=source, action=action, provider=provider))
        self.assertEqual(PARTIALLY_REDUCIBLE, evidence["sizing_state"])
        self.assertEqual("12", evidence["quantized_provider_close_size"])
        self.assertLessEqual(Decimal(evidence["quantized_provider_close_size"]), Decimal(evidence["provider_reducible_quantity"]))
        self.assertLessEqual(Decimal(evidence["effective_canonical_close_quantity"]), Decimal(evidence["current_canonical_quantity"]))
        self.assertLessEqual(Decimal(evidence["effective_canonical_close_quantity"]), Decimal(evidence["canonical_authorized_close_quantity"]))

    def test_material_changes_invalidate_old_evidence(self):
        value = self.sizing_input()
        evidence = evaluate_okx_close_residual_sizing(value)
        changed_capability = replace(value.capability, capability_generation_id="fp02-gen-002")
        changed = replace(value, capability=changed_capability)
        self.assertFalse(okx_close_residual_sizing_evidence_is_current(evidence, changed))

    def test_later_timestamp_alone_does_not_create_new_authority(self):
        value = self.sizing_input()
        evidence = evaluate_okx_close_residual_sizing(value)
        later = replace(value, evaluated_at=value.evaluated_at + timedelta(seconds=1))
        self.assertTrue(okx_close_residual_sizing_evidence_is_current(evidence, later))
        with self.assertRaises(OKXCloseSizingError) as caught:
            evaluate_okx_close_residual_sizing(later, supersedes_evidence=evidence)
        self.assertEqual("SUPERSESSION_REQUIRES_MATERIAL_CHANGE", caught.exception.code)

    def test_materially_new_provider_snapshot_creates_explicit_supersession(self):
        value = self.sizing_input()
        first = evaluate_okx_close_residual_sizing(value)
        observed = self.position_observed + timedelta(seconds=1)
        current = self.position(observed=observed)
        action = self.action(observed=observed)
        provider = self.provider(observed=observed, generation="provider-gen-002", snapshot_ref="provider-position-snapshot-002")
        second_input = self.sizing_input(source_position=current, current_position=current, action=action, provider=provider, evaluated_at=observed + timedelta(seconds=10))
        second = evaluate_okx_close_residual_sizing(second_input, supersedes_evidence=first)
        self.assertNotEqual(first["sizing_evidence_id"], second["sizing_evidence_id"])
        self.assertEqual(first["sizing_evidence_id"], second["supersedes_sizing_evidence_id"])

    def test_evidence_identity_is_mapping_order_independent(self):
        value = self.sizing_input()
        first = evaluate_okx_close_residual_sizing(value)
        provider = value.provider_exposure
        reordered_identity = dict(reversed(list(provider.provider_identity.items())))
        reordered_snapshot = dict(reversed(list(provider.provider_position_snapshot.items())))
        reordered_provider = replace(provider, provider_identity=reordered_identity, provider_position_snapshot=reordered_snapshot)
        second_input = self.sizing_input(provider=reordered_provider)
        second = evaluate_okx_close_residual_sizing(second_input)
        self.assertEqual(first["sizing_evidence_id"], second["sizing_evidence_id"])
        self.assertEqual(first["sizing_evidence_hash"], second["sizing_evidence_hash"])

    def test_emergency_exit_has_same_sizing_safety_invariants(self):
        source = self.position(lifecycle="EMERGENCY")
        action = self.action(emergency=True)
        value = self.sizing_input(
            source_position=source,
            current_position=source,
            action=action,
            capability=self.capability(role="EMERGENCY_EXIT"),
            applicability=self.applicability(role="EMERGENCY_EXIT"),
        )
        evidence = evaluate_okx_close_residual_sizing(value)
        self.assertEqual(FULLY_REDUCIBLE, evidence["sizing_state"])
        self.assertEqual("EMERGENCY_EXIT", evidence["action_role"])

    def test_no_transport_credentials_or_mutation_surface_is_part_of_input_or_evidence(self):
        input_fields = {item.name for item in fields(OKXCloseSizingInput)}
        forbidden = {"transport", "client", "api_key", "secret", "passphrase", "credentials", "submit", "cancel", "amend", "close_order"}
        self.assertTrue(input_fields.isdisjoint(forbidden))
        evidence = evaluate_okx_close_residual_sizing(self.sizing_input())
        serialized_keys = set(evidence)
        self.assertTrue(serialized_keys.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
