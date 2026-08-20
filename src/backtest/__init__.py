"""E3 historical replay primitives for the contracts-v0.1 research skeleton."""

from .costs import FeeModel, FixedFundingModel, SlippageModel
from .metrics import MetricsSummary, calculate_metrics
from .replay import (
    BacktestResult,
    DatasetDescriptor,
    E2RuntimeBinding,
    HistoricalReplayEngine,
    ReplayConfig,
    ReplayTrade,
    ReplayValidationError,
    RuntimeContractError,
)

__all__ = [
    "BacktestResult",
    "DatasetDescriptor",
    "E2RuntimeBinding",
    "FeeModel",
    "FixedFundingModel",
    "HistoricalReplayEngine",
    "MetricsSummary",
    "ReplayConfig",
    "ReplayTrade",
    "ReplayValidationError",
    "RuntimeContractError",
    "SlippageModel",
    "calculate_metrics",
]
