"""E1 market-data Slice 1 public surface.

Only the historical Candle path is exported here. Live market state, storage,
strategy, risk, and execution concerns remain outside E1 Slice 1.
"""

from .candle import CONTRACT_SCHEMA_VERSION, Candle
from .errors import (
    DuplicateCandleError,
    IncompleteHistoricalRangeError,
    MalformedCandleError,
    MarketDataError,
    MissingCandleError,
    OutOfOrderCandleError,
    ProviderResponseError,
    ProviderUnavailableError,
    RangeAlignmentError,
    UnclosedCandleError,
    UnsupportedSymbolError,
    UnsupportedTimeframeError,
)
from .historical import load_pionex_historical_candles, validate_historical_sequence
from .pionex import PionexPublicKlineSource, normalize_pionex_kline_page
from .timeframes import SUPPORTED_TIMEFRAMES

__all__ = [
    "CONTRACT_SCHEMA_VERSION",
    "Candle",
    "SUPPORTED_TIMEFRAMES",
    "PionexPublicKlineSource",
    "normalize_pionex_kline_page",
    "load_pionex_historical_candles",
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
]
