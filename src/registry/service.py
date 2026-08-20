from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract_validation import (
    validate_backtest_result_contract,
    validate_validation_decision_contract,
    validate_verification_metadata,
)
from .models import ValidationEvidenceRecord
from .service_base import DeferredCompatibilityBoundary
from .service_base import StrategyPlatformService as _StrategyPlatformServiceBase


class StrategyPlatformService(_StrategyPlatformServiceBase):
    """Public E6 platform service with fail-closed shared-evidence contract gates.

    The underlying early Slice 2 lifecycle implementation is preserved unchanged.
    This wrapper only strengthens the E3 evidence-ingest boundary: a caller cannot
    turn an incomplete/non-canonical shared object into promotable evidence merely
    by supplying PASS/LOCAL_EXECUTION metadata.
    """

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
