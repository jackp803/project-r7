"""E1 OKX historical market-data public surface.

Only the bounded public historical Candle path is exported here. Live market
state, storage, private account data, strategy, risk, and execution remain out
of scope for task E1-20260821-002.
"""

from .candle import CONTRACT_SCHEMA_VERSION, Candle
from .errors import (
    DuplicateCandleError,
    IncompleteHistoricalRangeError,
    MalformedCandleError,
    MarketDataError,
    MissingCandleError,
    OutOfOrderCandleError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
    RangeAlignmentError,
    UnclosedCandleError,
    UnsupportedSymbolError,
    UnsupportedTimeframeError,
)
from .historical import load_okx_historical_candles, validate_historical_sequence
from .okx import OkxPublicHistoricalCandleSource, normalize_okx_history_page, okx_instrument
from .timeframes import SUPPORTED_TIMEFRAMES, okx_bar

__all__ = [
    "CONTRACT_SCHEMA_VERSION",
    "Candle",
    "SUPPORTED_TIMEFRAMES",
    "OkxPublicHistoricalCandleSource",
    "okx_instrument",
    "okx_bar",
    "normalize_okx_history_page",
    "load_okx_historical_candles",
    "validate_historical_sequence",
    "MarketDataError",
    "UnsupportedTimeframeError",
    "UnsupportedSymbolError",
    "MalformedCandleError",
    "DuplicateCandleError",
    "OutOfOrderCandleError",
    "MissingCandleError",
    "UnclosedCandleError",
    "RangeAlignmentError",
    "IncompleteHistoricalRangeError",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "ProviderRateLimitError",
]
