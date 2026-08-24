from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .state_machine import PositionEvent, PositionLifecycleState, transition

SCHEMA_VERSION = "contracts-v0.1"
AUTHORIZATION_TYPE = "POSITION_ACTION"
ORDER_ROLE = "PROTECTION_STOP"
ORDER_TYPE = "STOP_MARKET"
CONSISTENT = "CONSISTENT"
HEALTHY = "HEALTHY"
OPEN = "OPEN"
UNKNOWN_STATUSES = frozenset({"UNKNOWN", "RECONCILIATION_REQUIRED"})
DEFINITIVE_INACTIVE_STATUSES = frozenset({"REJECTED", "CANCELED", "EXPIRED"})
TRIGGERED_OR_FILLED_STATUSES = frozenset({"PARTIALLY_FILLED", "FILLED"})
AMBIGUOUS_HEALTH_STATUSES = frozenset({"UNKNOWN", "DEGRADED"})


@dataclass(frozen=True)
class ProtectionResultEvidence:
    """E5-internal holder for already-normalized E4 evidence.

    This is intentionally not a shared or serialized contract. query_performed
    distinguishes an unavailable/not-performed query from an authoritative
    query that completed and found no exact order.
    """

    query_performed: bool
    queried_order: Any | None = None
    submit_result: Any | None = None
    reconciliation_result: Any | None = None
    position_reconciliation_status: str = CONSISTENT


@dataclass(frozen=True)
class ProtectionLifecycleOutcome:
    """E5-internal deterministic interpretation of normalized protection truth."""

    event: PositionEvent | None
    next_state: PositionLifecycleState
    reason_code: str
    protection_verified: bool


class ProtectionResultBridgeError(ValueError):
    pass


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _text(value: Any) -> str | None:
    value = _value(value)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except Exception:
            return None
    else:
        return None
    return parsed if parsed.is_finite() else None


def _status(obj: Any, field_name: str) -> str | None:
    return _text(_field(obj, field_name))


def _unknown_outcome(
    current_state: PositionLifecycleState,
    reason_code: str,
) -> ProtectionLifecycleOutcome:
    next_state = transition(current_state, PositionEvent.STATE_UNKNOWN)
    return ProtectionLifecycleOutcome(
        event=PositionEvent.STATE_UNKNOWN,
        next_state=next_state,
        reason_code=reason_code,
        protection_verified=False,
    )


def _event_outcome(
    current_state: PositionLifecycleState,
    event: PositionEvent,
    reason_code: str,
    *,
    protection_verified: bool = False,
) -> ProtectionLifecycleOutcome:
    return ProtectionLifecycleOutcome(
        event=event,
        next_state=transition(current_state, event),
        reason_code=reason_code,
        protection_verified=protection_verified,
    )


def _validate_request_shape(request: Any) -> str | None:
    if _field(request, "schema_version") != SCHEMA_VERSION:
        return "PROTECTION_REQUEST_SCHEMA_INVALID"
    if _field(request, "authorization_type") != AUTHORIZATION_TYPE:
        return "PROTECTION_REQUEST_AUTHORITY_INVALID"
    if _field(request, "order_role") != ORDER_ROLE:
        return "PROTECTION_REQUEST_ROLE_INVALID"
    if _field(request, "order_type") != ORDER_TYPE:
        return "PROTECTION_REQUEST_TYPE_INVALID"
    if _field(request, "reduce_only") is not True:
        return "PROTECTION_REQUEST_NOT_REDUCE_ONLY"

    for field_name in (
        "order_request_id",
        "client_order_id",
        "trade_plan_id",
        "position_action_id",
        "position_id",
        "risk_decision_id",
        "symbol",
    ):
        if _text(_field(request, field_name)) is None:
            return f"PROTECTION_REQUEST_{field_name.upper()}_INVALID"

    side = _status(request, "side")
    if side not in {"BUY", "SELL"}:
        return "PROTECTION_REQUEST_SIDE_INVALID"

    quantity = _decimal(_field(request, "quantity"))
    if quantity is None or quantity <= 0:
        return "PROTECTION_REQUEST_QUANTITY_INVALID"

    if _text(_field(request, "quantity_profile_version")) is None:
        return "PROTECTION_REQUEST_QUANTITY_PROFILE_INVALID"
    if _text(_field(request, "quantity_unit")) is None:
        return "PROTECTION_REQUEST_QUANTITY_UNIT_INVALID"
    if _text(_field(request, "quantity_asset")) is None:
        return "PROTECTION_REQUEST_QUANTITY_ASSET_INVALID"

    stop_price = _decimal(_field(request, "stop_price"))
    if stop_price is None or stop_price <= 0:
        return "PROTECTION_REQUEST_STOP_PRICE_INVALID"
    if _field(request, "limit_price") is not None:
        return "PROTECTION_REQUEST_LIMIT_PRICE_FORBIDDEN"
    if _field(request, "time_in_force") is not None:
        return "PROTECTION_REQUEST_TIF_FORBIDDEN"
    return None


