"""E1 OKX public historical and Gate C current-market surface."""

from .candle import CONTRACT_SCHEMA_VERSION, Candle
from .current import (
    GATE_C_CLOCK_TOLERANCE_MS,
    GATE_C_MAX_FRESHNESS_MS,
    CurrentMarketState,
    MarketSnapshot,
    OkxPublicCurrentMarketSource,
    normalize_okx_current_candles,
    normalize_okx_ticker,
)
from .errors import (
    DuplicateCandleError,
    FutureMarketDataError,
    IncompleteHistoricalRangeError,
    MalformedCandleError,
    MarketDataError,
    MissingCandleError,
    NonMonotonicMarketDataError,
    OutOfOrderCandleError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
    RangeAlignmentError,
    StaleMarketDataError,
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
    "MarketSnapshot",
    "SUPPORTED_TIMEFRAMES",
    "OkxPublicHistoricalCandleSource",
    "OkxPublicCurrentMarketSource",
    "CurrentMarketState",
    "GATE_C_MAX_FRESHNESS_MS",
    "GATE_C_CLOCK_TOLERANCE_MS",
    "okx_instrument",
    "okx_bar",
    "normalize_okx_history_page",
    "normalize_okx_ticker",
    "normalize_okx_current_candles",
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
    "StaleMarketDataError",
    "FutureMarketDataError",
    "NonMonotonicMarketDataError",
]
