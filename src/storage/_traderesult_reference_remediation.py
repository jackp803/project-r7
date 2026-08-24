from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, TYPE_CHECKING

from ._lifecycle_execution_binding import (
    augment_recovery_with_binding_and_trade_result as _base_augment_recovery,
    validate_trade_result_reference_graph as _base_validate_reference_graph,
)
from .runtime_models import PaperRuntimeRecovery, RuntimeValidationError

if TYPE_CHECKING:
    from ._paper_runtime import _PaperRuntimeStore


_PROTECTION_REQUIRED_LINEAGE = (
    "position_id",
    "trade_plan_id",
    "risk_decision_id",
    "risk_policy_version",
    "symbol",
)
_CLOSE_REQUIRED_LINEAGE = (
    "position_id",
    "trade_plan_id",
    "risk_decision_id",
    "risk_policy_version",
    "strategy_id",
    "strategy_version",
    "symbol",
)


def _payload_from_action(store: "_PaperRuntimeStore", action_id: str) -> dict[str, Any]:
    row = store._object_row("POSITION_ACTION", action_id)
    if row is None:
        raise RuntimeValidationError(
            "TRADE_RESULT_POSITION_ACTION_MISSING",
            f"TradeResult referenced PositionAction {action_id} is not durable",
        )
    value = store._row_payload(row)
    if not isinstance(value, dict):
        raise RuntimeValidationError(
            "TRADE_RESULT_POSITION_ACTION_INVALID",
            "referenced PositionAction payload is not an object",
        )
    return value


def _require_present(action: Mapping[str, Any], field: str) -> Any:
    if field not in action or action.get(field) is None:
        raise RuntimeValidationError(
            "TRADE_RESULT_POSITION_ACTION_LINEAGE_MISSING",
            f"referenced PositionAction.{field} is required by the settled authority profile",
        )
    value = action.get(field)
    if isinstance(value, str) and (not value or value != value.strip()):
        raise RuntimeValidationError(
            "TRADE_RESULT_POSITION_ACTION_LINEAGE_MISSING",
            f"referenced PositionAction.{field} must be a canonical non-empty value",
        )
    return value


def _require_equal(action: Mapping[str, Any], field: str, expected: Any) -> None:
    value = _require_present(action, field)
    if value != expected:
        raise RuntimeValidationError(
            "TRADE_RESULT_POSITION_ACTION_LINEAGE_MISMATCH",
            f"referenced PositionAction.{field} mismatches TradeResult/parent lineage",
        )


def _validate_required_position_action_lineage(
    store: "_PaperRuntimeStore",
    payload: Mapping[str, Any],
) -> None:
    refs = payload.get("exit_authority_refs")
    if not isinstance(refs, list):
        # The base validator owns reference-list shape diagnostics.
        return

    expected_by_field = {
        "position_id": payload.get("position_id"),
        "trade_plan_id": payload.get("trade_plan_id"),
        "risk_decision_id": payload.get("risk_decision_id"),
        "risk_policy_version": payload.get("risk_policy_version"),
        "strategy_id": payload.get("strategy_id"),
        "strategy_version": payload.get("strategy_version"),
        "symbol": payload.get("symbol"),
    }

    for ref in refs:
        if not isinstance(ref, Mapping):
            continue
        action_id = ref.get("position_action_id")
        if not isinstance(action_id, str) or not action_id:
            continue
        action = _payload_from_action(store, action_id)
        action_type = ref.get("action")
        role = ref.get("order_role")

        if action_type == "PROTECT" and role == "PROTECTION_STOP":
            for field in _PROTECTION_REQUIRED_LINEAGE:
                _require_equal(action, field, expected_by_field[field])
            _require_equal(action, "action", "PROTECT")
            _require_equal(action, "protection_profile_version", "protection-v0.1")
            continue

        if action_type in {"EXIT", "EMERGENCY_EXIT"} and role in {
            "POSITION_EXIT",
            "EMERGENCY_EXIT",
        }:
            for field in _CLOSE_REQUIRED_LINEAGE:
                _require_equal(action, field, expected_by_field[field])
            _require_equal(action, "action", action_type)
            _require_equal(action, "close_profile_version", "close-v0.1")


def validate_trade_result_reference_graph(
    store: "_PaperRuntimeStore",
    payload: Mapping[str, Any],
) -> None:
    """E6-018 strict settled-contract TradeResult reference-graph validation.

    The accepted E6-017 validator remains authoritative for request/fill/reference
    shape and linkage. This bounded remediation adds only mandatory settled-profile
    PositionAction authority lineage that legacy durable rows could omit.
    """

    _base_validate_reference_graph(store, payload)
    _validate_required_position_action_lineage(store, payload)


def _reason_and_severity(exc: RuntimeValidationError) -> tuple[str, str]:
    code = exc.code
    if "MISMATCH" in code or "CONFLICT" in code:
        return code, "CONFLICT"
    if "MISSING" in code:
        return code, "INCOMPLETE"
    return "TRADE_RESULT_REFERENCED_GRAPH_INVALID", "INCOMPLETE"


def augment_recovery_with_binding_and_trade_result(
    store: "_PaperRuntimeStore",
    recovery: PaperRuntimeRecovery,
) -> PaperRuntimeRecovery:
    """Preserve E6-017 recovery, then guarantee every TradeResult graph failure is non-READY."""

    augmented = _base_augment_recovery(store, recovery)
    reasons = list(augmented.reason_codes)
    requested_severity: str | None = None

    if augmented.trade_result is not None:
        try:
            validate_trade_result_reference_graph(store, augmented.trade_result.payload)
        except RuntimeValidationError as exc:
            reason, requested_severity = _reason_and_severity(exc)
            reasons.append(reason)

    unique_reasons = tuple(dict.fromkeys(reasons))
    status = augmented.status

    # Defect A: a generic invalid/duplicate/unused/shape-invalid reference graph
    # must never coexist with READY, even when it came from the E6-017 base path.
    if "TRADE_RESULT_REFERENCED_GRAPH_INVALID" in unique_reasons and status == "READY":
        status = "INCOMPLETE"

    if requested_severity == "CONFLICT":
        status = "CONFLICT"
    elif requested_severity == "INCOMPLETE" and status == "READY":
        status = "INCOMPLETE"

    return replace(augmented, status=status, reason_codes=unique_reasons)


__all__ = [
    "augment_recovery_with_binding_and_trade_result",
    "validate_trade_result_reference_graph",
]
