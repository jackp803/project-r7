from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from .models import (
    CompatibilityEvidence,
    EVIDENCE_STATUSES,
    EvidenceGateError,
    IntakeOutcome,
    IntakeReceipt,
    IntakeRejected,
    InvalidTransition,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyVersionRecord,
    SUPPORTED_SHARED_SCHEMA_VERSION,
    VALIDATION_DECISIONS,
    VERIFICATION_KINDS,
    ValidationEvidenceRecord,
)
from .ports import RegistryStore, StrategyCompatibilityBoundary

_FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "api_secret",
    "token",
    "password",
    "private_key",
    "secret",
    "credential",
    "credentials",
}
_REQUIRED_STRATEGY_FIELDS = {
    "schema_version",
    "strategy_id",
    "strategy_version",
    "name",
    "symbol",
    "required_timeframes",
    "parameters",
    "rules",
    "runtime_compatibility",
    "content_hash",
    "created_at",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntakeRejected(f"{field} must be a non-empty string")
    return value


def _no_duplicate_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IntakeRejected(f"duplicate JSON key is not allowed: {key}")
        result[key] = value
    return result


def _load_payload(payload: Mapping[str, Any] | str | bytes | bytearray) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return dict(payload)
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IntakeRejected("StrategyDefinition payload must be UTF-8") from exc
    if not isinstance(payload, str):
        raise IntakeRejected("StrategyDefinition intake accepts a mapping or JSON object")
    try:
        decoded = json.loads(payload, object_pairs_hook=_no_duplicate_object)
    except IntakeRejected:
        raise
    except json.JSONDecodeError as exc:
        raise IntakeRejected("StrategyDefinition payload is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise IntakeRejected("StrategyDefinition JSON root must be an object")
    return decoded


def _looks_secret_like_key(normalized: str) -> bool:
    if normalized in _FORBIDDEN_SECRET_KEYS:
        return True
    return any(normalized.endswith(f"_{suffix}") for suffix in _FORBIDDEN_SECRET_KEYS)


def _scan_secret_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.strip().lower()
            child_path = f"{path}.{key}"
            if _looks_secret_like_key(normalized):
                raise IntakeRejected(
                    f"secret-like field is forbidden in StrategyDefinition intake: {child_path}"
                )
            _scan_secret_keys(item, child_path)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_secret_keys(item, f"{path}[{index}]")


def _canonical_json(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise IntakeRejected("StrategyDefinition must be deterministically JSON serializable") from exc


def _validate_strategy_envelope(raw: Mapping[str, Any]) -> tuple[StrategyIdentity, Mapping[str, Any]]:
    missing = sorted(_REQUIRED_STRATEGY_FIELDS - set(raw.keys()))
    if missing:
        raise IntakeRejected(f"StrategyDefinition missing required fields: {', '.join(missing)}")
    schema_version = _nonempty(raw["schema_version"], "schema_version")
    if schema_version != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise IntakeRejected(
            f"unsupported StrategyDefinition schema_version={schema_version}; "
            f"expected {SUPPORTED_SHARED_SCHEMA_VERSION}"
        )
    identity = StrategyIdentity(
        _nonempty(raw["strategy_id"], "strategy_id"),
        _nonempty(raw["strategy_version"], "strategy_version"),
    )
    _nonempty(raw["name"], "name")
    _nonempty(raw["symbol"], "symbol")
    _nonempty(raw["content_hash"], "content_hash")
    _nonempty(raw["created_at"], "created_at")
    runtime = raw["runtime_compatibility"]
    if not isinstance(runtime, Mapping):
        raise IntakeRejected("runtime_compatibility must be an object")
    _nonempty(runtime.get("runtime_family"), "runtime_compatibility.runtime_family")
    _nonempty(runtime.get("runtime_version"), "runtime_compatibility.runtime_version")
    return identity, runtime


def _payload_hash(canonical_json: str) -> str:
    return f"sha256:{hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()}"


def _require_local_pass_metadata(
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
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise EvidenceGateError(
            f"{subject} local PASS evidence missing metadata: {', '.join(missing)}"
        )


class DeferredCompatibilityBoundary:
    """Fail-closed compatibility boundary used until the actual E2 adapter is wired."""

    def check(self, strategy_definition: Mapping[str, Any]) -> CompatibilityEvidence:
        identity, _ = _validate_strategy_envelope(strategy_definition)
        return CompatibilityEvidence(
            compatibility_id=_new_id("compat"),
            identity=identity,
            status="NOT_RUN",
            verification_kind="NOT_RUN",
            checker="E2_RUNTIME_NOT_WIRED",
            checked_at=_utc_now(),
            reason_codes=("E2_COMPATIBILITY_NOT_EXECUTED",),
            details={"schema_envelope": "accepted", "runtime_check": "NOT_RUN"},
        )


class StrategyPlatformService:
    """Early Slice 2 E6 service.

    This service intentionally exposes no CANDIDATE -> PAPER/APPROVED/LIVE method.
    Structural validity never becomes promotion authority.
    """

    def __init__(
        self,
        store: RegistryStore,
        compatibility_boundary: StrategyCompatibilityBoundary | None = None,
    ) -> None:
        self._store = store
        self._compatibility = compatibility_boundary or DeferredCompatibilityBoundary()

    def intake(
        self,
        payload: Mapping[str, Any] | str | bytes | bytearray,
        *,
        source_actor: str,
    ) -> IntakeOutcome:
        actor = _nonempty(source_actor, "source_actor")
        raw = _load_payload(payload)
        _scan_secret_keys(raw)
        identity, runtime = _validate_strategy_envelope(raw)
        canonical = _canonical_json(raw)
        registered_at = _utc_now()
        proposed = StrategyVersionRecord(
            identity=identity,
            strategy_schema_version=str(raw["schema_version"]),
            content_hash=str(raw["content_hash"]),
            name=str(raw["name"]),
            symbol=str(raw["symbol"]),
            declared_runtime_family=str(runtime["runtime_family"]),
            declared_runtime_version=str(runtime["runtime_version"]),
            definition_json=canonical,
            upstream_created_at=str(raw["created_at"]),
            registered_at=registered_at,
        )
        stored, created = self._store.register_strategy(proposed)

        compatibility = self._compatibility.check(raw)
        if compatibility.identity != identity:
            raise EvidenceGateError("E2 compatibility evidence identity does not match intake identity")
        if compatibility.status not in EVIDENCE_STATUSES:
            raise EvidenceGateError("E2 compatibility evidence has unsupported status")
        if compatibility.verification_kind not in VERIFICATION_KINDS:
            raise EvidenceGateError("E2 compatibility evidence has unsupported verification_kind")
        self._store.save_compatibility(compatibility)

        status_map = {
            "PASS": "REGISTERED" if created else "IDEMPOTENT",
            "FAIL": "COMPATIBILITY_FAIL",
            "BLOCKED": "COMPATIBILITY_BLOCKED",
            "NOT_RUN": "COMPATIBILITY_NOT_RUN",
            "NOT_APPLICABLE": "COMPATIBILITY_BLOCKED",
        }
        receipt = IntakeReceipt(
            intake_id=_new_id("intake"),
            identity=identity,
            payload_hash=_payload_hash(canonical),
            received_at=registered_at,
            source_actor=actor,
            result_status=status_map[compatibility.status],
            compatibility_id=compatibility.compatibility_id,
        )
        self._store.save_intake_receipt(receipt)
        return IntakeOutcome(stored, receipt, compatibility)

    def begin_backtesting(self, identity: StrategyIdentity, *, actor: str) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state != "DRAFT":
            raise InvalidTransition("begin_backtesting requires DRAFT")
        compatibility = self._store.latest_compatibility(identity)
        if compatibility is None:
            raise EvidenceGateError("no E2 compatibility evidence is recorded")
        if not compatibility.checker.startswith("E2"):
            raise EvidenceGateError("compatibility evidence is not from the E2 boundary")
        _require_local_pass_metadata(
            status=compatibility.status,
            verification_kind=compatibility.verification_kind,
            source_revision=compatibility.source_revision,
            environment=compatibility.environment,
            command=compatibility.command,
            result_ref=compatibility.result_ref,
            subject="DRAFT -> BACKTESTING",
        )
        return self._transition(
            strategy,
            "BACKTESTING",
            actor=actor,
            reason_codes=("E2_COMPATIBILITY_VERIFIED",),
            primary_evidence_id=None,
        )

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
        schema = _nonempty(payload.get("schema_version"), "BacktestResult.schema_version")
        if schema != SUPPORTED_SHARED_SCHEMA_VERSION:
            raise EvidenceGateError("unsupported BacktestResult schema_version")
        identity = StrategyIdentity(
            _nonempty(payload.get("strategy_id"), "BacktestResult.strategy_id"),
            _nonempty(payload.get("strategy_version"), "BacktestResult.strategy_version"),
        )
        strategy = self._require_strategy(identity)
        strategy_hash = _nonempty(
            payload.get("strategy_content_hash"), "BacktestResult.strategy_content_hash"
        )
        if strategy_hash != strategy.content_hash:
            raise EvidenceGateError("BacktestResult is bound to a different strategy content hash")
        upstream_id = _nonempty(
            payload.get("backtest_result_id"), "BacktestResult.backtest_result_id"
        )
        record = ValidationEvidenceRecord(
            evidence_id=_new_id("evidence"),
            evidence_type="BACKTEST_RESULT",
            upstream_object_id=upstream_id,
            identity=identity,
            strategy_content_hash=strategy_hash,
            upstream_schema_version=schema,
            producer="E3",
            payload_json=_canonical_json(payload),
            recorded_at=_utc_now(),
            verification_status=verification_status,
            verification_kind=verification_kind,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )
        self._store.save_validation_evidence(record)
        return record

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
        schema = _nonempty(payload.get("schema_version"), "ValidationDecision.schema_version")
        if schema != SUPPORTED_SHARED_SCHEMA_VERSION:
            raise EvidenceGateError("unsupported ValidationDecision schema_version")
        decision = _nonempty(payload.get("decision"), "ValidationDecision.decision")
        if decision not in VALIDATION_DECISIONS:
            raise EvidenceGateError("unsupported ValidationDecision.decision")
        identity = StrategyIdentity(
            _nonempty(payload.get("strategy_id"), "ValidationDecision.strategy_id"),
            _nonempty(payload.get("strategy_version"), "ValidationDecision.strategy_version"),
        )
        strategy = self._require_strategy(identity)
        parent = self._store.get_validation_evidence(backtest_evidence_id)
        if parent is None or parent.evidence_type != "BACKTEST_RESULT":
            raise EvidenceGateError("ValidationDecision requires a stored BacktestResult parent")
        if parent.identity != identity or parent.strategy_content_hash != strategy.content_hash:
            raise EvidenceGateError("ValidationDecision parent is bound to a different strategy version")
        referenced_backtest_id = _nonempty(
            payload.get("backtest_result_id"), "ValidationDecision.backtest_result_id"
        )
        if parent.upstream_object_id != referenced_backtest_id:
            raise EvidenceGateError("ValidationDecision references a different BacktestResult")
        upstream_id = _nonempty(
            payload.get("validation_decision_id"), "ValidationDecision.validation_decision_id"
        )
        record = ValidationEvidenceRecord(
            evidence_id=_new_id("evidence"),
            evidence_type="VALIDATION_DECISION",
            upstream_object_id=upstream_id,
            identity=identity,
            strategy_content_hash=strategy.content_hash,
            upstream_schema_version=schema,
            producer="E3",
            payload_json=_canonical_json(payload),
            recorded_at=_utc_now(),
            verification_status=verification_status,
            verification_kind=verification_kind,
            decision=decision,
            parent_evidence_id=parent.evidence_id,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )
        self._store.save_validation_evidence(record)
        return record

    def reject_from_backtesting(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        reason_codes: Sequence[str],
        evidence_id: str | None = None,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state != "BACKTESTING":
            raise InvalidTransition("rejection in this slice requires BACKTESTING")
        reasons = tuple(str(reason) for reason in reason_codes if str(reason))
        if not reasons:
            raise EvidenceGateError("REJECTED requires at least one reason code")
        if evidence_id is not None:
            evidence = self._store.get_validation_evidence(evidence_id)
            if evidence is None or evidence.identity != identity:
                raise EvidenceGateError("rejection evidence is not bound to this strategy version")
        return self._transition(
            strategy,
            "REJECTED",
            actor=actor,
            reason_codes=reasons,
            primary_evidence_id=evidence_id,
        )

    def mark_candidate(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        validation_evidence_id: str,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state != "BACKTESTING":
            raise InvalidTransition("CANDIDATE in this slice requires BACKTESTING")
        decision = self._store.get_validation_evidence(validation_evidence_id)
        if decision is None or decision.evidence_type != "VALIDATION_DECISION":
            raise EvidenceGateError("CANDIDATE requires stored E3 ValidationDecision evidence")
        if decision.identity != identity or decision.strategy_content_hash != strategy.content_hash:
            raise EvidenceGateError("ValidationDecision is not bound to this strategy version")
        if decision.producer != "E3" or decision.decision != "PASS":
            raise EvidenceGateError("CANDIDATE requires E3 ValidationDecision.decision=PASS")
        _require_local_pass_metadata(
            status=decision.verification_status,
            verification_kind=decision.verification_kind,
            source_revision=decision.source_revision,
            environment=decision.environment,
            command=decision.command,
            result_ref=decision.result_ref,
            subject="BACKTESTING -> CANDIDATE ValidationDecision",
        )
        if decision.parent_evidence_id is None:
            raise EvidenceGateError("ValidationDecision has no BacktestResult parent")
        backtest = self._store.get_validation_evidence(decision.parent_evidence_id)
        if backtest is None or backtest.evidence_type != "BACKTEST_RESULT":
            raise EvidenceGateError("ValidationDecision BacktestResult parent is missing")
        _require_local_pass_metadata(
            status=backtest.verification_status,
            verification_kind=backtest.verification_kind,
            source_revision=backtest.source_revision,
            environment=backtest.environment,
            command=backtest.command,
            result_ref=backtest.result_ref,
            subject="BACKTESTING -> CANDIDATE BacktestResult",
        )
        return self._transition(
            strategy,
            "CANDIDATE",
            actor=actor,
            reason_codes=("E3_VALIDATION_LOCAL_PASS",),
            primary_evidence_id=decision.evidence_id,
        )

    def _require_strategy(self, identity: StrategyIdentity) -> StrategyVersionRecord:
        strategy = self._store.get_strategy(identity)
        if strategy is None:
            raise EvidenceGateError("strategy version is not registered")
        return strategy

    def _transition(
        self,
        strategy: StrategyVersionRecord,
        new_state: str,
        *,
        actor: str,
        reason_codes: tuple[str, ...],
        primary_evidence_id: str | None,
    ) -> StrategyVersionRecord:
        allowed = {
            ("DRAFT", "BACKTESTING"),
            ("BACKTESTING", "REJECTED"),
            ("BACKTESTING", "CANDIDATE"),
        }
        edge = (strategy.current_lifecycle_state, new_state)
        if edge not in allowed:
            raise InvalidTransition(
                f"early Slice 2 service does not expose lifecycle transition {edge[0]} -> {edge[1]}"
            )
        changed_by = _nonempty(actor, "actor")
        transition = LifecycleTransitionRecord(
            transition_id=_new_id("transition"),
            identity=strategy.identity,
            previous_state=strategy.current_lifecycle_state,
            new_state=new_state,
            changed_at=_utc_now(),
            changed_by=changed_by,
            reason_codes=reason_codes,
            primary_evidence_id=primary_evidence_id,
            expected_registry_revision=strategy.registry_revision,
            resulting_registry_revision=strategy.registry_revision + 1,
        )
        return self._store.append_transition(transition)