def _result_identity_reason(request: Any, result: Any) -> str | None:
    if result is None:
        return "ORDER_RESULT_MISSING"
    if _field(result, "schema_version") != SCHEMA_VERSION:
        return "ORDER_RESULT_SCHEMA_INVALID"
    if _field(result, "order_request_id") != _field(request, "order_request_id"):
        return "ORDER_REQUEST_ID_MISMATCH"
    if _field(result, "client_order_id") != _field(request, "client_order_id"):
        return "CLIENT_ORDER_ID_MISMATCH"

    requested = _decimal(_field(result, "requested_quantity"))
    expected = _decimal(_field(request, "quantity"))
    filled = _decimal(_field(result, "filled_quantity"))
    if requested is None or expected is None or requested != expected:
        return "REQUESTED_QUANTITY_MISMATCH"
    if filled is None or filled < 0 or filled > requested:
        return "FILLED_QUANTITY_INVALID"
    return None


def _reconciliation_reason(
    request: Any,
    queried_order: Any | None,
    reconciliation: Any | None,
) -> str | None:
    if reconciliation is None:
        return None
    if _field(reconciliation, "client_order_id") != _field(request, "client_order_id"):
        return "RECONCILIATION_CLIENT_ID_MISMATCH"

    resolved_status = _status(reconciliation, "resolved_status")
    if resolved_status is None:
        return "RECONCILIATION_STATUS_INVALID"

    if queried_order is not None:
        queried_status = _status(queried_order, "order_status")
        if resolved_status != queried_status:
            return "RECONCILIATION_QUERY_CONTRADICTION"
        if _field(reconciliation, "retry_allowed") is True:
            return "RECONCILIATION_RETRY_CONTRADICTS_FOUND_ORDER"
    return None


def _submit_is_ambiguous(submit_result: Any | None) -> bool:
    if submit_result is None:
        return False
    return _status(submit_result, "order_status") in UNKNOWN_STATUSES


def _ambiguous_submit_is_resolved_open(
    request: Any,
    queried_order: Any,
    reconciliation: Any | None,
) -> bool:
    if reconciliation is None:
        return False
    if _field(reconciliation, "client_order_id") != _field(request, "client_order_id"):
        return False
    if _status(reconciliation, "resolved_status") != OPEN:
        return False
    if _field(reconciliation, "retry_allowed") is True:
        return False
    return _status(queried_order, "order_status") == OPEN


def _definitive_absence_status(
    request: Any,
    reconciliation: Any | None,
) -> str | None:
    if reconciliation is None:
        return None
    if _field(reconciliation, "client_order_id") != _field(request, "client_order_id"):
        return None
    if _field(reconciliation, "retry_allowed") is True:
        return None
    resolved = _status(reconciliation, "resolved_status")
    return resolved if resolved in DEFINITIVE_INACTIVE_STATUSES else None


