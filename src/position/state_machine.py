from __future__ import annotations

from enum import Enum


class PositionLifecycleState(str, Enum):
    PENDING_ENTRY = "PENDING_ENTRY"
    OPEN_UNPROTECTED = "OPEN_UNPROTECTED"
    OPEN_PROTECTED = "OPEN_PROTECTED"
    PROFIT_PROTECTED = "PROFIT_PROTECTED"
    EXIT_REQUESTED = "EXIT_REQUESTED"
    CLOSED = "CLOSED"
    EMERGENCY = "EMERGENCY"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class PositionEvent(str, Enum):
    ENTRY_FILL_OBSERVED = "ENTRY_FILL_OBSERVED"
    ENTRY_TERMINATED = "ENTRY_TERMINATED"
    PROTECTION_VERIFIED = "PROTECTION_VERIFIED"
    PROFIT_PROTECTION_VERIFIED = "PROFIT_PROTECTION_VERIFIED"
    PROTECTION_FAILED = "PROTECTION_FAILED"
    PROTECTION_LOST = "PROTECTION_LOST"
    EXIT_REQUESTED = "EXIT_REQUESTED"
    EXIT_FAILED = "EXIT_FAILED"
    POSITION_CLOSED = "POSITION_CLOSED"
    STATE_UNKNOWN = "STATE_UNKNOWN"
    RECONCILED_FLAT = "RECONCILED_FLAT"
    RECONCILED_OPEN_UNPROTECTED = "RECONCILED_OPEN_UNPROTECTED"
    RECONCILED_OPEN_PROTECTED = "RECONCILED_OPEN_PROTECTED"


class UnsafeTransitionError(ValueError):
    pass


_TRANSITIONS = {
    (PositionLifecycleState.PENDING_ENTRY, PositionEvent.ENTRY_FILL_OBSERVED): PositionLifecycleState.OPEN_UNPROTECTED,
    (PositionLifecycleState.PENDING_ENTRY, PositionEvent.ENTRY_TERMINATED): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.PENDING_ENTRY, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.OPEN_UNPROTECTED, PositionEvent.PROTECTION_VERIFIED): PositionLifecycleState.OPEN_PROTECTED,
    (PositionLifecycleState.OPEN_UNPROTECTED, PositionEvent.PROTECTION_FAILED): PositionLifecycleState.EMERGENCY,
    (PositionLifecycleState.OPEN_UNPROTECTED, PositionEvent.EXIT_REQUESTED): PositionLifecycleState.EXIT_REQUESTED,
    (PositionLifecycleState.OPEN_UNPROTECTED, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.OPEN_PROTECTED, PositionEvent.PROFIT_PROTECTION_VERIFIED): PositionLifecycleState.PROFIT_PROTECTED,
    (PositionLifecycleState.OPEN_PROTECTED, PositionEvent.PROTECTION_LOST): PositionLifecycleState.EMERGENCY,
    (PositionLifecycleState.OPEN_PROTECTED, PositionEvent.EXIT_REQUESTED): PositionLifecycleState.EXIT_REQUESTED,
    (PositionLifecycleState.OPEN_PROTECTED, PositionEvent.POSITION_CLOSED): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.OPEN_PROTECTED, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.PROFIT_PROTECTED, PositionEvent.PROTECTION_LOST): PositionLifecycleState.EMERGENCY,
    (PositionLifecycleState.PROFIT_PROTECTED, PositionEvent.EXIT_REQUESTED): PositionLifecycleState.EXIT_REQUESTED,
    (PositionLifecycleState.PROFIT_PROTECTED, PositionEvent.POSITION_CLOSED): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.PROFIT_PROTECTED, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.EXIT_REQUESTED, PositionEvent.POSITION_CLOSED): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.EXIT_REQUESTED, PositionEvent.EXIT_FAILED): PositionLifecycleState.EMERGENCY,
    (PositionLifecycleState.EXIT_REQUESTED, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.EMERGENCY, PositionEvent.EXIT_REQUESTED): PositionLifecycleState.EXIT_REQUESTED,
    (PositionLifecycleState.EMERGENCY, PositionEvent.POSITION_CLOSED): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.EMERGENCY, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
    (PositionLifecycleState.RECONCILIATION_REQUIRED, PositionEvent.RECONCILED_FLAT): PositionLifecycleState.CLOSED,
    (PositionLifecycleState.RECONCILIATION_REQUIRED, PositionEvent.RECONCILED_OPEN_UNPROTECTED): PositionLifecycleState.OPEN_UNPROTECTED,
    (PositionLifecycleState.RECONCILIATION_REQUIRED, PositionEvent.RECONCILED_OPEN_PROTECTED): PositionLifecycleState.OPEN_PROTECTED,
    (PositionLifecycleState.CLOSED, PositionEvent.STATE_UNKNOWN): PositionLifecycleState.RECONCILIATION_REQUIRED,
}


def transition(
    current: PositionLifecycleState | str,
    event: PositionEvent | str,
) -> PositionLifecycleState:
    """Apply an explicit fail-closed position lifecycle transition.

    There is intentionally no direct PENDING_ENTRY -> OPEN_PROTECTED transition:
    an observed fill first creates OPEN_UNPROTECTED exposure, and only verified
    protection may move it to OPEN_PROTECTED.
    """

    try:
        current_state = PositionLifecycleState(current)
    except ValueError as exc:
        raise UnsafeTransitionError(f"unknown lifecycle state: {current}") from exc
    try:
        position_event = PositionEvent(event)
    except ValueError as exc:
        raise UnsafeTransitionError(f"unknown position event: {event}") from exc

    target = _TRANSITIONS.get((current_state, position_event))
    if target is None:
        raise UnsafeTransitionError(
            f"transition is not permitted: {current_state.value} + {position_event.value}"
        )
    return target


def state_allows_safe_open_claim(state: PositionLifecycleState | str) -> bool:
    """Only verified protected states may be described as safely open."""

    try:
        lifecycle_state = PositionLifecycleState(state)
    except ValueError:
        return False
    return lifecycle_state in {
        PositionLifecycleState.OPEN_PROTECTED,
        PositionLifecycleState.PROFIT_PROTECTED,
    }


def state_blocks_new_exposure(state: PositionLifecycleState | str) -> bool:
    """Conservative E5 local gate for the V1 one-position baseline."""

    try:
        lifecycle_state = PositionLifecycleState(state)
    except ValueError:
        return True
    return lifecycle_state != PositionLifecycleState.CLOSED
