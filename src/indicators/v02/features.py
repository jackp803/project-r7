"""Versioned reference indicator evaluation over canonical E1 candle prefixes.

Batch and streaming share one numerical kernel. Snapshots are checked by
replaying verified history; their cached values never become trusted facts.
"""

from collections import deque
from dataclasses import dataclass,field
from datetime import datetime,timezone
from decimal import Decimal,DecimalException,localcontext
import hashlib
import json
from types import MappingProxyType

from indicators.v02.bands import donchian,population_bands
from indicators.v02.common import ARITHMETIC_PROFILE,REFERENCE_CONTEXT,canonical_decimal,finite_decimal
from indicators.v02.trend import EMA
from indicators.v02.wilder import WilderAverage
from market_data.candle import Candle
from market_data.timeframes import SUPPORTED_TIMEFRAMES,timeframe_duration

_FIELD_SOURCE=object()


def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _hash(value): return 'sha256:'+hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    semantic_version: str
    parameters: dict
    output: str
    timeframe: str
    source_field: str='close'
    source_dimensions: tuple[int,int] | None=None
    minimum_history: int=field(init=False)
    spec_hash: str=field(init=False)

    def __post_init__(self):
        from strategy.v02.ast import AstBuilder
        if not isinstance(self.timeframe,str) or self.timeframe not in SUPPORTED_TIMEFRAMES: raise ValueError('Unsupported timeframe')
        if not isinstance(self.source_field,str) or self.source_field not in {'open','high','low','close','volume'}:
            raise ValueError('Unsupported candle source field')
        dimensions=self.source_dimensions if self.source_dimensions is not None else (0,1) if self.source_field=='volume' else (1,0)
        if (not isinstance(dimensions,tuple) or len(dimensions)!=2 or
                any(type(power) is not int or abs(power)>4096 for power in dimensions)):
            raise ValueError('Bounded numeric source dimensions required')
        if self.name=='RSI' and dimensions!=(1,0): raise ValueError('RSI requires price source')
        object.__setattr__(self,'source_dimensions',dimensions)
        if not isinstance(self.parameters,dict): raise ValueError('Parameter mapping required')
        node={'kind':'indicator','name':self.name,'semantic_version':self.semantic_version,
              'parameters':dict(self.parameters),'output':self.output}
        candle_based=self.name in {'ATR','ADX','DONCHIAN'}
        if candle_based: node['timeframe']=self.timeframe
        else: node['source']={'kind':'field','timeframe':self.timeframe,'field':self.source_field}
        parsed=AstBuilder({}, {}, [self.timeframe]).compile(node)
        parameters=dict(parsed.data['parameters'])
        if 'k' in parameters: parameters['k']=canonical_decimal(parameters['k'])
        object.__setattr__(self,'parameters',MappingProxyType(parameters))
        object.__setattr__(self,'minimum_history',parsed.minimum_history)
        object.__setattr__(self,'spec_hash',_hash({'name':self.name,'version':self.semantic_version,
                     'parameters':parameters,'output':self.output,'timeframe':self.timeframe,
                     'source_field':self.source_field,'source_dimensions':dimensions,'arithmetic_profile':ARITHMETIC_PROFILE}))


@dataclass(frozen=True)
class CandlePrefix:
    candles: tuple[Candle,...]
    source_values: tuple[Decimal | None,...] | None=None

    def __post_init__(self):
        object.__setattr__(self,'candles',tuple(self.candles))
        if self.source_values is not None:
            object.__setattr__(self,'source_values',tuple(self.source_values))
            if len(self.source_values)!=len(self.candles): raise ValueError('Source prefix length mismatch')


@dataclass(frozen=True)
class FeatureValue:
    ready: bool
    value: Decimal | None
    reason_code: str
    units: str
    source_boundary: datetime | None
    source_bar_identity: tuple | None
    prefix_hash: str
    spec_hash: str
    semantic_version: str
    arithmetic_profile: str=ARITHMETIC_PROFILE


@dataclass
class FeatureState:
    spec: FeatureSpec
    count: int=0
    prefix_hash: str='sha256:'+hashlib.sha256(b'r7-feature-prefix-v1').hexdigest()
    previous: Candle | None=None
    previous_value: Decimal | None=None
    issue: str | None=None
    recovery_reason: str='NEW_STATE'
    kernel: dict=field(default_factory=dict)
    series: deque=field(default_factory=deque)
    observation: FeatureValue | None=None


@dataclass(frozen=True)
class FeatureUpdate:
    state: FeatureState
    observation: FeatureValue


def _observation(state,value=None):
    spec=state.spec
    dimensions=(0,0) if spec.name in {'RSI','ADX'} else (1,0) if spec.name in {'ATR','DONCHIAN'} else spec.source_dimensions
    units={(0,0):'dimensionless',(1,0):'price',(0,1):'volume'}.get(dimensions,f'price^{dimensions[0]}*volume^{dimensions[1]}')
    ready=state.issue is None and value is not None
    return FeatureValue(ready,value if ready else None,state.issue or ('READY' if ready else 'INSUFFICIENT_HISTORY'),
                        units,state.previous.close_time if state.previous else None,
                        state.previous.identity if state.previous else None,state.prefix_hash,
                        spec.spec_hash,spec.semantic_version)


