"""Thin E3 binding to the authoritative current-main E2 Strategy Runtime.

This module intentionally contains no indicator, DSL, TradeIntent, or strategy-decision
logic. It only adapts E3's replay call shape to E2's public StrategyDefinition parser
and StrategyRuntime evaluation path.
"""

from __future__ import annotations

from typing import Any

from .replay import E2RuntimeBinding, RuntimeContractError


class E2RuntimeUnavailableError(ImportError):
    """Raised when the current repository does not expose E2's public runtime package."""


def project_e2_runtime_binding(*,runtime_profile='0.1.0',candles_by_timeframe=None,
                             availability_model='recorded_received_at') -> E2RuntimeBinding:
    """Bind E3 historical replay to the real project E2 runtime.

    Current-main E2 public path::

        from strategy import StrategyRuntime, parse_strategy_definition
        parsed = parse_strategy_definition(strategy_payload)
        runtime = StrategyRuntime()
        signal = runtime.evaluate(parsed, closed_candle_history, evaluated_at)

    `parse_strategy_definition` is E2's authoritative compilation/validation boundary.
    E3 invokes it on every replay evaluation call and never interprets strategy rules,
    indicators, parameters, TradeIntent semantics, or provider execution details itself.
    """

    try:
        from strategy import RUNTIME_VERSION, StrategyRuntime, parse_strategy_definition
    except ImportError as exc:
        raise E2RuntimeUnavailableError(
            "Current-main E2 package 'strategy' is unavailable. E3 historical replay "
            "requires the repository's authoritative E2 StrategyRuntime package."
        ) from exc

    runtime = StrategyRuntime()
    if runtime_profile=='0.2.0':
        from types import MappingProxyType
        from strategy.v02.models import ParsedStrategyV02
        from strategy.v02.temporal import build_asof_bundle
        from strategy.v02.exits import build_exit_request
        from position.exit_requests import resolve_exit_constraints
        if candles_by_timeframe is None:
            raise RuntimeContractError('Explicit v0.2 E1 timeframe binding required')
        bound=MappingProxyType({key:tuple(rows) for key,rows in candles_by_timeframe.items()})
        def parsed(value):
            result=value if isinstance(value,ParsedStrategyV02) else parse_strategy_definition(value)
            if not isinstance(result,ParsedStrategyV02): raise RuntimeContractError('Explicit v0.2 strategy required')
            return result
        def bundle(value,history,boundary):
            strategy=parsed(value)
            if any(tf not in bound for tf in strategy.required_timeframes):
                raise RuntimeContractError('Required timeframe dataset missing')
            rows={tf:bound[tf] for tf in strategy.required_timeframes}
            # Evaluation prefix is E3's exact warmup/scored selection. Auxiliary
            # canonical inputs remain subject to E2 boundary/receipt filtering.
            rows[strategy.evaluation_timeframe]=history
            return strategy,build_asof_bundle(rows,boundary,boundary,availability_model=availability_model)
        def invoke_v02(runtime_object,value,history,boundary):
            strategy,asof=bundle(value,history,boundary)
            return runtime_object.evaluate(strategy,asof,boundary)
        def exits(value,history,boundary):
            strategy,asof=bundle(value,history,boundary)
            return resolve_exit_constraints(build_exit_request(strategy,asof))
        return E2RuntimeBinding(runtime,'0.2.0',invoke_v02,exits)
    if runtime_profile!='0.1.0': raise RuntimeContractError('Unsupported E2 runtime profile')
    runtime_version = str(runtime.version)
    if runtime_version != str(RUNTIME_VERSION):
        raise RuntimeContractError(
            "E2 runtime.version does not match exported RUNTIME_VERSION"
        )

    def invoke(
        runtime_object: Any,
        strategy_definition: Any,
        closed_history: tuple[Any, ...],
        evaluated_at: Any,
    ) -> Any:
        parsed_strategy = parse_strategy_definition(strategy_definition)
        return runtime_object.evaluate(parsed_strategy, closed_history, evaluated_at)

    return E2RuntimeBinding(
        runtime=runtime,
        runtime_version=runtime_version,
        invoke=invoke,
    )
