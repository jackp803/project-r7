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


def project_e2_runtime_binding() -> E2RuntimeBinding:
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
