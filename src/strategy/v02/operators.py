"""Typed Decimal/boolean observations; unavailable operands never become false."""

from dataclasses import dataclass
from decimal import Decimal,DecimalException,localcontext

from indicators.v02.common import REFERENCE_CONTEXT,finite_decimal
from strategy.v02.ast import OPERATORS


@dataclass(frozen=True)
class OperatorValue:
    value: Decimal | bool | None
    reason_code: str='READY'

    @property
    def ready(self): return self.reason_code=='READY' and self.value is not None


def _invalid(reason='INVALID_OPERATOR_INPUT'): return OperatorValue(None,reason)


def evaluate_operator(name,values,*,previous_values=None):
    if name not in OPERATORS or name in {'LAG','ROLLING_MIN','ROLLING_MAX'}:
        raise ValueError('Unknown scalar operator')
    if not isinstance(values,(tuple,list)): return _invalid()
    lower,upper=(2,128) if name in {'AND','OR','MIN','MAX'} else (1,1) if name in {'ABS','NOT'} else (2,2)
    if not lower<=len(values)<=upper: return _invalid()
    if any(value is None for value in values): return _invalid('INSUFFICIENT_HISTORY')
    logical=name in {'AND','OR','NOT'}
    if logical:
        if any(type(value) is not bool for value in values): return _invalid()
        return OperatorValue(all(values) if name=='AND' else any(values) if name=='OR' else not values[0])
    if name=='EQ' and all(type(value) is bool for value in values):
        return OperatorValue(values[0]==values[1])
    if any(not isinstance(value,Decimal) for value in values): return _invalid()
    try:
        for value in values: finite_decimal(str(value))
    except ValueError: return _invalid()
    if name.startswith('CROSS_'):
        if not isinstance(previous_values,(tuple,list)) or len(previous_values)!=2:
            return _invalid('INSUFFICIENT_HISTORY')
        if any(value is None for value in previous_values): return _invalid('INSUFFICIENT_HISTORY')
        if any(not isinstance(value,Decimal) for value in previous_values): return _invalid()
        try:
            for value in previous_values: finite_decimal(str(value))
        except ValueError: return _invalid()
        current_left,current_right=values
        previous_left,previous_right=previous_values
        return OperatorValue(previous_left<=previous_right and current_left>current_right if name=='CROSS_ABOVE'
                             else previous_left>=previous_right and current_left<current_right)
    try:
        with localcontext(REFERENCE_CONTEXT):
            if name=='ADD': result=values[0]+values[1]
            elif name=='SUB': result=values[0]-values[1]
            elif name=='MUL': result=values[0]*values[1]
            elif name=='DIV':
                if values[1]==0: return _invalid('DIVISION_BY_ZERO')
                result=values[0]/values[1]
            elif name=='ABS': result=abs(values[0])
            elif name=='MIN': result=min(values)
            elif name=='MAX': result=max(values)
            elif name=='GT': result=values[0]>values[1]
            elif name=='GTE': result=values[0]>=values[1]
            elif name=='LT': result=values[0]<values[1]
            elif name=='LTE': result=values[0]<=values[1]
            elif name=='EQ': result=values[0]==values[1]
            else: raise ValueError('Unimplemented scalar operator')
    except DecimalException: return _invalid('INVALID_ARITHMETIC')
    return OperatorValue(result)


def evaluate_series_operator(name,values,*,window=None,lag_bars=0):
    if name not in {'LAG','ROLLING_MIN','ROLLING_MAX'}: raise ValueError('Unknown series operator')
    if type(lag_bars) is not int or not 0<=lag_bars<=10000: raise ValueError('Invalid lag')
    if name!='LAG' and (type(window) is not int or not 1<=window<=10000): raise ValueError('Invalid window')
    if not isinstance(values,(tuple,list)): return _invalid()
    size=1 if name=='LAG' else window
    if len(values)<size+lag_bars: return _invalid('INSUFFICIENT_HISTORY')
    selected=values[-size-lag_bars:-lag_bars] if lag_bars else values[-size:]
    if any(value is None for value in selected): return _invalid('INSUFFICIENT_HISTORY')
    if name=='LAG' and type(selected[0]) is bool: return OperatorValue(selected[0])
    if any(not isinstance(value,Decimal) for value in selected): return _invalid()
    try:
        for value in selected: finite_decimal(str(value))
    except ValueError: return _invalid()
    return OperatorValue(selected[0] if name=='LAG' else min(selected) if name=='ROLLING_MIN' else max(selected))
