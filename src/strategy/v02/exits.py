"""Immutable E2 exit constraints bound to the actual as-of feature observation."""

from dataclasses import dataclass
import hashlib
import json

from indicators.v02.common import canonical_decimal
from indicators.v02.common import finite_decimal
from strategy.runtime import StrategyValidationError,_canonical_json,_format_utc,_load_definition,_parse_utc
from strategy.v02.ast import exact,identifier,fail
from strategy.v02.parser import canonical_definition
from strategy.v02.evaluation import ExpressionEvaluator,evaluate_v02

EXIT_REQUEST_PROFILE='r7-exit-request-v0.2'


@dataclass(frozen=True)
class ExitRequest:
    canonical_json: str

    def __post_init__(self):
        value=canonical_definition(_load_definition(self.canonical_json))
        exact(value,{'schema_version','exit_request_profile_version','strategy_id','strategy_version',
                     'strategy_content_hash','symbol','direction','market_boundary_ref','observed_at',
                     'reference_price','exit_policy','feature_anchors'},'INVALID_EXIT_REQUEST_FIELDS')
        if value['schema_version']!='contracts-v0.1' or value['exit_request_profile_version']!=EXIT_REQUEST_PROFILE:
            fail('UNSUPPORTED_EXIT_REQUEST_PROFILE')
        for key in ('strategy_id','strategy_version','strategy_content_hash','symbol','market_boundary_ref'):
            if not isinstance(value[key],str) or not 1<=len(value[key])<=256: fail('INVALID_EXIT_REQUEST_IDENTITY')
        if value['direction'] not in {'LONG','SHORT'}: fail('INVALID_EXIT_DIRECTION')
        _parse_utc(value['observed_at'],'observed_at')
        if finite_decimal(value['reference_price'])<=0: fail('INVALID_EXIT_REFERENCE')
        policy=value['exit_policy']
        exact(policy,{'stop','target','trailing','max_hold_seconds'},'INVALID_EXIT_POLICY')
        for role in ('stop','target','trailing'):
            item=policy[role]
            if item is None: continue
            if not isinstance(item,dict) or not isinstance(item.get('kind'),str): fail('INVALID_EXIT_POLICY')
            kind=item['kind']
            allowed={'fixed_price','fixed_distance','atr_multiple'} | ({'reward_risk'} if role=='target' else set())
            if role=='trailing': allowed={'fixed_distance'}
            if kind not in allowed: fail('INVALID_EXIT_POLICY')
            fields={'kind','feature','multiple'} if kind=='atr_multiple' else {'kind','multiple'} if kind=='reward_risk' else {'kind','value'}
            exact(item,fields,'INVALID_EXIT_POLICY')
            if kind=='atr_multiple': identifier(item['feature'])
            if finite_decimal(item['multiple' if kind in {'atr_multiple','reward_risk'} else 'value'])<=0: fail('INVALID_EXIT_VALUE')
        hold=policy['max_hold_seconds']
        if hold is not None and (type(hold) is not int or not 1<=hold<=31536000): fail('INVALID_MAX_HOLD')
        anchors=value['feature_anchors']
        if not isinstance(anchors,dict) or len(anchors)>128: fail('INVALID_EXIT_FEATURE_ANCHORS')
        for name,anchor in anchors.items():
            identifier(name)
            exact(anchor,{'value','semantic_version','market_boundary_ref','observed_at'},'INVALID_EXIT_FEATURE_ANCHOR')
            if anchor['semantic_version']!='r7-atr-wilder-v1' or anchor['market_boundary_ref']!=value['market_boundary_ref']:
                fail('EXIT_FEATURE_BINDING_MISMATCH')
            if finite_decimal(anchor['value'])<0: fail('INVALID_EXIT_FEATURE_ANCHOR')
            if _parse_utc(anchor['observed_at'],'feature_observed_at')>_parse_utc(value['observed_at'],'observed_at'):
                fail('FUTURE_EXIT_FEATURE_ANCHOR')
        object.__setattr__(self,'canonical_json',_canonical_json(value))

    @property
    def request_hash(self): return 'sha256:'+hashlib.sha256(self.canonical_json.encode('utf-8')).hexdigest()

    def as_dict(self): return json.loads(self.canonical_json)


def build_exit_request(strategy,bundle):
    signal=evaluate_v02(strategy,bundle)
    if signal['direction'] not in {'LONG','SHORT'}:
        raise StrategyValidationError('NON_ENTRY_EXIT_REQUEST','A healthy entry proposal is required')
    policy=json.loads(strategy.canonical_json)['rules']['exit_policy']
    evaluator=ExpressionEvaluator(strategy,bundle)
    anchors={}
    for role in ('stop','target'):
        item=policy[role]
        if item is not None and item['kind']=='atr_multiple':
            name=item['feature']
            observed=evaluator.value(strategy.features[name],bundle.boundary,bundle.information_cutoff)
            if not observed.ready: raise StrategyValidationError('ATR_OBSERVATION_UNAVAILABLE','Bound ATR is unavailable')
            anchors[name]={'value':canonical_decimal(str(observed.value)),
                           'semantic_version':'r7-atr-wilder-v1','market_boundary_ref':signal['market_boundary_ref'],
                           'observed_at':_format_utc(bundle.boundary)}
    value={'schema_version':'contracts-v0.1','exit_request_profile_version':EXIT_REQUEST_PROFILE,
           'strategy_id':strategy.strategy_id,'strategy_version':strategy.strategy_version,
           'strategy_content_hash':strategy.content_hash,'symbol':strategy.symbol,
           'direction':signal['direction'],'market_boundary_ref':signal['market_boundary_ref'],
           'observed_at':_format_utc(bundle.boundary),'reference_price':signal['reference_price'],
           'exit_policy':policy,'feature_anchors':anchors}
    return ExitRequest(_canonical_json(value))