def new_feature_state(spec):
    if not isinstance(spec,FeatureSpec): raise TypeError('FeatureSpec required')
    parameters=spec.parameters
    size=parameters.get('window',parameters.get('slow',1))
    state=FeatureState(spec,series=deque(maxlen=size+parameters.get('lag_bars',0)))
    if spec.name=='EMA': state.kernel['ema']=EMA(size)
    if spec.name=='RSI': state.kernel.update(gain=WilderAverage(size),loss=WilderAverage(size))
    if spec.name=='ATR': state.kernel['tr']=WilderAverage(size)
    if spec.name=='ADX':
        state.kernel.update(tr=WilderAverage(size),plus=WilderAverage(size),minus=WilderAverage(size),adx=WilderAverage(size))
    if spec.name=='MACD': state.kernel.update(fast=EMA(parameters['fast']),slow=EMA(parameters['slow']),signal=EMA(parameters['signal_window']))
    state.observation=_observation(state)
    return state


def _valid_input(state,bar,source_value):
    if not isinstance(bar,Candle): return 'CANONICAL_CANDLE_REQUIRED'
    if bar.timeframe!=state.spec.timeframe: return 'TIMEFRAME_MISMATCH'
    if not bar.is_closed: return 'UNFINALIZED_INPUT'
    if bar.open_time.microsecond or bar.close_time.microsecond: return 'MISALIGNED_INPUT'
    epoch=datetime(1970,1,1,tzinfo=timezone.utc)
    delta=bar.open_time-epoch
    seconds=delta.days*86400+delta.seconds
    if seconds%int(timeframe_duration(bar.timeframe).total_seconds()): return 'MISALIGNED_INPUT'
    if state.previous:
        if bar.symbol!=state.previous.symbol: return 'SYMBOL_MISMATCH'
        if bar.open_time!=state.previous.close_time: return 'GAP_IN_HISTORY'
    try:
        for name in ('open','high','low','close','volume'):
            value=getattr(bar,name)
            if not isinstance(value,Decimal): return 'NON_DECIMAL_INPUT'
            finite_decimal(str(value))
    except ValueError: return 'INVALID_DECIMAL_INPUT'
    if state.spec.name in {'ATR','ADX','DONCHIAN'}:
        if source_value is not _FIELD_SOURCE: return 'UNEXPECTED_SOURCE_OVERRIDE'
    else:
        if source_value is None: return 'MISSING_SOURCE_VALUE'
        if not isinstance(source_value,Decimal): return 'NON_DECIMAL_INPUT'
        try: finite_decimal(str(source_value))
        except ValueError: return 'INVALID_DECIMAL_INPUT'
    return None


def _material(bar,source):
    return {'schema_version':bar.schema_version,'symbol':bar.symbol,'timeframe':bar.timeframe,
            'open_time':bar.open_time.isoformat(),'close_time':bar.close_time.isoformat(),
            'financial':{key:canonical_decimal(str(getattr(bar,key))) for key in ('open','high','low','close','volume')},
            'is_closed':bar.is_closed,'source':bar.source,'source_record_id':bar.source_record_id,
            'received_at':bar.received_at.isoformat() if bar.received_at else None,
            'feature_source':'canonical candle' if source is _FIELD_SOURCE else canonical_decimal(str(source))}


def _true_range(bar,previous):
    if previous is None: return bar.high-bar.low
    return max(bar.high-bar.low,abs(bar.high-previous.close),abs(bar.low-previous.close))


def _atr(state,bar,source):
    return state.kernel['tr'].push(_true_range(bar,state.previous))

def _donchian(state,bar,source):
    state.series.append((bar.high,bar.low))
    params=state.spec.parameters; n=params['window']; lag=params['lag_bars']
    if len(state.series)<n+lag: return None
    values=list(state.series); selected=values[-n-lag:-lag] if lag else values[-n:]
    return donchian(selected)[state.spec.output]

def _adx(state,bar,source):
    if state.previous is None: return None
    kernel=state.kernel
    up=bar.high-state.previous.high; down=state.previous.low-bar.low
    plus=up if up>down and up>0 else Decimal(0)
    minus=down if down>up and down>0 else Decimal(0)
    tr=kernel['tr'].push(_true_range(bar,state.previous))
    sm_plus=kernel['plus'].push(plus); sm_minus=kernel['minus'].push(minus)
    if tr is None: return None
    plus_di=Decimal(100)*sm_plus/tr if tr else Decimal(0)
    minus_di=Decimal(100)*sm_minus/tr if tr else Decimal(0)
    denominator=plus_di+minus_di
    dx=Decimal(100)*abs(plus_di-minus_di)/denominator if denominator else Decimal(0)
    adx=kernel['adx'].push(dx)
    return {'value':adx,'plus_di':plus_di,'minus_di':minus_di}[state.spec.output]

