from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .state_machine import (
    PositionEvent,
    PositionLifecycleState,
    UnsafeTransitionError,
    transition,
)

SCHEMA_VERSION = "contracts-v0.1"
POSITION_LIFECYCLE_PROJECTION_PROFILE_VERSION = "position-lifecycle-projection-v0.1"

GENESIS = "GENESIS"
TRANSITION = "TRANSITION"
REATTESTATION = "REATTESTATION"

_RECONCILIATION_STATUSES = frozenset(
    {"CONSISTENT", "UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"}
)
_PROJECTION_KINDS = frozenset({GENESIS, TRANSITION, REATTESTATION})
_POSPROJ_RE = re.compile(r"^posproj_[0-9a-f]{64}$")
_DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

# Current canonical Position fields from contracts-v0.1 plus the accepted
# base-asset quantity profile fields used by the Gate B execution chain.
# Unknown fields fail closed rather than being silently promoted into the
# durable canonical projection without a shared-contract review.
_BASE_POSITION_FIELDS = frozenset(
    {
        "schema_version",
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "average_entry_price",
        "opened_at",
        "broker_state_observed_at",
        "reconciliation_status",
        "lifecycle_state",
        "unrealized_pnl",
        "realized_pnl",
        "current_stop_level",
        "current_target_level",
        "closed_at",
        "quantity_profile_version",
        "quantity_unit",
        "quantity_asset",
    }
)
_REQUIRED_BASE_POSITION_FIELDS = frozenset(
    {
        "schema_version",
        "position_id",
        "symbol",
        "side",
        "actual_quantity",
        "average_entry_price",
        "opened_at",
        "broker_state_observed_at",
        "reconciliation_status",
        "lifecycle_state",
    }
)
_PROJECTION_FIELDS = frozenset(
    {
        "position_lifecycle_projection_profile_version",
        "lifecycle_projection_id",
        "lifecycle_revision",
        "previous_lifecycle_projection_id",
        "lifecycle_projection_kind",
        "lifecycle_event",
        "lifecycle_interpreted_at",
        "lifecycle_source_broker_state_observed_at",
    }
)
_REQUIRED_PROJECTION_FIELDS = _PROJECTION_FIELDS
_E5_OWNED_POSITION_FIELDS = _PROJECTION_FIELDS | frozenset({"lifecycle_state"})


