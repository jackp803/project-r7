"""Information-bound closed-bar selection and independent submission clocks."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime,timezone
from types import MappingProxyType
from indicators.v02.common import finite_decimal

from market_data.candle import Candle
from market_data.timeframes import SUPPORTED_TIMEFRAMES,is_timeframe_aligned
from strategy.runtime import MarketBoundaryError,_parse_utc


def fail(code): raise MarketBoundaryError(code,code)


def aligned(value,timeframe):
    return is_timeframe_aligned(value,timeframe)


@dataclass(frozen=True)
class AsOfBundle:
    candles_by_timeframe: Mapping
    boundary: datetime
    information_cutoff: datetime
    availability_model: str

    def __post_init__(self):
        selected,boundary,cutoff=_select_candles(self.candles_by_timeframe,self.boundary,self.information_cutoff,self.availability_model)
        object.__setattr__(self,'candles_by_timeframe',selected)
        object.__setattr__(self,'boundary',boundary)
        object.__setattr__(self,'information_cutoff',cutoff)

    def visible(self,timeframe,boundary=None,information_cutoff=None):
        boundary=self.boundary if boundary is None else boundary
        cutoff=self.information_cutoff if information_cutoff is None else information_cutoff
        return tuple(bar for bar in self.candles_by_timeframe.get(timeframe,())
                     if bar.close_time<=boundary and (bar.received_at or bar.close_time)<=cutoff)


def build_asof_bundle(candles_by_timeframe,boundary,information_cutoff,*,availability_model='recorded_received_at'):
    return AsOfBundle(candles_by_timeframe,boundary,information_cutoff,availability_model)


def _select_candles(candles_by_timeframe,boundary,information_cutoff,availability_model):
    boundary=_parse_utc(boundary,'boundary')
    cutoff=_parse_utc(information_cutoff,'information_cutoff')
    if availability_model not in {'recorded_received_at','historical_close_assumption'}: fail('UNSUPPORTED_AVAILABILITY_MODEL')
    if not isinstance(candles_by_timeframe,Mapping) or not 1<=len(candles_by_timeframe)<=4: fail('INVALID_TIMEFRAME_BUNDLE')
    selected={}
    for timeframe,rows in candles_by_timeframe.items():
        if not isinstance(timeframe,str) or timeframe not in SUPPORTED_TIMEFRAMES: fail('UNSUPPORTED_TIMEFRAME')
        if not isinstance(rows,(tuple,list)): fail('INVALID_CANDLE_SEQUENCE')
        visible=[]
        for row in rows:
            if not isinstance(row,Candle): fail('CANONICAL_CANDLE_REQUIRED')
            # Later/incomplete observations do not participate in this decision.
            if row.close_time>boundary or not row.is_closed: continue
            if row.received_at is None and availability_model!='historical_close_assumption': fail('MISSING_AVAILABILITY_EVIDENCE')
            available=row.received_at or row.close_time
            if available<row.close_time: fail('FINALITY_BEFORE_CLOSE')
            if available>cutoff: continue
            if row.timeframe!=timeframe: fail('TIMEFRAME_MISMATCH')
            try:
                for field in ('open','high','low','close','volume'): finite_decimal(str(getattr(row,field)))
            except ValueError: fail('INVALID_DECIMAL_INPUT')
            if not aligned(row.open_time,timeframe) or not aligned(row.close_time,timeframe): fail('MISALIGNED_CANDLE')
            if visible and (row.open_time!=visible[-1].close_time or row.symbol!=visible[-1].symbol):
                fail('NONCONTIGUOUS_HISTORY')
            visible.append(row)
        selected[timeframe]=tuple(visible)
    return MappingProxyType(selected),boundary,cutoff


@dataclass(frozen=True)
class ValidityDecision:
    status: str
    new_entry_allowed: bool
    required_management_allowed: bool=True


def assess_submission_validity(manifest,now):
    now=_parse_utc(now,'now')
    value=manifest.raw if hasattr(manifest,'raw') else manifest
    if not isinstance(value,Mapping): fail('INVALID_VALIDITY')
    intent=value.get('intent_class')
    interval=value.get('validity')
    if intent not in {'EVERGREEN_STRATEGY','TACTICAL_STRATEGY'} or not isinstance(interval,Mapping) or interval.keys()!={'from','until'}:
        fail('INVALID_VALIDITY')
    lower=_parse_utc(interval['from'],'valid_from') if interval['from'] is not None else None
    upper=_parse_utc(interval['until'],'valid_until') if interval['until'] is not None else None
    if intent=='TACTICAL_STRATEGY' and (lower is None or upper is None): fail('TACTICAL_INTERVAL_REQUIRED')
    if lower is not None and upper is not None and lower>=upper: fail('INVALID_VALIDITY_INTERVAL')
    if upper is not None and now>=upper: return ValidityDecision('EXPIRED',False)
    if lower is not None and now<lower: return ValidityDecision('NOT_YET_VALID',False)
    return ValidityDecision('VALID',True)


def entry_deadline(entry_valid_until,approved_plan_expiry):
    return min(_parse_utc(entry_valid_until,'entry_valid_until'),_parse_utc(approved_plan_expiry,'approved_plan_expiry'))


def entry_is_current(deadline,now):
    return _parse_utc(now,'now')<_parse_utc(deadline,'entry_valid_until')
