from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Sequence

from brokers.okx_shadow import OKXShadowProviderReader, OKXShadowReadResult, ShadowFillCheckpoint
from market_data import Candle, MarketSnapshot
from risk import RiskPolicy, RiskProposal, derive_gate_c_risk_context, evaluate_trade_intent
from storage import OperationalModeRecovery, OperationalModeStore, ShadowCheckpoint
from strategy import (
    ENTRY_ORDER_TYPE_MARKET,
    ENTRY_PROFILE_VERSION,
    ParsedStrategyDefinition,
    StrategyRuntime,
    build_trade_intent,
)

SCHEMA_VERSION = "contracts-v0.1"
SHADOW_MODE = "SHADOW"
SHADOW_ENVIRONMENT_CLASSIFICATION = "PRODUCTION_READ_ONLY_SHADOW"
SHADOW_PLANNING_PROFILE = "shadow-hypothetical-planning-v0.1"

SHADOW_CAPABILITY_MANIFEST = (
    "observe_provider_read_only",
    "evaluate_existing_strategy_runtime",
    "derive_existing_gate_c_risk_context",
    "evaluate_existing_risk_policy",
    "persist_sanitized_shadow_checkpoint",
    "emit_non_authoritative_shadow_planning_evidence",
)

_FORBIDDEN_PROVIDER_CALLABLES = frozenset(
    {
        "submit", "submit_entry", "submit_order", "retry_entry", "retry_order", "place_order",
        "cancel", "cancel_order", "amend", "amend_order", "close_position", "set_leverage",
        "set_position_mode", "set_account_mode", "transfer", "withdraw", "deposit", "request", "send",
    }
)


