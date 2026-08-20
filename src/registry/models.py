from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

SUPPORTED_SHARED_SCHEMA_VERSION = "contracts-v0.1"
EARLY_LIFECYCLE_STATES = ("DRAFT", "BACKTESTING", "REJECTED", "CANDIDATE")
EVIDENCE_STATUSES = ("PASS", "FAIL", "BLOCKED", "NOT_RUN", "NOT_APPLICABLE")
VERIFICATION_KINDS = ("LOCAL_EXECUTION", "STATIC_REVIEW", "DECLARATION", "NOT_RUN")
VALIDATION_DECISIONS = ("PASS", "FAIL", "BLOCKED", "NOT_RUN")


class RegistryError(RuntimeError):
    """Base E6 registry/platform error."""


class IntakeRejected(RegistryError):
    pass


class IdentityConflict(RegistryError):
    pass


class InvalidTransition(RegistryError):
    pass


class EvidenceGateError(RegistryError):
    pass


class ConcurrencyConflict(RegistryError):
    pass


@dataclass(frozen=True)
class StrategyIdentity:
    strategy_id: str
    strategy_version: str


@dataclass(frozen=True)
class StrategyVersionRecord:
    identity: StrategyIdentity
    strategy_schema_version: str
    content_hash: str
    name: str
    symbol: str
    declared_runtime_family: str
    declared_runtime_version: str
    definition_json: str
    upstream_created_at: str
    registered_at: str
    current_lifecycle_state: str = "DRAFT"
    registry_revision: int = 0


@dataclass(frozen=True)
class CompatibilityEvidence:
    compatibility_id: str
    identity: StrategyIdentity
    status: str
    verification_kind: str
    checker: str
    checked_at: str
    reason_codes: Tuple[str, ...]
    details: Mapping[str, Any]
    source_revision: str | None = None
    environment: str | None = None
    command: str | None = None
    result_ref: str | None = None


@dataclass(frozen=True)
class ValidationEvidenceRecord:
    evidence_id: str
    evidence_type: str
    upstream_object_id: str
    identity: StrategyIdentity
    strategy_content_hash: str
    upstream_schema_version: str
    producer: str
    payload_json: str
    recorded_at: str
    verification_status: str
    verification_kind: str
    decision: str | None = None
    parent_evidence_id: str | None = None
    source_revision: str | None = None
    environment: str | None = None
    command: str | None = None
    result_ref: str | None = None


@dataclass(frozen=True)
class IntakeReceipt:
    intake_id: str
    identity: StrategyIdentity
    payload_hash: str
    received_at: str
    source_actor: str
    result_status: str
    compatibility_id: str | None = None


@dataclass(frozen=True)
class LifecycleTransitionRecord:
    transition_id: str
    identity: StrategyIdentity
    previous_state: str
    new_state: str
    changed_at: str
    changed_by: str
    reason_codes: Tuple[str, ...]
    primary_evidence_id: str | None
    expected_registry_revision: int
    resulting_registry_revision: int


@dataclass(frozen=True)
class IntakeOutcome:
    strategy: StrategyVersionRecord
    receipt: IntakeReceipt
    compatibility: CompatibilityEvidence
