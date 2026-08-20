from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from .costs import FeeModel, FixedFundingModel, SlippageModel
from .metrics import MetricsSummary, calculate_metrics

UTC = timezone.utc
SCHEMA_VERSION = "contracts-v0.1"
REPLAY_ENGINE_VERSION = "e3-replay-slice1-v1"
_ALLOWED_TIMEFRAMES = {"1m", "15m", "1h", "4h"}
_MISSING = object()


class ReplayValidationError(ValueError):
    """Historical input/configuration violates Slice 1 replay assumptions."""


class RuntimeContractError(ValueError):
    """E2 runtime output violates the contracts-v0.1 Signal boundary."""


def _read(obj: Any, field_name: str, default: Any = _MISSING) -> Any:
    if isinstance(obj, Mapping):
        if field_name in obj:
            return obj[field_name]
    elif hasattr(obj, field_name):
        return getattr(obj, field_name)
    if default is _MISSING:
        raise ReplayValidationError(f"required field missing: {field_name}")
    return default


def _decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ReplayValidationError(
            f"{field_name} must use Decimal/string/integer semantics, not binary float"
        )
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ReplayValidationError(f"invalid decimal field: {field_name}") from exc


def _utc(value: Any, field_name: str) -> datetime:
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ReplayValidationError(f"invalid RFC3339 timestamp: {field_name}") from exc
    if not isinstance(value, datetime):
        raise ReplayValidationError(f"{field_name} must be datetime or RFC3339 UTC string")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ReplayValidationError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _z(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_nonempty(value: Any, field_name: str) -> str:
    text = str(value) if value is not None else ""
    if not text:
        raise ReplayValidationError(f"{field_name} must be non-empty")
    return text


@dataclass(frozen=True)
class DatasetDescriptor:
    """E1-owned dataset provenance consumed by E3; E3 does not invent the hash."""

    dataset_id: str
    dataset_hash: str
    dataset_start: datetime | str
    dataset_end: datetime | str

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id is required")
        if not self.dataset_hash:
            raise ValueError("dataset_hash is required")


@dataclass(frozen=True)
class E2RuntimeBinding:
    """Adapter boundary that forces replay to invoke an E2 runtime object.

    `invoke` may adapt E2's concrete public API, but it must call that runtime. It must
    not contain duplicated strategy semantics. E3 deliberately does not accept a stream
    of precomputed Signals as a substitute for this binding.
    """

    runtime: Any
    runtime_version: str
    invoke: Callable[[Any, Any, tuple[Any, ...], datetime], Any]

    def __post_init__(self) -> None:
        if self.runtime is None:
            raise ValueError("an E2 runtime object is required")
        if not self.runtime_version:
            raise ValueError("E2 runtime_version is required")
        if not callable(self.invoke):
            raise TypeError("invoke must be callable")

    def evaluate(
        self,
        strategy_definition: Any,
        closed_history: tuple[Any, ...],
        evaluated_at: datetime,
    ) -> Any:
        return self.invoke(self.runtime, strategy_definition, closed_history, evaluated_at)


@dataclass(frozen=True)
class ReplayConfig:
    """Explicit Slice 1 research assumptions. No E5/live sizing authority is implied."""

    fixed_quantity: Decimal
    cost_model_version: str
    fee_model: FeeModel
    slippage_model: SlippageModel
    funding_model: FixedFundingModel
    close_open_position_at_dataset_end: bool = True
    run_created_at: datetime | None = None

    def __post_init__(self) -> None:
        quantity = _decimal(self.fixed_quantity, "fixed_quantity")
        if quantity <= 0:
            raise ValueError("fixed_quantity must be positive")
        if not self.cost_model_version:
            raise ValueError("cost_model_version is required")
        if self.run_created_at is not None:
            created_at = _utc(self.run_created_at, "run_created_at")
            object.__setattr__(self, "run_created_at", created_at)
        object.__setattr__(self, "fixed_quantity", quantity)

    def cost_assumptions(self) -> dict[str, Any]:
        return {
            "cost_model_version": self.cost_model_version,
            "fixed_quantity": str(self.fixed_quantity),
            "fee": self.fee_model.assumptions(),
            "slippage": self.slippage_model.assumptions(),
            "funding": self.funding_model.assumptions(),
        }


@dataclass(frozen=True)
class ReplayTrade:
    trade_id: str
    direction: str
    opened_at: datetime
    closed_at: datetime
    quantity: Decimal
    entry_reference_price: Decimal
    entry_fill_price: Decimal
    exit_reference_price: Decimal
    exit_fill_price: Decimal
    gross_pnl: Decimal
    net_pnl: Decimal
    total_fees: Decimal
    slippage_cost: Decimal
    funding_cost: Decimal
    exit_reason: str
    entry_signal_id: str

    def fingerprint_fields(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "direction": self.direction,
            "opened_at": _z(self.opened_at),
            "closed_at": _z(self.closed_at),
            "quantity": str(self.quantity),
            "entry_reference_price": str(self.entry_reference_price),
            "entry_fill_price": str(self.entry_fill_price),
            "exit_reference_price": str(self.exit_reference_price),
            "exit_fill_price": str(self.exit_fill_price),
            "gross_pnl": str(self.gross_pnl),
            "net_pnl": str(self.net_pnl),
            "total_fees": str(self.total_fees),
            "slippage_cost": str(self.slippage_cost),
            "funding_cost": str(self.funding_cost),
            "exit_reason": self.exit_reason,
            "entry_signal_id": self.entry_signal_id,
        }


@dataclass(frozen=True)
class BacktestResult:
    backtest_result_id: str
    strategy_id: str
    strategy_version: str
    strategy_content_hash: str
    runtime_version: str
    dataset_id: str
    dataset_hash: str
    dataset_start: datetime
    dataset_end: datetime
    cost_model_version: str
    created_at: datetime
    metrics: MetricsSummary
    trades: tuple[ReplayTrade, ...]
    runtime_invocations: int
    cost_assumptions: dict[str, Any]

    def to_contract(self, *, include_trades: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "backtest_result_id": self.backtest_result_id,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "strategy_content_hash": self.strategy_content_hash,
            "runtime_version": self.runtime_version,
            "dataset_id": self.dataset_id,
            "dataset_hash": self.dataset_hash,
            "dataset_start": _z(self.dataset_start),
            "dataset_end": _z(self.dataset_end),
            "cost_model_version": self.cost_model_version,
            "created_at": _z(self.created_at),
            "replay_engine_version": REPLAY_ENGINE_VERSION,
            **self.metrics.to_contract_fields(),
            "reproducibility": {
                "runtime_provider": "E2",
                "runtime_invocations": self.runtime_invocations,
                "cost_assumptions": self.cost_assumptions,
            },
            "validation_stages": {
                "oos": "NOT_RUN",
                "walk_forward": "NOT_RUN",
                "monte_carlo": "NOT_RUN",
                "parameter_robustness": "NOT_RUN",
                "regime": "NOT_RUN",
            },
        }
        if include_trades:
            payload["trades"] = [trade.fingerprint_fields() for trade in self.trades]
        return payload


@dataclass(frozen=True)
class _CandleFrame:
    raw: Any
    schema_version: str
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class _SignalView:
    signal_id: str
    direction: str
    evaluated_at: datetime
    stop_level: Decimal | None
    target_level: Decimal | None
    max_hold_seconds: int | None


@dataclass(frozen=True)
class _PendingEntry:
    direction: str
    signal_id: str
    stop_level: Decimal | None
    target_level: Decimal | None
    max_hold_seconds: int | None


@dataclass
class _OpenPosition:
    direction: str
    entry_signal_id: str
    opened_at: datetime
    quantity: Decimal
    entry_reference_price: Decimal
    entry_fill_price: Decimal
    entry_fee: Decimal
    entry_slippage_cost: Decimal
    stop_level: Decimal | None
    target_level: Decimal | None
    max_hold_seconds: int | None


class HistoricalReplayEngine:
    """Closed-candle historical replay that delegates every decision to E2."""

    def __init__(self, runtime: E2RuntimeBinding, config: ReplayConfig) -> None:
        self._runtime = runtime
        self._config = config

    def run(
        self,
        strategy_definition: Any,
        candles: Iterable[Any],
        dataset: DatasetDescriptor,
    ) -> BacktestResult:
        strategy_id = _require_nonempty(_read(strategy_definition, "strategy_id"), "strategy_id")
        strategy_version = _require_nonempty(
            _read(strategy_definition, "strategy_version"), "strategy_version"
        )
        strategy_content_hash = _require_nonempty(
            _read(strategy_definition, "content_hash"), "content_hash"
        )
        strategy_symbol = _require_nonempty(_read(strategy_definition, "symbol"), "symbol")
        required_timeframes = _read(strategy_definition, "required_timeframes")
        if isinstance(required_timeframes, str) or not isinstance(required_timeframes, Sequence):
            raise ReplayValidationError("required_timeframes must be a sequence")
        if len(required_timeframes) != 1:
            raise ReplayValidationError(
                "Slice 1 replay supports exactly one required timeframe; multi-timeframe replay is not implemented"
            )
        required_timeframe = str(required_timeframes[0])

        frames = tuple(self._project_candle(raw) for raw in candles)
        if not frames:
            raise ReplayValidationError("historical replay requires at least one Candle")
        self._validate_frames(frames, strategy_symbol, required_timeframe, dataset)

        trades: list[ReplayTrade] = []
        position: _OpenPosition | None = None
        pending_entry: _PendingEntry | None = None
        pending_exit_reason: str | None = None
        runtime_invocations = 0

        for index, frame in enumerate(frames):
            if position is not None and position.max_hold_seconds is not None:
                deadline = position.opened_at + timedelta(seconds=position.max_hold_seconds)
                if frame.open_time >= deadline:
                    trades.append(
                        self._close_position(position, frame.open, frame.open_time, "MAX_HOLD")
                    )
                    position = None
                    pending_exit_reason = None

            if position is not None and pending_exit_reason is not None:
                trades.append(
                    self._close_position(
                        position,
                        frame.open,
                        frame.open_time,
                        pending_exit_reason,
                    )
                )
                position = None
                pending_exit_reason = None

            if position is None and pending_entry is not None:
                position = self._open_position(pending_entry, frame.open, frame.open_time)
                pending_entry = None

            if position is not None:
                protective = self._protective_exit(position, frame)
                if protective is not None:
                    exit_reference, exit_reason = protective
                    # Intrabar order is unknown from OHLC. Recording close_time is conservative
                    # for funding duration and avoids inventing an intrabar timestamp.
                    trades.append(
                        self._close_position(
                            position,
                            exit_reference,
                            frame.close_time,
                            exit_reason,
                        )
                    )
                    position = None
                    pending_exit_reason = None

            history = tuple(item.raw for item in frames[: index + 1])
            if any(item.close_time > frame.close_time for item in frames[: index + 1]):
                raise ReplayValidationError("internal no-look-ahead boundary violation")
            raw_signal = self._runtime.evaluate(strategy_definition, history, frame.close_time)
            runtime_invocations += 1
            signal = self._parse_signal(
                raw_signal,
                expected_strategy_id=strategy_id,
                expected_strategy_version=strategy_version,
                expected_strategy_hash=strategy_content_hash,
                expected_symbol=strategy_symbol,
                expected_boundary=frame.close_time,
            )

            if position is None:
                if signal.direction in ("LONG", "SHORT"):
                    pending_entry = _PendingEntry(
                        direction=signal.direction,
                        signal_id=signal.signal_id,
                        stop_level=signal.stop_level,
                        target_level=signal.target_level,
                        max_hold_seconds=signal.max_hold_seconds,
                    )
            elif signal.direction in ("LONG", "SHORT") and signal.direction != position.direction:
                pending_exit_reason = "OPPOSITE_SIGNAL"

        if position is not None and self._config.close_open_position_at_dataset_end:
            final_frame = frames[-1]
            trades.append(
                self._close_position(
                    position,
                    final_frame.close,
                    final_frame.close_time,
                    "DATASET_END",
                )
            )
            position = None

        metrics = calculate_metrics(trades)
        created_at = self._config.run_created_at or datetime.now(UTC)
        result_id = self._result_id(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            strategy_content_hash=strategy_content_hash,
            dataset=dataset,
            trades=trades,
        )
        return BacktestResult(
            backtest_result_id=result_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            strategy_content_hash=strategy_content_hash,
            runtime_version=self._runtime.runtime_version,
            dataset_id=dataset.dataset_id,
            dataset_hash=dataset.dataset_hash,
            dataset_start=_utc(dataset.dataset_start, "dataset_start"),
            dataset_end=_utc(dataset.dataset_end, "dataset_end"),
            cost_model_version=self._config.cost_model_version,
            created_at=created_at,
            metrics=metrics,
            trades=tuple(trades),
            runtime_invocations=runtime_invocations,
            cost_assumptions=self._config.cost_assumptions(),
        )

    @staticmethod
    def _project_candle(raw: Any) -> _CandleFrame:
        schema_version = _require_nonempty(_read(raw, "schema_version"), "candle.schema_version")
        symbol = _require_nonempty(_read(raw, "symbol"), "candle.symbol")
        timeframe = _require_nonempty(_read(raw, "timeframe"), "candle.timeframe")
        if timeframe not in _ALLOWED_TIMEFRAMES:
            raise ReplayValidationError(f"unsupported baseline timeframe: {timeframe}")
        open_time = _utc(_read(raw, "open_time"), "candle.open_time")
        close_time = _utc(_read(raw, "close_time"), "candle.close_time")
        if open_time >= close_time:
            raise ReplayValidationError("Candle must satisfy open_time < close_time")
        if _read(raw, "is_closed") is not True:
            raise ReplayValidationError("historical replay accepts finalized closed Candles only")
        _require_nonempty(_read(raw, "source"), "candle.source")

        open_price = _decimal(_read(raw, "open"), "candle.open")
        high = _decimal(_read(raw, "high"), "candle.high")
        low = _decimal(_read(raw, "low"), "candle.low")
        close = _decimal(_read(raw, "close"), "candle.close")
        volume = _decimal(_read(raw, "volume"), "candle.volume")
        if volume < 0:
            raise ReplayValidationError("Candle volume must be non-negative")
        if not (low <= open_price <= high and low <= close <= high):
            raise ReplayValidationError("malformed OHLC violates low <= open/close <= high")

        return _CandleFrame(
            raw=raw,
            schema_version=schema_version,
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

    @staticmethod
    def _validate_frames(
        frames: tuple[_CandleFrame, ...],
        strategy_symbol: str,
        required_timeframe: str,
        dataset: DatasetDescriptor,
    ) -> None:
        previous: _CandleFrame | None = None
        for frame in frames:
            if frame.symbol != strategy_symbol:
                raise ReplayValidationError("Candle symbol does not match StrategyDefinition")
            if frame.timeframe != required_timeframe:
                raise ReplayValidationError("Candle timeframe does not match StrategyDefinition")
            if previous is not None:
                if frame.open_time <= previous.open_time:
                    raise ReplayValidationError("duplicate or out-of-order Candle open_time")
                if frame.open_time < previous.close_time:
                    raise ReplayValidationError("overlapping Candle intervals are not allowed")
            previous = frame

        dataset_start = _utc(dataset.dataset_start, "dataset_start")
        dataset_end = _utc(dataset.dataset_end, "dataset_end")
        if dataset_start != frames[0].open_time:
            raise ReplayValidationError("dataset_start must match the first consumed Candle.open_time")
        if dataset_end != frames[-1].close_time:
            raise ReplayValidationError("dataset_end must match the last consumed Candle.close_time")
        if dataset_start >= dataset_end:
            raise ReplayValidationError("dataset_start must be before dataset_end")

    @staticmethod
    def _parse_signal(
        raw_signal: Any,
        *,
        expected_strategy_id: str,
        expected_strategy_version: str,
        expected_strategy_hash: str,
        expected_symbol: str,
        expected_boundary: datetime,
    ) -> _SignalView:
        _require_nonempty(_read(raw_signal, "schema_version"), "signal.schema_version")
        signal_id = _require_nonempty(_read(raw_signal, "signal_id"), "signal.signal_id")
        strategy_id = _require_nonempty(_read(raw_signal, "strategy_id"), "signal.strategy_id")
        strategy_version = _require_nonempty(
            _read(raw_signal, "strategy_version"), "signal.strategy_version"
        )
        content_hash = _require_nonempty(
            _read(raw_signal, "strategy_content_hash"), "signal.strategy_content_hash"
        )
        symbol = _require_nonempty(_read(raw_signal, "symbol"), "signal.symbol")
        evaluated_at = _utc(_read(raw_signal, "evaluated_at"), "signal.evaluated_at")
        direction = _require_nonempty(_read(raw_signal, "direction"), "signal.direction")
        _read(raw_signal, "reason_codes")
        _require_nonempty(
            _read(raw_signal, "market_boundary_ref"), "signal.market_boundary_ref"
        )

        if strategy_id != expected_strategy_id or strategy_version != expected_strategy_version:
            raise RuntimeContractError("E2 Signal strategy identity does not match StrategyDefinition")
        if content_hash != expected_strategy_hash:
            raise RuntimeContractError("E2 Signal strategy_content_hash mismatch")
        if symbol != expected_symbol:
            raise RuntimeContractError("E2 Signal symbol mismatch")
        if evaluated_at != expected_boundary:
            raise RuntimeContractError(
                "E2 Signal evaluated_at must equal the exact closed-candle replay boundary"
            )
        if direction not in ("LONG", "SHORT", "NO_TRADE"):
            raise RuntimeContractError(f"unsupported E2 Signal direction: {direction}")

        stop_raw = _read(raw_signal, "strategy_stop_level", None)
        target_raw = _read(raw_signal, "strategy_target_level", None)
        max_hold_raw = _read(raw_signal, "max_hold_seconds", None)
        stop = None if stop_raw is None else _decimal(stop_raw, "signal.strategy_stop_level")
        target = None if target_raw is None else _decimal(
            target_raw, "signal.strategy_target_level"
        )
        if max_hold_raw is None:
            max_hold = None
        else:
            if isinstance(max_hold_raw, bool) or not isinstance(max_hold_raw, int):
                raise RuntimeContractError("max_hold_seconds must be an integer")
            if max_hold_raw <= 0:
                raise RuntimeContractError("max_hold_seconds must be positive")
            max_hold = max_hold_raw

        return _SignalView(
            signal_id=signal_id,
            direction=direction,
            evaluated_at=evaluated_at,
            stop_level=stop,
            target_level=target,
            max_hold_seconds=max_hold,
        )

    def _open_position(
        self,
        request: _PendingEntry,
        reference_price: Decimal,
        opened_at: datetime,
    ) -> _OpenPosition:
        order_side = "BUY" if request.direction == "LONG" else "SELL"
        fill = self._config.slippage_model.fill_price(reference_price, order_side, "ENTRY")
        quantity = self._config.fixed_quantity
        entry_fee = self._config.fee_model.fee(fill * quantity, "ENTRY")
        slippage_cost = self._config.slippage_model.slippage_cost(
            reference_price, fill, quantity
        )
        return _OpenPosition(
            direction=request.direction,
            entry_signal_id=request.signal_id,
            opened_at=opened_at,
            quantity=quantity,
            entry_reference_price=reference_price,
            entry_fill_price=fill,
            entry_fee=entry_fee,
            entry_slippage_cost=slippage_cost,
            stop_level=request.stop_level,
            target_level=request.target_level,
            max_hold_seconds=request.max_hold_seconds,
        )

    @staticmethod
    def _protective_exit(
        position: _OpenPosition, frame: _CandleFrame
    ) -> tuple[Decimal, str] | None:
        if position.direction == "LONG":
            stop_hit = position.stop_level is not None and frame.low <= position.stop_level
            target_hit = position.target_level is not None and frame.high >= position.target_level
            if stop_hit:
                # If stop and target are both touched, stop wins. If the market gaps
                # through the stop at the candle open, use the worse open reference.
                stop_reference = (
                    frame.open
                    if position.stop_level is not None and frame.open <= position.stop_level
                    else position.stop_level
                )
                assert stop_reference is not None
                return stop_reference, "STOP_LOSS"
            if target_hit:
                assert position.target_level is not None
                return position.target_level, "TAKE_PROFIT"
            return None

        stop_hit = position.stop_level is not None and frame.high >= position.stop_level
        target_hit = position.target_level is not None and frame.low <= position.target_level
        if stop_hit:
            stop_reference = (
                frame.open
                if position.stop_level is not None and frame.open >= position.stop_level
                else position.stop_level
            )
            assert stop_reference is not None
            return stop_reference, "STOP_LOSS"
        if target_hit:
            assert position.target_level is not None
            return position.target_level, "TAKE_PROFIT"
        return None

    def _close_position(
        self,
        position: _OpenPosition,
        exit_reference_price: Decimal,
        closed_at: datetime,
        exit_reason: str,
    ) -> ReplayTrade:
        exit_order_side = "SELL" if position.direction == "LONG" else "BUY"
        exit_fill = self._config.slippage_model.fill_price(
            exit_reference_price, exit_order_side, "EXIT"
        )
        exit_fee = self._config.fee_model.fee(
            exit_fill * position.quantity, "EXIT"
        )
        total_fees = position.entry_fee + exit_fee
        exit_slippage = self._config.slippage_model.slippage_cost(
            exit_reference_price, exit_fill, position.quantity
        )
        total_slippage = position.entry_slippage_cost + exit_slippage

        if position.direction == "LONG":
            gross_pnl = (exit_fill - position.entry_fill_price) * position.quantity
        else:
            gross_pnl = (position.entry_fill_price - exit_fill) * position.quantity

        funding_cost = self._config.funding_model.cost(
            position.direction,
            position.quantity,
            position.entry_fill_price,
            position.opened_at,
            closed_at,
        )
        net_pnl = gross_pnl - total_fees - funding_cost
        trade_id = self._trade_id(position, exit_fill, closed_at, exit_reason)
        return ReplayTrade(
            trade_id=trade_id,
            direction=position.direction,
            opened_at=position.opened_at,
            closed_at=closed_at,
            quantity=position.quantity,
            entry_reference_price=position.entry_reference_price,
            entry_fill_price=position.entry_fill_price,
            exit_reference_price=exit_reference_price,
            exit_fill_price=exit_fill,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            total_fees=total_fees,
            slippage_cost=total_slippage,
            funding_cost=funding_cost,
            exit_reason=exit_reason,
            entry_signal_id=position.entry_signal_id,
        )

    @staticmethod
    def _trade_id(
        position: _OpenPosition,
        exit_fill: Decimal,
        closed_at: datetime,
        exit_reason: str,
    ) -> str:
        material = "|".join(
            [
                position.entry_signal_id,
                position.direction,
                _z(position.opened_at),
                str(position.entry_fill_price),
                _z(closed_at),
                str(exit_fill),
                exit_reason,
            ]
        )
        return "replay_trade_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]

    def _result_id(
        self,
        *,
        strategy_id: str,
        strategy_version: str,
        strategy_content_hash: str,
        dataset: DatasetDescriptor,
        trades: Sequence[ReplayTrade],
    ) -> str:
        material = {
            "replay_engine_version": REPLAY_ENGINE_VERSION,
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "strategy_content_hash": strategy_content_hash,
            "runtime_version": self._runtime.runtime_version,
            "dataset_id": dataset.dataset_id,
            "dataset_hash": dataset.dataset_hash,
            "dataset_start": _z(_utc(dataset.dataset_start, "dataset_start")),
            "dataset_end": _z(_utc(dataset.dataset_end, "dataset_end")),
            "cost_assumptions": self._config.cost_assumptions(),
            "close_open_position_at_dataset_end": self._config.close_open_position_at_dataset_end,
            "trades": [trade.fingerprint_fields() for trade in trades],
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return "backtest_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