def interpret_protection_result(
    request: Any,
    evidence: ProtectionResultEvidence,
    current_state: PositionLifecycleState | str,
) -> ProtectionLifecycleOutcome:
    """Interpret normalized protection order truth into existing E5 lifecycle semantics.

    The function consumes evidence only. It never submits, queries, cancels, or
    retries broker orders and it contains no provider-native translation.
    """

    try:
        lifecycle = PositionLifecycleState(current_state)
    except ValueError as exc:
        raise ProtectionResultBridgeError(f"unknown lifecycle state: {current_state}") from exc

    request_reason = _validate_request_shape(request)
    if request_reason is not None:
        return _unknown_outcome(lifecycle, request_reason)

    if evidence.position_reconciliation_status != CONSISTENT:
        return _unknown_outcome(lifecycle, "POSITION_TRUTH_NOT_CONSISTENT")

    if evidence.submit_result is not None:
        submit_reason = _result_identity_reason(request, evidence.submit_result)
        if submit_reason is not None:
            return _unknown_outcome(lifecycle, f"SUBMIT_{submit_reason}")

    if evidence.query_performed is not True:
        return _unknown_outcome(lifecycle, "AUTHORITATIVE_QUERY_NOT_PERFORMED")

    queried = evidence.queried_order
    if queried is None:
        absence_status = _definitive_absence_status(
            request,
            evidence.reconciliation_result,
        )
        if absence_status is None:
            return _unknown_outcome(lifecycle, "AUTHORITATIVE_QUERY_NOT_FOUND_UNRESOLVED")
        if lifecycle == PositionLifecycleState.OPEN_UNPROTECTED:
            return _event_outcome(
                lifecycle,
                PositionEvent.PROTECTION_FAILED,
                f"PROTECTION_{absence_status}",
            )
        if lifecycle in {
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        }:
            return _event_outcome(
                lifecycle,
                PositionEvent.PROTECTION_LOST,
                f"PROTECTION_{absence_status}",
            )
        return _unknown_outcome(lifecycle, "PROTECTION_ABSENCE_OUTSIDE_SUPPORTED_LIFECYCLE")

    query_reason = _result_identity_reason(request, queried)
    if query_reason is not None:
        return _unknown_outcome(lifecycle, f"QUERY_{query_reason}")

    reconciliation_reason = _reconciliation_reason(
        request,
        queried,
        evidence.reconciliation_result,
    )
    if reconciliation_reason is not None:
        return _unknown_outcome(lifecycle, reconciliation_reason)

    query_status = _status(queried, "order_status")
    query_health = _status(queried, "execution_health_status")

    if query_status in UNKNOWN_STATUSES:
        return _unknown_outcome(lifecycle, f"ORDER_STATUS_{query_status}")
    if query_health in AMBIGUOUS_HEALTH_STATUSES or query_health != HEALTHY:
        return _unknown_outcome(lifecycle, f"EXECUTION_HEALTH_{query_health or 'INVALID'}")

    if query_status == OPEN:
        broker_order_id = _text(_field(queried, "broker_order_id"))
        if broker_order_id is None:
            return _unknown_outcome(lifecycle, "BROKER_ORDER_ID_REQUIRED_FOR_VERIFICATION")
        if _submit_is_ambiguous(evidence.submit_result) and not _ambiguous_submit_is_resolved_open(
            request,
            queried,
            evidence.reconciliation_result,
        ):
            return _unknown_outcome(lifecycle, "AMBIGUOUS_SUBMIT_NOT_RECONCILED_TO_OPEN")
        if lifecycle == PositionLifecycleState.OPEN_UNPROTECTED:
            return _event_outcome(
                lifecycle,
                PositionEvent.PROTECTION_VERIFIED,
                "PROTECTION_ACTIVE_VERIFIED",
                protection_verified=True,
            )
        if lifecycle in {
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        }:
            return ProtectionLifecycleOutcome(
                event=None,
                next_state=lifecycle,
                reason_code="PROTECTION_REMAINS_ACTIVE",
                protection_verified=True,
            )
        return _unknown_outcome(lifecycle, "ACTIVE_PROTECTION_OUTSIDE_SUPPORTED_LIFECYCLE")

    if query_status in DEFINITIVE_INACTIVE_STATUSES:
        if lifecycle == PositionLifecycleState.OPEN_UNPROTECTED:
            return _event_outcome(
                lifecycle,
                PositionEvent.PROTECTION_FAILED,
                f"PROTECTION_{query_status}",
            )
        if lifecycle in {
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        }:
            return _event_outcome(
                lifecycle,
                PositionEvent.PROTECTION_LOST,
                f"PROTECTION_{query_status}",
            )
        return _unknown_outcome(lifecycle, "INACTIVE_PROTECTION_OUTSIDE_SUPPORTED_LIFECYCLE")

    if query_status in TRIGGERED_OR_FILLED_STATUSES:
        return _unknown_outcome(lifecycle, f"PROTECTIVE_EXIT_{query_status}_REQUIRES_POSITION_CLOSE_TRUTH")

    return _unknown_outcome(lifecycle, f"ORDER_STATUS_{query_status or 'INVALID'}_NOT_VERIFIABLE")
