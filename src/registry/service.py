from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contract_validation import (
    validate_backtest_result_contract,
    validate_validation_decision_contract,
    validate_verification_metadata,
)
from .lifecycle_authority import (
    require_backtesting_authority,
    require_candidate_authority,
    require_rejection_authority,
)
from .models import StrategyIdentity, StrategyVersionRecord, ValidationEvidenceRecord
from .service_base import DeferredCompatibilityBoundary
from .service_base import StrategyPlatformService as _StrategyPlatformServiceBase


class StrategyPlatformService(_StrategyPlatformServiceBase):
    """Public E6 platform service with fail-closed evidence and lifecycle authority gates."""

    def record_backtest_result(
        self,
        payload: Mapping[str, Any],
        *,
        verification_status: str = "NOT_RUN",
        verification_kind: str = "NOT_RUN",
        source_revision: str | None = None,
        environment: str | None = None,
        command: str | None = None,
        result_ref: str | None = None,
    ) -> ValidationEvidenceRecord:
        validate_backtest_result_contract(payload)
        validate_verification_metadata(
            status=verification_status,
            verification_kind=verification_kind,
        )
        return super().record_backtest_result(
            payload,
            verification_status=verification_status,
            verification_kind=verification_kind,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )

    def record_validation_decision(
        self,
        payload: Mapping[str, Any],
        *,
        backtest_evidence_id: str,
        verification_status: str = "NOT_RUN",
        verification_kind: str = "NOT_RUN",
        source_revision: str | None = None,
        environment: str | None = None,
        command: str | None = None,
        result_ref: str | None = None,
    ) -> ValidationEvidenceRecord:
        validate_validation_decision_contract(payload)
        validate_verification_metadata(
            status=verification_status,
            verification_kind=verification_kind,
        )
        return super().record_validation_decision(
            payload,
            backtest_evidence_id=backtest_evidence_id,
            verification_status=verification_status,
            verification_kind=verification_kind,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )

    def begin_backtesting(self, identity: StrategyIdentity, *, actor: str) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "DRAFT":
            require_backtesting_authority(self._store, strategy)
        return super().begin_backtesting(identity, actor=actor)

    def mark_candidate(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        validation_evidence_id: str,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "BACKTESTING":
            require_candidate_authority(self._store, strategy, validation_evidence_id)
        return super().mark_candidate(
            identity,
            actor=actor,
            validation_evidence_id=validation_evidence_id,
        )

    def reject_from_backtesting(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        reason_codes: Sequence[str],
        evidence_id: str | None = None,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "BACKTESTING":
            require_rejection_authority(
                self._store,
                strategy,
                reason_codes=reason_codes,
                primary_evidence_id=evidence_id,
            )
        return super().reject_from_backtesting(
            identity,
            actor=actor,
            reason_codes=reason_codes,
            evidence_id=evidence_id,
        )
