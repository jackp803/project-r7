"""The additive E2 runtime profile; all execution remains a proposal."""

from decimal import Decimal
import hashlib

from indicators.v02.common import finite_decimal,canonical_decimal
from indicators.v02.features import CandlePrefix,FeatureSpec,evaluate_feature,_material
from strategy.runtime import RUNTIME_FAMILY,_canonical_json,_format_utc,_parse_utc,MarketBoundaryError
from strategy.v02.models import ParsedStrategyV02
from strategy.v02.operators import OperatorValue,evaluate_operator,evaluate_series_operator
from strategy.v02.temporal import AsOfBundle,aligned

RUNTIME_VERSION='0.2.0'


class ExpressionEvaluator:
    def __init__(self,strategy,bundle):
        self.strategy,self.bundle=strategy,bundle
        self.cache={}

    def value(self,expression,boundary,cutoff):
        key=(id(expression),boundary,cutoff)
        if key not in self.cache: self.cache[key]=self._value(expression,boundary,cutoff)
        return self.cache[key]

    def series(self,expression,timeframe,boundary,cutoff):
        rows=self.bundle.visible(timeframe,boundary,cutoff)
        return rows,tuple(self.value(expression,row.close_time,cutoff) for row in rows)

    def _value(self,expression,boundary,cutoff):
        kind,data=expression.kind,expression.data
        if kind=='decimal': return OperatorValue(finite_decimal(data['value']))
        if kind=='parameter': return OperatorValue(Decimal(data['value']))
        if kind=='feature': return self.value(self.strategy.features[data['name']],boundary,cutoff)
        if kind=='field':
            rows=self.bundle.visible(data['timeframe'],boundary,cutoff)
            return OperatorValue(getattr(rows[-1],data['field'])) if rows else OperatorValue(None,'INSUFFICIENT_HISTORY')
        if kind=='indicator':
            if expression.children:
                source=expression.children[0]
                timeframe=next(iter(source.source_timeframes))
                rows,values=self.series(source,timeframe,boundary,cutoff)
                # Leading source warmup is unavailable, never an invented zero.
                first=next((i for i,value in enumerate(values) if value.ready),len(values))
                if any(not value.ready and value.reason_code!='INSUFFICIENT_HISTORY' for value in values):
                    return next(value for value in values if not value.ready and value.reason_code!='INSUFFICIENT_HISTORY')
                feature=FeatureSpec(data['name'],data['semantic_version'],dict(data['parameters']),data['output'],timeframe,
                                    source_dimensions=source.units.signature()[:2])
                observed=evaluate_feature(feature,CandlePrefix(rows[first:],tuple(value.value for value in values[first:])))
            else:
                timeframe=data['timeframe']
                rows=self.bundle.visible(timeframe,boundary,cutoff)
                feature=FeatureSpec(data['name'],data['semantic_version'],dict(data['parameters']),data['output'],timeframe)
                observed=evaluate_feature(feature,CandlePrefix(rows))
            return OperatorValue(observed.value,observed.reason_code)
        name='LAG' if kind=='lag' else data['name']
        if name in {'LAG','ROLLING_MIN','ROLLING_MAX'}:
            source=expression.children[0]
            if len(source.source_timeframes)!=1: return OperatorValue(None,'INVALID_SERIES_CLOCK')
            timeframe=next(iter(source.source_timeframes))
            rows,values=self.series(source,timeframe,boundary,cutoff)
            if any(not value.ready and value.reason_code!='INSUFFICIENT_HISTORY' for value in values):
                return next(value for value in values if not value.ready and value.reason_code!='INSUFFICIENT_HISTORY')
            return evaluate_series_operator(name,tuple(value.value for value in values),
                                            window=data.get('window'),lag_bars=data.get('bars',data.get('lag_bars',0)))
        values=tuple(self.value(child,boundary,cutoff) for child in expression.children)
        invalid=next((value for value in values if not value.ready),None)
        if invalid is not None: return invalid
        previous=None
        if name.startswith('CROSS_'):
            frames=expression.source_timeframes
            timeframe=next(iter(frames)) if len(frames)==1 else self.strategy.evaluation_timeframe
            rows=self.bundle.visible(timeframe,boundary,cutoff)
            if len(rows)<2: return OperatorValue(None,'INSUFFICIENT_HISTORY')
            previous_boundary=rows[-2].close_time
            previous_cutoff=min(cutoff,previous_boundary)
            previous_values=tuple(self.value(child,previous_boundary,previous_cutoff) for child in expression.children)
            invalid=next((value for value in previous_values if not value.ready),None)
            if invalid is not None: return invalid
            previous=tuple(value.value for value in previous_values)
        return evaluate_operator(name,tuple(value.value for value in values),previous_values=previous)


