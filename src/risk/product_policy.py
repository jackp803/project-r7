"""Strict local selection adapter for the existing E5 RiskPolicy, without defaults."""
from dataclasses import dataclass,fields
from decimal import Decimal
import json

from registry.product_assessment import canonical,digest
from .policy import RiskPolicy

_UNITS=dict(margin='USDT_AMOUNT',notional='USDT_AMOUNT',estimated_cost='USDT_AMOUNT',
            drawdown='USDT_AMOUNT',leverage='RATIO',reward_risk='RATIO',time='SECONDS')
_DECIMALS=('max_margin','max_notional','max_leverage','min_reward_risk','max_estimated_cost','max_drawdown')


@dataclass(frozen=True)
class SelectedRiskPolicy:
    canonical_json: str
    policy_hash: str
    risk_policy: RiskPolicy


def parse_product_risk_policy(value,*,namespace):
    value=json.loads(canonical(value))
    if set(value)!= {'schema_version','namespace','generation','units','policy'}:
        raise ValueError('Strict selected risk policy fields required')
    if value['schema_version']!='r7-selected-risk-policy-v0.2' or namespace not in ('FIXTURE','LOCAL_RESEARCH') or value['namespace']!=namespace:
        raise ValueError('Selected risk namespace/profile mismatch')
    if type(value['generation']) is not int or not 1<=value['generation']<=2147483647 or value['units']!=_UNITS:
        raise ValueError('Explicit risk generation and canonical E5 units required')
    policy=value['policy']
    if not isinstance(policy,dict) or set(policy)!={field.name for field in fields(RiskPolicy)}:
        raise ValueError('Complete exact E5 policy required')
    material=dict(policy)
    for key in _DECIMALS:
        if not isinstance(policy[key],str) or len(policy[key])>128: raise ValueError('Decimal strings required')
        material[key]=Decimal(policy[key])
    for key in ('version','margin_mode'):
        if not isinstance(policy[key],str) or not policy[key].strip(): raise ValueError('Nonempty E5 policy identity required')
    risk=RiskPolicy(**material)
    raw=canonical(value)
    return SelectedRiskPolicy(raw,digest(raw),risk)