class ShadowCompositionError(RuntimeError):
    """Sanitized E7 composition failure; messages never contain provider secrets/data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ShadowPlanningEvidence:
    """E7-local audit view; not TradeIntent, RiskDecision, ApprovedTradePlan, or execution authority."""

    profile_version: str
    operational_mode: str
    provider_observation_ref: str
    signal_id: str
    intent_id: str
    risk_decision_id: str
    risk_decision: str
    hypothetical_new_exposure_allowed: bool
    provider_submit_reachable: bool = False
    provider_mutation_reachable: bool = False


@dataclass(frozen=True, repr=False)
class ShadowCycleResult:
    """Sanitized Shadow result that deliberately exports no executable authority object."""

    mode_revision: int
    provider_observation_ref: str
    provider_read_healthy: bool
    shadow_checkpoint_id: str | None
    signal: Mapping[str, Any]
    planning_evidence: ShadowPlanningEvidence | None
    ready_for_hypothetical_new_exposure: bool
    reason_codes: tuple[str, ...]

    def __repr__(self) -> str:
        signal_id = self.signal.get("signal_id") if isinstance(self.signal, Mapping) else None
        risk_id = None if self.planning_evidence is None else self.planning_evidence.risk_decision_id
        return (
            "ShadowCycleResult(mode_revision={!r}, provider_observation_ref={!r}, "
            "provider_read_healthy={!r}, shadow_checkpoint_id={!r}, signal_id={!r}, "
            "risk_decision_id={!r}, planning_evidence_profile={!r}, "
            "ready_for_hypothetical_new_exposure={!r}, reason_codes={!r})"
        ).format(
            self.mode_revision,
            self.provider_observation_ref,
            self.provider_read_healthy,
            self.shadow_checkpoint_id,
            signal_id,
            risk_id,
            None if self.planning_evidence is None else self.planning_evidence.profile_version,
            self.ready_for_hypothetical_new_exposure,
            self.reason_codes,
        )


def _require_utc(value: datetime, code: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ShadowCompositionError(code)
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ShadowCompositionError(code)
    return value.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return _require_utc(value, "UTC_TIME_REQUIRED").isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ShadowCompositionError("SANITIZED_AUDIT_MATERIAL_INVALID") from exc


def _public_callables(value: object) -> frozenset[str]:
    names: set[str] = set()
    for name in dir(value):
        if name.startswith("_"):
            continue
        try:
            member = getattr(value, name)
        except Exception as exc:
            raise ShadowCompositionError("PROVIDER_CAPABILITY_INSPECTION_FAILED") from exc
        if callable(member):
            names.add(name)
    return frozenset(names)


def _validate_provider_reader(provider_reader: object) -> OKXShadowProviderReader:
    if type(provider_reader) is not OKXShadowProviderReader:
        raise ShadowCompositionError("SHADOW_PROVIDER_READER_TYPE_REQUIRED")
    public = _public_callables(provider_reader)
    if public != frozenset({"observe"}):
        raise ShadowCompositionError("SHADOW_PROVIDER_CAPABILITY_SURFACE_CHANGED")
    if public & _FORBIDDEN_PROVIDER_CALLABLES:
        raise ShadowCompositionError("SHADOW_PROVIDER_MUTATION_CAPABILITY_REACHABLE")
    return provider_reader


def _require_finalized_e1_candles(
    candles: Sequence[Candle], *, evaluated_at: datetime, symbol: str
) -> tuple[Candle, ...]:
    if isinstance(candles, (str, bytes, bytearray)) or not isinstance(candles, Sequence):
        raise ShadowCompositionError("E1_FINALIZED_CANDLE_SEQUENCE_REQUIRED")
    result = tuple(candles)
    if not result:
        raise ShadowCompositionError("E1_FINALIZED_CANDLE_SEQUENCE_REQUIRED")
    for candle in result:
        if type(candle) is not Candle:
            raise ShadowCompositionError("E1_CANONICAL_CANDLE_REQUIRED")
        if candle.symbol != symbol:
            raise ShadowCompositionError("E1_CANDLE_SYMBOL_MISMATCH")
        if candle.is_closed is not True:
            raise ShadowCompositionError("E1_UNFINALIZED_CANDLE_REJECTED")
        if candle.close_time > evaluated_at:
            raise ShadowCompositionError("E1_FUTURE_CANDLE_REJECTED")
    return result


def _fill_checkpoint_material(value: object) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if type(value) is not ShadowFillCheckpoint:
        raise ShadowCompositionError("E4_FILL_CHECKPOINT_SHAPE_INVALID")
    return {
        "latest_fill_timestamp_ms": value.latest_fill_timestamp_ms,
        "records_at_latest_timestamp": value.records_at_latest_timestamp,
    }


def _sanitized_observation_material(
    market_snapshot: MarketSnapshot, shadow_result: OKXShadowReadResult
) -> dict[str, Any]:
    observation = shadow_result.sanitized_observation
    return {
        "market": {
            "schema_version": market_snapshot.schema_version,
            "symbol": market_snapshot.symbol,
            "observed_at": _format_utc(market_snapshot.observed_at),
            "received_at": _format_utc(market_snapshot.received_at),
            "health_status": market_snapshot.health_status,
            "source": market_snapshot.source,
            "freshness_ms": market_snapshot.freshness_ms,
        },
        "provider": {
            "provider": observation.provider,
            "api_version": observation.api_version,
            "environment": observation.environment,
            "rest_hostname": observation.rest_hostname,
            "canonical_symbol": observation.canonical_symbol,
            "provider_instrument_id": observation.provider_instrument_id,
            "observed_at": _format_utc(observation.observed_at),
            "provider_time": None if observation.provider_time is None else _format_utc(observation.provider_time),
            "clock_skew_ms": observation.clock_skew_ms,
            "clock_status": observation.clock_status,
            "permission_category": observation.permission_category,
            "account_config_known": observation.account_config_known,
            "account_level": observation.account_level,
            "position_mode": observation.position_mode,
            "subaccount_status": observation.subaccount_status,
            "usdt_balance_known": observation.usdt_balance_known,
            "position_known": observation.position_known,
            "unexpected_exposure": observation.unexpected_exposure,
            "isolated_leverage_known": observation.isolated_leverage_known,
            "isolated_leverage_ok": observation.isolated_leverage_ok,
            "pending_order_count": observation.pending_order_count,
            "recent_fill_window_count": observation.recent_fill_window_count,
            "fill_checkpoint": _fill_checkpoint_material(observation.fill_checkpoint),
            "new_unreconciled_fill_count": observation.new_unreconciled_fill_count,
            "private_get_count": observation.private_get_count,
            "health_status": observation.health_status,
            "reason_codes": list(observation.reason_codes),
        },
    }


def _observation_identity(
    market_snapshot: MarketSnapshot, shadow_result: OKXShadowReadResult
) -> tuple[str, str]:
    material = _canonical_json(_sanitized_observation_material(market_snapshot, shadow_result))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"r7obs_{digest[:48]}", f"sha256:{digest}"


def _checkpoint_payload(
    market_snapshot: MarketSnapshot, shadow_result: OKXShadowReadResult
) -> dict[str, Any]:
    observation = shadow_result.sanitized_observation
    provider_ref, provider_hash = _observation_identity(market_snapshot, shadow_result)
    required_true = (
        market_snapshot.health_status == "HEALTHY",
        shadow_result.healthy,
        observation.permission_category == "read_only",
        observation.account_config_known is True,
        observation.usdt_balance_known is True,
        observation.position_known is True,
        observation.isolated_leverage_known is True,
        observation.isolated_leverage_ok is True,
        observation.unexpected_exposure is False,
        observation.pending_order_count == 0,
        observation.new_unreconciled_fill_count == 0,
    )
    if not all(required_true):
        raise ShadowCompositionError("UNSAFE_SHADOW_OBSERVATION_CANNOT_BE_CHECKPOINTED")
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "OKX",
        "environment_classification": SHADOW_ENVIRONMENT_CLASSIFICATION,
        "regional_hostname_ref": observation.rest_hostname,
        "canonical_instrument": "BTC_USDT_PERP",
        "provider_instrument": "BTC-USDT-SWAP",
        "observed_at": _format_utc(observation.observed_at),
        "permission_category": "read_only",
        "market_healthy": True,
        "account_config_known": True,
        "balance_known": True,
        "position_truth_known": True,
        "isolated_leverage_known": True,
        "unexpected_exposure": False,
        "pending_order_count": 0,
        "unreconciled_fill_count": 0,
        "provider_observation_ref": provider_ref,
        "provider_observation_hash": provider_hash,
        "reason_codes": [],
    }


class ShadowComposition:
    """Gate C no-submit composition over accepted E1/E2/E4/E5/E6 surfaces.

    There is no Broker, ExecutionGateway, OrderRequest, generic authenticated transport,
    TradeIntent/RiskDecision output, or ApprovedTradePlan output in the public composition
    result. The only E4 operation retained is the bound read-only `observe` capability.

    E4 fill checkpoint provenance is held only inside this trusted composition object;
    callers cannot inject a checkpoint. A new composition after restart starts without a
    trusted fill checkpoint and therefore fails closed if provider fill history cannot be
    reconciled safely.
    """

    __slots__ = ("_mode_store", "_observe_provider", "_strategy_runtime", "_fill_checkpoint")

    def __init__(
        self,
        *,
        mode_store: OperationalModeStore,
        provider_reader: OKXShadowProviderReader,
        strategy_runtime: StrategyRuntime | None = None,
    ) -> None:
        if type(mode_store) is not OperationalModeStore:
            raise ShadowCompositionError("E6_OPERATIONAL_MODE_STORE_REQUIRED")
        reader = _validate_provider_reader(provider_reader)
        runtime = StrategyRuntime() if strategy_runtime is None else strategy_runtime
        if type(runtime) is not StrategyRuntime:
            raise ShadowCompositionError("E2_STRATEGY_RUNTIME_REQUIRED")
        self._mode_store = mode_store
        self._observe_provider = reader.observe
        self._strategy_runtime = runtime
        self._fill_checkpoint: ShadowFillCheckpoint | None = None

    @staticmethod
    def capability_manifest() -> tuple[str, ...]:
        return SHADOW_CAPABILITY_MANIFEST

    def recover_shadow_state(self) -> OperationalModeRecovery:
        recovery = self._mode_store.recover()
        if recovery.current_mode is None:
            raise ShadowCompositionError("AUTHORITATIVE_OPERATIONAL_MODE_MISSING")
        if recovery.current_mode.mode != SHADOW_MODE:
            raise ShadowCompositionError("AUTHORITATIVE_SHADOW_MODE_REQUIRED")
        if recovery.status in {"CONFLICT", "LIVE_UNAUTHORIZED"}:
            raise ShadowCompositionError("AUTHORITATIVE_OPERATIONAL_MODE_UNSAFE")
        return recovery

    def run_cycle(
        self,
        *,
        strategy: ParsedStrategyDefinition,
        candles: Sequence[Candle],
        market_snapshot: MarketSnapshot,
        risk_policy: RiskPolicy,
        risk_proposal: RiskProposal,
        risk_evaluation_time: datetime,
        kill_switch_active: bool,
        trades_today: int,
        consecutive_losses: int,
        drawdown: Decimal,
        strategy_stop_level: Decimal | str | None = None,
        strategy_target_level: Decimal | str | None = None,
        max_hold_seconds: int | None = None,
    ) -> ShadowCycleResult:
        evaluation_time = _require_utc(risk_evaluation_time, "RISK_EVALUATION_TIME_UTC_REQUIRED")
        initial_recovery = self.recover_shadow_state()
        if type(market_snapshot) is not MarketSnapshot:
            raise ShadowCompositionError("E1_MARKET_SNAPSHOT_REQUIRED")
        if not isinstance(strategy, ParsedStrategyDefinition):
            raise ShadowCompositionError("E2_PARSED_STRATEGY_REQUIRED")
        finalized = _require_finalized_e1_candles(
            candles, evaluated_at=evaluation_time, symbol=market_snapshot.symbol
        )

        shadow_result = self._observe_provider(previous_fill_checkpoint=self._fill_checkpoint)
        if type(shadow_result) is not OKXShadowReadResult:
            raise ShadowCompositionError("E4_SHADOW_READ_RESULT_REQUIRED")

        derivation = derive_gate_c_risk_context(
            market_snapshot,
            shadow_result,
            risk_evaluation_time=evaluation_time,
            kill_switch_active=kill_switch_active,
            trades_today=trades_today,
            consecutive_losses=consecutive_losses,
            drawdown=drawdown,
        )
        provider_ref, _provider_hash = _observation_identity(market_snapshot, shadow_result)

        checkpoint: ShadowCheckpoint | None = None
        post_reconciliation: OperationalModeRecovery | None = None
        if derivation.safe_for_new_exposure:
            checkpoint = self._mode_store.record_shadow_checkpoint(
                _checkpoint_payload(market_snapshot, shadow_result)
            )
            post_reconciliation = self.recover_shadow_state()
            if not post_reconciliation.shadow_planning_safe:
                raise ShadowCompositionError("FRESH_SHADOW_RECONCILIATION_NOT_ESTABLISHED")
            self._fill_checkpoint = shadow_result.sanitized_observation.fill_checkpoint

        signal = self._strategy_runtime.evaluate(strategy, finalized, evaluation_time)
        if signal.get("direction") == "NO_TRADE":
            reasons = set(derivation.reason_codes)
            reasons.update(str(code) for code in signal.get("reason_codes", ()))
            if checkpoint is None:
                reasons.update(initial_recovery.reason_codes)
            return ShadowCycleResult(
                mode_revision=initial_recovery.current_mode.mode_revision,
                provider_observation_ref=provider_ref,
                provider_read_healthy=shadow_result.healthy,
                shadow_checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
                signal=dict(signal),
                planning_evidence=None,
                ready_for_hypothetical_new_exposure=False,
                reason_codes=tuple(sorted(reasons)),
            )

        trade_intent = build_trade_intent(
            signal,
            entry_profile_version=ENTRY_PROFILE_VERSION,
            entry_order_type=ENTRY_ORDER_TYPE_MARKET,
            generated_at=evaluation_time,
            entry_reference_price=signal.get("reference_price"),
            strategy_stop_level=strategy_stop_level,
            strategy_target_level=strategy_target_level,
            max_hold_seconds=max_hold_seconds,
        )
        risk_decision = evaluate_trade_intent(
            trade_intent,
            derivation.context,
            risk_proposal,
            risk_policy,
            decided_at=evaluation_time,
        )

        ready = (
            risk_decision.get("decision") == "APPROVE"
            and checkpoint is not None
            and post_reconciliation is not None
            and post_reconciliation.shadow_planning_safe
        )
        planning_evidence = ShadowPlanningEvidence(
            profile_version=SHADOW_PLANNING_PROFILE,
            operational_mode=SHADOW_MODE,
            provider_observation_ref=provider_ref,
            signal_id=str(signal.get("signal_id", "")),
            intent_id=str(trade_intent.get("intent_id", "")),
            risk_decision_id=str(risk_decision.get("risk_decision_id", "")),
            risk_decision=str(risk_decision.get("decision", "")),
            hypothetical_new_exposure_allowed=ready,
            provider_submit_reachable=False,
            provider_mutation_reachable=False,
        )

        reasons = set(derivation.reason_codes)
        reasons.update(str(code) for code in risk_decision.get("reason_codes", ()))
        if checkpoint is None:
            reasons.update(initial_recovery.reason_codes)

        return ShadowCycleResult(
            mode_revision=initial_recovery.current_mode.mode_revision,
            provider_observation_ref=provider_ref,
            provider_read_healthy=shadow_result.healthy,
            shadow_checkpoint_id=None if checkpoint is None else checkpoint.checkpoint_id,
            signal=dict(signal),
            planning_evidence=planning_evidence,
            ready_for_hypothetical_new_exposure=ready,
            reason_codes=tuple(sorted(reasons)),
        )


__all__ = [
    "SHADOW_CAPABILITY_MANIFEST",
    "SHADOW_PLANNING_PROFILE",
    "ShadowComposition",
    "ShadowCompositionError",
    "ShadowCycleResult",
    "ShadowPlanningEvidence",
]
