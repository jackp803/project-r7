from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._sqlite_registry import _apply_migrations, _connect

SCHEMA_VERSION = "contracts-v0.1"
OPERATIONAL_MODES = frozenset({"RESEARCH", "PAPER", "SHADOW", "LIVE", "PAUSED", "LOCKED"})
_GATE_C_TRANSITION_TARGETS = frozenset({"SHADOW", "PAUSED", "LOCKED"})

_MODE_AUDIT_FIELDS = frozenset(
    {
        "schema_version",
        "mode",
        "changed_at",
        "changed_by",
        "reason_codes",
        "approval_record_id",
        "previous_mode",
        "mode_revision",
        "evidence_ref",
    }
)
_SHADOW_CHECKPOINT_FIELDS = frozenset(
    {
        "schema_version",
        "provider",
        "environment_classification",
        "regional_hostname_ref",
        "canonical_instrument",
        "provider_instrument",
        "observed_at",
        "permission_category",
        "market_healthy",
        "account_config_known",
        "balance_known",
        "position_truth_known",
        "isolated_leverage_known",
        "unexpected_exposure",
        "pending_order_count",
        "unreconciled_fill_count",
        "provider_observation_ref",
        "provider_observation_hash",
        "reason_codes",
    }
)
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_OBSERVATION_REF_RE = re.compile(r"^r7obs_[A-Za-z0-9._-]{1,120}$")
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class OperationalModeError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class OperationalModeValidationError(OperationalModeError):
    pass


class OperationalModeAuthorityError(OperationalModeError):
    pass


class OperationalModeConflictError(OperationalModeError):
    pass


@dataclass(frozen=True)
class OperationalModeRecord:
    transition_id: str
    mode_revision: int
    schema_version: str
    previous_mode: str | None
    mode: str
    changed_at: str
    changed_by: str
    reason_codes: tuple[str, ...]
    approval_record_id: str | None
    evidence_ref: str
    payload_hash: str


@dataclass(frozen=True)
class ShadowCheckpoint:
    checkpoint_id: str
    checkpoint_revision: int
    mode_revision: int
    observed_at: str
    provider_observation_ref: str
    payload_json: str
    payload_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise OperationalModeValidationError(
                "SHADOW_CHECKPOINT_PAYLOAD_NOT_OBJECT",
                "stored Shadow checkpoint payload is not a JSON object",
            )
        return value


@dataclass(frozen=True)
class OperationalModeRecovery:
    status: str
    reason_codes: tuple[str, ...]
    current_mode: OperationalModeRecord | None
    last_shadow_checkpoint: ShadowCheckpoint | None
    fresh_reconciliation_required: bool
    shadow_planning_safe: bool


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise OperationalModeValidationError(
            "NONCANONICAL_JSON",
            "operational-mode material must be canonical JSON",
        ) from exc


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mode_transition_id(payload_json: str) -> str:
    return "opmode_" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _checkpoint_id(mode_revision: int, payload_json: str) -> str:
    identity = _canonical_json({"mode_revision": mode_revision, "payload_json": payload_json})
    return "shadowcp_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OperationalModeValidationError(
            "INVALID_TIMESTAMP",
            f"{field} must be RFC3339 UTC with Z suffix",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise OperationalModeValidationError(
            "INVALID_TIMESTAMP",
            f"{field} is not valid RFC3339 UTC",
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OperationalModeValidationError(
            "INVALID_TIMESTAMP",
            f"{field} must be UTC",
        )
    return parsed.astimezone(timezone.utc)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise OperationalModeValidationError(
            "INVALID_TEXT_FIELD",
            f"{field} must be a non-empty canonical string",
        )
    return value


def _safe_token(value: Any, field: str) -> str:
    text = _text(value, field)
    if _SAFE_TOKEN_RE.fullmatch(text) is None:
        raise OperationalModeValidationError(
            "UNSAFE_REFERENCE_FIELD",
            f"{field} must be a sanitized identifier/reference token",
        )
    return text


def _reason_codes(value: Any, field: str = "reason_codes") -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise OperationalModeValidationError(
            "INVALID_REASON_CODES",
            f"{field} must be an array",
        )
    result: list[str] = []
    for item in value:
        code = _safe_token(item, f"{field}[]")
        result.append(code)
    if len(result) != len(set(result)):
        raise OperationalModeValidationError(
            "DUPLICATE_REASON_CODES",
            f"{field} must not contain duplicates",
        )
    return tuple(result)


def _mode_payload(
    *,
    mode: str,
    previous_mode: str | None,
    mode_revision: int,
    changed_at: str,
    changed_by: str,
    reason_codes: Sequence[str],
    approval_record_id: str | None,
    evidence_ref: str,
) -> dict[str, Any]:
    if mode not in OPERATIONAL_MODES:
        raise OperationalModeValidationError("UNSUPPORTED_OPERATIONAL_MODE", f"unsupported OperationalMode: {mode}")
    if previous_mode is not None and previous_mode not in OPERATIONAL_MODES:
        raise OperationalModeValidationError("UNSUPPORTED_PREVIOUS_MODE", "previous OperationalMode is unsupported")
    if type(mode_revision) is not int or mode_revision < 0:
        raise OperationalModeValidationError("INVALID_MODE_REVISION", "mode_revision must be a non-negative integer")
    _utc(changed_at, "changed_at")
    actor = _safe_token(changed_by, "changed_by")
    reasons = _reason_codes(reason_codes)
    if not reasons:
        raise OperationalModeValidationError("MODE_REASON_REQUIRED", "mode transition requires at least one reason code")
    approval = None if approval_record_id is None else _safe_token(approval_record_id, "approval_record_id")
    evidence = _safe_token(evidence_ref, "evidence_ref")
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "changed_at": changed_at,
        "changed_by": actor,
        "reason_codes": list(reasons),
        "approval_record_id": approval,
        "previous_mode": previous_mode,
        "mode_revision": mode_revision,
        "evidence_ref": evidence,
    }


