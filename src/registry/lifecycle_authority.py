from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from .contract_validation import (
    validate_backtest_result_contract,
    validate_validation_decision_contract,
)
from .models import (
    EvidenceGateError,
    LifecycleTransitionRecord,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
)

if TYPE_CHECKING:
    from .ports import RegistryStore


def require_local_execution_pass(
    *,
    status: str,
    verification_kind: str,
    source_revision: str | None,
    environment: str | None,
    command: str | None,
    result_ref: str | None,
    subject: str,
) -> None:
    if status != "PASS" or verification_kind != "LOCAL_EXECUTION":
        raise EvidenceGateError(f"{subject} requires verified LOCAL_EXECUTION PASS evidence")
    required = {
        "source_revision": source_revision,
        "environment": environment,
        "command": command,
        "result_ref": result_ref,
    }
    missing = [name for name, value in required.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        raise EvidenceGateError(
            f"{subject} local PASS evidence missing metadata: {', '.join(missing)}"
        )


def require_backtesting_authority(store: RegistryStore, strategy: StrategyVersionRecord) -> None:
    compatibility = store.latest_compatibility(strategy.identity)
    if compatibility is None:
        raise EvidenceGateError("DRAFT -> BACKTESTING requires durable E2 compatibility evidence")
    if compatibility.identity != strategy.identity:
        raise EvidenceGateError("E2 compatibility evidence is bound to a different strategy version")
    if not compatibility.checker.startswith("E2"):
        raise EvidenceGateError("compatibility evidence is not from the E2 boundary")
    require_local_execution_pass(
        status=compatibility.status,
        verification_kind=compatibility.verification_kind,
        source_revision=compatibility.source_revision,
        environment=compatibility.environment,
        command=compatibility.command,
        result_ref=compatibility.result_ref,
        subject="DRAFT -> BACKTESTING",
    )


def _decode_payload(record: ValidationEvidenceRecord, object_name: str) -> Mapping[str, object]:
    try:
        payload = json.loads(record.payload_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise EvidenceGateError(f"stored {object_name} payload_json is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise EvidenceGateError(f"stored {object_name} payload_json must decode to an object")
    return payload


def _require_evidence_bound_to_strategy(
    evidence: ValidationEvidenceRecord,
    strategy: StrategyVersionRecord,
    *,
    subject: str,
) -> None:
    if evidence.identity != strategy.identity:
        raise EvidenceGateError(f"{subject} is bound to a different strategy version")
    if evidence.strategy_content_hash != strategy.content_hash:
        raise EvidenceGateError(f"{subject} is bound to a different strategy content hash")


def require_candidate_authority(
    store: RegistryStore,
    strategy: StrategyVersionRecord,
    primary_evidence_id: str | None,
) -> tuple[ValidationEvidenceRecord, ValidationEvidenceRecord]:
    if not isinstance(primary_evidence_id, str) or not primary_evidence_id.strip():
        raise EvidenceGateError("BACKTESTING -> CANDIDATE requires authoritative ValidationDecision evidence")

    decision = store.get_validation_evidence(primary_evidence_id)
    if decision is None or decision.evidence_type != "VALIDATION_DECISION":
        raise EvidenceGateError("CANDIDATE requires stored E3 ValidationDecision evidence")
    if decision.producer != "E3" or decision.decision != "PASS":
        raise EvidenceGateError("CANDIDATE requires E3 ValidationDecision.decision=PASS")
    _require_evidence_bound_to_strategy(decision, strategy, subject="ValidationDecision")
    require_local_execution_pass(
        status=decision.verification_status,
        verification_kind=decision.verification_kind,
        source_revision=decision.source_revision,
        environment=decision.environment,
        command=decision.command,
        result_ref=decision.result_ref,
        subject="BACKTESTING -> CANDIDATE ValidationDecision",
    )

    decision_payload = _decode_payload(decision, "ValidationDecision")
    decision_view = validate_validation_decision_contract(decision_payload)
    if decision.upstream_object_id != decision_view.validation_decision_id:
        raise EvidenceGateError("stored ValidationDecision id does not match canonical payload")
    if decision.upstream_schema_version != decision_view.schema_version:
        raise EvidenceGateError("stored ValidationDecision schema does not match canonical payload")
    if (
        decision_view.strategy_id != strategy.identity.strategy_id
        or decision_view.strategy_version != strategy.identity.strategy_version
    ):
        raise EvidenceGateError("canonical ValidationDecision is bound to a different strategy version")
    if decision_view.decision != "PASS" or decision_view.decision != decision.decision:
        raise EvidenceGateError("stored ValidationDecision decision does not match canonical payload")

    if not isinstance(decision.parent_evidence_id, str) or not decision.parent_evidence_id.strip():
        raise EvidenceGateError("ValidationDecision has no BacktestResult parent")
    backtest = store.get_validation_evidence(decision.parent_evidence_id)
    if backtest is None or backtest.evidence_type != "BACKTEST_RESULT":
        raise EvidenceGateError("ValidationDecision BacktestResult parent is missing")
    if backtest.producer != "E3":
        raise EvidenceGateError("ValidationDecision parent is not an E3 BacktestResult")
    _require_evidence_bound_to_strategy(backtest, strategy, subject="BacktestResult")
    require_local_execution_pass(
        status=backtest.verification_status,
        verification_kind=backtest.verification_kind,
        source_revision=backtest.source_revision,
        environment=backtest.environment,
        command=backtest.command,
        result_ref=backtest.result_ref,
        subject="BACKTESTING -> CANDIDATE BacktestResult",
    )

    backtest_payload = _decode_payload(backtest, "BacktestResult")
    backtest_view = validate_backtest_result_contract(backtest_payload)
    if backtest.upstream_object_id != backtest_view.backtest_result_id:
        raise EvidenceGateError("stored BacktestResult id does not match canonical payload")
    if backtest.upstream_schema_version != backtest_view.schema_version:
        raise EvidenceGateError("stored BacktestResult schema does not match canonical payload")
    if (
        backtest_view.strategy_id != strategy.identity.strategy_id
        or backtest_view.strategy_version != strategy.identity.strategy_version
        or backtest_view.strategy_content_hash != strategy.content_hash
    ):
        raise EvidenceGateError("canonical BacktestResult is bound to a different strategy version/content")
    if decision_view.backtest_result_id != backtest_view.backtest_result_id:
        raise EvidenceGateError("ValidationDecision references a different canonical BacktestResult")

    return decision, backtest


def require_rejection_authority(
    store: RegistryStore,
    strategy: StrategyVersionRecord,
    *,
    reason_codes: Sequence[str],
    primary_evidence_id: str | None,
) -> None:
    reasons = tuple(reason for reason in reason_codes if isinstance(reason, str) and reason.strip())
    if not reasons:
        raise EvidenceGateError("REJECTED requires at least one reason code")
    if primary_evidence_id is None:
        return
    evidence = store.get_validation_evidence(primary_evidence_id)
    if evidence is None:
        raise EvidenceGateError("rejection evidence does not exist")
    _require_evidence_bound_to_strategy(evidence, strategy, subject="rejection evidence")


def require_transition_authority(
    store: RegistryStore,
    strategy: StrategyVersionRecord,
    transition: LifecycleTransitionRecord,
) -> None:
    edge = (transition.previous_state, transition.new_state)
    if edge == ("DRAFT", "BACKTESTING"):
        require_backtesting_authority(store, strategy)
        return
    if edge == ("BACKTESTING", "CANDIDATE"):
        require_candidate_authority(store, strategy, transition.primary_evidence_id)
        return
    if edge == ("BACKTESTING", "REJECTED"):
        require_rejection_authority(
            store,
            strategy,
            reason_codes=transition.reason_codes,
            primary_evidence_id=transition.primary_evidence_id,
        )
        return
    raise EvidenceGateError(
        f"no persistence authority policy exists for lifecycle transition {edge[0]} -> {edge[1]}"
    )