def _sma(state,bar,source):
    state.series.append(source)
    n=state.spec.parameters['window']
    return sum(state.series,Decimal(0))/Decimal(n) if len(state.series)==n else None

def _ema(state,bar,source):
    state.series.append(source)
    return state.kernel['ema'].push(source)

def _rsi(state,bar,source):
    state.series.append(source)
    if state.previous_value is None: return None
    change=source-state.previous_value; kernel=state.kernel
    gain=kernel['gain'].push(max(change,Decimal(0))); loss=kernel['loss'].push(max(-change,Decimal(0)))
    if gain is None: return None
    if gain==loss==0: return Decimal(50)
    if loss==0: return Decimal(100)
    if gain==0: return Decimal(0)
    return Decimal(100)-Decimal(100)/(Decimal(1)+gain/loss)

def _macd(state,bar,source):
    state.series.append(source); kernel=state.kernel
    fast=kernel['fast'].push(source); slow=kernel['slow'].push(source)
    if slow is None: return None
    line=fast-slow; signal=kernel['signal'].push(line)
    return {'line':line,'signal':signal,'histogram':line-signal if signal is not None else None}[state.spec.output]

def _bollinger(state,bar,source):
    state.series.append(source); params=state.spec.parameters
    if len(state.series)<params['window']: return None
    return population_bands(state.series,finite_decimal(params['k']))[state.spec.output]

# Execution and generated inventory consume the same real callables.
INDICATOR_HANDLERS={'SMA':_sma,'EMA':_ema,'RSI':_rsi,'ATR':_atr,'ADX':_adx,
                    'MACD':_macd,'BOLLINGER':_bollinger,'DONCHIAN':_donchian}


def update_feature(state,bar,*,source_value=_FIELD_SOURCE):
    if not isinstance(state,FeatureState): raise TypeError('FeatureState required')
    candle_based=state.spec.name in {'ATR','ADX','DONCHIAN'}
    source=(getattr(bar,state.spec.source_field,None) if source_value is _FIELD_SOURCE and not candle_based else source_value)
    state.count+=1
    issue=_valid_input(state,bar,source)
    state.issue=state.issue or issue
    value=None
    with localcontext(REFERENCE_CONTEXT):
        if not state.issue:
            state.prefix_hash=_hash({'previous':state.prefix_hash,'bar':_material(bar,source)})
            handler=INDICATOR_HANDLERS.get(state.spec.name)
            if not callable(handler): state.issue='NOT_IMPLEMENTED'
            try: value=handler(state,bar,source) if callable(handler) else None
            except DecimalException: state.issue='INVALID_ARITHMETIC'
        else:
            state.prefix_hash=_hash({'previous':state.prefix_hash,'invalid_observation':state.issue,'count':state.count})
    if isinstance(bar,Candle): state.previous=bar
    if isinstance(source,Decimal): state.previous_value=source
    state.observation=_observation(state,value)
    return FeatureUpdate(state,state.observation)


def evaluate_feature(spec,prefix):
    if not isinstance(prefix,CandlePrefix): raise TypeError('CandlePrefix required')
    state=new_feature_state(spec)
    for i,bar in enumerate(prefix.candles):
        source=_FIELD_SOURCE if prefix.source_values is None else prefix.source_values[i]
        update_feature(state,bar,source_value=source)
    return state.observation


def snapshot_feature(state):
    def numeric(value): return canonical_decimal(str(value)) if value is not None else None
    cache={'kernel':{key:{'window':item.window,'count':item.count,'total':numeric(item.total),'value':numeric(item.value)}
                     for key,item in state.kernel.items()},
           'series':[[numeric(value) for value in pair] if isinstance(pair,tuple) else numeric(pair) for pair in state.series],
           'previous_value':numeric(state.previous_value),'issue':state.issue,
           'previous':_material(state.previous,_FIELD_SOURCE) if state.previous else None,
           'observation_value':numeric(state.observation.value)}
    return {'schema_version':'r7-feature-snapshot-v1','spec_hash':state.spec.spec_hash,
            'prefix_hash':state.prefix_hash,'count':state.count,'arithmetic_profile':ARITHMETIC_PROFILE,'state':cache}


def restore_feature(spec,prefix,snapshot):
    state=new_feature_state(spec)
    for i,bar in enumerate(prefix.candles):
        source=_FIELD_SOURCE if prefix.source_values is None else prefix.source_values[i]
        update_feature(state,bar,source_value=source)
    expected=snapshot_feature(state)
    try:
        raw=_canonical(snapshot)
        matches=len(raw.encode('utf-8'))<=4*1024*1024 and raw==_canonical(expected)
    except (ValueError,TypeError,RecursionError): matches=False
    state.recovery_reason='VALIDATED_REPLAY' if matches else 'RECOMPUTED_SNAPSHOT_MISMATCH'
    return state