class LifecycleProjectionError(ValueError):
    """Fail-closed validation error for position-lifecycle-projection-v0.1."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _canonical_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise LifecycleProjectionError("INVALID_TEXT_FIELD", f"{field} must be a non-empty string")
    if value != value.strip():
        raise LifecycleProjectionError(
            "NONCANONICAL_TEXT_FIELD",
            f"{field} must not contain surrounding whitespace",
        )
    return value


def _serialized_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LifecycleProjectionError(
            "INVALID_TIMESTAMP",
            f"{field} must be an RFC3339 UTC string ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise LifecycleProjectionError(
            "INVALID_TIMESTAMP",
            f"{field} must be valid RFC3339 UTC",
        ) from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LifecycleProjectionError("INVALID_TIMESTAMP", f"{field} must be UTC")
    return parsed.astimezone(timezone.utc)


def _explicit_interpretation_time(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise LifecycleProjectionError(
            "INVALID_INTERPRETATION_TIME",
            "lifecycle_interpreted_at must be supplied explicitly as a datetime",
        )
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise LifecycleProjectionError(
            "INVALID_INTERPRETATION_TIME",
            "lifecycle_interpreted_at must be timezone-aware UTC",
        )
    return value.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_decimal(value: Any, field: str, *, allow_negative: bool) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise LifecycleProjectionError(
            "INVALID_DECIMAL",
            f"{field} must be a canonical base-10 decimal string",
        )
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise LifecycleProjectionError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    if not parsed.is_finite():
        raise LifecycleProjectionError("INVALID_DECIMAL", f"{field} must be finite")
    if parsed == 0 and value.startswith("-"):
        raise LifecycleProjectionError("INVALID_DECIMAL", f"{field} must not encode negative zero")
    if not allow_negative and parsed < 0:
        raise LifecycleProjectionError("INVALID_DECIMAL", f"{field} must be non-negative")
    return parsed


def _canonical_state(value: Any, field: str = "Position.lifecycle_state") -> PositionLifecycleState:
    if not isinstance(value, str):
        raise LifecycleProjectionError("INVALID_LIFECYCLE_STATE", f"{field} must be a canonical string")
    try:
        return PositionLifecycleState(value)
    except ValueError as exc:
        raise LifecycleProjectionError("INVALID_LIFECYCLE_STATE", f"unsupported lifecycle state: {value}") from exc


def _requested_state(value: PositionLifecycleState | str) -> PositionLifecycleState:
    try:
        return PositionLifecycleState(value)
    except (TypeError, ValueError) as exc:
        raise LifecycleProjectionError("INVALID_LIFECYCLE_STATE", f"unsupported lifecycle state: {value}") from exc


def _requested_event(value: PositionEvent | str) -> PositionEvent:
    try:
        return PositionEvent(value)
    except (TypeError, ValueError) as exc:
        raise LifecycleProjectionError("INVALID_LIFECYCLE_EVENT", f"unsupported lifecycle event: {value}") from exc


def _canonical_json(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise LifecycleProjectionError(
            "NONCANONICAL_POSITION_PAYLOAD",
            "Position projection contains a non-JSON canonical value",
        ) from exc


def _validate_position_payload(
    position: Mapping[str, Any],
    *,
    profiled: bool,
) -> dict[str, Any]:
    if not isinstance(position, Mapping):
        raise LifecycleProjectionError("INVALID_POSITION", "Position must be a mapping")

    if not profiled:
        unexpected_profile = sorted(set(position.keys()) & _PROJECTION_FIELDS)
        if unexpected_profile:
            raise LifecycleProjectionError(
                "SOURCE_POSITION_ALREADY_PROFILED",
                "exact E4 source Position must not carry lifecycle projection metadata",
            )

    allowed = _BASE_POSITION_FIELDS | (_PROJECTION_FIELDS if profiled else frozenset())
    unknown = sorted(set(position.keys()) - allowed)
    if unknown:
        raise LifecycleProjectionError(
            "UNSUPPORTED_POSITION_FIELDS",
            "Position contains unsupported fields: " + ", ".join(unknown),
        )

    missing = sorted(_REQUIRED_BASE_POSITION_FIELDS - set(position.keys()))
    if missing:
        raise LifecycleProjectionError(
            "POSITION_INCOMPLETE",
            "Position missing required fields: " + ", ".join(missing),
        )
    if position.get("schema_version") != SCHEMA_VERSION:
        raise LifecycleProjectionError("UNSUPPORTED_SCHEMA_VERSION", "Position schema_version is unsupported")

    _canonical_text(position.get("position_id"), "Position.position_id")
    _canonical_text(position.get("symbol"), "Position.symbol")
    if position.get("side") not in {"LONG", "SHORT"}:
        raise LifecycleProjectionError("INVALID_POSITION_SIDE", "Position.side must be LONG or SHORT")
    if position.get("reconciliation_status") not in _RECONCILIATION_STATUSES:
        raise LifecycleProjectionError(
            "INVALID_RECONCILIATION_STATUS",
            "Position.reconciliation_status is unsupported",
        )
    lifecycle = _canonical_state(position.get("lifecycle_state"))

    actual_quantity = _canonical_decimal(
        position.get("actual_quantity"),
        "Position.actual_quantity",
        allow_negative=False,
    )
    _canonical_decimal(
        position.get("average_entry_price"),
        "Position.average_entry_price",
        allow_negative=False,
    )
    opened_at = _serialized_utc(position.get("opened_at"), "Position.opened_at")
    observed_at = _serialized_utc(
        position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
    )
    if observed_at < opened_at:
        raise LifecycleProjectionError(
            "POSITION_TIME_INCONSISTENT",
            "broker_state_observed_at cannot predate opened_at",
        )

    for field in ("unrealized_pnl", "realized_pnl"):
        if field in position:
            _canonical_decimal(position[field], f"Position.{field}", allow_negative=True)
    for field in ("current_stop_level", "current_target_level"):
        if field in position:
            _canonical_decimal(position[field], f"Position.{field}", allow_negative=False)
    if "closed_at" in position:
        _serialized_utc(position["closed_at"], "Position.closed_at")
    for field in ("quantity_profile_version", "quantity_unit", "quantity_asset"):
        if field in position:
            _canonical_text(position[field], f"Position.{field}")

    _canonical_json(dict(position))
    return {
        "lifecycle_state": lifecycle,
        "actual_quantity": actual_quantity,
        "broker_state_observed_at": observed_at,
    }


def _broker_fact_payload(position: Mapping[str, Any]) -> dict[str, Any]:
    """Return every current canonical Position field except E5 lifecycle authority."""

    return {
        key: value
        for key, value in position.items()
        if key not in _E5_OWNED_POSITION_FIELDS
    }


def stable_lifecycle_projection_id(projection: Mapping[str, Any]) -> str:
    """Compute the PR #57 posproj_ identity over the complete payload except its ID."""

    if not isinstance(projection, Mapping):
        raise LifecycleProjectionError("INVALID_POSITION", "projection must be a mapping")
    material = dict(projection)
    material.pop("lifecycle_projection_id", None)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return "posproj_" + digest


