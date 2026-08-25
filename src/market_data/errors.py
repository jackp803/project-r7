"""Typed E1 market-data failures for public historical/current OKX data."""


class MarketDataError(Exception):
    """Base class for E1 market-data failures."""


class UnsupportedTimeframeError(MarketDataError):
    pass


class UnsupportedSymbolError(MarketDataError):
    pass


class MalformedCandleError(MarketDataError):
    pass


class DuplicateCandleError(MarketDataError):
    pass


class OutOfOrderCandleError(MarketDataError):
    pass


class MissingCandleError(MarketDataError):
    pass


class UnclosedCandleError(MarketDataError):
    pass


class RangeAlignmentError(MarketDataError):
    pass


class IncompleteHistoricalRangeError(MarketDataError):
    pass


class ProviderResponseError(MarketDataError):
    pass


class ProviderUnavailableError(MarketDataError):
    pass


class ProviderRateLimitError(MarketDataError):
    pass


class StaleMarketDataError(MarketDataError):
    pass


class FutureMarketDataError(MarketDataError):
    pass


class NonMonotonicMarketDataError(MarketDataError):
    pass