def evaluate_v02(strategy,bundle):
    if not isinstance(strategy,ParsedStrategyV02) or not isinstance(bundle,AsOfBundle):
        raise MarketBoundaryError('INVALID_V02_INPUT','Parsed v0.2 strategy and explicit AsOfBundle required')
    if not aligned(bundle.boundary,strategy.evaluation_timeframe):
        raise MarketBoundaryError('MISALIGNED_EVALUATION','Evaluation boundary must be finalized timeframe close')
    if any(timeframe not in bundle.candles_by_timeframe for timeframe in strategy.required_timeframes):
        raise MarketBoundaryError('MISSING_REQUIRED_TIMEFRAME','Required timeframe missing from as-of bundle')
    rows_by_frame={timeframe:bundle.visible(timeframe) for timeframe in strategy.required_timeframes}
    if any(row.symbol!=strategy.symbol for rows in rows_by_frame.values() for row in rows):
        raise MarketBoundaryError('SYMBOL_MISMATCH','Consumed candle does not match strategy symbol')
    evaluator=ExpressionEvaluator(strategy,bundle)
    features=tuple(evaluator.value(strategy.features[name],bundle.boundary,bundle.information_cutoff) for name in strategy.feature_order)
    long=evaluator.value(strategy.long_expression,bundle.boundary,bundle.information_cutoff)
    short=evaluator.value(strategy.short_expression,bundle.boundary,bundle.information_cutoff)
    evaluation_rows=rows_by_frame[strategy.evaluation_timeframe]
    invalid=next((value for value in (*features,long,short) if not value.ready),None)
    current=bool(evaluation_rows and evaluation_rows[-1].close_time==bundle.boundary)
    if not current: direction,reasons='NO_TRADE',['MISSING_EVALUATION_BAR']
    elif invalid is not None: direction,reasons='NO_TRADE',[invalid.reason_code]
    elif long.value and short.value: direction,reasons='NO_TRADE',['CONFLICTING_ENTRY_RULES']
    elif long.value: direction,reasons='LONG',['LONG_RULE_MATCHED']
    elif short.value: direction,reasons='SHORT',['SHORT_RULE_MATCHED']
    else: direction,reasons='NO_TRADE',['NO_RULE_MATCHED']
    material={'runtime_family':RUNTIME_FAMILY,'runtime_version':RUNTIME_VERSION,
              'arithmetic_profile':strategy.arithmetic_profile,'strategy_content_hash':strategy.content_hash,
              'boundary':_format_utc(bundle.boundary),'information_cutoff':_format_utc(bundle.information_cutoff),
              'availability_model':bundle.availability_model,
              'candles':{timeframe:[_material(row,source=row.close) for row in rows] for timeframe,rows in rows_by_frame.items()}}
    boundary_ref='sha256:'+hashlib.sha256(_canonical_json(material).encode('utf-8')).hexdigest()
    identity={'strategy_id':strategy.strategy_id,'strategy_version':strategy.strategy_version,
              'strategy_content_hash':strategy.content_hash,'runtime_family':RUNTIME_FAMILY,'runtime_version':RUNTIME_VERSION,
              'market_boundary_ref':boundary_ref,'evaluated_at':_format_utc(bundle.boundary),'direction':direction,'reason_codes':reasons}
    signal={'schema_version':'contracts-v0.1','signal_id':'sig_'+hashlib.sha256(_canonical_json(identity).encode('utf-8')).hexdigest(),
            'strategy_id':strategy.strategy_id,'strategy_version':strategy.strategy_version,'strategy_content_hash':strategy.content_hash,
            'symbol':strategy.symbol,'evaluated_at':_format_utc(bundle.boundary),'direction':direction,
            'reason_codes':reasons,'market_boundary_ref':boundary_ref}
    if current: signal['reference_price']=canonical_decimal(str(evaluation_rows[-1].close))
    return signal
