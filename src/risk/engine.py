from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .policy import RiskPolicy

SUPPORTED_SHARED_SCHEMA_VERSION = "contracts-v0.1"

_TRADE_INTENT_REQUIRED = {
    "schema_version",
    "intent_id",
    "signal_id",
    "strategy_id",
    "strategy_version",
    "symbol",
    "direction",
    "generated_at",
    "market_boundary_ref",
}
_TRADE_INTENT_OPTIONAL = {
    "entry_reference_price",
    "entry_style",
    "strategy_stop_level",
    "strategy_target_level",
    "max_hold_seconds",
}


@dataclass(frozen=True)
class RiskContext:
    market_health_status: str
    market_data_fresh: bool
    account_state_status: str
    account_state_known: bool
    position_state_status: str
    position_state_known: bool
    order_state_status: str
    order_state_known: bool
    kill_switch_active: bool
    new_exposure_allowed: bool
    trades_today: int
    open_position_count: int
    same_symbol_position_open: bool
    consecutive_losses: int
    drawdown: Decimal
    available_balance: Decimal | None


@dataclass(frozen=True)
class RiskProposal:
    quantity: Decimal
    notional: Decimal
    margin: Decimal
    leverage: Decimal
    estimated_max_loss: Decimal
    estimated_cost: Decimal
    reward_amount: Decimal
    required_stop_level: Decimal | None
    required_target_level: Decimal | None


class RiskInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RiskInputError("INVALID_TIMESTAMP", "timestamp must be RFC 3339 UTC ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RiskInputError("INVALID_TIMESTAMP", "timestamp must be valid RFC 3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RiskInputError("INVALID_TIMESTAMP", "timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _fmt_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise RiskInputError("INVALID_DECIMAL", f"{field} is not a valid decimal") from exc
    else:
        raise RiskInputError("INVALID_DECIMAL", f"{field} must be Decimal or decimal string")
    if not result.is_finite():
        raise RiskInputError("INVALID_DECIMAL", f"{field} must be finite")
    return result


def _is_finite_nonnegative_decimal(value: Any) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value >= 0


def _stable_id(prefix: str, material: Mapping[str, Any]) -> str:
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_trade_intent(intent: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    keys = set(intent.keys())
    missing = sorted(_TRADE_INTENT_REQUIRED - keys)
    extra = sorted(keys - _TRADE_INTENT_REQUIRED - _TRADE_INTENT_OPTIONAL)
    if missing:
        reasons.append("TRADE_INTENT_MISSING_REQUIRED_FIELD")
    if extra:
        reasons.append("TRADE_INTENT_UNDECLARED_FIELD")
    if intent.get("schema_version") != SUPPORTED_SHARED_SCHEMA_VERSION:
        reasons.append("UNSUPPORTED_SCHEMA_VERSION")
    if intent.get("direction") not in {"LONG", "SHORT"}:
        reasons.append("INVALID_DIRECTION")
    for field in (
        "intent_id",
        "signal_id",
        "strategy_id",
        "strategy_version",
        "symbol",
        "market_boundary_ref",
    ):
        value = intent.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"INVALID_{field.upper()}")
    if "generated_at" in intent:
        try:
            _utc(intent["generated_at"])
        except RiskInputError:
            reasons.append("INVALID_GENERATED_AT")

    entry_style = intent.get("entry_style")
    if not isinstance(entry_style, str) or not entry_style.strip():
        reasons.append("ENTRY_STYLE_REQUIRED_FOR_PLAN")

    if intent.get("max_hold_seconds") is not None:
        hold_seconds = intent["max_hold_seconds"]
        if type(hold_seconds) is not int or hold_seconds <= 0:
            reasons.append("INVALID_MAX_HOLD_SECONDS")

    for field in ("entry_reference_price", "strategy_stop_level", "strategy_target_level"):
        if intent.get(field) is None:
            continue
        try:
            value = _decimal(intent[field], field)
        except RiskInputError:
            reasons.append(f"INVALID_{field.upper()}")
            continue
        if value <= 0:
            reasons.append(f"INVALID_{field.upper()}")
    return reasons


def _validate_context(context: RiskContext) -> list[str]:
    reasons: list[str] = []
    for field_name in (
        "market_health_status",
        "account_state_status",
        "position_state_status",
        "order_state_status",
    ):
        value = getattr(context, field_name)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"INVALID_{field_name.upper()}")

    if context.market_data_fresh is not True:
        reasons.append("MARKET_DATA_STALE_OR_UNKNOWN")
    if context.account_state_known is not True:
        reasons.append("ACCOUNT_STATE_UNKNOWN")
    if context.position_state_known is not True:
        reasons.append("POSITION_STATE_UNKNOWN")
    if context.order_state_known is not True:
        reasons.append("ORDER_STATE_UNKNOWN")
    if context.kill_switch_active is not False:
        reasons.append("KILL_SWITCH_ACTIVE")
    if context.new_exposure_allowed is not True:
        reasons.append("NEW_EXPOSURE_DISABLED")
    if context.same_symbol_position_open is not False:
        reasons.append("AVERAGING_DOWN_OR_POSITION_ADD_BLOCKED")

    for field_name in ("trades_today", "open_position_count", "consecutive_losses"):
        value = getattr(context, field_name)
        if type(value) is not int or value < 0:
            reasons.append("INVALID_RISK_COUNTER_STATE")
            break

    if not _is_finite_nonnegative_decimal(context.drawdown):
        reasons.append("INVALID_DRAWDOWN_STATE")
    if context.available_balance is None:
        reasons.append("AVAILABLE_BALANCE_UNKNOWN")
    elif not _is_finite_nonnegative_decimal(context.available_balance):
        reasons.append("INVALID_AVAILABLE_BALANCE")
    return reasons


def _validate_proposal(proposal: RiskProposal | None, context: RiskContext, policy: RiskPolicy) -> list[str]:
    if proposal is None:
        return ["SIZING_UNAVAILABLE"]

    reasons: list[str] = []
    valid: dict[str, bool] = {}
    for field_name in (
        "quantity",
        "notional",
        "margin",
        "leverage",
        "estimated_max_loss",
        "estimated_cost",
        "reward_amount",
    ):
        value = getattr(proposal, field_name)
        valid[field_name] = _is_finite_nonnegative_decimal(value)
        if not valid[field_name]:
            reasons.append(f"INVALID_{field_name.upper()}")

    if valid["quantity"] and proposal.quantity <= 0:
        reasons.append("INVALID_QUANTITY")
    if valid["notional"] and proposal.notional <= 0:
        reasons.append("INVALID_NOTIONAL")
    if valid["margin"] and proposal.margin <= 0:
        reasons.append("INVALID_MARGIN")
    if valid["leverage"] and proposal.leverage <= 0:
        reasons.append("INVALID_LEVERAGE")
    if valid["estimated_max_loss"] and proposal.estimated_max_loss <= 0:
        reasons.append("INVALID_ESTIMATED_MAX_LOSS")
    if valid["reward_amount"] and proposal.reward_amount <= 0:
        reasons.append("INVALID_REWARD_AMOUNT")

    if proposal.required_stop_level is None:
        reasons.append("PROTECTIVE_STOP_REQUIRED")
    elif (
        not isinstance(proposal.required_stop_level, Decimal)
        or not proposal.required_stop_level.is_finite()
        or proposal.required_stop_level <= 0
    ):
        reasons.append("INVALID_PROTECTIVE_STOP")
    if proposal.required_target_level is not None and (
        not isinstance(proposal.required_target_level, Decimal)
        or not proposal.required_target_level.is_finite()
        or proposal.required_target_level <= 0
    ):
        reasons.append("INVALID_PROTECTIVE_TARGET")

    if valid["margin"] and proposal.margin > policy.max_margin:
        reasons.append("MARGIN_CAP_EXCEEDED")
    if valid["notional"] and proposal.notional > policy.max_notional:
        reasons.append("NOTIONAL_CAP_EXCEEDED")
    if valid["leverage"] and proposal.leverage > policy.max_leverage:
        reasons.append("LEVERAGE_CAP_EXCEEDED")
    if valid["estimated_cost"] and proposal.estimated_cost > policy.max_estimated_cost:
        reasons.append("COST_CAP_EXCEEDED")
    if (
        valid["margin"]
        and _is_finite_nonnegative_decimal(context.available_balance)
        and proposal.margin > context.available_balance
    ):
        reasons.append("INSUFFICIENT_BALANCE")

    if all(valid[field] for field in ("estimated_max_loss", "estimated_cost", "reward_amount")):
        total_risk = proposal.estimated_max_loss + proposal.estimated_cost
        if total_risk <= 0:
            reasons.append("INVALID_TOTAL_RISK")
        elif proposal.reward_amount / total_risk < policy.min_reward_risk:
            reasons.append("REWARD_RISK_BELOW_MINIMUM")
    return reasons


def evaluate_trade_intent(
    intent: Mapping[str, Any],
    context: RiskContext,
    proposal: RiskProposal | None,
    policy: RiskPolicy,
    *,
    decided_at: datetime,
) -> dict[str, Any]:
    """Produce an auditable fail-closed RiskDecision.

    This is an E5 gate skeleton. It intentionally requires an explicit sizing
    proposal and explicit policy rather than deriving capital-risk defaults.
    """

    if decided_at.tzinfo is None or decided_at.utcoffset() != timezone.utc.utcoffset(decided_at):
        raise ValueError("decided_at must be timezone-aware UTC")

    reasons = _validate_trade_intent(intent)
    reasons.extend(_validate_context(context))

    generated_at: datetime | None = None
    try:
        generated_at = _utc(intent["generated_at"])
    except (KeyError, RiskInputError, TypeError):
        pass
    if generated_at is not None:
        age = (decided_at - generated_at).total_seconds()
        if age < 0:
            reasons.append("TRADE_INTENT_FROM_FUTURE")
        elif age > policy.max_intent_age_seconds:
            reasons.append("TRADE_INTENT_STALE")

    if type(context.trades_today) is int and context.trades_today >= policy.max_trades_per_day:
        reasons.append("DAILY_TRADE_LIMIT_REACHED")
    if type(context.open_position_count) is int and context.open_position_count >= policy.max_open_positions:
        reasons.append("SIMULTANEOUS_POSITION_LIMIT_REACHED")
    if _is_finite_nonnegative_decimal(context.drawdown) and context.drawdown >= policy.max_drawdown:
        reasons.append("DRAWDOWN_LOCK_ACTIVE")
    if (
        type(context.consecutive_losses) is int
        and context.consecutive_losses >= policy.max_consecutive_losses
    ):
        reasons.append("CONSECUTIVE_LOSS_LOCK_ACTIVE")

    reasons.extend(_validate_proposal(proposal, context, policy))
    reasons = sorted(set(reasons))
    decision = "REJECT" if reasons else "APPROVE"

    decided_at_text = _fmt_utc(decided_at)
    material = {
        "intent_id": intent.get("intent_id"),
        "strategy_id": intent.get("strategy_id"),
        "strategy_version": intent.get("strategy_version"),
        "risk_policy_version": policy.version,
        "decided_at": decided_at_text,
        "decision": decision,
        "reason_codes": reasons,
    }
    result: dict[str, Any] = {
        "schema_version": SUPPORTED_SHARED_SCHEMA_VERSION,
        "risk_decision_id": _stable_id("risk_", material),
        "intent_id": str(intent.get("intent_id", "")),
        "strategy_id": str(intent.get("strategy_id", "")),
        "strategy_version": str(intent.get("strategy_version", "")),
        "decision": decision,
        "reason_codes": reasons,
        "risk_policy_version": policy.version,
        "decided_at": decided_at_text,
        "market_health_status": context.market_health_status,
        "account_state_status": context.account_state_status,
        "position_state_status": context.position_state_status,
    }

    if decision == "APPROVE" and proposal is not None:
        hold_seconds = policy.max_hold_seconds
        if intent.get("max_hold_seconds") is not None:
            hold_seconds = min(intent["max_hold_seconds"], policy.max_hold_seconds)
        result.update(
            {
                "approved_quantity": format(proposal.quantity, "f"),
                "approved_notional": format(proposal.notional, "f"),
                "approved_margin": format(proposal.margin, "f"),
                "approved_leverage": format(proposal.leverage, "f"),
                "margin_mode": policy.margin_mode,
                "estimated_max_loss": format(proposal.estimated_max_loss, "f"),
                "estimated_cost": format(proposal.estimated_cost, "f"),
                "required_stop_level": format(proposal.required_stop_level, "f"),
                "max_hold_seconds": hold_seconds,
            }
        )
        if proposal.required_target_level is not None:
            result["required_target_level"] = format(proposal.required_target_level, "f")
    return result


def build_approved_trade_plan(
    intent: Mapping[str, Any],
    risk_decision: Mapping[str, Any],
    policy: RiskPolicy,
    *,
    created_at: datetime,
) -> dict[str, Any]:
    """Emit ApprovedTradePlan only from an APPROVE decision.

    The nested instruction shapes are an E5-owned provisional serialization of
    already-approved bounds; E4/E7 integration must review them before treating
    them as a stable cross-module executable sub-contract.
    """

    if risk_decision.get("decision") != "APPROVE":
        raise RiskInputError("RISK_NOT_APPROVED", "ApprovedTradePlan requires APPROVE RiskDecision")
    if risk_decision.get("risk_policy_version") != policy.version:
        raise RiskInputError("POLICY_VERSION_MISMATCH", "RiskDecision policy does not match plan policy")
    if risk_decision.get("intent_id") != intent.get("intent_id"):
        raise RiskInputError("INTENT_ID_MISMATCH", "RiskDecision does not belong to TradeIntent")
    if intent.get("schema_version") != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise RiskInputError("UNSUPPORTED_SCHEMA_VERSION", "TradeIntent schema is unsupported")
    if risk_decision.get("schema_version") != SUPPORTED_SHARED_SCHEMA_VERSION:
        raise RiskInputError("UNSUPPORTED_SCHEMA_VERSION", "RiskDecision schema is unsupported")
    if created_at.tzinfo is None or created_at.utcoffset() != timezone.utc.utcoffset(created_at):
        raise ValueError("created_at must be timezone-aware UTC")

    required = (
        "approved_quantity",
        "approved_leverage",
        "margin_mode",
        "required_stop_level",
        "max_hold_seconds",
    )
    missing = [field for field in required if field not in risk_decision]
    if missing:
        raise RiskInputError("APPROVAL_BOUNDS_INCOMPLETE", f"missing approved bounds: {missing}")

    entry_style = intent.get("entry_style")
    if not isinstance(entry_style, str) or not entry_style.strip():
        raise RiskInputError("ENTRY_STYLE_REQUIRED", "entry_style is required for plan skeleton")

    created_at_text = _fmt_utc(created_at)
    expires_at = created_at + timedelta(seconds=policy.plan_ttl_seconds)
    entry_instruction: dict[str, Any] = {"style": entry_style}
    if intent.get("entry_reference_price") is not None:
        entry_instruction["reference_price"] = format(
            _decimal(intent["entry_reference_price"], "entry_reference_price"), "f"
        )

    protection_instruction: dict[str, Any] = {
        "stop_level": risk_decision["required_stop_level"],
        "max_hold_seconds": risk_decision["max_hold_seconds"],
    }
    if risk_decision.get("required_target_level") is not None:
        protection_instruction["target_level"] = risk_decision["required_target_level"]

    identity_material = {
        "risk_decision_id": risk_decision.get("risk_decision_id"),
        "intent_id": intent.get("intent_id"),
        "created_at": created_at_text,
        "expires_at": _fmt_utc(expires_at),
    }
    return {
        "schema_version": SUPPORTED_SHARED_SCHEMA_VERSION,
        "trade_plan_id": _stable_id("plan_", identity_material),
        "risk_decision_id": risk_decision["risk_decision_id"],
        "intent_id": intent["intent_id"],
        "strategy_id": intent["strategy_id"],
        "strategy_version": intent["strategy_version"],
        "symbol": intent["symbol"],
        "direction": intent["direction"],
        "quantity": risk_decision["approved_quantity"],
        "leverage": risk_decision["approved_leverage"],
        "margin_mode": risk_decision["margin_mode"],
        "entry_instruction": entry_instruction,
        "protection_instruction": protection_instruction,
        "created_at": created_at_text,
        "expires_at": _fmt_utc(expires_at),
        "risk_policy_version": policy.version,
    }
