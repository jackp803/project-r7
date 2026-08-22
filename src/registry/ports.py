from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence

from .models import (
    CompatibilityEvidence,
    IntakeReceipt,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
)


class StrategyCompatibilityBoundary(Protocol):
    """Adapter boundary to the authoritative E2 compatibility validator/runtime.

    E6 must not implement Strategy DSL/runtime semantics behind this interface.
    """

    def check(self, strategy_definition: Mapping[str, Any]) -> CompatibilityEvidence:
        ...


class RegistryStore(Protocol):
    def register_strategy(self, record: StrategyVersionRecord) -> tuple[StrategyVersionRecord, bool]:
        """Return (stored_record, created). Conflicting content for the same identity must fail."""
        ...

    def get_strategy(self, identity: StrategyIdentity) -> StrategyVersionRecord | None:
        ...

    def list_versions(self, strategy_id: str) -> Sequence[StrategyVersionRecord]:
        ...

    def save_compatibility(self, evidence: CompatibilityEvidence) -> None:
        ...

    def latest_compatibility(self, identity: StrategyIdentity) -> CompatibilityEvidence | None:
        ...

    def save_intake_receipt(self, receipt: IntakeReceipt) -> None:
        ...

    def save_validation_evidence(self, evidence: ValidationEvidenceRecord) -> None:
        ...

    def get_validation_evidence(self, evidence_id: str) -> ValidationEvidenceRecord | None:
        ...

    def find_validation_decisions(self, identity: StrategyIdentity) -> Sequence[ValidationEvidenceRecord]:
        ...

    def append_transition(
        self,
        transition: LifecycleTransitionRecord,
    ) -> StrategyVersionRecord:
        """Append audit event and update current-state projection atomically."""
        ...
