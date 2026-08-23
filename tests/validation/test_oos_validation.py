from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import unittest

from registry.contract_validation import validate_validation_decision_contract
from validation import (
    EXECUTION_EXECUTED,
    EXECUTION_NOT_RUN,
    OOSValidationContext,
    ValidationPolicy,
    ValidationSubject,
    evaluate_oos_validation,
)


class ContractObject:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def to_contract(self) -> dict:
        return deepcopy(self.payload)


def backtest_payload(**overrides) -> dict:
    payload = {
        "schema_version": "contracts-v0.1",
        "backtest_result_id": "backtest_oos_fixture_001",
        "strategy_id": "strategy-oos-fixture",
        "strategy_version": "1.0.0",
        "strategy_content_hash": "sha256:strategy-oos-fixture",
        "runtime_version": "0.1.0",
        "dataset_id": "dataset-oos-2026q2",
        "dataset_hash": "sha256:oos-2026q2",
        "dataset_start": "2026-04-01T00:00:00Z",
        "dataset_end": "2026-06-30T23:59:59Z",
        "cost_model_version": "cost-oos-fixture-v1",
        "created_at": "2026-08-22T12:00:00Z",
        "total_trades": 20,
        "wins": 12,
        "losses": 7,
        "breakeven": 1,
        "gross_pnl": "150",
        "net_pnl": "100",
        "total_fees": "20",
        "profit_factor": "1.5",
        "expectancy": "5",
        "max_drawdown": "10",
        "max_consecutive_losses": 2,
    }
    payload.update(overrides)
    return payload


def subject() -> ValidationSubject:
    return ValidationSubject(
        strategy_id="strategy-oos-fixture",
        strategy_version="1.0.0",
        backtest_result_id="backtest_oos_fixture_001",
    )


def passing_policy(**overrides) -> ValidationPolicy:
    values = {
        "version": "oos-policy-v0.1-fixture",
        "min_total_trades": 10,
        "min_net_pnl": Decimal("0"),
        "max_drawdown": Decimal("20"),
        "max_consecutive_losses": 3,
        "min_profit_factor": Decimal("1.2"),
    }
    values.update(overrides)
    return ValidationPolicy(**values)


def valid_context(**overrides) -> OOSValidationContext:
    values = {
        "split_id": "split-2026-h1-v1",
        "oos_dataset_id": "dataset-oos-2026q2",
        "oos_dataset_hash": "sha256:oos-2026q2",
        "oos_dataset_start": "2026-04-01T00:00:00Z",
        "oos_dataset_end": "2026-06-30T23:59:59Z",
        "training_dataset_id": "dataset-train-2025q4-2026q1",
        "training_dataset_hash": "sha256:train-2025q4-2026q1",
        "validation_policy_version": "oos-policy-v0.1-fixture",
    }
    values.update(overrides)
    return OOSValidationContext(**values)


def evaluate(
    payload=None,
    *,
    policy=None,
    context=None,
    execution_state=EXECUTION_EXECUTED,
    decided_at="2026-08-22T12:30:00Z",
):
    return evaluate_oos_validation(
        subject=subject(),
        backtest_result=backtest_payload() if payload is None else payload,
        context=valid_context() if context is None else context,
        policy=passing_policy() if policy is None else policy,
        execution_state=execution_state,
        decided_at=decided_at,
    )


