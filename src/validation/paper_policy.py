"""Selected forward policy adapter reusing canonical E3 numeric thresholds."""
from dataclasses import dataclass
import json

from validation.oos import ValidationPolicy
from validation.robustness.common import canonical,digest,freeze,exact,text,integer,decimal,dec_text,fail

_UNITS=dict(time='SECONDS',trade_count='CLOSED_TRADES',pnl='USDT_AMOUNT',
            expectancy='USDT_PER_CLOSED_TRADE',drawdown='USDT_AMOUNT')


@dataclass(frozen=True)
class PaperPromotionPolicy:
    canonical_json: str
    policy_hash: str
    validation_policy: ValidationPolicy
    def as_dict(self): return json.loads(self.canonical_json)


def parse_paper_promotion_policy(value,*,namespace):
    value=freeze(value)
    exact(value,('schema_version','policy_id','namespace','generation','validation_policy_version','min_elapsed_seconds',
        'min_closed_trades','min_net_pnl_usdt','min_expectancy_usdt_per_trade','max_drawdown_usdt','max_consecutive_losses',
        'min_profit_factor','profit_factor_null_handling','required_healthy_seconds','maximum_observation_gap_seconds','units'))
    if value['schema_version']!='r7-paper-promotion-policy-v0.2' or value['namespace']!=namespace or namespace not in ('FIXTURE','LOCAL_RESEARCH'):
        fail('PAPER_POLICY_NAMESPACE_PROFILE_MISMATCH')
    if value['units']!=_UNITS: fail('PAPER_POLICY_UNSUPPORTED_UNITS')
    for field in ('policy_id','validation_policy_version'): text(value[field])
    for field in ('generation','min_elapsed_seconds','min_closed_trades','required_healthy_seconds','maximum_observation_gap_seconds'):
        integer(value[field],1,2147483647)
    integer(value['max_consecutive_losses'],0,2147483647)
    if value['required_healthy_seconds']>value['min_elapsed_seconds']: fail('PAPER_POLICY_HEALTH_EXCEEDS_DURATION')
    if value['profit_factor_null_handling'] not in ('BLOCK','ALLOW_NO_LOSSES'): fail('PAPER_POLICY_NULL_HANDLING_REQUIRED')
    for field in ('min_net_pnl_usdt','min_expectancy_usdt_per_trade'):
        value[field]=dec_text(decimal(value[field]))
    for field in ('max_drawdown_usdt','min_profit_factor'):
        value[field]=dec_text(decimal(value[field],minimum=0))
    thresholds=ValidationPolicy(value['validation_policy_version'],value['min_closed_trades'],value['min_net_pnl_usdt'],
        value['max_drawdown_usdt'],value['max_consecutive_losses'],
        None if value['profit_factor_null_handling']=='ALLOW_NO_LOSSES' else value['min_profit_factor'])
    raw=canonical(value); return PaperPromotionPolicy(raw,digest(raw.encode()),thresholds)
