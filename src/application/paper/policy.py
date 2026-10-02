"""Explicit versioned simulation configuration; no installed financial defaults."""
from dataclasses import dataclass
from decimal import Decimal
import json

from registry.product_assessment import canonical, digest
from indicators.v02.common import finite_decimal
from strategy.v02.temporal import assess_submission_validity

_FIELDS = {'schema_version', 'namespace', 'mode', 'policy_id', 'generation',
    'initial_balance_usdt', 'quantity', 'leverage', 'fee_rate', 'slippage_bps',
    'estimated_roundtrip_cost_usdt', 'initial_fill_fraction', 'partial_remainder_behavior',
    'market_max_age_seconds', 'action_ttl_seconds', 'protection_poll_seconds',
    'maximum_cached_candles_per_timeframe', 'funding_model', 'account_scope'}


@dataclass(frozen=True)
class PaperSimulationPolicy:
    canonical_json: str
    policy_hash: str
    def as_dict(self): return json.loads(self.canonical_json)


def parse_simulation_policy(value, *, namespace):
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise ValueError('Complete explicit simulation policy required')
    if (value['schema_version'] != 'r7-paper-simulation-policy-v0.2' or
        value['namespace'] != namespace or (namespace, value['mode']) not in
        (('FIXTURE', 'ACCELERATED_FIXTURE'), ('LOCAL_RESEARCH', 'REAL_TIME'))):
        raise ValueError('Paper fixture/real elapsed profile mismatch')
    if not isinstance(value['policy_id'], str) or not 1 <= len(value['policy_id']) <= 256:
        raise ValueError('Simulation policy identity required')
    for name in ('generation', 'market_max_age_seconds', 'action_ttl_seconds',
                 'protection_poll_seconds', 'maximum_cached_candles_per_timeframe'):
        if type(value[name]) is not int or not 1 <= value[name] <= 2_147_483_647:
            raise ValueError('Explicit positive Paper generation/scheduling limits required')
    if value['maximum_cached_candles_per_timeframe'] > 4000 or value['action_ttl_seconds'] > 300:
        raise ValueError('Paper cache/action lifetime exceeds bounded runtime profile')
    for name in ('initial_balance_usdt', 'quantity', 'leverage', 'fee_rate', 'slippage_bps',
                 'estimated_roundtrip_cost_usdt', 'initial_fill_fraction'):
        if not isinstance(value[name], str) or len(value[name]) > 128: raise ValueError('Paper financial decimal strings required')
        number = finite_decimal(value[name])
        if not number.is_finite() or number < 0: raise ValueError('Finite nonnegative Paper financial values required')
        if name in ('initial_balance_usdt', 'quantity', 'leverage', 'initial_fill_fraction') and number == 0:
            raise ValueError('Paper balance/quantity/leverage/fill fraction must be positive')
    if Decimal(value['initial_fill_fraction']) > 1 or Decimal(value['fee_rate']) > 1 or Decimal(value['slippage_bps']) > 10000:
        raise ValueError('Invalid bounded Paper fill/cost model')
    if (value['partial_remainder_behavior'] != 'CANCEL_AFTER_FIRST_FILL' or
        value['funding_model'] != 'EXPLICIT_REGISTERED_PAPER_ZERO' or
        value['account_scope'] != 'ISOLATED_PER_STRATEGY_RUN'):
        raise ValueError('Unsupported simulation remainder/funding profile')
    raw = canonical(value)
    return PaperSimulationPolicy(raw, digest(raw))


def bind_submission_validity(value, now):
    if not isinstance(value, dict) or set(value) != {'intent_class', 'validity'}:
        raise ValueError('Explicit original submission validity required')
    assess_submission_validity(value, now)
    return canonical(value)
