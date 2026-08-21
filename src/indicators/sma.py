from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence


def sma(values: Sequence[Decimal], window: int) -> Optional[Decimal]:
    """Return the simple moving average for the trailing window.

    Financial inputs must already be Decimal values. Insufficient history is
    represented as None rather than an invented partial-window value.
    """
    if type(window) is not int or window <= 0:
        raise ValueError("window must be a positive integer")
    if any(not isinstance(value, Decimal) for value in values):
        raise TypeError("SMA values must use Decimal semantics")
    if len(values) < window:
        return None

    trailing = values[-window:]
    return sum(trailing, Decimal("0")) / Decimal(window)
