"""Thin E3 binding to the authoritative E2 Strategy Runtime.

This module intentionally contains no indicator, DSL, or strategy-decision logic.
It only adapts E3's replay call shape to E2's public Slice 1 API.
"""

from __future__ import annotations

from typing import Any

from .replay import E2RuntimeBinding, RuntimeContractError


class E2RuntimeUnavailableError(ImportError):
    """Raised when an integration checkout does not contain E2's public runtime package."""


def project_e2_runtime_binding() -> E2RuntimeBinding:
    """Bind E3 replay to the real project E2 runtime.

    Required E2 public API, per E2 Slice 1 handoff::

        from strategy import StrategyRuntime, parse_strategy_definition
        strategy = parse_strategy_definition(strategy_payload)
        runtime = StrategyRuntime()
        signal = runtime.evaluate(strategy, candles, evaluated_at)

    The StrategyDefinition is parsed by E2 on every E3 evaluation call. E3 does
    not interpret rules, indicators, or parameters itself.
    """

    try:
        from strategy import RUNTIME_VERSION, StrategyRuntime, parse_strategy_definition
    except ImportError as exc:  # dependency is merged by E7 integration, not copied by E3
        raise E2RuntimeUnavailableError(
            "E2 Slice 1 package 'strategy' is unavailable. Integrate "
            "agent/e2-strategy-engine (or its reviewed main revision) before running "
            "the concrete E2/E3 replay test."
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