class OOSValidationTests(unittest.TestCase):
    def test_canonical_pass_from_explicit_oos_bindings_and_thresholds(self) -> None:
        decision = evaluate(payload=ContractObject(backtest_payload()))

        self.assertEqual(decision.decision, "PASS")
        self.assertEqual(decision.reason_codes, ("OOS_POLICY_CRITERIA_PASSED",))
        contract = decision.to_contract()
        self.assertEqual(contract["strategy_id"], subject().strategy_id)
        self.assertEqual(contract["strategy_version"], subject().strategy_version)
        self.assertEqual(contract["backtest_result_id"], subject().backtest_result_id)
        self.assertEqual(contract["validation_policy_version"], passing_policy().version)
        self.assertEqual(contract["policy_thresholds"]["min_total_trades"], 10)
        self.assertEqual(contract["oos_binding"]["split_id"], "split-2026-h1-v1")

    def test_quantitative_fail_reason_codes_have_stable_order(self) -> None:
        payload = backtest_payload(
            total_trades=5,
            wins=1,
            losses=4,
            breakeven=0,
            net_pnl="-1",
            profit_factor="0.8",
            max_drawdown="30",
            max_consecutive_losses=4,
        )
        decision = evaluate(payload=payload)

        self.assertEqual(decision.decision, "FAIL")
        self.assertEqual(
            decision.reason_codes,
            (
                "MIN_TOTAL_TRADES_NOT_MET",
                "MIN_NET_PNL_NOT_MET",
                "MAX_DRAWDOWN_EXCEEDED",
                "MAX_CONSECUTIVE_LOSSES_EXCEEDED",
                "MIN_PROFIT_FACTOR_NOT_MET",
            ),
        )

    def test_impossible_consecutive_loss_count_is_blocked(self) -> None:
        payload = backtest_payload(
            total_trades=5,
            wins=2,
            losses=3,
            breakeven=0,
            max_consecutive_losses=4,
        )
        decision = evaluate(payload=payload)

        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(
            decision.reason_codes,
            ("BACKTEST_TRADE_COUNTS_INCONSISTENT",),
        )

    def test_missing_oos_context_is_blocked(self) -> None:
        decision = evaluate_oos_validation(
            subject=subject(),
            backtest_result=backtest_payload(),
            context=None,
            policy=passing_policy(),
            execution_state=EXECUTION_EXECUTED,
            decided_at="2026-08-22T12:30:00Z",
        )
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(decision.reason_codes, ("OOS_CONTEXT_MISSING",))

    def test_training_oos_identity_collision_is_blocked(self) -> None:
        context = valid_context(
            training_dataset_id="dataset-oos-2026q2",
            training_dataset_hash="sha256:oos-2026q2",
        )
        decision = evaluate(context=context)
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(
            decision.reason_codes,
            ("TRAIN_OOS_DATASET_ID_COLLISION", "TRAIN_OOS_DATASET_HASH_COLLISION"),
        )

    def test_backtest_oos_dataset_mismatch_is_blocked(self) -> None:
        context = valid_context(oos_dataset_hash="sha256:different-oos")
        decision = evaluate(context=context)
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(decision.reason_codes, ("OOS_BACKTEST_DATASET_HASH_MISMATCH",))

    def test_explicit_not_run_state_cannot_become_pass(self) -> None:
        decision = evaluate(execution_state=EXECUTION_NOT_RUN)
        self.assertEqual(decision.decision, "NOT_RUN")
        self.assertEqual(decision.reason_codes, ("EXECUTION_NOT_RUN",))

    def test_unsupported_schema_and_invalid_type_fail_closed(self) -> None:
        unsupported = evaluate(payload=backtest_payload(schema_version="contracts-v9"))
        self.assertEqual(unsupported.decision, "BLOCKED")
        self.assertEqual(unsupported.reason_codes, ("BACKTEST_SCHEMA_UNSUPPORTED",))

        invalid_type = evaluate(payload=object())
        self.assertEqual(invalid_type.decision, "BLOCKED")
        self.assertEqual(invalid_type.reason_codes, ("BACKTEST_RESULT_TYPE_INVALID",))

    def test_binary_float_financial_value_is_blocked_not_coerced(self) -> None:
        decision = evaluate(payload=backtest_payload(net_pnl=100.0))
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(decision.reason_codes, ("BACKTEST_DECIMAL_INVALID",))

    def test_strategy_and_backtest_identity_binding_mismatch_is_blocked(self) -> None:
        decision = evaluate(payload=backtest_payload(strategy_id="different-strategy"))
        self.assertEqual(decision.decision, "BLOCKED")
        self.assertEqual(decision.reason_codes, ("BACKTEST_STRATEGY_ID_MISMATCH",))
        self.assertEqual(decision.to_contract()["strategy_id"], subject().strategy_id)

    def test_profit_factor_null_cannot_pass_when_threshold_configured(self) -> None:
        decision = evaluate(payload=backtest_payload(profit_factor=None))
        self.assertEqual(decision.decision, "FAIL")
        self.assertEqual(decision.reason_codes, ("PROFIT_FACTOR_REQUIRED_BUT_NULL",))

    def test_identical_authority_inputs_keep_identity_when_decided_at_changes(self) -> None:
        first = evaluate(decided_at="2026-08-22T12:30:00Z")
        second = evaluate(decided_at="2026-08-22T13:30:00Z")
        self.assertEqual(first.validation_decision_id, second.validation_decision_id)
        self.assertNotEqual(first.to_contract()["decided_at"], second.to_contract()["decided_at"])

    def test_emitted_payload_is_accepted_by_e6_contract_validator(self) -> None:
        contract = evaluate().to_contract()
        view = validate_validation_decision_contract(contract)
        self.assertEqual(view.validation_decision_id, contract["validation_decision_id"])
        self.assertEqual(view.strategy_id, contract["strategy_id"])
        self.assertEqual(view.strategy_version, contract["strategy_version"])
        self.assertEqual(view.backtest_result_id, contract["backtest_result_id"])
        self.assertEqual(view.decision, "PASS")

    def test_construction_has_no_registry_or_lifecycle_authority(self) -> None:
        contract = evaluate().to_contract()
        for forbidden in (
            "lifecycle_state",
            "registry_transition",
            "promotion",
            "operational_mode",
            "paper",
            "shadow",
            "live",
        ):
            self.assertNotIn(forbidden, contract)

    def test_policy_threshold_change_changes_policy_and_decision_identity(self) -> None:
        first = evaluate(policy=passing_policy(min_net_pnl=Decimal("0")))
        second = evaluate(policy=passing_policy(min_net_pnl=Decimal("1")))
        self.assertNotEqual(first.validation_policy_id, second.validation_policy_id)
        self.assertNotEqual(first.validation_decision_id, second.validation_decision_id)


if __name__ == "__main__":
    unittest.main()