def _validate_stored_mode_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _MODE_AUDIT_FIELDS:
        raise OperationalModeValidationError(
            "OPERATIONAL_MODE_AUDIT_FIELDS_INVALID",
            "stored operational-mode audit payload has invalid fields",
        )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise OperationalModeValidationError("UNSUPPORTED_SCHEMA_VERSION", "stored OperationalMode schema is unsupported")
    return _mode_payload(
        mode=value.get("mode"),
        previous_mode=value.get("previous_mode"),
        mode_revision=value.get("mode_revision"),
        changed_at=value.get("changed_at"),
        changed_by=value.get("changed_by"),
        reason_codes=value.get("reason_codes"),
        approval_record_id=value.get("approval_record_id"),
        evidence_ref=value.get("evidence_ref"),
    )


def _validate_shadow_checkpoint_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if set(payload) != _SHADOW_CHECKPOINT_FIELDS:
        missing = sorted(_SHADOW_CHECKPOINT_FIELDS - set(payload))
        extra = sorted(set(payload) - _SHADOW_CHECKPOINT_FIELDS)
        raise OperationalModeValidationError(
            "SHADOW_CHECKPOINT_FIELDS_INVALID",
            f"Shadow checkpoint fields mismatch; missing={missing}, extra={extra}",
        )
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise OperationalModeValidationError("UNSUPPORTED_SCHEMA_VERSION", "Shadow checkpoint schema is unsupported")
    if payload.get("provider") != "OKX":
        raise OperationalModeValidationError("SHADOW_PROVIDER_MISMATCH", "accepted Gate C Shadow provider must be OKX")
    if payload.get("environment_classification") != "PRODUCTION_READ_ONLY_SHADOW":
        raise OperationalModeValidationError(
            "SHADOW_ENVIRONMENT_MISMATCH",
            "accepted Gate C checkpoint must be production read-only Shadow evidence",
        )
    regional_ref = _safe_token(payload.get("regional_hostname_ref"), "regional_hostname_ref")
    if payload.get("canonical_instrument") != "BTC_USDT_PERP" or payload.get("provider_instrument") != "BTC-USDT-SWAP":
        raise OperationalModeValidationError(
            "SHADOW_INSTRUMENT_MISMATCH",
            "accepted Gate C checkpoint must bind BTC_USDT_PERP to BTC-USDT-SWAP",
        )
    observed_at = _text(payload.get("observed_at"), "observed_at")
    _utc(observed_at, "observed_at")
    if payload.get("permission_category") != "read_only":
        raise OperationalModeValidationError(
            "SHADOW_PERMISSION_NOT_READ_ONLY",
            "accepted Gate C checkpoint requires read_only permission category",
        )
    for field in (
        "market_healthy",
        "account_config_known",
        "balance_known",
        "position_truth_known",
        "isolated_leverage_known",
        "unexpected_exposure",
    ):
        if type(payload.get(field)) is not bool:
            raise OperationalModeValidationError("INVALID_SHADOW_BOOLEAN", f"{field} must be boolean")
    if not payload["market_healthy"]:
        raise OperationalModeValidationError("SHADOW_MARKET_NOT_HEALTHY", "accepted checkpoint requires healthy market evidence")
    for field in ("account_config_known", "balance_known", "position_truth_known", "isolated_leverage_known"):
        if not payload[field]:
            raise OperationalModeValidationError("SHADOW_REQUIRED_TRUTH_UNKNOWN", f"accepted checkpoint requires {field}=true")
    if payload["unexpected_exposure"]:
        raise OperationalModeValidationError("SHADOW_UNEXPECTED_EXPOSURE", "unexpected provider exposure cannot be accepted")
    for field in ("pending_order_count", "unreconciled_fill_count"):
        value = payload.get(field)
        if type(value) is not int or value < 0:
            raise OperationalModeValidationError("INVALID_SHADOW_COUNT", f"{field} must be a non-negative integer")
        if value != 0:
            raise OperationalModeValidationError("SHADOW_PROVIDER_ACTIVITY_PRESENT", f"accepted checkpoint requires {field}=0")
    observation_ref = _text(payload.get("provider_observation_ref"), "provider_observation_ref")
    if _OBSERVATION_REF_RE.fullmatch(observation_ref) is None:
        raise OperationalModeValidationError(
            "UNSAFE_PROVIDER_OBSERVATION_REF",
            "provider_observation_ref must be an R7-generated sanitized reference",
        )
    observation_hash = payload.get("provider_observation_hash")
    if not isinstance(observation_hash, str) or _HASH_RE.fullmatch(observation_hash) is None:
        raise OperationalModeValidationError(
            "INVALID_PROVIDER_OBSERVATION_HASH",
            "provider_observation_hash must be sha256:<lowercase hex>",
        )
    reasons = _reason_codes(payload.get("reason_codes"), "reason_codes")
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "OKX",
        "environment_classification": "PRODUCTION_READ_ONLY_SHADOW",
        "regional_hostname_ref": regional_ref,
        "canonical_instrument": "BTC_USDT_PERP",
        "provider_instrument": "BTC-USDT-SWAP",
        "observed_at": observed_at,
        "permission_category": "read_only",
        "market_healthy": True,
        "account_config_known": True,
        "balance_known": True,
        "position_truth_known": True,
        "isolated_leverage_known": True,
        "unexpected_exposure": False,
        "pending_order_count": 0,
        "unreconciled_fill_count": 0,
        "provider_observation_ref": observation_ref,
        "provider_observation_hash": observation_hash,
        "reason_codes": list(reasons),
    }


