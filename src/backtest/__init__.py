"""E3 historical replay primitives for the contracts-v0.1 research skeleton."""

from .costs import FeeModel, FixedFundingModel, SlippageModel
from .e2_runtime import E2RuntimeUnavailableError, project_e2_runtime_binding
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
    "E2RuntimeUnavailableError",
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
    "project_e2_runtime_binding",
]