def _event_can_reach_state(event: PositionEvent, state: PositionLifecycleState) -> bool:
    for candidate in PositionLifecycleState:
        try:
            if transition(candidate, event) == state:
                return True
        except UnsafeTransitionError:
            continue
    return False


def validate_position_lifecycle_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one self-contained position-lifecycle-projection-v0.1 payload."""

    facts = _validate_position_payload(projection, profiled=True)
    missing = sorted(_REQUIRED_PROJECTION_FIELDS - set(projection.keys()))
    if missing:
        raise LifecycleProjectionError(
            "LIFECYCLE_PROJECTION_INCOMPLETE",
            "profiled Position missing fields: " + ", ".join(missing),
        )
    if (
        projection.get("position_lifecycle_projection_profile_version")
        != POSITION_LIFECYCLE_PROJECTION_PROFILE_VERSION
    ):
        raise LifecycleProjectionError(
            "UNSUPPORTED_LIFECYCLE_PROJECTION_PROFILE",
            "Position lifecycle projection profile is unsupported",
        )

    projection_id = _canonical_text(
        projection.get("lifecycle_projection_id"),
        "Position.lifecycle_projection_id",
    )
    if _POSPROJ_RE.fullmatch(projection_id) is None:
        raise LifecycleProjectionError(
            "INVALID_LIFECYCLE_PROJECTION_ID",
            "lifecycle_projection_id must be posproj_<sha256>",
        )

    revision = projection.get("lifecycle_revision")
    if type(revision) is not int or revision < 0:
        raise LifecycleProjectionError(
            "INVALID_LIFECYCLE_REVISION",
            "lifecycle_revision must be a non-negative integer",
        )
    kind = projection.get("lifecycle_projection_kind")
    if kind not in _PROJECTION_KINDS:
        raise LifecycleProjectionError(
            "INVALID_LIFECYCLE_PROJECTION_KIND",
            "lifecycle_projection_kind is unsupported",
        )

    previous_id = projection.get("previous_lifecycle_projection_id")
    event_value = projection.get("lifecycle_event")
    if kind == GENESIS:
        if revision != 0 or previous_id is not None or event_value is not None:
            raise LifecycleProjectionError(
                "INVALID_GENESIS_PROJECTION",
                "GENESIS requires revision=0, previous=null, lifecycle_event=null",
            )
    else:
        if revision == 0:
            raise LifecycleProjectionError(
                "INVALID_LIFECYCLE_REVISION",
                "non-GENESIS projection requires revision > 0",
            )
        previous_text = _canonical_text(
            previous_id,
            "Position.previous_lifecycle_projection_id",
        )
        if _POSPROJ_RE.fullmatch(previous_text) is None:
            raise LifecycleProjectionError(
                "INVALID_PREDECESSOR_ID",
                "previous_lifecycle_projection_id must be posproj_<sha256>",
            )
        if kind == TRANSITION:
            if not isinstance(event_value, str):
                raise LifecycleProjectionError(
                    "INVALID_LIFECYCLE_EVENT",
                    "TRANSITION requires a canonical lifecycle_event string",
                )
            event = _requested_event(event_value)
            if not _event_can_reach_state(event, facts["lifecycle_state"]):
                raise LifecycleProjectionError(
                    "DECLARED_TRANSITION_STATE_INVALID",
                    "lifecycle_event cannot produce the declared lifecycle_state",
                )
        elif event_value is not None:
            raise LifecycleProjectionError(
                "INVALID_REATTESTATION_PROJECTION",
                "REATTESTATION requires lifecycle_event=null",
            )

    source_anchor_text = projection.get("lifecycle_source_broker_state_observed_at")
    if source_anchor_text != projection.get("broker_state_observed_at"):
        raise LifecycleProjectionError(
            "LIFECYCLE_SOURCE_ANCHOR_MISMATCH",
            "lifecycle source anchor must exactly equal broker_state_observed_at",
        )
    source_anchor = _serialized_utc(
        source_anchor_text,
        "Position.lifecycle_source_broker_state_observed_at",
    )
    interpreted_at = _serialized_utc(
        projection.get("lifecycle_interpreted_at"),
        "Position.lifecycle_interpreted_at",
    )
    if interpreted_at < source_anchor:
        raise LifecycleProjectionError(
            "INTERPRETATION_PREDATES_BROKER_OBSERVATION",
            "lifecycle_interpreted_at cannot predate its broker observation",
        )

    expected_id = stable_lifecycle_projection_id(projection)
    if projection_id != expected_id:
        raise LifecycleProjectionError(
            "LIFECYCLE_PROJECTION_ID_MISMATCH",
            "lifecycle_projection_id does not match the complete canonical payload",
        )

    return {
        **facts,
        "revision": revision,
        "projection_id": projection_id,
        "kind": kind,
        "source_anchor": source_anchor,
        "interpreted_at": interpreted_at,
    }


def _validate_source_and_previous(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_facts = _validate_position_payload(source_position, profiled=False)
    previous_facts = validate_position_lifecycle_projection(previous_projection)

    if source_position.get("position_id") != previous_projection.get("position_id"):
        raise LifecycleProjectionError(
            "POSITION_ID_MISMATCH",
            "source Position.position_id must match previous projection",
        )
    if source_facts["broker_state_observed_at"] < previous_facts["source_anchor"]:
        raise LifecycleProjectionError(
            "BROKER_OBSERVATION_REGRESSION",
            "source broker observation cannot regress below previous lifecycle anchor",
        )
    if source_facts["broker_state_observed_at"] == previous_facts["source_anchor"]:
        if _broker_fact_payload(source_position) != _broker_fact_payload(previous_projection):
            raise LifecycleProjectionError(
                "EQUAL_TIME_BROKER_FACT_CONFLICT",
                "equal broker observation time requires identical E4-owned Position facts",
            )
    return source_facts, previous_facts


def _projection_payload(
    source_position: Mapping[str, Any],
    *,
    lifecycle_state: PositionLifecycleState,
    revision: int,
    previous_id: str | None,
    kind: str,
    event: PositionEvent | None,
    interpreted_at: datetime,
) -> dict[str, Any]:
    source_anchor = _serialized_utc(
        source_position.get("broker_state_observed_at"),
        "Position.broker_state_observed_at",
    )
    if interpreted_at < source_anchor:
        raise LifecycleProjectionError(
            "INTERPRETATION_PREDATES_BROKER_OBSERVATION",
            "lifecycle_interpreted_at cannot predate its broker observation",
        )

    payload = dict(source_position)
    payload["lifecycle_state"] = lifecycle_state.value
    payload["position_lifecycle_projection_profile_version"] = (
        POSITION_LIFECYCLE_PROJECTION_PROFILE_VERSION
    )
    payload["lifecycle_revision"] = revision
    payload["previous_lifecycle_projection_id"] = previous_id
    payload["lifecycle_projection_kind"] = kind
    payload["lifecycle_event"] = None if event is None else event.value
    payload["lifecycle_interpreted_at"] = _fmt_utc(interpreted_at)
    payload["lifecycle_source_broker_state_observed_at"] = source_position[
        "broker_state_observed_at"
    ]
    payload["lifecycle_projection_id"] = stable_lifecycle_projection_id(payload)
    validate_position_lifecycle_projection(payload)
    return payload


def build_position_lifecycle_genesis(
    source_position: Mapping[str, Any],
    *,
    lifecycle_state: PositionLifecycleState | str,
    lifecycle_interpreted_at: datetime,
) -> dict[str, Any]:
    """Build the first durability-eligible E5 lifecycle projection (revision 0)."""

    _validate_position_payload(source_position, profiled=False)
    state = _requested_state(lifecycle_state)
    interpreted_at = _explicit_interpretation_time(lifecycle_interpreted_at)
    return _projection_payload(
        source_position,
        lifecycle_state=state,
        revision=0,
        previous_id=None,
        kind=GENESIS,
        event=None,
        interpreted_at=interpreted_at,
    )


def _build_transition(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    event: PositionEvent,
    interpreted_at: datetime,
) -> dict[str, Any]:
    _, previous_facts = _validate_source_and_previous(source_position, previous_projection)
    try:
        target_state = transition(previous_facts["lifecycle_state"], event)
    except UnsafeTransitionError as exc:
        raise LifecycleProjectionError(
            "INVALID_LIFECYCLE_TRANSITION",
            str(exc),
        ) from exc
    return _projection_payload(
        source_position,
        lifecycle_state=target_state,
        revision=previous_facts["revision"] + 1,
        previous_id=previous_facts["projection_id"],
        kind=TRANSITION,
        event=event,
        interpreted_at=interpreted_at,
    )


def build_position_lifecycle_transition(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    lifecycle_event: PositionEvent | str,
    lifecycle_interpreted_at: datetime,
) -> dict[str, Any]:
    """Apply a canonical non-closure E5 PositionEvent and serialize the next revision.

    POSITION_CLOSED is deliberately excluded. Final closure must use
    build_position_lifecycle_closed_transition() with a successful real
    TradeResultBuildOutcome so caller-supplied event material cannot bypass
    authoritative-flat/funding/fee validation.
    """

    event = _requested_event(lifecycle_event)
    if event == PositionEvent.POSITION_CLOSED:
        raise LifecycleProjectionError(
            "TRADE_RESULT_CLOSURE_OUTCOME_REQUIRED",
            "POSITION_CLOSED projection requires a successful TradeResultBuildOutcome",
        )
    interpreted_at = _explicit_interpretation_time(lifecycle_interpreted_at)
    return _build_transition(
        source_position,
        previous_projection,
        event=event,
        interpreted_at=interpreted_at,
    )


def build_position_lifecycle_closed_transition(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    trade_result_outcome: Any,
    lifecycle_interpreted_at: datetime,
) -> dict[str, Any]:
    """Serialize POSITION_CLOSED only from E5's successful TradeResult outcome."""

    # Local import avoids a module-import cycle while still requiring the exact
    # current E5 outcome type rather than a caller-authored event substitute.
    from .trade_result import TradeResultBuildOutcome

    if not isinstance(trade_result_outcome, TradeResultBuildOutcome):
        raise LifecycleProjectionError(
            "INVALID_TRADE_RESULT_OUTCOME",
            "closure projection requires TradeResultBuildOutcome",
        )
    if (
        trade_result_outcome.event != PositionEvent.POSITION_CLOSED
        or trade_result_outcome.next_state != PositionLifecycleState.CLOSED
    ):
        raise LifecycleProjectionError(
            "INVALID_TRADE_RESULT_OUTCOME",
            "TradeResultBuildOutcome must authorize POSITION_CLOSED -> CLOSED",
        )
    trade_result = trade_result_outcome.trade_result
    if not isinstance(trade_result, Mapping):
        raise LifecycleProjectionError(
            "INVALID_TRADE_RESULT_OUTCOME",
            "TradeResultBuildOutcome.trade_result must be a mapping",
        )

    source_facts = _validate_position_payload(source_position, profiled=False)
    previous_facts = validate_position_lifecycle_projection(previous_projection)
    if source_position.get("position_id") != previous_projection.get("position_id"):
        raise LifecycleProjectionError("POSITION_ID_MISMATCH", "closure Position ID does not match previous projection")
    if trade_result.get("position_id") != source_position.get("position_id"):
        raise LifecycleProjectionError("TRADE_RESULT_POSITION_MISMATCH", "TradeResult position_id mismatch")
    if trade_result.get("symbol") != source_position.get("symbol"):
        raise LifecycleProjectionError("TRADE_RESULT_SYMBOL_MISMATCH", "TradeResult symbol mismatch")
    if source_facts["actual_quantity"] != Decimal("0"):
        raise LifecycleProjectionError(
            "CLOSURE_SOURCE_NOT_FLAT",
            "POSITION_CLOSED projection requires exact source Position.actual_quantity=0",
        )
    if source_position.get("reconciliation_status") != "CONSISTENT":
        raise LifecycleProjectionError(
            "CLOSURE_SOURCE_NOT_CONSISTENT",
            "POSITION_CLOSED projection requires source reconciliation_status=CONSISTENT",
        )
    flat_anchor = source_position.get("broker_state_observed_at")
    if trade_result.get("closed_at") != flat_anchor or trade_result.get("flat_position_observed_at") != flat_anchor:
        raise LifecycleProjectionError(
            "TRADE_RESULT_FLAT_ANCHOR_MISMATCH",
            "TradeResult closed/flat observation must equal exact source broker observation",
        )
    if source_facts["broker_state_observed_at"] < previous_facts["source_anchor"]:
        raise LifecycleProjectionError(
            "BROKER_OBSERVATION_REGRESSION",
            "closure broker observation cannot regress below previous lifecycle anchor",
        )
    if source_facts["broker_state_observed_at"] == previous_facts["source_anchor"]:
        if _broker_fact_payload(source_position) != _broker_fact_payload(previous_projection):
            raise LifecycleProjectionError(
                "EQUAL_TIME_BROKER_FACT_CONFLICT",
                "equal broker observation time requires identical E4-owned Position facts",
            )

    interpreted_at = _explicit_interpretation_time(lifecycle_interpreted_at)
    return _build_transition(
        source_position,
        previous_projection,
        event=PositionEvent.POSITION_CLOSED,
        interpreted_at=interpreted_at,
    )


def build_position_lifecycle_reattestation(
    source_position: Mapping[str, Any],
    previous_projection: Mapping[str, Any],
    *,
    lifecycle_interpreted_at: datetime,
) -> dict[str, Any]:
    """Re-attest the previous E5 lifecycle state against equal/newer E4 facts."""

    _, previous_facts = _validate_source_and_previous(source_position, previous_projection)
    interpreted_at = _explicit_interpretation_time(lifecycle_interpreted_at)
    return _projection_payload(
        source_position,
        lifecycle_state=previous_facts["lifecycle_state"],
        revision=previous_facts["revision"] + 1,
        previous_id=previous_facts["projection_id"],
        kind=REATTESTATION,
        event=None,
        interpreted_at=interpreted_at,
    )