class OperationalModeStore:
    """E6-authoritative OperationalMode and sanitized Gate C Shadow checkpoint store.

    The supported surface never submits provider requests, never accepts credentials,
    never derives risk state, and never creates a transition into LIVE.
    """

    __slots__ = ("_connection", "_fresh_shadow_checkpoint_id")

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._fresh_shadow_checkpoint_id: str | None = None

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "OperationalModeStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _mode_record_from_row(self, row: sqlite3.Row) -> OperationalModeRecord:
        try:
            value = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise OperationalModeValidationError("OPERATIONAL_MODE_PAYLOAD_INVALID", "stored mode payload is invalid JSON") from exc
        payload = _validate_stored_mode_payload(value)
        payload_json = _canonical_json(payload)
        payload_hash = _sha256_text(payload_json)
        transition_id = _mode_transition_id(payload_json)
        if row["payload_json"] != payload_json or row["payload_hash"] != payload_hash or row["transition_id"] != transition_id:
            raise OperationalModeConflictError(
                "OPERATIONAL_MODE_AUDIT_CORRUPT",
                "stored operational-mode identity/hash does not match canonical audit payload",
            )
        if (
            row["mode_revision"] != payload["mode_revision"]
            or row["schema_version"] != payload["schema_version"]
            or row["previous_mode"] != payload["previous_mode"]
            or row["new_mode"] != payload["mode"]
            or row["changed_at"] != payload["changed_at"]
            or row["changed_by"] != payload["changed_by"]
            or row["reason_codes_json"] != _canonical_json(payload["reason_codes"])
            or row["approval_record_id"] != payload["approval_record_id"]
            or row["evidence_ref"] != payload["evidence_ref"]
        ):
            raise OperationalModeConflictError(
                "OPERATIONAL_MODE_COLUMN_PAYLOAD_CONFLICT",
                "stored operational-mode index columns contradict canonical payload",
            )
        return OperationalModeRecord(
            transition_id=transition_id,
            mode_revision=payload["mode_revision"],
            schema_version=payload["schema_version"],
            previous_mode=payload["previous_mode"],
            mode=payload["mode"],
            changed_at=payload["changed_at"],
            changed_by=payload["changed_by"],
            reason_codes=tuple(payload["reason_codes"]),
            approval_record_id=payload["approval_record_id"],
            evidence_ref=payload["evidence_ref"],
            payload_hash=payload_hash,
        )

    def _validated_mode_history(self) -> tuple[OperationalModeRecord, ...]:
        rows = self._connection.execute(
            "SELECT * FROM operational_mode_transitions ORDER BY mode_revision"
        ).fetchall()
        records = tuple(self._mode_record_from_row(row) for row in rows)
        previous: OperationalModeRecord | None = None
        for expected_revision, record in enumerate(records):
            if record.mode_revision != expected_revision:
                raise OperationalModeConflictError(
                    "OPERATIONAL_MODE_REVISION_GAP",
                    "operational-mode audit revisions are not contiguous",
                )
            if expected_revision == 0:
                if record.previous_mode is not None:
                    raise OperationalModeConflictError(
                        "OPERATIONAL_MODE_GENESIS_CONTRADICTORY",
                        "operational-mode revision 0 must have previous_mode=null",
                    )
            elif previous is None or record.previous_mode != previous.mode:
                raise OperationalModeConflictError(
                    "OPERATIONAL_MODE_PREDECESSOR_CONFLICT",
                    "operational-mode audit predecessor does not match prior mode",
                )
            previous = record
        return records

    def _insert_mode_record(self, payload: Mapping[str, Any]) -> OperationalModeRecord:
        canonical = _validate_stored_mode_payload(dict(payload))
        payload_json = _canonical_json(canonical)
        payload_hash = _sha256_text(payload_json)
        transition_id = _mode_transition_id(payload_json)
        self._connection.execute(
            """
            INSERT INTO operational_mode_transitions (
                transition_id, mode_revision, schema_version, previous_mode, new_mode,
                changed_at, changed_by, reason_codes_json, approval_record_id,
                evidence_ref, payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transition_id,
                canonical["mode_revision"],
                canonical["schema_version"],
                canonical["previous_mode"],
                canonical["mode"],
                canonical["changed_at"],
                canonical["changed_by"],
                _canonical_json(canonical["reason_codes"]),
                canonical["approval_record_id"],
                canonical["evidence_ref"],
                payload_json,
                payload_hash,
            ),
        )
        row = self._connection.execute(
            "SELECT * FROM operational_mode_transitions WHERE transition_id = ?",
            (transition_id,),
        ).fetchone()
        if row is None:
            raise OperationalModeConflictError("OPERATIONAL_MODE_INSERT_LOST", "inserted mode transition is not readable")
        return self._mode_record_from_row(row)

    def initialize(
        self,
        mode: str,
        *,
        changed_at: str,
        changed_by: str,
        reason_codes: Sequence[str],
        evidence_ref: str,
        approval_record_id: str | None = None,
    ) -> OperationalModeRecord:
        if mode == "LIVE":
            raise OperationalModeAuthorityError(
                "LIVE_NOT_AUTHORIZED",
                "Gate C task authority does not permit creation or promotion of LIVE mode",
            )
        if mode == "SHADOW":
            raise OperationalModeAuthorityError(
                "SHADOW_REQUIRES_AUDITED_TRANSITION",
                "SHADOW must be entered from an existing authoritative non-LIVE mode",
            )
        if mode not in {"RESEARCH", "PAPER", "PAUSED", "LOCKED"}:
            raise OperationalModeValidationError("UNSUPPORTED_OPERATIONAL_MODE", f"unsupported initial OperationalMode: {mode}")
        payload = _mode_payload(
            mode=mode,
            previous_mode=None,
            mode_revision=0,
            changed_at=changed_at,
            changed_by=changed_by,
            reason_codes=reason_codes,
            approval_record_id=approval_record_id,
            evidence_ref=evidence_ref,
        )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            if self._connection.execute("SELECT 1 FROM operational_mode_transitions LIMIT 1").fetchone() is not None:
                raise OperationalModeConflictError(
                    "OPERATIONAL_MODE_ALREADY_INITIALIZED",
                    "authoritative OperationalMode state already exists",
                )
            record = self._insert_mode_record(payload)
            self._connection.commit()
            self._fresh_shadow_checkpoint_id = None
            return record
        except OperationalModeError:
            self._connection.rollback()
            raise
        except Exception:
            self._connection.rollback()
            raise

    def transition(
        self,
        new_mode: str,
        *,
        expected_revision: int,
        changed_at: str,
        changed_by: str,
        reason_codes: Sequence[str],
        evidence_ref: str,
        approval_record_id: str | None = None,
    ) -> OperationalModeRecord:
        if new_mode == "LIVE":
            raise OperationalModeAuthorityError(
                "LIVE_NOT_AUTHORIZED",
                "Gate C task authority forbids any transition into LIVE",
            )
        if new_mode not in _GATE_C_TRANSITION_TARGETS:
            raise OperationalModeAuthorityError(
                "MODE_TRANSITION_OUTSIDE_GATE_C_SCOPE",
                "this bounded Gate C surface may transition only to SHADOW, PAUSED, or LOCKED",
            )
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            history = self._validated_mode_history()
            if not history:
                raise OperationalModeConflictError(
                    "OPERATIONAL_MODE_NOT_INITIALIZED",
                    "OperationalMode must be initialized before a transition",
                )
            current = history[-1]
            if current.mode_revision != expected_revision:
                raise OperationalModeConflictError(
                    "OPERATIONAL_MODE_REVISION_CONFLICT",
                    "expected OperationalMode revision does not match durable current revision",
                )
            if current.mode == new_mode:
                raise OperationalModeValidationError("OPERATIONAL_MODE_NOOP", "no-op mode transitions are not persisted")
            if current.mode == "LIVE":
                raise OperationalModeAuthorityError(
                    "LIVE_STATE_OUTSIDE_GATE_C_AUTHORITY",
                    "Gate C surface cannot reinterpret an existing LIVE mode",
                )
            if current.mode == "LOCKED" and new_mode == "SHADOW":
                raise OperationalModeAuthorityError(
                    "LOCKED_MODE_NOT_CLEARED",
                    "LOCKED cannot be cleared into SHADOW by this bounded Gate C surface",
                )
            payload = _mode_payload(
                mode=new_mode,
                previous_mode=current.mode,
                mode_revision=current.mode_revision + 1,
                changed_at=changed_at,
                changed_by=changed_by,
                reason_codes=reason_codes,
                approval_record_id=approval_record_id,
                evidence_ref=evidence_ref,
            )
            record = self._insert_mode_record(payload)
            self._connection.commit()
            self._fresh_shadow_checkpoint_id = None
            return record
        except OperationalModeError:
            self._connection.rollback()
            raise
        except Exception:
            self._connection.rollback()
            raise

    def history(self) -> tuple[OperationalModeRecord, ...]:
        return self._validated_mode_history()

    def _checkpoint_from_row(self, row: sqlite3.Row) -> ShadowCheckpoint:
        try:
            raw = json.loads(row["payload_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise OperationalModeValidationError(
                "SHADOW_CHECKPOINT_PAYLOAD_INVALID",
                "stored Shadow checkpoint is invalid JSON",
            ) from exc
        if not isinstance(raw, dict):
            raise OperationalModeValidationError(
                "SHADOW_CHECKPOINT_PAYLOAD_NOT_OBJECT",
                "stored Shadow checkpoint payload is not an object",
            )
        payload = _validate_shadow_checkpoint_payload(raw)
        payload_json = _canonical_json(payload)
        payload_hash = _sha256_text(payload_json)
        checkpoint_id = _checkpoint_id(int(row["mode_revision"]), payload_json)
        if row["payload_json"] != payload_json or row["payload_hash"] != payload_hash or row["checkpoint_id"] != checkpoint_id:
            raise OperationalModeConflictError(
                "SHADOW_CHECKPOINT_CORRUPT",
                "stored Shadow checkpoint identity/hash does not match canonical sanitized payload",
            )
        if row["observed_at"] != payload["observed_at"] or row["provider_observation_ref"] != payload["provider_observation_ref"]:
            raise OperationalModeConflictError(
                "SHADOW_CHECKPOINT_COLUMN_PAYLOAD_CONFLICT",
                "Shadow checkpoint index columns contradict sanitized payload",
            )
        revision = row["checkpoint_revision"]
        mode_revision = row["mode_revision"]
        if type(revision) is not int or revision < 0 or type(mode_revision) is not int or mode_revision < 0:
            raise OperationalModeConflictError("SHADOW_CHECKPOINT_REVISION_INVALID", "Shadow checkpoint revision metadata is invalid")
        return ShadowCheckpoint(
            checkpoint_id=checkpoint_id,
            checkpoint_revision=revision,
            mode_revision=mode_revision,
            observed_at=payload["observed_at"],
            provider_observation_ref=payload["provider_observation_ref"],
            payload_json=payload_json,
            payload_hash=payload_hash,
        )

    def _validated_checkpoints_for_mode(self, mode_revision: int) -> tuple[ShadowCheckpoint, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM shadow_provider_checkpoints
            WHERE mode_revision = ?
            ORDER BY checkpoint_revision
            """,
            (mode_revision,),
        ).fetchall()
        checkpoints = tuple(self._checkpoint_from_row(row) for row in rows)
        previous: ShadowCheckpoint | None = None
        for checkpoint in checkpoints:
            if previous is not None:
                prior_time = _utc(previous.observed_at, "stored prior checkpoint observed_at")
                current_time = _utc(checkpoint.observed_at, "stored checkpoint observed_at")
                if current_time <= prior_time:
                    raise OperationalModeConflictError(
                        "SHADOW_CHECKPOINT_TIME_CONFLICT",
                        "accepted Shadow checkpoint observations must advance strictly in time",
                    )
            previous = checkpoint
        return checkpoints

    def record_shadow_checkpoint(self, payload: Mapping[str, Any]) -> ShadowCheckpoint:
        canonical = _validate_shadow_checkpoint_payload(payload)
        payload_json = _canonical_json(canonical)
        payload_hash = _sha256_text(payload_json)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            history = self._validated_mode_history()
            if not history or history[-1].mode != "SHADOW":
                raise OperationalModeAuthorityError(
                    "SHADOW_MODE_REQUIRED",
                    "sanitized provider checkpoint may be accepted only while authoritative mode is SHADOW",
                )
            current_mode = history[-1]
            checkpoint_id = _checkpoint_id(current_mode.mode_revision, payload_json)
            existing = self._connection.execute(
                "SELECT * FROM shadow_provider_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
            if existing is not None:
                checkpoint = self._checkpoint_from_row(existing)
                self._connection.rollback()
                # Exact durable replay after restart is not fresh provider evidence.
                return checkpoint

            by_ref = self._connection.execute(
                "SELECT * FROM shadow_provider_checkpoints WHERE provider_observation_ref = ?",
                (canonical["provider_observation_ref"],),
            ).fetchone()
            if by_ref is not None:
                raise OperationalModeConflictError(
                    "SHADOW_OBSERVATION_REF_CONFLICT",
                    "provider_observation_ref already identifies different durable checkpoint material",
                )

            current_checkpoints = self._validated_checkpoints_for_mode(current_mode.mode_revision)
            if current_checkpoints:
                latest = current_checkpoints[-1]
                if _utc(canonical["observed_at"], "observed_at") <= _utc(latest.observed_at, "latest checkpoint observed_at"):
                    raise OperationalModeConflictError(
                        "SHADOW_CHECKPOINT_NOT_NEWER",
                        "new accepted provider checkpoint must advance the observation boundary",
                    )
            max_row = self._connection.execute(
                "SELECT MAX(checkpoint_revision) AS max_revision FROM shadow_provider_checkpoints"
            ).fetchone()
            prior_revision = None if max_row is None else max_row["max_revision"]
            checkpoint_revision = 0 if prior_revision is None else int(prior_revision) + 1
            self._connection.execute(
                """
                INSERT INTO shadow_provider_checkpoints (
                    checkpoint_id, checkpoint_revision, mode_revision,
                    observed_at, provider_observation_ref, payload_json, payload_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    checkpoint_revision,
                    current_mode.mode_revision,
                    canonical["observed_at"],
                    canonical["provider_observation_ref"],
                    payload_json,
                    payload_hash,
                ),
            )
            row = self._connection.execute(
                "SELECT * FROM shadow_provider_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
            if row is None:
                raise OperationalModeConflictError("SHADOW_CHECKPOINT_INSERT_LOST", "inserted Shadow checkpoint is not readable")
            checkpoint = self._checkpoint_from_row(row)
            self._connection.commit()
            self._fresh_shadow_checkpoint_id = checkpoint.checkpoint_id
            return checkpoint
        except OperationalModeError:
            self._connection.rollback()
            raise
        except sqlite3.IntegrityError as exc:
            self._connection.rollback()
            raise OperationalModeConflictError(
                "SHADOW_CHECKPOINT_DURABLE_CONFLICT",
                "Shadow checkpoint violates durable identity/lineage constraints",
            ) from exc
        except Exception:
            self._connection.rollback()
            raise

    def recover(self) -> OperationalModeRecovery:
        try:
            history = self._validated_mode_history()
        except OperationalModeError as exc:
            return OperationalModeRecovery(
                status="CONFLICT",
                reason_codes=(exc.code,),
                current_mode=None,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        if not history:
            return OperationalModeRecovery(
                status="MISSING",
                reason_codes=("OPERATIONAL_MODE_MISSING",),
                current_mode=None,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        current = history[-1]
        if current.mode == "LIVE":
            return OperationalModeRecovery(
                status="LIVE_UNAUTHORIZED",
                reason_codes=("LIVE_OUTSIDE_GATE_C_AUTHORITY",),
                current_mode=current,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        if current.mode != "SHADOW":
            return OperationalModeRecovery(
                status="READY",
                reason_codes=(),
                current_mode=current,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=False,
                shadow_planning_safe=False,
            )
        try:
            checkpoints = self._validated_checkpoints_for_mode(current.mode_revision)
        except OperationalModeError as exc:
            return OperationalModeRecovery(
                status="CONFLICT",
                reason_codes=(exc.code,),
                current_mode=current,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        if not checkpoints:
            return OperationalModeRecovery(
                status="RECONCILIATION_REQUIRED",
                reason_codes=("SHADOW_CHECKPOINT_MISSING",),
                current_mode=current,
                last_shadow_checkpoint=None,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        latest = checkpoints[-1]
        if self._fresh_shadow_checkpoint_id != latest.checkpoint_id:
            return OperationalModeRecovery(
                status="RECONCILIATION_REQUIRED",
                reason_codes=("FRESH_SHADOW_RECONCILIATION_REQUIRED",),
                current_mode=current,
                last_shadow_checkpoint=latest,
                fresh_reconciliation_required=True,
                shadow_planning_safe=False,
            )
        return OperationalModeRecovery(
            status="READY",
            reason_codes=(),
            current_mode=current,
            last_shadow_checkpoint=latest,
            fresh_reconciliation_required=False,
            shadow_planning_safe=True,
        )


def open_operational_mode_store(path: str | Path) -> OperationalModeStore:
    connection = _connect(path)
    try:
        _apply_migrations(connection)
        return OperationalModeStore(connection)
    except Exception:
        connection.close()
        raise


__all__ = [
    "OPERATIONAL_MODES",
    "OperationalModeAuthorityError",
    "OperationalModeConflictError",
    "OperationalModeError",
    "OperationalModeRecord",
    "OperationalModeRecovery",
    "OperationalModeStore",
    "OperationalModeValidationError",
    "ShadowCheckpoint",
    "open_operational_mode_store",
]
